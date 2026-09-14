# -*- coding: utf-8 -*-
"""
Cvartale si loturi.

Un cvartal = o celula de latice ale carei 4 laturi sunt strazi. Fiindca lucram pe latice
(nu pe un graf arbitrar), nu avem nevoie de parcurgere de fete planare: celula e deja un
patrulater si stim exact care latura e strada si de ce rang.

Loturile se taie "in inel": un rAnd de loturi pe fiecare latura cu strada, cu fata spre
strada, si ce rAmAne in mijloc devine curte interioara / parcare. Asa arata cvartalele
reale si asa se obtine automat ce ne trebuie pentru cladirile vanilla: fiecare lot stie
unde e strada, deci stie in ce direcite trebuie sa priveasca fatada.
"""
from __future__ import annotations

import math

import numpy as np

from . import roads as R
from . import zoning as Z


class Lot:
    """Un lot de construit: patrulater, cu o latura la strada."""

    __slots__ = ("cx", "cy", "z", "width", "depth", "yaw", "zone", "street_kind",
                 "corner", "block", "poly", "kind")

    def __init__(self, cx, cy, z, width, depth, yaw, zone, street_kind,
                 corner=False, block=None, poly=None, kind="lot"):
        self.cx = float(cx)          # centrul lotului
        self.cy = float(cy)
        self.z = float(z)            # cota terenului in centru
        self.width = float(width)    # de-a lungul strazii
        self.depth = float(depth)    # perpendicular pe strada
        self.yaw = float(yaw)        # grade: direcita in care priveste fatada (spre strada)
        self.zone = int(zone)
        self.street_kind = int(street_kind)
        self.corner = bool(corner)
        self.block = block           # (i, j) celula de latice
        self.poly = poly             # (4,2) colturile, pentru desen
        self.kind = kind             # "lot" | "yard"

    @property
    def area(self) -> float:
        return self.width * self.depth

    def to_json(self) -> dict:
        return {"x": round(self.cx, 2), "y": round(self.cy, 2), "z": round(self.z, 2),
                "w": round(self.width, 2), "d": round(self.depth, 2), "yaw": round(self.yaw, 1),
                "zone": Z.ZONE_NAMES.get(self.zone, "?"), "street": R.KIND_NAMES.get(self.street_kind, "?"),
                "corner": self.corner, "kind": self.kind}


class Block:
    """Un cvartal: patrulaterul dintre 4 strazi, plus loturile lui."""

    __slots__ = ("i", "j", "corners", "zone", "lots", "yard", "sides")

    def __init__(self, i, j, corners, zone, sides):
        self.i = int(i)
        self.j = int(j)
        self.corners = corners      # (4,2) in ordine: SV, SE, NE, NV in spatiul laticei
        self.zone = int(zone)
        self.sides = sides          # 4 x (kind, exista) in ordinea laturilor
        self.lots = []
        self.yard = None

    @property
    def center(self):
        return self.corners.mean(axis=0)


def _inset_quad(corners: np.ndarray, amounts) -> np.ndarray:
    """
    Retrage fiecare latura a patrulaterului cu `amounts[k]` metri spre interior.

    Nu e un offset poligonal exact (nu avem nevoie): mutam fiecare latura pe normala ei
    interioara si recalculam colturile prin intersectia liniilor vecine. Pentru cvartale
    aproape dreptunghiulare, diferenta e sub un centimetru.
    """
    n = len(corners)
    lines = []
    centroid = corners.mean(axis=0)
    for k in range(n):
        a = corners[k]
        b = corners[(k + 1) % n]
        d = b - a
        length = math.hypot(d[0], d[1])
        if length < 1e-6:
            lines.append(None)
            continue
        d = d / length
        nrm = np.array([-d[1], d[0]])
        # normala spre interior
        if np.dot(centroid - a, nrm) < 0:
            nrm = -nrm
        lines.append((a + nrm * float(amounts[k]), d))

    out = []
    for k in range(n):
        l_prev = lines[(k - 1) % n]
        l_cur = lines[k]
        if l_prev is None or l_cur is None:
            out.append(corners[k])
            continue
        p1, d1 = l_prev
        p2, d2 = l_cur
        denom = d1[0] * d2[1] - d1[1] * d2[0]
        if abs(denom) < 1e-9:
            out.append(corners[k])
            continue
        t = ((p2[0] - p1[0]) * d2[1] - (p2[1] - p1[1]) * d2[0]) / denom
        out.append(p1 + d1 * t)
    return np.array(out, dtype=np.float64)


def _quad_ok(quad: np.ndarray, min_side: float = 4.0) -> bool:
    for k in range(4):
        if np.linalg.norm(quad[(k + 1) % 4] - quad[k]) < min_side:
            return False
    # convexitate: toate produsele vectoriale au acelasi semn
    signs = []
    for k in range(4):
        a = quad[(k + 1) % 4] - quad[k]
        b = quad[(k + 2) % 4] - quad[(k + 1) % 4]
        signs.append(np.sign(a[0] * b[1] - a[1] * b[0]))
    return len(set(s for s in signs if s != 0)) == 1


class BlockPlan:
    """Construieste cvartalele si loturile pentru un `CityGrid`."""

    def __init__(self, cfg, grid: "R.CityGrid", zones: "Z.ZoneField", rng, log=print):
        self.cfg = cfg
        self.grid = grid
        self.zones = zones
        self.rng = rng
        self.log = log
        self.blocks = []
        self.lots = []

    # ------------------------------------------------------------------
    def build(self):
        grid = self.grid
        made = 0
        skipped = 0
        for j in range(grid.nv - 1):
            for i in range(grid.nu - 1):
                block = self._make_block(i, j)
                if block is None:
                    skipped += 1
                    continue
                self.blocks.append(block)
                made += 1

        for block in self.blocks:
            self._subdivide(block)
            self.lots.extend(block.lots)

        buildable = [l for l in self.lots if l.kind == "lot"]
        yards = len(self.lots) - len(buildable)
        self.log(f"  cvartale: {made} (ignorate {skipped}), loturi {len(buildable)} + {yards} curti")
        if buildable:
            widths = np.array([l.width for l in buildable])
            depths = np.array([l.depth for l in buildable])
            self.log(f"  loturi: latime {widths.min():.0f}-{widths.max():.0f} m "
                     f"(medie {widths.mean():.0f}), adancime {depths.min():.0f}-{depths.max():.0f} m")
        return self

    def _make_block(self, i, j):
        """Celula (i,j) devine cvartal daca are toate 4 nodurile bune si cel putin 2 strazi."""
        grid = self.grid
        v = grid.valid
        if not (v[j, i] and v[j, i + 1] and v[j + 1, i + 1] and v[j + 1, i]):
            return None

        corners = np.array([grid.P[j, i], grid.P[j, i + 1], grid.P[j + 1, i + 1], grid.P[j + 1, i]],
                           dtype=np.float64)
        if not _quad_ok(corners, min_side=8.0):
            return None

        # laturile in ordinea colturilor: 0 = sud (j), 1 = est (i+1), 2 = nord (j+1), 3 = vest (i)
        sides = [
            (int(grid.Hk[j, i]), bool(grid.H[j, i])),
            (int(grid.Vk[j, i]), bool(grid.V[j, i + 1])),
            (int(grid.Hk[j + 1, i]), bool(grid.H[j + 1, i])),
            (int(grid.Vk[j, i]), bool(grid.V[j, i])),
        ]
        if sum(1 for _kind, exists in sides if exists) < 2:
            return None

        center = corners.mean(axis=0)
        zone = int(self.zones.at(center[0], center[1]))
        if zone == Z.NONE:
            return None
        return Block(i, j, corners, zone, sides)

    # ------------------------------------------------------------------ loturi
    def _subdivide(self, block: "Block"):
        cfg = self.cfg
        rules = Z.rules_for(block.zone)
        lot_w, lot_d = rules["lot"]
        lot_w = float(lot_w)
        lot_d = float(lot_d)

        # Retragerea de la axa strazii: jumatate de carosabil + trotuar.
        amounts = []
        for kind, exists in block.sides:
            if exists:
                amounts.append(self.grid.width_of(kind) * 0.5 + float(cfg.city_sidewalk))
            else:
                amounts.append(0.5)     # latura fara strada: doar un mic decalaj
        inner = _inset_quad(block.corners, amounts)
        if not _quad_ok(inner, min_side=6.0):
            return

        if block.zone == Z.PARK:
            block.yard = inner
            block.lots.append(self._yard_lot(block, inner))
            return

        # Cat de adanc e cvartalul pe fiecare direcite: distanta intre laturile opuse.
        span_ns = 0.5 * (np.linalg.norm(inner[3] - inner[0]) + np.linalg.norm(inner[2] - inner[1]))
        span_ew = 0.5 * (np.linalg.norm(inner[1] - inner[0]) + np.linalg.norm(inner[2] - inner[3]))

        # Adancimea rAndului de loturi: nu mai mult de jumatate din cvartal, ca sa rAmAna curte.
        depth_for = {
            0: min(lot_d, span_ns * 0.45),
            2: min(lot_d, span_ns * 0.45),
            1: min(lot_d, span_ew * 0.45),
            3: min(lot_d, span_ew * 0.45),
        }

        used = []
        for side in range(4):
            kind, exists = block.sides[side]
            if not exists:
                continue
            depth = depth_for[side]
            if depth < 8.0:
                continue
            self._row_of_lots(block, inner, side, kind, lot_w, depth, used)

        # Miezul rAmas: curte / parcare, daca a mai rAmas ceva.
        core_amounts = [depth_for[k] if block.sides[k][1] and depth_for[k] >= 8.0 else 0.0
                        for k in range(4)]
        if any(core_amounts):
            core = _inset_quad(inner, core_amounts)
            if _quad_ok(core, min_side=10.0):
                block.yard = core
                block.lots.append(self._yard_lot(block, core))

    def _row_of_lots(self, block, inner, side, street_kind, lot_w, depth, used):
        """Un rAnd de loturi pe latura `side`, cu fata la strada."""
        a = inner[side]
        b = inner[(side + 1) % 4]
        edge = b - a
        length = float(np.hypot(edge[0], edge[1]))
        if length < 8.0:
            return
        along = edge / length
        # normala spre interiorul cvartalului
        inward = np.array([-along[1], along[0]])
        centroid = inner.mean(axis=0)
        if np.dot(centroid - a, inward) < 0:
            inward = -inward

        # Colturile cvartalului sunt "scumpe": lasam loc pentru lotul de colt al laturii vecine.
        margin = 0.0
        usable = length - 2 * margin
        count = max(1, int(round(usable / lot_w)))
        width = usable / count
        if width < 7.0:
            count = max(1, int(usable // 7.0))
            width = usable / count if count else usable
        if width < 6.0:
            return

        # Fatada priveste spre strada, adica invers decat `inward`.
        yaw = math.degrees(math.atan2(-inward[1], -inward[0]))

        for k in range(count):
            t0 = margin + k * width
            tc = t0 + width * 0.5
            base = a + along * tc
            center = base + inward * (depth * 0.5)
            poly = np.array([
                a + along * t0,
                a + along * (t0 + width),
                a + along * (t0 + width) + inward * depth,
                a + along * t0 + inward * depth,
            ], dtype=np.float64)

            # Nu suprapunem loturile de pe laturi vecine (colturile cvartalului).
            if any(np.hypot(center[0] - qx, center[1] - qy) < (min(width, depth) * 0.5 + qr)
                   for qx, qy, qr in used):
                continue
            used.append((float(center[0]), float(center[1]), min(width, depth) * 0.35))

            z = float(self.grid.height_at(np.array([center[0]]), np.array([center[1]]))[0])
            lot = Lot(center[0], center[1], z, width, depth, yaw, block.zone, street_kind,
                      corner=(k == 0 or k == count - 1), block=(block.i, block.j), poly=poly)
            block.lots.append(lot)

    def _yard_lot(self, block, poly):
        center = poly.mean(axis=0)
        w = float(np.linalg.norm(poly[1] - poly[0]))
        d = float(np.linalg.norm(poly[3] - poly[0]))
        z = float(self.grid.height_at(np.array([center[0]]), np.array([center[1]]))[0])
        return Lot(center[0], center[1], z, w, d, 0.0, block.zone, 0,
                   corner=False, block=(block.i, block.j), poly=poly, kind="yard")

    # ------------------------------------------------------------------ raport
    def buildable(self):
        return [l for l in self.lots if l.kind == "lot"]

    def stats(self) -> dict:
        out = {"blocks": len(self.blocks), "lots": 0, "yards": 0, "by_zone": {}}
        for lot in self.lots:
            if lot.kind == "yard":
                out["yards"] += 1
                continue
            out["lots"] += 1
            name = Z.ZONE_NAMES.get(lot.zone, "?")
            out["by_zone"][name] = out["by_zone"].get(name, 0) + 1
        return out
