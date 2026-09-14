# -*- coding: utf-8 -*-
"""
Importa arhetipuri in catalog din XML-uri de .ytyp exportate cu CodeWalker.

Asta e calea "de lux": numele sunt exacte si cutiile vin direct din fisiere, deci nu mai
e nevoie de scanarea din joc. In schimb ai nevoie de CodeWalker si de GTA V instalat.

Cum obtii XML-urile:
 1. deschide CodeWalker -> RPF Explorer;
 2. caseta de search: `.ytyp`  (sau intra in x64a.rpf\\levels\\gta5\\..., update\\update.rpf\\...);
 3. selecteaza fisierele .ytyp care te interesteaza (cele din `_citye`, `_cityw`, `_cityne`,
    `_countryside` etc. contin cladirile) -> click dreapta -> Export XML;
 4. ruleaza: python tools\\import_ytyp_xml.py C:\\cale\\catre\\folderul_cu_xml

Se pot da mai multe foldere/fisiere. Se citeste recursiv.

    python tools\\import_ytyp_xml.py D:\\ytyp_xml
    python tools\\import_ytyp_xml.py D:\\ytyp_xml --min 4 --max 120
"""
from __future__ import annotations

import glob
import os
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dayzgen.city import catalog as C  # noqa: E402

# Arhetipurile de tip MLO (interioare) si LOD-urile nu ne interesteaza ca cladiri.
SKIP_SUFFIXES = ("_lod", "_slod", "_slod1", "_slod2", "_slod3", "_slod4", "_lod1", "_lod2")


def _float_attr(node, name: str, fallback: float = 0.0) -> float:
    if node is None:
        return fallback
    raw = node.get(name)
    if raw is None:
        raw = node.text
    try:
        return float(raw)
    except (TypeError, ValueError):
        return fallback


def _vec(parent, tag: str):
    node = parent.find(tag)
    if node is None:
        return None
    return (_float_attr(node, "x"), _float_attr(node, "y"), _float_attr(node, "z"))


def parse_ytyp(path: str) -> list:
    """Intoarce [(nume, bb_min, bb_max, lod_dist)] dintr-un XML de .ytyp."""
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as error:
        print(f"  ! {os.path.basename(path)}: XML invalid ({error})")
        return []

    out = []
    for item in root.iter("Item"):
        # Arhetipurile normale au type="CBaseArchetypeDef"; MLO-urile CMloArchetypeDef.
        kind = item.get("type") or ""
        if kind and "Mlo" in kind:
            continue

        name_node = item.find("name")
        if name_node is None:
            continue
        name = (name_node.get("value") or name_node.text or "").strip().lower()
        if not name or len(name) > 64:
            continue
        if name.endswith(SKIP_SUFFIXES):
            continue

        bb_min = _vec(item, "bbMin")
        bb_max = _vec(item, "bbMax")
        if bb_min is None or bb_max is None:
            continue
        out.append((name, bb_min, bb_max, _float_attr(item.find("lodDist"), "value", 0.0)))
    return out


def collect(paths) -> list:
    files = []
    for target in paths:
        if os.path.isdir(target):
            files.extend(sorted(glob.glob(os.path.join(target, "**", "*.xml"), recursive=True)))
            files.extend(sorted(glob.glob(os.path.join(target, "**", "*.ytyp.xml"), recursive=True)))
        elif os.path.isfile(target):
            files.append(target)
        else:
            print(f"  ! nu exista: {target}")
    seen = set()
    unique = []
    for path in files:
        key = os.path.normcase(os.path.abspath(path))
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def main(argv) -> int:
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 1

    def opt(flag, fallback):
        if flag in argv:
            index = argv.index(flag)
            if index + 1 < len(argv):
                try:
                    return float(argv[index + 1])
                except ValueError:
                    pass
        return fallback

    min_side = opt("--min", 3.0)
    max_side = opt("--max", 150.0)

    files = collect(args)
    if not files:
        print("Nu am gasit niciun XML.")
        return 1
    print(f"{len(files)} fisiere XML.")

    cat = C.Catalog.load()
    before = len(cat)
    seen = 0
    added = 0
    skipped = 0

    for path in files:
        entries = parse_ytyp(path)
        seen += len(entries)
        for name, bb_min, bb_max, lod in entries:
            sx = abs(bb_max[0] - bb_min[0])
            sy = abs(bb_max[1] - bb_min[1])
            sz = abs(bb_max[2] - bb_min[2])
            if max(sx, sy) < min_side or sz < 1.0 or max(sx, sy, sz) > max_side:
                skipped += 1
                continue
            cat.add_measurement(name, bb_min, bb_max, lod)
            added += 1
        print(f"  {os.path.basename(path)}: {len(entries)} arhetipuri")

    path = cat.save()
    print()
    print(f"catalog.json scris: {path}")
    print(f"  citite {seen}, pastrate {added}, ignorate dupa dimensiuni {skipped}")
    print(f"  total in catalog: {len(cat)} (+{len(cat) - before} noi)")
    stats = cat.stats()
    for key in C.CATEGORIES:
        if stats.get(key):
            print(f"  {key:10s}: {stats[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
