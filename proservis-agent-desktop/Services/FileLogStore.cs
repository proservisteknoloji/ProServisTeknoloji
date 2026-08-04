namespace Proservis.Agent.Desktop.Services;

public static class FileLogStore
{
    private static readonly Lock SyncRoot = new();

    public static string GetLogPath()
    {
        var logDir = Path.Combine(AppContext.BaseDirectory, "logs");
        Directory.CreateDirectory(logDir);
        return Path.Combine(logDir, "ProservisAgent.log");
    }

    public static void Append(string text)
    {
        lock (SyncRoot)
        {
            File.AppendAllText(GetLogPath(), text + Environment.NewLine);
        }
    }
}
