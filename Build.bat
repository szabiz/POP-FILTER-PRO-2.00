@echo off
setlocal EnableDelayedExpansion

title Pop Filter Pro Build System

echo.
echo ==========================================
echo Pop Filter Pro v2.00 Build System
echo ==========================================
echo.

REM ==================================================
REM Force a clean, isolated build environment
REM Prevents pip's cache / user site-packages from
REM pulling in unwanted or mismatched package versions
REM ==================================================

set PIP_NO_CACHE_DIR=1
set PYTHONNOUSERSITE=1
set PYTHONDONTWRITEBYTECODE=1

REM ==================================================
REM Always start from a fresh virtual environment
REM ==================================================

echo [1/8] Creating a clean virtual environment...

if exist ".venv_build" (
    echo   Removing existing .venv_build ...
    rmdir /s /q .venv_build
)

python -m venv .venv_build
if errorlevel 1 (
    echo.
    echo ERROR: Failed to create the virtual environment. Is Python installed and on PATH?
    pause
    exit /b 1
)

REM ==================================================
REM Install pinned build dependencies only
REM (versions match DEPENDENCIES.txt - no unpinned
REM "latest" installs, so no surprise transitive deps)
REM ==================================================

echo.
echo [2/8] Installing pinned build dependencies...

call .venv_build\Scripts\python.exe -m pip install --no-cache-dir --upgrade pip
if errorlevel 1 goto :pipfail

call .venv_build\Scripts\python.exe -m pip install --no-cache-dir ^
 numpy==2.5.3 ^
 scipy==1.18.1 ^
 sounddevice==0.5.6 ^
 pyinstaller==6.22.3
if errorlevel 1 goto :pipfail

goto :afterpip

:pipfail
echo.
echo ==========================================
echo DEPENDENCY INSTALL FAILED
echo ==========================================
pause
exit /b 1

:afterpip

REM ==================================================
REM Clean previous builds
REM ==================================================

echo.
echo [3/8] Cleaning old build/dist output...

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM ==================================================
REM Build executable
REM ==================================================

echo.
echo [4/8] Building executable...

call .venv_build\Scripts\pyinstaller.exe ^
 --noconfirm ^
 --clean ^
 --onedir ^
 --windowed ^
 --name PopFilterPro ^
 --icon icon.ico ^
 --add-data "icon.ico;." ^
 app.py

if errorlevel 1 (
    echo.
    echo ==========================================
    echo BUILD FAILED
    echo ==========================================
    pause
    exit /b 1
)

REM ==================================================
REM Copy required license / documentation files
REM These are mandatory - the build fails if any of
REM them is missing, so a build is never shipped
REM without its license notices.
REM ==================================================

echo.
echo [5/8] Copying required license and documentation files...

set MISSING=0

if exist LICENSE (
    copy /y LICENSE dist\PopFilterPro\ >nul
    echo   OK   LICENSE
) else (
    echo   MISSING  LICENSE
    set MISSING=1
)

if exist THIRD-PARTY-LICENSES.txt (
    copy /y THIRD-PARTY-LICENSES.txt dist\PopFilterPro\ >nul
    echo   OK   THIRD-PARTY-LICENSES.txt
) else (
    echo   MISSING  THIRD-PARTY-LICENSES.txt
    set MISSING=1
)

if exist README.txt (
    copy /y README.txt dist\PopFilterPro\ >nul
    echo   OK   README.txt
) else (
    echo   MISSING  README.txt
    set MISSING=1
)

REM README.md is optional (source-repo documentation, not
REM required for the shipped binary), copied if present.
if exist README.md (
    copy /y README.md dist\PopFilterPro\ >nul
    echo   OK   README.md (optional)
)

if !MISSING! == 1 (
    echo.
    echo ==========================================
    echo BUILD FAILED - required file(s) missing
    echo ==========================================
    echo One or more mandatory files ^(LICENSE, THIRD-PARTY-LICENSES.txt,
    echo README.txt^) were not found next to Build.bat. Refusing to ship
    echo a build without its license notices.
    pause
    exit /b 1
)

REM ==================================================
REM Generate build reports
REM ==================================================

echo.
echo [6/8] Generating build reports...

dir /b dist\PopFilterPro\*.dll > dist\PopFilterPro\DLL_LIST.txt 2>nul

if exist build\PopFilterPro\warn-PopFilterPro.txt (
    copy /y build\PopFilterPro\warn-PopFilterPro.txt dist\PopFilterPro\ >nul
)

REM ==================================================
REM Show build information
REM ==================================================

echo.
echo [7/8] Build analysis
echo.

echo ==========================================
echo BUNDLED DLL FILES
echo ==========================================
type dist\PopFilterPro\DLL_LIST.txt

echo.

if exist dist\PopFilterPro\warn-PopFilterPro.txt (
    echo ==========================================
    echo PYINSTALLER WARNINGS ^(saved as warn-PopFilterPro.txt^)
    echo ==========================================
    type dist\PopFilterPro\warn-PopFilterPro.txt
)

echo.
echo [8/8] Build successful
echo.
echo ==========================================
echo BUILD SUCCESSFUL
echo ==========================================
echo.
echo Output folder:
echo dist\PopFilterPro
echo.

dir dist\PopFilterPro

echo.
pause
