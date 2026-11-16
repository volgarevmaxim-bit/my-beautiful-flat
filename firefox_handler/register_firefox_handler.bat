@echo off
rem ------------------------------------------------------------
rem  register_firefox_handler.bat
rem  Registers the myflat: URL protocol under HKCU (no admin).
rem  Run once (double-click). The handler opens CIAN links in
rem  Firefox when it is installed, otherwise in the default browser.
rem  The protocol is launched through open_in_firefox.vbs (wscript),
rem  so NO console window appears on every click.
rem  This script hides itself and reports the result as a dialog.
rem ------------------------------------------------------------
if /i "%~1"=="--hidden" goto :run

set "HIDEBAT=%TEMP%\mbflat_reg_hidden.vbs"
> "%HIDEBAT%" echo Set sh = CreateObject("WScript.Shell")
>> "%HIDEBAT%" echo sh.Run """%~f0"" --hidden", 0, False
wscript.exe "%HIDEBAT%"
del "%HIDEBAT%" >nul 2>&1
exit /b

:run
rem Remove any old registration first (the old version pointed at the .bat).
reg delete "HKCU\Software\Classes\myflat" /f >nul 2>&1
reg add "HKCU\Software\Classes\myflat" /ve /d "URL:myflat" /f >nul
reg add "HKCU\Software\Classes\myflat" /v "URL Protocol" /d "" /f >nul
reg add "HKCU\Software\Classes\myflat\shell\open\command" /ve /d "\"%SystemRoot%\System32\wscript.exe\" \"%~dp0open_in_firefox.vbs\" \"%%1\"" /f >nul
if errorlevel 1 (
    if /i "%~2"=="--silent" exit /b 1
    powershell -NoProfile -WindowStyle Hidden -Command "Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show('Не удалось зарегистрировать протокол myflat.','myflat',[System.Windows.MessageBoxButton]::OK,[System.Windows.MessageBoxImage]::Error) | Out-Null"
    exit /b 1
)
if /i "%~2"=="--silent" exit /b 0
powershell -NoProfile -WindowStyle Hidden -Command "Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show('Протокол myflat перерегистрирован: ЦИАН теперь открывается без консольного окна.','myflat',[System.Windows.MessageBoxButton]::OK,[System.Windows.MessageBoxImage]::Information) | Out-Null"
exit /b 0
