# -*- coding: utf-8 -*-
"""
Catalogul de arhetipuri vanilla: scrie lista de candidati pentru scanerul din joc si
transforma masuratorile primite de la joc in `dayzgen/data/catalog.json`.

Nu are nevoie de Blender. Ruleaza cu Python-ul de sistem.

    python make_catalog.py                 # candidates.json (daca lipseste) + merge measurements -> catalog.json
    python make_catalog.py --candidates    # doar rescrie candidates.json
    python make_catalog.py --stats         # ce are catalogul acum
    python make_catalog.py --reclassify    # re-aplica regulile de categorie peste tot
    python make_catalog.py --block nume1 nume2 ...     # pune modele pe lista neagra
    python make_catalog.py --tag nume cat[ stil]       # eticheteaza manual un model

Pasii, pe scurt:
 1. aici: `python make_catalog.py --candidates`
 2. in joc (admin nivel 5): `/catalogscan`  -> dureaza, scrie dayzgen/data/measurements.json
 3. aici (sau automat la finalul scanarii): `python make_catalog.py` -> catalog.json
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dayzgen.city import catalog as C            # noqa: E402
from dayzgen.city import seed_names              # noqa: E402

MEASUREMENTS_PATH = os.path.join(C.DATA_DIR, "measurements.json")


def read_measurements(path: str = MEASUREMENTS_PATH) -> list:
    if not os.path.isfile(path):
        return []
    with open(path, "r", encoding="utf-8") as handle:
        raw = json.load(handle)
    items = raw if isinstance(raw, list) else (raw.get("measurements") or [])
    out = []
    for entry in items:
        name = str(entry.get("name", "")).strip().lower()
        mn = entry.get("min")
        mx = entry.get("max")
        if not name or not isinstance(mn, list) or not isinstance(mx, list):
            continue
        if len(mn) < 3 or len(mx) < 3:
            continue
        out.append((name, mn[:3], mx[:3]))
    return out


def read_verified(path: str = MEASUREMENTS_PATH) -> list:
    """Numele confirmate in joc de /catalogscan (cladirile deja masurate din fisiere)."""
    if not os.path.isfile(path):
        return []
    with open(path, "r", encoding="utf-8") as handle:
        raw = json.load(handle)
    names = raw.get("verified") if isinstance(raw, dict) else None
    return [str(n).strip().lower() for n in (names or []) if str(n).strip()]


def copy_to_resource(path: str):
    """Copie a listei in resursa mapeditor, ca serverul s-o gaseasca oricum."""
    import shutil
    try:
        from dayzgen import config as MC
        map_json = os.path.join(os.path.dirname(os.path.abspath(__file__)), "map.json")
        cfg = MC.MapConfig.from_json(map_json) if os.path.isfile(map_json) else MC.MapConfig()
        resource = os.path.join(cfg.fivem_resources_dir, "mapeditor")
        if not os.path.isdir(resource):
            return None
        target_dir = os.path.join(resource, "catalog")
        os.makedirs(target_dir, exist_ok=True)
        target = os.path.join(target_dir, "candidates.json")
        shutil.copyfile(path, target)
        return target
    except Exception as error:
        print(f"  (nu am putut copia lista in resursa: {error})")
        return None


def do_candidates() -> None:
    path = seed_names.write_spec()
    spec = json.load(open(path, "r", encoding="utf-8"))
    print(f"candidates.json scris: {path}")
    copy = copy_to_resource(path)
    if copy:
        print(f"  copie pentru server: {copy}")
    print(f"  de confirmat  : {len(spec.get('verify', []))} cladiri din catalog")
    print(f"  nume literale : {len(spec['literal'])}")
    print(f"  combinatii    : ~{spec['estimate']:,}".replace(",", "."))
    lists = seed_names.load_namelists()
    if lists:
        print(f"  din namelists/: {len(lists)} nume")
    else:
        print(f"  (poti pune liste de nume in {seed_names.NAMELIST_DIR}, o linie per model)")
    print("Acum in joc: /catalogscan")


def do_merge() -> None:
    measurements = read_measurements()
    verified = read_verified()
    if not measurements and not verified:
        print(f"Nu exista masuratori in {MEASUREMENTS_PATH}.")
        print("Ruleaza /catalogscan in joc mai intai (sau /catalog <model> pentru unul singur).")
        return

    cat = C.Catalog.load()
    before = len(cat)
    for name, mn, mx in measurements:
        cat.add_measurement(name, mn, mx)
    confirmed = 0
    for name in verified:
        if name in cat and not cat[name].verified:
            cat[name].verified = True
            confirmed += 1
    path = cat.save()

    stats = cat.stats()
    print(f"catalog.json scris: {path}")
    print(f"  arhetipuri: {len(cat)} (+{len(cat) - before} noi), confirmate in joc acum: {confirmed}")
    for key in C.CATEGORIES:
        if stats.get(key):
            print(f"  {key:10s}: {stats[key]}")
    if stats.get("blocked"):
        print(f"  blocate   : {stats['blocked']}")


def do_stats() -> None:
    cat = C.Catalog.load()
    if not len(cat):
        return print("Catalogul e gol.")
    stats = cat.stats()
    print(f"{len(cat)} arhetipuri, {stats['verified']} masurate in joc, {stats['blocked']} blocate")
    for key in C.CATEGORIES:
        items = cat.by_category(key)
        if not items:
            continue
        smallest = min(items, key=lambda a: a.footprint)
        largest = max(items, key=lambda a: a.footprint)
        print(f"  {key:10s}: {len(items):4d}  amprenta {smallest.sx:.0f}x{smallest.sy:.0f} .. "
              f"{largest.sx:.0f}x{largest.sy:.0f} m")


def do_reclassify() -> None:
    cat = C.Catalog.load()
    changed = cat.reclassify(only_unknown=False)
    cat.save()
    print(f"Reclasificate {changed} arhetipuri.")


def do_block(names) -> None:
    cat = C.Catalog.load()
    hit = 0
    for name in names:
        key = str(name).strip().lower()
        if key in cat:
            cat[key].blocked = True
            hit += 1
        else:
            print(f"  necunoscut: {key}")
    cat.save()
    print(f"{hit} modele blocate.")


def do_tag(args) -> None:
    if len(args) < 2:
        return print("Foloseste: --tag <model> <categorie> [stil]")
    name = args[0].strip().lower()
    category = args[1].strip().lower()
    style = args[2].strip().lower() if len(args) > 2 else None
    if category not in C.CATEGORIES:
        return print(f"Categorii valide: {', '.join(C.CATEGORIES)}")
    if style and style not in C.STYLES:
        return print(f"Stiluri valide: {', '.join(C.STYLES)}")

    cat = C.Catalog.load()
    if name not in cat:
        return print(f"{name} nu e in catalog. Ruleaza /catalog {name} in joc mai intai.")
    cat[name].category = category
    if style:
        cat[name].style = style
    cat.save()
    print(f"{name} -> {category}{' / ' + style if style else ''}")


def main(argv) -> int:
    args = list(argv)
    if "--candidates" in args:
        do_candidates()
        return 0
    if "--stats" in args:
        do_stats()
        return 0
    if "--reclassify" in args:
        do_reclassify()
        return 0
    if "--block" in args:
        do_block(args[args.index("--block") + 1:])
        return 0
    if "--tag" in args:
        do_tag(args[args.index("--tag") + 1:])
        return 0

    if not os.path.isfile(C.CANDIDATES_PATH):
        do_candidates()
        print()
    do_merge()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
