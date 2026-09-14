# -*- coding: utf-8 -*-
"""Aleile unui parc, fara Blender: generatorul (gen_cartier.park_layout) si editorul de pe web (previzualizarea) le
socotesc la fel, cu acelasi rng. Poteci "auto" = ale generatorului: alee pe contur, 2-3 alei curbe spre o piateta
rotunda; "manual" (parcul din plan are poteci = "manual") = doar cararile tale. Cararile stau langa plan, in
<plan>_carari.json (le pune unealta Carare din /mapeditor, prin serverul editorului), ca salvarea planului din pagina
sa nu le stearga."""
import json
import math
from pathlib import Path

LATIME = 2.2        # latimea unei carari puse fara latime (aleile generatorului au 2.2-2.4 m)


def rounded_rect(ax, ay, bx, by, r):
    pts = []
    for cx, cy, a0 in ((bx - r, ay + r, -90), (bx - r, by - r, 0), (ax + r, by - r, 90), (ax + r, ay + r, 180)):
        for k in range(7):
            a = math.radians(a0 + 90 * k / 6)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts + [pts[0]]


def curve(p0, p1, p2, n=24):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]) for t in (k / n for k in range(n + 1))]


def park_paths(x0, y0, x1, y1, rng, poly=None, auto=True, extra=()):
    """-> (alei [(puncte, latime)], centrul (cx, cy), raza piatetei; 0 = fara piateta). poly = poligonul parcului
    (sens trigonometric); fara el parcul e dreptunghiul x0..x1, y0..y1. extra = cararile tale care trec prin el.
    rng se consuma la fel si cu auto=False: restul parcului (copaci, banci) nu se muta cand schimbi potecile."""
    w, d = x1 - x0, y1 - y0
    if poly is None:
        ins = min(6.0, min(w, d) * 0.16)
        paths = [(rounded_rect(x0 + ins, y0 + ins, x1 - ins, y1 - ins, min(9.0, min(w, d) * 0.25)), 2.4)]
        cx, cy = (x0 + x1) / 2 + rng.uniform(-0.1, 0.1) * w, (y0 + y1) / 2 + rng.uniform(-0.1, 0.1) * d
        entries = [(x0, y0), (x1, y1), (x0, y1), (x1, y0), ((x0 + x1) / 2, y0), ((x0 + x1) / 2, y1),
                   (x0, (y0 + y1) / 2), (x1, (y0 + y1) / 2)]
    else:
        cx, cy = sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly)
        loop = [(cx + (px - cx) * max(0.3, 1 - 7.0 / max(math.hypot(px - cx, py - cy), 1e-6)),
                 cy + (py - cy) * max(0.3, 1 - 7.0 / max(math.hypot(px - cx, py - cy), 1e-6))) for px, py in poly]
        paths = [(loop + loop[:1], 2.4)]
        entries = [tuple(p) for p in poly] + [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
                                              for a, b in zip(poly, poly[1:] + poly[:1])]
    for ex, ey in rng.sample(entries, rng.randint(2, 3)):
        mx, my = (ex + cx) / 2, (ey + cy) / 2
        bend = rng.uniform(-0.25, 0.25)
        paths.append((curve((ex, ey), (mx - (cy - ey) * bend, my + (cx - ex) * bend), (cx, cy)), 2.2))
    plaza = rng.uniform(4.0, 5.5)
    if not auto:
        paths, plaza = [], 0.0
    return paths + [([tuple(p[:2]) for p in pts], float(wd)) for pts, wd in extra if len(pts) >= 2], (cx, cy), plaza


def carari_file(plan_path):
    p = Path(plan_path)
    return p.with_name(p.stem + "_carari.json")


def load_carari(plan_path):
    """[{"id", "latime", "puncte": [[x, y], ...]}] in coordonatele planului; [] daca nu sunt."""
    try:
        data = json.loads(carari_file(plan_path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [c for c in data.get("carari", []) if len(c.get("puncte") or []) >= 2]


def near(carari, poly, pad=3.0):
    """Cararile a caror cutie atinge cutia poligonului (+pad): [(puncte, latime)] pentru park_paths(extra=)."""
    xs, ys = [p[0] for p in poly], [p[1] for p in poly]
    bx0, by0, bx1, by1 = min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad
    out = []
    for c in carari:
        cx, cy = [p[0] for p in c["puncte"]], [p[1] for p in c["puncte"]]
        if max(cx) < bx0 or min(cx) > bx1 or max(cy) < by0 or min(cy) > by1:
            continue
        out.append(([(float(p[0]), float(p[1])) for p in c["puncte"]], float(c.get("latime") or LATIME)))
    return out
