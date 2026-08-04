using System.Net.Http.Json;
using Proservis.Agent.Desktop.Models;

namespace Proservis.Agent.Desktop.Services;

public sealed class TelemetryUploader
{
    private static readonly HttpClient SecureClient = CreateHttpClient(verifyTls: true);
    private static readonly HttpClient InsecureClient = CreateHttpClient(verifyTls: false);

    public async Task ReportStatusAsync(
        AgentConfig config,
        string status,
        string? statusReason,
        Action<string>? log,
        CancellationToken cancellationToken)
    {
        var normalizedStatus = (status ?? string.Empty).Trim().ToLowerInvariant();
        if (normalizedStatus is not ("online" or "offline" or "warning"))
        {
            throw new InvalidOperationException("Unsupported status value.");
        }

        var payload = new
        {
            tenantId = config.TenantId,
            agentId = config.AgentId,
            apiKey = config.ApiKey,
            status = normalizedStatus,
            statusReason = string.IsNullOrWhiteSpace(statusReason) ? null : statusReason.Trim(),
            version = config.Version,
            machineName = Environment.MachineName,
            siteName = config.CustomerName,
        };

        var endpoint = $"{config.ServerUrl.TrimEnd('/')}/api/agent/status";
        using var response = await GetHttpClient(config.VerifyTls).PostAsJsonAsync(endpoint, payload, cancellationToken);
        var body = await response.Content.ReadAsStringAsync(cancellationToken);

        if (!response.IsSuccessStatusCode)
        {
            throw new InvalidOperationException($"Status update failed {(int)response.StatusCode}: {body}");
        }

        log?.Invoke($"Agent durum bildirildi: {normalizedStatus}");
    }

    public async Task UploadAsync(
        AgentConfig config,
        IReadOnlyList<DeviceTelemetryRow> rows,
        Action<string>? log,
        CancellationToken cancellationToken)
    {
        var payload = new AgentTelemetryUploadRequest
        {
            TenantId = config.TenantId,
            AgentId = config.AgentId,
            ApiKey = config.ApiKey,
            CollectedAt = DateTimeOffset.UtcNow.ToString("O"),
            Version = config.Version,
            Devices = rows.ToList(),
        };

        var endpoint = $"{config.ServerUrl.TrimEnd('/')}/api/agent/telemetry/upload";
        using var response = await GetHttpClient(config.VerifyTls).PostAsJsonAsync(endpoint, payload, cancellationToken);
        var body = await response.Content.ReadAsStringAsync(cancellationToken);

        if (!response.IsSuccessStatusCode)
        {
            throw new InvalidOperationException($"Upload failed {(int)response.StatusCode}: {body}");
        }

        log?.Invoke($"Upload basarili: {(int)response.StatusCode}");
    }

    private static HttpClient GetHttpClient(bool verifyTls) => verifyTls ? SecureClient : InsecureClient;

    private static HttpClient CreateHttpClient(bool verifyTls)
    {
        var handler = new SocketsHttpHandler
        {
            PooledConnectionIdleTimeout = TimeSpan.FromMinutes(2),
            PooledConnectionLifetime = TimeSpan.FromMinutes(10),
            MaxConnectionsPerServer = 8,
        };

        if (!verifyTls)
        {
            handler.SslOptions.RemoteCertificateValidationCallback = static (_, _, _, _) => true;
        }

        return new HttpClient(handler, disposeHandler: false)
        {
            Timeout = TimeSpan.FromSeconds(30),
        };
    }
}
