# -*- coding: utf-8 -*-
"""
Construieste biblioteca Sollumz de modele GTA V (geometrie + texturi) direct din jocul instalat.

Dupa asta, cand imporți in Blender un .ymap (File > Import > Sollumz), fiecare entitate apare
ca modelul ei real din joc, cu texturi. Biblioteca apare si in Asset Browser-ul din Blender,
de unde poti trage cladiri GTA direct in scena.

Ruleaza in Blender fara interfata, cu profilul izolat din tools\\ (vezi BIBLIOTECA_GTA.bat):

    blender -b -P tools\\blender_build_library.py -- --ytyps output\\oras\\ytyps.txt
    blender -b -P tools\\blender_build_library.py -- --pattern "^downtown_01_metadata_00[1-3]_strm$"

Optiuni: --lib <folder> (implicit output\\gta_asset_library), --jobs N (procese Blender paralele),
--gta <cale GTA V> (implicit din CitizenFX.ini).

Construieste cate un .blend pentru fiecare .ytyp ales. Un .ytyp de oras are sute de arhetipuri,
deci alege doar ce foloseste orasul (fisierul ytyps.txt scris de generator).
"""
import importlib
import importlib.util
import os
import re
import sys
import time
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from _sollumz_setup import register_asset_library, setup_sollumz  # noqa: E402


def solid_ytyps() -> list:
    """Fisierele .ytyp care contin cladiri masurate ca solide in catalog (cele bune de folosit)."""
    import json
    path = ROOT / "dayzgen" / "data" / "catalog.json"
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    names = set()
    for arch in data.get("archetypes") or ():
        tags = arch.get("tags") or []
        if "solid" in tags:
            names.update(t[5:] for t in tags if t.startswith("ytyp:"))
    return sorted(names)


def cli_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = {"ytyps": None, "pattern": None, "lib": None, "jobs": max(1, (os.cpu_count() or 4) // 3), "gta": None}
    i = 0
    while i < len(argv):
        key = argv[i].lstrip("-")
        if key in out and i + 1 < len(argv):
            out[key] = argv[i + 1]
            i += 2
        else:
            i += 1
    return out


def gta_dir(explicit):
    if explicit:
        return explicit
    spec = importlib.util.spec_from_file_location("cfg_game", ROOT / "tools" / "catalog_from_game.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.gta_dir([])


def collect_missing(lib_dir: Path) -> list:
    """Numele .dds pe care bibliotecile le cer, dar care nu sunt impachetate (partea roz)."""
    missing = set()
    for path in sorted(lib_dir.glob("*.blend")):
        with bpy.data.libraries.load(str(path), link=True) as (src, dst):
            dst.images = list(src.images)
        for img in dst.images:
            if img is not None and img.packed_file is None and img.filepath.startswith("//"):
                missing.add(bpy.path.basename(img.filepath))
    return sorted(missing)


def fix_textures(game: str, lib_dir: Path):
    """Texturile din dictionarele comune ale jocului, scrise ca .dds langa biblioteca."""
    names = collect_missing(lib_dir)
    (lib_dir / "missing_textures.txt").write_text("\n".join(names), encoding="utf-8")
    print(f"texturi lipsa in biblioteca: {len(names)}")
    spec = importlib.util.spec_from_file_location("gta_textures", ROOT / "tools" / "gta_textures.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.extract_textures(game, names, str(lib_dir))


def main():
    args = cli_args()
    pkg = setup_sollumz()
    library = importlib.import_module(f"{pkg}.shared.game_assets.library")

    game = gta_dir(args["gta"])
    if not game or not (Path(game) / "GTA5.exe").is_file():
        print(f"EROARE: nu gasesc GTA V ({game}). Da --gta \"<cale>\".")
        return 1

    lib_dir = Path(args["lib"]).resolve() if args["lib"] else ROOT / "output" / "gta_asset_library"
    lib_dir.mkdir(parents=True, exist_ok=True)

    names = None
    if args["pattern"]:
        pattern = args["pattern"]
    elif args["ytyps"]:
        names = [line.strip() for line in Path(args["ytyps"]).read_text(encoding="utf-8").splitlines() if line.strip()]
    elif "--solid" in sys.argv:
        names = solid_ytyps()
        print(f"{len(names)} fisiere .ytyp contin cladiri solide din catalog")
    else:
        print("EROARE: da --ytyps <fisier>, --solid sau --pattern <regex>.")
        return 1

    if names is not None:
        if not names:
            print("EROARE: lista de .ytyp e goala.")
            return 1
        # Incremental: un .ytyp deja construit nu se mai reface (--force il reface).
        if "--force" not in sys.argv:
            built = [n for n in names if (lib_dir / f"_assets.{n}.blend").is_file()]
            names = [n for n in names if n not in built]
            if built:
                print(f"{len(built)} fisiere .ytyp sunt deja in biblioteca")
        pattern = "^(" + "|".join(re.escape(n) for n in names) + ")$" if names else None
        print(f"{len(names)} fisiere .ytyp de construit")

    # Folderul bibliotecii trebuie sa fie in preferintele Sollumz, altfel importul de .ymap nu
    # il gaseste. Profilul e cel izolat din tools\, deci Blender-ul pornit cu BLENDER_EDITOR.bat
    # vede aceeasi setare.
    prefs = bpy.context.preferences.addons[pkg].preferences
    known = {Path(bpy.path.abspath(d.path)).resolve() for d in prefs.shared_assets_directories if d.path}
    if lib_dir not in known:
        bpy.ops.sollumz.prefs_shared_assets_directory_add(name="GTA V (generator)", path=str(lib_dir))
        bpy.context.preferences.is_dirty = True
        bpy.ops.wm.save_userpref()
        print(f"biblioteca adaugata in preferintele Sollumz: {lib_dir}")
    register_asset_library(lib_dir)

    print(f"GTA V: {game}")
    print(f"biblioteca: {lib_dir}")
    print(f"procese paralele: {args['jobs']}  (indexarea jocului dureaza cateva minute)")
    started = time.time()

    def progress(done, total):
        if done is not None:
            print(f"  {done}/{total} biblioteci ({time.time() - started:.0f} s)", flush=True)

    # Operatorul Sollumz porneste aceeasi functie pe un temporizator, care nu ruleaza fara
    # interfata; aici o conducem direct.
    failed = False
    if pattern is None:
        library.build_library_cache([lib_dir])
        print(f"nimic nou; cache reconstruit: {library.asset_cache_path()}")
    else:
        work = library.build_library(Path(game), lib_dir, "GTA5", int(args["jobs"]), pattern, progress)
        try:
            for delay in work:
                time.sleep(min(max(float(delay or 0.0), 0.05), 1.0))
        except Exception as error:
            # un fisier .ytyp stricat nu trebuie sa opreasca texturile si categoriile celorlalte
            import traceback
            traceback.print_exc()
            print(f"EROARE la construirea bibliotecii: {error}")
            failed = True
        blends = sorted(lib_dir.glob("*.blend"))
        print(f"gata in {time.time() - started:.0f} s: {len(blends)} fisiere .blend in {lib_dir}")
        print(f"cache: {library.asset_cache_path()}")

    if "--no-textures" not in sys.argv:
        fix_textures(game, lib_dir)
    # Asset Browser-ul pe categorii (Case, Blocuri, Garduri...) in loc de numele fisierelor din joc
    spec = importlib.util.spec_from_file_location("lib_catalogs", ROOT / "tools" / "blender_library_catalogs.py")
    catalogs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(catalogs)
    catalogs.organize(lib_dir)
    return 1 if failed else 0


if __name__ == "__main__":
    code = 1
    try:
        code = main()
    finally:
        sys.stdout.flush()
    sys.exit(code)
