namespace Proservis.Agent.Desktop.Models;

public sealed class DeviceTelemetryRow
{
    public string SerialNumber { get; set; } = "";
    public string? Brand { get; set; }
    public string? Model { get; set; }
    public string? IpAddress { get; set; }
    public string? Hostname { get; set; }
    public string? MacAddress { get; set; }
    public long? BwCounter { get; set; }
    public long? ColorCounter { get; set; }
    public long? TotalCounter { get; set; }
    public int? TonerBlack { get; set; }
    public int? TonerCyan { get; set; }
    public int? TonerMagenta { get; set; }
    public int? TonerYellow { get; set; }
    public bool? Online { get; set; }
    public string? WarningCode { get; set; }
    public string? WarningText { get; set; }
    public string Protocol { get; set; } = "snmp";
}

public sealed class AgentTelemetryUploadRequest
{
    public string TenantId { get; set; } = "";
    public string AgentId { get; set; } = "";
    public string ApiKey { get; set; } = "";
    public string CollectedAt { get; set; } = "";
    public string Version { get; set; } = "1.0.0";
    public List<DeviceTelemetryRow> Devices { get; set; } = [];
}
