# -*- coding: utf-8 -*-
"""
Construieste catalogul de arhetipuri direct din fisierele GTA V, fara CodeWalker si fara
scanare in joc.

Citeste arhivele .rpf ale jocului cu `szio` (deja in tools\\pydeps), gaseste toate
fisierele .ytyp (definitiile de arhetip), si pune in `dayzgen/data/catalog.json` numele
exact si cutia exacta a fiecarei cladiri.

`szio` citeste arhivele criptate RPF7 doar cu modulul nativ `pymateria`, compilat pentru
Python 3.13 - adica Python-ul din Blender. Scriptul se re-lanseaza singur cu el daca e nevoie.

    python tools\\catalog_from_game.py                  toate zonele de oras (_citye, _cityw)
    python tools\\catalog_from_game.py --all            toata harta (dureaza mai mult)
    python tools\\catalog_from_game.py --area _citye    doar o zona
    python tools\\catalog_from_game.py --gta "E:\\...\\Grand Theft Auto V"
    python tools\\catalog_from_game.py --fresh          sterge catalogul vechi inainte (pastreaza nimic)

Doua lucruri de stiut despre datele reale:

1. Rockstar imparte fiecare cvartal in zeci de arhetipuri: placa de sol, bucati de drum,
   overlay-uri, detalii, semne, cabluri, scari, parapete. Majoritatea NU sunt cladiri care
   pot sta singure pe un lot. Filtrul de mai jos le taie dupa bucatile din nume.
2. Cladirile de harta NU au coliziune proprie: coliziunea lor e in .ybn-ul static al zonei
   originale din Los Santos. Mutate pe alta harta, se vad dar nu sunt solide. Arhetipurile
   care au totusi `physicsDictionary` primesc eticheta `phys` in catalog. Restul au nevoie
   de coliziune coapta in .ybn-ul tile-ului (faza C a planului).

Arhetipurile importate au `ok` = false: stim ca exista si ce cutie au, dar nu stim inca daca
se incarca oriunde pe harta. Dupa import, `/catalogscan` in joc le verifica si le marcheaza.
"""
from __future__ import annotations

import configparser
import glob
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PYDEPS = os.path.join(ROOT, "tools", "pydeps")
sys.path.insert(0, ROOT)
sys.path.insert(0, PYDEPS)

DEFAULT_AREAS = ("_citye", "_cityw")

# Bucati din nume (separate de "_", fara cifrele de la coada) care tradeaza o piesa de
# cladire / infrastructura, nu o cladire intreaga. Exemple reale din joc: vb_05_grnd5,
# hw1_rd_04_03, dt1_23_ov2, sm_11_bld4_det2, vb_38_build02_em, ap1_01_c_sthbld3_int.
SKIP_TOKENS = frozenset((
    "lod", "slod", "superlod", "proxy",
    "em", "emit", "emis", "emiss", "emissive", "night", "light", "lights", "neon", "lamp", "lamps",
    "decal", "decals", "shadow", "shad", "occl", "ref", "iref", "glue",
    "det", "dets", "detail", "details", "dtl", "ov", "ovly", "overlay", "int", "interior",
    "rd", "road", "roads", "fwy", "sign", "signs", "fwysign", "billboard", "bb",
    "cable", "cables", "cablemesh", "wire", "wires", "pylon", "pole", "poles",
    "grnd", "gnd", "ground", "land", "terrain", "sidewalk", "pavement", "kerb", "curb",
    "stair", "stairs", "step", "steps", "ramp", "tunnel", "bridge", "rail", "rails",
    "track", "tracks", "barrier", "barriers",
    "glass", "railing", "railings", "hanging", "hangings", "roof", "roofs", "roofover",
    "fence", "fences", "fnc", "wall", "walls", "pipe", "pipes",
    "rock", "rocks", "rubble", "debris", "water", "weed", "weeds", "grass",
    "tree", "trees", "bush", "bushes", "shrub", "shrubs", "hedge", "hedges",
    "flower", "flowers", "plant", "plants", "planter", "props", "prop",
    "sculpt", "statue",
    # scapate de filtrul LOD pe datele reale (2026-09-11)
    "ladder", "ladders", "triladders", "wyre", "ship", "shipa", "boat", "tnl", "tnlsec", "hdg",
    "sig", "frame", "emd", "crane", "graff", "armco", "trelis", "trellis", "antena", "antenna",
    "aerial", "aeriala", "aerialb", "radar", "fizz", "fizzing", "dcl", "dcls", "prox", "refprox",
    "bal", "perim", "dec", "text", "texts", "wash", "lines",
    # scapate dupa ce am permis si modelele fara LOD propriu (2026-09-11)
    "reflect", "shell", "jumptest", "test", "fur", "furniture", "rv", "ctr",
))

# Cuvinte lipite fara "_" (ex. seoulstepsextrasint, cablemesh9354).
SKIP_SUBSTRINGS = ("cablemesh", "fwysign", "billboard", "roofover", "superlod", "slod",
                   "_lod", "emissive", "railing", "stairs", "steps", "fence", "hedge",
                   "decal", "shadow", "ladder", "graff", "aerial", "antenna", "antena", "fizz",
                   "refprox", "trelis", "trellis", "washline",
                   # vazute in prima randare cu modele solide (2026-09-11)
                   "crate", "scaf", "walkway", "fountain", "lguard", "bathroom", "_fake", "carparkentr",
                   # suprafete plate (iarba, umbre, reflexii, apa) si obiecte care nu sunt cladiri
                   "grass", "gfur", "fur_", "iref", "shad", "shdw", "shdb", "pool", "canopy",
                   "pergola", "shipint", "blimp", "proxy", "reflec")

# Zone de harta care sunt numai infrastructura.
SKIP_AREAS = frozenset(("fwy", "rd", "rail", "tunnel", "bridge", "marina"))


# ---------------------------------------------------------------------- mediu

def blender_python():
    """python.exe-ul din Blender (3.13, compatibil cu pymateria)."""
    hint = os.path.join(ROOT, "tools", "blender_path.txt")
    candidates = []
    if os.path.isfile(hint):
        with open(hint, "r", encoding="utf-8") as handle:
            exe = handle.read().strip().strip('"')
        if exe:
            base = os.path.dirname(exe)
            candidates += glob.glob(os.path.join(base, "*", "python", "bin", "python.exe"))
    for pf in (os.environ.get("ProgramFiles", r"C:\Program Files"),
               os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")):
        candidates += sorted(glob.glob(os.path.join(pf, "Blender Foundation", "*", "*",
                                                    "python", "bin", "python.exe")), reverse=True)
    for exe in candidates:
        if os.path.isfile(exe):
            return exe
    return None


def ensure_pymateria(script=None):
    """Daca Python-ul curent nu poate citi RPF7, re-lansam `script` (implicit acesta) cu cel din Blender."""
    try:
        import pymateria  # noqa: F401
        return
    except Exception:
        pass
    if os.environ.get("DZ_RELAUNCHED") == "1":
        print("EROARE: pymateria nu se incarca nici cu Python-ul din Blender.")
        raise SystemExit(2)
    exe = blender_python()
    if not exe:
        print("EROARE: nu gasesc Python-ul din Blender. Scrie calea catre blender.exe in "
              "tools\\blender_path.txt.")
        raise SystemExit(2)
    print(f"(re-lansez cu {exe})", flush=True)
    env = dict(os.environ, DZ_RELAUNCHED="1")
    code = subprocess.call([exe, os.path.abspath(script or __file__)] + sys.argv[1:], env=env)
    raise SystemExit(code)


def gta_dir(argv):
    if "--gta" in argv:
        index = argv.index("--gta")
        if index + 1 < len(argv):
            return argv[index + 1]
    env = os.environ.get("GTA_DIR")
    if env and os.path.isdir(env):
        return env
    # FiveM tine calea jocului in CitizenFX.ini
    local = os.environ.get("LOCALAPPDATA", "")
    for ini in (os.path.join(local, "FiveM", "FiveM.app", "CitizenFX.ini"),
                os.path.join(local, "FiveM", "CitizenFX.ini")):
        if os.path.isfile(ini):
            parser = configparser.ConfigParser()
            try:
                parser.read(ini, encoding="utf-8")
                path = parser.get("Game", "IVPath", fallback="").strip()
            except (configparser.Error, UnicodeDecodeError):
                path = ""
            if path and os.path.isdir(path):
                return path
    return None


# ---------------------------------------------------------------------- parcurgere

def iter_ytyp(archive, parts, inner="", depth=0, max_depth=6):
    """(parts_arhive_imbricate, nume_fisier) pentru fiecare .ytyp, recursiv prin .rpf imbricate."""
    yield from iter_files(archive, parts, (".ytyp",), inner, depth, max_depth)


def iter_files(archive, parts, suffixes, inner="", depth=0, max_depth=6):
    """(parts_arhive_imbricate, cale) pentru fiecare fisier cu una din extensiile date, recursiv."""
    try:
        entries = list(archive.list_dir(inner))
    except Exception:
        return
    for name in entries:
        path = f"{inner}/{name}" if inner else name
        low = name.lower()
        if low.endswith(suffixes):
            yield parts, path
        elif low.endswith(".rpf"):
            if depth >= max_depth:
                continue
            try:
                nested = archive.open_nested(path)
            except Exception:
                nested = None
            if nested is not None:
                yield from iter_files(nested, parts + [path], suffixes, "", depth + 1, max_depth)
        else:
            try:
                is_dir = archive.is_dir(path)
            except Exception:
                is_dir = False
            if is_dir:
                yield from iter_files(archive, parts, suffixes, path, depth, max_depth)


def wanted_area(parts, path, areas):
    if not areas:
        return True
    text = "/".join(parts + [path]).lower()
    return any(area.lower() in text for area in areas)


def is_building_name(name: str) -> bool:
    """True daca numele arata a cladire intreaga, nu a piesa / infrastructura."""
    low = name.lower()
    if low.startswith(("prop_", "p_", "v_")):
        return False     # mobilierul urban are deja lista lui (seed_names.URBAN_PROPS)
    if any(part in low for part in SKIP_SUBSTRINGS):
        return False
    tokens = low.split("_")
    if tokens and tokens[0].rstrip("0123456789") in SKIP_AREAS:
        return False
    for token in tokens[1:]:
        core = token.rstrip("0123456789")
        if token in SKIP_TOKENS or core in SKIP_TOKENS:
            return False
    return True


# ---------------------------------------------------------------------- main

def prune_catalog() -> int:
    """Scoate din catalogul existent ce nu mai trece de filtrul de nume; pastreaza etichetele."""
    from dayzgen.city import catalog as C
    cat = C.Catalog.load(required=True)
    # Fisierele de interioare (.ytyp cu "interior" in nume) definesc piese de interior si
    # cochilii, nu cladiri de pus pe lot.
    drop = [name for name, arch in cat.items.items()
            if not is_building_name(name)
            or any(t.startswith("ytyp:") and "interior" in t for t in arch.tags)]
    for name in drop:
        del cat.items[name]
    cat.save()
    print(f"scoase {len(drop)} bucati dupa filtrul actualizat; raman {len(cat)}")
    return 0


def main(argv) -> int:
    if "--prune" in argv:
        return prune_catalog()
    ensure_pymateria()
    import szio
    from szio import rpf, vfs
    from dayzgen.city import catalog as C

    root = gta_dir(argv)
    if not root:
        print("Nu gasesc GTA V. Da calea cu --gta \"E:\\...\\Grand Theft Auto V\".")
        return 1

    if "--all" in argv:
        areas = ()
    elif "--area" in argv:
        index = argv.index("--area")
        areas = (argv[index + 1],) if index + 1 < len(argv) else DEFAULT_AREAS
    else:
        areas = DEFAULT_AREAS

    min_side = 4.0
    max_side = 160.0
    tops = sorted(glob.glob(os.path.join(root, "x64*.rpf")))
    update = os.path.join(root, "update", "update.rpf")
    if os.path.isfile(update):
        tops.append(update)
    print(f"GTA V: {root}")
    print(f"zone: {', '.join(areas) if areas else 'toata harta'}; {len(tops)} arhive de top")

    if "--fresh" in argv and os.path.isfile(C.CATALOG_PATH):
        os.remove(C.CATALOG_PATH)
        print("catalogul vechi a fost sters (--fresh)")

    cat = C.Catalog.load()
    before = len(cat)
    t0 = time.time()
    files = 0
    seen = 0
    kept = 0
    with_phys = 0
    all_names = set()     # toate arhetipurile vazute, inclusiv LOD-urile, pentru eticheta `haslod`
    skipped_name = 0
    skipped_size = 0
    errors = 0

    for top in tops:
        try:
            archive = rpf.open_rpf(top)
        except Exception as error:
            print(f"  ! {os.path.basename(top)}: {type(error).__name__}")
            continue
        top_files = 0
        for parts, path in iter_ytyp(archive, []):
            if not wanted_area(parts, path, areas):
                continue
            if "interior" in os.path.basename(path).lower():
                continue  # piese de interior si cochilii, nu cladiri

            try:
                types = szio.try_load_asset(vfs.VPath(top, *parts, path))
            except Exception:
                types = None
            if types is None or not hasattr(types, "archetypes"):
                errors += 1
                continue
            files += 1
            top_files += 1
            ytyp_name = os.path.splitext(os.path.basename(path))[0]
            for arch in types.archetypes:
                seen += 1
                raw_name = str(getattr(arch, "name", "") or "").strip().lower()
                if raw_name:
                    all_names.add(raw_name)
                kind = str(getattr(arch, "type", ""))
                if "MLO" in kind.upper():
                    continue
                name = str(getattr(arch, "name", "") or "").strip().lower()
                if not name or not is_building_name(name):
                    skipped_name += 1
                    continue
                try:
                    mn = [float(v) for v in arch.bb_min]
                    mx = [float(v) for v in arch.bb_max]
                except Exception:
                    continue
                sx, sy, sz = mx[0] - mn[0], mx[1] - mn[1], mx[2] - mn[2]
                # O cladire are si latime si adancime; o placa de 100 x 100 x 3 m e sol/drum.
                if (max(sx, sy) < min_side or min(sx, sy) < 2.5 or sz < 3.0
                        or max(sx, sy, sz) > max_side or sz < 0.06 * max(sx, sy)):
                    skipped_size += 1
                    continue
                entry = cat.add_measurement(name, mn, mx, float(getattr(arch, "lod_dist", 0.0) or 0.0),
                                            verified=None)
                tags = [f"ytyp:{ytyp_name}"]
                if str(getattr(arch, "physics_dictionary", "") or "").strip():
                    tags.append("phys")
                    with_phys += 1
                entry.tags = tuple(entry.tags) + tuple(t for t in tags if t not in entry.tags)
                kept += 1
        if top_files:
            print(f"  {os.path.basename(top)}: {top_files} fisiere .ytyp "
                  f"({kept} cladiri pana acum, {time.time() - t0:.0f} s)", flush=True)
        vfs.clear_archive_cache()

    # Cladirile intregi au aproape mereu un LOD propriu (<nume>_lod). Detaliile, overlay-urile si
    # decalurile nu. E cel mai bun semnal pe care il avem fara sa citim .ymap-urile zonei.
    with_lod = 0
    for entry in cat.items.values():
        if f"{entry.name}_lod" in all_names:
            with_lod += 1
            if "haslod" not in entry.tags:
                entry.tags = tuple(entry.tags) + ("haslod",)

    path = cat.save()
    stats = cat.stats()
    print()
    print(f"catalog.json scris: {path}")
    print(f"  cu LOD propriu (haslod, probabil cladiri intregi): {with_lod}")
    print(f"  .ytyp citite {files} (erori {errors}), arhetipuri vazute {seen}")
    print(f"  pastrate {kept}; ignorate: piese/LOD/props {skipped_name}, dimensiuni {skipped_size}")
    print(f"  cu coliziune proprie (phys): {with_phys} din {kept}")
    print(f"  total in catalog: {len(cat)} (+{len(cat) - before} noi)")
    for key in C.CATEGORIES:
        if stats.get(key):
            print(f"  {key:10s}: {stats[key]}")
    print(f"  durata: {time.time() - t0:.0f} s")
    print()
    print("Urmatorul pas: python make_catalog.py --candidates, apoi /catalogscan in joc")
    print("(verifica ce arhetipuri se incarca oriunde pe harta si le marcheaza ok).")
    return 0


if __name__ == "__main__":
    code = main(sys.argv[1:])
    sys.stdout.flush()
    # os._exit evita avertismentele de "leaked function" ale lui nanobind la inchidere.
    os._exit(code)
