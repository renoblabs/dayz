@echo off
REM ============================================================
REM Generate DayZ mod signing key pair
REM
REM Usage:
REM   sign-keygen.bat <ModName>
REM
REM Output:
REM   keys\<ModName>.biprivatekey  — KEEP SECRET. Never share. Never commit.
REM   keys\<ModName>.bikey         — Distribute to server operators.
REM                                   Goes in the server's keys\ folder.
REM ============================================================

setlocal

set MOD_NAME=%1
if "%MOD_NAME%"=="" (
    echo Usage: sign-keygen.bat ^<ModName^>
    echo Example: sign-keygen.bat BossSignal
    exit /b 1
)

set DSSIGN="C:\Program Files (x86)\Steam\steamapps\common\DayZ Tools\Bin\DsUtils\DSCreateKey.exe"
set KEYS_DIR=%~dp0keys

if not exist %DSSIGN% (
    echo [ERROR] DSCreateKey.exe not found.
    echo         Install DayZ Tools via Steam first.
    exit /b 1
)

if not exist %KEYS_DIR% mkdir %KEYS_DIR%

REM Check if key already exists
if exist "%KEYS_DIR%\%MOD_NAME%.biprivatekey" (
    echo [WARN] Key pair for %MOD_NAME% already exists at %KEYS_DIR%
    echo        Delete and re-run only if you need to rotate keys.
    echo        Rotating means redistributing the new .bikey to all server admins.
    set /p CONFIRM="Type YES to overwrite: "
    if not "%CONFIRM%"=="YES" exit /b 0
)

echo.
echo Generating %MOD_NAME% key pair…
REM IMPORTANT: DSCreateKey must be invoked from INSIDE the keys directory,
REM with just the bare name as arg. Passing a path prefix (e.g.
REM "%KEYS_DIR%\%MOD_NAME%") makes DSCreateKey write the path into the
REM key file instead of a real RSA key — DSSignFile then silently fails.
pushd "%KEYS_DIR%"
%DSSIGN% %MOD_NAME%
popd

if errorlevel 1 (
    echo [ERROR] Key generation failed for %MOD_NAME%.
    exit /b 1
)

echo.
echo [SUCCESS] %MOD_NAME% key pair generated:
echo   PRIVATE: %KEYS_DIR%\%MOD_NAME%.biprivatekey  ← KEEP SECRET
echo   PUBLIC:  %KEYS_DIR%\%MOD_NAME%.bikey          ← distribute to server admins
echo.
endlocal
