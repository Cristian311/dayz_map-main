# -*- coding: utf-8 -*-
"""
Piese de strada de lipit cap la cap in Blender: drept (10/20 m), trecere de pietoni, intersectie in cruce si
in T, curba de 90 de grade, capat de strada. Asfalt cu marcaje, bordura de 15 cm, trotuar.

    GENEREAZA_STRADA.bat
    _blender.bat -b -P gen_strada.py -- --tip strada --piesa kit

Tipuri: strada (2 benzi, 14 m cu trotuarele), artera (4 benzi, 21 m), alee (fara marcaje, 8 m).
Toate piesele au drumul pe axa Y, originea la mijloc (curba: in coltul din interior) si baza la Z = 0
(asfaltul la 5 cm, trotuarul la 20 cm). Se lipesc prin colturi (Snap pe Vertex) si se rotesc cu R Z 90.
Iese in output\\strazi\\<tip>_<piesa>.glb + .blend.
"""
import argparse
import math
import random
import runpy
import sys
from pathlib import Path

import bpy
from mathutils import Vector

TOOLS = Path(__file__).resolve().parent
cli = runpy.run_path(str(TOOLS / "gen_cladire.py"), run_name="gen_strada")
gen = cli["gen"]

# latime carosabil, latime trotuar (cu bordura), raza trotuarului din interiorul curbei, marcaje
TYPES = {"strada": (8.0, 3.0, 6.0, "dublu"), "artera": (14.0, 3.5, 8.0, "patru"), "alee": (5.0, 1.5, 4.0, None)}
C, ZA, ZS, ZM = 0.25, 0.05, 0.2, 0.062      # bordura, asfalt, trotuar, marcaje
PIECES = ("drept20", "drept10", "trecere", "cruce", "T", "curba", "capat")


class Road:
    def __init__(self, m, kind):
        self.m = m
        self.r, self.s, self.ri, self.marks = TYPES[kind]
        self.h = self.r / 2
        self.W2 = self.r / 2 + self.s

    def profile(self, marks=True):
        """Sectiunea transversala: benzi orizontale (x0, x1, z, rol, (linie, pas) sau None) si pereti
        (x, z0, z1, +1 = spre +x / -1, rol)."""
        h, W2 = self.h, self.W2
        strips = [(-h, h, ZA, "asfalt", None),
                  (-h - C, -h, ZS, "bordura", None), (h, h + C, ZS, "bordura", None),
                  (-W2, -h - C, ZS, "trotuar", None), (h + C, W2, ZS, "trotuar", None)]
        if marks and self.marks:
            strips += [(-0.22, -0.1, ZM, "marcaj_galben", None), (0.1, 0.22, ZM, "marcaj_galben", None)]
            if self.marks == "patru":
                q = self.r / 4
                strips += [(-q - 0.07, -q + 0.07, ZM, "marcaj_alb", (2.5, 5.0)),
                           (q - 0.07, q + 0.07, ZM, "marcaj_alb", (2.5, 5.0))]
        walls = [(-h, ZA, ZS, 1, "bordura"), (h, ZA, ZS, -1, "bordura"),
                 (-W2, 0.0, ZS, -1, "trotuar"), (W2, 0.0, ZS, 1, "trotuar")]
        return strips, walls


def sweep(m, samples, profile, caps=(True, True)):
    """Trage sectiunea de-a lungul drumului: samples = [(punct, directie, metri de la inceputul piesei)]."""
    strips, walls = profile

    def at(i, x, z):
        p, t = samples[i][0], samples[i][1]
        z0 = samples[i][3] if len(samples[i]) > 3 else 0.0   # inaltimea drumului in punctul asta (orase)
        return Vector((p.x + t.y * x, p.y - t.x * x, z + z0))   # x spre dreapta directiei de mers

    for i in range(len(samples) - 1):
        mid = (samples[i][2] + samples[i + 1][2]) / 2
        for x0, x1, z, role, dash in strips:
            if dash and mid % dash[1] >= dash[0]:
                continue
            m.quad(at(i, x0, z), at(i, x1, z), at(i + 1, x1, z), at(i + 1, x0, z), role)
        for x, z0, z1, facing, role in walls:
            a0, b0, a1, b1 = at(i, x, z0), at(i + 1, x, z0), at(i, x, z1), at(i + 1, x, z1)
            if facing > 0:
                m.quad(a0, b0, b1, a1, role)
            else:
                m.quad(b0, a0, a1, b1, role)
    for x0, x1, z, role, _dash in strips:
        if role.startswith("marcaj"):
            continue
        if caps[0]:
            m.quad(at(0, x0, 0.0), at(0, x1, 0.0), at(0, x1, z), at(0, x0, z), role)
        if caps[1]:
            m.quad(at(-1, x1, 0.0), at(-1, x0, 0.0), at(-1, x0, z), at(-1, x1, z), role)


def line(y0, y1, start, step=0.5):
    n = max(1, round((y1 - y0) / step))
    return [(Vector((0.0, y0 + (y1 - y0) * k / n)), Vector((0.0, 1.0)), y0 + (y1 - y0) * k / n - start)
            for k in range(n + 1)]


def arc(radius, step=0.5):
    n = max(12, round(radius * math.pi / 2 / step))
    out = []
    for k in range(n + 1):
        a = math.pi / 2 * k / n
        out.append((Vector((radius * math.cos(a), radius * math.sin(a))), Vector((-math.sin(a), math.cos(a))),
                    radius * a))
    return out


def rot(k):
    """Rotire cu k * 90 de grade in jurul originii (pastreaza sensul fetelor)."""
    c, s = round(math.cos(k * math.pi / 2)), round(math.sin(k * math.pi / 2))
    return lambda x, y, z: Vector((x * c - y * s, x * s + y * c, z))


def rect(m, f, x0, y0, x1, y1, z, role):
    m.quad(f(x0, y0, z), f(x1, y0, z), f(x1, y1, z), f(x0, y1, z), role)


def wall(m, f, a, b, z0, z1, role):
    """Perete vertical de la a la b, cu fata vizibila la dreapta sensului a -> b."""
    m.quad(f(a[0], a[1], z0), f(b[0], b[1], z0), f(b[0], b[1], z1), f(a[0], a[1], z1), role)


def zebra(m, f, x0, x1, y0, y1):
    """Trecere de pietoni: dungi de 50 cm paralele cu Y, intre x0 si x1."""
    x = x0
    while x + 0.5 <= x1 + 1e-6:
        rect(m, f, x, y0, x + 0.5, y1, ZM, "marcaj_alb")
        x += 1.0


def vwall(m, a, b, z0, z1, role, normal):
    """Perete vertical intre punctele a si b (x, y), cu fata spre `normal`."""
    if (b[1] - a[1]) * normal[0] - (b[0] - a[0]) * normal[1] < 0:
        a, b = b, a
    wall(m, rot(0), a, b, z0, z1, role)


def edge(x0, y0, x1, y1, side):
    """Capetele laturii unui dreptunghi si normala ei spre exterior."""
    return {"-x": ((x0, y0), (x0, y1), (-1, 0)), "+x": ((x1, y0), (x1, y1), (1, 0)),
            "-y": ((x0, y0), (x1, y0), (0, -1)), "+y": ((x0, y1), (x1, y1), (0, 1))}[side]


def sidewalk(m, x0, y0, x1, y1, curbs):
    """Bucata de trotuar cu bordura pe laturile dinspre asfalt (curbs: "-x", "+x", "-y", "+y")."""
    f = rot(0)
    xa, xb = x0 + (C if "-x" in curbs else 0.0), x1 - (C if "+x" in curbs else 0.0)
    ya, yb = y0 + (C if "-y" in curbs else 0.0), y1 - (C if "+y" in curbs else 0.0)
    rect(m, f, xa, ya, xb, yb, ZS, "trotuar")
    if "-x" in curbs:
        rect(m, f, x0, y0, xa, y1, ZS, "bordura")
    if "+x" in curbs:
        rect(m, f, xb, y0, x1, y1, ZS, "bordura")
    if "-y" in curbs:
        rect(m, f, xa, y0, xb, ya, ZS, "bordura")
    if "+y" in curbs:
        rect(m, f, xa, yb, xb, y1, ZS, "bordura")
    for side in curbs:
        a, b, n = edge(x0, y0, x1, y1, side)
        vwall(m, a, b, ZA, ZS, "bordura", n)


def intersection(m, rv, sv, rh, sh, arms="NESW"):
    """Intersectie intre drumul pe Y (carosabil rv, trotuar sv) si drumul pe X (rh, sh); latimile pot fi
    diferite (bulevard cu strada). arms = bratele deschise (N = +y, S = -y, E = +x, W = -x), cu trecere de
    pietoni; pe celelalte laturi trotuarul merge continuu."""
    hx, hy = rv / 2, rh / 2
    xs, ys = (-hx - sv, -hx, hx, hx + sv), (-hy - sh, -hy, hy, hy + sh)
    arm_at = {(1, 2): "N", (1, 0): "S", (2, 1): "E", (0, 1): "W"}

    def is_road(ci, cj):
        name = arm_at.get((ci, cj))
        return (ci, cj) == (1, 1) or (name is not None and name in arms)

    for ci in range(3):
        for cj in range(3):
            x0, x1, y0, y1 = xs[ci], xs[ci + 1], ys[cj], ys[cj + 1]
            road = is_road(ci, cj)
            if road:
                rect(m, rot(0), x0, y0, x1, y1, ZA, "asfalt")
            else:
                near = (("-x", ci - 1, cj), ("+x", ci + 1, cj), ("-y", ci, cj - 1), ("+y", ci, cj + 1))
                sidewalk(m, x0, y0, x1, y1, {s for s, ni, nj in near if 0 <= ni < 3 and 0 <= nj < 3 and is_road(ni, nj)})
            for side, outer in (("-x", ci == 0), ("+x", ci == 2), ("-y", cj == 0), ("+y", cj == 2)):
                if outer:
                    a, b, n = edge(x0, y0, x1, y1, side)
                    vwall(m, a, b, 0.0, ZA if road else ZS, "asfalt" if road else "trotuar", n)
    if "N" in arms:
        zebra(m, rot(0), -hx + 0.4, hx - 0.4, hy + 0.35, hy + sh - 0.35)
    if "S" in arms:
        zebra(m, rot(0), -hx + 0.4, hx - 0.4, -hy - sh + 0.35, -hy - 0.35)
    # bratele pe X: dungi paralele cu X (rot(1): X = -y local, Y = x local)
    if "E" in arms:
        zebra(m, rot(1), -hy + 0.4, hy - 0.4, -(hx + sv - 0.35), -(hx + 0.35))
    if "W" in arms:
        zebra(m, rot(1), -hy + 0.4, hy - 0.4, hx + 0.35, hx + sv - 0.35)


def piece(road, kind):
    m, h, W2, s = road.m, road.h, road.W2, road.s
    same = rot(0)
    if kind in ("drept20", "drept10"):
        L = 20.0 if kind == "drept20" else 10.0
        sweep(m, line(-L / 2, L / 2, -L / 2), road.profile())
    elif kind == "trecere":
        sweep(m, line(-5.0, -2.5, -5.0), road.profile(), (True, False))
        sweep(m, line(-2.5, 2.5, -5.0), road.profile(marks=False), (False, False))
        sweep(m, line(2.5, 5.0, -5.0), road.profile(), (False, True))
        zebra(m, same, -h + 0.4, h - 0.4, -1.6, 1.6)
    elif kind in ("cruce", "T"):
        intersection(m, road.r, road.s, road.r, road.s, "NESW" if kind == "cruce" else "NSW")
    elif kind == "curba":
        sweep(m, arc(road.ri + W2), road.profile())
    elif kind == "capat":
        L = 12.0
        e = L / 2 - s
        strips, walls = road.profile()
        strips = [st for st in strips if not st[3].startswith("marcaj")]
        sweep(m, line(-L / 2, e - 1.0, -L / 2), road.profile(), (True, False))
        sweep(m, line(e - 1.0, e, -L / 2), (strips, walls), (False, False))
        # trotuarul de la capat, cu bordura spre drum
        rect(m, same, -h - C, e, h + C, e + C, ZS, "bordura")
        rect(m, same, -W2, e, -h - C, e + C, ZS, "trotuar")
        rect(m, same, h + C, e, W2, e + C, ZS, "trotuar")
        rect(m, same, -W2, e + C, W2, L / 2, ZS, "trotuar")
        wall(m, same, (-h, e), (h, e), ZA, ZS, "bordura")
        wall(m, same, (W2, L / 2), (-W2, L / 2), 0.0, ZS, "trotuar")
        wall(m, same, (-W2, L / 2), (-W2, e), 0.0, ZS, "trotuar")
        wall(m, same, (W2, e), (W2, L / 2), 0.0, ZS, "trotuar")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--tip", default="strada", choices=list(TYPES))
    ap.add_argument("--piesa", default="kit", choices=("kit",) + PIECES)
    ap.add_argument("--texturi", default="gta", choices=["gta", "simple"])
    ap.add_argument("--out", default=str(TOOLS.parent / "output" / "strazi"))
    a = ap.parse_args(argv)

    cli["clear_scene"]()
    materials = gen["Materials"](a.texturi, random.Random(1))
    coll = bpy.data.collections.new(f"{a.tip}_{a.piesa}")
    bpy.context.scene.collection.children.link(coll)
    x = 0.0
    for kind in (PIECES if a.piesa == "kit" else (a.piesa,)):
        m = gen["Mesh"](materials)
        piece(Road(m, a.tip), kind)
        obj = m.to_object(f"{a.tip}_{kind}")
        obj["harta_tip"] = "strada"
        coll.objects.link(obj)
        # in kit piesele stau in sir, la 6 m una de alta
        xs = [v.co.x for v in obj.data.vertices]
        obj.location.x = x - min(xs)
        x += max(xs) - min(xs) + 6.0
        print(f"STRADA {obj.name}: {len(obj.data.polygons)} fete, {obj.dimensions.x:.1f} x {obj.dimensions.y:.1f} m")
    print(f"STRADA_FISIER {cli['save'](coll.name, a.out)}")


if __name__ == "__main__":
    main()
