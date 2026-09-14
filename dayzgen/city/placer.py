# -*- coding: utf-8 -*-
"""
Cladiri vanilla GTA V pe loturi.

Pentru fiecare lot: alege din catalog un arhetip care incape (dupa zona, latime, adancime),
il intoarce cu fata spre strada, il retrage de la trotuar cat cere zona si il aseaza pe
teren. Nu creeaza geometrie: iese doar o lista de entitati (model + pozitie + rotatie),
care devine .ymap pentru joc si scena de previzualizare pentru Blender.

Conventii:
- `lot.yaw` = directia in care priveste fatada (spre strada), grade, trigonometric;
- fata unui model vanilla se presupune pe -Y local, corectabila per arhetip cu `yaw_offset`;
- heading-ul GTA (rotatie pe Z, grade) care duce -Y local pe directia f este yaw + 90.
"""
from __future__ import annotations

import math
import random

from . import zoning as Z


class Placement:
    __slots__ = ("model", "x", "y", "z", "heading", "zone", "category", "lot", "sx", "sy",
                 "height", "lod", "ytyp", "footprint")

    def to_json(self) -> dict:
        return {"model": self.model, "x": round(self.x, 3), "y": round(self.y, 3), "z": round(self.z, 3),
                "heading": round(self.heading, 2), "zone": Z.ZONE_NAMES.get(self.zone, "?"),
                "category": self.category, "lot": self.lot, "size": [round(self.sx, 2), round(self.sy, 2),
                                                                     round(self.height, 2)],
                "lod": round(self.lod, 1), "ytyp": self.ytyp}


def _rot(x: float, y: float, deg: float):
    r = math.radians(deg)
    c, s = math.cos(r), math.sin(r)
    return x * c - y * s, x * s + y * c


def _obb(cx, cy, hx, hy, deg):
    """Colturile unui dreptunghi rotit (pentru testul de suprapunere)."""
    return [(cx + px, cy + py) for px, py in (_rot(sx * hx, sy * hy, deg)
                                              for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)))]


def _overlap(a, b, margin: float = 0.5) -> bool:
    """Separating axis test intre doua dreptunghiuri rotite; `margin` = cat se pot atinge."""
    for poly in (a, b):
        for i in range(4):
            x1, y1 = poly[i]
            x2, y2 = poly[(i + 1) % 4]
            ax, ay = y1 - y2, x2 - x1
            norm = math.hypot(ax, ay) or 1.0
            ax, ay = ax / norm, ay / norm
            pa = [px * ax + py * ay for px, py in a]
            pb = [px * ax + py * ay for px, py in b]
            if max(pa) - margin <= min(pb) or max(pb) - margin <= min(pa):
                return False
    return True


def _ytyp_of(arch) -> str:
    for tag in arch.tags:
        if tag.startswith("ytyp:"):
            return tag[5:]
    return ""


# Zonele jocului din care vin modelele (prefixul fisierului .ytyp). Portul, aeroportul si zonele
# industriale au "cladiri" care de fapt sunt stive de containere, rezervoare si pasarele: au
# acoperis plin, deci trec de filtrul `solid`, dar intr-un cartier de case arata absurd.
INDUSTRIAL_AREAS = ("port", "airport", "indust", "docks")
# Acelasi lucru dupa prefixul modelului: po1 = portul, ap1 = aeroportul, id1/id2 = industrial.
# Unele vin din .ytyp-uri cu nume ne-standard (ex. interioare), deci prefixul e plasa de siguranta.
INDUSTRIAL_PREFIXES = ("po1_", "ap1_", "id1_", "id2_", "hei_po1_", "hei_ap1_", "hei_id")


def _is_industrial(arch) -> bool:
    return (_ytyp_of(arch).split("_metadata")[0].startswith(INDUSTRIAL_AREAS)
            or arch.name.startswith(INDUSTRIAL_PREFIXES))


class BuildingPlacer:
    """
    `require_lod`: foloseste doar arhetipuri cu eticheta `haslod` (cladiri intregi). Daca nu
    exista niciunul care sa incapa, lotul ramane liber - mai bine curte decat o bucata de fatada.
    """

    def __init__(self, cfg, city, catalog, seed=None, log=print, require_lod=True):
        self.cfg = cfg
        self.city = city
        self.catalog = catalog
        self.rng = random.Random(int(cfg.seed if seed is None else seed) ^ 0xB11D)
        self.log = log
        self.require_lod = require_lod
        # Dupa tools\measure_solidity.py catalogul stie care modele au acoperis (`solid`):
        # schelele, cadrele si balustradele cu LOD propriu raman pe dinafara.
        self.require_solid = any("solid" in a.tags for a in catalog.items.values())
        self.placements = []
        self.empty = 0
        self._boxes = []
        self._recent = []
        self._uses = {}

    # ------------------------------------------------------------------ alegere
    def _options(self, width, depth, cats, rules, zone):
        industrial_zone = zone == Z.INDUSTRIAL

        def fit(style):
            opts = self.catalog.fit(width, depth, cats, style=style, tolerance=0.12, min_fill=rules["fill"])
            # Acoperisul masurat e semnalul cel mai bun pentru o cladire intreaga. LOD-ul propriu
            # conteaza doar cat lipseste masuratoarea: casele mici au des un LOD comun, de grup.
            if self.require_solid:
                opts = [o for o in opts if "solid" in o[0].tags]
            elif self.require_lod:
                opts = [o for o in opts if "haslod" in o[0].tags]
            if industrial_zone:
                opts = [o for o in opts if _is_industrial(o[0])] or opts
            else:
                opts = [o for o in opts if not _is_industrial(o[0])]
            return opts

        # Stilul zonei e o preferinta, nu o conditie: fara potriviri in stil, orice stil e mai
        # bun decat un lot gol. Fallback-ul vine DUPA filtrul de cladiri intregi.
        style = rules.get("style")
        return (fit(style) if style else []) or fit(None)

    def _choose(self, lot, depth, rules):
        cats = rules["corner_cats"] if lot.corner and rules["corner_cats"] else rules["cats"]
        opts = self._options(lot.width, depth, cats, rules, lot.zone)
        if not opts and cats is not rules["cats"]:
            opts = self._options(lot.width, depth, rules["cats"], rules, lot.zone)
        if not opts:
            return None
        # Varietate: alegere ponderata pe toate variantele. Un model deja folosit pierde repede
        # din sansa, iar cel de la lotul vecin nu se repeta deloc; umplerea lotului conteaza,
        # dar nu mai decide singura (altfel acelasi model castiga toate loturile de aceeasi marime).
        weights = []
        for arch, _extra, fill in opts:
            if arch.name in self._recent:
                weights.append(0.0)
                continue
            uses = self._uses.get(arch.name, 0)
            bonus = 1.3 if "haslod" in arch.tags else 1.0
            weights.append(bonus * (0.35 + fill) / (1.0 + uses) ** 1.5)
        if not any(weights):
            weights = [1.0] * len(opts)
        return self.rng.choices(opts, weights=weights, k=1)[0]

    # ------------------------------------------------------------------ plasare
    def place(self):
        grid = self.city.grid
        lots = self.city.lots
        for index, lot in enumerate(lots):
            rules = Z.rules_for(lot.zone)
            if not rules["cats"]:
                continue
            setback = float(rules["setback"])
            depth = lot.depth - setback
            if depth < 6.0 or lot.width < 6.0:
                self.empty += 1
                continue
            choice = self._choose(lot, depth, rules)
            if choice is None:
                self.empty += 1
                continue
            arch, extra, _fill = choice

            fx, fy = math.cos(math.radians(lot.yaw)), math.sin(math.radians(lot.yaw))
            heading = (lot.yaw + 90.0 + arch.yaw_offset + extra) % 360.0
            m_depth = arch.sy if extra == 0 else arch.sx
            m_width = arch.sx if extra == 0 else arch.sy
            shift = lot.depth * 0.5 - setback - m_depth * 0.5
            ax, ay = lot.cx + fx * shift, lot.cy + fy * shift

            box = _obb(ax, ay, m_width * 0.5, m_depth * 0.5, lot.yaw + 90.0)
            if any(_overlap(box, other) for other in self._boxes):
                self.empty += 1
                continue

            # Pe panta, baza sta pe coltul cel mai de jos: mai bine putin ingropata decat plutind.
            xs = [p[0] for p in box] + [ax]
            ys = [p[1] for p in box] + [ay]
            ground = float(min(grid.height_at(xs, ys)))

            ox, oy = _rot(arch.center_xy[0], arch.center_xy[1], heading)
            item = Placement()
            item.model = arch.name
            item.x = ax - ox
            item.y = ay - oy
            item.z = ground - arch.base_z
            item.heading = heading
            item.zone = lot.zone
            item.category = arch.category
            item.lot = index
            item.sx, item.sy, item.height = arch.sx, arch.sy, arch.height
            item.lod = max(float(arch.lod_dist or 0.0), 150.0)
            item.ytyp = _ytyp_of(arch)
            item.footprint = box
            self.placements.append(item)
            self._boxes.append(box)
            self._recent = (self._recent + [arch.name])[-4:]
            self._uses[arch.name] = self._uses.get(arch.name, 0) + 1

        cats = {}
        for p in self.placements:
            cats[p.category] = cats.get(p.category, 0) + 1
        self.log(f"  cladiri: {len(self.placements)} plasate, {self.empty} loturi libere; "
                 + ", ".join(f"{k} {v}" for k, v in sorted(cats.items(), key=lambda kv: -kv[1])))
        return self

    def ytyps(self) -> list:
        return sorted({p.ytyp for p in self.placements if p.ytyp})

    def models(self) -> list:
        return sorted({p.model for p in self.placements})
