# -*- coding: utf-8 -*-
"""
Texturile GTA V pe care Sollumz nu le gaseste cand construieste biblioteca (partea roz din Blender).

Cladirile de harta isi iau o parte din texturi din dictionare comune ("parinte"), legate in
manifestele zonelor, intr-un format binar (PSO) pe care nu il citim. In loc sa urmarim
legaturile, cautam texturile lipsa dupa nume in toate .ytd-urile jocului, incepand cu zonele de
oras, si le scriem ca .dds langa biblioteca: Blender le cauta exact acolo (cale relativa //nume.dds).

    python tools\\gta_textures.py        citeste output\\gta_asset_library\\missing_textures.txt

Pasul ruleaza si singur la finalul tools\\blender_build_library.py.
"""
import glob
import importlib.util
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools", "pydeps"))
DEFAULT_LIB = os.path.join(ROOT, "output", "gta_asset_library")


def _game_tool():
    spec = importlib.util.spec_from_file_location("cfg_game", os.path.join(ROOT, "tools", "catalog_from_game.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def ytd_paths(game_dir: str, tool) -> list:
    """Toate .ytd-urile jocului, cele din zonele de oras primele."""
    from szio import rpf, vfs
    city, rest = [], []
    tops = sorted(glob.glob(os.path.join(game_dir, "x64*.rpf")))
    update = os.path.join(game_dir, "update", "update.rpf")
    if os.path.isfile(update):
        tops.append(update)
    for top in tops:
        try:
            archive = rpf.open_rpf(top)
        except Exception:
            continue
        for parts, path in tool.iter_files(archive, [], (".ytd",)):
            (city if tool.wanted_area(parts, path, tool.DEFAULT_AREAS) else rest).append((top, parts, path))
        vfs.clear_archive_cache()
    return city + rest


def extract_textures(game_dir: str, names, out_dir: str, log=print):
    """Scrie in `out_dir` fiecare textura `<nume>.dds` ceruta. Intoarce (gasite, ramase)."""
    import szio
    from szio import vfs
    tool = _game_tool()
    wanted = {str(n).strip().lower() for n in names if str(n).strip()}
    wanted -= {os.path.basename(p).lower() for p in glob.glob(os.path.join(out_dir, "*.dds"))}
    # Numele negasite o data nu mai sunt cautate: un singur nume inexistent ar forta de fiecare
    # data parcurgerea tuturor dictionarelor jocului (cateva minute).
    not_found_path = os.path.join(out_dir, "textures_not_found.txt")
    not_found = set()
    if os.path.isfile(not_found_path):
        with open(not_found_path, "r", encoding="utf-8") as handle:
            not_found = {line.strip().lower() for line in handle if line.strip()}
    wanted -= not_found
    if not wanted:
        log("texturi: nimic de extras")
        return 0, 0

    total = len(wanted)
    t0 = time.time()
    paths = ytd_paths(game_dir, tool)
    log(f"texturi: caut {total} in {len(paths)} dictionare .ytd")
    for n, (top, parts, path) in enumerate(paths):
        try:
            txd = szio.try_load_asset(vfs.VPath(top, *parts, path))
        except Exception:
            txd = None
        for name, tex in (getattr(txd, "textures", None) or {}).items():
            data = getattr(tex, "data", None)
            fname = str(getattr(data, "name", "") or f"{name}.dds").lower()
            if not fname.endswith(".dds"):
                fname += ".dds"
            if fname not in wanted:
                continue
            try:
                raw = data.read_bytes()
            except Exception:
                continue
            with open(os.path.join(out_dir, fname), "wb") as handle:
                handle.write(raw)
            wanted.discard(fname)
        if not wanted:
            break
        if (n + 1) % 250 == 0:
            vfs.clear_archive_cache()
            log(f"  {n + 1}/{len(paths)} dictionare, gasite {total - len(wanted)}/{total} ({time.time() - t0:.0f} s)")

    found = total - len(wanted)
    if wanted:
        with open(not_found_path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(sorted(not_found | wanted)) + "\n")
    log(f"texturi: {found}/{total} extrase in {out_dir} ({time.time() - t0:.0f} s)")
    return found, len(wanted)


def main(argv) -> int:
    tool = _game_tool()
    tool.ensure_pymateria(__file__)
    lib = argv[argv.index("--lib") + 1] if "--lib" in argv else DEFAULT_LIB
    listing = os.path.join(lib, "missing_textures.txt")
    if not os.path.isfile(listing):
        print(f"Lipseste {listing} (se scrie la finalul BIBLIOTECA_GTA.bat).")
        return 1
    with open(listing, "r", encoding="utf-8") as handle:
        names = handle.read().splitlines()
    game = tool.gta_dir(argv)
    if not game:
        print("Nu gasesc GTA V (--gta \"<cale>\").")
        return 1
    extract_textures(game, names, lib)
    return 0


if __name__ == "__main__":
    exit_code = main(sys.argv[1:])
    sys.stdout.flush()
    os._exit(exit_code)
