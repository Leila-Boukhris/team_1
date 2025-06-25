@echo off
echo Préparation de la création de l'installateur FoodFlex...
echo.

:: Vérification de l'existence de Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Python n'est pas installé ou n'est pas dans le PATH.
    echo Veuillez installer Python depuis https://www.python.org/downloads/
    echo Assurez-vous de cocher "Add Python to PATH" lors de l'installation.
    pause
    exit /b 1
)

:: Construction de l'application avec PyInstaller
echo Construction de l'application...
python build_app.py

if %errorlevel% neq 0 (
    echo.
    echo Une erreur s'est produite lors de la construction de l'application.
    pause
    exit /b 1
)

:: Vérification de l'existence de NSIS
where makensis >nul 2>nul
if %errorlevel% neq 0 (
    echo NSIS n'est pas installé ou n'est pas dans le PATH.
    echo Pour créer l'installateur, veuillez installer NSIS depuis https://nsis.sourceforge.io/Download
    echo.
    echo Si vous ne souhaitez pas créer l'installateur, vous pouvez utiliser directement l'application
    echo qui se trouve dans le dossier dist\FoodFlex
    pause
    exit /b 1
)

:: Création du script NSIS
echo Création du script d'installation...
echo !define APP_NAME "FoodFlex" > installer.nsi
echo !define COMP_NAME "FoodFlex" >> installer.nsi
echo !define VERSION "1.0.0" >> installer.nsi
echo !define COPYRIGHT "© 2025 FoodFlex" >> installer.nsi
echo !define DESCRIPTION "Application de Cuisine Marocaine" >> installer.nsi
echo !define LICENSE_TXT "LICENSE" >> installer.nsi
echo !define INSTALLER_NAME "FoodFlex-Setup.exe" >> installer.nsi
echo !define MAIN_APP_EXE "FoodFlex.exe" >> installer.nsi
echo !define INSTALL_TYPE "SetShellVarContext current" >> installer.nsi
echo !define REG_ROOT "HKCU" >> installer.nsi
echo !define REG_APP_PATH "Software\Microsoft\Windows\CurrentVersion\App Paths\${MAIN_APP_EXE}" >> installer.nsi
echo !define UNINSTALL_PATH "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" >> installer.nsi
echo !define REG_START_MENU "Start Menu Folder" >> installer.nsi
echo !define DESKTOP_SHORTCUT "Desktop" >> installer.nsi
echo !define STARTMENU_SHORTCUT "StartMenu" >> installer.nsi
echo. >> installer.nsi
echo SetCompressor LZMA >> installer.nsi
echo. >> installer.nsi
echo !include "MUI2.nsh" >> installer.nsi
echo. >> installer.nsi
echo !define MUI_ICON "foodproject\static\foodapp\img\favicon.ico" >> installer.nsi
echo !define MUI_UNICON "foodproject\static\foodapp\img\favicon.ico" >> installer.nsi
echo. >> installer.nsi
echo !define MUI_HEADERIMAGE >> installer.nsi
echo !define MUI_HEADERIMAGE_BITMAP "foodproject\static\foodapp\img\logo.png" >> installer.nsi
echo !define MUI_HEADERIMAGE_RIGHT >> installer.nsi
echo. >> installer.nsi
echo !define MUI_ABORTWARNING >> installer.nsi
echo !define MUI_UNABORTWARNING >> installer.nsi
echo. >> installer.nsi
echo !insertmacro MUI_PAGE_WELCOME >> installer.nsi
echo !insertmacro MUI_PAGE_DIRECTORY >> installer.nsi
echo !insertmacro MUI_PAGE_INSTFILES >> installer.nsi
echo !insertmacro MUI_PAGE_FINISH >> installer.nsi
echo. >> installer.nsi
echo !insertmacro MUI_UNPAGE_CONFIRM >> installer.nsi
echo !insertmacro MUI_UNPAGE_INSTFILES >> installer.nsi
echo. >> installer.nsi
echo !insertmacro MUI_LANGUAGE "French" >> installer.nsi
echo. >> installer.nsi
echo Name "${APP_NAME}" >> installer.nsi
echo OutFile "${INSTALLER_NAME}" >> installer.nsi
echo InstallDir "$PROGRAMFILES\${APP_NAME}" >> installer.nsi
echo. >> installer.nsi
echo Section -MainProgram >> installer.nsi
echo ${INSTALL_TYPE} >> installer.nsi
echo SetOverwrite ifnewer >> installer.nsi
echo SetOutPath "$INSTDIR" >> installer.nsi
echo File /r "dist\FoodFlex\*.*" >> installer.nsi
echo SectionEnd >> installer.nsi
echo. >> installer.nsi
echo Section -Icons_Reg >> installer.nsi
echo SetOutPath "$INSTDIR" >> installer.nsi
echo WriteUninstaller "$INSTDIR\uninstall.exe" >> installer.nsi
echo CreateDirectory "$SMPROGRAMS\${APP_NAME}" >> installer.nsi
echo CreateShortcut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\${MAIN_APP_EXE}" >> installer.nsi
echo CreateShortcut "$SMPROGRAMS\${APP_NAME}\Désinstaller ${APP_NAME}.lnk" "$INSTDIR\uninstall.exe" >> installer.nsi
echo CreateShortcut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${MAIN_APP_EXE}" >> installer.nsi
echo. >> installer.nsi
echo WriteRegStr ${REG_ROOT} "${REG_APP_PATH}" "" "$INSTDIR\${MAIN_APP_EXE}" >> installer.nsi
echo WriteRegStr ${REG_ROOT} "${UNINSTALL_PATH}" "DisplayName" "${APP_NAME}" >> installer.nsi
echo WriteRegStr ${REG_ROOT} "${UNINSTALL_PATH}" "UninstallString" "$INSTDIR\uninstall.exe" >> installer.nsi
echo WriteRegStr ${REG_ROOT} "${UNINSTALL_PATH}" "DisplayIcon" "$INSTDIR\${MAIN_APP_EXE}" >> installer.nsi
echo WriteRegStr ${REG_ROOT} "${UNINSTALL_PATH}" "DisplayVersion" "${VERSION}" >> installer.nsi
echo WriteRegStr ${REG_ROOT} "${UNINSTALL_PATH}" "Publisher" "${COMP_NAME}" >> installer.nsi
echo. >> installer.nsi
echo SectionEnd >> installer.nsi
echo. >> installer.nsi
echo Section Uninstall >> installer.nsi
echo ${INSTALL_TYPE} >> installer.nsi
echo Delete "$INSTDIR\*.*" >> installer.nsi
echo RMDir /r "$INSTDIR" >> installer.nsi
echo Delete "$DESKTOP\${APP_NAME}.lnk" >> installer.nsi
echo Delete "$SMPROGRAMS\${APP_NAME}\*.*" >> installer.nsi
echo RmDir "$SMPROGRAMS\${APP_NAME}" >> installer.nsi
echo DeleteRegKey ${REG_ROOT} "${REG_APP_PATH}" >> installer.nsi
echo DeleteRegKey ${REG_ROOT} "${UNINSTALL_PATH}" >> installer.nsi
echo SectionEnd >> installer.nsi

:: Création de l'installateur avec NSIS
echo Création de l'installateur...
makensis installer.nsi

if %errorlevel% neq 0 (
    echo.
    echo Une erreur s'est produite lors de la création de l'installateur.
    pause
    exit /b 1
)

echo.
echo L'installateur a été créé avec succès!
echo Vous pouvez trouver l'installateur dans le dossier actuel sous le nom "FoodFlex-Setup.exe"
pause 