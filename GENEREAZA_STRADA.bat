@echo off
setlocal
cd /d "%~dp0"
rem Piese de strada de lipit cap la cap in Blender (output\strazi\<tip>_<piesa>.glb + .blend).
rem Enter = valoarea din paranteza.

echo Tipuri de strada:
echo  1  strada   2 benzi, linie dubla galbena, 14 m cu trotuarele
echo  2  artera   4 benzi, 21 m cu trotuarele
echo  3  alee     fara marcaje, 8 m
set "T=1"
set /p "T=Alege [1]: "
set "TIP=strada"
if "%T%"=="2" set "TIP=artera"
if "%T%"=="3" set "TIP=alee"

echo.
echo Piese:
echo  1  tot kitul intr-un fisier (drept 20 m, drept 10 m, trecere, cruce, T, curba, capat)
echo  2  drept 20 m     3  drept 10 m     4  trecere de pietoni
echo  5  intersectie in cruce             6  intersectie in T
echo  7  curba de 90 de grade             8  capat de strada
set "P=1"
set /p "P=Alege [1]: "
set "PIESA=kit"
if "%P%"=="2" set "PIESA=drept20"
if "%P%"=="3" set "PIESA=drept10"
if "%P%"=="4" set "PIESA=trecere"
if "%P%"=="5" set "PIESA=cruce"
if "%P%"=="6" set "PIESA=T"
if "%P%"=="7" set "PIESA=curba"
if "%P%"=="8" set "PIESA=capat"

set "TEX=gta"
set /p "TEX=Texturi: gta sau simple [gta]: "

echo Generez...
call "%~dp0tools\_blender.bat" -b -P "%~dp0tools\gen_strada.py" -- --tip %TIP% --piesa %PIESA% --texturi %TEX% ^
    > "%TEMP%\gen_strada.log" 2>&1
findstr /b "STRADA" "%TEMP%\gen_strada.log"
findstr /c:"Error" /c:"error:" "%TEMP%\gen_strada.log"
if exist "%~dp0output\strazi" start "" explorer "%~dp0output\strazi"
echo.
echo Tragi fisierul .glb in Blender. Piesele se lipesc prin colturi: magnetul din bara de sus pornit,
echo "Snap To: Vertex", apoi G si duci coltul unei piese langa coltul celeilalte. R Z 90 = rotire.
pause
