using System.Net;
using System.Net.Sockets;

namespace Proservis.Agent.Desktop.Services;

internal static class IpRangeParser
{
    public static IReadOnlyList<IPAddress> Expand(IEnumerable<string> ranges)
        => Expand(ranges, 1024, out _);

    public static IReadOnlyList<IPAddress> Expand(IEnumerable<string> ranges, int maxHosts, out bool wasTruncated)
    {
        wasTruncated = false;
        maxHosts = Math.Max(1, maxHosts);

        var set = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var output = new List<IPAddress>();

        foreach (var raw in ranges ?? [])
        {
            var token = (raw ?? "").Trim();
            if (string.IsNullOrWhiteSpace(token)) continue;
            token = NormalizeShortcutRange(token);

            IEnumerable<IPAddress> ips = token.Contains('/')
                ? ParseCidr(token)
                : token.Contains('-')
                    ? ParseStartEnd(token)
                    : ParseSingle(token);

            foreach (var ip in ips)
            {
                var key = ip.ToString();
                if (!set.Add(key))
                {
                    continue;
                }

                if (output.Count >= maxHosts)
                {
                    wasTruncated = true;
                    return output;
                }

                output.Add(ip);
            }
        }

        return output;
    }

    private static IEnumerable<IPAddress> ParseSingle(string raw)
    {
        if (IPAddress.TryParse(raw, out var ip) && ip.AddressFamily == AddressFamily.InterNetwork)
        {
            yield return ip;
        }
    }

    private static string NormalizeShortcutRange(string raw)
    {
        if (raw.Contains('/') || raw.Contains('-')) return raw;

        var parts = raw
            .Split('.', StringSplitOptions.TrimEntries | StringSplitOptions.RemoveEmptyEntries);

        if (parts.Length is < 1 or > 3) return raw;
        if (parts.Any(part => !byte.TryParse(part, out _))) return raw;

        return parts.Length switch
        {
            1 => $"{parts[0]}.0.0.0/8",
            2 => $"{parts[0]}.{parts[1]}.0.0/16",
            3 => $"{parts[0]}.{parts[1]}.{parts[2]}.0/24",
            _ => raw,
        };
    }

    private static IEnumerable<IPAddress> ParseStartEnd(string raw)
    {
        var parts = raw.Split('-', StringSplitOptions.TrimEntries | StringSplitOptions.RemoveEmptyEntries);
        if (parts.Length != 2) yield break;
        if (!TryToUInt32(parts[0], out var start)) yield break;
        if (!TryToUInt32(parts[1], out var end)) yield break;
        if (end < start) (start, end) = (end, start);
        for (var i = start; i <= end; i++)
        {
            yield return FromUInt32(i);
            if (i == uint.MaxValue) break;
        }
    }

    private static IEnumerable<IPAddress> ParseCidr(string raw)
    {
        var parts = raw.Split('/', StringSplitOptions.TrimEntries | StringSplitOptions.RemoveEmptyEntries);
        if (parts.Length != 2) yield break;
        if (!TryToUInt32(parts[0], out var ip)) yield break;
        if (!int.TryParse(parts[1], out var prefix)) yield break;
        if (prefix < 0 || prefix > 32) yield break;

        var mask = prefix == 0 ? 0u : uint.MaxValue << (32 - prefix);
        var network = ip & mask;
        var broadcast = network | ~mask;
        // For regular subnets, skip network and broadcast addresses.
        var start = (prefix <= 30) ? network + 1 : network;
        var end = (prefix <= 30) ? broadcast - 1 : broadcast;
        if (start > end) yield break;
        for (var i = start; i <= end; i++)
        {
            yield return FromUInt32(i);
            if (i == uint.MaxValue) break;
        }
    }

    private static bool TryToUInt32(string value, out uint result)
    {
        result = 0;
        if (!IPAddress.TryParse(value, out var ip)) return false;
        if (ip.AddressFamily != AddressFamily.InterNetwork) return false;
        var bytes = ip.GetAddressBytes();
        result = (uint)(bytes[0] << 24 | bytes[1] << 16 | bytes[2] << 8 | bytes[3]);
        return true;
    }

    private static IPAddress FromUInt32(uint value)
    {
        var bytes = new[]
        {
            (byte)(value >> 24),
            (byte)(value >> 16),
            (byte)(value >> 8),
            (byte)value,
        };
        return new IPAddress(bytes);
    }
}
