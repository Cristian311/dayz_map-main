# -*- coding: utf-8 -*-
"""
Cartier in grila, stil Liberty City: bulevarde pe Y, strazi pe X, intersectii la fiecare colt. Cvartalele sunt
de mai multe feluri: inchise (randuri de blocuri pe toate laturile, curte la mijloc), cu doua randuri si o alee
pe mijloc, turn intr-o piateta, parcare, parc. In randuri apar alei intre cladiri (se intra in curti), iar
cladirile sunt mai inalte spre centru. Cu --relief terenul are dealuri line: strazile il urmeaza, cladirile
stau la nivelul strazii din fata lor, cu fundatie de piatra spre vale.

    GENEREAZA_CARTIER.bat  sau  GENERATOR.bat (fereastra cu toate setarile)
    _blender.bat -b -P gen_cartier.py -- --x 3 --y 2 --cvartal 80x50 --relief 8

Bratele intersectiilor de pe margine raman deschise: acolo lipesti piese din kitul de strada de acelasi tip.
Iese in output\\cartiere\\cartier_<seed>.glb + .blend.
"""
import argparse
import json
import math
import random
import runpy
import sys
import time
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS / "oras"))
import park_plan as PP  # noqa: E402  aleile parcului: le socoteste la fel si editorul de pe web
st = runpy.run_path(str(TOOLS / "gen_strada.py"), run_name="gen_cartier")
cli, gen = st["cli"], st["gen"]
props = runpy.run_path(str(TOOLS / "gta_props.py"), run_name="gta_props")
TYPES, ZS = st["TYPES"], st["ZS"]
WALLS = ["perete_caramida", "perete_caramida", "perete_vila", "perete_beton"]
# parcuri: props GTA din biblioteca (copac, raza coroanei in m), alese dupa ce au fost randate
PARK_CELL = 0.25
# (model, raza coroanei); fara stejar (17 m), cedru (31 m) si mesteacanul mare (16 m): umpleau cerul de sub ei
PARK_TREES = [("prop_tree_maple_02", 5.0), ("prop_tree_maple_03", 3.0), ("prop_tree_lficus_03", 4.0),
              ("prop_tree_birch_03", 2.5), ("prop_tree_birch_03b", 3.0), ("prop_tree_cedar_s_01", 2.6)]
PARK_TREE_WEIGHTS = [3, 4, 3, 3, 3, 1]
PARK_BUSHES = ["prop_bush_lrg_01", "prop_bush_lrg_02", "prop_bush_med_01", "prop_bush_med_03"]
PARK_BENCHES = ["prop_bench_01a", "prop_bench_01b", "prop_bench_01c"]
PARK_BINS = ["prop_bin_05a"]
PARK_FOUNTAIN = "prop_fountain2"


def add_piece(coll, materials, name, draw, x, y, angle=0.0, kind="strada"):
    m = gen["Mesh"](materials)
    draw(m)
    obj = m.to_object(name)
    obj["harta_tip"] = kind
    coll.objects.link(obj)
    obj.location = (x, y, 0.0)
    obj.rotation_euler.z = angle
    return obj


def straight(kind, length):
    return lambda m: st["sweep"](m, st["line"](-length / 2, length / 2, -length / 2), st["Road"](m, kind).profile())


_rounded_rect, _curve = PP.rounded_rect, PP.curve


def park_layout(x0, y0, x1, y1, rng, poly=None, auto=True, extra=()):
    """Planul parcului pe o grila de PARK_CELL m: 0 = iarba, 1 = pavaj (margine, alei, piateta), 2 = in afara
    parcului (poly = poligonul cvartalului, sens trigonometric; fara el parcul e dreptunghiul x0..x1, y0..y1).
    Aleile vin din park_plan.park_paths: ale generatorului daca auto (alee pe contur, alei curbe spre o piateta
    rotunda), plus cararile tale din extra. Se tin si ca polilinii, pentru banci."""
    w, d = x1 - x0, y1 - y0
    nx, ny = max(1, int(w / PARK_CELL)), max(1, int(d / PARK_CELL))
    X, Y = np.meshgrid(x0 + (np.arange(nx) + 0.5) * PARK_CELL, y0 + (np.arange(ny) + 0.5) * PARK_CELL)
    mask = np.zeros((ny, nx), np.uint8)
    if poly is None:
        mask[(X < x0 + 1.5) | (X > x1 - 1.5) | (Y < y0 + 1.5) | (Y > y1 - 1.5)] = 1
    else:
        inside = np.zeros(X.shape, bool)
        near_edge = np.full(X.shape, 1e9)
        for (ax, ay), (bx, by) in zip(poly, poly[1:] + poly[:1]):
            inside ^= ((ay > Y) != (by > Y)) & (X < ax + (Y - ay) * (bx - ax) / (by - ay + 1e-12))
            dx, dy = bx - ax, by - ay
            t = np.clip(((X - ax) * dx + (Y - ay) * dy) / max(dx * dx + dy * dy, 1e-9), 0.0, 1.0)
            near_edge = np.minimum(near_edge, (X - ax - t * dx) ** 2 + (Y - ay - t * dy) ** 2)
        mask[~inside] = 2
        mask[inside & (near_edge < 1.5 ** 2)] = 1
    paths, (cx, cy), plaza = PP.park_paths(x0, y0, x1, y1, rng, poly, auto, extra)
    for pts, width in paths:
        hw = width / 2
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            i0, i1 = max(0, int((min(ax, bx) - hw - x0) / PARK_CELL)), min(nx, int((max(ax, bx) + hw - x0) / PARK_CELL) + 1)
            j0, j1 = max(0, int((min(ay, by) - hw - y0) / PARK_CELL)), min(ny, int((max(ay, by) + hw - y0) / PARK_CELL) + 1)
            if i0 >= i1 or j0 >= j1:
                continue
            px, py = X[j0:j1, i0:i1], Y[j0:j1, i0:i1]
            dx, dy = bx - ax, by - ay
            t = np.clip(((px - ax) * dx + (py - ay) * dy) / max(dx * dx + dy * dy, 1e-9), 0.0, 1.0)
            near = (px - ax - t * dx) ** 2 + (py - ay - t * dy) ** 2 < hw * hw
            sub = mask[j0:j1, i0:i1]
            sub[near & (sub != 2)] = 1
    if plaza > 0:
        mask[((X - cx) ** 2 + (Y - cy) ** 2 < plaza * plaza) & (mask != 2)] = 1
    return {"x0": x0, "y0": y0, "x1": x1, "y1": y1, "mask": mask, "paths": paths, "center": (cx, cy),
            "plaza": plaza, "poly": poly, "loop": auto}


PARK_MESH = 1.0     # latura grilei de triunghiuri a parcului (aleile au 2.2-2.4 m)


def _seg_dist(X, Y, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    t = np.clip(((X - ax) * dx + (Y - ay) * dy) / max(dx * dx + dy * dy, 1e-12), 0.0, 1.0)
    return np.sqrt((X - ax - t * dx) ** 2 + (Y - ay - t * dy) ** 2)


def _seg_min(X, Y, S, off=None, ring=False):
    """Pe toate segmentele S (k x 4: ax, ay, bx, by) odata: distanta minima de la fiecare punct (minus off[k], daca e
    dat) si, cu ring=True, daca punctul e in inelul lor (par-impar). Aceleasi formule ca _seg_dist, deci aceleasi
    valori; un segment odata (bucla Python) facea 4 milioane de apeluri numpy pe un oras si lua 2 minute."""
    shape = np.shape(X)
    x = np.asarray(X, float).reshape(-1, 1)
    y = np.asarray(Y, float).reshape(-1, 1)
    n = x.shape[0]
    dist, inside = np.full(n, 1e9), np.zeros(n, bool)
    if len(S) and n:
        ax, ay, bx, by = S[:, 0], S[:, 1], S[:, 2], S[:, 3]
        dx, dy = bx - ax, by - ay
        l2 = np.maximum(dx * dx + dy * dy, 1e-12)
        step = max(1, 1_000_000 // len(S))         # bucati de puncte: cel mult ~8 MB pe matrice
        for i in range(0, n, step):
            xs, ys = x[i:i + step], y[i:i + step]
            t = np.clip(((xs - ax) * dx + (ys - ay) * dy) / l2, 0.0, 1.0)
            d = np.sqrt((xs - ax - t * dx) ** 2 + (ys - ay - t * dy) ** 2)
            if off is not None:
                d = d - off
            dist[i:i + step] = d.min(axis=1)
            if ring:
                cross = ((ay > ys) != (by > ys)) & (xs < ax + (ys - ay) * (bx - ax) / (by - ay + 1e-12))
                inside[i:i + step] = (cross.sum(axis=1) % 2) == 1
    return dist.reshape(shape), inside.reshape(shape)


def _field_segs(L):
    """Segmentele parcului ca matrice numpy (conturul, gaurile, strazile taiate, aleile), facute o data pe parc."""
    poly, holes, cut, paths = L.get("poly"), L.get("holes", ()), L.get("cut", ()), L["paths"]
    sig = (len(poly or ()), len(holes), len(cut), len(paths))
    cached = L.get("_segs")
    if cached and cached[0] == sig:
        return cached[1]

    def ring(pts):
        pts = list(pts)
        return np.array([(a[0], a[1], b[0], b[1]) for a, b in zip(pts, pts[1:] + pts[:1])], float).reshape(-1, 4)

    def chains(lines, off):
        segs = [(a[0], a[1], b[0], b[1]) for pts, _w in lines for a, b in zip(pts, pts[1:])]
        offs = [off(w) for pts, w in lines for _ in range(max(0, len(pts) - 1))]
        return np.array(segs, float).reshape(-1, 4), np.array(offs, float)

    data = {"poly": ring(poly) if poly else None, "holes": [ring(h) for h in holes],
            "cut": chains(cut, float), "paths": chains(paths, lambda w: w / 2)}
    L["_segs"] = (sig, data)
    return data


def _cut_dist(L, X, Y):
    """Distanta pana la marginea strazilor taiate din parc (negativa pe strada)."""
    S, off = _field_segs(L)["cut"]
    return _seg_min(X, Y, S, off)[0]


def park_cut(L, lines):
    """Strazile care intra in parc fara sa-l imparta (fundaturi, bucle din cvartal): parcul le ocoleste, cu o
    margine de pavaj langa ele. lines = [(puncte xy, jumatatea latimii strazii cu trotuar)]."""
    L["cut"] = [([tuple(p[:2]) for p in pts], float(half)) for pts, half in lines if len(pts) >= 2]
    if not L["cut"]:
        return
    mask = L["mask"]
    ny, nx = mask.shape
    X, Y = np.meshgrid(L["x0"] + (np.arange(nx) + 0.5) * PARK_CELL, L["y0"] + (np.arange(ny) + 0.5) * PARK_CELL)
    d = _cut_dist(L, X, Y)
    mask[(d < 0) & (mask != 2)] = 2              # strada: nici copaci, nici banci
    mask[(d >= 0) & (d < 1.5) & (mask == 0)] = 1


def park_holes(L, holes):
    """Suprafetele desenate in parc (parcare, piateta, teren de sport) au prioritate: parcul le ocoleste (iarba se
    opreste la o margine de pavaj de 1.5 m), iar copacii si bancile nu se pun pe ele."""
    L["holes"] = [[tuple(p[:2]) for p in h] for h in holes if len(h) >= 3]
    if not L["holes"]:
        return
    mask = L["mask"]
    ny, nx = mask.shape
    X, Y = np.meshgrid(L["x0"] + (np.arange(nx) + 0.5) * PARK_CELL, L["y0"] + (np.arange(ny) + 0.5) * PARK_CELL)
    for hole in L["holes"]:
        edge = np.full(X.shape, 1e9)
        inside = np.zeros(X.shape, bool)
        for (ax, ay), (bx, by) in zip(hole, hole[1:] + hole[:1]):
            edge = np.minimum(edge, _seg_dist(X, Y, ax, ay, bx, by))
            inside ^= ((ay > Y) != (by > Y)) & (X < ax + (Y - ay) * (bx - ax) / (by - ay + 1e-12))
        mask[inside] = 2
        mask[~inside & (edge < 1.5) & (mask == 0)] = 1


def park_fields(L, X, Y):
    """(in, pav) in punctele X, Y: in > 0 inauntrul parcului, pav < 0 pe pavaj (margine, alei, piateta).
    Distante in metri, deci marginile iarba/alee se taie exact pe curba, nu in trepte."""
    x0, y0, x1, y1, poly = L["x0"], L["y0"], L["x1"], L["y1"], L.get("poly")
    S = _field_segs(L)
    if poly:
        edge, inside = _seg_min(X, Y, S["poly"], ring=True)
        fin = np.where(inside, edge, -edge)
    else:
        fin = np.minimum(np.minimum(X - x0, x1 - X), np.minimum(Y - y0, y1 - Y))
    for H in S["holes"]:
        edge, inside = _seg_min(X, Y, H, ring=True)
        fin = np.minimum(fin, np.where(inside, -edge, edge))
    if len(S["cut"][0]):
        fin = np.minimum(fin, _seg_min(X, Y, *S["cut"])[0])
    pav = fin - 1.5
    if len(S["paths"][0]):
        pav = np.minimum(pav, _seg_min(X, Y, *S["paths"])[0])
    cx, cy = L["center"]
    if L["plaza"] > 0:      # fara piateta cand parcul are doar cararile tale
        pav = np.minimum(pav, np.sqrt((X - cx) ** 2 + (Y - cy) ** 2) - L["plaza"])
    return fin, pav


def _clip(poly, vals, keep_pos, cut, field):
    """Partea poligonului (varfuri + valori ale campului) cu valoarea > 0 (keep_pos) sau <= 0. Punctul de pe o
    latura se calculeaza cu capetele in ordine fixa, deci doua triunghiuri vecine il obtin identic."""
    out = []
    n = len(poly)
    for k in range(n):
        p, q, a, b = poly[k], poly[(k + 1) % n], vals[k], vals[(k + 1) % n]
        if (a > 0) == keep_pos:
            out.append(p)
        if (a > 0) != (b > 0):
            key = (p, q) if p <= q else (q, p)
            if key not in cut:
                (u, fu), (w, fw) = (p, a), (q, b)
                if p > q:
                    (u, fu), (w, fw) = (w, fw), (u, fu)
                t = fu / (fu - fw)
                cut[key] = (u[0] + (w[0] - u[0]) * t, u[1] + (w[1] - u[1]) * t)
            out.append(cut[key])
    return out


def plate_layout(poly, holes=(), lines=()):
    """Plan pentru park_draw(L, role): placa unui cvartal fara gauri (suprafetele desenate in el) si fara
    coridoarele strazilor din el (fundaturi, alei), taiate exact. Cu triunghiurile vechi, placa acoperea aleea la
    aceeasi inaltime cu trotuarul ei si in joc cele doua clipeau (triunghiuri rupte)."""
    xs, ys = [p[0] for p in poly], [p[1] for p in poly]
    return {"x0": min(xs), "y0": min(ys), "x1": max(xs), "y1": max(ys), "poly": [tuple(p[:2]) for p in poly],
            "holes": [[tuple(p[:2]) for p in h] for h in holes], "paths": [], "center": (1e9, 1e9), "plaza": 0.0,
            "step": 2.0,        # fara alei de urmarit: 2 m ajung (la 1 m un cvartal mare avea 65 000 de fete)
            "cut": [([tuple(p[:2]) for p in pts], float(half)) for pts, half in lines if len(pts) >= 2]}


def park_draw(L, role=None, z=ZS):
    """role = un singur material (placa din plate_layout), fara alei; altfel parcul cu iarba si pavaj."""
    return _park_draw(L, role, z)


def _park_draw(L, role, z):
    """Parcul ca o singura placa: o grila de triunghiuri de PARK_MESH m, taiata dupa campurile lui park_fields
    in iarba si pavaj. Varfurile de pe laturi sunt comune, deci pe deal suprafata ramane neteda (fara trepte si
    fara crapaturi in care se loveau rotile)."""
    def draw(m):
        x0, y0, x1, y1 = L["x0"], L["y0"], L["x1"], L["y1"]
        step = L.get("step", PARK_MESH)
        nx, ny = max(1, math.ceil((x1 - x0) / step)), max(1, math.ceil((y1 - y0) / step))
        gx, gy = np.linspace(x0, x1, nx + 1), np.linspace(y0, y1, ny + 1)
        X, Y = np.meshgrid(gx, gy)
        fin, pav = park_fields(L, X, Y)
        cut_in, cut_pav, memo = {}, {}, {}

        def field(pts):
            miss = [p for p in pts if p not in memo]
            if miss:
                a, b = park_fields(L, np.array([p[0] for p in miss]), np.array([p[1] for p in miss]))
                for p, fa, fb in zip(miss, a, b):
                    memo[p] = (float(fa), float(fb))
            return [memo[p] for p in pts]

        for j in range(ny):
            for i in range(nx):
                c = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
                if all(fin[b, a] <= 0 for a, b in c):
                    continue
                for tri_ in ((c[0], c[1], c[2]), (c[0], c[2], c[3])) if (i + j) % 2 == 0 else \
                        ((c[0], c[1], c[3]), (c[1], c[2], c[3])):
                    pts = [(float(gx[a]), float(gy[b])) for a, b in tri_]
                    for p, (a, b) in zip(pts, tri_):
                        memo[p] = (float(fin[b, a]), float(pav[b, a]))
                    part = _clip(pts, [v[0] for v in field(pts)], True, cut_in, 0)
                    if len(part) < 3:
                        continue
                    fv = [v[1] for v in field(part)]
                    if role:
                        m.face([Vector((px, py, z)) for px, py in part], role)
                        continue
                    for keep, kind in ((True, "iarba"), (False, "trotuar")):
                        piece = _clip(part, fv, keep, cut_pav, 1)
                        if len(piece) >= 3:
                            m.face([Vector((px, py, z)) for px, py in piece], kind)
        if L.get("poly"):
            poly = L["poly"]
            for a, b in zip(poly, poly[1:] + poly[:1]):
                st["vwall"](m, a, b, -0.4, z, role or "trotuar", (b[1] - a[1], a[0] - b[0]))
        else:
            for side in ("-x", "+x", "-y", "+y"):
                a, b, n = st["edge"](x0, y0, x1, y1, side)
                st["vwall"](m, a, b, 0.0, z, role or "trotuar", n)
    return draw


def _grass(L, x, y, clear):
    """Iarba in (x, y) si nicio alee mai aproape de `clear` m."""
    mask = L["mask"]
    i, j = int((x - L["x0"]) / PARK_CELL), int((y - L["y0"]) / PARK_CELL)
    r = int(math.ceil(clear / PARK_CELL))
    if i - r < 0 or j - r < 0 or i + r >= mask.shape[1] or j + r >= mask.shape[0]:
        return False
    return not mask[j - r:j + r + 1, i - r:i + r + 1].any()


def _walk(pts, rng, first, gap):
    """Puncte (x, y, directie) de-a lungul poliliniei, la distante aleatoare intre gap[0] si gap[1]."""
    at, acc = first, 0.0
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        seg = math.hypot(bx - ax, by - ay)
        if seg < 1e-6:
            continue
        while at <= acc + seg:
            t = (at - acc) / seg
            yield ax + (bx - ax) * t, ay + (by - ay) * t, (bx - ax) / seg, (by - ay) / seg
            at += rng.uniform(*gap)
        acc += seg


def park_props(coll, L, rng, ground):
    """Banci pe marginea aleilor (cu fata spre alee) si in jurul piatetei, cosuri, fantana, copaci in grupuri
    rare si cativa singuri, tufe langa alei. ground(x, y) = inaltimea solului."""
    avail = set(props["load"]([n for n, _r in PARK_TREES] + PARK_BUSHES + PARK_BENCHES + PARK_BINS
                              + [PARK_FOUNTAIN]))
    trees = [(t, w) for t, w in zip(PARK_TREES, PARK_TREE_WEIGHTS) if t[0] in avail]
    bushes = [b for b in PARK_BUSHES if b in avail]
    benches = [b for b in PARK_BENCHES if b in avail]
    bins = [b for b in PARK_BINS if b in avail]
    placed = []

    def free(x, y, r):
        return all((x - a) ** 2 + (y - b) ** 2 >= (r + c) ** 2 for a, b, c in placed)

    def put(name, x, y, rot, r):
        props["place"](coll, name, x, y, ground(x, y), rot)
        placed.append((x, y, r))

    def pick():
        return rng.choices([t for t, _w in trees], [w for _t, w in trees])[0]

    x0, y0, x1, y1 = L["x0"], L["y0"], L["x1"], L["y1"]
    cx, cy = L["center"]
    plaza = L["plaza"] > 0      # fara piateta (si fantana) cand parcul are doar cararile tale
    if PARK_FOUNTAIN in avail and plaza:
        put(PARK_FOUNTAIN, cx, cy, rng.uniform(0, 2 * math.pi), 1.0)
    bench = rng.choice(benches) if benches else None   # acelasi model de banca in tot parcul
    if bench:
        face = props["facing"](bench)
        a0 = rng.uniform(0, 2 * math.pi)
        for k in range(4 if plaza else 0):
            a = a0 + k * math.pi / 2
            x, y = cx + (L["plaza"] + 0.9) * math.cos(a), cy + (L["plaza"] + 0.9) * math.sin(a)
            if _grass(L, x, y, 0.3) and free(x, y, 1.2):
                put(bench, x, y, a + math.pi - face, 1.2)
        for pts, width in L["paths"]:
            for x, y, tx, ty in _walk(pts, rng, rng.uniform(4.0, 9.0), (10.0, 16.0)):
                side = rng.choice((-1, 1))
                nx_, ny_ = -ty * side, tx * side
                bx, by = x + nx_ * (width / 2 + 0.8), y + ny_ * (width / 2 + 0.8)
                if not (_grass(L, bx, by, 0.4) and free(bx, by, 1.5)):
                    continue
                put(bench, bx, by, math.atan2(-ny_, -nx_) - face, 1.5)
                if bins and rng.random() < 0.35:
                    ex, ey = bx + tx * 1.9, by + ty * 1.9
                    if _grass(L, ex, ey, 0.2) and free(ex, ey, 0.5):
                        put(rng.choice(bins), ex, ey, rng.uniform(0, 2 * math.pi), 0.5)
    area = (x1 - x0) * (y1 - y0)
    if trees:
        # sir de copaci de acelasi fel de-a lungul aleii de pe contur, de ambele parti (ca in parcurile din NY)
        # (doar pe aleea de contur a generatorului; cu cararile tale parcul n-o are)
        loop, width = L["paths"][0] if L.get("loop", True) and L["paths"] else ([], 0.0)
        # aleea de pe contur e langa strada: acolo doar copaci cu coroana mica, ca sa nu acopere strada
        small = [t for t, _w in trees if t[1] <= 3.5]
        avenue = rng.choice(small)[0] if small else pick()[0]
        for x, y, tx, ty in _walk(loop, rng, rng.uniform(3.0, 8.0), (11.0, 15.0)):
            for side in (-1, 1):
                ax, ay = x - ty * side * (width / 2 + 2.8), y + tx * side * (width / 2 + 2.8)
                if _grass(L, ax, ay, 1.8) and free(ax, ay, 3.0):
                    put(avenue, ax, ay, rng.uniform(0, 2 * math.pi), 3.0)
        # grupuri pe peluze, mai ales dintr-o singura specie
        for _ in range(max(3, int(area / 700))):
            spot = next(((gx, gy) for gx, gy in ((rng.uniform(x0, x1), rng.uniform(y0, y1)) for _ in range(30))
                         if _grass(L, gx, gy, 4.0)), None)
            if spot is None:
                continue
            name, r = pick()
            for _ in range(rng.randint(3, 6)):
                if rng.random() < 0.25:
                    name, r = pick()
                x, y = spot[0] + rng.gauss(0, 4.5), spot[1] + rng.gauss(0, 4.5)
                # coroana (raza r) ramane in parc, nu peste trotuar si strada
                if _grass(L, x, y, 2.5) and free(x, y, r * 0.6) and x0 + r < x < x1 - r and y0 + r < y < y1 - r:
                    put(name, x, y, rng.uniform(0, 2 * math.pi), r * 0.6)
        for _ in range(int(area / 450)):
            name, r = pick()
            x, y = rng.uniform(x0 + r, x1 - r), rng.uniform(y0 + r, y1 - r)
            if _grass(L, x, y, 3.0) and free(x, y, r * 0.7):
                put(name, x, y, rng.uniform(0, 2 * math.pi), r * 0.7)
    for _ in range(int(2 * ((x1 - x0) + (y1 - y0)) / 8) if bushes else 0):
        x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
        if _grass(L, x, y, 1.0) and not _grass(L, x, y, 2.6) and free(x, y, 1.6):
            put(rng.choice(bushes), x, y, rng.uniform(0, 2 * math.pi), 1.6)


def lot_ground(x0, y0, x1, y1, kind, rng):
    """Placa cvartalului la nivelul trotuarului (parcare = asfalt cu locuri); parcul e o singura placa cu iarba si
    alei. Intoarce (desen, planul parcului sau None)."""
    if kind == "parc":
        layout = park_layout(x0, y0, x1, y1, rng)
        return park_draw(layout), layout

    def draw(m):
        m.box(x0, y0, 0.0, x1, y1, ZS, "asfalt" if kind == "parcare" else "trotuar")
        z = ZS + 0.012

        def q(a0, b0, a1, b1, role):
            m.quad(Vector((a0, b0, z)), Vector((a1, b0, z)), Vector((a1, b1, z)), Vector((a0, b1, z)), role)

        if kind == "parcare":
            cy = (y0 + y1) / 2
            rows = [(y0 + 0.8, y0 + 5.8), (y1 - 5.8, y1 - 0.8)]
            if y1 - y0 >= 34.0:
                rows += [(cy - 5.2, cy - 0.2), (cy + 0.2, cy + 5.2)]
            for b0, b1 in rows:
                x = x0 + 1.5
                while x <= x1 - 1.5:
                    q(x - 0.06, b0, x + 0.06, b1, "marcaj_alb")
                    x += 2.6
    return draw, None


def heightfield(seed, amp, wavelength):
    """Dealuri line: cateva unde lungi cu directii si faze dupa seed; intre -amp si +amp (m)."""
    if amp <= 0:
        return None
    r = random.Random(seed * 31 + 7)
    waves = []
    for k in range(4):
        ang = r.uniform(0.0, math.pi)
        lam = wavelength * r.uniform(0.75, 1.35) / (1.0 + 0.6 * k)
        waves.append((math.cos(ang) * 2 * math.pi / lam, math.sin(ang) * 2 * math.pi / lam,
                      r.uniform(0.0, 2 * math.pi), 1.0 / (1.0 + k)))
    total = sum(w[3] for w in waves)
    return lambda x, y: amp * sum(w * math.sin(kx * x + ky * y + ph) for kx, ky, ph, w in waves) / total


def drape(obj, h, max_edge=2.5):
    """Imparte fetele mari si ridica fiecare varf la inaltimea terenului din punctul lui. Varfurile care se
    suprapun se unesc intai, altfel fetele vecine se impart diferit si pe deal apar crapaturi si trepte."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    for _ in range(10):
        long = [e for e in bm.edges if e.calc_length() > max_edge]
        if not long:
            break
        bmesh.ops.subdivide_edges(bm, edges=long, cuts=1, use_grid_fill=True)
    mw = obj.matrix_world
    for v in bm.verts:
        w = mw @ v.co
        v.co.z += h(w.x, w.y)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def settle(obj, h, coll, materials):
    """Cladirea la nivelul strazii din fata ei; dedesubt fundatie pana sub punctul cel mai jos al terenului."""
    p = json.loads(obj["harta_gen"])
    hw, hd = p["latime"] / 2, p["adancime"] / 2
    mw = obj.matrix_world.copy()
    front = mw @ Vector((0.0, -hd, 0.0))
    zf = h(front.x, front.y)
    zmin = min(h(*(mw @ Vector((sx * hw, sy * hd, 0.0))).xy) for sx in (-1, 1) for sy in (-1, 1))
    obj.location.z += zf
    m = gen["Mesh"](materials)
    m.box(-hw, -hd, -(zf - zmin + 0.6), hw, hd, 0.0, "soclu")
    base = m.to_object(obj.name + "_fundatie")
    base["harta_tip"] = "fundatie"
    coll.objects.link(base)
    base.parent = obj


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--x", type=int, default=3, help="cvartale pe X")
    ap.add_argument("--y", type=int, default=2, help="cvartale pe Y")
    ap.add_argument("--cvartal", default="80x50", help="marimea unui cvartal fara strazi, in m (X x Y)")
    ap.add_argument("--bulevard", default="artera", choices=list(TYPES), help="drumurile pe Y")
    ap.add_argument("--strada", default="strada", choices=list(TYPES), help="drumurile pe X")
    ap.add_argument("--etaje-min", type=int, default=3)
    ap.add_argument("--etaje-max", type=int, default=9)
    ap.add_argument("--alei", type=float, default=0.3, help="sansa unei alei intre doua cladiri")
    ap.add_argument("--doua-randuri", type=float, default=0.2, help="sansa: cvartal cu doua randuri si alee")
    ap.add_argument("--turnuri", type=float, default=0.06, help="sansa: turn intr-o piateta")
    ap.add_argument("--parcari", type=float, default=0.06, help="sansa: parcare")
    ap.add_argument("--parcuri", type=float, default=0.12, help="sansa: parc")
    ap.add_argument("--relief", type=float, default=0.0, help="cat urca si coboara terenul (m); 0 = plat")
    ap.add_argument("--netezime", type=float, default=250.0, help="lungimea dealurilor (m); mai mare = mai lin")
    ap.add_argument("--texturi", default="gta", choices=["gta", "simple"])
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=str(TOOLS.parent / "output" / "cartiere"))
    a = ap.parse_args(argv)
    seed = a.seed or random.randint(1, 99999)
    rng = random.Random(seed)
    t0 = time.time()

    bx, by = (float(v) for v in a.cvartal.lower().split("x"))
    rv, sv = TYPES[a.bulevard][:2]
    rh, sh = TYPES[a.strada][:2]
    wv, wh = rv + 2 * sv, rh + 2 * sh
    px, py = bx + wv, by + wh
    xs = [i * px - a.x * px / 2 for i in range(a.x + 1)]
    ys = [j * py - a.y * py / 2 for j in range(a.y + 1)]

    cli["clear_scene"]()
    name = f"cartier_{seed}"
    top = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(top)
    roads, lots, houses = (bpy.data.collections.new(n) for n in ("Strazi", "Curti si parcuri", "Cladiri"))
    for c in (roads, lots, houses):
        top.children.link(c)
    materials = gen["Materials"](a.texturi, random.Random(seed))

    cross = lambda m: st["intersection"](m, rv, sv, rh, sh)
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            add_piece(roads, materials, f"intersectie_{i}_{j}", cross, x, y)
            if j < a.y:
                add_piece(roads, materials, f"bulevard_{i}_{j}", straight(a.bulevard, by), x, (y + ys[j + 1]) / 2)
            if i < a.x:
                add_piece(roads, materials, f"strada_{i}_{j}", straight(a.strada, bx), (x + xs[i + 1]) / 2, y,
                          math.pi / 2)

    radius = math.hypot(xs[-1], ys[-1]) or 1.0
    count, kinds, parks = 0, {}, []
    for i in range(a.x):
        for j in range(a.y):
            x0, x1 = xs[i] + wv / 2, xs[i + 1] - wv / 2
            y0, y1 = ys[j] + wh / 2, ys[j + 1] - wh / 2
            lw, ld = x1 - x0, y1 - y0
            r = rng.random()
            kind = "inchis"
            for k, w in (("parc", a.parcuri), ("parcare", a.parcari), ("turn", a.turnuri), ("doua", a.doua_randuri)):
                if r < w:
                    kind = k
                    break
                r -= w
            if kind == "turn" and min(lw, ld) - 16.0 < 14.0:
                kind = "inchis"
            kinds[kind] = kinds.get(kind, 0) + 1
            draw, layout = lot_ground(x0, y0, x1, y1, kind, rng)
            add_piece(lots, materials, f"{kind}_{i}_{j}", draw, 0.0, 0.0, kind="curte")
            if layout is not None:
                parks.append(layout)
            if kind in ("parc", "parcare"):
                continue
            # mai inalt spre centru
            t = 1.0 - math.hypot((x0 + x1) / 2, (y0 + y1) / 2) / radius
            emax = a.etaje_min + round((a.etaje_max - a.etaje_min) * (0.35 + 0.65 * t))
            emin = max(a.etaje_min, emax - 3)
            if kind == "turn":
                s = min(min(lw, ld) - 16.0, 32.0)
                p = {"tip": "bloc", "latime": round(s * rng.uniform(0.8, 1.0), 1), "adancime": round(s, 1),
                     "etaje": emax + rng.randint(3, 8), "inaltime": 3.2, "acoperis": "plat", "interior": False,
                     "comercial": True, "texturi": a.texturi, "seed": rng.randrange(1, 99999),
                     "perete": rng.choice(WALLS), "rezervor": 0.3}
                obj, _inside = gen["build"](p)
                houses.objects.link(obj)
                obj.location = ((x0 + x1) / 2, (y0 + y1) / 2, ZS)
                count += 1
                continue
            d = rng.uniform(14.0, 18.0)
            if kind == "doua":
                d, sides = min(d, (ld - 6.0) / 2), False
            else:
                sides = ld >= 2 * d + 8 and lw >= 2 * d
                if not sides:
                    d = min(d, ld / 2)
            # (lungime, x, y, rotire, capete lipite): sud, nord, apoi est si vest intre ele
            rows = [(lw, (x0 + x1) / 2, y0, 0.0, (False, False)), (lw, (x0 + x1) / 2, y1, math.pi, (False, False))]
            if sides:
                rows += [(ld - 2 * d, x1, (y0 + y1) / 2, math.pi / 2, (True, True)),
                         (ld - 2 * d, x0, (y0 + y1) / 2, -math.pi / 2, (True, True))]
            for k, (length, rx, ry, angle, ends) in enumerate(rows):
                root = cli["row"](houses, length, d, emin, emax, a.texturi, False, rng.randrange(1, 99999), ends,
                                  jitter=(0.0, 0.0, -1.0, -2.0), name=f"cvartal_{i}_{j}_{k}", gaps=a.alei)
                root.location = (rx, ry, ZS)
                root.rotation_euler.z = angle
                count += len(root.children)
            print(f"CARTIER cvartal {i},{j} ({kind}): etaje {emin}-{emax} ({time.time() - t0:.0f} s)")

    h = heightfield(seed, a.relief, a.netezime)
    if h is not None:
        bpy.context.view_layer.update()
        for obj in list(roads.objects) + list(lots.objects):
            drape(obj, h)
        for obj in [o for o in houses.objects if o.get("harta_tip") == "cladire"]:
            settle(obj, h, houses, materials)
        # teren sub si in jurul cartierului, ca sa nu stea in aer
        mx0, mx1 = xs[0] - wv / 2 - 40.0, xs[-1] + wv / 2 + 40.0
        my0, my1 = ys[0] - wh / 2 - 40.0, ys[-1] + wh / 2 + 40.0
        ground = add_piece(lots, materials, "teren", lambda m: m.quad(
            Vector((mx0, my0, -0.03)), Vector((mx1, my0, -0.03)), Vector((mx1, my1, -0.03)),
            Vector((mx0, my1, -0.03)), "iarba"), 0.0, 0.0, kind="teren")
        drape(ground, h, max_edge=5.0)
        print(f"CARTIER relief +-{a.relief:g} m ({time.time() - t0:.0f} s)")

    if parks:
        greenery = bpy.data.collections.new("Vegetatie si mobilier")
        top.children.link(greenery)
        ground = (lambda x, y: h(x, y) + ZS) if h is not None else (lambda x, y: ZS)
        prng = random.Random(seed + 991)
        for L in parks:
            park_props(greenery, L, prng, ground)
        print(f"CARTIER parcuri: {len(greenery.objects)} props ({time.time() - t0:.0f} s)")

    size = (xs[-1] - xs[0] + wv, ys[-1] - ys[0] + wh)
    print(f"CARTIER {name}: {a.x} x {a.y} cvartale, {size[0]:.0f} x {size[1]:.0f} m, {count} cladiri, "
          f"{', '.join(f'{v} {k}' for k, v in sorted(kinds.items()))}, {time.time() - t0:.0f} s")
    print(f"CARTIER_FISIER {cli['save'](name, a.out)}")


if __name__ == "__main__":
    main()
