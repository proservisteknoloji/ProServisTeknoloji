using System.Net.Http.Json;
using System.Text.Json;
using System.Diagnostics;
using Microsoft.Win32;
using Proservis.Agent.Desktop.Models;
using Proservis.Agent.Desktop.Services;

namespace Proservis.Agent.Desktop;

public sealed class MainForm : Form
{
    private const int MaxLogLines = 10;
    private const int TrimLogLinesTo = 10;

    private sealed class PairResponse
    {
        public bool Ok { get; set; }
        public string TenantId { get; set; } = "";
        public string CustomerId { get; set; } = "";
        public string CustomerName { get; set; } = "";
        public string AgentId { get; set; } = "";
        public string ApiKey { get; set; } = "";
    }

    private readonly AgentRunner _runner = new();
    private readonly NotifyIcon _trayIcon = new();
    private bool _allowClose;

    private readonly TextBox _pairingCode = new();
    private readonly TextBox _ranges = new();
    private readonly CheckBox _brandKyocera = new();
    private readonly CheckBox _brandKonica = new();
    private readonly CheckBox _brandCanon = new();
    private readonly CheckBox _brandSamsung = new();
    private readonly CheckBox _brandLexmark = new();
    private readonly CheckBox _brandOther = new();
    private readonly CheckBox _startWithWindows = new();
    private readonly Button _startButton = new();
    private readonly Button _stopButton = new();
    private readonly Button _runNowButton = new();
    private readonly Button _copyErrorButton = new();
    private readonly Button _uninstallButton = new();
    private readonly Label _status = new();
    private readonly TextBox _logs = new();
    private string _lastErrorDetail = "";
    private readonly bool _startHidden;

    public MainForm(bool startHidden = false)
    {
        _startHidden = startHidden;
        Text = "Proservis Agent";
        Width = 880;
        Height = 720;
        MinimumSize = new Size(760, 620);
        StartPosition = FormStartPosition.CenterScreen;

        BuildUi();
        BindEvents();
        LoadConfigToUi();
        ApplyStartupRegistration(ConfigStore.Load().StartWithWindows);

        if (Icon is not null)
        {
            _trayIcon.Icon = Icon;
        }
        else
        {
            _trayIcon.Icon = SystemIcons.Application;
        }
        _trayIcon.Text = "Proservis Agent";
        _trayIcon.Visible = true;
        _trayIcon.ContextMenuStrip = BuildTrayMenu();
        _trayIcon.DoubleClick += (_, _) =>
        {
            Show();
            WindowState = FormWindowState.Normal;
            BringToFront();
        };

        Shown += (_, _) =>
        {
            if (_startHidden)
            {
                Hide();
                WindowState = FormWindowState.Minimized;
            }

            _ = TryAutoStartAsync();
        };
    }

    private void BuildUi()
    {
        var root = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            ColumnCount = 1,
            RowCount = 3,
            Padding = new Padding(12),
        };
        root.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100f));
        root.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        root.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        root.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        Controls.Add(root);

        var inputPanel = new TableLayoutPanel
        {
            Dock = DockStyle.Top,
            ColumnCount = 1,
            AutoSize = true,
            AutoSizeMode = AutoSizeMode.GrowAndShrink,
            Margin = new Padding(0),
        };
        inputPanel.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100f));
        root.Controls.Add(inputPanel);

        var pairingLabel = new Label { Text = "Eslestirme Kodu", AutoSize = true, Margin = new Padding(3, 8, 3, 3) };
        _pairingCode.Dock = DockStyle.Top;
        _pairingCode.PlaceholderText = "Ornek: ABCDEF1234-9876";
        inputPanel.Controls.Add(pairingLabel);
        inputPanel.Controls.Add(_pairingCode);

        var rangeLabel = new Label
        {
            Text = "Ag Araliklari (her agi ayri satira yazin, Enter ile alt satira gecin)",
            AutoSize = true,
            Margin = new Padding(3, 8, 3, 3),
        };
        _ranges.Multiline = true;
        _ranges.AcceptsReturn = true;
        _ranges.AcceptsTab = false;
        _ranges.Height = 150;
        _ranges.Dock = DockStyle.Top;
        _ranges.ScrollBars = ScrollBars.Vertical;
        _ranges.PlaceholderText = "Ornek:\r\n192.168.1\r\n192.168.2\r\n10.10.5.0/24";
        inputPanel.Controls.Add(rangeLabel);
        inputPanel.Controls.Add(_ranges);

        var brandLabel = new Label
        {
            Text = "Tarama Markalari",
            AutoSize = true,
            Margin = new Padding(3, 8, 3, 3),
        };
        inputPanel.Controls.Add(brandLabel);

        var brandPanel = new FlowLayoutPanel
        {
            Dock = DockStyle.Top,
            AutoSize = true,
            WrapContents = true,
        };
        _brandKyocera.Text = "Kyocera";
        _brandKonica.Text = "Konica Minolta";
        _brandCanon.Text = "Canon";
        _brandSamsung.Text = "Samsung";
        _brandLexmark.Text = "Lexmark";
        _brandOther.Text = "Diger";
        _brandKyocera.Checked = true;
        _brandKonica.Checked = true;
        _brandCanon.Checked = true;
        _brandSamsung.Checked = true;
        _brandLexmark.Checked = true;
        _brandOther.Checked = true;
        brandPanel.Controls.AddRange([_brandKyocera, _brandKonica, _brandCanon, _brandSamsung, _brandLexmark, _brandOther]);
        inputPanel.Controls.Add(brandPanel);

        _startWithWindows.Text = "Bilgisayar acildiginda otomatik baslat";
        _startWithWindows.AutoSize = true;
        _startWithWindows.Margin = new Padding(3, 10, 3, 3);
        inputPanel.Controls.Add(_startWithWindows);

        var buttonBar = new FlowLayoutPanel
        {
            Dock = DockStyle.Top,
            AutoSize = true,
            Padding = new Padding(0, 8, 0, 8),
        };
        _startButton.Text = "Baslat";
        _stopButton.Text = "Durdur";
        _runNowButton.Text = "Simdi Tara / Gonder";
        _copyErrorButton.Text = "Hatayi Kopyala";
        _uninstallButton.Text = "Kaldir";
        _status.Text = "Durum: Hazir";
        _status.AutoSize = true;
        _status.Margin = new Padding(16, 8, 0, 0);
        buttonBar.Controls.AddRange([_startButton, _stopButton, _runNowButton, _copyErrorButton, _uninstallButton, _status]);
        root.Controls.Add(buttonBar);

        var logGroup = new GroupBox
        {
            Dock = DockStyle.Fill,
            Text = "Log",
            MinimumSize = new Size(0, 220),
            Padding = new Padding(8),
        };
        _logs.Multiline = true;
        _logs.ReadOnly = true;
        _logs.ScrollBars = ScrollBars.Both;
        _logs.WordWrap = false;
        _logs.Dock = DockStyle.Fill;
        _logs.BackColor = Color.White;
        logGroup.Controls.Add(_logs);
        root.Controls.Add(logGroup);
    }

    private ContextMenuStrip BuildTrayMenu()
    {
        var menu = new ContextMenuStrip();
        menu.Items.Add("Ac", null, (_, _) =>
        {
            Show();
            WindowState = FormWindowState.Normal;
            BringToFront();
        });
        menu.Items.Add("Cikis", null, async (_, _) =>
        {
            _allowClose = true;
            _trayIcon.Visible = false;
            await _runner.StopAsync();
            Close();
        });
        return menu;
    }

    private void ApplyStartupRegistration(bool enabled)
    {
        try
        {
            using var runKey = Registry.CurrentUser.OpenSubKey(
                @"Software\Microsoft\Windows\CurrentVersion\Run",
                writable: true);
            if (runKey is null) return;

            const string startupValueName = "ProservisAgentStartup";
            if (!enabled)
            {
                if (runKey.GetValue(startupValueName) is not null)
                {
                    runKey.DeleteValue(startupValueName, throwOnMissingValue: false);
                }
                return;
            }

            var exePath = Application.ExecutablePath;
            var command = $"\"{exePath}\" --minimized";
            var current = Convert.ToString(runKey.GetValue(startupValueName)) ?? string.Empty;
            if (!string.Equals(current, command, StringComparison.Ordinal))
            {
                runKey.SetValue(startupValueName, command);
            }
        }
        catch (Exception ex)
        {
            Log("Baslangic kaydi yazilamadi: " + ex.Message);
        }
    }

    private void BindEvents()
    {
        _runner.Log += Log;
        _runner.RunningChanged += running =>
        {
            if (InvokeRequired)
            {
                BeginInvoke(() => _status.Text = $"Durum: {(running ? "Calisiyor" : "Durdu")}");
                return;
            }
            _status.Text = $"Durum: {(running ? "Calisiyor" : "Durdu")}";
        };

        _startButton.Click += async (_, _) =>
        {
            try
            {
                var cfg = ReadConfigFromUi();
                var paired = await EnsurePairingAsync(cfg);
                _runner.Start(paired);
                SaveConfig(paired);
            }
            catch (Exception ex)
            {
                ReportError("Baslatma hatasi", ex);
            }
        };

        _runNowButton.Click += async (_, _) =>
        {
            try
            {
                var cfg = ReadConfigFromUi();
                var paired = await EnsurePairingAsync(cfg);
                SaveConfig(paired);
                await _runner.RunOnceAsync(paired);
            }
            catch (Exception ex)
            {
                ReportError("Tek sefer hatasi", ex);
            }
        };

        _copyErrorButton.Click += (_, _) =>
        {
            if (string.IsNullOrWhiteSpace(_lastErrorDetail))
            {
                MessageBox.Show("Kopyalanacak hata bulunamadi.", "Bilgi", MessageBoxButtons.OK, MessageBoxIcon.Information);
                return;
            }

            try
            {
                Clipboard.SetText(_lastErrorDetail);
                MessageBox.Show("Hata detayi panoya kopyalandi.", "Bilgi", MessageBoxButtons.OK, MessageBoxIcon.Information);
            }
            catch (Exception ex)
            {
                Log("Panoya kopyalama hatasi: " + ex.Message);
            }
        };

        _uninstallButton.Click += async (_, _) => await UninstallAsync();

        _stopButton.Click += async (_, _) => await _runner.StopAsync();

        _startWithWindows.CheckedChanged += (_, _) =>
        {
            try
            {
                var cfg = ReadConfigFromUi();
                SaveConfig(cfg);
                ApplyStartupRegistration(cfg.StartWithWindows);
            }
            catch (Exception ex)
            {
                ReportError("Baslangic ayari kaydedilemedi", ex);
            }
        };

        Resize += (_, _) =>
        {
            if (WindowState == FormWindowState.Minimized)
            {
                Hide();
                _trayIcon.ShowBalloonTip(1200, "Proservis Agent", "Agent arka planda calisiyor.", ToolTipIcon.Info);
            }
        };

        FormClosing += (_, e) =>
        {
            if (_allowClose) return;
            e.Cancel = true;
            Hide();
            _trayIcon.ShowBalloonTip(1200, "Proservis Agent", "Agent arka planda calisiyor.", ToolTipIcon.Info);
        };
    }

    private async Task UninstallAsync()
    {
        var confirm = MessageBox.Show(
            "Agent kaldirilsin mi? Baslangic kaydi ve ayarlar silinecek, uygulama kapanacak.",
            "Proservis Agent",
            MessageBoxButtons.YesNo,
            MessageBoxIcon.Warning);
        if (confirm != DialogResult.Yes) return;

        try
        {
            await _runner.StopAsync();
            ApplyStartupRegistration(false);

            var configPath = ConfigStore.GetConfigPath();
            if (File.Exists(configPath))
            {
                File.Delete(configPath);
            }

            var exePath = Application.ExecutablePath;
            var exeDir = Path.GetDirectoryName(exePath) ?? string.Empty;
            var cmdArgs =
                $"/c ping 127.0.0.1 -n 3 > nul && del /f /q \"{exePath}\"" +
                (string.IsNullOrWhiteSpace(exeDir) ? string.Empty : $" && rmdir \"{exeDir}\" 2>nul");

            Process.Start(new ProcessStartInfo
            {
                FileName = "cmd.exe",
                Arguments = cmdArgs,
                CreateNoWindow = true,
                UseShellExecute = false,
                WindowStyle = ProcessWindowStyle.Hidden,
            });

            _allowClose = true;
            _trayIcon.Visible = false;
            Close();
        }
        catch (Exception ex)
        {
            ReportError("Kaldirma hatasi", ex);
        }
    }

    private AgentConfig ReadConfigFromUi()
    {
        var current = ConfigStore.Load();
        var pairingCodeInput = _pairingCode.Text.Trim();
        return new AgentConfig
        {
            PairingCode = string.IsNullOrWhiteSpace(pairingCodeInput) ? current.PairingCode : pairingCodeInput,
            TenantId = current.TenantId,
            TenantName = current.TenantName,
            CustomerId = current.CustomerId,
            CustomerName = current.CustomerName,
            AgentId = current.AgentId,
            AgentName = current.AgentName,
            ApiKey = current.ApiKey,
            ServerUrl = string.IsNullOrWhiteSpace(current.ServerUrl) ? "https://proservislive.web.app" : current.ServerUrl,
            IntervalSeconds = current.IntervalSeconds > 0 ? current.IntervalSeconds : 86400,
            SnmpCommunity = string.IsNullOrWhiteSpace(current.SnmpCommunity) ? "public" : current.SnmpCommunity,
            SnmpPort = current.SnmpPort > 0 ? current.SnmpPort : 161,
            SnmpTimeoutMs = current.SnmpTimeoutMs > 0 ? current.SnmpTimeoutMs : 1500,
            SnmpRetries = current.SnmpRetries >= 0 ? current.SnmpRetries : 1,
            MaxParallel = current.MaxParallel > 0 ? Math.Min(current.MaxParallel, 8) : 8,
            MaxTargetsPerCycle = current.MaxTargetsPerCycle > 0 ? Math.Min(Math.Max(current.MaxTargetsPerCycle, 64), 4096) : 1024,
            VerifyTls = current.VerifyTls,
            Version = string.IsNullOrWhiteSpace(current.Version) ? "1.0.0" : current.Version,
            DiscoveryRanges = SplitLines(_ranges.Text),
            StaticIps = current.StaticIps ?? [],
            SelectedBrands = ReadSelectedBrands(),
            StartWithWindows = _startWithWindows.Checked,
        };
    }

    private static void SaveConfig(AgentConfig cfg)
    {
        ConfigStore.Save(cfg);
    }

    private void LoadConfigToUi()
    {
        var cfg = ConfigStore.Load();
        _pairingCode.Text = cfg.PairingCode;
        _ranges.Text = string.Join(Environment.NewLine, cfg.DiscoveryRanges ?? []);
        var selected = new HashSet<string>(cfg.SelectedBrands ?? [], StringComparer.OrdinalIgnoreCase);
        _brandKyocera.Checked = selected.Count == 0 || selected.Contains("Kyocera");
        _brandKonica.Checked = selected.Count == 0 || selected.Contains("Konica Minolta");
        _brandCanon.Checked = selected.Count == 0 || selected.Contains("Canon");
        _brandSamsung.Checked = selected.Count == 0 || selected.Contains("Samsung");
        _brandLexmark.Checked = selected.Count == 0 || selected.Contains("Lexmark");
        _brandOther.Checked = selected.Count == 0 || selected.Contains("Diger");
        _startWithWindows.Checked = cfg.StartWithWindows;
    }

    private async Task TryAutoStartAsync()
    {
        var cfg = ConfigStore.Load();
        if (!_startHidden || !cfg.StartWithWindows || _runner.IsRunning)
        {
            return;
        }

        try
        {
            var paired = await EnsurePairingAsync(cfg);
            SaveConfig(paired);
            _runner.Start(paired);
        }
        catch (Exception ex)
        {
            ReportError("Otomatik baslatma hatasi", ex);
        }
    }

    private async Task<AgentConfig> EnsurePairingAsync(AgentConfig cfg)
    {
        var current = ConfigStore.Load();
        var hasStoredIdentity =
            !string.IsNullOrWhiteSpace(current.AgentId)
            && !string.IsNullOrWhiteSpace(current.ApiKey)
            && !string.IsNullOrWhiteSpace(current.TenantId);

        if (cfg.DiscoveryRanges.Count == 0 && current.DiscoveryRanges.Count > 0)
        {
            cfg.DiscoveryRanges = current.DiscoveryRanges;
        }
        if (cfg.DiscoveryRanges.Count == 0)
        {
            throw new InvalidOperationException("En az bir ag araligi girilmelidir.");
        }

        if (hasStoredIdentity
            && (string.IsNullOrWhiteSpace(cfg.PairingCode)
                || string.Equals(current.PairingCode, cfg.PairingCode, StringComparison.OrdinalIgnoreCase)))
        {
            cfg.TenantId = current.TenantId;
            cfg.TenantName = current.TenantName;
            cfg.CustomerId = current.CustomerId;
            cfg.CustomerName = current.CustomerName;
            cfg.AgentId = current.AgentId;
            cfg.ApiKey = current.ApiKey;
            cfg.AgentName = current.AgentName;
            cfg.PairingCode = current.PairingCode;
            Log("Kayitli agent kimligi kullanildi.");
            return cfg;
        }

        if (string.IsNullOrWhiteSpace(cfg.PairingCode))
        {
            throw new InvalidOperationException("Eslestirme kodu girilmelidir.");
        }

        using var client = new HttpClient { Timeout = TimeSpan.FromSeconds(20) };
        var endpoint = $"{cfg.ServerUrl.TrimEnd('/')}/api/agent/pair";
        Log("Eslestirme endpoint: " + endpoint);
        var response = await client.PostAsJsonAsync(
            endpoint,
            new
            {
                pairingCode = cfg.PairingCode,
                machineName = Environment.MachineName,
                siteName = Environment.UserDomainName,
                version = cfg.Version,
                collectIntervalMinutes = Math.Max(1, cfg.IntervalSeconds / 60),
                networkRanges = cfg.DiscoveryRanges,
            });

        var body = await response.Content.ReadAsStringAsync();
        if (!response.IsSuccessStatusCode)
        {
            throw new InvalidOperationException($"Agent eslestirme basarisiz: {body}");
        }

        var parsed = JsonSerializer.Deserialize<PairResponse>(body, new JsonSerializerOptions
        {
            PropertyNameCaseInsensitive = true,
        });
        if (parsed is null
            || string.IsNullOrWhiteSpace(parsed.AgentId)
            || string.IsNullOrWhiteSpace(parsed.ApiKey)
            || string.IsNullOrWhiteSpace(parsed.TenantId))
        {
            throw new InvalidOperationException("Agent eslestirme donen veri gecersiz.");
        }

        cfg.TenantId = parsed.TenantId;
        cfg.TenantName = parsed.TenantId;
        cfg.CustomerId = parsed.CustomerId;
        cfg.CustomerName = parsed.CustomerName;
        cfg.AgentId = parsed.AgentId;
        cfg.ApiKey = parsed.ApiKey;
        cfg.AgentName = $"{Environment.MachineName}-agent";
        Log("Agent kod ile eslestirildi.");
        return cfg;
    }

    private void Log(string line)
    {
        var text = $"[{DateTime.Now:HH:mm:ss}] {line}";
        FileLogStore.Append(text);
        if (InvokeRequired)
        {
            BeginInvoke(() => AppendLog(text));
            return;
        }
        AppendLog(text);
    }

    private void ReportError(string context, Exception ex)
    {
        _lastErrorDetail = $"{context}{Environment.NewLine}{ex}";
        Log($"{context}: {ex.Message}");
    }

    private void AppendLog(string text)
    {
        TrimLogsIfNeeded();
        _logs.AppendText(text + Environment.NewLine);
        _logs.SelectionStart = _logs.TextLength;
        _logs.ScrollToCaret();
    }

    private void TrimLogsIfNeeded()
    {
        var lineCount = _logs.Lines.Length;
        if (lineCount < MaxLogLines) return;

        var trimmed = _logs.Lines
            .Skip(Math.Max(0, lineCount - TrimLogLinesTo))
            .ToArray();

        _logs.Lines = trimmed;
        _logs.SelectionStart = _logs.TextLength;
    }

    private static List<string> SplitLines(string raw)
    {
        return raw
            .Split(new[] { "\r\n", "\n", ";" }, StringSplitOptions.RemoveEmptyEntries)
            .Select(x => x.Trim())
            .Where(x => !string.IsNullOrWhiteSpace(x))
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .ToList();
    }

    private List<string> ReadSelectedBrands()
    {
        var brands = new List<string>();
        if (_brandKyocera.Checked) brands.Add("Kyocera");
        if (_brandKonica.Checked) brands.Add("Konica Minolta");
        if (_brandCanon.Checked) brands.Add("Canon");
        if (_brandSamsung.Checked) brands.Add("Samsung");
        if (_brandLexmark.Checked) brands.Add("Lexmark");
        if (_brandOther.Checked) brands.Add("Diger");
        return brands;
    }
}
