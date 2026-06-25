@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM DayZ Mod Build Script (Hardened)
REM
REM Usage:
REM   build.bat <ModName>
REM
REM Example:
REM   build.bat BossSignal
REM
REM MOD_NAME must match the folder name in mods/ EXACTLY.
REM ============================================================

set MOD_NAME=%1
if "%MOD_NAME%"=="" (
    echo Usage: build.bat ^<ModName^>
    exit /b 1
)

REM ── Tool Paths ──────────────────────────────────────────────
set FILEBANK="C:\Program Files (x86)\Steam\steamapps\common\DayZ Tools\Bin\PboUtils\FileBank.exe"
set DSSIGNFILE="C:\Program Files (x86)\Steam\steamapps\common\DayZ Tools\Bin\DsUtils\DSSignFile.exe"

if not exist %FILEBANK% (
    echo [ERROR] FileBank.exe not found at: %FILEBANK%
    exit /b 1
)
if not exist %DSSIGNFILE% (
    echo [ERROR] DSSignFile.exe not found at: %DSSIGNFILE%
    exit /b 1
)

REM ── Mod Path Discovery ──────────────────────────────────────
for %%i in ("%~dp0..") do set ABS_REPO_ROOT=%%~fi
set MOD_DIR=%ABS_REPO_ROOT%\mods\ %MOD_NAME%
REM Remove space
set MOD_DIR=%ABS_REPO_ROOT%\mods\%MOD_NAME%

if not exist "%MOD_DIR%" (
    echo [ERROR] Mod folder not found: %MOD_DIR%
    echo         Standardization Rule: Mod folder name must match prefix exactly.
    exit /b 1
)

set ABS_OUTPUT_ROOT=%ABS_REPO_ROOT%\output\@%MOD_NAME%
set ABS_ADDONS_DIR=%ABS_OUTPUT_ROOT%\addons
set ABS_KEYS_DIR=%ABS_OUTPUT_ROOT%\keys
set ABS_PRIVATE_KEY=%~dp0keys\%MOD_NAME%.biprivatekey
set ABS_PUBLIC_KEY=%~dp0keys\%MOD_NAME%.bikey

if not exist "%ABS_PRIVATE_KEY%" (
    echo [ERROR] Private key not found: %ABS_PRIVATE_KEY%
    echo         Run sign-keygen.bat %MOD_NAME% first.
    exit /b 1
)

REM ── Prepare Output ──────────────────────────────────────────
if not exist "%ABS_ADDONS_DIR%" mkdir "%ABS_ADDONS_DIR%"
if not exist "%ABS_KEYS_DIR%"   mkdir "%ABS_KEYS_DIR%"

echo.
echo [Build] ===================================================
echo   Mod    : %MOD_NAME%
echo   Source : %MOD_DIR%
echo   Output : %ABS_ADDONS_DIR%
echo [Build] ===================================================

REM ── Pack PBO ────────────────────────────────────────────────
echo Packing %MOD_NAME%.pbo...

REM IMPORTANT: To avoid double-nesting inside the PBO (e.g. prefix/foldername/scripts)
REM we must pack from INSIDE the folder, or use the prefix property correctly.
REM A prefix mismatch here can break the mission module.

pushd "%MOD_DIR%"
%FILEBANK% -property prefix=%MOD_NAME% -dst "%ABS_ADDONS_DIR%" *.*
popd

if errorlevel 1 (
    echo [ERROR] FileBank failed.
    exit /b 1
)

REM FileBank with *.* might produce a PBO named after the folder or first file.
REM We expect it to be MOD_NAME.pbo if we did it right, but let's be safe.
if not exist "%ABS_ADDONS_DIR%\%MOD_NAME%.pbo" (
    REM Try to find any .pbo created in the last 10 seconds in that dir
    echo [WARN] %MOD_NAME%.pbo not found, checking for renamed output...
    for /f "delims=" %%a in ('dir /b /od "%ABS_ADDONS_DIR%\*.pbo"') do set LATEST_PBO=%%a
    if defined LATEST_PBO (
        echo Renaming !LATEST_PBO! to %MOD_NAME%.pbo
        move /y "%ABS_ADDONS_DIR%\!LATEST_PBO!" "%ABS_ADDONS_DIR%\%MOD_NAME%.pbo" >nul
    ) else (
        echo [ERROR] No PBO was generated.
        exit /b 1
    )
)

set ABS_PBO_PATH=%ABS_ADDONS_DIR%\%MOD_NAME%.pbo

REM ── Sign PBO ────────────────────────────────────────────────
echo Signing %MOD_NAME%.pbo...
pushd "%~dp0keys"
%DSSIGNFILE% "%MOD_NAME%.biprivatekey" "%ABS_PBO_PATH%"
popd

if errorlevel 1 (
    echo [ERROR] DSSignFile failed.
    exit /b 1
)

REM ── Copy Public Key ─────────────────────────────────────────
copy /y "%ABS_PUBLIC_KEY%" "%ABS_KEYS_DIR%\" >nul

echo.
echo [SUCCESS] Build complete for %MOD_NAME%.
echo.
endlocal
