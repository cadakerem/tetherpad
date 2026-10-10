; Script generated for TetherPad Installer
#define MyAppName "TetherPad"
#ifndef MyAppVersion
  #define MyAppVersion "1.1.0"
#endif
#define MyAppPublisher "Kerem Barbaros Karnabat"
#define MyAppURL "https://github.com/cadakerem/tetherpad"
#define MyAppExeName "TetherPad.exe"

[Setup]
; Unique application GUID
AppId={{5E2DFE43-E6AA-4A59-8A19-1B8604314E29}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=LICENSE
OutputDir=Output
OutputBaseFilename=TetherPad_Setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startwithwindows"; Description: "Start TetherPad automatically when Windows starts"; GroupDescription: "Startup Options:"; Flags: unchecked

[Files]
Source: "{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "ScreenGuard.apk"; DestDir: "{app}"; Flags: ignoreversion
Source: "platform-tools\*"; DestDir: "{app}\platform-tools"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startwithwindows

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
