; ProServis Inno Setup Script
; Teknik Servis Yönetim Sistemi

#define MyAppName "ProServis"
#define MyAppVersion "2.3.0"
#define MyAppPublisher "Ümit Sağdıç"
#define MyAppURL "https://github.com/yourusername/proservis"
#define MyAppExeName "ProServis.exe"

[Setup]
; Temel Bilgiler
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=LICENSE
OutputDir=installer_output
OutputBaseFilename=ProServis_v{#MyAppVersion}_Setup
SetupIconFile=ProServis.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64

; Dil
ShowLanguageDialog=no

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
Source: "dist\ProServis\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion isreadme
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
  // Eski sürüm kontrolü yapılabilir
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
  DataDir: String;
begin
  if CurStep = ssPostInstall then
  begin
    // ProgramData klasörünü oluştur
    DataDir := ExpandConstant('C:\ProgramData\ProServis');
    if not DirExists(DataDir) then
      CreateDir(DataDir);
    
    // ProgramData klasörüne yazma izni ver (tüm kullanıcılara)
    Exec('icacls', ExpandConstant('"' + DataDir + '" /grant Users:(OI)(CI)F /T'), '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    
    // AppData\Roaming klasörünü de oluştur
    DataDir := ExpandConstant('{userappdata}\ProServis');
    if not DirExists(DataDir) then
      CreateDir(DataDir);
  end;
end;

[UninstallDelete]
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\temp"
Type: filesandordirs; Name: "{app}\backups"

[Messages]
turkish.WelcomeLabel1=ProServis Kurulum Sihirbazına Hoş Geldiniz
turkish.WelcomeLabel2=Bu sihirbaz [name/ver] uygulamasını bilgisayarınıza kuracaktır.%n%nDevam etmeden önce çalışan tüm uygulamaları kapatmanız önerilir.
turkish.FinishedLabel=ProServis başarıyla kuruldu!%n%nUygulamayı başlatmak için Bitir'e tıklayın.
