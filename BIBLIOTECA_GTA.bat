@echo off
setlocal
cd /d "%~dp0"
rem Construieste biblioteca Blender cu modelele GTA V (si texturile lor) folosite de orasul
rem generat, apoi scena .blend a orasului. Prima rulare dureaza: indexeaza tot jocul.

set "CITY=%~1"
if "%CITY%"=="" for /d %%D in ("output\*_oras") do set "CITY=%%D"
if not exist "%CITY%\ytyps.txt" (
    echo Ruleaza intai: python generate_city.py
    pause
    exit /b 1
)

call "%~dp0tools\_blender.bat" -b -P "%~dp0tools\blender_build_library.py" -- --ytyps "%CITY%\ytyps.txt"
call "%~dp0tools\_blender.bat" -b -P "%~dp0tools\blender_city_scene.py" -- --city "%CITY%" --render
echo.
echo Scena: %CITY%   (deschide-o cu BLENDER_EDITOR.bat)
pause
