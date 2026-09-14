@echo off
rem Porneste Blender cu Sollumz si preferintele din tools\ (profil izolat), cu argumentele date.
rem Folosit de BIBLIOTECA_GTA.bat si BLENDER_EDITOR.bat.
setlocal
set "ROOT=%~dp0.."

set "BLENDER="
if exist "%ROOT%\tools\blender_path.txt" set /p BLENDER=<"%ROOT%\tools\blender_path.txt"
if not exist "%BLENDER%" (
    for /d %%D in ("%ProgramFiles%\Blender Foundation\Blender*") do set "BLENDER=%%D\blender.exe"
)
if not exist "%BLENDER%" (
    for /f "delims=" %%P in ('where blender 2^>nul') do set "BLENDER=%%P"
)
if not exist "%BLENDER%" (
    echo Nu am gasit blender.exe. Scrie calea completa in tools\blender_path.txt
    exit /b 1
)

set "BLENDER_USER_EXTENSIONS=%ROOT%\tools\blender_ext"
set "BLENDER_USER_CONFIG=%ROOT%\tools\blender_config"
if not exist "%BLENDER_USER_CONFIG%" mkdir "%BLENDER_USER_CONFIG%"

"%BLENDER%" %*
