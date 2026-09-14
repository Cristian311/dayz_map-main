@echo off
setlocal
cd /d "%~dp0"
rem Genereaza o cladire intr-un fisier (output\cladiri\<tip>_<seed>.glb + .blend), fara sa deschizi Blender.
rem Alegi o cladire gata setata sau 0 ca sa le alegi tu. Enter = valoarea din paranteza.

set "TIP=casa" & set "ETAJE=0" & set "LAT=0" & set "ADA=0" & set "ACO=auto" & set "INT=n" & set "TEX=gta"
set "MAG=d"

echo  1  Casa mica de suburbie        (parter, 10 x 8 m, acoperis in doua ape)
echo  2  Casa cu etaj                  (2 niveluri, 12 x 9 m)
echo  3  Vila Vinewood                 (2 niveluri, 20 x 13 m, acoperis in patru ape)
echo  4  Vila mare                     (3 niveluri, 26 x 16 m)
echo  5  Bloc Liberty City mic         (4 etaje, 12 x 16 m, magazine la parter)
echo  6  Bloc Liberty City             (6 etaje, 16 x 20 m, magazine la parter)
echo  7  Bloc Liberty City inalt       (9 etaje, 20 x 24 m)
echo  8  Bloc de locuinte              (5 etaje, fara magazine)
echo  9  Magazin de cartier            (14 x 12 m, vitrine si firma)
echo 10  Supermarket                   (30 x 22 m)
echo 11  Hala / depozit                (30 x 40 m)
echo 12  Casa cu interior              (2 niveluri, se intra in ea)
echo 13  Rand de blocuri Liberty City  (60 m de cladiri lipite, 3-7 etaje, fiecare alta)
echo 14  Rand lung de blocuri          (100 m, 4-9 etaje)
echo 15  Rand de blocuri joase         (60 m, 2-4 etaje)
echo  0  Aleg eu totul
set "P=1"
set /p "P=Alege [1]: "

if "%P%"=="1"  (set "TIP=casa" & set "ETAJE=1" & set "LAT=10" & set "ADA=8" & set "ACO=doua")
if "%P%"=="2"  (set "TIP=casa" & set "ETAJE=2" & set "LAT=12" & set "ADA=9")
if "%P%"=="3"  (set "TIP=vila" & set "ETAJE=2" & set "LAT=20" & set "ADA=13" & set "ACO=patru")
if "%P%"=="4"  (set "TIP=vila" & set "ETAJE=3" & set "LAT=26" & set "ADA=16")
if "%P%"=="5"  (set "TIP=bloc" & set "ETAJE=4" & set "LAT=12" & set "ADA=16")
if "%P%"=="6"  (set "TIP=bloc" & set "ETAJE=6" & set "LAT=16" & set "ADA=20")
if "%P%"=="7"  (set "TIP=bloc" & set "ETAJE=9" & set "LAT=20" & set "ADA=24")
if "%P%"=="8"  (set "TIP=bloc" & set "ETAJE=5" & set "LAT=18" & set "ADA=14" & set "MAG=n")
if "%P%"=="9"  (set "TIP=magazin" & set "LAT=14" & set "ADA=12")
if "%P%"=="10" (set "TIP=magazin" & set "LAT=30" & set "ADA=22")
if "%P%"=="11" (set "TIP=hala" & set "LAT=30" & set "ADA=40")
if "%P%"=="12" (set "TIP=casa" & set "ETAJE=2" & set "LAT=12" & set "ADA=10" & set "INT=d")
set "RAND="
if "%P%"=="13" set "RAND=--rand --lungime 60 --etaje-min 3 --etaje-max 7"
if "%P%"=="14" set "RAND=--rand --lungime 100 --etaje-min 4 --etaje-max 9"
if "%P%"=="15" set "RAND=--rand --lungime 60 --etaje-min 2 --etaje-max 4"
if not "%P%"=="0" goto seed

echo Tipuri: vila, casa, bloc (caramida, Liberty City), magazin, hala
set /p "TIP=Tip [casa]: "
set /p "ETAJE=Etaje [implicit dupa tip]: "
set /p "LAT=Latime in metri [implicit dupa tip]: "
set /p "ADA=Adancime in metri [implicit dupa tip]: "
set /p "ACO=Acoperis: auto, patru, doua, plat [auto]: "
set /p "INT=Cu interior? d/n [n]: "
set /p "MAG=Bloc cu magazine la parter? d/n [d]: "

:seed
set /p "TEX=Texturi: gta sau simple [gta]: "
set "SEED=0"
set /p "SEED=Seed (acelasi seed = aceeasi cladire) [la intamplare]: "

set "EXTRA=%RAND%"
if /i "%INT%"=="d" set "EXTRA=%EXTRA% --interior"
if /i "%MAG%"=="n" set "EXTRA=%EXTRA% --fara-magazin"

echo Generez...
call "%~dp0tools\_blender.bat" -b -P "%~dp0tools\gen_cladire.py" -- --tip %TIP% --etaje %ETAJE% --latime %LAT% ^
    --adancime %ADA% --acoperis %ACO% --texturi %TEX% --seed %SEED% %EXTRA% > "%TEMP%\gen_cladire.log" 2>&1
findstr /b "CLADIRE" "%TEMP%\gen_cladire.log"
findstr /c:"Error" /c:"error:" "%TEMP%\gen_cladire.log"
if exist "%~dp0output\cladiri" start "" explorer "%~dp0output\cladiri"
echo.
echo Tragi fisierul .glb in fereastra Blender (sau File ^> Append ^> fisierul .blend ^> Object).
pause
