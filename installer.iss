; ============================================================================
; Sample Mapping Editor - Inno Setup Installer Script
; ============================================================================
; This creates a professional Windows installer with:
; - Start Menu shortcuts
; - Desktop shortcut (optional)
; - Uninstaller
; - File associations (optional)
; - Modern UI
; ============================================================================

#define MyAppName "Sample Mapping Editor"
#define MyAppVersion "2.0"
#define MyAppPublisher "Your Name"
#define MyAppURL "https://github.com/alchy/sample-editor"
#define MyAppExeName "SampleMappingEditor.exe"

[Setup]
; App information
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; Installation directories
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

; Output
OutputDir=installers
OutputBaseFilename=SampleMappingEditor-Setup-v{#MyAppVersion}
Compression=lzma2/max
SolidCompression=yes

; Modern UI
WizardStyle=modern
SetupIconFile=resources\app_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

; Privileges
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Architecture
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Main executable
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

; Documentation
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion isreadme

; License (if exists)
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion; AfterInstall: AfterMyProgInstall('Do something')

[Icons]
; Start Menu
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"

; Desktop
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Option to launch after installation
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up user data on uninstall (optional - commented out by default)
; Type: filesandordirs; Name: "{userappdata}\SampleMappingEditor"

[Code]
procedure AfterMyProgInstall(S: String);
begin
  // Custom post-installation code can go here
end;

function InitializeSetup(): Boolean;
begin
  Result := True;
end;
