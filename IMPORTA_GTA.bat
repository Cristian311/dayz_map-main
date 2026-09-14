@echo off
setlocal
cd /d "%~dp0"
rem Aduce modele GTA V in biblioteca Blender, direct din joc, cu texturi, pe categorii.
rem
rem   IMPORTA_GTA.bat                   toate fisierele .ytyp cu cladiri intregi din catalog
rem   IMPORTA_GTA.bat props             props-urile: garduri, stalpi, semne, banci, copaci... (tools\props_ytyps.txt)
rem   IMPORTA_GTA.bat beverly           doar fisierele .ytyp care au "beverly" in nume
rem   IMPORTA_GTA.bat "downtown|venice" mai multe zone
rem
rem Zone de oras utile: downtown, beverly, venice, hollywood, santamon, koreatown,
rem scentral, sanpedro, indust, port, airport.
rem Dupa: BLENDER_EDITOR.bat, apoi Asset Browser, biblioteca "GTA V (generator)".

if "%~1"=="" (
    call "%~dp0tools\_blender.bat" -b -P "%~dp0tools\blender_build_library.py" -- --solid
) else if /i "%~1"=="props" (
    call "%~dp0tools\_blender.bat" -b -P "%~dp0tools\blender_build_library.py" -- --ytyps "%~dp0tools\props_ytyps.txt"
) else (
    call "%~dp0tools\_blender.bat" -b -P "%~dp0tools\blender_build_library.py" -- --pattern "%~1"
)
echo.
pause
