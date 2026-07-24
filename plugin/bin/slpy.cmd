@echo off
REM SnapCode `slpy` launcher for native Windows shells (cmd / PowerShell).
REM The POSIX `slpy` script is used by Claude Code's Bash tool (git-bash); this .cmd is
REM for users who run `slpy` directly in cmd/PowerShell. It forwards to the slpy.exe that
REM bootstrap.py installed into the plugin data dir, running bootstrap once if needed.

setlocal
if defined CLAUDE_PLUGIN_DATA (
  set "DATA_DIR=%CLAUDE_PLUGIN_DATA%"
) else (
  set "DATA_DIR=%USERPROFILE%\.claude\plugins\data\snapcode-snapcode"
)
set "REAL_SLPY=%DATA_DIR%\bin\slpy.exe"

if not exist "%REAL_SLPY%" (
  python "%~dp0bootstrap.py" 2>nul || py "%~dp0bootstrap.py"
)
if not exist "%REAL_SLPY%" (
  echo [snapcode] slpy is not installed yet and bootstrap did not produce it. 1>&2
  echo           expected: %REAL_SLPY% 1>&2
  exit /b 1
)
"%REAL_SLPY%" %*
