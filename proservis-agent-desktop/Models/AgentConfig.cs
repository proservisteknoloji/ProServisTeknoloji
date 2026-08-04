namespace Proservis.Agent.Desktop.Models;

public sealed class AgentConfig
{
    public string PairingCode { get; set; } = "";
    public string TenantId { get; set; } = "";
    public string TenantName { get; set; } = "";
    public string CustomerId { get; set; } = "";
    public string CustomerName { get; set; } = "";
    public string AgentId { get; set; } = "";
    public string AgentName { get; set; } = "";
    public string ApiKey { get; set; } = "";
    public string ServerUrl { get; set; } = "https://proservislive.web.app";
    public int IntervalSeconds { get; set; } = 300;
    public string SnmpCommunity { get; set; } = "public";
    public int SnmpPort { get; set; } = 161;
    public int SnmpTimeoutMs { get; set; } = 1500;
    public int SnmpRetries { get; set; } = 1;
    public int MaxParallel { get; set; } = 8;
    public int MaxTargetsPerCycle { get; set; } = 1024;
    public List<string> DiscoveryRanges { get; set; } = [];
    public List<string> StaticIps { get; set; } = [];
    public List<string> SelectedBrands { get; set; } = ["Kyocera", "Konica Minolta", "Canon", "Samsung", "Lexmark", "Diger"];
    public bool StartWithWindows { get; set; }
    public bool VerifyTls { get; set; } = true;
    public string Version { get; set; } = "1.0.0";
}
