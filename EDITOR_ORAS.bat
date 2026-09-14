@echo off
rem Editorul de oras in browser: desenezi strazile (orice unghi), inaltimile si zonele, apoi Genereaza (Blender).
rem Planurile stau in output\orase\<nume>.json, orasele generate in output\orase\<nume>.glb / .blend.
cd /d "%~dp0"
title Editor de oras - inchide fereastra asta ca sa opresti editorul
python "%~dp0tools\oras\server.py" %*
if errorlevel 1 (
    echo.
    echo Daca scrie ca portul e ocupat, editorul e deja pornit: deschide http://127.0.0.1:8765/
    pause
)
