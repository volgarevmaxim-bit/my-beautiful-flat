@echo off
rem ------------------------------------------------------------
rem  open_in_firefox.bat
rem  Handler for the custom myflat: URL protocol (registered
rem  under HKCU, no admin required). See register_firefox_handler.bat
rem  Usage: open_in_firefox.bat "myflat:https://www.cian.ru/sale/flat/123/"
rem  1) Strip the myflat: prefix.
rem  2) Validate: URL must start with https:// and contain cian.ru.
rem     Arbitrary schemes / URLs are never executed.
rem  3) Open in Firefox if installed, otherwise in the default browser.
rem ------------------------------------------------------------
setlocal EnableExtensions

set "ARG=%~1"
if not defined ARG exit /b 1

rem Strip the myflat: prefix (case-insensitive).
if /i "%ARG:~0,7%"=="myflat:" (
    set "URL=%ARG:~7%"
) else (
    set "URL=%ARG%"
)

rem Validate via environment variable to avoid cmd metacharacter
rem injection (the URL never appears as raw text on a command line).
set "MBFLAT_URL=%URL%"
powershell -NoProfile -Command "if(-not $env:MBFLAT_URL.ToLower().StartsWith('https://') -or -not $env:MBFLAT_URL.ToLower().Contains('cian.ru')){exit 1}"
if errorlevel 1 exit /b 1

rem Locate firefox.exe across common install paths.
set "FF="
if exist "%ProgramFiles%\Mozilla Firefox\firefox.exe" set "FF=%ProgramFiles%\Mozilla Firefox\firefox.exe"
if not defined FF if exist "%ProgramFiles(x86)%\Mozilla Firefox\firefox.exe" set "FF=%ProgramFiles(x86)%\Mozilla Firefox\firefox.exe"
if not defined FF if exist "%LOCALAPPDATA%\Mozilla Firefox\firefox.exe" set "FF=%LOCALAPPDATA%\Mozilla Firefox\firefox.exe"

rem Open in Firefox, or fall back to the default browser.
if defined FF (
    start "" "%FF%" "%URL%"
) else (
    start "" "%URL%"
)
exit /b 0
