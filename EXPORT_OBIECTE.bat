@echo off
setlocal
rem Exporta obiectele puse manual din editorul in joc, direct in resursa FiveM instalata.
rem Nu regenereaza harta si nu are nevoie de Blender (foloseste szio din tools\pydeps).

set "PY="
for /f "delims=" %%P in ('where python 2^>nul') do if not defined PY set "PY=%%P"
if not defined PY for /f "delims=" %%P in ('where py 2^>nul') do if not defined PY set "PY=%%P"
if not defined PY (
    echo Nu am gasit Python pe calculator.
    echo Instaleaza Python 3.10 sau mai nou de pe python.org, bifeaza
    echo "Add python.exe to PATH", apoi ruleaza din nou acest fisier.
    pause
    exit /b 1
)

"%PY%" "%~dp0export_custom_ymap.py" %*
echo.
if not "%DAYZGEN_NOPAUSE%"=="1" pause
