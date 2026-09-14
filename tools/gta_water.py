# -*- coding: utf-8 -*-
"""Scoate water.xml-ul jocului (din update.rpf daca il are, altfel din common.rpf) in output/gta_water.xml.
Exportul FiveM (blender_fivem_export.py) il ia de acolo, adauga lacurile oraselor (apa la nivelul solului) si il
pune in resursa hartii; clientul il incarca cu LoadWaterFromPath. Cu el apa din joc ramane cea originala.

    python tools/gta_water.py [--gta "E:\\...\\Grand Theft Auto V"]
"""
import os
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS / "pydeps"))
sys.path.insert(0, str(TOOLS))
OUT = TOOLS.parent / "output" / "gta_water.xml"


def extract(argv=()):
    from szio import rpf
    from catalog_from_game import gta_dir
    root = gta_dir(list(argv))
    if not root:
        raise RuntimeError('nu gasesc GTA V: da calea cu --gta "E:\\...\\Grand Theft Auto V"')
    tries = [(os.path.join(root, "update", "update.rpf"), "common/data/levels/gta5/water.xml"),
             (os.path.join(root, "common.rpf"), "data/levels/gta5/water.xml")]
    for top, inner in tries:
        if not os.path.isfile(top):
            continue
        try:
            data = rpf.open_rpf(top).read_bytes(inner)
        except Exception as error:  # noqa: BLE001 - incercam urmatoarea arhiva
            print(f"  nu e in {os.path.basename(top)}/{inner} ({type(error).__name__}: {error})")
            continue
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_bytes(data)
        return f"{os.path.basename(top)}/{inner}"
    raise RuntimeError("water.xml nu e in update.rpf si nici in common.rpf")


if __name__ == "__main__":
    src = extract(sys.argv[1:])
    print(f"APA {src} -> {OUT} ({OUT.stat().st_size} octeti)")
