@echo off
REM ============================================================================
REM Sample Mapping Editor - Build Script for Windows
REM ============================================================================
REM This script automates the build process:
REM 1. Checks for required tools (Python, PyInstaller)
REM 2. Installs PyInstaller if needed
REM 3. Cleans previous builds
REM 4. Builds the executable
REM 5. Optionally creates installer with Inno Setup
REM ============================================================================

setlocal enabledelayedexpansion

echo.
echo ================================================================================
echo Sample Mapping Editor - Build Script
echo ================================================================================
echo.

REM Check if virtual environment is activated
if not defined VIRTUAL_ENV (
    echo WARNING: Virtual environment not detected!
    echo Please activate your virtual environment first:
    echo   .venv\Scripts\activate
    echo.
    pause
    exit /b 1
)

echo [1/6] Checking Python environment...
python --version
if %ERRORLEVEL% neq 0 (
    echo ERROR: Python not found!
    pause
    exit /b 1
)
echo ✓ Python found
echo.

echo [2/6] Checking PyInstaller...
python -c "import PyInstaller" 2>nul
if %ERRORLEVEL% neq 0 (
    echo PyInstaller not found. Installing...
    pip install pyinstaller
    if %ERRORLEVEL% neq 0 (
        echo ERROR: Failed to install PyInstaller
        pause
        exit /b 1
    )
)
echo ✓ PyInstaller ready
echo.

echo [3/6] Cleaning previous builds...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "*.spec~" del /q "*.spec~"
echo ✓ Clean completed
echo.

echo [4/6] Building executable...
echo This may take 5-10 minutes depending on your system...
echo.
pyinstaller sample-editor.spec --clean --noconfirm

if %ERRORLEVEL% neq 0 (
    echo.
    echo ERROR: Build failed!
    echo Check the output above for errors.
    pause
    exit /b 1
)

echo.
echo ✓ Build completed successfully!
echo.

REM Check if executable was created
if not exist "dist\SampleMappingEditor.exe" (
    echo ERROR: Executable not found in dist folder!
    pause
    exit /b 1
)

REM Get file size
for %%A in ("dist\SampleMappingEditor.exe") do set SIZE=%%~zA
set /a SIZE_MB=!SIZE! / 1048576

echo ================================================================================
echo Build Summary
echo ================================================================================
echo Executable:  dist\SampleMappingEditor.exe
echo Size:        !SIZE_MB! MB
echo.

echo [5/6] Testing executable...
echo Starting application for quick test (close it to continue)...
timeout /t 2 /nobreak >nul
start "" "dist\SampleMappingEditor.exe"
echo ✓ Application started
echo.

echo [6/6] Creating release package...
if not exist "releases" mkdir "releases"

REM Get version from git tag or use timestamp
for /f "tokens=*" %%a in ('git describe --tags --abbrev^=0 2^>nul') do set VERSION=%%a
if "!VERSION!"=="" (
    for /f "tokens=1-3 delims=/ " %%a in ("%date%") do set VERSION=v%%c%%b%%a
)

set RELEASE_NAME=SampleMappingEditor-!VERSION!-Windows

REM Create release folder
if exist "releases\!RELEASE_NAME!" rmdir /s /q "releases\!RELEASE_NAME!"
mkdir "releases\!RELEASE_NAME!"

REM Copy files
copy "dist\SampleMappingEditor.exe" "releases\!RELEASE_NAME!\" >nul
copy "README.md" "releases\!RELEASE_NAME!\" >nul 2>nul
copy "LICENSE" "releases\!RELEASE_NAME!\" >nul 2>nul

REM Create README for release
echo Sample Mapping Editor !VERSION! > "releases\!RELEASE_NAME!\INSTALL.txt"
echo. >> "releases\!RELEASE_NAME!\INSTALL.txt"
echo Simply run SampleMappingEditor.exe - no installation required! >> "releases\!RELEASE_NAME!\INSTALL.txt"
echo. >> "releases\!RELEASE_NAME!\INSTALL.txt"
echo System Requirements: >> "releases\!RELEASE_NAME!\INSTALL.txt"
echo - Windows 10/11 (64-bit) >> "releases\!RELEASE_NAME!\INSTALL.txt"
echo - ~200 MB free disk space >> "releases\!RELEASE_NAME!\INSTALL.txt"
echo - Audio device for playback >> "releases\!RELEASE_NAME!\INSTALL.txt"

echo ✓ Release package created: releases\!RELEASE_NAME!
echo.

REM Optional: Create ZIP archive if 7-Zip is available
where 7z >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo Creating ZIP archive...
    cd releases
    7z a -tzip "!RELEASE_NAME!.zip" "!RELEASE_NAME!\*" >nul
    cd ..
    echo ✓ ZIP created: releases\!RELEASE_NAME!.zip
) else (
    echo NOTE: 7-Zip not found - skipping ZIP creation
    echo You can manually zip the releases\!RELEASE_NAME! folder
)

echo.
echo ================================================================================
echo BUILD COMPLETE!
echo ================================================================================
echo.
echo Your executable is ready:
echo   dist\SampleMappingEditor.exe
echo.
echo Release package:
echo   releases\!RELEASE_NAME!\
echo.
echo You can now:
echo   1. Test the executable
echo   2. Share the release folder with users
echo   3. Create installer with: build_installer.bat (optional)
echo.
pause
