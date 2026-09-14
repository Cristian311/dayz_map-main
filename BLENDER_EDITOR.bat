@echo off
setlocal
cd /d "%~dp0"
rem Deschide Blender cu Sollumz si biblioteca de modele GTA V configurate.
rem   BLENDER_EDITOR.bat                      Blender gol, pentru un oras facut de la zero
rem   BLENDER_EDITOR.bat oras.blend           un fisier anume (sau trage .blend-ul peste .bat)
rem Uneltele de harta si exportul in FiveM: bara laterala din viewport (tasta N), tab-ul Harta.
if "%~1"=="" (
    call "%~dp0tools\_blender.bat" -P "%~dp0tools\blender_fivem_export.py" -P "%~dp0tools\blender_map_tools.py" -P "%~dp0tools\blender_gen_buildings.py"
) else (
    call "%~dp0tools\_blender.bat" "%~f1" -P "%~dp0tools\blender_fivem_export.py" -P "%~dp0tools\blender_map_tools.py" -P "%~dp0tools\blender_gen_buildings.py"
)
