@echo off
REM ============================================================
REM Pack All Mods in sequence
REM ============================================================

setlocal

cd /d "%~dp0"

echo [PACK ALL] Starting build for all mods...
echo.

call build.bat BossSignal
if errorlevel 1 goto :fail

call build.bat HiveApiMod
if errorlevel 1 goto :fail

call build.bat TrophyHunter
if errorlevel 1 goto :fail

call build.bat MarksContent
if errorlevel 1 goto :fail

echo.
echo [PACK ALL] SUCCESS: All mods built and signed.
echo.
endlocal
exit /b 0

:fail
echo.
echo [PACK ALL] FAILED: Build stopped due to errors.
echo.
endlocal
exit /b 1
