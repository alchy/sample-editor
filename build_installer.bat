@echo off
REM ============================================================================
REM Create Windows Installer using Inno Setup
REM ============================================================================
REM Prerequisites:
REM 1. Run build.bat first to create the executable
REM 2. Install Inno Setup from: https://jrsoftware.org/isdl.php
REM ============================================================================

echo.
echo ================================================================================
echo Sample Mapping Editor - Installer Builder
echo ================================================================================
echo.

REM Check if executable exists
if not exist "dist\SampleMappingEditor.exe" (
    echo ERROR: Executable not found!
    echo Please run build.bat first to create the executable.
    echo.
    pause
    exit /b 1
)

REM Check for Inno Setup
set INNO_PATH=
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set INNO_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe
) else if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set INNO_PATH=C:\Program Files\Inno Setup 6\ISCC.exe
)

if "%INNO_PATH%"=="" (
    echo Inno Setup not found!
    echo.
    echo Please install Inno Setup 6 from:
    echo https://jrsoftware.org/isdl.php
    echo.
    echo After installation, run this script again.
    echo.
    pause
    exit /b 1
)

echo Found Inno Setup: %INNO_PATH%
echo.

REM Create installers directory
if not exist "installers" mkdir "installers"

echo Building installer...
echo.
"%INNO_PATH%" installer.iss

if %ERRORLEVEL% neq 0 (
    echo.
    echo ERROR: Installer build failed!
    pause
    exit /b 1
)

echo.
echo ================================================================================
echo INSTALLER BUILD COMPLETE!
echo ================================================================================
echo.

REM Find the created installer
for %%F in (installers\SampleMappingEditor-Setup-*.exe) do (
    echo Installer created: %%F
    for %%A in ("%%F") do set SIZE=%%~zA
    set /a SIZE_MB=!SIZE! / 1048576
    echo Size: !SIZE_MB! MB
)

echo.
echo You can now distribute this installer to users!
echo.
pause
