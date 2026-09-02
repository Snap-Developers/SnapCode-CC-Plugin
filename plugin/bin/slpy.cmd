@echo off
setlocal
REM SnapCode slpy launcher (Windows cmd / PowerShell).
REM The sibling `slpy` is now a POSIX sh script (for Git-Bash / macOS / Linux), which
REM cmd can't run — so this batch file forwards to the real slpy.exe directly, mirroring
REM bootstrap.py's data-dir resolution. If slpy.exe isn't there yet, run bootstrap once.

if defined CLAUDE_PLUGIN_ROOT (set "PLUGIN_ROOT=%CLAUDE_PLUGIN_ROOT%") else (for %%I in ("%~dp0..") do set "PLUGIN_ROOT=%%~fI")

if defined CLAUDE_PLUGIN_DATA (
  set "PLUGIN_DATA=%CLAUDE_PLUGIN_DATA%"
) else if exist "%USERPROFILE%\.claude\plugins\data" (
  set "PLUGIN_DATA=%USERPROFILE%\.claude\plugins\data\snapcode-snapcode"
) else (
  set "PLUGIN_DATA=%PLUGIN_ROOT%\.data"
)

set "REAL_SLPY=%PLUGIN_DATA%\bin\slpy.exe"

if not exist "%REAL_SLPY%" (
  python "%PLUGIN_ROOT%\bin\bootstrap.py" 2>nul || py "%PLUGIN_ROOT%\bin\bootstrap.py"
)

if not exist "%REAL_SLPY%" (
  echo [snapcode] slpy is not installed yet and bootstrap did not produce it. 1>&2
  echo           expected: %REAL_SLPY% 1>&2
  exit /b 1
)

"%REAL_SLPY%" %*
