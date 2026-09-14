# -*- coding: utf-8 -*-
"""
Pregateste Sollumz in Blender-ul pornit cu profilul izolat din tools\\ (tools\\_blender.bat).

Sollumz isi cauta dependintele (szio, pymateria) intr-un site-packages propriu, in folderul de
date al extensiei; generatorul le tine in tools\\pydeps. Le copiem o data acolo, ca orice Blender
pornit cu acest profil sa le gaseasca: procesele pe care Sollumz le porneste singur la
construirea bibliotecii si Blender-ul deschis de BLENDER_EDITOR.bat.
"""
import importlib
import shutil
import sys
from pathlib import Path

import addon_utils
import bpy

ROOT = Path(__file__).resolve().parent.parent
PYDEPS = ROOT / "tools" / "pydeps"


def _package() -> str:
    for mod in addon_utils.modules():
        if mod.__name__.split(".")[-1].lower() in ("sollumz", "sollumz_dev"):
            return mod.__name__
    raise RuntimeError("Sollumz nu a fost gasit in tools\\blender_ext (ruleaza INSTALEAZA_TOOLS.bat).")


def _copy_deps(pkg: str) -> bool:
    deps = importlib.import_module(f"{pkg}.dependencies")
    site = Path(deps.site_packages_path())
    site.mkdir(parents=True, exist_ok=True)
    copied = False
    for item in PYDEPS.iterdir():
        target = site / item.name
        if target.exists():
            continue
        if item.is_dir():
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)
        copied = True
    if copied:
        print(f"dependintele Sollumz copiate in {site}")
    return copied


def register_asset_library(path, name: str = "GTA V (generator)") -> bool:
    """
    Inregistreaza folderul ca biblioteca de asset-uri Blender, ca modelele GTA sa apara in
    Asset Browser (de acolo le tragi direct in scena). Sollumz il stie doar ca "shared assets".
    """
    libs = bpy.context.preferences.filepaths.asset_libraries
    target = str(Path(path).resolve()).lower()
    for lib in libs:
        if str(Path(bpy.path.abspath(lib.path)).resolve()).lower() == target:
            return False
    try:
        libs.new(name=name, directory=str(path))
    except Exception:
        bpy.ops.preferences.asset_library_add(directory=str(path))
        libs[-1].name = name
    bpy.context.preferences.is_dirty = True
    bpy.ops.wm.save_userpref()
    print(f"biblioteca de asset-uri Blender adaugata: {name} -> {path}")
    return True


def setup_sollumz(save_prefs: bool = True) -> str:
    """Activeaza Sollumz cu dependintele montate; intoarce numele pachetului."""
    if str(PYDEPS) not in sys.path:
        sys.path.insert(0, str(PYDEPS))
    pkg = _package()
    copied = _copy_deps(pkg)
    deps = importlib.import_module(f"{pkg}.dependencies")

    # Daca Sollumz a pornit fara dependinte, s-a inregistrat doar partial: il repornim.
    if pkg in bpy.context.preferences.addons and (copied or not deps.IS_SZIO_AVAILABLE):
        bpy.ops.preferences.addon_disable(module=pkg)
    if pkg not in bpy.context.preferences.addons:
        bpy.ops.preferences.addon_enable(module=pkg)

    deps = importlib.import_module(f"{pkg}.dependencies")
    if not deps.IS_SZIO_AVAILABLE:
        raise RuntimeError("Sollumz nu vede szio nici dupa copierea dependintelor.")
    if save_prefs:
        # Sollumz ramane activat in profil, pentru procesele-lucrator si pentru editor.
        bpy.context.preferences.is_dirty = True
        bpy.ops.wm.save_userpref()
    return pkg
