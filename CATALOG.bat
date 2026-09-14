@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo  Catalog de arhetipuri vanilla (pentru generatorul de orase)
echo ============================================================
echo.
echo  Pasul 1 (aici)  : scriu lista de nume pe care o scaneaza jocul
echo  Pasul 2 (in joc): /catalogscan   - admin nivel 5, dureaza cateva minute
echo  Pasul 3 (aici)  : clasific masuratorile in catalog.json
echo.

set PY=python
%PY% --version >nul 2>&1 || set PY=py
%PY% --version >nul 2>&1 || (
    echo Python nu a fost gasit in PATH.
    pause
    exit /b 1
)

if "%~1"=="" (
    %PY% make_catalog.py
) else (
    %PY% make_catalog.py %*
)

echo.
pause
