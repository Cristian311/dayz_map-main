@echo off
rem Fereastra cu toate generatoarele: cladire, rand de cladiri, strazi, cartier (setari + setari prestabilite).
cd /d "%~dp0"
where pythonw >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw "%~dp0tools\generator_gui.py"
) else (
    python "%~dp0tools\generator_gui.py"
    if errorlevel 1 pause
)
