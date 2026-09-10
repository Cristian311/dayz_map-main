@echo off
setlocal
rem Descarca Sollumz 2.9.0 si dependintele Python (szio, pymateria) in folderul tools\.
rem Nu modifica instalarea ta de Blender: totul ramane in acest folder.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\setup_tools.ps1"
pause
