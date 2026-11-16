@echo off
rem ------------------------------------------------------------
rem  open_in_firefox.bat
rem  Handler for the myflat: URL protocol. Launched HIDDEN via
rem  open_in_firefox.vbs (wscript), so no console window flashes.
rem  Usage: open_in_firefox.bat "myflat:https://www.cian.ru/sale/flat/123/"
rem  1) Strip the myflat: prefix.
rem  2) Validate in pure batch (NO PowerShell): scheme must be
rem     https:// and the host must be www.cian.ru / cian.ru / *.cian.ru.
rem     Anything else is never opened.
rem  3) Open in Firefox if installed, otherwise in the default browser.
rem ------------------------------------------------------------
setlocal EnableExtensions

set "ARG=%~1"
if not defined ARG exit /b 1

set "URL=%ARG%"
if /i "%URL:~0,7%"=="myflat:" set "URL=%URL:~7%"
if not defined URL exit /b 1

rem 1) Scheme check (substring compare, no metacharacter expansion).
if /i not "%URL:~0,8%"=="https://" exit /b 1

rem 2) Host check: strip https://, take the host up to the first "/".
rem    for /f keeps the value quoted, so & and other metacharacters
rem    inside the URL stay literal.
set "REST=%URL:~8%"
set "HOST="
for /f "delims=/" %%H in ("%REST%") do set "HOST=%%H"
if not defined HOST exit /b 1
set "OK="
if /i "%HOST%"=="www.cian.ru" set OK=1
if /i "%HOST%"=="cian.ru" set OK=1
if not defined OK if /i "%HOST:~-8%"==".cian.ru" set OK=1
if not defined OK exit /b 1

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
