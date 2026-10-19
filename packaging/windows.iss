#define AppVersion GetEnv('JARVIS_VERSION')
[Setup]
AppId=JarvisCommunityPreview
AppName=JARVIS Community Preview
AppVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\JARVIS Community
DefaultGroupName=JARVIS Community
PrivilegesRequired=lowest
OutputDir=..\release
OutputBaseFilename=JARVIS-{#AppVersion}-windows-x64-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\JARVIS.exe
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
[Files]
Source: "..\dist\JARVIS\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Tasks]
Name: desktopicon; Description: "Create a desktop shortcut"; Flags: unchecked
[Icons]
Name: "{group}\JARVIS Community"; Filename: "{app}\JARVIS.exe"
Name: "{autodesktop}\JARVIS Community"; Filename: "{app}\JARVIS.exe"; Tasks: desktopicon
[Run]
Filename: "{app}\JARVIS.exe"; Description: "Launch JARVIS"; Flags: nowait postinstall skipifsilent
