using System.Globalization;
using System.Net;
using System.Net.NetworkInformation;
using System.Text.RegularExpressions;
using Lextm.SharpSnmpLib;
using Lextm.SharpSnmpLib.Messaging;
using Proservis.Agent.Desktop.Models;

namespace Proservis.Agent.Desktop.Services;

public sealed class SnmpCollector
{
    private static readonly HashSet<string> ExplicitBrandSelections = new(StringComparer.OrdinalIgnoreCase)
    {
        "Kyocera",
        "Konica Minolta",
        "Canon",
        "Samsung",
        "Lexmark",
    };

    private const string OidSysName = "1.3.6.1.2.1.1.5.0";
    private const string OidSysDescr = "1.3.6.1.2.1.1.1.0";
    private const string OidPrinterSerial = "1.3.6.1.2.1.43.5.1.1.17.1";
    private const string OidRicohSerial = "1.3.6.1.4.1.367.3.2.1.2.1.4.0";
    private const string OidCanonSerial = "1.3.6.1.4.1.1602.1.11.1.3.1.4.2.0";
    private const string OidXeroxSerial = "1.3.6.1.4.1.253.8.53.3.2.1.3.1";
    private const string OidInterfaceMacBase1 = "1.3.6.1.2.1.2.2.1.6.1";
    private const string OidInterfaceMacBase2 = "1.3.6.1.2.1.2.2.1.6.2";
    private const string OidMarkerLifeCountPrefix = "1.3.6.1.2.1.43.10.2.1.4.1.";
    private const string OidSupplyDescriptionPrefix = "1.3.6.1.2.1.43.11.1.1.6.1.";
    private const string OidSupplyMaxPrefix = "1.3.6.1.2.1.43.11.1.1.8.1.";
    private const string OidSupplyLevelPrefix = "1.3.6.1.2.1.43.11.1.1.9.1.";

    private const string OidKyoceraTotalCounter = "1.3.6.1.4.1.1347.43.10.1.1.12.1.1";
    private const string OidKyoceraBwCounter = "1.3.6.1.4.1.1347.42.2.1.1.1.8.1.1";
    private const string OidKyoceraColorCounter = "1.3.6.1.4.1.1347.42.2.1.1.1.8.1.2";

    private const string OidLexmarkBwCounter = "1.3.6.1.4.1.641.2.1.5.2";
    private const string OidLexmarkColorCounter = "1.3.6.1.4.1.641.2.1.5.3";
    private const string OidLexmarkTotalCounter = "1.3.6.1.4.1.641.2.1.5.1";
    private const string OidLexmarkPaperGeneralCountTypePrefix = "1.3.6.1.4.1.641.6.4.2.1.1.2.";
    private const string OidLexmarkPaperGeneralCountValuePrefix = "1.3.6.1.4.1.641.6.4.2.1.1.4.";
    private const string OidLexmarkSupplyColorantPrefix = "1.3.6.1.4.1.641.6.4.4.1.1.4.";
    private const string OidLexmarkSupplyDescriptionPrefix = "1.3.6.1.4.1.641.6.4.4.1.1.5.";
    private const string OidLexmarkSupplyStatusPrefix = "1.3.6.1.4.1.641.6.4.4.1.1.12.";
    private const string OidLexmarkSupplyCapacityPrefix = "1.3.6.1.4.1.641.6.4.4.1.1.14.";
    private const string OidLexmarkSupplyLevelPrefix = "1.3.6.1.4.1.641.6.4.4.1.1.16.";

    private const int LexmarkTypePrintTotal = 16;
    private const int LexmarkTypePrintMono = 17;
    private const int LexmarkTypePrintColor = 18;
    private const int LexmarkTypeClickPrintMono = 130;
    private const int LexmarkTypeClickPrintColor = 131;
    private const int LexmarkTypeClickPrintTotal = 133;

    public async Task<IReadOnlyList<DeviceTelemetryRow>> CollectAsync(
        AgentConfig config,
        Action<string>? log,
        CancellationToken cancellationToken)
    {
        var targets = new List<string>();
        targets.AddRange(config.StaticIps ?? []);
        targets.AddRange(config.DiscoveryRanges ?? []);

        var ips = IpRangeParser.Expand(targets, config.MaxTargetsPerCycle, out var truncatedBySafetyLimit).ToList();
        if (truncatedBySafetyLimit)
        {
            log?.Invoke(
                $"Guvenlik limiti devrede: hedefler {config.MaxTargetsPerCycle} IP ile sinirlandi. Ag kesintisi riskini azaltmak icin araligi daraltin.");
        }
        var excludedIps = BuildSafetyExcludedIps();
        var removedForSafety = ips.RemoveAll(ip => excludedIps.Contains(ip.ToString()));
        if (removedForSafety > 0)
        {
            log?.Invoke($"Guvenlik filtresi: yerel/gateway {removedForSafety} IP tarama disinda tutuldu.");
        }
        if (ips.Count == 0)
        {
            log?.Invoke("SNMP hedefi yok. DiscoveryRanges/StaticIps girin.");
            return [];
        }
        log?.Invoke($"SNMP tarama basladi. Hedef: {ips.Count} IP (limit: {config.MaxTargetsPerCycle})");

        var semaphore = new SemaphoreSlim(Math.Max(1, config.MaxParallel));
        var tasks = ips.Select(async ip =>
        {
            await semaphore.WaitAsync(cancellationToken);
            try
            {
                return await ProbeDeviceAsync(ip, config, log, cancellationToken);
            }
            finally
            {
                semaphore.Release();
            }
        });

        var rows = await Task.WhenAll(tasks);
        var rawResult = rows.Where(x => x is not null).Cast<DeviceTelemetryRow>().ToList();
        var result = DeduplicateBySerial(rawResult, log);
        log?.Invoke($"SNMP tarama bitti. Bulunan cihaz: {result.Count}");
        return result;
    }

    private static HashSet<string> BuildSafetyExcludedIps()
    {
        var excluded = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        try
        {
            foreach (var nic in NetworkInterface.GetAllNetworkInterfaces())
            {
                if (nic.OperationalStatus != OperationalStatus.Up) continue;
                if (nic.NetworkInterfaceType == NetworkInterfaceType.Loopback) continue;
                if (nic.NetworkInterfaceType == NetworkInterfaceType.Tunnel) continue;
                var props = nic.GetIPProperties();
                foreach (var unicast in props.UnicastAddresses)
                {
                    if (unicast.Address.AddressFamily != System.Net.Sockets.AddressFamily.InterNetwork) continue;
                    excluded.Add(unicast.Address.ToString());
                }
                foreach (var gateway in props.GatewayAddresses)
                {
                    if (gateway.Address.AddressFamily != System.Net.Sockets.AddressFamily.InterNetwork) continue;
                    excluded.Add(gateway.Address.ToString());
                }
            }
        }
        catch
        {
            // ignore network adapter probing failures; collector can proceed.
        }
        return excluded;
    }    private static List<DeviceTelemetryRow> DeduplicateBySerial(
        IReadOnlyList<DeviceTelemetryRow> rows,
        Action<string>? log)
    {
        if (rows.Count <= 1) return rows.ToList();

        var output = new List<DeviceTelemetryRow>();
        var groups = rows
            .GroupBy(r => (r.SerialNumber ?? string.Empty).Trim(), StringComparer.OrdinalIgnoreCase)
            .ToList();

        foreach (var group in groups)
        {
            if (group.Count() == 1)
            {
                output.Add(group.First());
                continue;
            }

            var selected = group
                .OrderByDescending(ScoreRow)
                .ThenBy(r => r.IpAddress ?? string.Empty, StringComparer.OrdinalIgnoreCase)
                .First();
            output.Add(selected);

            var droppedIps = group
                .Where(r => !ReferenceEquals(r, selected))
                .Select(r => r.IpAddress ?? "-")
                .Distinct(StringComparer.OrdinalIgnoreCase)
                .ToList();
            log?.Invoke(
                $"Ayni seri icin tekrar eden kayitlar elendi: serial={selected.SerialNumber}, secilenIp={selected.IpAddress ?? "-"}, elenen={string.Join(", ", droppedIps)}");
        }

        return output;
    }

    private static int ScoreRow(DeviceTelemetryRow row)
    {
        var score = 0;
        if (!IsLikelyNetworkOrBroadcast(row.IpAddress)) score += 3;
        if (!string.IsNullOrWhiteSpace(row.Hostname)) score += 1;
        if (row.TotalCounter.HasValue || row.BwCounter.HasValue) score += 1;
        return score;
    }

    private static bool IsLikelyNetworkOrBroadcast(string? ipAddress)
    {
        if (string.IsNullOrWhiteSpace(ipAddress)) return false;
        if (!IPAddress.TryParse(ipAddress, out var ip)) return false;
        var bytes = ip.GetAddressBytes();
        if (bytes.Length != 4) return false;
        return bytes[3] == 0 || bytes[3] == 255;
    }

    private static async Task<DeviceTelemetryRow?> ProbeDeviceAsync(
        IPAddress ip,
        AgentConfig config,
        Action<string>? log,
        CancellationToken cancellationToken)
    {
        var endpoint = new IPEndPoint(ip, config.SnmpPort);
        var community = new OctetString(config.SnmpCommunity);
        var timeout = Math.Max(500, config.SnmpTimeoutMs);
        var retries = Math.Max(0, config.SnmpRetries);

        try
        {
            var sysDescr = await GetStringAsync(endpoint, community, OidSysDescr, timeout, retries, cancellationToken);
            var detectedBrand = GuessBrand(sysDescr);
            if (!IsBrandSelected(config, detectedBrand)) return null;

            var serial = await GetStringAsync(endpoint, community, OidPrinterSerial, timeout, retries, cancellationToken);
            if (string.IsNullOrWhiteSpace(serial) && string.Equals(detectedBrand, "Ricoh", StringComparison.OrdinalIgnoreCase))
                serial = await GetStringAsync(endpoint, community, OidRicohSerial, timeout, retries, cancellationToken);
            if (string.IsNullOrWhiteSpace(serial) && string.Equals(detectedBrand, "Canon", StringComparison.OrdinalIgnoreCase))
                serial = await GetStringAsync(endpoint, community, OidCanonSerial, timeout, retries, cancellationToken);
            if (string.IsNullOrWhiteSpace(serial) && string.Equals(detectedBrand, "Xerox", StringComparison.OrdinalIgnoreCase))
                serial = await GetStringAsync(endpoint, community, OidXeroxSerial, timeout, retries, cancellationToken);

            if (string.IsNullOrWhiteSpace(serial))
            {
                var macRaw = await GetStringAsync(endpoint, community, OidInterfaceMacBase1, timeout, retries, cancellationToken);
                if (string.IsNullOrWhiteSpace(macRaw))
                    macRaw = await GetStringAsync(endpoint, community, OidInterfaceMacBase2, timeout, retries, cancellationToken);
                
                if (!string.IsNullOrWhiteSpace(macRaw))
                {
                    var macClean = new string(macRaw.Where(c => char.IsLetterOrDigit(c)).ToArray());
                    serial = "MAC-" + macClean.ToUpperInvariant();
                }
            }

            if (string.IsNullOrWhiteSpace(serial)) return null;

            var sysName = await GetStringAsync(endpoint, community, OidSysName, timeout, retries, cancellationToken);
            var supplies = await ReadStandardSupplyRowsAsync(endpoint, community, timeout, retries, cancellationToken, detectedBrand);
            var counters = await ReadStandardCounterIndexesAsync(endpoint, community, timeout, retries, cancellationToken, detectedBrand);

            if (string.Equals(detectedBrand, "Lexmark", StringComparison.OrdinalIgnoreCase))
            {
                var lexmarkSupplies = await ReadLexmarkSupplyRowsAsync(endpoint, community, timeout, retries, cancellationToken);
                if (lexmarkSupplies.Count > 0)
                {
                    supplies = lexmarkSupplies;
                }
            }

            var resolved = ResolveCounters(counters, supplies);

            (long? bw, long? color, long? total)? kyoceraRaw = null;
            if (string.Equals(detectedBrand, "Kyocera", StringComparison.OrdinalIgnoreCase))
            {
                var kyoceraResolved = await ResolveKyoceraCountersAsync(endpoint, community, timeout, retries, cancellationToken, resolved);
                kyoceraRaw = kyoceraResolved;
                resolved = kyoceraResolved;
                if (!resolved.bw.HasValue && resolved.total.HasValue && resolved.color.HasValue)
                {
                    var derivedBw = resolved.total.Value - resolved.color.Value;
                    if (derivedBw >= 0) resolved = (derivedBw, resolved.color, resolved.total);
                }
                if (!resolved.bw.HasValue && resolved.total.HasValue && !resolved.color.HasValue)
                {
                    resolved = (resolved.total.Value, 0, resolved.total);
                }
            }
            else if (string.Equals(detectedBrand, "Lexmark", StringComparison.OrdinalIgnoreCase))
            {
                resolved = await ResolveLexmarkCountersAsync(endpoint, community, timeout, retries, cancellationToken, resolved, log, ip);
            }

            var toner = ResolveTonerPercentages(supplies);
            var model = GuessModel(sysDescr, detectedBrand);

            var rawSuffix = kyoceraRaw.HasValue
                ? $" | kyoceraRawBw={kyoceraRaw.Value.bw?.ToString() ?? "null"} | kyoceraRawColor={kyoceraRaw.Value.color?.ToString() ?? "null"} | kyoceraRawTotal={kyoceraRaw.Value.total?.ToString() ?? "null"}"
                : string.Empty;

            log?.Invoke(
                $"SNMP cihaz {ip} | brand={detectedBrand ?? "-"} | serial={serial.Trim()} | bw={resolved.bw?.ToString() ?? "null"} | color={resolved.color?.ToString() ?? "null"} | total={resolved.total?.ToString() ?? "null"}{rawSuffix}");

            LogBrandDiagnostics(log, detectedBrand, ip, sysDescr, model, counters, supplies, resolved);

            return new DeviceTelemetryRow
            {
                SerialNumber = serial.Trim(),
                Brand = detectedBrand,
                Model = model,
                IpAddress = ip.ToString(),
                Hostname = string.IsNullOrWhiteSpace(sysName) ? null : sysName.Trim(),
                BwCounter = resolved.bw,
                ColorCounter = resolved.color,
                TotalCounter = resolved.total,
                TonerBlack = toner.black,
                TonerCyan = toner.cyan,
                TonerMagenta = toner.magenta,
                TonerYellow = toner.yellow,
                Online = true,
                Protocol = "snmp",
            };
        }
        catch
        {
            return null;
        }
    }

    private static async Task<string?> GetStringAsync(
        IPEndPoint endpoint,
        OctetString community,
        string oid,
        int timeoutMs,
        int retries,
        CancellationToken cancellationToken)
    {
        for (var attempt = 0; attempt <= retries; attempt++)
        {
            try
            {
                var task = Messenger.GetAsync(
                    VersionCode.V2,
                    endpoint,
                    community,
                    [new Variable(new ObjectIdentifier(oid))]);

                var completed = await Task.WhenAny(task, Task.Delay(timeoutMs, cancellationToken));
                if (completed != task) throw new System.TimeoutException();

                var result = await task;
                var data = result.FirstOrDefault()?.Data;
                return data switch
                {
                    OctetString os => os.ToString(),
                    Integer32 i => i.ToString(),
                    Counter32 c => c.ToString(),
                    Counter64 c64 => c64.ToString(),
                    Gauge32 g => g.ToString(),
                    TimeTicks t => t.ToString(),
                    _ => data?.ToString(),
                };
            }
            catch when (attempt < retries)
            {
            }
        }

        return null;
    }

    private static async Task<long?> GetLongAsync(
        IPEndPoint endpoint,
        OctetString community,
        string oid,
        int timeoutMs,
        int retries,
        CancellationToken cancellationToken)
    {
        var raw = await GetStringAsync(endpoint, community, oid, timeoutMs, retries, cancellationToken);
        if (string.IsNullOrWhiteSpace(raw)) return null;

        if (long.TryParse(raw, NumberStyles.Integer, CultureInfo.InvariantCulture, out var direct)) return direct;
        if (long.TryParse(raw, NumberStyles.Integer, CultureInfo.CurrentCulture, out direct)) return direct;

        var noSeparators = raw.Replace(".", string.Empty).Replace(",", string.Empty).Replace(" ", string.Empty);
        if (long.TryParse(noSeparators, NumberStyles.Integer, CultureInfo.InvariantCulture, out var cleaned)) return cleaned;

        var compactChars = noSeparators.Where(c => char.IsDigit(c) || c == '-').ToArray();
        if (compactChars.Length == 0) return null;
        var compact = new string(compactChars);
        if (long.TryParse(compact, NumberStyles.Integer, CultureInfo.InvariantCulture, out var extracted)) return extracted;

        return null;
    }
    private sealed class SupplyRow
    {
        public string Description { get; set; } = "";
        public string? Colorant { get; set; }
        public long? Max { get; set; }
        public long? Level { get; set; }
        public long? Status { get; set; }
        public string Source { get; set; } = "standard";
    }

    private sealed class LexmarkPaperCountRow
    {
        public int DeviceIndex { get; set; }
        public int RowIndex { get; set; }
        public int Type { get; set; }
        public long Value { get; set; }
    }

    private static async Task<List<long>> ReadStandardCounterIndexesAsync(
        IPEndPoint endpoint,
        OctetString community,
        int timeoutMs,
        int retries,
        CancellationToken cancellationToken,
        string? brand)
    {
        var values = new List<long>();
        var maxIndex = ResolveCounterMaxIndex(brand);
        for (var idx = 1; idx <= maxIndex; idx++)
        {
            var value = await GetLongAsync(endpoint, community, OidMarkerLifeCountPrefix + idx, timeoutMs, retries, cancellationToken);
            if (value.HasValue && value.Value >= 0) values.Add(value.Value);
        }

        return values;
    }

    private static async Task<List<SupplyRow>> ReadStandardSupplyRowsAsync(
        IPEndPoint endpoint,
        OctetString community,
        int timeoutMs,
        int retries,
        CancellationToken cancellationToken,
        string? brand)
    {
        var rows = new List<SupplyRow>();
        var maxIndex = ResolveSupplyMaxIndex(brand);
        for (var idx = 1; idx <= maxIndex; idx++)
        {
            var level = await GetLongAsync(endpoint, community, OidSupplyLevelPrefix + idx, timeoutMs, retries, cancellationToken);
            var max = await GetLongAsync(endpoint, community, OidSupplyMaxPrefix + idx, timeoutMs, retries, cancellationToken);
            var desc = await GetStringAsync(endpoint, community, OidSupplyDescriptionPrefix + idx, timeoutMs, retries, cancellationToken);
            if (!level.HasValue && !max.HasValue && string.IsNullOrWhiteSpace(desc)) continue;

            rows.Add(new SupplyRow
            {
                Description = (desc ?? string.Empty).Trim(),
                Max = max,
                Level = level,
            });
        }

        return rows;
    }

    private static async Task<List<SupplyRow>> ReadLexmarkSupplyRowsAsync(
        IPEndPoint endpoint,
        OctetString community,
        int timeoutMs,
        int retries,
        CancellationToken cancellationToken)
    {
        var rows = new List<SupplyRow>();

        for (var deviceIndex = 1; deviceIndex <= 2; deviceIndex++)
        {
            var emptyStreak = 0;
            for (var supplyIndex = 1; supplyIndex <= 32; supplyIndex++)
            {
                var suffix = $"{deviceIndex}.{supplyIndex}";
                var description = await GetStringAsync(endpoint, community, OidLexmarkSupplyDescriptionPrefix + suffix, timeoutMs, retries, cancellationToken);
                var colorant = await GetStringAsync(endpoint, community, OidLexmarkSupplyColorantPrefix + suffix, timeoutMs, retries, cancellationToken);
                var status = await GetLongAsync(endpoint, community, OidLexmarkSupplyStatusPrefix + suffix, timeoutMs, retries, cancellationToken);
                var capacity = await GetLongAsync(endpoint, community, OidLexmarkSupplyCapacityPrefix + suffix, timeoutMs, retries, cancellationToken);
                var level = await GetLongAsync(endpoint, community, OidLexmarkSupplyLevelPrefix + suffix, timeoutMs, retries, cancellationToken);

                if (string.IsNullOrWhiteSpace(description) && string.IsNullOrWhiteSpace(colorant) && !capacity.HasValue && !level.HasValue)
                {
                    emptyStreak++;
                    if (emptyStreak >= 8 && rows.Count > 0) break;
                    continue;
                }

                emptyStreak = 0;
                rows.Add(new SupplyRow
                {
                    Description = (description ?? string.Empty).Trim(),
                    Colorant = string.IsNullOrWhiteSpace(colorant) ? null : colorant.Trim(),
                    Max = capacity,
                    Level = level,
                    Status = status,
                    Source = "lexmark-mps",
                });
            }
        }

        return rows;
    }

    private static (long? bw, long? color, long? total) ResolveCounters(
        IReadOnlyList<long> counters,
        IReadOnlyList<SupplyRow> supplies)
    {
        if (counters.Count == 0) return (null, null, null);

        var normalized = counters.Where(x => x >= 0).ToList();
        var sorted = normalized.OrderByDescending(x => x).ToList();
        if (sorted.Count == 0) return (null, null, null);

        var hasColorSupplies = supplies.Any(x =>
            ContainsAnyWord(x.Description, ["cyan", "mavi"]) ||
            ContainsAnyWord(x.Description, ["magenta", "kirmizi", "k�rm�z�"]) ||
            ContainsAnyWord(x.Description, ["yellow", "sari", "sar�"]) ||
            ContainsAnyWord(x.Colorant ?? string.Empty, ["cyan", "magenta", "yellow"]));

        if (sorted.Count == 1)
        {
            var totalOnly = sorted[0];
            return hasColorSupplies ? (null, null, totalOnly) : (totalOnly, 0, totalOnly);
        }

        if (!hasColorSupplies)
        {
            return (sorted[0], 0, sorted[0]);
        }

        if (normalized.Count >= 3)
        {
            const long tolerance = 5;
            var totalCandidate = sorted[0];
            var rest = normalized.Where(v => v != totalCandidate).ToList();
            for (var i = 0; i < rest.Count; i++)
            {
                for (var j = i + 1; j < rest.Count; j++)
                {
                    var a = rest[i];
                    var b = rest[j];
                    var diff = Math.Abs((a + b) - totalCandidate);
                    if (diff <= tolerance)
                    {
                        return (a, b, totalCandidate);
                    }
                }
            }
        }

        var first = sorted[0];
        var second = sorted[1];
        if (first >= second && second >= 0)
        {
            var colorDerived = first - second;
            if (colorDerived >= 0) return (second, colorDerived, first);
        }

        return (first, second > 0 ? second : 0, first);
    }

    private static (int? black, int? cyan, int? magenta, int? yellow) ResolveTonerPercentages(IReadOnlyList<SupplyRow> supplies)
    {
        int? black = null;
        int? cyan = null;
        int? magenta = null;
        int? yellow = null;

        foreach (var row in supplies)
        {
            var percent = ComputeSupplyPercent(row.Level, row.Max);
            if (!percent.HasValue) continue;
            var description = row.Description;
            var colorant = row.Colorant ?? string.Empty;

            if (black is null && (ContainsAnyWord(description, ["black", "siyah", "bk", "k toner"]) || ContainsAnyWord(colorant, ["black"])))
            {
                black = percent;
                continue;
            }

            if (cyan is null && (ContainsAnyWord(description, ["cyan", "mavi", "c toner"]) || ContainsAnyWord(colorant, ["cyan"])))
            {
                cyan = percent;
                continue;
            }

            if (magenta is null && (ContainsAnyWord(description, ["magenta", "kirmizi", "k�rm�z�", "m toner"]) || ContainsAnyWord(colorant, ["magenta"])))
            {
                magenta = percent;
                continue;
            }

            if (yellow is null && (ContainsAnyWord(description, ["yellow", "sari", "sar�", "y toner"]) || ContainsAnyWord(colorant, ["yellow"])))
            {
                yellow = percent;
                continue;
            }
        }

        if (black is null || cyan is null || magenta is null || yellow is null)
        {
            var fallback = supplies
                .Select(x => ComputeSupplyPercent(x.Level, x.Max))
                .Where(x => x.HasValue)
                .Select(x => x!.Value)
                .Take(4)
                .ToList();
            if (black is null && fallback.Count > 0) black = fallback[0];
            if (cyan is null && fallback.Count > 1) cyan = fallback[1];
            if (magenta is null && fallback.Count > 2) magenta = fallback[2];
            if (yellow is null && fallback.Count > 3) yellow = fallback[3];
        }

        return (black, cyan, magenta, yellow);
    }

    private static int? ComputeSupplyPercent(long? level, long? max)
    {
        if (!level.HasValue || level.Value < 0) return null;
        if (max.HasValue && max.Value > 0)
        {
            var ratio = (double)level.Value / max.Value * 100.0;
            if (double.IsNaN(ratio) || double.IsInfinity(ratio)) return null;
            return (int)Math.Clamp(Math.Round(ratio), 0, 100);
        }

        return ToPercent(level);
    }

    private static int? ToPercent(long? value)
    {
        if (!value.HasValue || value.Value < 0) return null;
        if (value.Value > 100) return 100;
        return (int)value.Value;
    }
    private static bool ContainsAnyWord(string value, IEnumerable<string> words)
    {
        var normalized = (value ?? string.Empty).Trim().ToLowerInvariant();
        if (string.IsNullOrWhiteSpace(normalized)) return false;
        return words.Any(w => normalized.Contains(w, StringComparison.OrdinalIgnoreCase));
    }

    private static string? GuessBrand(string? sysDescr)
    {
        var s = (sysDescr ?? string.Empty).ToLowerInvariant();
        if (s.Contains("kyocera")) return "Kyocera";
        if (s.Contains("konica")) return "Konica Minolta";
        if (s.Contains("develop")) return "Konica Minolta";
        if (s.Contains("canon")) return "Canon";
        if (s.Contains("samsung")) return "Samsung";
        if (s.Contains("lexmark")) return "Lexmark";
        if (s.Contains("brother")) return "Brother";
        if (s.Contains("hp")) return "HP";
        if (s.Contains("xerox")) return "Xerox";
        if (s.Contains("ricoh")) return "Ricoh";
        if (s.Contains("epson")) return "Epson";
        if (s.Contains("oki")) return "OKI";
        if (s.Contains("sharp")) return "Sharp";
        return string.IsNullOrWhiteSpace(s) ? null : "Diger";
    }

    private static string? GuessModel(string? sysDescr, string? brand)
    {
        if (string.IsNullOrWhiteSpace(sysDescr) || string.IsNullOrWhiteSpace(brand)) return null;

        var cleaned = Regex.Replace(sysDescr.Trim(), "\\s+", " ");
        cleaned = cleaned.Split(';', ',', '\r', '\n')[0].Trim();
        if (cleaned.Length == 0) return null;

        string? model = brand switch
        {
            "Lexmark" => ExtractBrandModel(cleaned, "Lexmark"),
            "Canon" => ExtractBrandModel(cleaned, "Canon"),
            "Kyocera" => ExtractBrandModel(cleaned, "Kyocera"),
            "Konica Minolta" => ExtractBrandModel(cleaned, "Konica"),
            _ => null,
        };

        if (string.IsNullOrWhiteSpace(model)) return null;
        if (model.Length > 64) return null;
        if (model.Equals(cleaned, StringComparison.OrdinalIgnoreCase)) return null;

        return model.Trim();
    }

    private static string? ExtractBrandModel(string sysDescr, string brandToken)
    {
        var match = Regex.Match(
            sysDescr,
            $@"\b{Regex.Escape(brandToken)}\b[\s:/-]+(?<model>[A-Za-z0-9][A-Za-z0-9+\- ]{{2,40}})",
            RegexOptions.IgnoreCase);

        if (!match.Success) return null;

        var value = match.Groups["model"].Value.Trim();
        value = Regex.Replace(value, @"\b(Network|Printer|Series|PCL|UFR|PS3?|PostScript|Firmware|Version)\b.*$", string.Empty, RegexOptions.IgnoreCase).Trim();
        value = Regex.Replace(value, "\\s{2,}", " ").Trim(' ', '-', '/', ':');
        return value.Length == 0 ? null : value;
    }

    private static bool IsBrandSelected(AgentConfig config, string? detectedBrand)
    {
        var selected = config.SelectedBrands ?? [];
        if (selected.Count == 0) return true;
        if (string.IsNullOrWhiteSpace(detectedBrand))
        {
            return selected.Any(x => string.Equals(x, "Diger", StringComparison.OrdinalIgnoreCase));
        }

        if (selected.Any(x => string.Equals(x, detectedBrand, StringComparison.OrdinalIgnoreCase)))
        {
            return true;
        }

        var allowOther = selected.Any(x => string.Equals(x, "Diger", StringComparison.OrdinalIgnoreCase));
        return allowOther && !ExplicitBrandSelections.Contains(detectedBrand);
    }

    private static int ResolveCounterMaxIndex(string? brand)
    {
        if (string.Equals(brand, "Kyocera", StringComparison.OrdinalIgnoreCase)) return 48;
        if (string.Equals(brand, "Konica Minolta", StringComparison.OrdinalIgnoreCase)) return 32;
        if (string.Equals(brand, "Canon", StringComparison.OrdinalIgnoreCase)) return 32;
        if (string.Equals(brand, "Samsung", StringComparison.OrdinalIgnoreCase)) return 24;
        if (string.Equals(brand, "Lexmark", StringComparison.OrdinalIgnoreCase)) return 32;
        return 16;
    }

    private static int ResolveSupplyMaxIndex(string? brand)
    {
        if (string.Equals(brand, "Lexmark", StringComparison.OrdinalIgnoreCase)) return 48;
        if (string.Equals(brand, "Kyocera", StringComparison.OrdinalIgnoreCase)) return 48;
        if (string.Equals(brand, "Canon", StringComparison.OrdinalIgnoreCase)) return 32;
        if (string.Equals(brand, "Konica Minolta", StringComparison.OrdinalIgnoreCase)) return 32;
        return 24;
    }

    private static async Task<(long? bw, long? color, long? total)> ResolveKyoceraCountersAsync(
        IPEndPoint endpoint,
        OctetString community,
        int timeoutMs,
        int retries,
        CancellationToken cancellationToken,
        (long? bw, long? color, long? total) fallback)
    {
        var total = await GetLongAsync(endpoint, community, OidKyoceraTotalCounter, timeoutMs, retries, cancellationToken);
        var bw = await GetLongAsync(endpoint, community, OidKyoceraBwCounter, timeoutMs, retries, cancellationToken);
        var color = await GetLongAsync(endpoint, community, OidKyoceraColorCounter, timeoutMs, retries, cancellationToken);

        var hasAny = total.HasValue || bw.HasValue || color.HasValue;
        if (!hasAny) return fallback;

        var nextTotal = total ?? fallback.total;
        var nextBw = bw ?? fallback.bw;
        var nextColor = color ?? fallback.color;

        if (nextTotal.HasValue && nextBw.HasValue && !nextColor.HasValue)
        {
            var derived = nextTotal.Value - nextBw.Value;
            if (derived >= 0) nextColor = derived;
        }

        if (nextTotal.HasValue && nextColor.HasValue && !nextBw.HasValue)
        {
            var derived = nextTotal.Value - nextColor.Value;
            if (derived >= 0) nextBw = derived;
        }

        if (!nextTotal.HasValue && nextBw.HasValue && nextColor.HasValue)
        {
            nextTotal = nextBw.Value + nextColor.Value;
        }

        if (nextTotal.HasValue && nextBw.HasValue && nextBw.Value > 0)
        {
            if (!nextColor.HasValue || nextColor.Value == 0)
            {
                var derivedBw = nextTotal.Value - nextBw.Value;
                if (derivedBw > 0)
                {
                    nextColor = nextBw.Value;
                    nextBw = derivedBw;
                }
            }
        }

        return (nextBw, nextColor, nextTotal);
    }
    private static async Task<(long? bw, long? color, long? total)> ResolveLexmarkCountersAsync(
        IPEndPoint endpoint,
        OctetString community,
        int timeoutMs,
        int retries,
        CancellationToken cancellationToken,
        (long? bw, long? color, long? total) fallback,
        Action<string>? log,
        IPAddress ip)
    {
        var mpsRows = await ReadLexmarkPaperCountsAsync(endpoint, community, timeoutMs, retries, cancellationToken);
        if (mpsRows.Count > 0)
        {
            var bw = SelectLexmarkCounter(mpsRows, LexmarkTypePrintMono, LexmarkTypeClickPrintMono);
            var color = SelectLexmarkCounter(mpsRows, LexmarkTypePrintColor, LexmarkTypeClickPrintColor);
            var total = SelectLexmarkCounter(mpsRows, LexmarkTypePrintTotal, LexmarkTypeClickPrintTotal);

            if (!total.HasValue && bw.HasValue && color.HasValue)
            {
                total = bw.Value + color.Value;
            }

            if (bw.HasValue || color.HasValue || total.HasValue)
            {
                log?.Invoke(
                    $"SNMP debug Lexmark {ip} | source=mps | bw={bw?.ToString() ?? "null"} | color={color?.ToString() ?? "null"} | total={total?.ToString() ?? "null"}");
                return (bw ?? fallback.bw, color ?? fallback.color, total ?? fallback.total);
            }
        }

        var legacyBw = await GetLongAsync(endpoint, community, OidLexmarkBwCounter, timeoutMs, retries, cancellationToken);
        var legacyColor = await GetLongAsync(endpoint, community, OidLexmarkColorCounter, timeoutMs, retries, cancellationToken);
        var legacyTotal = await GetLongAsync(endpoint, community, OidLexmarkTotalCounter, timeoutMs, retries, cancellationToken);

        if (!legacyBw.HasValue && !legacyColor.HasValue && !legacyTotal.HasValue)
        {
            return fallback;
        }

        var nextBw = legacyBw ?? fallback.bw;
        var nextColor = legacyColor ?? fallback.color;
        var nextTotal = legacyTotal ?? fallback.total;

        if (!nextTotal.HasValue && nextBw.HasValue && nextColor.HasValue)
        {
            nextTotal = nextBw.Value + nextColor.Value;
        }

        log?.Invoke(
            $"SNMP debug Lexmark {ip} | source=legacy | bw={nextBw?.ToString() ?? "null"} | color={nextColor?.ToString() ?? "null"} | total={nextTotal?.ToString() ?? "null"}");

        return (nextBw, nextColor, nextTotal);
    }

    private static async Task<List<LexmarkPaperCountRow>> ReadLexmarkPaperCountsAsync(
        IPEndPoint endpoint,
        OctetString community,
        int timeoutMs,
        int retries,
        CancellationToken cancellationToken)
    {
        var rows = new List<LexmarkPaperCountRow>();

        for (var deviceIndex = 1; deviceIndex <= 2; deviceIndex++)
        {
            var emptyStreak = 0;
            for (var rowIndex = 1; rowIndex <= 64; rowIndex++)
            {
                var suffix = $"{deviceIndex}.{rowIndex}";
                var type = await GetLongAsync(endpoint, community, OidLexmarkPaperGeneralCountTypePrefix + suffix, timeoutMs, retries, cancellationToken);
                if (!type.HasValue)
                {
                    emptyStreak++;
                    if (emptyStreak >= 10 && rows.Count > 0) break;
                    continue;
                }

                emptyStreak = 0;
                var value = await GetLongAsync(endpoint, community, OidLexmarkPaperGeneralCountValuePrefix + suffix, timeoutMs, retries, cancellationToken);
                if (!value.HasValue) continue;

                rows.Add(new LexmarkPaperCountRow
                {
                    DeviceIndex = deviceIndex,
                    RowIndex = rowIndex,
                    Type = (int)type.Value,
                    Value = value.Value,
                });
            }
        }

        return rows;
    }

    private static long? SelectLexmarkCounter(IReadOnlyList<LexmarkPaperCountRow> rows, params int[] preferredTypes)
    {
        foreach (var preferredType in preferredTypes)
        {
            var hit = rows
                .Where(x => x.Type == preferredType)
                .OrderByDescending(x => x.Value)
                .FirstOrDefault();
            if (hit is not null)
            {
                return hit.Value;
            }
        }

        return null;
    }

    private static void LogBrandDiagnostics(
        Action<string>? log,
        string? brand,
        IPAddress ip,
        string? sysDescr,
        string? model,
        IReadOnlyList<long> counters,
        IReadOnlyList<SupplyRow> supplies,
        (long? bw, long? color, long? total) resolved)
    {
        if (log is null) return;
        if (!string.Equals(brand, "Lexmark", StringComparison.OrdinalIgnoreCase) &&
            !string.Equals(brand, "Canon", StringComparison.OrdinalIgnoreCase))
        {
            return;
        }

        var needsCounterDebug = !resolved.bw.HasValue || !resolved.color.HasValue;
        var needsSupplyDebug = supplies.Count == 0 || supplies.All(x => !ComputeSupplyPercent(x.Level, x.Max).HasValue);
        if (!needsCounterDebug && !needsSupplyDebug) return;

        var counterText = counters.Count == 0 ? "-" : string.Join(", ", counters.Take(8));
        var supplyText = supplies.Count == 0
            ? "-"
            : string.Join(" | ", supplies.Take(6).Select(x =>
                $"{(string.IsNullOrWhiteSpace(x.Colorant) ? x.Description : $"{x.Description}/{x.Colorant}")}:{x.Level?.ToString() ?? "null"}/{x.Max?.ToString() ?? "null"}"));

        log(
            $"SNMP debug {brand} {ip} | modelGuess={(model ?? "-")} | sysDescr={(sysDescr ?? "-")} | counters=[{counterText}] | supplies=[{supplyText}]");
    }
}


