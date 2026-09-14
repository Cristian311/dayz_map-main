# -*- coding: utf-8 -*-
"""
Props GTA din biblioteca (banci, copaci, tufe, fantani...) puse in scena de generatoare. Fiecare prop e o copie
a obiectului din biblioteca (pastreaza sz_asset_archetype_info), deci la export in FiveM ramane referinta GTA
(cu coliziunea lui), iar in .glb se vede modelul intreg.

    props = runpy.run_path("gta_props.py")
    names = props["load"](["prop_bench_01a", "prop_tree_eng_oak_01"])   # doar cele gasite
    props["place"](colectie, "prop_bench_01a", x, y, z_sol, rotire_z)
"""
import json
import math
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / "output" / "gta_asset_library"
INDEX = LIB / "_props_index.json"
_templates = {}


def _index(names):
    """{nume prop: fisier .blend}; cautarea prin biblioteca se face o data si se tine minte."""
    cache = {}
    try:
        cache = json.loads(INDEX.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cache = {}
    files = sorted(str(p) for p in LIB.glob("_assets.*.blend"))
    wanted = set(names)
    if cache.get("files") != len(files) or not wanted <= set(cache.get("seen", [])):
        found = dict(cache.get("props", {})) if cache.get("files") == len(files) else {}
        missing = wanted - set(found)
        # fisierele de props (v_*) intai: acolo sunt aproape toate
        for path in sorted(files, key=lambda p: not Path(p).name.startswith("_assets.v_")):
            if not missing:
                break
            with bpy.data.libraries.load(path) as (src, _dst):
                for n in src.objects:
                    if n in missing:
                        found[n] = path
                        missing.discard(n)
        seen = sorted(wanted | set(cache.get("seen", []))) if cache.get("files") == len(files) else sorted(wanted)
        cache = {"files": len(files), "seen": seen, "props": found}
        INDEX.write_text(json.dumps(cache, indent=1), encoding="utf-8")
    return cache.get("props", {})


def load(names):
    """Aduce sabloanele (neasezate in scena); intoarce numele gasite, in ordinea ceruta."""
    index = _index(names)
    by_file = {}
    for n in names:
        if n in index and n not in _templates:
            by_file.setdefault(index[n], []).append(n)
    for path, group in by_file.items():
        try:
            with bpy.data.libraries.load(path, link=False) as (_src, dst):
                dst.objects = list(group)   # Blender inlocuieste continutul listei cu obiectele aduse
        except Exception as error:
            print(f"[props] nu s-au putut aduce din {Path(path).name}: {error}")
            continue
        for n, obj in zip(group, dst.objects):
            if obj is not None:
                _templates[n] = obj
    return [n for n in names if n in _templates]


def place(coll, name, x, y, z, rot_z=0.0):
    """O copie a propului cu originea pe sol la (x, y, z), rotita in jurul lui Z. Originea props-urilor GTA e
    la nivelul solului (copacii si tufele au radacini sub ea), deci nu se aseaza dupa cutia lor."""
    obj = _templates[name].copy()
    coll.objects.link(obj)
    obj.location = (x, y, z)
    obj.rotation_euler = (0.0, 0.0, rot_z)
    return obj


def facing(name):
    """Unghiul (radiani, fata de +X) spre care priveste propul: de la varfurile cele mai inalte (spatarul unei
    banci) spre mijlocul cutiei, rotunjit la axe."""
    tmpl = _templates[name]
    verts = [v.co for v in tmpl.data.vertices]
    if not verts:
        return 0.0
    top = max(v.z for v in verts)
    back = [v for v in verts if v.z > top * 0.8]
    bb = tmpl.bound_box
    dx = (min(c[0] for c in bb) + max(c[0] for c in bb)) / 2 - sum(v.x for v in back) / len(back)
    dy = (min(c[1] for c in bb) + max(c[1] for c in bb)) / 2 - sum(v.y for v in back) / len(back)
    if abs(dy) >= abs(dx):
        return math.pi / 2 if dy > 0 else -math.pi / 2
    return 0.0 if dx > 0 else math.pi


def size(name):
    """(latime x, adancime y, inaltime) a propului, in m."""
    return tuple(_templates[name].dimensions)
