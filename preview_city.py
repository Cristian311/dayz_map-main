# -*- coding: utf-8 -*-
"""
Previzualizare rapida a orasului, fara Blender.

Ruleaza doar partea de numpy: relief -> sate -> drumuri -> zonare -> strazi -> cvartale ->
loturi, si scrie un PNG cu zonele colorate, strazile pe rang si conturul loturilor. Bun
pentru reglat `city_*` din map.json in cateva secunde, inainte de generarea adevarata.

    python preview_city.py                      foloseste map.json daca exista, altfel presetul demo
    python preview_city.py --preset tiny
    python preview_city.py --seed 42 --radius 300 --block 80
    python preview_city.py --out oras.png --px 1600
"""
from __future__ import annotations

import copy
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402

from dayzgen import config as C           # noqa: E402
from dayzgen.city.plan import CityPlan    # noqa: E402
from dayzgen.preview import render_map_preview  # noqa: E402
from dayzgen.terrain import World         # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def _arg(argv, flag, cast=float, fallback=None):
    if flag in argv:
        index = argv.index(flag)
        if index + 1 < len(argv):
            try:
                return cast(argv[index + 1])
            except ValueError:
                pass
    return fallback


def load_config(argv) -> C.MapConfig:
    preset = _arg(argv, "--preset", str, None)
    map_json = os.path.join(HERE, "map.json")

    if preset:
        cfg = copy.deepcopy(C.PRESETS[preset])
        cfg.preset = preset
    elif os.path.isfile(map_json):
        cfg = C.MapConfig.from_json(map_json)
        print(f"config: map.json (preset {cfg.preset})")
    else:
        cfg = copy.deepcopy(C.PRESETS["demo"])

    # Previzualizarea are sens doar cu orasul pornit.
    cfg.city = True
    for flag, field, cast in (("--seed", "seed", int), ("--radius", "city_radius", float),
                              ("--block", "city_block", float), ("--size", "size", float),
                              ("--angle", "city_angle", float), ("--warp", "city_warp", float),
                              ("--grade", "city_max_grade", float)):
        value = _arg(argv, flag, cast, None)
        if value is not None:
            setattr(cfg, field, value)

    if "--center" in argv:
        index = argv.index("--center")
        if index + 2 < len(argv):
            cfg.city_center = (float(argv[index + 1]), float(argv[index + 2]))

    # Orasul are nevoie de loc: daca raza depaseste harta, o strAngem.
    max_radius = cfg.size * 0.40
    if cfg.city_radius > max_radius:
        print(f"  city_radius {cfg.city_radius:.0f} m e prea mare pentru o harta de "
              f"{cfg.size:.0f} m; folosesc {max_radius:.0f} m")
        cfg.city_radius = max_radius

    cfg.validate()
    return cfg


def main(argv) -> int:
    t0 = time.time()
    cfg = load_config(argv)
    out = _arg(argv, "--out", str, os.path.join(HERE, "oras_preview.png"))
    px = int(_arg(argv, "--px", float, 1400))

    print(f"harta {cfg.size:.0f} m, seed {cfg.seed}, oras raza {cfg.city_radius:.0f} m, "
          f"cvartal {cfg.city_block:.0f} m")

    world = World(cfg, building_radii={k: 8.0 for k in C.BUILDING_KEYS}, log=print)
    world.generate_heightmap()
    world.place_villages()
    world.build_roads()

    city = CityPlan(cfg, world, log=print).build()
    if city.plan is None:
        print("Nu s-a putut genera orasul. Incearca alt seed, alt centru sau o raza mai mare.")
        return 1

    # Casele de sat si cAmpurile ocolesc orasul (world.city_mask e pus de CityPlan).
    world.place_buildings()
    world.place_fields()
    world.compute_layers()

    render_map_preview(world, out, size=px, city=city)
    for line in city.summary_lines():
        print(line)

    plan_path = os.path.splitext(out)[0] + ".json"
    with open(plan_path, "w", encoding="utf-8") as handle:
        json.dump(city.to_json(), handle, indent=1)

    lots = city.lots
    if lots:
        areas = np.array([l.area for l in lots])
        print(f"  suprafata loturilor: total {areas.sum() / 10000.0:.1f} ha, "
              f"mediu {areas.mean():.0f} m2 (min {areas.min():.0f}, max {areas.max():.0f})")
    print(f"\nImagine: {out}")
    print(f"Plan    : {plan_path}")
    print(f"Durata  : {time.time() - t0:.1f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
