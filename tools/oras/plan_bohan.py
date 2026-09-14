# -*- coding: utf-8 -*-
"""
Scrie planul output/orase/bohan.json: un cartier inspirat din Bohan (Bronx-ul din GTA IV). Nu e harta jocului
(nu avem coordonatele ei), ci aceeasi idee: bulevard curb pe malul apei de jur imprejur, deal in vest cu strazi
serpuite si case, grila usor stramba in centru, blocuri-turn maro pe gazon cu copaci ("projects"), randuri de
caramida, un parc mare pe o colina, industrie la apa in sud.

    python tools/oras/plan_bohan.py        apoi in editor: planul "bohan" (sau Genereaza direct)
"""
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import plan_geom as G  # noqa: E402

NX, NY = 6, 4                      # noduri pe X si Y (5 x 3 cvartale)


def pos(i, j):
    """Grila stramba: coloanele se unduiesc putin, randurile la fel (ca strazile vechi din Bronx)."""
    return (round(i * 135 - 337 + 14 * math.sin(j * 1.3 + 0.4), 1),
            round(j * 115 - 172 + 16 * math.sin(i * 0.8), 1))


def height(x, y):
    """Dealul din vest (pana la ~11 m), restul aproape plat, cu mici valuri."""
    return round(max(0.0, (-x - 60.0) / 270.0) * 11.0 + 0.6 * math.sin(y / 90.0), 1)


def build():
    nodes, roads = [], []
    for j in range(NY):
        for i in range(NX):
            x, y = pos(i, j)
            nodes.append({"id": f"n{i}_{j}", "x": x, "y": y, "z": height(x, y)})
    # cvartalele unite: parcul mare (2,1)+(3,1) si superblocul de turnuri (2,2)+(3,2)
    skip = {("v", 3, 1), ("v", 3, 2)}
    for j in range(NY):
        for i in range(NX - 1):
            (ax, ay), (bx, by) = pos(i, j), pos(i + 1, j)
            outer = j in (0, NY - 1)
            road = {"id": f"h{i}_{j}", "a": f"n{i}_{j}", "b": f"n{i + 1}_{j}", "tip": "artera" if outer else "strada"}
            if outer:   # malul: bulevardul se umfla spre apa
                road["puncte"] = [[round((ax + bx) / 2, 1), round((ay + by) / 2 + (-20 if j == 0 else 20), 1)]]
            roads.append(road)
    for i in range(NX):
        for j in range(NY - 1):
            if ("v", i, j) in skip:
                continue
            (ax, ay), (bx, by) = pos(i, j), pos(i, j + 1)
            outer = i in (0, NX - 1)
            road = {"id": f"v{i}_{j}", "a": f"n{i}_{j}", "b": f"n{i}_{j + 1}",
                    "tip": "artera" if outer or i == 2 else "strada"}
            if outer:
                road["puncte"] = [[round((ax + bx) / 2 + (-22 if i == 0 else 22), 1), round((ay + by) / 2, 1)]]
            elif i == 1:   # strazile de pe deal serpuiesc
                road["puncte"] = [[round((ax + bx) / 2 + (12 if j % 2 else -12), 1), round((ay + by) / 2, 1)]]
            roads.append(road)

    def center(i, j):
        pts = [pos(i, j), pos(i + 1, j), pos(i + 1, j + 1), pos(i, j + 1)]
        return round(sum(p[0] for p in pts) / 4, 1), round(sum(p[1] for p in pts) / 4, 1)

    layout = {(0, 2): "suburbie", (1, 2): "proiecte", (2, 2): "proiecte", (4, 2): "proiecte",
              (0, 1): "suburbie", (1, 1): "lc_caramida", (2, 1): "parc", (4, 1): "lc_caramida",
              (0, 0): "parc", (1, 0): "lc_caramida", (2, 0): "lc_caramida", (3, 0): "industrial", (4, 0): "industrial"}
    zones = [{"x": center(i, j)[0], "y": center(i, j)[1], "tip": t} for (i, j), t in layout.items()]
    # colina din parcul mare, dealul din vest si malul (terenul din afara strazilor)
    cx, cy = center(2, 1)
    alt = [{"x": round(cx + 70, 1), "y": round(cy, 1), "z": 6.0}, {"x": -480.0, "y": 0.0, "z": 16.0},
           {"x": -470.0, "y": 230.0, "z": 12.0}, {"x": 0.0, "y": -300.0, "z": -1.0}, {"x": 420.0, "y": -250.0, "z": -1.0}]
    return {"version": 1, "seed": 1947, "texturi": "gta", "panta_max": 0.10, "zona_implicita": "lc_caramida",
            "nodes": nodes, "roads": roads, "zones": zones, "altitudini": alt}


if __name__ == "__main__":
    plan = build()
    A = G.analyze(plan)
    ok = [b for b in A["blocks"] if b["valid"]]
    print(f"bohan: {len(plan['roads'])} strazi, {len(A['junctions'])} intersectii, {len(ok)}/{len(A['blocks'])} cvartale,"
          f" zone {sorted(b['zona'] for b in ok)}")
    for w in A["warnings"]:
        print("  avertisment:", w["mesaj"], (w["x"], w["y"]))
    out = HERE.parents[1] / "output" / "orase" / "bohan.json"
    out.write_text(json.dumps(plan, indent=1), encoding="utf-8")
    print("scris:", out)
