# -*- coding: utf-8 -*-
"""
Orasul desenat in editor (output/orase/<nume>.json) construit in Blender: strazi pe orice traseu, cu panta si
profilul lor (benzi, mediana, parcare), poduri si tuneluri, intersectii in orice unghi (tools/oras/plan_geom.py),
cvartale umplute dupa zona lor, suprafete desenate (parc, piateta, parcare, teren de sport, gazon, zone de
cladiri), apa cu chei, cladiri puse de mana, mobilier stradal automat, props pictate, teren. Iese in
output/orase/<nume>.glb + .blend.

    _blender.bat -b -P gen_oras.py -- --plan output/orase/oras.json
"""
import argparse
import bisect
import hashlib
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
from mathutils import Vector, geometry

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS / "oras"))
import plan_geom as G  # noqa: E402
import park_plan as PP  # noqa: E402

cart = runpy.run_path(str(TOOLS / "gen_cartier.py"), run_name="gen_oras")
st, cli, gen, props = cart["st"], cart["cli"], cart["gen"], cart["props"]
ZA, ZS, ZM, C = st["ZA"], st["ZS"], st["ZM"], st["C"]
# apa (doar previzualizare in Blender: marea din jur; in joc e marea GTA)
gen["SIMPLE_MATS"]["apa"] = ("apa", 12.0)
gen["SPECIAL_TEX"]["apa"] = lambda: np.ones((16, 16, 3)) * np.array([0.12, 0.3, 0.42])
gen["SIMPLE_MATS"]["nisip"] = ("nisip", 6.0)
gen["SPECIAL_TEX"]["nisip"] = lambda: np.ones((16, 16, 3)) * np.array([0.78, 0.7, 0.52])

# zonele si asezarea cladirilor: in tools/oras/layout.py, ca editorul de pe web sa arate aceleasi cladiri
import layout as LY  # noqa: E402
from layout import ZONES, in_rect, overlap, poly_overlap, rect, seg_dist  # noqa: E402,F401

# mobilier stradal automat (modele GTA din biblioteca)
FURNITURE = {"lampa": ["prop_streetlight_01"], "lampa_mare": ["prop_streetlight_03"], "semafor": ["prop_traffic_01a"],
             "hidrant": ["prop_fire_hydrant_1"], "cos": ["prop_bin_01a"], "ziare": ["prop_news_disp_02a", "prop_news_disp_03a"],
             "statie": ["prop_busstop_02"], "copac": ["prop_tree_birch_03", "prop_tree_birch_03b", "prop_tree_maple_03"]}   # coroane de 4-6 m, nu acopera strada
BASKET = "prop_basketball_net"
TUNNEL_H = 6.5       # inaltimea libera in tunel
DECK = 1.1           # grosimea podului


# ------------------------------------------------------------------------------------------ geometrie

def tri(m, poly, z, role, holes=(), down=False):
    """Poligon orizontal (orice forma, cu gauri) impartit in triunghiuri, cu fata in sus (sau in jos)."""
    loops = [[Vector((p[0], p[1], z)) for p in poly]] + [[Vector((p[0], p[1], z)) for p in h] for h in holes]
    pts = [p for loop in loops for p in loop]
    for a, b, c in geometry.tessellate_polygon(loops):
        pa, pb, pc = pts[a], pts[b], pts[c]
        if ((pb - pa).cross(pc - pa).z < 0) != down:
            pb, pc = pc, pb
        m.face([pa, pb, pc], role)


def skirt(m, poly, z0, z1, role):
    """Peretii de pe conturul unui poligon (sens trigonometric), cu fata spre exterior."""
    for p, q in zip(poly, poly[1:] + poly[:1]):
        st["vwall"](m, p, q, z0, z1, role, (q[1] - p[1], p[0] - q[0]))


def curb_walls(m, line, z0, z1, role, side):
    """Pereti verticali de-a lungul poliliniei, cu fata spre stanga (side=1) sau dreapta (-1) sensului."""
    for a, b in zip(line, line[1:]):
        d = (b[0] - a[0], b[1] - a[1])
        if math.hypot(*d) < 1e-6:
            continue
        n = (-d[1] * side, d[0] * side)
        st["vwall"](m, a, b, z0, z1, role, n)


def offset_line(line, dist):
    """Polilinia mutata la stanga cu dist (miter simplu)."""
    out = []
    for i, p in enumerate(line):
        a, b = line[max(i - 1, 0)], line[min(i + 1, len(line) - 1)]
        d = G.norm(G.sub(b, a))
        out.append(G.add(p, G.mul(G.left(d), dist)))
    return out


def offset_poly(poly, d):
    """Poligonul (sens trigonometric) marit spre exterior cu d m."""
    out, n = [], len(poly)
    for i in range(n):
        a, b, c = poly[i - 1], poly[i], poly[(i + 1) % n]
        d1, d2 = G.sub(b, a), G.sub(c, b)
        n1, n2 = G.right(G.norm(d1)), G.right(G.norm(d2))
        p1, p2 = G.add(a, G.mul(n1, d)), G.add(b, G.mul(n2, d))
        t = G.line_hit(p1, d1, p2, d2)
        X = G.add(p1, G.mul(d1, t)) if t is not None else G.add(b, G.mul(n1, d))
        if G.length(G.sub(X, b)) > 3 * d:
            X = G.add(b, G.mul(G.norm(G.add(n1, n2)), d))
        out.append(X)
    return G.untangle(out)


def obox(m, c, t, w, d, z0, z1, role):
    """Cutie rotita: w de-a lungul lui t, d de-a curmezisul, de la z0 la z1."""
    R = rect(c, t, G.left(t), w, d)
    m.face([Vector((p[0], p[1], z1)) for p in R], role)
    for p, q in zip(R, R[1:] + R[:1]):
        m.quad(Vector((p[0], p[1], z0)), Vector((q[0], q[1], z0)), Vector((q[0], q[1], z1)), Vector((p[0], p[1], z1)), role)


def lane_layout(T, M=None):
    """Benzile fiecarei jumatati de strada: {sg: (benzi, latime banda, parcare)}; sg -1 = stanga sensului a -> b
    (circula spre a), +1 = dreapta (spre b). M = marcajele strazii din plan (lipsa = tipul strazii)."""
    M = M or {}
    h = T["r"] / 2
    med = T.get("mediana", 0.0) if T.get("mediana", 0.0) > 0.5 else 0.0
    side = M.get("parcare") or ("ambele" if T.get("parcare") else "niciuna")
    out = {}
    for sg, key in ((-1, "st"), (1, "dr")):
        n = max(1, min(4, int((M.get("benzi") or {}).get(key) or T.get("benzi", 1))))
        park = 2.4 if side in ("ambele", key) else 0.0
        # parcarea oblica (45 de grade) cere 4.6 m: doar daca benzile raman de macar 2.75 m, altfel ramane paralela
        if park and M.get("parcare_stil") == "oblica" and (h - med / 2 - 4.6) / n >= 2.75:
            park = 4.6
        out[sg] = (n, (h - med / 2 - park) / n, park)
    return med, out


def profile_for(T, nivel="sol", M=None):
    """Sectiunea strazii dupa profil (benzi, mediana, parcare, marcaje); podurile au parapet si dedesubt.
    M = marcajele strazii din plan: linia din mijloc (dubla / simpla / intrerupta / niciuna), benzi pe fiecare
    sens, parcare pe o parte sau pe amandoua, bordura rosie / galbena."""
    M = M or {}
    h, s = T["r"] / 2, T["s"]
    W = h + s
    med, lanes = lane_layout(T, M)
    colors = {"rosie": "bordura_rosie", "galbena": "bordura_galbena"}
    curb = {sg: colors.get((M.get("bordura") or {}).get(key), "bordura") for sg, key in ((-1, "st"), (1, "dr"))}
    strips, walls = [], []
    if med:
        mrole = "iarba" if T.get("mediana_tip", "iarba") == "iarba" else "trotuar"
        strips += [(-h, -med / 2, ZA, "asfalt", None), (med / 2, h, ZA, "asfalt", None), (-med / 2, med / 2, ZS, mrole, None)]
        walls += [(-med / 2, ZA, ZS, -1, "bordura"), (med / 2, ZA, ZS, 1, "bordura")]
    else:
        strips.append((-h, h, ZA, "asfalt", None))
    strips += [(-h - C, -h, ZS, curb[-1], None), (h, h + C, ZS, curb[1], None),
               (-W, -h - C, ZS, "trotuar", None), (h + C, W, ZS, "trotuar", None)]
    if T.get("marcaj", True):
        centre = M.get("centru", "dubla")
        if not med and centre == "dubla":
            strips += [(-0.22, -0.1, ZM, "marcaj_galben", None), (0.1, 0.22, ZM, "marcaj_galben", None)]
        elif not med and centre in ("simpla", "intrerupta"):
            strips.append((-0.07, 0.07, ZM, "marcaj_galben", (3.0, 6.0) if centre == "intrerupta" else None))
        bus = M.get("bus") or ""
        for sg, (n, lw, park) in lanes.items():
            for k in range(1, n):
                x = sg * (med / 2 + k * lw)
                if k == n - 1 and bus in ("ambele", "dr" if sg > 0 else "st"):
                    strips.append((x - 0.12, x + 0.12, ZM, "marcaj_alb", None))     # banda de autobuz: linie plina lata
                else:
                    strips.append((x - 0.07, x + 0.07, ZM, "marcaj_alb", (2.5, 5.0)))
            if park:
                x = sg * (h - park)
                strips.append((x - 0.07, x + 0.07, ZM, "marcaj_alb", None))
    bottom = -DECK if nivel == "pod" else -0.5
    top = ZS + 1.0 if nivel == "pod" else ZS
    walls += [(-h, ZA, ZS, 1, curb[-1]), (h, ZA, ZS, -1, curb[1]),
              (-W, bottom, top, -1, "trotuar"), (W, bottom, top, 1, "trotuar")]
    if nivel == "pod":
        i = W - 0.25
        walls += [(-i, ZS, ZS + 1.0, 1, "bordura"), (i, ZS, ZS + 1.0, -1, "bordura")]
        strips += [(-W, -i, ZS + 1.0, "bordura", None), (i, W, ZS + 1.0, "bordura", None),
                   (W, -W, bottom, "soclu", None)]        # dedesubtul podului (x descrescator = fata in jos)
    return strips, walls


def bend_marks(m, J, strips):
    """Marcajele peste un cot (nod cu doua strazi): acolo asfaltul e al intersectiei si linia din mijloc se oprea.
    Curba merge de la capatul unui brat la al celuilalt pe langa nod (Bezier patratica); doar liniile continue."""
    (a, b) = J["brate"]
    Ea, Eb, P = a["E"], b["E"], (J["x"], J["y"])
    z = J["z"] + ZM
    n_seg = 12
    pts, dirs = [], []
    for k in range(n_seg + 1):
        t = k / n_seg
        pts.append(tuple((1 - t) ** 2 * Ea[i] + 2 * (1 - t) * t * P[i] + t * t * Eb[i] for i in range(2)))
        d = tuple(2 * (1 - t) * (P[i] - Ea[i]) + 2 * t * (Eb[i] - P[i]) for i in range(2))
        ln = math.hypot(*d) or 1.0
        dirs.append((d[0] / ln, d[1] / ln))
    for x0, x1, _z, role, dash in strips:
        if dash or not role.startswith("marcaj"):
            continue
        for k in range(n_seg):
            (pa, da), (pb, db) = (pts[k], dirs[k]), (pts[k + 1], dirs[k + 1])
            na, nb = G.left(da), G.left(db)
            q = [G.add(pa, G.mul(na, x0)), G.add(pb, G.mul(nb, x0)), G.add(pb, G.mul(nb, x1)), G.add(pa, G.mul(na, x1))]
            m.face([Vector((p[0], p[1], z)) for p in q], role)


RAMP = 0.8      # cat intra in strada bordura coborata de la capetele trecerii


def curb_ramps(m, E, e, n, h, z):
    """Bordura coborata la capetele trecerii de pietoni: panta din asfalt pana sus pe trotuar, cat trecerea."""
    u0, u1 = 0.45, G.ZEBRA - 0.45
    for sg in (-1, 1):
        def P(u, x, zz, sg=sg):
            p = G.add(G.add(E, G.mul(e, -u)), G.mul(n, sg * x))
            return Vector((p[0], p[1], zz))
        top = [P(u0, h - RAMP, z + ZA), P(u1, h - RAMP, z + ZA), P(u1, h, z + ZS), P(u0, h, z + ZS)]
        if (top[1] - top[0]).cross(top[2] - top[0]).z < 0:
            top = top[::-1]
        m.face(top, "trotuar")
        # laturile pantei: spre E la u0, spre intersectie la u1
        for u, out in ((u0, 1.0), (u1, -1.0)):
            side = [P(u, h - RAMP, z + ZA), P(u, h, z + ZA), P(u, h, z + ZS)]
            if (side[1] - side[0]).cross(side[2] - side[0]).dot(Vector((e[0], e[1], 0.0)) * out) < 0:
                side = side[::-1]
            m.face(side, "trotuar")


def junction_mesh(m, J, bend_strips=None):
    if bend_strips and len(J["brate"]) == 2:
        bend_marks(m, J, bend_strips)
    z = J["z"]
    low = -DECK if J.get("nivel") == "pod" else -0.5
    tri(m, J["asfalt"], z + ZA, "asfalt")
    for walk in J["trotuare"]:
        tri(m, walk["poligon"], z + ZS, "trotuar")
        curb = walk["bordura"]
        on_curb = {(round(p[0], 3), round(p[1], 3)) for p in curb}
        poly = walk["poligon"]
        for p, q in zip(poly, poly[1:] + poly[:1]):
            if (round(p[0], 3), round(p[1], 3)) in on_curb and (round(q[0], 3), round(q[1], 3)) in on_curb:
                continue
            st["vwall"](m, p, q, z + low, z + ZS, "trotuar", (q[1] - p[1], p[0] - q[0]))
        if J.get("nivel") == "pod":
            tri(m, poly, z + low, "soclu", down=True)
        # bordura merge in jurul intersectiei (asfaltul in stanga): perete spre asfalt, dunga de beton deasupra
        curb_walls(m, curb, z + ZA, z + ZS, "bordura", 1)
        inner = offset_line(curb, -C)
        for (a, b), (c, d) in zip(zip(curb, curb[1:]), zip(inner, inner[1:])):
            m.quad(Vector((a[0], a[1], z + ZS + 0.004)), Vector((c[0], c[1], z + ZS + 0.004)),
                   Vector((d[0], d[1], z + ZS + 0.004)), Vector((b[0], b[1], z + ZS + 0.004)), "bordura")
    if J.get("nivel") == "pod":
        tri(m, J["asfalt"], z + low, "soclu", down=True)
    for arm in J["brate"]:
        if not arm["zebra"]:
            continue
        E, e, h = arm["E"], arm["e"], arm["h"]
        n = G.left(e)
        curb_ramps(m, E, e, n, h, z)
        if arm.get("zebra_stil") == "linii":
            # trecere cu doua linii transversale (fara dungi)
            for u0 in (G.ZEBRA - 0.35, 0.65):
                p0, p1 = G.add(E, G.mul(e, -u0)), G.add(E, G.mul(e, -(u0 - 0.3)))
                q = [G.add(p0, G.mul(n, -h + 0.3)), G.add(p0, G.mul(n, h - 0.3)), G.add(p1, G.mul(n, h - 0.3)),
                     G.add(p1, G.mul(n, -h + 0.3))]
                if (q[1][0] - q[0][0]) * (q[2][1] - q[0][1]) - (q[1][1] - q[0][1]) * (q[2][0] - q[0][0]) < 0:
                    q = q[::-1]
                m.face([Vector((p[0], p[1], z + ZM)) for p in q], "marcaj_alb")
            continue
        x = -h + 0.4
        while x + 0.5 <= h - 0.4 + 1e-6:
            p0 = G.add(E, G.mul(e, -(G.ZEBRA - 0.35)))
            p1 = G.add(E, G.mul(e, -0.35))
            q = [G.add(p0, G.mul(n, x)), G.add(p0, G.mul(n, x + 0.5)), G.add(p1, G.mul(n, x + 0.5)), G.add(p1, G.mul(n, x))]
            if (q[1][0] - q[0][0]) * (q[2][1] - q[0][1]) - (q[1][1] - q[0][1]) * (q[2][0] - q[0][0]) < 0:
                q = q[::-1]
            m.face([Vector((p[0], p[1], z + ZM)) for p in q], "marcaj_alb")
            x += 1.0


def road_mesh(m, R, T, open_a, open_b):
    samples = [(Vector((s[0], s[1])), Vector((s[3], s[4])), s[5], s[2]) for s in R["samples"]]
    M = R.get("marcaje") or {}
    st["sweep"](m, samples, profile_for(T, R["nivel"], M), (open_a, open_b))
    if T.get("marcaj", True):
        road_marks(m, R, T, M, open_a, open_b)


# sagetile de pe asfalt, in metri: u de-a lungul benzii (spre intersectie, varful la u = 3.2), v spre stanga
_SHAFT = [(0.0, -0.08), (2.0, -0.08), (2.0, 0.08), (0.0, 0.08)]
_HEAD = [(2.0, -0.32), (3.2, 0.0), (2.0, 0.32)]
_LEFT = [[(1.2, 0.0), (1.5, 0.0), (1.5, 0.62), (1.2, 0.62)], [(1.0, 0.62), (1.7, 0.62), (1.35, 1.2)]]
ARROWS = {"fata": [_SHAFT, _HEAD], "stanga": [_SHAFT[:1] + [(1.5, -0.08), (1.5, 0.08)] + _SHAFT[3:]] + _LEFT}
ARROWS["dreapta"] = [[(u, -v) for u, v in part] for part in ARROWS["stanga"]]
ARROWS["stanga_fata"] = ARROWS["fata"] + _LEFT
ARROWS["fata_dreapta"] = ARROWS["fata"] + [[(u, -v) for u, v in part] for part in _LEFT]


def _lane_arrows(n, mode):
    """Sageata fiecarei benzi (de la cea de langa mijloc la cea de langa trotuar) dupa alegerea din editor."""
    if mode == "fata":
        return ["fata"] * n
    if mode == "stanga":
        return ["stanga"] + ["fata"] * (n - 1) if n > 1 else ["stanga_fata"]
    if mode == "dreapta":
        return ["fata"] * (n - 1) + ["dreapta"] if n > 1 else ["fata_dreapta"]
    if mode == "banda":
        if n == 1:
            return ["stanga_fata"]
        if n == 2:
            return ["stanga", "fata_dreapta"]
        return ["stanga"] + ["fata"] * (n - 2) + ["dreapta"]
    return []


# literele de pe asfalt (STOP, SLOW, BUS): 3 x 5 casute, randul 0 = sus (spre intersectie)
FONT = {"S": ("111", "100", "111", "001", "111"), "T": ("111", "010", "010", "010", "010"),
        "O": ("111", "101", "101", "101", "111"), "P": ("111", "101", "111", "100", "100"),
        "B": ("110", "101", "110", "101", "110"), "U": ("101", "101", "101", "101", "111"),
        "L": ("100", "100", "100", "100", "111"), "W": ("101", "101", "101", "111", "101")}


def road_text(put, at, word, s_far, fwd, xc, width, length=2.6):
    """Un cuvant pe banda, citit de soferul care vine spre capat: literele de la stanga la dreapta pe latimea
    benzii, lungite de-a lungul ei (ca in joc). s_far = marginea de sus (spre intersectie), xc = mijlocul benzii."""
    cols = len(word) * 4 - 1
    cw, ch = min(width * 0.8 / cols, 0.2), length / 5
    v0 = cols * cw / 2                   # marginea din stanga soferului
    for i, letter in enumerate(word):
        for r, row in enumerate(FONT.get(letter, ())):
            c = 0
            while c < 3:
                if row[c] != "1":
                    c += 1
                    continue
                c1 = c
                while c1 < 3 and row[c1] == "1":
                    c1 += 1
                va, vb = v0 - (i * 4 + c) * cw, v0 - (i * 4 + c1) * cw
                da, db = r * ch, (r + 1) * ch
                put([at(s_far - fwd * da, xc - fwd * va, 0.002), at(s_far - fwd * da, xc - fwd * vb, 0.002),
                     at(s_far - fwd * db, xc - fwd * vb, 0.002), at(s_far - fwd * db, xc - fwd * va, 0.002)])
                c = c1


def road_marks(m, R, T, M, open_a, open_b):
    """Ce se pune pe asfalt peste profil: linia de stop si sagetile la capatul fiecarui sens (spre intersectia lui),
    liniutele locurilor de parcare. x spre dreapta sensului a -> b, ca in gen_strada.sweep."""
    smp = R["samples"]
    if len(smp) < 2:
        return
    ss = [p[5] for p in smp]

    base = _sampler(smp)

    def at(s, x, dz=0.0):
        return base(s, x, ZM + dz)

    def put(pts, role="marcaj_alb"):
        area = sum(p.x * q.y - q.x * p.y for p, q in zip(pts, pts[1:] + pts[:1]))
        m.face(pts if area > 0 else pts[::-1], role)

    h = T["r"] / 2
    med, lanes = lane_layout(T, M)
    length = ss[-1] - ss[0]
    for end, sg, closed in (("a", -1, open_a), ("b", 1, open_b)):
        if closed:          # capat de strada fara intersectie: nici stop, nici sageti
            continue
        n, lw, park = lanes[sg]
        # sensul care ajunge la capatul asta: la b merge pe dreapta (x > 0) spre +s, la a pe stanga spre -s
        fwd = 1.0 if end == "b" else -1.0
        s_end = ss[-1] if end == "b" else ss[0]
        inner = med / 2 + (0.25 if not med else 0.1)
        if (M.get("stop") or {}).get(end) and length > 4.0:
            s0, s1 = s_end - fwd * 0.75, s_end - fwd * 0.35
            x0, x1 = sg * inner, sg * (h - park - 0.1)
            put([at(s0, x0), at(s0, x1), at(s1, x1), at(s1, x0)])
        # scris pe fiecare banda intre linia de stop si sageti (sagetile incep la 6 m)
        word = str((M.get("scris") or {}).get(end) or "").upper()
        if word and length > 10.0:
            for k in range(n):
                road_text(put, at, word, s_end - fwd * 1.4, fwd, sg * (med / 2 + (k + 0.5) * lw), lw)
        kinds = _lane_arrows(n, (M.get("viraj") or {}).get(end))
        if kinds and length > 14.0:
            tip_s = s_end - fwd * 6.0
            for k, kind in enumerate(kinds):
                xc = sg * (med / 2 + (k + 0.5) * lw)
                for part in ARROWS[kind]:
                    # u spre intersectie, v spre stanga mersului (la b: -x, la a: +x)
                    put([at(tip_s - fwd * (3.2 - u), xc - fwd * v, 0.002) for u, v in part])
    bus = M.get("bus") or ""
    for sg, (n, lw, park) in lanes.items():
        d = 1.0 if sg > 0 else -1.0          # sensul de mers pe partea asta
        if park and length > 12.0:
            x0, x1 = sg * (h - park), sg * (h - 0.05)
            if park > 3.0:
                # parcare oblica (lane_layout i-a facut loc): linii la 45 de grade, masina intra cu fata, din mers
                s = ss[0] + 3.0 + park
                while s < ss[-1] - 3.0 - park:
                    put([at(s - 0.07, x0), at(s + d * park - 0.07, x1), at(s + d * park + 0.07, x1), at(s + 0.07, x0)])
                    s += 3.5
            else:
                s = ss[0] + 3.0
                while s < ss[-1] - 3.0:
                    put([at(s - 0.05, x0), at(s - 0.05, x1), at(s + 0.05, x1), at(s + 0.05, x0)])
                    s += 5.5
        # banda de autobuz: BUS pe banda de langa trotuar, din 60 in 60 m (linia plina e in profile_for)
        if bus in ("ambele", "dr" if sg > 0 else "st") and length > 30.0:
            xc = sg * (med / 2 + (n - 0.5) * lw)
            s = ss[0] + 15.0
            while s < ss[-1] - 15.0:
                road_text(put, at, "BUS", s + d * 1.3, d, xc, lw)
                s += 60.0


def _sampler(smp):
    """at(s, x, z): punctul strazii la s metri de-a lungul ei, x spre dreapta sensului a -> b, z peste axa ei."""
    ss = [p[5] for p in smp]

    def at(s, x, z=0.0):
        s = min(max(s, ss[0]), ss[-1])
        k = min(max(bisect.bisect_right(ss, s) - 1, 0), len(smp) - 2)
        a, b = smp[k], smp[k + 1]
        t = (s - a[5]) / max(b[5] - a[5], 1e-9)
        px, py, pz = (a[i] + (b[i] - a[i]) * t for i in range(3))
        dx, dy = a[3] + (b[3] - a[3]) * t, a[4] + (b[4] - a[4]) * t
        ln = math.hypot(dx, dy) or 1.0
        dx, dy = dx / ln, dy / ln
        return Vector((px + dy * x, py - dx * x, pz + z))
    return at


# ------------------------------------------------------------------------------------------ uzura asfaltului

# cat de des apar fisurile, petele si peticele (marcaje.uzura pe strada, plan.uzura pentru tot orasul)
WEAR = {"niciuna": 0.0, "putina": 0.5, "normala": 1.0, "multa": 2.0}
# inaltimea fiecarui fel peste asfalt (ZA), sub marcaje (ZM); cele mici deasupra celor mari
WEAR_Z = {"uzura_petic1": 0.003, "uzura_petic2": 0.003, "uzura_petic3": 0.003, "uzura_margine": 0.004,
          "uzura_fisuri": 0.005, "uzura_pete": 0.006, "uzura_ulei": 0.007, "uzura_canal": 0.008}
PATCHES = ("uzura_petic1", "uzura_petic2", "uzura_petic3")


# uzura strazilor si intersectiilor fata de WEAR: "normala" la 1.0 iesea prea multa in joc
ROAD_WEAR = 0.6


def wear_level(M, default="normala"):
    return WEAR.get((M or {}).get("uzura") or default, 1.0) * ROAD_WEAR


def decal(m, pos, role, uv=(0.0, 0.0, 1.0, 1.0), fade=(0.0, 0.0), alpha=1.0, flip=None):
    """Un decal pe asfalt. pos(u, v) -> punctul (u de-a lungul, v de-a curmezisul, 0..1); uv = dreptunghiul din
    textura (u0, v0, u1, v1). fade = cat din fiecare latura se estompeaza din alfa varfurilor (asa isi ascunde
    jocul marginile peticelor si ale capacelor, care n-au transparenta in textura). flip = None: fata in sus
    (dupa sensul din plan); pe pereti se da explicit."""
    tu = [0.0, fade[0], 1.0 - fade[0], 1.0] if fade[0] > 0 else [0.0, 1.0]
    tv = [0.0, fade[1], 1.0 - fade[1], 1.0] if fade[1] > 0 else [0.0, 1.0]

    def a_of(a, b):
        edge = (fade[0] > 0 and a in (0.0, 1.0)) or (fade[1] > 0 and b in (0.0, 1.0))
        return 0.0 if edge else alpha

    for i in range(len(tu) - 1):
        for j in range(len(tv) - 1):
            cs = [(tu[i], tv[j]), (tu[i + 1], tv[j]), (tu[i + 1], tv[j + 1]), (tu[i], tv[j + 1])]
            pts = [pos(a, b) for a, b in cs]
            uvs = [(uv[0] + (uv[2] - uv[0]) * a, uv[1] + (uv[3] - uv[1]) * b) for a, b in cs]
            als = [a_of(a, b) for a, b in cs]
            if flip is None:    # o data pe decal, dupa primul patrat
                flip = sum(p.x * q.y - q.x * p.y for p, q in zip(pts, pts[1:] + pts[:1])) < 0
            if flip:
                pts, uvs, als = pts[::-1], uvs[::-1], als[::-1]
            m.face(pts, role, uv=uvs, alpha=als)


def road_wear(m, R, T, M, dead, seed, default="normala"):
    """Uzura asfaltului pe o strada, cu decalurile jocului: pete de ulei pe mijlocul benzilor (mai dese inainte de
    intersectie, unde se asteapta), fisuri, petice, margine rupta langa bordura, capace de canal si guri de scurgere
    inainte de colt. Aleatoare, dar la fel la fiecare generare (seed = strada). dead = capetele fara intersectie."""
    f = wear_level(M, default)
    smp = R["samples"]
    if f <= 0 or len(smp) < 2:
        return
    base = _sampler(smp)
    s0, s1 = smp[0][5], smp[-1][5]
    L = s1 - s0
    if L < 6.0:
        return
    rng = random.Random(f"uzura:{seed}")
    has = m.materials.has
    h = T["r"] / 2
    med, lanes = lane_layout(T, M)

    def put(role, s, x, length, width, ang=0.0, uv=(0.0, 0.0, 1.0, 1.0), fade=(0.0, 0.0)):
        if not has(role):
            return
        ca, sa = math.cos(ang), math.sin(ang)
        dz = ZA + WEAR_Z[role]

        def pos(u, v):
            du, dv = (u - 0.5) * length, (v - 0.5) * width
            return base(s + du * ca - dv * sa, x + du * sa + dv * ca, dz)
        decal(m, pos, role, uv, fade)

    drive = [(sg, sg * (med / 2 + (k + 0.5) * lw), lw) for sg, (n, lw, _p) in lanes.items() for k in range(n)]
    # pete pe mijlocul benzilor: masinile picura pe unde merg
    for sg, xc, lw in drive:
        s = s0 + rng.uniform(2.0, 12.0) / f
        while s < s1 - 3.0:
            u0 = rng.random() * 0.5
            put("uzura_pete", s, xc + rng.uniform(-0.2, 0.2), rng.uniform(3.0, 6.0), min(1.5, lw * 0.5),
                uv=(u0, 0.0, u0 + 0.5, 1.0), fade=(0.15, 0.25))
            s += rng.uniform(10.0, 24.0) / f
    # la intersectie: coada de la semafor (pete mai dese, ulei unde sta motorul) si gura de scurgere langa bordura
    for end, sg, closed in (("a", -1, dead[0]), ("b", 1, dead[1])):
        if closed or L < 12.0:
            continue
        fwd = 1.0 if end == "b" else -1.0
        s_end = s1 if end == "b" else s0
        n, lw, park = lanes[sg]
        for k in range(n):
            xc = sg * (med / 2 + (k + 0.5) * lw)
            for d in (rng.uniform(2.0, 3.5), rng.uniform(8.0, 10.0)):
                if rng.random() < min(1.0, 0.7 * f):
                    put("uzura_pete", s_end - fwd * d, xc, 3.0, min(1.5, lw * 0.5), fade=(0.2, 0.25))
            if rng.random() < min(1.0, 0.5 * f):
                put("uzura_ulei", s_end - fwd * rng.uniform(2.0, 4.0), xc + rng.uniform(-0.3, 0.3), 1.6, 1.6,
                    ang=rng.uniform(0.0, math.tau))
        if rng.random() < 0.8:
            put("uzura_canal", s_end - fwd * 2.5, sg * (h - 0.4), 0.8, 0.8, uv=(0.5, 0.5, 1.0, 1.0))
    # fisuri oriunde pe carosabil (nu pe mediana)
    for _ in range(int(L / 14.0 * f + rng.random())):
        x = rng.uniform(-h + 0.4, h - 0.4)
        if med and abs(x) < med / 2 + 0.3:
            continue
        size, u0, v0 = rng.uniform(1.8, 2.6), rng.choice((0.0, 0.5)), rng.choice((0.0, 0.5))
        put("uzura_fisuri", rng.uniform(s0 + 2.0, s1 - 2.0), x, size, size, ang=rng.uniform(0.0, math.tau),
            uv=(u0, v0, u0 + 0.5, v0 + 0.5), fade=(0.1, 0.1))
    # petice de asfalt reparat, pe urma rotilor; bucata din textura cat petecul (textura ~4 m)
    kinds = [r for r in PATCHES if has(r)]
    for _ in range(int(L / 45.0 * f + rng.random()) if kinds else 0):
        sg, xc, lw = rng.choice(drive)
        length, width = rng.uniform(1.8, 5.0), rng.uniform(1.2, max(1.3, min(lw - 0.4, 2.8)))
        eu, ev = min(1.0, length / 4.0), min(1.0, width / 4.0)
        u0, v0 = rng.uniform(0.0, 1.0 - eu), rng.uniform(0.0, 1.0 - ev)
        put(rng.choice(kinds), rng.uniform(s0 + 3.0, s1 - 3.0), xc + rng.uniform(-0.4, 0.4), length, width,
            uv=(u0, v0, u0 + eu, v0 + ev), fade=(min(0.3, 0.5 / length), min(0.3, 0.5 / width)))
    # marginea rupta langa bordura: textura are partea opaca jos (v = 0, spre bordura), zimtii transparenti sus
    for sg in (-1, 1):
        s = s0 + rng.uniform(0.5, 8.0) / f
        while s < s1 - 2.0:
            length = min(rng.uniform(4.0, 9.0), s1 - 1.0 - s)
            if length > 1.5:
                u0 = rng.random()
                v0, v1 = (1.0, 0.0) if sg > 0 else (0.0, 1.0)
                put("uzura_margine", s + length / 2, sg * (h - 0.47), length, 0.9,
                    uv=(u0, v0, u0 + length / 3.6, v1), fade=(min(0.3, 1.0 / length), 0.0))
            s += length + rng.uniform(6.0, 20.0) / f
    # ulei pe locurile de parcare
    for sg, (n, lw, park) in lanes.items():
        s = s0 + 5.75
        while park and s < s1 - 3.0:
            if rng.random() < 0.3 * f:
                put("uzura_ulei", s + rng.uniform(-1.0, 1.0), sg * (h - park / 2), 1.5, 1.5,
                    ang=rng.uniform(0.0, math.tau))
            s += 5.5
    # capace de canal pe mijlocul unei benzi, la 40-75 m
    s = s0 + rng.uniform(8.0, 30.0)
    while s < s1 - 6.0:
        sg, xc, lw = rng.choice(drive)
        put("uzura_canal", s, xc + rng.uniform(-0.3, 0.3), 1.1, 1.1, uv=(0.0, 0.5, 0.5, 1.0))
        s += rng.uniform(40.0, 75.0)


def junction_wear(m, J, f, seed):
    """Uzura in intersectie: fisuri, pete (masinile care vireaza si asteapta), cate un petic."""
    poly = J["asfalt"]
    if f <= 0 or len(poly) < 3:
        return
    has = m.materials.has
    rng = random.Random(f"uzura:{seed}")
    xs, ys = [p[0] for p in poly], [p[1] for p in poly]
    area = abs(G.area(poly))
    z = J["z"] + ZA

    def spot():
        for _ in range(20):
            p = (rng.uniform(min(xs), max(xs)), rng.uniform(min(ys), max(ys)))
            if G.inside(p, poly):
                return p
        return None

    def put(role, p, length, width, uv=(0.0, 0.0, 1.0, 1.0), fade=(0.0, 0.0)):
        if p is None or not has(role):
            return
        ang = rng.uniform(0.0, math.tau)
        ca, sa, zz = math.cos(ang), math.sin(ang), z + WEAR_Z[role]

        def pos(u, v):
            du, dv = (u - 0.5) * length, (v - 0.5) * width
            return Vector((p[0] + du * ca - dv * sa, p[1] + du * sa + dv * ca, zz))
        decal(m, pos, role, uv, fade)

    for _ in range(int(area / 110.0 * f + rng.random())):
        size, u0, v0 = rng.uniform(1.8, 2.6), rng.choice((0.0, 0.5)), rng.choice((0.0, 0.5))
        put("uzura_fisuri", spot(), size, size, (u0, v0, u0 + 0.5, v0 + 0.5), (0.1, 0.1))
    for _ in range(int(area / 80.0 * f + rng.random())):
        u0 = rng.random() * 0.5
        put("uzura_pete", spot(), rng.uniform(2.5, 4.5), 1.4, (u0, 0.0, u0 + 0.5, 1.0), (0.2, 0.25))
    # fara petice: in intersectie n-au o directie a lor si, rotite la intamplare, pareau pete negre (randare de test)


# ------------------------------------------------------------------------------------------ pete pe iarba

# (rol, marime min, max, pondere, moale): moale = textura fara transparenta (DXT1), marginile se estompeaza din alfa
# varfurilor si se ia o bucata aleatoare din ea; celelalte au forma lor in alfa si se pun intregi
GRASS_SPOTS = (("pata_pamant1", 2.0, 4.5, 3, False), ("pata_pamant2", 2.5, 6.0, 3, True),
               ("pata_pamant3", 3.0, 7.0, 2, True), ("pata_frunze1", 3.0, 7.0, 2, True),
               ("pata_frunze2", 2.5, 5.0, 2, True), ("pata_urma", 1.5, 3.0, 2, False))
# peste iarba: destul cat sa nu clipeasca (placa e lipita de teren din 4 in 4 m), fiecare fel la alta inaltime
GRASS_Z = {k[0]: 0.04 + 0.005 * i for i, k in enumerate(GRASS_SPOTS)}
GRASS_SPOTS_V = 1       # intra in hash-ul cvartalelor: schimbat = toate se refac o data


def near_line(p, pts, d):
    """p e la mai putin de d de linia frant pts."""
    for a, b in zip(pts, pts[1:]):
        abx, aby = b[0] - a[0], b[1] - a[1]
        t = min(1.0, max(0.0, ((p[0] - a[0]) * abx + (p[1] - a[1]) * aby) / max(abx * abx + aby * aby, 1e-9)))
        if math.hypot(a[0] + abx * t - p[0], a[1] + aby * t - p[1]) < d:
            return True
    return False


def grass_spots(m, poly, f, seed, skip, z):
    """Pete pe iarba unui cvartal / parc, cu decalurile jocului: pamant batatorit, frunze, urme. In grupuri de 1-3
    (ca in joc, unde pamantul si frunzele stau impreuna), cam un grup la 150 m2 (f = plan.uzura). skip(x, y) = unde
    nu se pune (apa, strazi, suprafete desenate). Varfurile stau la z; drape le lipeste apoi de teren."""
    has = m.materials.has
    kinds = [k for k in GRASS_SPOTS if has(k[0])]
    area = abs(G.area(poly))
    if f <= 0 or not kinds or area < 40.0:
        return
    rng = random.Random(f"iarba:{seed}")
    xs, ys = [p[0] for p in poly], [p[1] for p in poly]
    weights = [k[3] for k in kinds]
    for _ in range(int(area / 150.0 * f + rng.random())):
        p = None
        for _try in range(10):
            q = (rng.uniform(min(xs), max(xs)), rng.uniform(min(ys), max(ys)))
            if G.inside(q, poly) and not skip(*q):
                p = q
                break
        if p is None:
            continue
        for k in range(rng.choice((1, 1, 2, 3))):
            role, lo, hi, _w, soft = rng.choices(kinds, weights)[0]
            c = (p[0] + rng.uniform(-2.5, 2.5), p[1] + rng.uniform(-2.5, 2.5)) if k else p
            length = rng.uniform(lo, hi)
            width = length * (0.5 if role == "pata_urma" else rng.uniform(0.6, 1.0))
            ang = rng.uniform(0.0, math.tau)
            ca, sa, zz = math.cos(ang), math.sin(ang), z + GRASS_Z[role] + 0.002 * k
            # toata pata pe iarba: colturile (cu 1 m in plus) in suprafata si nu pe strada / apa (altfel iese pe trotuar)
            corners = [(c[0] + du * ca - dv * sa, c[1] + du * sa + dv * ca)
                       for du in (-length / 2 - 1.0, length / 2 + 1.0) for dv in (-width / 2 - 1.0, width / 2 + 1.0)]
            if any(not G.inside(q, poly) or skip(*q) for q in corners + [c]):
                continue
            if soft:
                e = rng.uniform(0.4, 0.8)
                u0, v0 = rng.uniform(0.0, 1.0 - e), rng.uniform(0.0, 1.0 - e)
                uv, fade, alpha = (u0, v0, u0 + e, v0 + e * width / length), (0.35, 0.35), rng.uniform(0.7, 0.95)
            else:
                uv, fade, alpha = (0.0, 0.0, 1.0, 1.0), (0.1, 0.1), 1.0

            def pos(u, v, c=c, length=length, width=width, ca=ca, sa=sa, zz=zz):
                du, dv = (u - 0.5) * length, (v - 0.5) * width
                return Vector((c[0] + du * ca - dv * sa, c[1] + du * sa + dv * ca, zz))
            decal(m, pos, role, uv, fade, alpha)


def _smooth(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)


def paint_blend(obj):
    """Iarba amestecata (Color 2, vezi Materials._terrain): zgomot pe coordonatele lumii, deci placile vecine se
    continua fara cusatura. Albastru = alta iarba in pete mari (si frunze in loc de pamant); verde = pamant sau
    frunze, mai rar. Obiectele fara Color 2 (fara iarba amestecata) raman cum sunt."""
    from mathutils import noise as mnoise
    me = obj.data
    col = me.color_attributes.get("Color 2")
    if col is None or not me.loops:
        return
    mw = obj.matrix_world
    co = np.empty(len(me.vertices) * 3, dtype=np.float32)
    me.vertices.foreach_get("co", co)
    vb, vg = [], []
    for p in co.reshape(-1, 3):
        w = mw @ Vector(p)
        big = mnoise.noise(Vector((w.x / 30.0, w.y / 30.0, 1.7))) + 0.4 * mnoise.noise(Vector((w.x / 9.0, w.y / 9.0, 4.1)))
        dirt = mnoise.noise(Vector((w.x / 17.0, w.y / 17.0, 8.3))) + 0.35 * mnoise.noise(Vector((w.x / 5.0, w.y / 5.0, 2.9)))
        vb.append(_smooth(-0.05, 0.45, big))
        vg.append(_smooth(0.3, 0.7, dirt) * 0.85)
    vi = np.empty(len(me.loops), dtype=np.int32)
    me.loops.foreach_get("vertex_index", vi)
    rgba = np.zeros((len(me.loops), 4), dtype=np.float32)
    rgba[:, 2] = np.array(vb, dtype=np.float32)[vi]
    rgba[:, 1] = np.array(vg, dtype=np.float32)[vi]
    rgba[:, 3] = 1.0
    col.data.foreach_set("color_srgb", rgba.ravel())


# ------------------------------------------------------------------------------------------ murdarie pe cladiri

# dare de apa sub ferestre si de sub streasina, murdaria de la baza peretilor: decalurile jocului (decal.sps)
GRIME_DRIPS = ("murdarie_dare1", "murdarie_dare2", "murdarie_dare3", "murdarie_dare4")
GRIME_V = 3             # intra in hash-ul cvartalelor si al cladirilor puse de mana: schimbat = se refac o data
WALL_OUT = 0.025        # cat sta decalul in fata peretelui (sa nu clipeasca)
WINDOWS = ("geam", "geam_noapte", "sticla")


def wall_decal(m, p, n, w, h, role, uv=(0.0, 0.0, 1.0, 1.0), fade=(0.0, 0.0), alpha=1.0):
    """Decal pe un perete vertical: p = mijlocul lui pe perete, n = normala orizontala spre afara."""
    t = Vector((-n.y, n.x, 0.0))
    base = p + n * WALL_OUT

    def pos(u, v):
        return base + t * ((u - 0.5) * w) + Vector((0.0, 0.0, (v - 0.5) * h))
    decal(m, pos, role, uv, fade, alpha, flip=False)     # t x sus = n: fata spre afara


def building_grime(m, obj, f, seed):
    """Murdarie pe o cladire generata (in coordonatele ei): o dunga murdara la baza peretilor, dare de sub
    streasina si sub unele ferestre. Peretii si ferestrele se afla dupa rolurile materialelor (harta_roluri); doar
    fetele care dau afara (nimic din cladire in fata lor pe 15 m, deci nu si peretii din interioare)."""
    from mathutils.bvhtree import BVHTree
    has = m.materials.has
    drips = [r for r in GRIME_DRIPS if has(r)]
    base_ok = has("murdarie_baza")
    me = obj.data
    if f <= 0 or not (drips or base_ok) or not me.polygons:
        return
    rng = random.Random(f"murdarie:{seed}")
    try:
        rmap = json.loads(obj.get("harta_roluri") or "{}")
    except (TypeError, ValueError):
        rmap = {}
    by_mat = {v[0]: k for k, v in rmap.items() if isinstance(v, list) and v}
    roles = [by_mat.get(s.material.name, "") if s.material else "" for s in obj.material_slots]
    verts = [v.co.copy() for v in me.vertices]
    tree = BVHTree.FromPolygons(verts, [tuple(p.vertices) for p in me.polygons])
    up = Vector((0.0, 0.0, 1.0))

    def role_of(i):
        mi = me.polygons[i].material_index
        return roles[mi] if mi < len(roles) else ""

    def outside(p, n):
        return tree.ray_cast(p + n * 0.05, n, 15.0)[0] is None

    def wall_at(p, n):
        """Peretele din spatele lui p (ferestrele stau putin in perete)."""
        loc, nrm, idx, _d = tree.ray_cast(p + n * 1.0, -n, 1.6)
        if loc is None or nrm.dot(n) < 0.9 or not role_of(idx).startswith("perete"):
            return None
        return loc

    faces = []
    for poly in me.polygons:
        if abs(poly.normal.z) > 0.2 or poly.area < 0.3:
            continue
        n = Vector((poly.normal.x, poly.normal.y, 0.0)).normalized()
        c = poly.center.copy()
        t = Vector((-n.y, n.x, 0.0))
        pts = [verts[i] for i in poly.vertices]
        us = [(q - c).dot(t) for q in pts]
        zs = [q.z for q in pts]
        faces.append((role_of(poly.index), n, c, t, min(us), max(us), min(zs), max(zs)))
    wall_top = max([z1 for r, *_rest, z1 in faces if r.startswith("perete")] or [0.0])

    for role, n, c, t, u0, u1, z0, z1 in faces:
        width = u1 - u0
        if role.startswith("perete"):
            if width < 1.0 or not outside(c, n):
                continue
            # umezeala / stropii de la baza parterului: darele intoarse (inchise jos, se sting in sus), una langa
            # alta pe bucati din perete. Alfa 0.6-0.95 abia se vedea, 0.85-1 si de doua ori mai dese era prea mult
            # (GRIME_V 2): acum la mijloc.
            u = u0
            while drips and z0 < 0.5 and u < u1 - 0.6:
                w, h = rng.uniform(0.8, 1.8), rng.uniform(0.6, 1.2)
                if u + w > u1:
                    break
                if rng.random() < min(1.0, 0.35 * f):
                    p = c + t * (u + w / 2) + up * (z0 + h / 2 - c.z)
                    wall_decal(m, p, n, w, h, rng.choice(drips), uv=(0.0, 1.0, 1.0, 0.0), fade=(0.15, 0.2),
                               alpha=rng.uniform(0.5, 0.75))
                u += w * rng.uniform(1.2, 2.2)
            # dare de sub streasina / cornisa (peretii care ajung sus)
            if drips and z1 > wall_top - 0.6:
                for _ in range(int(width / 7.0 * f + rng.random() * 0.6)):
                    w, h = rng.uniform(0.8, 2.0), min(rng.uniform(1.5, 4.0), z1 - z0 - 0.3)
                    if h < 0.8 or width < w:
                        continue
                    p = c + t * rng.uniform(u0 + w / 2, u1 - w / 2) + up * (z1 - 0.1 - h / 2 - c.z)
                    wall_decal(m, p, n, w, h, rng.choice(drips), fade=(0.1, 0.1), alpha=rng.uniform(0.5, 0.75))
        elif role in WINDOWS and drips and width > 0.4 and rng.random() < min(1.0, 0.3 * f) and outside(c, n):
            # dara de sub fereastra (apa de pe pervaz), lipita sub ea
            loc = wall_at(c + up * (z0 - 0.25 - c.z), n)
            if loc is None:
                continue
            want = min(rng.uniform(0.8, 2.2), loc.z - 0.3)
            # doar cat peretele e drept: se opreste la cornisa / balconul de dedesubt (altfel iesea si pe sub ele)
            flat, depth = 0.0, loc.dot(n)
            while flat < want:
                q = wall_at(loc - up * (flat + 0.2), n)
                if q is None or abs(q.dot(n) - depth) > 0.03:
                    break
                flat += 0.2
            h = min(flat, want) + 0.2
            if h < 0.6:
                continue
            p = loc + up * (0.2 - h / 2)
            wall_decal(m, p, n, width * rng.uniform(0.6, 1.0), h, rng.choice(drips), fade=(0.1, 0.1),
                       alpha=rng.uniform(0.85, 1.0))


def cut_faces(obj, pred):
    """Scoate fetele orizontale al caror mijloc cade unde pred(x, y) (apa, rampa unui pod / tunel)."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    mw = obj.matrix_world
    dead = [f for f in bm.faces if f.normal.z > 0.5 and pred(*(mw @ f.calc_center_median())[:2])]
    if dead:
        bmesh.ops.delete(bm, geom=dead, context="FACES")
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


# ------------------------------------------------------------------------------------------ cvartale

def fill_block(poly, Z, rng, tex, avoid=None, edges_on=None):
    """Asezarea din tools/oras/layout.py, cu inaltimea de etaj a fiecarui tip din generatorul de cladiri."""
    return LY.fill_block(poly, Z, rng, tex, avoid, edges_on,
                         heights={k: v[3] for k, v in gen["DEFAULTS"].items()})


PARK_STALL, PARK_AISLE, PARK_W = 5.0, 6.0, 2.6     # adancimea locului, culoarul dintre randuri, latimea locului


def parking_marks(m, poly, z):
    """Locuri de parcare pe toata suprafata, in randuri paralele cu latura cea mai lunga: un rand pe margine, apoi
    culoar, doua randuri spate in spate, culoar... Un loc se deseneaza doar daca ambele capete sunt in poligon."""
    a, b = max(zip(poly, poly[1:] + poly[:1]), key=lambda e: G.length(G.sub(e[1], e[0])))
    t = G.norm(G.sub(b, a))
    n = G.left(t)
    ts = [G.dot(p, t) for p in poly]
    ns = [G.dot(p, n) for p in poly]

    def at(u, v):
        return G.add(G.mul(t, u), G.mul(n, v))

    def mark(p0, p1, d):
        q = [G.add(p0, G.mul(d, -0.06)), G.add(p0, G.mul(d, 0.06)), G.add(p1, G.mul(d, 0.06)), G.add(p1, G.mul(d, -0.06))]
        m.face([Vector((x, y, z)) for x, y in q], "marcaj_alb")

    rows, v, single = [], min(ns) + 0.4, True
    while v + PARK_STALL <= max(ns) - 0.4:
        rows.append((v, v + PARK_STALL))
        v += PARK_STALL
        if single or len(rows) % 2 == 1:     # dupa randul de pe margine si dupa fiecare pereche: culoar
            v += PARK_AISLE
        single = False
    for r0, r1 in rows:
        u = min(ts) + 1.0
        ticks = []
        while u <= max(ts) - 1.0:
            p0, p1 = at(u, r0), at(u, r1)
            if G.inside(p0, poly) and G.inside(p1, poly) and G.inside(at(u, (r0 + r1) / 2), poly):
                mark(p0, p1, t)
                ticks.append(u)
            u += PARK_W
        if len(ticks) > 1:      # linia din spatele locurilor, intre prima si ultima liniuta
            mark(at(ticks[0], r1 if (r0, r1) == rows[0] else r0), at(ticks[-1], r1 if (r0, r1) == rows[0] else r0), n)


def court(poly):
    """Terenul de baschet cel mai mare care incape, aliniat cu latura cea mai lunga: (centru, t, lungime, latime)."""
    a, b = max(zip(poly, poly[1:] + poly[:1]), key=lambda e: G.length(G.sub(e[1], e[0])))
    t = G.norm(G.sub(b, a))
    n = G.left(t)
    us, vs = [G.dot(p, t) for p in poly], [G.dot(p, n) for p in poly]
    cu, cv = (min(us) + max(us)) / 2, (min(vs) + max(vs)) / 2
    c = G.add(G.mul(t, cu), G.mul(n, cv))
    L, Wd = min(28.0, max(us) - min(us) - 4.0), min(15.0, max(vs) - min(vs) - 4.0)
    while L >= 12.0 and not all(G.inside(p, poly) for p in rect(c, t, n, L + 2, Wd + 2)):
        L, Wd = L * 0.9, Wd * 0.9
    return (c, t, L, Wd) if L >= 12.0 and Wd >= 7.0 else None


def court_lines(m, c, t, L, Wd, z):
    n = G.left(t)

    def bar(p, q, w=0.08):
        d = G.norm(G.sub(q, p))
        k = G.mul(G.left(d), w / 2)
        pts = [G.sub(p, k), G.add(p, k), G.add(q, k), G.sub(q, k)]
        if (pts[1][0] - pts[0][0]) * (pts[2][1] - pts[0][1]) - (pts[1][1] - pts[0][1]) * (pts[2][0] - pts[0][0]) < 0:
            pts = pts[::-1]
        m.face([Vector((x, y, z)) for x, y in pts], "marcaj_alb")

    R = rect(c, t, n, L, Wd)
    for p, q in zip(R, R[1:] + R[:1]):
        bar(p, q)
    bar(G.add(c, G.mul(n, -Wd / 2)), G.add(c, G.mul(n, Wd / 2)))
    ring = [G.add(c, G.add(G.mul(t, 1.8 * math.cos(a)), G.mul(n, 1.8 * math.sin(a))))
            for a in (2 * math.pi * k / 20 for k in range(21))]
    for p, q in zip(ring, ring[1:]):
        bar(p, q)


# ------------------------------------------------------------------------------------------ constructie

def progress(f, text):
    """Cat s-a facut (0..1) si etapa: serverul editorului arata bara si cat mai dureaza."""
    print(f"PROGRES {f:.3f} {text}", flush=True)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--out", default=str(TOOLS.parent / "output" / "orase"))
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--texturi", default="")
    # deschis cu .blend-ul generat inainte: reface doar strazile / cvartalele / terenul schimbate (vezi unit())
    ap.add_argument("--incremental", action="store_true")
    a = ap.parse_args(argv)
    t0 = time.time()
    path = Path(a.plan)
    plan = json.loads(path.read_text(encoding="utf-8"))
    seed = a.seed or int(plan.get("seed", 1))
    tex = a.texturi or plan.get("texturi", "gta")
    rng = random.Random(seed)
    A = G.analyze(plan)
    carari_plan = PP.load_carari(path)      # <plan>_carari.json: cararile puse cu unealta Carare din /mapeditor
    types = A["tipuri"]
    grid = G.terrain(plan, A, step=6.0, margin=90.0)
    sea = A["mare"]
    for w in A["warnings"]:
        print(f"ORAS avertisment: {w['mesaj']} ({w['x']:.0f}, {w['y']:.0f})")
    progress(0.03, "strazi si intersectii")

    # inaltimea strazii celei mai apropiate (fata cladirilor) si a solului din cvartale; podurile si tunelurile
    # nu conteaza (trec pe deasupra / pe dedesubt)
    sol = [r for r in A["roads"].values() if r["nivel"] == "sol"]
    S = np.array([[p[0], p[1], p[2]] for r in sol for p in r["samples"]]
                 + [[j["x"], j["y"], j["z"]] for j in A["junctions"].values() if j["nivel"] == "sol"] or [[0.0, 0.0, 0.0]])

    def street(x, y):
        d2 = (S[:, 0] - x) ** 2 + (S[:, 1] - y) ** 2
        i = int(np.argmin(d2))
        return float(S[i, 2]), math.sqrt(float(d2[i]))

    def ground(x, y):
        """Solul cvartalelor: langa strazi exact la nivelul lor, spre interior terenul interpolat."""
        zs, d = street(x, y)
        w = min(max((d - 8.0) / 20.0, 0.0), 1.0)
        g = zs * (1 - w) + G.height(grid, x, y) * w
        # in interiorul cvartalului solul nu se departeaza cu mai mult de 3 m de strada: un punct de altitudine
        # de 16 m langa strazi la 0 facea un deal peste case (dealurile adevarate se fac ridicand strazile)
        return zs + max(-3.0, min(3.0, g - zs))

    waters = [s["poligon"] for s in A["suprafete"] if s["tip"] == "apa"]
    # malul fiecarei ape: "chei" (beton), "plaja" (nisip care intra lin in apa), "natural" (mal cu iarba in panta)
    water_mal = [s.get("mal", "chei") for s in A["suprafete"] if s["tip"] == "apa"]

    def in_water(x, y, margin=0.0):
        return any(G.inside((x, y), w) or (margin and min(seg_dist((x, y), p, q)
                                                            for p, q in zip(w, w[1:] + w[:1])) < margin)
                   for w in waters)

    # coridoarele podurilor si tunelurilor: acolo nu se construieste, iar placile se taie unde drumul e aproape
    cors = []
    for r in A["roads"].values():
        if r["nivel"] != "sol":
            smp = np.array([s[:3] for s in r["samples"]])
            cors.append((smp[:, 0], smp[:, 1], smp[:, 2], r["W"], r["nivel"], (smp[:, 0].min() - r["W"] - 2,
                         smp[:, 1].min() - r["W"] - 2, smp[:, 0].max() + r["W"] + 2, smp[:, 1].max() + r["W"] + 2)))

    def corridor(x, y, zg, build):
        for xs, ys, zs, W, lvl, bb in cors:
            if x < bb[0] or x > bb[2] or y < bb[1] or y > bb[3]:
                continue
            d2 = (xs - x) ** 2 + (ys - y) ** 2
            k = int(np.argmin(d2))
            if d2[k] > (W + (1.5 if build else 0.8)) ** 2:
                continue
            clear = zs[k] - zg if lvl == "pod" else zg - zs[k]
            if build or clear < (3.5 if lvl == "pod" else 7.5):
                if lvl == "pod" or clear < 12.0:
                    return True
        return False

    name = path.stem
    scene = bpy.context.scene
    # ---- generare incrementala: fiecare strada, intersectie, cvartal, cladire pusa de mana, teren, apa e o
    # "unitate" cu amprenta intrarilor ei; din .blend-ul de data trecuta raman cele cu aceeasi amprenta
    code = code_version()
    try:
        old_units = json.loads(scene.get("oras_units") or "{}") if a.incremental else {}
    except ValueError:
        old_units = {}
    inc = bool(old_units) and old_units.get("_code") == code and old_units.get("_plan") == name
    if a.incremental and not inc:
        print("ORAS generez tot orasul (" + ("s-a schimbat codul generatorului" if old_units else "prima generare")
              + ")")
    if not inc:
        cli["clear_scene"]()
        for c in list(bpy.data.collections):
            bpy.data.collections.remove(c)
        old_units = {}
    top = bpy.data.collections.get(f"oras_{name}") or bpy.data.collections.new(f"oras_{name}")
    if top.name not in scene.collection.children:
        scene.collection.children.link(top)
    colls = {}
    for k in ("Strazi", "Cvartale", "Cladiri", "Vegetatie si mobilier", "Mobilier stradal", "Teren", "Apa", "Natura"):
        c = bpy.data.collections.get(k) or bpy.data.collections.new(k)
        if c.name not in top.children:
            top.children.link(c)
        colls[k] = c
    materials = gen["Materials"](tex, random.Random(seed))
    # iarba ca terenul GTA: alta iarba, pamant si frunze amestecate in pete mari (Materials._terrain, paint_blend)
    blend_on = tex == "gta" and plan.get("iarba_amestec", True) is not False
    materials.blend = blend_on
    units = {"_code": code, "_plan": name}
    by_unit = {}        # unitate -> numele obiectelor ei din .blend
    if inc:
        for o in bpy.data.objects:
            if o.get("harta_unit"):
                by_unit.setdefault(o["harta_unit"], []).append(o.name)
    stats = {"refacute": 0, "pastrate": 0}
    grid_sig = hashlib.sha1(np.ascontiguousarray(grid["z"]).tobytes()).hexdigest()
    street_sig = hashlib.sha1(np.ascontiguousarray(S).tobytes()).hexdigest()

    def digest(parts):
        raw = json.dumps([code, tex, seed, parts], sort_keys=True, separators=(",", ":"),
                         default=lambda v: v.tolist() if hasattr(v, "tolist") else str(v))
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()

    def drop(names):
        for n in names:
            o = bpy.data.objects.get(n)
            if o is None:
                continue
            me = o.data if o.type == "MESH" else None
            bpy.data.objects.remove(o, do_unlink=True)
            if me is not None and me.users == 0:
                bpy.data.meshes.remove(me)

    def unit(key, parts, build):
        """Face unitatea doar daca i s-au schimbat intrarile (parts); altfel pastreaza obiectele ei din .blend.
        build() pune obiectele si intoarce ce trebuie tinut minte (conturul cladirilor). -> (meta, refacuta)."""
        h = digest(parts)
        old = old_units.get(key)
        names = by_unit.pop(key, [])
        if inc and old and old.get("hash") == h and all(n in bpy.data.objects for n in names):
            units[key] = old
            stats["pastrate"] += 1
            return old.get("meta"), False
        drop(names)
        before = set(bpy.data.objects.keys())
        meta = build()
        for n in set(bpy.data.objects.keys()) - before:
            bpy.data.objects[n]["harta_unit"] = key
        units[key] = {"hash": h, "meta": meta}
        stats["refacute"] += 1
        return meta, True

    def noval(*_args):
        return None

    def add(coll, obj_name, draw, kind):
        m = gen["Mesh"](materials)
        if kind == "curte":     # placile de cvartal si parcurile: alt unghi si alt inceput al texturii pe fiecare
            r = random.Random(obj_name)
            m.uv_turn = (r.randrange(4), r.random(), r.random())
        draw(m)
        if not m.faces:
            return None
        obj = m.to_object(obj_name)
        obj["harta_tip"] = kind
        colls[coll].objects.link(obj)
        return obj

    wear_default = plan.get("uzura") or "normala"

    def wear_obj(name, draw):
        """Uzura asfaltului: obiect separat, fara coliziune, incarcat doar de aproape (ca decalurile jocului)."""
        obj = add("Strazi", name + "_uzura", draw, "uzura")
        if obj is not None:
            obj["fivem_lod"] = 120.0
            obj["fivem_fara_coliziune"] = True
        return obj

    pete_default = plan.get("pete") or "normala"
    grime_default = plan.get("murdarie") or "normala"
    # cate pete pe iarba / cata murdarie pe cladiri: ale orasului, sau din marcajul de zona al cvartalului (editorul
    # web, cardul Cvartal); do_block le pune pe ale cvartalului inainte sa-l faca
    cur = {"pete": WEAR.get(pete_default, 1.0), "murdarie": WEAR.get(grime_default, 1.0)}

    def block_level(block, key, default):
        return WEAR.get(((block or {}).get("marcaj") or {}).get(key) or default, 1.0)

    def spots_obj(name, poly, seed, holes=(), inner=()):
        """Petele de pe iarba unei suprafete: obiect separat, ca uzura (fara coliziune, doar de aproape)."""
        def skip(x, y):
            return (in_water(x, y) or any(G.inside((x, y), h) for h in holes)
                    or any(near_line((x, y), pts, W / 2 + 1.5) for pts, W in inner)
                    or corridor(x, y, ground(x, y), False))
        obj = add("Cvartale", name + "_pete", lambda m: grass_spots(m, poly, cur["pete"], seed, skip, ZS), "uzura")
        if obj is not None:
            cart["drape"](obj, ground, max_edge=2.0)
            obj["fivem_lod"] = 120.0
            obj["fivem_fara_coliziune"] = True
        return obj

    # ---- strazi, intersectii, poduri
    for rid, R in A["roads"].items():
        ends = (R["a"] not in A["junctions"], R["b"] not in A["junctions"])
        label = f"{'pod' if R['nivel'] == 'pod' else 'tunel' if R['nivel'] == 'tunel' else 'strada'}_{rid}"
        # R["T"] = profilul strazii, cu benzile schimbate pe strada asta din editor (latime reala)
        unit(f"road:{rid}", (R, ends, wear_default),
             lambda R=R, ends=ends, label=label, rid=rid: noval(
                 add("Strazi", label, lambda m: road_mesh(m, R, R["T"], *ends), "strada"),
                 wear_obj(label, lambda m: road_wear(m, R, R["T"], R.get("marcaje") or {}, ends, rid,
                                                     wear_default))))
    def bend_strips(J):
        """Marcajele care continua peste un cot (doua strazi): profilul strazii, sau doar linia galbena din
        mijloc daca cele doua strazi au profiluri diferite."""
        if len(J["brate"]) != 2:
            return None
        ts = [A["roads"][arm["road"]]["T"] for arm in J["brate"]]
        if not all(t.get("marcaj", True) for t in ts):
            return None
        strips = profile_for(ts[0])[0]
        if ts[0] != ts[1]:
            if any(t.get("mediana", 0.0) > 0.5 for t in ts):
                return None
            strips = [s for s in strips if s[3] == "marcaj_galben"]
        return strips

    for nid, J in A["junctions"].items():
        strips = bend_strips(J)
        # intersectia e cat de uzata e cea mai uzata strada care intra in ea
        jf = max([wear_level(A["roads"][arm["road"]].get("marcaje"), wear_default) for arm in J["brate"]] or [0.0])
        unit(f"junction:{nid}", (J, strips, jf),
             lambda J=J, strips=strips, nid=nid, jf=jf: noval(
                 add("Strazi", f"intersectie_{nid}", lambda m: junction_mesh(m, J, strips), "strada"),
                 wear_obj(f"intersectie_{nid}", lambda m: junction_wear(m, J, jf, nid))))

    def pillars(m):
        for R in A["roads"].values():
            if R["nivel"] != "pod":
                continue
            smp = R["samples"]
            span = R["s1"] - R["s0"]
            k = max(1, int(span / 22.0))
            for i in range(1, k):
                s = smp[int(len(smp) * i / k)]
                x, y, z = s[0], s[1], s[2]
                zg = G.height(grid, x, y)
                if z - DECK - zg < 2.0:
                    continue
                if street(x, y)[1] < 13.0:       # nu pe strada de dedesubt
                    continue
                obox(m, (x, y), (s[3], s[4]), 1.4, 2 * R["W"] * 0.55, zg - 1.0, z - DECK, "soclu")
        for J in A["junctions"].values():
            if J["nivel"] == "pod":
                zg = G.height(grid, J["x"], J["y"])
                obox(m, (J["x"], J["y"]), (1.0, 0.0), 2.6, 2.6, zg - 1.0, J["z"] - DECK, "soclu")
    unit("pillars", ([R for R in A["roads"].values() if R["nivel"] == "pod"],
                     [J for J in A["junctions"].values() if J["nivel"] == "pod"], grid_sig, street_sig),
         lambda: noval(add("Strazi", "poduri_piloni", pillars, "strada")))
    print(f"ORAS strazi: {len(A['roads'])} strazi, {len(A['junctions'])} intersectii, "
          f"{len(A['pasaje'])} pasaje ({time.time() - t0:.0f} s)")
    progress(0.07, "mobilier stradal")
    if plan.get("mobilier", True):
        def furniture():
            n = street_furniture(colls["Mobilier stradal"], A, types, random.Random(seed + 5))
            print(f"ORAS mobilier stradal: {n} obiecte ({time.time() - t0:.0f} s)")
        unit("furniture", (A["roads"], A["junctions"], types), furniture)
    progress(0.1, "cvartale")

    # ---- cladiri puse de mana (le ocolesc si cvartalele)
    custom = []
    for k in plan.get("cladiri", []):
        ang = math.radians(float(k.get("r", -90.0)))
        front = (math.cos(ang), math.sin(ang))
        nn = (-front[0], -front[1])
        tt = G.right(nn)
        if k.get("tip") == "gta":
            w, d = float(k.get("w", 12.0)), float(k.get("d", 12.0))
        else:
            q = k.get("p", {})
            tip = q.get("tip", "bloc") if q.get("tip") in gen["DEFAULTS"] else "bloc"
            w, d = float(q.get("latime", gen["DEFAULTS"][tip][0])), float(q.get("adancime", gen["DEFAULTS"][tip][1]))
        c = (float(k["x"]), float(k["y"]))
        custom.append({"k": k, "c": c, "t": tt, "n": nn, "w": w, "d": d, "R": rect(c, tt, nn, w, d)})

    def avoid_for(own, lines=()):
        """lines = strazile din cvartal (inner_roads): nicio cladire peste ele sau lipita de trotuarul lor."""
        def avoid(R):
            cx, cy = sum(p[0] for p in R) / 4, sum(p[1] for p in R) / 4
            pts = R + [(cx, cy)] + [G.mul(G.add(p, q), 0.5) for p, q in zip(R, R[1:] + R[:1])]
            return (any(in_water(*p) for p in pts) or any(poly_overlap(R, o) for o in own)
                    or any(seg_dist(p, a, b) < half + 1.0 for road, half in lines
                           for a, b in zip(road, road[1:]) for p in pts)
                    or any(poly_overlap(R, cb["R"]) for cb in custom)
                    or any(corridor(p[0], p[1], ground(*p), True) for p in pts))
        return avoid

    count = [0]
    foot = []       # conturul fiecarei cladiri, pentru harta de pe minimap
    foot_info = []  # pentru editorul de pe web: ce e fiecare (cele generate se pot sterge sau face editabile)
    # cladirile generate sterse in editor: nu se mai pun (punctul e centrul lor; restul cvartalului ramane la fel)
    removed = [tuple(p[:2]) for p in plan.get("cladiri_sterse", [])]

    def unit_b(key, parts, build):
        """unit() pentru ce pune cladiri: conturul lor (minimap, editorul web, props sub case) se tine minte, ca o
        unitate pastrata sa-l dea mai departe fara sa refaca nimic. True = refacuta."""
        n0, c0 = len(foot), count[0]

        def run():
            build()
            return {"foot": [[list(p) for p in R] for R in foot[n0:]], "info": foot_info[n0:], "n": count[0] - c0}
        meta, fresh = unit(key, parts, run)
        if not fresh and meta:
            foot.extend([[tuple(p) for p in R] for R in meta["foot"]])
            foot_info.extend(meta["info"])
            count[0] += meta["n"]
        return fresh

    def place_building(b, p=None):
        obj, _inside = gen["build"](p or b["p"])
        colls["Cladiri"].objects.link(obj)
        front = G.sub(b["c"], G.mul(b["n"], b["d"] / 2))
        # pe strada in panta: la coltul din fata cel mai inalt (altfel acela intra sub trotuar); pe partea de jos se
        # vede soclul (fundatia de mai jos), ca in joc
        side = G.mul((-b["n"][1], b["n"][0]), b["w"] / 2)
        zf = max(street(*p)[0] for p in (front, G.add(front, side), G.sub(front, side)))
        # pe panta care urca dinspre strada: casa sta pe teren (in fata se vede soclul), nu ingropata in deal
        zf = max(zf, max(ground(*pt) for pt in list(b["R"]) + [b["c"]]) - 0.2)
        obj.location = (b["c"][0], b["c"][1], zf + ZS)
        obj.rotation_euler.z = G.angle(b["n"]) - math.pi / 2
        low = min(ground(*pt) for pt in b["R"])
        wm = bpy.data.materials.get(obj.get("perete_mat", ""))
        ws = float(obj.get("perete_scala", 3.0))
        fm = gen["Mesh"](type("WallOnly", (), {"get": lambda self, role: (wm, ws)})() if wm else materials)
        fm.box(-b["w"] / 2, -b["d"] / 2, -(zf - low + 0.6), b["w"] / 2, b["d"] / 2, 0.0, "soclu")
        base = fm.to_object(obj.name + "_fundatie")
        base["harta_tip"] = "fundatie"
        colls["Cladiri"].objects.link(base)
        base.parent = obj
        # murdarie doar pe blocuri: pe hale, case, vile, magazine si turnuri darele aratau a pete rosii
        if cur["murdarie"] > 0 and (p or b["p"]).get("tip") == "bloc":
            gm = gen["Mesh"](materials)
            building_grime(gm, obj, cur["murdarie"], f"{b['c'][0]:.1f},{b['c'][1]:.1f}")
            if gm.faces:
                grime = gm.to_object(obj.name + "_murdarie")
                grime["harta_tip"] = "uzura"
                grime["fivem_lod"] = 150.0
                grime["fivem_fara_coliziune"] = True
                colls["Cladiri"].objects.link(grime)
                grime.parent = obj
        count[0] += 1
        foot.append(b["R"])
        if "k" in b:
            foot_info.append({"id": b["k"].get("id")})
        else:
            q = p or b["p"]
            foot_info.append({"x": round(b["c"][0], 1), "y": round(b["c"][1], 1),
                              "r": round(math.degrees(math.atan2(-b["n"][1], -b["n"][0])), 1),
                              "tip": q.get("tip"), "w": round(b["w"], 1), "d": round(b["d"], 1),
                              "etaje": q.get("etaje"), "comercial": bool(q.get("comercial"))})
        return obj

    def ground_zs(x, y):
        return ground(x, y) + ZS

    road_boxes = {}     # strada -> (puncte, dreptunghiul lor): testul "punct in cvartal" doar unde se pot atinge

    def inner_roads(poly):
        """Strazile de la sol care intra in cvartal fara sa-l imparta (fundaturi, bucle): (puncte, jumatate de
        latime cu trotuar). Cele de pe margine au axul in afara poligonului, deci nu intra."""
        out = []
        px, py = [p[0] for p in poly], [p[1] for p in poly]
        x0, y0, x1, y1 = min(px), min(py), max(px), max(py)
        for rid, r in A["roads"].items():
            if r["nivel"] != "sol":
                continue
            box = road_boxes.get(rid)
            if box is None:
                pts = [(s[0], s[1]) for s in r["samples"]]
                box = road_boxes[rid] = (pts, min(p[0] for p in pts), min(p[1] for p in pts),
                                         max(p[0] for p in pts), max(p[1] for p in pts))
            pts, rx0, ry0, rx1, ry1 = box
            if rx1 < x0 or rx0 > x1 or ry1 < y0 or ry0 > y1:
                continue
            if any(x0 <= p[0] <= x1 and y0 <= p[1] <= y1 and G.inside(p, poly) for p in pts):
                out.append((pts, r["W"]))
        return out

    def plate(poly, role, obj_name, holes=(), cut=False, z=ZS, inner=()):
        def draw(m):
            if inner:
                # strazile din cvartal (fundaturi, alei) decupate exact: placa nu mai sta peste trotuarul lor
                cart["park_draw"](cart["plate_layout"](poly, holes, inner), role, z)(m)
            else:
                tri(m, poly, z, role, holes)
                skirt(m, poly, -0.4, z, role)
        obj = add("Cvartale", obj_name, draw, "curte")
        if obj is not None:
            cart["drape"](obj, ground, max_edge=2.0 if cut else 4.0)
            paint_blend(obj)
            if inner:
                obj["fivem_col_max"] = 60000     # grila de 1 m: coliziunea exacta (vezi local_collision)
            if cut:
                cut_faces(obj, lambda x, y: in_water(x, y) or corridor(x, y, ground(x, y), False))
        return obj

    def fill_zone(poly, Z, brng, avoid, edges_on=None, lines=()):
        placed = fill_block(poly, Z, brng, tex, avoid, edges_on)
        if removed:
            placed = [b for b in placed if not any(G.inside(pt, b["R"]) for pt in removed)]
        if Z.get("copaci"):
            scatter_trees(colls["Vegetatie si mobilier"], poly, placed, Z["copaci"], brng, ground_zs, lines)
        for b in placed:
            place_building(b)

    def build_area(sf, block, brng, with_plate=True):
        """O suprafata desenata in cvartal: placa ei si ce e pe ea (un cvartal intreg are deja placa)."""
        poly, tip = [tuple(p) for p in sf["poligon"]], sf["tip"]
        Z = ZONES.get(tip, ZONES["gol"])
        veg = colls["Vegetatie si mobilier"]
        label = f"{tip}_{sf.get('id') or block['id']}"
        if Z["mod"] == "parc":
            xs, ys = [p[0] for p in poly], [p[1] for p in poly]
            L = cart["park_layout"](min(xs), min(ys), max(xs), max(ys), brng, poly=poly,
                                    auto=sf.get("poteci") != "manual", extra=PP.near(carari_plan, poly))
            cart["park_cut"](L, inner_roads(poly))
            park = add("Cvartale", label, cart["park_draw"](L), "curte")
            if park is not None:
                cart["drape"](park, ground, max_edge=4.0)
                paint_blend(park)
                park["fivem_col_max"] = 60000
            spots_obj(label, poly, label, inner=inner_roads(poly))
            cart["park_props"](veg, L, brng, ground_zs)
            return
        if with_plate:
            plate(poly, Z["sol"], label)
        if Z["mod"] in ("rand", "case"):
            fill_zone(poly, Z, brng, avoid_for([]), [tuple(p) for p in block["poligon"]])
        elif Z["mod"] == "piateta":
            piazza_props(veg, poly, brng, ground_zs)
        elif Z["mod"] == "parcare":
            mk = add("Cvartale", label + "_marcaje", lambda m: parking_marks(m, poly, 0.03), "curte")
            if mk is not None:
                cart["drape"](mk, lambda x, y: ground(x, y) + ZS, max_edge=4.0)
        elif Z["mod"] == "sport":
            ct = court(poly)
            if ct:
                c, t, Lc, Wc = ct
                mk = add("Cvartale", label + "_marcaje", lambda m: court_lines(m, c, t, Lc, Wc, 0.03), "curte")
                if mk is not None:
                    cart["drape"](mk, lambda x, y: ground(x, y) + ZS, max_edge=4.0)
                if props["load"]([BASKET]):
                    face = props["facing"](BASKET)
                    for sg in (-1, 1):
                        p = G.add(c, G.mul(t, sg * (Lc / 2 + 0.3)))
                        props["place"](veg, BASKET, p[0], p[1], ground_zs(*p), G.angle(G.mul(t, -sg)) - face)
        elif Z["mod"] == "gazon":
            spots_obj(label, poly, label, inner=inner_roads(poly))
            scatter_trees(veg, poly, [], 2.0, brng, ground_zs)
            bushes = props["load"](cart["PARK_BUSHES"])
            xs, ys = [p[0] for p in poly], [p[1] for p in poly]
            for _ in range(int(abs(G.area(poly)) / 250.0) if bushes else 0):
                p = (brng.uniform(min(xs), max(xs)), brng.uniform(min(ys), max(ys)))
                if G.inside(p, poly):
                    props["place"](veg, brng.choice(bushes), p[0], p[1], ground_zs(*p), brng.uniform(0, 2 * math.pi))

    # ---- cvartale
    bpy.context.view_layer.update()
    total_area = sum(max(b["arie"], 1.0) for b in A["blocks"]) or 1.0
    done_area = 0.0
    # grupul fiecarui obiect ("Parc 2", "Cladiri LC 5"): map editorul din joc le arata asa (editor/entities.json)
    grup_names = {"lc_caramida": "Cladiri LC", "centru": "Centru", "proiecte": "Proiecte", "suburbie": "Case",
                  "industrial": "Industrial", "parc": "Parc", "piateta": "Piateta", "parcare": "Parcare",
                  "sport": "Teren de sport", "gazon": "Gazon", "gol": "Curte"}
    grup_count = {}
    tag = {"label": None, "before": set()}

    def tag_new():
        if not tag["label"]:
            return
        for key in set(bpy.data.objects.keys()) - tag["before"]:
            o = bpy.data.objects[key]
            if "harta_grup" not in o:
                o["harta_grup"] = tag["label"]

    def do_block(block, poly, Z, brng):
        cur["pete"] = block_level(block, "pete", pete_default)
        cur["murdarie"] = block_level(block, "murdarie", grime_default)
        areas = [A["suprafete"][i] for i in block.get("suprafete", [])]
        holes = [a["poligon"] for a in areas]
        xs, ys = [p[0] for p in poly], [p[1] for p in poly]
        bb = (min(xs), min(ys), max(xs), max(ys))
        cut = (any(bb[0] < p[0] < bb[2] and bb[1] < p[1] < bb[3] for w in waters for p in w)
               or any(not (c[5][2] < bb[0] or c[5][0] > bb[2] or c[5][3] < bb[1] or c[5][1] > bb[3]) for c in cors)
               or any(in_water(*p) for p in poly))
        plate(poly, Z["sol"], f"cvartal_{block['id']}_{block['zona']}", holes,
              cut, z=ZS - (0.3 if Z["mod"] == "parc" else 0.0), inner=inner_roads(poly))    # sub parc: bine sub iarba (in joc 2 cm clipesc)
        if Z["sol"] == "iarba" and block["valid"] and Z["mod"] not in ("gazon", "parc"):
            spots_obj(f"cvartal_{block['id']}", poly, block["id"], holes, inner_roads(poly))
        for sf in areas:
            build_area(sf, block, random.Random(seed * 7919 + block["id"] * 31 + len(sf["poligon"])))
        if not block["valid"] or Z["mod"] in ("gol", "parcare", "sport", "gazon"):
            if block["valid"] and Z["mod"] in ("parcare", "sport", "gazon"):
                build_area({"poligon": poly, "tip": block["zona"], "id": f"c{block['id']}"}, block, brng, False)
            return
        if Z["mod"] == "parc":
            L = cart["park_layout"](bb[0], bb[1], bb[2], bb[3], brng, poly=poly, extra=PP.near(carari_plan, poly),
                                    auto=(block.get("poteci") or (block.get("marcaj") or {}).get("poteci")) != "manual")
            cart["park_cut"](L, inner_roads(poly))     # parcul nu mai trece peste strazile din el
            cart["park_holes"](L, holes)               # nici peste suprafetele desenate in el (parcare peste parc)
            park = add("Cvartale", f"parc_{block['id']}", cart["park_draw"](L), "curte")
            if park is not None:
                cart["drape"](park, ground, max_edge=4.0)
                paint_blend(park)
                park["fivem_col_max"] = 60000    # coliziunea exacta (vezi local_collision)
            spots_obj(f"parc_{block['id']}", poly, f"parc{block['id']}", holes, inner_roads(poly))
            cart["park_props"](colls["Vegetatie si mobilier"], L, brng, ground_zs)
            return
        if Z["mod"] == "piateta":
            piazza_props(colls["Vegetatie si mobilier"], poly, brng, ground_zs)
            return
        inner = inner_roads(poly)
        fill_zone(poly, Z, brng, avoid_for(holes, inner), lines=inner)
        print(f"ORAS cvartal {block['id']} ({block['zona']}, {block['arie']:.0f} m2): {count[0]} cladiri ({time.time() - t0:.0f} s)")

    def block_inputs(block, poly):
        """Tot ce schimba un cvartal: forma, zona, suprafetele, cladirile sterse / puse de mana, apele, podurile si
        strazile care trec prin el, si solul (inaltimea strazilor din jur si terenul pictat, la 10 m)."""
        xs, ys = [p[0] for p in poly], [p[1] for p in poly]
        bb = (min(xs) - 6.0, min(ys) - 6.0, max(xs) + 6.0, max(ys) + 6.0)

        def near(pts):
            return any(bb[0] <= p[0] <= bb[2] and bb[1] <= p[1] <= bb[3] for p in pts)
        pts = [(float(x), float(y)) for x in np.arange(bb[0], bb[2], 10.0) for y in np.arange(bb[1], bb[3], 10.0)]
        return {"cvartal": block, "suprafete": [A["suprafete"][i] for i in block.get("suprafete", [])],
                "sterse": [p for p in removed if near([p])], "manuale": [cb["k"] for cb in custom if near(cb["R"])],
                "ape": [w for w in waters if near(w)],
                "coridoare": [[c[0], c[1], c[2], c[3], c[4]] for c in cors
                              if not (c[5][2] < bb[0] or c[5][0] > bb[2] or c[5][3] < bb[1] or c[5][1] > bb[3])],
                "strazi": inner_roads(poly), "sol": [round(ground(x, y), 2) for x, y in pts + list(poly)],
                "detalii": [GRASS_SPOTS_V, GRIME_V, pete_default, grime_default, blend_on],
                "carari": PP.near(carari_plan, poly)}

    for bi, block in enumerate(A["blocks"]):
        tag_new()
        materials.variant = block["id"]     # iarba / pavajul / asfaltul cvartalului: varianta lui
        zona = block["zona"] if block["valid"] else "gol"
        grup_count[zona] = grup_count.get(zona, 0) + 1
        tag["label"], tag["before"] = f"{grup_names.get(zona, zona)} {grup_count[zona]}", set(bpy.data.objects.keys())
        progress(0.1 + 0.65 * done_area / total_area, f"cvartal {bi + 1} din {len(A['blocks'])}")
        done_area += max(block["arie"], 1.0)        # cladirile cer timp cam cat aria cvartalului
        poly = [tuple(p) for p in block["poligon"]]
        if len(poly) < 3 or block["zona"] == "apa":
            continue
        Z = LY.zone_for(block)      # stilul zonei + "Magazine la parter" ales pe cvartal / zona
        brng = random.Random(seed * 1000 + block["id"])
        if not unit_b(f"block:{block['id']}", block_inputs(block, poly),
                      lambda block=block, poly=poly, Z=Z, brng=brng: do_block(block, poly, Z, brng)):
            print(f"ORAS cvartal {block['id']} ({block['zona']}): neschimbat")

    tag_new()
    tag["label"] = None
    materials.variant = None

    # ---- cladiri puse de mana
    progress(0.75, "cladiri puse de mana si props")
    cur["murdarie"] = WEAR.get(grime_default, 1.0)
    for ci, cb in enumerate(custom):
        k = cb["k"]
        key = f"custom:{k.get('id') or ci}"
        front = G.sub(cb["c"], G.mul(cb["n"], cb["d"] / 2))
        inputs = [k, cb["R"], [round(ground(*pt), 2) for pt in list(cb["R"]) + [cb["c"]]], round(street(*front)[0], 2),
                  GRIME_V, grime_default]
        if k.get("tip") == "gta":
            def place_gta(k=k, cb=cb):
                model = k.get("m", "")
                if not props["load"]([model]):
                    print(f"ORAS avertisment: modelul GTA {model} nu e in biblioteca (importa-i zona cu IMPORTA_GTA.bat)")
                    return
                tmpl = props["_templates"][model]
                bbx = [v[0] for v in tmpl.bound_box]
                bby = [v[1] for v in tmpl.bound_box]
                bbz = [v[2] for v in tmpl.bound_box]
                rz = G.angle(cb["n"]) - math.pi / 2
                lx, ly = (min(bbx) + max(bbx)) / 2, (min(bby) + max(bby)) / 2
                ox = cb["c"][0] - (lx * math.cos(rz) - ly * math.sin(rz))
                oy = cb["c"][1] - (lx * math.sin(rz) + ly * math.cos(rz))
                props["place"](colls["Cladiri"], model, ox, oy, ground_zs(*cb["c"]) - min(bbz), rz)
                count[0] += 1
                foot.append(cb["R"])
                foot_info.append({"id": k.get("id")})
            unit_b(key, inputs, place_gta)
            continue
        q = dict(k.get("p", {}))
        tip = q.get("tip", "bloc") if q.get("tip") in gen["DEFAULTS"] else "bloc"
        dw, dd, df, dh = gen["DEFAULTS"][tip]
        p = {"tip": tip, "latime": cb["w"], "adancime": cb["d"], "etaje": int(q.get("etaje", df)),
             "inaltime": float(q.get("inaltime", dh)), "acoperis": q.get("acoperis", "plat" if tip == "bloc" else "auto"),
             "interior": bool(q.get("interior", False)), "comercial": bool(q.get("comercial", tip in ("bloc", "magazin"))),
             "texturi": tex, "seed": int(q.get("seed", rng.randrange(1, 99999))), "rezervor": float(q.get("rezervor", 0.3)),
             "scara_incendiu": float(q.get("scara_incendiu", 0.0))}
        if q.get("perete"):
            p["perete"] = q["perete"]
        for opt in ("stil", "balcoane", "retras"):      # stilul turnului, planul balcoanelor, etajul retras
            if q.get(opt) is not None:
                p[opt] = q[opt]
        unit_b(key, inputs + [p], lambda cb=cb, p=p: place_building(cb, p))

    # ---- props pictate cu pensula
    painted = [pr for pr in plan.get("props", []) if pr.get("m")]
    # cladirile au prioritate: un copac pictat care cade in casa (sau la 1.5 m de ea) nu se pune; ramane in plan,
    # deci revine daca stergi casa
    grown = []
    for R in foot:
        cx, cy = sum(p[0] for p in R) / len(R), sum(p[1] for p in R) / len(R)
        big = [(p[0] + (p[0] - cx) / max(math.hypot(p[0] - cx, p[1] - cy), 1e-6) * 2.1,
                p[1] + (p[1] - cy) / max(math.hypot(p[0] - cx, p[1] - cy), 1e-6) * 2.1) for p in R]
        grown.append((min(p[0] for p in big), min(p[1] for p in big), max(p[0] for p in big), max(p[1] for p in big), big))

    def under_building(x, y):
        return any(x0 <= x <= x1 and y0 <= y <= y1 and G.inside((x, y), big) for x0, y0, x1, y1, big in grown)

    def place_painted():
        have = set(props["load"](sorted({pr["m"] for pr in painted})))
        for pr in painted:
            if pr["m"] in have and not in_water(pr["x"], pr["y"]) and not under_building(pr["x"], pr["y"]):
                props["place"](colls["Vegetatie si mobilier"], pr["m"], pr["x"], pr["y"], ground_zs(pr["x"], pr["y"]),
                               math.radians(float(pr.get("r", 0.0))))
        missing = sorted({pr["m"] for pr in painted} - have)
        if missing:
            print(f"ORAS avertisment: props care nu sunt in biblioteca: {', '.join(missing[:6])}")

    if painted:
        unit("props", (painted, [g[4] for g in grown],
                       [round(ground(pr["x"], pr["y"]), 2) for pr in painted]), place_painted)

    progress(0.78, "teren")
    # ---- teren: sub oras mereu sub strazi si cvartale, sub apa fundul, spre margini coboara in mare (plaja)
    Zg, x0, y0, s = grid["z"], grid["x0"], grid["y0"], grid["step"]
    ny, nx = Zg.shape
    GX, GY = np.meshgrid(x0 + np.arange(nx) * s, y0 + np.arange(ny) * s)
    zs, dmin, near = np.zeros_like(GX), np.full(GX.shape, 1e12), np.zeros(GX.shape, int)
    for k in range(0, len(S), 128):
        c = S[k:k + 128]
        d2 = (GX[..., None] - c[:, 0]) ** 2 + (GY[..., None] - c[:, 1]) ** 2
        idx = d2.argmin(-1)
        dk = np.take_along_axis(d2, idx[..., None], -1)[..., 0]
        better = dk < dmin
        zs, dmin, near = np.where(better, c[idx, 2], zs), np.where(better, dk, dmin), np.where(better, k + idx, near)
    dmin = np.sqrt(dmin)
    # cat acopera fiecare punct din S (in aceeasi ordine): strada cu trotuar, intersectia pana la trotuarele ei
    reach = [R["W"] for R in sol for _p in R["samples"]]
    for J in A["junctions"].values():
        if J["nivel"] == "sol":
            pts = list(J["asfalt"]) + [p for w in J["trotuare"] for p in w["poligon"]]
            reach.append(max((math.hypot(p[0] - J["x"], p[1] - J["y"]) for p in pts), default=10.0))
    covered = dmin < np.array(reach or [0.0])[near] + 0.3       # sub asfalt / trotuar: nu se vede
    w = np.clip((dmin - 8.0) / 20.0, 0.0, 1.0)
    surface = zs + np.clip(zs * (1 - w) + Zg * w - zs, -3.0, 3.0)      # ca ground(): fara dealuri in cvartale
    city = dmin < 16.0
    in_blocks = np.zeros(GX.shape, bool)
    for block in A["blocks"]:
        poly = block["poligon"]
        inside = np.zeros(GX.shape, bool)
        for (ax, ay), (bx, by) in zip(poly, poly[1:] + poly[:1]):
            inside ^= ((ay > GY) != (by > GY)) & (GX < ax + (GY - ay) * (bx - ax) / (by - ay + 1e-12))
        in_blocks |= inside
    city |= in_blocks
    # capat de strada (fara intersectie): dincolo de el nu e nimic peste teren, iar coborat ca sub strada lasa o
    # groapa; de la ultimul pas al grilei dinainte de capat terenul ramane aproape la nivelul strazii
    end_zone = np.zeros(GX.shape, bool)
    for R in sol:
        smp = R["samples"]
        for node, p, sign in ((R["a"], smp[0], -1.0), (R["b"], smp[-1], 1.0)):
            if node in A["junctions"]:
                continue
            ex, ey = GX - p[0], GY - p[1]
            along = (ex * p[3] + ey * p[4]) * sign
            end_zone |= (along > -s) & (np.hypot(ex, ey) <= dmin + s) & (dmin < 16.0)
    end_zone &= ~in_blocks
    # sub strazi, intersectii si cvartale mult mai jos: grila (s m) e mai rara decat curbura strazii, iar la 35 cm
    # triunghiurile terenului ieseau prin asfalt ca dungi de iarba. Ce e acoperit poate cobori oricat (min cu
    # terenul natural); pe marginea orasului, langa trotuar, terenul ramane la nivelul strazii: cu terenul natural
    # mai jos acolo ramanea un perete sub trotuar si orasul parea ca pluteste
    hidden = covered | (in_blocks & (dmin < 14.0))
    under = np.where(end_zone, 0.15, np.where(hidden, 1.5, 0.35))
    Zt = np.where(hidden, np.minimum(Zg - 0.25, surface - under), surface - under)
    # in afara orasului coboara lin (45 m) spre terenul natural
    far = np.clip((dmin - 16.0) / 45.0, 0.0, 1.0)
    far = far * far * (3.0 - 2.0 * far)
    Zt = np.where(city, Zt, (surface - 0.35) * (1.0 - far) + (Zg - 0.25) * far)
    ii, jj = np.meshgrid(np.arange(nx), np.arange(ny))
    edge = np.minimum(np.minimum(ii, nx - 1 - ii), np.minimum(jj, ny - 1 - jj)) * s
    fall = np.clip(edge / 45.0, 0.0, 1.0)
    Zt = np.where(city, Zt, Zt * fall + (sea - 8.0) * (1 - fall))
    wet = np.zeros(GX.shape, bool)
    for wpoly, mal in zip(waters, water_mal):
        if mal != "chei":
            continue        # plaja / mal natural: terenul intra in panta sub apa (plan_geom.terrain), fara bazin
        inside = np.zeros(GX.shape, bool)
        for (ax, ay), (bx, by) in zip(wpoly, wpoly[1:] + wpoly[:1]):
            inside ^= ((ay > GY) != (by > GY)) & (GX < ax + (GY - ay) * (bx - ax) / (by - ay + 1e-12))
        wet |= inside

    def zt(x, y):
        fx, fy = (x - x0) / s, (y - y0) / s
        i = min(max(int(fx), 0), nx - 2)
        j = min(max(int(fy), 0), ny - 2)
        tx, ty = min(max(fx - i, 0.0), 1.0), min(max(fy - j, 0.0), 1.0)
        return float(Zt[j, i] * (1 - tx) * (1 - ty) + Zt[j, i + 1] * tx * (1 - ty) + Zt[j + 1, i] * (1 - tx) * ty
                     + Zt[j + 1, i + 1] * tx * ty)

    # tuneluri: pereti, tavan, portaluri; terenul se deschide deasupra rampelor (santul dintre pereti)
    hole = np.zeros(GX.shape, bool)
    tunnels = [R for R in A["roads"].values() if R["nivel"] == "tunel"]

    def tunnel_mesh(m):
        for R in tunnels:
            W = R["W"] + 0.3
            smp = R["samples"]

            def at(i, x, z):
                p = smp[i]
                return Vector((p[0] + p[4] * x, p[1] - p[3] * x, z))

            depth = [zt(p[0], p[1]) - p[2] for p in smp]
            closed = [dp >= TUNNEL_H + 0.3 for dp in depth]
            for i in range(len(smp) - 1):
                if max(depth[i], depth[i + 1]) < 0.3:
                    continue
                za, zb = smp[i][2], smp[i + 1][2]
                shut = closed[i] and closed[i + 1]
                for side in (-1, 1):
                    def top(k, z):
                        if shut:
                            return z + TUNNEL_H
                        p = at(k, side * W, 0.0)
                        return max(z + ZS + 0.9, zt(p.x, p.y) + 0.3)
                    a0, b0 = at(i, side * W, za - 0.5), at(i + 1, side * W, zb - 0.5)
                    a1, b1 = at(i, side * W, top(i, za)), at(i + 1, side * W, top(i + 1, zb))
                    if side > 0:
                        m.quad(a0, a1, b1, b0, "bordura")
                    else:
                        m.quad(a0, b0, b1, a1, "bordura")
                    if not shut:
                        # buza de iarba peste marginea santului (acopera golul lasat de grila terenului)
                        o0, o1 = at(i, side * (W + 7.0), 0.0), at(i + 1, side * (W + 7.0), 0.0)
                        q = [Vector((a1.x, a1.y, a1.z)), Vector((b1.x, b1.y, b1.z)),
                             Vector((o1.x, o1.y, zt(o1.x, o1.y) + 0.1)), Vector((o0.x, o0.y, zt(o0.x, o0.y) + 0.1))]
                        m.face(q if side < 0 else q[::-1], "iarba")
                if shut:
                    m.quad(at(i, -W, za + TUNNEL_H), at(i, W, za + TUNNEL_H), at(i + 1, W, zb + TUNNEL_H),
                           at(i + 1, -W, zb + TUNNEL_H), "bordura")     # tavanul, cu fata in jos
                if closed[i] != closed[i + 1]:
                    k = i + 1 if closed[i + 1] else i
                    z = smp[k][2]
                    ztop = max(zt(*at(k, x, 0.0)[:2]) for x in (-W, 0.0, W)) + 0.3
                    q = [at(k, -W, z + TUNNEL_H), at(k, W, z + TUNNEL_H), at(k, W, ztop), at(k, -W, ztop)]
                    m.face(q if closed[i + 1] else q[::-1], "bordura")     # portalul, cu fata spre sant

    # santul deschis de deasupra rampelor: fara teren acolo (calculat separat de pereti: tunelul poate ramane
    # neschimbat, iar terenul se reface)
    for R in tunnels:
        W = R["W"] + 0.3
        smp = R["samples"]
        depth = [zt(p[0], p[1]) - p[2] for p in smp]
        closed = [dp >= TUNNEL_H + 0.3 for dp in depth]
        for i in range(len(smp) - 1):
            if max(depth[i], depth[i + 1]) < 0.3 or (closed[i] and closed[i + 1]):
                continue
            p = smp[i]
            hole[(GX - p[0]) ** 2 + (GY - p[1]) ** 2 < (W + 1.0) ** 2] = True
    zt_sig = hashlib.sha1(np.round(Zt, 2).tobytes()).hexdigest()
    if tunnels:
        unit("tunnels", (tunnels, zt_sig), lambda: noval(add("Strazi", "tuneluri", tunnel_mesh, "strada")))

    def terrain(m):
        for j in range(ny - 1):
            for i in range(nx - 1):
                if wet[j, i] or wet[j, i + 1] or wet[j + 1, i] or wet[j + 1, i + 1]:
                    continue
                if hole[j, i] or hole[j, i + 1] or hole[j + 1, i] or hole[j + 1, i + 1]:
                    continue
                xa, xb, ya, yb = x0 + i * s, x0 + (i + 1) * s, y0 + j * s, y0 + (j + 1) * s
                m.quad(Vector((xa, ya, Zt[j, i])), Vector((xb, ya, Zt[j, i + 1])),
                       Vector((xb, yb, Zt[j + 1, i + 1])), Vector((xa, yb, Zt[j + 1, i])), "iarba")
    def build_terrain():
        ter = add("Teren", "teren", terrain, "teren")
        if ter is not None:
            ter["fivem_lod"] = 1500.0      # terenul se vede de departe in joc (altfel dispare marginea orasului)
            paint_blend(ter)
    unit("terrain", (zt_sig, hashlib.sha1(wet.tobytes() + hole.tobytes()).hexdigest(), x0, y0, s, nx, ny, blend_on),
         build_terrain)

    progress(0.82, "apa")
    block_boxes = [(min(p[0] for p in b["poligon"]), min(p[1] for p in b["poligon"]), max(p[0] for p in b["poligon"]),
                    max(p[1] for p in b["poligon"]), b["poligon"]) for b in A["blocks"] if b["valid"]]

    def near_city(x, y):
        """Pe strada / trotuar sau intr-un cvartal: natura (nisipul, iarba ei, copacii) nu se pune acolo."""
        if street(x, y)[1] < 14.0:
            return True
        return any(bx0 <= x <= bx1 and by0 <= y <= by1 and G.inside((x, y), poly)
                   for bx0, by0, bx1, by1, poly in block_boxes)

    def beach(k, wpoly):
        """Plaja pe malul apei: fasie de nisip de la 30 m pe uscat pana la 12 m in apa (terenul coboara acolo lin)."""
        outer, inner = offset_poly(wpoly, 30.0), offset_poly(wpoly, -12.0)
        if len(outer) < 3:
            return None
        holes = [inner] if len(inner) >= 3 and abs(G.area(inner)) > 1.0 else []
        obj = add("Natura", f"plaja_mal_{k}", lambda m: tri(m, outer, 0.0, "nisip", holes), "curte")
        if obj is not None:
            # 5 m: fasia merge pe tot malul (la o mare mare, zeci de mii de fete); terenul de sub ea e din 4 in 4 m
            cart["drape"](obj, lambda x, y: zt(x, y) + 0.06, max_edge=5.0)
            cut_faces(obj, near_city)
        return obj

    # apa: bazin (fund + chei de beton) si o promenada de beton pe mal, peste golul lasat de grila terenului. Nivelul
    # fiecarei ape: la lac / rau cel pus de plan_geom.terrain (sub cel mai jos punct al malului), altfel marea GTA
    wsf = [sf for sf in A["suprafete"] if sf["tip"] == "apa"]
    lakes = []      # apa la nivelul solului: exportul FiveM o pune in water.xml (in joc se poate inota in ea)
    for k, wpoly in enumerate(waters):
        wpoly = [tuple(p) for p in wpoly]
        lake = wsf[k].get("nivel") != "mare"
        lvl = float(wsf[k].get("nivel_z", sea)) if lake else sea
        bed = lvl - (G.LAKE_DEPTH if lake else 5.0)
        if lake:
            lakes.append({"poligon": [list(p) for p in wpoly], "z": round(lvl, 2)})
            unit(f"lake:{k}", (wpoly, lvl), lambda k=k, wpoly=wpoly, lvl=lvl: noval(add(
                "Apa", f"lac_previzualizare_{k}", lambda m: tri(m, wpoly, lvl, "apa"), "previzualizare")))
        if water_mal[k] != "chei":
            if water_mal[k] == "plaja":
                unit(f"water:{k}", (wpoly, lvl, zt_sig, street_sig, "plaja"),
                     lambda k=k, wpoly=wpoly: noval(beach(k, wpoly)))
            continue

        def basin(m, wpoly=wpoly, bed=bed, lvl=lvl):
            tri(m, wpoly, bed, "soclu")
            for p, q in zip(wpoly, wpoly[1:] + wpoly[:1]):
                n = max(1, int(G.length(G.sub(q, p)) / 3.0))
                for u in range(n):
                    a_ = G.add(p, G.mul(G.sub(q, p), u / n))
                    b_ = G.add(p, G.mul(G.sub(q, p), (u + 1) / n))
                    ta, tb = max(zt(*a_) + 0.15, lvl + 0.4), max(zt(*b_) + 0.15, lvl + 0.4)
                    m.quad(Vector((a_[0], a_[1], bed - 0.5)), Vector((a_[0], a_[1], ta)),
                           Vector((b_[0], b_[1], tb)), Vector((b_[0], b_[1], bed - 0.5)), "bordura")
        def build_water(k=k, wpoly=wpoly, basin=basin, lvl=lvl):
            add("Apa", f"bazin_{k}", basin, "strada")
            outer = offset_poly(wpoly, 1.5 * s)
            if len(outer) >= 3 and G.area(outer) > G.area(wpoly):
                quay = add("Apa", f"chei_{k}", lambda m, o=outer, h=wpoly: tri(m, o, 0.0, "trotuar", [h]), "strada")
                if quay is not None:
                    cart["drape"](quay, lambda x, y: max(zt(x, y) + 0.15, lvl + 0.4), max_edge=3.0)
        unit(f"water:{k}", (wpoly, lvl, zt_sig), build_water)
    bpy.context.scene["fivem_apa"] = json.dumps(lakes)

    # ---- natura (plaja, camp, padure): oriunde, si departe de strazi, pe terenul de la marginea orasului
    nature_role = {"plaja": "nisip", "camp": "iarba", "padure": "iarba"}

    def build_nature(sf, poly, sid):
        tip = sf["tip"]
        obj = add("Natura", f"{tip}_{sid}", lambda m: tri(m, poly, 0.0, nature_role[tip]), "curte")
        if obj is not None:
            # 8 m, nu 4: o plaja de 1 km cu fete de 4 m trecea de 16 MiB in joc (FiveM o incarca greu sau deloc)
            cart["drape"](obj, lambda x, y: zt(x, y) + 0.08, max_edge=8.0)
            cut_faces(obj, lambda x, y: near_city(x, y) or in_water(x, y))
            paint_blend(obj)
        rng = random.Random(f"natura:{sid}")
        veg = colls["Vegetatie si mobilier"]
        xs, ys = [p[0] for p in poly], [p[1] for p in poly]
        area_m2 = abs(G.area(poly))

        def scatter(per_m2, models):
            names = props["load"](models)
            for _ in range(int(area_m2 / per_m2 + rng.random()) if names else 0):
                for _try in range(8):
                    p = (rng.uniform(min(xs), max(xs)), rng.uniform(min(ys), max(ys)))
                    if G.inside(p, poly) and not near_city(*p) and not in_water(*p):
                        props["place"](veg, rng.choice(names), p[0], p[1], zt(*p), rng.uniform(0.0, math.tau))
                        break
        if tip == "padure":
            scatter(60.0, FOREST_TREES)
            scatter(250.0, NATURE_BUSHES)
            scatter(1500.0, FOREST_LOGS)
        elif tip == "camp":
            scatter(180.0, NATURE_BUSHES)
            scatter(450.0, ROCKS)
            scatter(900.0, FIELD_TREES)
        else:
            scatter(700.0, PALMS)
            scatter(1500.0, ROCKS_SMALL)
        return obj

    for sf in A["suprafete"]:
        if sf["tip"] not in nature_role:
            continue
        poly = [tuple(p) for p in sf["poligon"]]
        sid = sf.get("id") or f"{int(poly[0][0])}_{int(poly[0][1])}"
        unit(f"nature:{sid}", (sf, zt_sig, street_sig),
             lambda sf=sf, poly=poly, sid=sid: noval(build_nature(sf, poly, sid)))
    # marea din jur (doar in Blender; in joc e marea GTA, orasul sta la joc.z m deasupra ei)
    bx0, by0, bx1, by1 = x0 - 400, y0 - 400, x0 + nx * s + 400, y0 + ny * s + 400

    def build_sea():
        sea_obj = add("Apa", "mare_previzualizare",
                      lambda m: m.quad(Vector((bx0, by0, sea)), Vector((bx1, by0, sea)), Vector((bx1, by1, sea)),
                                       Vector((bx0, by1, sea)), "apa"), "previzualizare")
        if sea_obj is not None:
            sea_obj.hide_render = False
    unit("sea", (bx0, by0, bx1, by1, sea), build_sea)
    # ce era in .blend dintr-o unitate care nu mai exista (strada stearsa, cvartale unite) pleaca
    for names in by_unit.values():
        drop(names)
    scene["oras_units"] = json.dumps(units, separators=(",", ":"))
    print(f"ORAS {'incremental' if inc else 'complet'}: {stats['refacute']} bucati refacute, "
          f"{stats['pastrate']} pastrate din data trecuta ({time.time() - t0:.0f} s)")
    progress(0.84, "harta pentru minimap")
    # harta de sus pentru minimap / harta mare; exportul FiveM o gaseste in scena
    png = Path(a.out) / f"{name}_harta.png"
    mx, my, msize = draw_minimap(A, grid, foot, png)
    bpy.context.scene["fivem_minimap"] = json.dumps({"png": str(png), "x0": mx, "y0": my, "size": msize})
    print(f"ORAS harta pentru minimap: {png.name}")
    # contururile cladirilor pentru editorul de pe web: le arata peste cvartale, ca sa vezi unde e loc gol
    (Path(a.out) / f"{name}_cladiri.json").write_text(
        json.dumps([dict(info, R=[[round(p[0], 1), round(p[1], 1)] for p in R]) for R, info in zip(foot, foot_info)]),
        encoding="utf-8")
    # reteaua de strazi pentru GPS-ul din joc (exportul FiveM o pune in client/gps.js): intersectiile si, pe
    # fiecare strada, un punct la ~6 m, cu intersectiile de la capete (None = capat de strada)
    J_ids = set(A["junctions"])
    net = {"j": {nid: [round(J["x"], 1), round(J["y"], 1), round(J["z"], 1)] for nid, J in A["junctions"].items()},
           "r": [[R["a"] if R["a"] in J_ids else None, R["b"] if R["b"] in J_ids else None,
                  [[round(p[0], 1), round(p[1], 1), round(p[2], 1)] for p in R["samples"][::6] + R["samples"][-1:]]]
                 for R in A["roads"].values()]}
    bpy.context.scene["fivem_drumuri"] = json.dumps(net)
    print(f"ORAS {name}: {len(A['blocks'])} cvartale, {count[0]} cladiri, "
          f"{len(colls['Vegetatie si mobilier'].objects)} props, {len(colls['Mobilier stradal'].objects)} mobilier, "
          f"{len(waters)} ape, {len(tunnels)} tuneluri, {len(A['warnings'])} avertismente, {time.time() - t0:.0f} s")
    # ce ai schimbat in joc cu /mapeditor (obiecte puse, obiecte ascunse) apare si in .blend
    try:
        game = runpy.run_path(str(Path(__file__).resolve().parent / "import_din_joc.py"), run_name="import_din_joc")
        game["import_game_edits"](plan, name, props, log=print)
    except Exception as error:      # orasul se salveaza oricum, doar fara modificarile din joc
        print(f"ORAS avertisment: nu am adus modificarile din joc: {error}")
    progress(0.86, "salvez .blend")
    # fara .glb: nu-l foloseste nimic (exportul FiveM si editorul web lucreaza cu .blend-ul), iar la generarea
    # completa scrierea lui lua cam cat toata generarea cladirilor (226 din 683 s la profilare)
    print(f"ORAS_FISIER {cli['save'](name, a.out, glb=False)}")


# fisierele care fac orasul: daca se schimba vreunul, generarea incrementala reface tot
CODE_FILES = ("gen_oras.py", "gen_cartier.py", "gen_strada.py", "gen_cladire.py", "blender_gen_buildings.py",
              "gta_props.py", "oras/plan_geom.py", "oras/layout.py", "oras/park_plan.py")


def code_version():
    h = hashlib.sha1()
    for f in CODE_FILES:
        path = TOOLS / f
        h.update(path.read_bytes() if path.is_file() else f.encode("utf-8"))
    return h.hexdigest()


MAP_COLORS = {"teren": (0.29, 0.31, 0.30, 1.0), "cvartal": (0.35, 0.37, 0.36, 1.0), "cladire": (0.48, 0.5, 0.5, 1.0),
              "verde": (0.3, 0.43, 0.27, 1.0), "pavaj": (0.45, 0.44, 0.4, 1.0), "asfalt": (0.4, 0.41, 0.42, 1.0),
              "apa": (0.26, 0.42, 0.58, 1.0), "trotuar": (0.53, 0.54, 0.54, 1.0), "strada": (0.8, 0.81, 0.81, 1.0),
              "tunel": (0.56, 0.57, 0.57, 1.0), "nisip": (0.72, 0.66, 0.5, 1.0)}
MAP_ZONES = {"parc": "verde", "gazon": "verde", "piateta": "pavaj", "parcare": "asfalt", "sport": "asfalt", "apa": "apa",
             "plaja": "nisip", "camp": "verde", "padure": "verde"}


def draw_minimap(A, grid, foot, png):
    """Orasul vazut de sus, in culorile radarului GTA: pentru minimap si harta mare din joc (exportul FiveM il pune
    ca overlay). Marea ramane transparenta, dedesubt se vede marea jocului. Intoarce coltul de jos-stanga si
    latura imaginii, in metri."""
    x0, y0, s = grid["x0"], grid["y0"], grid["step"]
    ny, nx = grid["z"].shape
    size = max(nx, ny) * s
    px = int(min(2048, max(512, math.ceil(size / 512.0) * 512)))
    mpp = size / px
    img = np.zeros((px, px, 4), np.float32)      # randul 0 = nord

    def region(xs, ys, pad=0.0):
        i0, i1 = max(int((min(xs) - pad - x0) / mpp), 0), min(int((max(xs) + pad - x0) / mpp) + 2, px)
        j0, j1 = max(int((y0 + size - max(ys) - pad) / mpp), 0), min(int((y0 + size - min(ys) + pad) / mpp) + 2, px)
        if i0 >= i1 or j0 >= j1:
            return None
        GX, GY = np.meshgrid(x0 + (np.arange(i0, i1) + 0.5) * mpp, y0 + size - (np.arange(j0, j1) + 0.5) * mpp)
        return img[j0:j1, i0:i1], GX, GY

    def fill(poly, key):
        if len(poly) < 3:
            return
        r = region([p[0] for p in poly], [p[1] for p in poly])
        if r is None:
            return
        sub, GX, GY = r
        inside = np.zeros(GX.shape, bool)
        for (ax, ay), (bx, by) in zip(poly, list(poly[1:]) + list(poly[:1])):
            inside ^= ((ay > GY) != (by > GY)) & (GX < ax + (GY - ay) * (bx - ax) / (by - ay + 1e-12))
        sub[inside] = MAP_COLORS[key]

    def line(pts, half, key):
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            r = region((ax, bx), (ay, by), half)
            if r is None:
                continue
            sub, GX, GY = r
            dx, dy = bx - ax, by - ay
            t = np.clip(((GX - ax) * dx + (GY - ay) * dy) / (dx * dx + dy * dy + 1e-9), 0.0, 1.0)
            sub[(GX - ax - t * dx) ** 2 + (GY - ay - t * dy) ** 2 <= half * half] = MAP_COLORS[key]

    edge = 20.0      # terenul coboara in mare pe margini
    fill([(x0 + edge, y0 + edge), (x0 + nx * s - edge, y0 + edge), (x0 + nx * s - edge, y0 + ny * s - edge),
          (x0 + edge, y0 + ny * s - edge)], "teren")
    for b in A["blocks"]:
        fill(b["poligon"], MAP_ZONES.get(b["zona"], "cvartal"))
    for sf in A["suprafete"]:
        fill(sf["poligon"], MAP_ZONES.get(sf["tip"], "cvartal"))
    for R in foot:
        fill(R, "cladire")
    roads = sorted(A["roads"].values(), key=lambda R: {"tunel": 0, "sol": 1, "pod": 2}[R["nivel"]])
    for R in roads:
        pts = [(p[0], p[1]) for p in R["samples"][::2]] + [tuple(R["samples"][-1][:2])]
        if R["nivel"] == "tunel":
            line(pts, R["r"] / 2, "tunel")
            continue
        line(pts, R["W"], "trotuar")
        line(pts, R["r"] / 2, "strada")
    for J in A["junctions"].values():
        for w in J["trotuare"]:
            fill(w["poligon"], "trotuar")
        fill(J["asfalt"], "strada")
    im = bpy.data.images.new(png.stem, px, px, alpha=True)
    im.pixels.foreach_set(np.ascontiguousarray(img[::-1]).ravel())      # Blender tine randurile de jos in sus
    im.filepath_raw = str(png)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return float(x0), float(y0), float(size)


# copaci de oras, cu coroana de cel mult ~8 m: stejarul (17 m), mesteacanul mare (16 m) si cedrii (31 m) acopereau
# strazile si umpleau cerul cand stateai sub ei
LAWN_TREES = ["prop_tree_maple_03", "prop_tree_birch_03", "prop_tree_birch_03b", "prop_tree_lficus_03"]
# natura (suprafetele plaja / camp / padure): modele gasite in biblioteca (v_trees, v_bush, v_rocks, v_palm, v_ext_veg)
FOREST_TREES = ["prop_tree_pine_01", "prop_tree_pine_02", "prop_tree_cedar_02", "prop_tree_cedar_03", "prop_tree_cedar_04",
                "prop_tree_oak_01", "prop_tree_eng_oak_01"]
FIELD_TREES = ["prop_tree_oak_01", "prop_tree_olive_01", "prop_tree_mquite_01"]
FOREST_LOGS = ["prop_tree_fallen_01", "prop_tree_fallen_02", "prop_tree_fallen_pine_01", "prop_tree_log_01", "prop_tree_stump_01"]
NATURE_BUSHES = ["prop_bush_lrg_01", "prop_bush_lrg_02", "prop_bush_med_01", "prop_bush_med_03", "prop_bush_dead_02",
                 "prop_grass_dry_02", "prop_grass_dry_03", "prop_veg_grass_01_a", "prop_veg_grass_01_c"]
ROCKS = ["prop_rock_1_a", "prop_rock_1_c", "prop_rock_3_a", "prop_rock_3_c", "prop_rock_4_a", "prop_rock_4_c", "prop_rock_5_a"]
ROCKS_SMALL = ["prop_rock_1_b", "prop_rock_1_d", "prop_rock_3_b", "prop_rock_5_b"]
PALMS = ["prop_palm_med_01a", "prop_palm_med_01b", "prop_palm_med_01c", "prop_palm_sm_01a", "prop_palm_sm_01e",
         "prop_plant_palm_01a"]


def street_furniture(coll, A, types, rng):
    """Stalpi de iluminat (bratul peste strada), semafoare la intersectii, hidranti, cosuri, automate de ziare,
    statii de autobuz pe artere, copaci pe trotuar unde profilul cere. Intoarce cate obiecte a pus."""
    have = set(props["load"]([n for v in FURNITURE.values() for n in v]))

    def pick(k):
        opts = [n for n in FURNITURE[k] if n in have]
        return rng.choice(opts) if opts else None

    face = {n: props["facing"](n) for n in have}
    placed = [0]

    def put(model, x, y, z, toward):
        """toward = unghiul spre care trebuie sa priveasca modelul (bratul stalpului, capetele semaforului)."""
        props["place"](coll, model, x, y, z, toward - face.get(model, 0.0))
        placed[0] += 1

    for R in A["roads"].values():
        if R["nivel"] == "tunel":
            continue
        T = R.get("T") or types.get(R["tip"], types["strada"])
        h = T["r"] / 2
        smp = R["samples"]
        if R["s1"] - R["s0"] < 16.0 or len(smp) < 2:
            continue
        cum = [s[5] for s in smp]

        def at(s):
            k = min(max(int(np.searchsorted(cum, s)) - 1, 0), len(smp) - 2)
            a, b = smp[k], smp[k + 1]
            t = (s - a[5]) / max(b[5] - a[5], 1e-9)
            return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t, a[3], a[4])

        def side_point(s, side, off):
            x, y, z, tx, ty = at(s)
            rx, ry = ty, -tx
            return x + rx * side * off, y + ry * side * off, z, math.atan2(-ry * side, -rx * side)

        big = T["r"] >= 12.0
        lamp = pick("lampa_mare" if big else "lampa") or pick("lampa")
        spacing = T.get("stalpi", 28.0 if R["tip"] != "alee" else 0.0) if "stalpi" in T else (0.0 if R["tip"] == "alee" else 28.0)
        both = big or T.get("benzi", 1) >= 2
        if lamp and spacing:
            s, k = R["s0"] + 8.0, 0
            while s < R["s1"] - 8.0:
                for side in ((1, -1) if both else ((1,) if k % 2 == 0 else (-1,))):
                    ss = s + (spacing / 2 if both and side < 0 else 0.0)
                    if ss < R["s1"] - 8.0:
                        x, y, z, toward = side_point(ss, side, h + 0.75)
                        put(lamp, x, y, z + ZS, toward)
                s += spacing
                k += 1
        if R["nivel"] != "sol":
            continue
        tree = pick("copac") if T.get("copaci") and T["s"] >= 2.5 else None
        if tree:
            s = R["s0"] + 9.0 + spacing / 2 if spacing else R["s0"] + 9.0
            while s < R["s1"] - 9.0:
                for side in (1, -1):
                    x, y, z, _ = side_point(s, side, h + C + T["s"] * 0.45)
                    props["place"](coll, tree, x, y, z + ZS, rng.uniform(0, 2 * math.pi))
                    placed[0] += 1
                s += 14.0
        if R["tip"] == "alee":
            continue
        for key, first, step, side, off in (("hidrant", 14.0, 65.0, 1, h + 0.55), ("cos", 24.0, 55.0, -1, h + 0.6)):
            model = pick(key)
            s = R["s0"] + first
            while model and s < R["s1"] - 8.0:
                x, y, z, toward = side_point(s, side, off)
                put(model, x, y, z + ZS, toward)
                s += step
        stop = pick("statie")
        if big and stop and R["s1"] - R["s0"] > 90.0:
            x, y, z, toward = side_point((R["s0"] + R["s1"]) / 2, 1, R["W"] - 1.2)
            put(stop, x, y, z + ZS, toward)
    light = pick("semafor")
    for J in A["junctions"].values():
        if len(J["brate"]) < 3 or J["nivel"] != "sol":
            continue
        for arm in J["brate"]:
            E, e, hh = arm["E"], arm["e"], arm["h"]
            if hh < 3.0:
                continue
            lft = G.left(e)
            p = G.add(E, G.mul(lft, hh + 0.7))       # pe trotuar, langa banda care vine spre intersectie
            if light:
                put(light, p[0], p[1], J["z"] + ZS, G.angle(G.mul(lft, -1)))    # bratul peste banda
            if rng.random() < 0.35:
                news = pick("ziare")
                q = G.add(G.add(E, G.mul(G.right(e), hh + 1.0)), G.mul(e, 1.5))
                if news:
                    put(news, q[0], q[1], J["z"] + ZS, G.angle(G.left(e)))
    return placed[0]


def scatter_trees(coll, poly, placed, density, rng, ground, lines=()):
    """Copaci pe gazonul cvartalului (density = copaci la 1000 m2): nu pe cladiri, nu pe trotuar, la cel putin
    10 m unul de altul, din 1-2 specii pe cvartal (ca sa arate plantati, nu amestecati). lines = strazile din
    cvartal (fundaturi, alei): nici pe ele."""
    names = props["load"](LAWN_TREES)
    if not names:
        return
    species = rng.sample(names, min(2, len(names)))
    # coroana nu trece peste marginea cvartalului (altfel acopera trotuarul si strada)
    reach = {n: max(3.5, max(props["size"](n)[:2]) / 2 + 0.5) for n in species}
    want = int(abs(G.area(poly)) / 1000.0 * density)
    xs, ys = [p[0] for p in poly], [p[1] for p in poly]
    pts = []

    def edge_dist(p):
        return min(seg_dist(p, a, b) for a, b in zip(poly, poly[1:] + poly[:1]))

    for _ in range(want * 8):
        if len(pts) >= want:
            break
        p = (rng.uniform(min(xs), max(xs)), rng.uniform(min(ys), max(ys)))
        kind = rng.choice(species)
        # cel putin 10 m intre copaci: la 7 m coroanele se uneau intr-un acoperis continuu de frunze
        if not G.inside(p, poly) or edge_dist(p) < reach[kind] or any((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 < 100 for q in pts):
            continue
        if any(seg_dist(p, a, b) < half + reach[kind] for road, half in lines for a, b in zip(road, road[1:])):
            continue
        if any(abs(G.dot(G.sub(p, b["c"]), b["t"])) < b["w"] / 2 + 3.0 and abs(G.dot(G.sub(p, b["c"]), b["n"])) < b["d"] / 2 + 3.0
               for b in placed):
            continue
        pts.append(p)
        props["place"](coll, kind, p[0], p[1], ground(*p), rng.uniform(0, 2 * math.pi))


def piazza_props(coll, poly, rng, ground):
    """Piateta pavata: copaci in sir pe margini, banci intre ei, o fantana la mijloc."""
    names = props["load"](["prop_tree_maple_03", "prop_tree_birch_03", "prop_bench_01a", "prop_fountain2"])
    if not names:
        return
    tree = next((n for n in ("prop_tree_maple_03", "prop_tree_birch_03") if n in names), None)
    bench = "prop_bench_01a" if "prop_bench_01a" in names else None
    cx = sum(p[0] for p in poly) / len(poly)
    cy = sum(p[1] for p in poly) / len(poly)
    if "prop_fountain2" in names and G.inside((cx, cy), poly):
        props["place"](coll, "prop_fountain2", cx, cy, ground(cx, cy), 0.0)
    for a, b in zip(poly, poly[1:] + poly[:1]):
        L = G.length(G.sub(b, a))
        t = G.norm(G.sub(b, a))
        n = G.left(t)
        k = 4.0
        while k < L - 4.0:
            p = G.add(G.add(a, G.mul(t, k)), G.mul(n, 3.5))
            if G.inside(p, poly):
                if tree and int(k / 8) % 2 == 0:
                    props["place"](coll, tree, p[0], p[1], ground(*p), rng.uniform(0, 2 * math.pi))
                elif bench:
                    props["place"](coll, bench, p[0], p[1], ground(*p),
                                   G.angle(n) - props["facing"](bench))
            k += 8.0


if __name__ == "__main__":
    main()
