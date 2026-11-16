@echo off
rem ------------------------------------------------------------
rem  register_firefox_handler.bat
rem  Registers the myflat: URL protocol under HKCU (no admin).
rem  Run once. The handler opens CIAN links in Firefox when it is
rem  installed, otherwise in the default browser.
rem ------------------------------------------------------------

reg add "HKCU\Software\Classes\myflat" /ve /d "URL:myflat" /f >nul
reg add "HKCU\Software\Classes\myflat" /v "URL Protocol" /d "" /f >nul
reg add "HKCU\Software\Classes\myflat\shell\open\command" /ve /d "\"%~dp0open_in_firefox.bat\" \"%%1\"" /f >nul
if errorlevel 1 (
    echo ERROR: registration failed
    exit /b 1
)

echo OK
echo.
echo myflat: protocol is registered for the current user.
echo Handler: "%~dp0open_in_firefox.bat"
echo.
echo Re-run this script anytime to refresh the handler path
echo (for example after moving this folder).
exit /b 0
