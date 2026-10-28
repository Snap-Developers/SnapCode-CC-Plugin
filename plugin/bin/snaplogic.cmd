@echo off
setlocal
REM SnapCode snaplogic launcher (Windows cmd / PowerShell).
REM The sibling `snaplogic` is a POSIX sh script, which cmd can't run, so this forwards
REM to the real snaplogic.exe directly, mirroring bootstrap.py's data-dir resolution.
REM If snaplogic.exe isn't there yet, run bootstrap once.

if defined CLAUDE_PLUGIN_ROOT (set "PLUGIN_ROOT=%CLAUDE_PLUGIN_ROOT%") else (for %%I in ("%~dp0..") do set "PLUGIN_ROOT=%%~fI")

if defined CLAUDE_PLUGIN_DATA (
  set "PLUGIN_DATA=%CLAUDE_PLUGIN_DATA%"
) else if exist "%USERPROFILE%\.claude\plugins\data" (
  set "PLUGIN_DATA=%USERPROFILE%\.claude\plugins\data\snapcode-snapcode"
) else (
  set "PLUGIN_DATA=%PLUGIN_ROOT%\.data"
)

set "REAL_CLI=%PLUGIN_DATA%\bin\snaplogic.exe"

REM Bootstrap prints its hook JSON on stdout; keep it out of the command's own output.
if not exist "%REAL_CLI%" (
  set "SNAPCODE_FROM_LAUNCHER=1"
  python "%PLUGIN_ROOT%\bin\bootstrap.py" 1>&2 2>nul || py "%PLUGIN_ROOT%\bin\bootstrap.py" 1>&2
)

if not exist "%REAL_CLI%" (
  echo [snapcode] the snaplogic CLI is not installed yet and bootstrap did not produce it. 1>&2
  echo           expected: %REAL_CLI% 1>&2
  exit /b 1
)

REM Tag the call as SnapCode's; the CLI appends this to its User-Agent. cmd cannot
REM tell an empty variable from an unset one, so opting out means setting another value.
if not defined SNAPLOGIC_CLIENT (
  if exist "%PLUGIN_DATA%\client_token" (set /p SNAPLOGIC_CLIENT=<"%PLUGIN_DATA%\client_token") else (set "SNAPLOGIC_CLIENT=snapcode")
)

set "UV_TOOL_DIR=%PLUGIN_DATA%\tools"
set "UV_TOOL_BIN_DIR=%PLUGIN_DATA%\bin"
set "PATH=%PLUGIN_DATA%\bin;%PATH%"

"%REAL_CLI%" %*
