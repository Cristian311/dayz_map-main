# -*- coding: utf-8 -*-
"""Teste pentru plan_geom.py pe planuri-exemplu:  python tools/oras/test_plan_geom.py
Scrie si planurile in output/orase/exemple/ (pentru gen_oras.py si editor)."""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plan_geom as G  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "output" / "orase" / "exemple"


def grid(nx=3, ny=3, bx=100.0, by=70.0):
    nodes, roads = [], []
    for j in range(ny + 1):
        for i in range(nx + 1):
            nodes.append({"id": f"n{i}_{j}", "x": i * bx, "y": j * by, "z": 0.0})
            if i:
                roads.append({"id": f"h{i}_{j}", "a": f"n{i - 1}_{j}", "b": f"n{i}_{j}", "tip": "strada"})
            if j:
                roads.append({"id": f"v{i}_{j}", "a": f"n{i}_{j - 1}", "b": f"n{i}_{j}", "tip": "artera"})
    return {"nodes": nodes, "roads": roads, "zones": [], "altitudini": []}


def star(n=5, r=130.0):
    nodes = [{"id": "c", "x": 0.0, "y": 0.0, "z": 0.0}]
    roads = []
    for k in range(n):
        a = 2 * math.pi * k / n + 0.3
        nodes.append({"id": f"o{k}", "x": r * math.cos(a), "y": r * math.sin(a), "z": 0.0})
        roads.append({"id": f"s{k}", "a": "c", "b": f"o{k}", "tip": "strada"})
        roads.append({"id": f"r{k}", "a": f"o{k}", "b": f"o{(k + 1) % n}", "tip": "artera"})
    return {"nodes": nodes, "roads": roads, "zones": [], "altitudini": []}


def acute():
    p = {"nodes": [{"id": "a", "x": 0, "y": 0}, {"id": "b", "x": 150, "y": 0},
                   {"id": "c", "x": 150 * math.cos(math.radians(20)), "y": 150 * math.sin(math.radians(20))}],
         "roads": [{"id": "ab", "a": "a", "b": "b"}, {"id": "ac", "a": "a", "b": "c"}, {"id": "bc", "a": "b", "b": "c"}]}
    return p


def curved_slope(rise):
    return {"nodes": [{"id": "a", "x": 0, "y": 0, "z": 0}, {"id": "b", "x": 220, "y": 0, "z": rise},
                      {"id": "c", "x": 220, "y": -90, "z": rise}, {"id": "d", "x": 0, "y": -90, "z": 0}],
            "roads": [{"id": "ab", "a": "a", "b": "b", "tip": "artera", "puncte": [[110, 45]]},
                      {"id": "bc", "a": "b", "b": "c"}, {"id": "cd", "a": "c", "b": "d"}, {"id": "da", "a": "d", "b": "a"}],
            "zones": [{"x": 110, "y": -30, "tip": "parc"}], "altitudini": [{"x": 110, "y": 120, "z": 25}]}


def dead_end():
    p = grid(1, 1, 140, 90)
    p["nodes"].append({"id": "m", "x": 70, "y": 40})
    p["roads"].append({"id": "fund", "a": "n0_0", "b": "m", "tip": "alee"})
    return p


def crossing():
    return {"nodes": [{"id": "a", "x": 0, "y": 0}, {"id": "b", "x": 100, "y": 100},
                      {"id": "c", "x": 0, "y": 100}, {"id": "d", "x": 100, "y": 0}],
            "roads": [{"id": "ab", "a": "a", "b": "b"}, {"id": "cd", "a": "c", "b": "d"}]}


def complete():
    """Tot ce stie editorul: pod peste 4 strazi, lac, parc / parcare / zona de cladiri desenate, bulevard cu
    mediana (profil propriu), deal pictat, cladire pusa de mana, props."""
    p = grid(3, 2)
    for r in p["roads"]:
        if r["id"].startswith("h") and r["id"].endswith("_1"):
            r["tip"] = "bulevard"
    for n in p["nodes"]:
        n.pop("z", None)
        n["auto"] = True
    p["nodes"] += [{"id": "pa", "x": -80, "y": 105, "auto": True}, {"id": "pb", "x": -20, "y": 105, "z": 9.0},
                   {"id": "pc", "x": 320, "y": 105, "z": 9.0}, {"id": "pd", "x": 380, "y": 105, "auto": True}]
    p["roads"] += [{"id": "p1", "a": "pa", "b": "pb", "nivel": "pod"}, {"id": "p2", "a": "pb", "b": "pc", "nivel": "pod"},
                   {"id": "p3", "a": "pc", "b": "pd", "nivel": "pod"}]
    p["profile"] = {"bulevard": {"nume": "Bulevard", "carosabil": 20.0, "trotuar": 4.0, "benzi": 2, "mediana": 4.0,
                                 "mediana_tip": "iarba", "copaci": True, "stalpi": 26}}
    nx, ny, s, x0, y0 = 70, 40, 8.0, -120.0, -120.0
    p["teren"] = {"x0": x0, "y0": y0, "step": s, "nx": nx, "ny": ny,
                  "h": [round(6.0 * math.exp(-((x0 + i * s - 330) ** 2 + (y0 + j * s - 170) ** 2) / (2 * 70.0 ** 2)), 2)
                        for j in range(ny) for i in range(nx)]}
    p["suprafete"] = [{"id": "s1", "tip": "apa", "puncte": [[-60, -110], [360, -110], [360, -45], [-60, -45]]},
                      {"id": "s2", "tip": "parc", "puncte": [[20, 18], [62, 18], [62, 55], [20, 55]]},
                      {"id": "s3", "tip": "parcare", "puncte": [[80, 30], [125, 30], [125, 60], [80, 60]]},
                      {"id": "s4", "tip": "lc_caramida", "puncte": [[215, 40], [285, 40], [285, 75], [215, 75]]}]
    p["zones"] = [{"x": 250, "y": 35, "tip": "suburbie"}, {"x": 150, "y": 175, "tip": "centru"}]
    p["cladiri"] = [{"id": "k1", "x": 250, "y": 125, "r": -90, "tip": "gen",
                     "p": {"tip": "bloc", "latime": 30, "adancime": 16, "etaje": 4}}]
    p["props"] = [{"m": "prop_tree_maple_02", "x": 30 + 6 * k, "y": 62, "r": 0} for k in range(5)]
    p["joc"] = {"x": 5500, "y": -5500, "z": 3, "resursa": "oras_complet"}
    return p


def check_complete():
    plan = complete()
    res = G.analyze(plan)
    valid = [b for b in res["blocks"] if b["valid"]]
    areas = {a["id"]: a for a in res["suprafete"]}
    hill = res["noduri"]["n3_2"]
    grid_ = G.terrain(plan, res, step=8.0)
    lake = G.height(grid_, 150, -80)
    ok = (len(res["pasaje"]) == 4 and len(valid) == 6 and set(areas) == {"s1", "s2", "s3", "s4"}
          and all(G.inside(p, next(b["poligon"] for b in res["blocks"] if b["id"] == areas["s3"]["bloc"]))
                  for p in areas["s3"]["poligon"])
          and hill > 1.0 and lake < res["mare"] - 4.0 and res["roads"]["h1_1"]["r"] == 20.0
          and not [w for w in res["warnings"] if w["tip"] != "panta"])
    print(f"{'OK ' if ok else 'GRESIT'} complet: {len(valid)} cvartale, pasaje {len(res['pasaje'])}, suprafete "
          f"{sorted(areas)}, nod pe deal {hill:.1f} m, fundul lacului {lake:.1f} m, avertismente "
          f"{[w['mesaj'] for w in res['warnings']]}")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "complet.json").write_text(json.dumps(dict(plan, seed=7, texturi="gta"), indent=1), encoding="utf-8")
    return ok


def check(name, plan, blocks=None, warn=(), nowarn=True):
    res = G.analyze(plan)
    ok = True
    valid = [b for b in res["blocks"] if b["valid"]]
    for b in valid:
        if G.area(b["poligon"]) <= 0 or not G.simple(b["poligon"]):
            ok = False
            print(f"  cvartal {b['id']} invalid")
    for nid, j in res["junctions"].items():
        if not G.simple(j["asfalt"]):
            ok = False
            print(f"  asfalt autointersectat la {nid}")
    kinds = sorted({w["tip"] for w in res["warnings"]})
    if blocks is not None and len(valid) != blocks:
        ok = False
    if any(k not in kinds for k in warn) or (nowarn and not warn and kinds):
        ok = False
    grid_ = G.terrain(plan, res, step=8.0)
    print(f"{'OK ' if ok else 'GRESIT'} {name}: {len(valid)} cvartale valide / {len(res['blocks'])}, "
          f"{len(res['junctions'])} intersectii, avertismente {kinds}, teren {grid_['z'].shape}, "
          f"zone {[b['zona'] for b in valid][:4]}")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.json").write_text(json.dumps(dict(plan, seed=7, texturi="gta"), indent=1), encoding="utf-8")
    return ok


results = [
    check("grila", grid(), blocks=9),
    check("stea", star(), blocks=5),
    check("unghi_ascutit", acute(), warn=("unghi",)),
    check("curba_panta", curved_slope(12.0), blocks=1),
    check("panta_mare", curved_slope(40.0), blocks=1, warn=("panta",)),
    check("fundatura", dead_end(), blocks=1),
    check("incrucisare", crossing(), warn=("incrucisare",)),
    check_complete(),
]
print("TOATE OK" if all(results) else "UNELE TESTE AU PICAT")
sys.exit(0 if all(results) else 1)
