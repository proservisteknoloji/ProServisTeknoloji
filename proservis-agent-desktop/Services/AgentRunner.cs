using Proservis.Agent.Desktop.Models;

namespace Proservis.Agent.Desktop.Services;

public sealed class AgentRunner
{
    private const int SafeMaxParallel = 8;
    private readonly SnmpCollector _collector = new();
    private readonly TelemetryUploader _uploader = new();
    private CancellationTokenSource? _cts;
    private Task? _loopTask;

    public bool IsRunning => _loopTask is { IsCompleted: false };

    public event Action<string>? Log;
    public event Action<bool>? RunningChanged;

    public void Start(AgentConfig config)
    {
        if (IsRunning) return;
        config = NormalizeConfig(config);
        ValidateConfig(config);

        _cts = new CancellationTokenSource();
        var token = _cts.Token;
        _loopTask = Task.Run(async () =>
        {
            RunningChanged?.Invoke(true);
            Log?.Invoke("Agent baslatildi.");
            try
            {
                await TryReportStatusAsync(config, "online", null);
                while (!token.IsCancellationRequested)
                {
                    await RunCycleAsync(config, token);
                    await Task.Delay(TimeSpan.FromSeconds(Math.Max(10, config.IntervalSeconds)), token);
                }
            }
            catch (OperationCanceledException)
            {
                // stop
            }
            catch (Exception ex)
            {
                Log?.Invoke($"Agent dongu hatasi: {ex.Message}");
            }
            finally
            {
                await TryReportStatusAsync(config, "offline", "Agent durduruldu");
                RunningChanged?.Invoke(false);
                Log?.Invoke("Agent durdu.");
            }
        }, token);
    }

    public async Task RunOnceAsync(AgentConfig config)
    {
        config = NormalizeConfig(config);
        ValidateConfig(config);
        using var cts = new CancellationTokenSource(TimeSpan.FromMinutes(2));
        await RunCycleAsync(config, cts.Token);
    }

    public async Task StopAsync()
    {
        if (!IsRunning) return;
        _cts?.Cancel();
        try
        {
            if (_loopTask is not null) await _loopTask;
        }
        catch
        {
            // ignore
        }
        finally
        {
            _cts?.Dispose();
            _cts = null;
            _loopTask = null;
        }
    }

    private async Task RunCycleAsync(AgentConfig config, CancellationToken token)
    {
        Log?.Invoke("Tarama basliyor...");
        var rows = await _collector.CollectAsync(config, Log, token);
        if (rows.Count == 0)
        {
            Log?.Invoke("Cihaz bulunamadi.");
            return;
        }

        Log?.Invoke($"Bulunan cihaz: {rows.Count}. Gonderim basliyor...");
        await _uploader.UploadAsync(config, rows, Log, token);
    }

    private static void ValidateConfig(AgentConfig config)
    {
        var missing = new List<string>();
        if (string.IsNullOrWhiteSpace(config.TenantId)) missing.Add(nameof(config.TenantId));
        if (string.IsNullOrWhiteSpace(config.AgentId)) missing.Add(nameof(config.AgentId));
        if (string.IsNullOrWhiteSpace(config.ApiKey)) missing.Add(nameof(config.ApiKey));
        if (string.IsNullOrWhiteSpace(config.ServerUrl)) missing.Add(nameof(config.ServerUrl));
        if (missing.Count > 0)
        {
            throw new InvalidOperationException("Eksik alanlar: " + string.Join(", ", missing));
        }
    }

    private static AgentConfig NormalizeConfig(AgentConfig config)
    {
        config.MaxParallel = Math.Clamp(config.MaxParallel, 1, SafeMaxParallel);
        config.MaxTargetsPerCycle = Math.Clamp(config.MaxTargetsPerCycle, 64, 4096);
        config.SnmpTimeoutMs = Math.Max(500, config.SnmpTimeoutMs);
        config.SnmpRetries = Math.Max(0, config.SnmpRetries);
        config.IntervalSeconds = Math.Max(30, config.IntervalSeconds);
        return config;
    }

    private async Task TryReportStatusAsync(AgentConfig config, string status, string? statusReason)
    {
        try
        {
            using var timeoutCts = new CancellationTokenSource(TimeSpan.FromSeconds(12));
            await _uploader.ReportStatusAsync(config, status, statusReason, Log, timeoutCts.Token);
        }
        catch (Exception ex)
        {
            Log?.Invoke($"Agent durum bildirimi basarisiz ({status}): {ex.Message}");
        }
    }
}
