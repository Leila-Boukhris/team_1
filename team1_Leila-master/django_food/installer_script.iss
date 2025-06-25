#define MyAppName "FoodFlex"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "FoodFlex Team"
#define MyAppURL "https://www.foodflex.com/"
#define MyAppExeName "FoodFlex.exe"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Do not use the same AppId value in installers for other applications.
AppId={{F7A2C309-0EBE-4E37-A586-D775282BF9BC}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=installer
OutputBaseFilename={#MyAppName}_Setup_{#MyAppVersion}
SetupIconFile=foodproject\static\foodapp\img\favicon.ico
Compression=lzma
SolidCompression=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
; Ajout d'informations supplémentaires
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=FoodFlex - Application de Cuisine Marocaine
VersionInfoCopyright=© 2023 FoodFlex. Tous droits réservés.
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
; Options d'installation
WizardStyle=modern
WizardSizePercent=120
WizardImageFile=foodproject\static\foodapp\img\wizard_image.bmp
WizardSmallImageFile=foodproject\static\foodapp\img\wizard_small_image.bmp
; Paramètres de compatibilité
MinVersion=10.0.17763
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 0,6.1
Name: "startmenuicon"; Description: "Créer un raccourci dans le menu Démarrer"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checked
Name: "autostart"; Description: "Lancer FoodFlex au démarrage de Windows"; Flags: unchecked

[Files]
Source: "dist\FoodFlex.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\README.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\Lancer_FoodFlex.bat"; DestDir: "{app}"; Flags: ignoreversion
; Création d'un dossier logs vide
Source: "logs\*"; DestDir: "{app}\logs"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Lire le README"; Filename: "{app}\README.txt"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: autostart

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
// Vérification de la configuration système minimale
function InitializeSetup(): Boolean;
var
  MemTotal: Int64;
  DiskFree: Int64;
  OSVersion: TWindowsVersion;
begin
  // Vérification de la mémoire RAM (minimum 4 Go)
  if not GetPhysicalMemoryInMB(MemTotal) then begin
    MsgBox('Impossible de déterminer la quantité de RAM. Installation continue...', mbInformation, MB_OK);
  end else if MemTotal < 4096 then begin
    if MsgBox('Votre système dispose de moins de 4 Go de RAM. FoodFlex pourrait ne pas fonctionner correctement. Voulez-vous continuer quand même?', mbConfirmation, MB_YESNO) = IDNO then
      Result := False
    else
      Result := True;
  end;
  
  // Vérifier l'espace disque disponible (minimum 500 Mo)
  DiskFree := GetSpaceOnDisk(ExpandConstant('{autopf}'), True);
  if DiskFree < 500 * 1024 * 1024 then begin
    if MsgBox('Espace disque insuffisant. Au moins 500 Mo sont nécessaires. Voulez-vous continuer quand même?', mbError, MB_YESNO) = IDNO then
      Result := False
    else
      Result := True;
  end;

  // Vérification de la version de Windows (minimum Windows 10)
  GetWindowsVersionEx(OSVersion);
  if (OSVersion.Major < 10) then begin
    MsgBox('FoodFlex nécessite Windows 10 ou supérieur. Impossible de continuer.', mbError, MB_OK);
    Result := False;
  end else
    Result := True;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  mRes: Integer;
begin
  case CurUninstallStep of
    usUninstall:
      begin
        mRes := MsgBox('Voulez-vous supprimer tous les fichiers de logs et de données? ' +
                      'Si vous choisissez Non, les données seront conservées.', mbConfirmation, MB_YESNO or MB_DEFBUTTON2)
        if mRes = IDYES then
          DelTree(ExpandConstant('{app}\logs'), True, True, True);
      end;
  end;
end; 