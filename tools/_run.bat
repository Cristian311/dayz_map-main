@echo off
setlocal EnableDelayedExpansion
rem Ruleaza generatorul in Blender (headless), cu Sollumz + dependintele din folderul tools\.
rem Utilizare: _run.bat <preset> [argumente suplimentare pentru run_dayz_map.py]

set "ROOT=%~dp0.."
set "PRESET=%~1"
if "%PRESET%"=="" set "PRESET=demo"
shift

rem --- gaseste Blender ---
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
    pause
    exit /b 1
)

if not exist "%ROOT%\tools\blender_ext\user_default\sollumz\blender_manifest.toml" (
    echo Sollumz nu este in tools\. Ruleaza INSTALEAZA_TOOLS.bat mai intai.
    pause
    exit /b 1
)

set "BLENDER_USER_EXTENSIONS=%ROOT%\tools\blender_ext"
set "BLENDER_USER_CONFIG=%ROOT%\tools\blender_config"
if not exist "%BLENDER_USER_CONFIG%" mkdir "%BLENDER_USER_CONFIG%"

rem --- map.json de langa .bat-uri (setarile salvate din DayZ Map Studio) ---
set "CFGARG="
if exist "%ROOT%\map.json" set CFGARG=--config "%ROOT%\map.json"

echo Blender: %BLENDER%
echo Preset:  %PRESET%
if exist "%ROOT%\map.json" echo Config:  %ROOT%\map.json
echo.
"%BLENDER%" -b -P "%ROOT%\run_dayz_map.py" -- --preset %PRESET% %CFGARG% %1 %2 %3 %4 %5 %6 %7 %8 %9
echo.
echo Rezultatul este in %ROOT%\output\ (vezi REZUMAT.txt)
rem DAYZGEN_NOPAUSE=1 (setat de DayZ Map Studio) = nu astepta o tasta la final
if not "%DAYZGEN_NOPAUSE%"=="1" pause
