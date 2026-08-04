using System.Text.Json;
using Proservis.Agent.Desktop.Models;

namespace Proservis.Agent.Desktop.Services;

public static class ConfigStore
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        WriteIndented = true,
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        PropertyNameCaseInsensitive = true,
    };

    public static string GetConfigDirectory()
    {
        var baseDir = AppContext.BaseDirectory;
        var dir = Path.Combine(baseDir, "data");
        Directory.CreateDirectory(dir);
        return dir;
    }

    public static string GetConfigPath() => Path.Combine(GetConfigDirectory(), "config.json");

    public static AgentConfig Load()
    {
        var path = GetConfigPath();
        if (!File.Exists(path)) return new AgentConfig();
        var json = File.ReadAllText(path);
        return JsonSerializer.Deserialize<AgentConfig>(json, JsonOptions) ?? new AgentConfig();
    }

    public static void Save(AgentConfig config)
    {
        var json = JsonSerializer.Serialize(config, JsonOptions);
        File.WriteAllText(GetConfigPath(), json);
    }
}
