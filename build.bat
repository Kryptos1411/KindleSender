@echo off
echo ========================================
echo    Kindle Sender Build Script
echo ========================================
echo.

REM Activate virtual environment
call venv\Scripts\activate
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    echo Make sure you have created it with: python -m venv venv
    pause
    exit /b 1
)

REM Check if calibre.zip exists
if not exist "calibre.zip" (
    echo calibre.zip not found. Creating...
    echo.
    
    if exist "calibre_portable\Calibre" (
        powershell -Command "Compress-Archive -Path 'calibre_portable\Calibre\*' -DestinationPath 'calibre.zip' -Force"
        echo Created calibre.zip
    ) else (
        echo ERROR: calibre_portable\Calibre folder not found!
        echo.
        echo Please:
        echo   1. Download Calibre Portable from https://calibre-ebook.com/download_portable
        echo   2. Extract it
        echo   3. Copy the Calibre folder to calibre_portable\Calibre
        echo.
        pause
        exit /b 1
    )
)

echo.
echo Checking calibre.zip size...
for %%A in (calibre.zip) do (
    set SIZE=%%~zA
    echo calibre.zip: %%~zA bytes
)

REM Clean previous builds
echo.
echo Cleaning previous builds...
if exist "dist" rmdir /s /q dist
if exist "build" rmdir /s /q build

REM Build
echo.
echo Building application...
echo.
pyinstaller build.spec --clean

echo.
echo ========================================

if exist "dist\KindleSender.exe" (
    echo    BUILD SUCCESSFUL!
    echo ========================================
    echo.
    echo Output: dist\KindleSender.exe
    echo.
    for %%A in (dist\KindleSender.exe) do echo Size: %%~zA bytes
    echo.
    echo First run will extract Calibre to:
    echo   %%LOCALAPPDATA%%\KindleSender\calibre\
    echo.
) else (
    echo    BUILD FAILED!
    echo ========================================
    echo.
    echo Check the output above for errors.
)

echo.
pause