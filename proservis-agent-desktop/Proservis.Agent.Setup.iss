#define MyAppName "Proservis Agent"
#ifndef MyAppVersion
  #define MyAppVersion "1.1.0"
#endif
#define MyAppPublisher "Proservis"
#define MyAppExeName "Proservis.Agent.Desktop.exe"

[Setup]
AppId={{8E6F887F-2F01-44BE-BE4D-55A8B78620FB}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
AllowNoIcons=yes
OutputDir=..\installer_output
OutputBaseFilename=ProservisAgent_v{#MyAppVersion}_Setup
SetupIconFile=..\ProServis.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"

[Tasks]
Name: "desktopicon"; Description: "Masaustune kisayol olustur"; Flags: unchecked

[Dirs]
Name: "{app}\data"; Permissions: users-full
Name: "{app}\logs"; Permissions: users-full

[Files]
Source: "..\publish\agent-desktop-win-x64\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Proservis Agent'i baslat"; Flags: nowait postinstall skipifsilent

[Code]
var
  PairingPage: TInputQueryWizardPage;
  NetworkPage: TWizardPage;
  BrandPage: TWizardPage;
  NetworkMemo: TMemo;
  BrandKyocera: TNewCheckBox;
  BrandKonica: TNewCheckBox;
  BrandCanon: TNewCheckBox;
  BrandSamsung: TNewCheckBox;
  BrandLexmark: TNewCheckBox;
  BrandOther: TNewCheckBox;
  StartWithWindowsCheck: TNewCheckBox;

function JsonEscape(const Value: string): string;
begin
  Result := Value;
  StringChange(Result, '\', '\\');
  StringChange(Result, '"', '\"');
  StringChange(Result, #13, '');
  StringChange(Result, #10, '\n');
end;

function BuildRangesJson: string;
var
  Items: TStringList;
  i: Integer;
  Line: string;
begin
  Items := TStringList.Create;
  try
    Line := NetworkMemo.Text;
    StringChange(Line, ';', #13#10);
    Items.Text := Line;
    Result := '[';
    for i := 0 to Items.Count - 1 do
    begin
      Line := Trim(Items[i]);
      if Line <> '' then
      begin
        if Result <> '[' then
          Result := Result + ',';

        Result := Result + '"' + JsonEscape(Line) + '"';
      end;
    end;

    Result := Result + ']';
  finally
    Items.Free;
  end;
end;

function BuildBrandsJson: string;
begin
  Result := '[';

  if BrandKyocera.Checked then
  begin
    if Result <> '[' then Result := Result + ',';
    Result := Result + '"Kyocera"';
  end;

  if BrandKonica.Checked then
  begin
    if Result <> '[' then Result := Result + ',';
    Result := Result + '"Konica Minolta"';
  end;

  if BrandCanon.Checked then
  begin
    if Result <> '[' then Result := Result + ',';
    Result := Result + '"Canon"';
  end;

  if BrandSamsung.Checked then
  begin
    if Result <> '[' then Result := Result + ',';
    Result := Result + '"Samsung"';
  end;

  if BrandLexmark.Checked then
  begin
    if Result <> '[' then Result := Result + ',';
    Result := Result + '"Lexmark"';
  end;

  if BrandOther.Checked then
  begin
    if Result <> '[' then Result := Result + ',';
    Result := Result + '"Diger"';
  end;

  Result := Result + ']';
end;

function BoolLiteral(Value: Boolean): string;
begin
  if Value then
    Result := 'true'
  else
    Result := 'false';
end;

procedure SaveInitialConfig;
var
  ConfigPath: string;
  PairingCode: string;
  Json: string;
begin
  PairingCode := Trim(PairingPage.Values[0]);
  ConfigPath := ExpandConstant('{app}\data\config.json');

  Json := '{' + #13#10 +
    '  "pairingCode": "' + JsonEscape(PairingCode) + '",' + #13#10 +
    '  "tenantId": "",' + #13#10 +
    '  "tenantName": "",' + #13#10 +
    '  "customerId": "",' + #13#10 +
    '  "customerName": "",' + #13#10 +
    '  "agentId": "",' + #13#10 +
    '  "agentName": "",' + #13#10 +
    '  "apiKey": "",' + #13#10 +
    '  "serverUrl": "https://proservislive.web.app",' + #13#10 +
    '  "intervalSeconds": 300,' + #13#10 +
    '  "snmpCommunity": "public",' + #13#10 +
    '  "snmpPort": 161,' + #13#10 +
    '  "snmpTimeoutMs": 1200,' + #13#10 +
    '  "snmpRetries": 0,' + #13#10 +
    '  "maxParallel": 4,' + #13#10 +
    '  "maxTargetsPerCycle": 1024,' + #13#10 +
    '  "discoveryRanges": ' + BuildRangesJson + ',' + #13#10 +
    '  "staticIps": [],' + #13#10 +
    '  "selectedBrands": ' + BuildBrandsJson + ',' + #13#10 +
    '  "startWithWindows": ' + BoolLiteral(StartWithWindowsCheck.Checked) + ',' + #13#10 +
    '  "verifyTls": true,' + #13#10 +
    '  "version": "{#MyAppVersion}"' + #13#10 +
    '}';

  SaveStringToFile(ConfigPath, Json, False);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;

  if CurPageID = NetworkPage.ID then
  begin
    if Trim(NetworkMemo.Text) = '' then
    begin
      MsgBox('En az bir ag araligi girmeniz gerekir.', mbError, MB_OK);
      Result := False;
    end;
  end;
end;

procedure InitializeWizard;
begin
  PairingPage := CreateInputQueryPage(
    wpSelectDir,
    'Agent Eslestirme',
    'Agent ilk konfigurasyonu',
    'Web panelinden aldiginiz eslestirme kodunu girebilirsiniz. Bos birakirsaniz sonradan agent ekranindan girilebilir.');
  PairingPage.Add('Eslestirme Kodu:', False);

  NetworkPage := CreateCustomPage(
    PairingPage.ID,
    'Ag Arama Ayarlari',
    'Tarama yapilacak ag araliklarini girin. Her satira bir aralik yazin.');

  NetworkMemo := TMemo.Create(WizardForm);
  NetworkMemo.Parent := NetworkPage.Surface;
  NetworkMemo.Left := ScaleX(0);
  NetworkMemo.Top := ScaleY(8);
  NetworkMemo.Width := NetworkPage.SurfaceWidth;
  NetworkMemo.Height := ScaleY(170);
  NetworkMemo.ScrollBars := ssVertical;
  NetworkMemo.WordWrap := False;
  NetworkMemo.Text := '192.168.1'#13#10'192.168.2';

  BrandPage := CreateCustomPage(
    NetworkPage.ID,
    'Marka ve Baslangic',
    'Tarama markalarini secin ve acilista otomatik baslatmayi belirleyin.');

  BrandKyocera := TNewCheckBox.Create(WizardForm);
  BrandKyocera.Parent := BrandPage.Surface;
  BrandKyocera.Left := ScaleX(0);
  BrandKyocera.Top := ScaleY(8);
  BrandKyocera.Caption := 'Kyocera';
  BrandKyocera.Checked := True;

  BrandKonica := TNewCheckBox.Create(WizardForm);
  BrandKonica.Parent := BrandPage.Surface;
  BrandKonica.Left := ScaleX(0);
  BrandKonica.Top := BrandKyocera.Top + ScaleY(22);
  BrandKonica.Caption := 'Konica Minolta';
  BrandKonica.Checked := True;

  BrandCanon := TNewCheckBox.Create(WizardForm);
  BrandCanon.Parent := BrandPage.Surface;
  BrandCanon.Left := ScaleX(0);
  BrandCanon.Top := BrandKonica.Top + ScaleY(22);
  BrandCanon.Caption := 'Canon';
  BrandCanon.Checked := True;

  BrandSamsung := TNewCheckBox.Create(WizardForm);
  BrandSamsung.Parent := BrandPage.Surface;
  BrandSamsung.Left := ScaleX(0);
  BrandSamsung.Top := BrandCanon.Top + ScaleY(22);
  BrandSamsung.Caption := 'Samsung';
  BrandSamsung.Checked := True;

  BrandLexmark := TNewCheckBox.Create(WizardForm);
  BrandLexmark.Parent := BrandPage.Surface;
  BrandLexmark.Left := ScaleX(0);
  BrandLexmark.Top := BrandSamsung.Top + ScaleY(22);
  BrandLexmark.Caption := 'Lexmark';
  BrandLexmark.Checked := True;

  BrandOther := TNewCheckBox.Create(WizardForm);
  BrandOther.Parent := BrandPage.Surface;
  BrandOther.Left := ScaleX(0);
  BrandOther.Top := BrandLexmark.Top + ScaleY(22);
  BrandOther.Caption := 'Diger';
  BrandOther.Checked := True;

  StartWithWindowsCheck := TNewCheckBox.Create(WizardForm);
  StartWithWindowsCheck.Parent := BrandPage.Surface;
  StartWithWindowsCheck.Left := ScaleX(0);
  StartWithWindowsCheck.Top := BrandOther.Top + ScaleY(32);
  StartWithWindowsCheck.Caption := 'Bilgisayar yeniden basladiginda agent otomatik baslasin';
  StartWithWindowsCheck.Checked := True;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    SaveInitialConfig;
  end;
end;
