using System.Windows.Forms;

namespace Proservis.Agent.Desktop;

internal static class Program
{
    [STAThread]
    private static void Main()
    {
        ApplicationConfiguration.Initialize();
        var startHidden = Environment.GetCommandLineArgs()
            .Any(arg => string.Equals(arg, "--minimized", StringComparison.OrdinalIgnoreCase));
        Application.Run(new MainForm(startHidden));
    }
}
