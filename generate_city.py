# -*- coding: utf-8 -*-
"""
Genereaza un oras complet, fara Blender: teren, strazi, zone, loturi si cladiri vanilla GTA V.

    python generate_city.py                       map.json (orasul e pornit automat)
    python generate_city.py --preset demo --radius 280 --seed 7

Scrie in output\\<nume>_oras\\:
    <nume>_city.ymap   cladirile, in coordonate de lume: pentru joc si pentru importul in Blender
    plan.json          loturile si cladirile
    terrain.npz        relieful, strazile si zonele, pentru scena din Blender
    ytyps.txt          fisierele .ytyp folosite (biblioteca Blender se construieste doar pentru ele)
    preview.png        harta 2D cu amprentele cladirilor

Scrierea .ymap cere modulul nativ pymateria (Python-ul din Blender); scriptul se re-lanseaza
singur cu el. Apoi: BIBLIOTECA_GTA.bat (o data) si BLENDER_EDITOR.bat.
"""
import importlib.util
import json
import math
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "tools", "pydeps"))


def _load(relative: str):
    path = os.path.join(HERE, *relative.split("/")) + ".py"
    spec = importlib.util.spec_from_file_location(relative.replace("/", "_"), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def ensure_pymateria():
    try:
        import pymateria  # noqa: F401
        return
    except Exception:
        pass
    if os.environ.get("DZ_RELAUNCHED") == "1":
        print("EROARE: pymateria nu se incarca nici cu Python-ul din Blender.")
        raise SystemExit(2)
    exe = _load("tools/catalog_from_game").blender_python()
    if not exe:
        print("EROARE: nu gasesc Python-ul din Blender (scrie calea catre blender.exe in tools\\blender_path.txt).")
        raise SystemExit(2)
    print(f"(re-lansez cu {exe})", flush=True)
    code = subprocess.call([exe, os.path.abspath(__file__)] + sys.argv[1:], env=dict(os.environ, DZ_RELAUNCHED="1"))
    raise SystemExit(code)


def main(argv) -> int:
    ensure_pymateria()
    import numpy as np
    from dayzgen import config as C
    from dayzgen import gta_export as GX
    from dayzgen.city.catalog import Catalog
    from dayzgen.city.placer import BuildingPlacer
    from dayzgen.preview import render_map_preview
    from dayzgen.terrain import World

    cfg = _load("preview_city").load_config(argv)
    out_dir = os.path.join(HERE, "output", f"{cfg.name}_oras")
    os.makedirs(out_dir, exist_ok=True)
    t0 = time.time()
    print(f"harta {cfg.size:.0f} m, seed {cfg.seed}, oras raza {cfg.city_radius:.0f} m")

    world = World(cfg, building_radii={k: 8.0 for k in C.BUILDING_KEYS}, log=print)
    world.generate_heightmap()
    world.place_villages()
    world.build_roads()
    city = world.build_city()
    if city is None:
        print("Nu s-a putut genera orasul. Incearca alt seed, alt centru sau o raza mai mare.")
        return 1

    catalog = Catalog.load(required=True)
    placer = BuildingPlacer(cfg, city, catalog, log=print).place()
    city.buildings = placer.placements
    world.place_buildings()
    world.place_fields()
    world.compute_layers()

    # --- .ymap cu cladirile, in coordonate de lume
    items = []
    for p in placer.placements:
        r = 0.5 * math.hypot(p.sx, p.sy) + 2.0
        items.append({
            "archetype": p.model,
            "pos": [p.x + cfg.origin_x, p.y + cfg.origin_y, p.z],
            "rot": list(GX._rot_quat(0.0, 0.0, p.heading)),
            "scale": [1.0, 1.0],
            "lod": p.lod,
            "bb": [[-r, -r, -p.height], [r, r, p.height]],
            "guid": GX._guid(f"{cfg.name}:city:{p.lot}:{p.model}"),
        })
    ymap_name = f"{cfg.name}_city"
    GX.write_ymap(ymap_name, items, out_dir, gen9=False)

    # --- teren, pentru scena din Blender
    gx, gy = np.meshgrid(world.coords, world.coords)
    np.savez_compressed(
        os.path.join(out_dir, "terrain.npz"),
        h=world.h.astype(np.float32), street=world.street_mask, city=world.city_mask,
        zones=city.zones.at(gx, gy).astype(np.uint8),
        cell=float(cfg.cell), size=float(cfg.size), origin=np.array([cfg.origin_x, cfg.origin_y]),
    )

    with open(os.path.join(out_dir, "ytyps.txt"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(placer.ytyps()) + "\n")

    plan = city.to_json()
    plan["buildings"] = [p.to_json() for p in placer.placements]
    with open(os.path.join(out_dir, "plan.json"), "w", encoding="utf-8") as handle:
        json.dump(plan, handle, indent=1)

    render_map_preview(world, os.path.join(out_dir, "preview.png"), size=1400, city=city)

    print()
    for line in city.summary_lines():
        print(line)
    print(f"  modele distincte: {len(placer.models())}, fisiere .ytyp: {len(placer.ytyps())}")
    print(f"\nRezultat: {out_dir}  ({time.time() - t0:.1f} s)")
    print("Urmatorul pas: BIBLIOTECA_GTA.bat (modelele reale in Blender), apoi BLENDER_EDITOR.bat")
    return 0


if __name__ == "__main__":
    exit_code = main(sys.argv[1:])
    sys.stdout.flush()
    os._exit(exit_code)
