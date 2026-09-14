@echo off
setlocal
cd /d "%~dp0"
rem Cartier in grila, stil Liberty City (output\cartiere\cartier_<seed>.glb + .blend).
rem Enter = valoarea din paranteza.

echo Marime:
echo  1  mic         2 x 2 cvartale  (~210 x 150 m)
echo  2  mediu       3 x 2 cvartale  (~310 x 150 m)
echo  3  mare        4 x 3 cvartale  (~400 x 220 m, cateva minute)
echo  4  foarte mare 5 x 4 cvartale  (~500 x 290 m, dureaza mult)
set "M=2"
set /p "M=Alege [2]: "
set "NX=3" & set "NY=2"
if "%M%"=="1" (set "NX=2" & set "NY=2")
if "%M%"=="3" (set "NX=4" & set "NY=3")
if "%M%"=="4" (set "NX=5" & set "NY=4")

echo.
echo Inaltime:
echo  1  Liberty City mixt   (3-9 etaje, mai inalt spre centru)
echo  2  centru inalt        (5-14 etaje)
echo  3  cartier jos         (2-5 etaje)
set "H=1"
set /p "H=Alege [1]: "
set "EMIN=3" & set "EMAX=9"
if "%H%"=="2" (set "EMIN=5" & set "EMAX=14")
if "%H%"=="3" (set "EMIN=2" & set "EMAX=5")

set "CV=80x50"
set /p "CV=Marimea unui cvartal in metri, X x Y [80x50]: "
set "TEX=gta"
set /p "TEX=Texturi: gta sau simple [gta]: "
set "SEED=0"
set /p "SEED=Seed (acelasi seed = acelasi cartier) [la intamplare]: "

echo Generez... (un cartier mediu dureaza 1-3 minute)
call "%~dp0tools\_blender.bat" -b -P "%~dp0tools\gen_cartier.py" -- --x %NX% --y %NY% --cvartal %CV% ^
    --etaje-min %EMIN% --etaje-max %EMAX% --texturi %TEX% --seed %SEED% > "%TEMP%\gen_cartier.log" 2>&1
findstr /b "CARTIER" "%TEMP%\gen_cartier.log"
findstr /c:"Error" /c:"error:" "%TEMP%\gen_cartier.log"
if exist "%~dp0output\cartiere" start "" explorer "%~dp0output\cartiere"
echo.
echo Tragi fisierul .glb in Blender (sau File ^> Append ^> fisierul .blend ^> Collection).
pause
