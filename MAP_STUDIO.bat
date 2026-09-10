@echo off
setlocal
rem Deschide DayZ Map Studio (interfata grafica pentru setari + previzualizare + generare).

set "PY="
for /f "delims=" %%P in ('where pythonw 2^>nul') do if not defined PY set "PY=%%P"
if not defined PY for /f "delims=" %%P in ('where python 2^>nul') do if not defined PY set "PY=%%P"
if not defined PY (
    echo Nu am gasit Python pe calculator.
    echo Instaleaza Python 3.10 sau mai nou de pe python.org, bifeaza
    echo "Add python.exe to PATH", apoi ruleaza din nou acest fisier.
    pause
    exit /b 1
)

"%PY%" -c "import numpy, tkinter" 2>nul
if errorlevel 1 (
    echo Lipseste numpy sau tkinter. Ruleaza:
    echo     "%PY%" -m pip install numpy
    pause
    exit /b 1
)

start "" "%PY%" "%~dp0map_studio.py"
