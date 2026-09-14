# -*- coding: utf-8 -*-
"""
Zonarea orasului: ce fel de cladiri au dreptul sa apara unde.

Zona e un cAmp scalar calculat din distanta la centru + zgomot + relief, nu o lista de
poligoane: e mai ieftin, se poate eSantiona oriunde si iese cu granite neregulate, ca in
orasele reale. Se poate suprascrie cu o grila pictata manual (studio), pastrata in map.json.

Zonele se folosesc in doua locuri: `roads` sterge strazi locale in zonele rare (suburbie,
industrial) ca sa iasa cvartale mari, si `placer` alege din ce categorii de arhetipuri ia
cladirea pentru fiecare lot.
"""
from __future__ import annotations

import math

import numpy as np

from ..noise import fbm, smoothstep

# Ordinea conteaza: indicii ajung in grila uint8.
NONE = 0
DOWNTOWN = 1
MIDTOWN = 2
RESIDENTIAL = 3
SUBURB = 4
INDUSTRIAL = 5
PARK = 6

ZONE_NAMES = {
    NONE: "none",
    DOWNTOWN: "downtown",
    MIDTOWN: "midtown",
    RESIDENTIAL: "residential",
    SUBURB: "suburb",
    INDUSTRIAL: "industrial",
    PARK: "park",
}

# Culori pentru previzualizarea 2D (RGB 0..255).
ZONE_COLORS = {
    NONE: (120, 120, 110),
    DOWNTOWN: (86, 96, 128),
    MIDTOWN: (112, 116, 140),
    RESIDENTIAL: (150, 138, 120),
    SUBURB: (168, 164, 126),
    INDUSTRIAL: (132, 118, 104),
    PARK: (104, 140, 92),
}

# Regulile de plasare per zona. `cats` = categoriile de arhetipuri acceptate, in ordinea
# preferintei; `setback` = cat se retrage cladirea de la trotuar (m); `lot` = (latime, adancime)
# tinta a lotului; `fill` = cat trebuie sa umple cladirea lotul ca sa fie acceptata.
ZONE_RULES = {
    DOWNTOWN: {
        "cats": ("tower", "midrise", "lowrise"),
        "corner_cats": ("midrise", "lowrise", "shop"),
        "setback": 0.0,
        "lot": (24.0, 30.0),
        "fill": 0.55,
        "style": "downtown",
        "keep_local_streets": 1.0,
    },
    MIDTOWN: {
        "cats": ("midrise", "lowrise", "shop"),
        "corner_cats": ("lowrise", "shop"),
        "setback": 1.0,
        "lot": (20.0, 26.0),
        "fill": 0.4,
        "style": "downtown",
        "keep_local_streets": 0.9,
    },
    RESIDENTIAL: {
        "cats": ("lowrise", "house", "shop"),
        "corner_cats": ("shop", "lowrise"),
        "setback": 3.0,
        "lot": (17.0, 24.0),
        "fill": 0.30,   # o casa reala ocupa cam o treime din lot
        "style": None,
        "keep_local_streets": 0.75,
    },
    SUBURB: {
        "cats": ("house", "garage"),
        "corner_cats": ("house",),
        "setback": 6.0,
        "lot": (16.0, 26.0),
        "fill": 0.22,   # curte mare in suburbie
        "style": "suburb",
        "keep_local_streets": 0.55,
    },
    INDUSTRIAL: {
        "cats": ("warehouse", "garage"),
        "corner_cats": ("warehouse",),
        "setback": 5.0,
        "lot": (46.0, 40.0),
        "fill": 0.35,
        "style": "industrial",
        "keep_local_streets": 0.2,
    },
    PARK: {
        "cats": (),
        "corner_cats": (),
        "setback": 0.0,
        "lot": (30.0, 30.0),
        "fill": 0.0,
        "style": None,
        "keep_local_streets": 0.4,
    },
}


def rules_for(zone: int) -> dict:
    return ZONE_RULES.get(int(zone), ZONE_RULES[RESIDENTIAL])


class ZoneField:
    """
    Grila de zone peste toata harta, la pas grosier (implicit 8 m).

    `zones[j, i]` = indicele zonei pentru celula (i, j). Se eSantioneaza cu `at(x, y)`.
    """

    def __init__(self, cfg, world, rng, cell: float = 8.0, painted=None):
        self.cfg = cfg
        self.world = world
        self.rng = rng
        self.cell = float(cell)
        self.n = int(math.ceil(cfg.size / self.cell)) + 1
        self.center = (float(cfg.city_center[0]) * cfg.size, float(cfg.city_center[1]) * cfg.size)
        self.radius = float(cfg.city_radius)
        self.zones = None
        self.mask = None          # in interiorul orasului (uscat, panta ok, in forma de oras)
        self.painted = painted    # grila mica (lista de liste) pictata in studio, sau None

    # ------------------------------------------------------------------ helpers
    def _grid_xy(self):
        coords = np.arange(self.n, dtype=np.float64) * self.cell
        return np.meshgrid(coords, coords)

    def at(self, x, y):
        """Zona in punctele (x, y) - metri, coordonate locale de harta."""
        ix = np.clip(np.round(np.asarray(x, dtype=np.float64) / self.cell).astype(np.int64), 0, self.n - 1)
        iy = np.clip(np.round(np.asarray(y, dtype=np.float64) / self.cell).astype(np.int64), 0, self.n - 1)
        return self.zones[iy, ix]

    def inside(self, x, y):
        ix = np.clip(np.round(np.asarray(x, dtype=np.float64) / self.cell).astype(np.int64), 0, self.n - 1)
        iy = np.clip(np.round(np.asarray(y, dtype=np.float64) / self.cell).astype(np.int64), 0, self.n - 1)
        return self.mask[iy, ix]

    # ------------------------------------------------------------------ construire
    def build(self):
        cfg = self.cfg
        seed = int(cfg.seed) ^ 0x5C17
        gx, gy = self._grid_xy()
        cx, cy = self.center
        R = max(1.0, self.radius)

        dx = gx - cx
        dy = gy - cy
        dist = np.hypot(dx, dy)
        ang = np.arctan2(dy, dx)

        # Forma orasului: disc cu contur neregulat (nu vrem un cerc perfect).
        wob = fbm(np.cos(ang) * 1.7 + 3.1, np.sin(ang) * 1.7 - 1.4, 4, seed=seed + 3) * 0.5 + 0.5
        shape_r = R * (0.82 + 0.34 * wob)
        r = dist / np.maximum(shape_r, 1.0)

        # Zgomotul care strica granitele concentrice.
        u = gx / cfg.size
        v = gy / cfg.size
        jitter = fbm(u * 5.5, v * 5.5, 4, seed=seed + 7) * float(cfg.city_zone_noise)
        rn = r + jitter

        zones = np.full((self.n, self.n), NONE, dtype=np.uint8)
        zones[rn < 1.05] = SUBURB
        zones[rn < 0.72] = RESIDENTIAL
        zones[rn < 0.46] = MIDTOWN
        zones[rn < 0.24] = DOWNTOWN

        # Lobul industrial: un sector unghiular, spre exterior, de obicei langa apa/drum.
        ind_dir = float(self.rng.uniform(0, 2 * math.pi))
        d_ang = np.abs(np.arctan2(np.sin(ang - ind_dir), np.cos(ang - ind_dir)))
        ind = (d_ang < 0.62) & (rn > 0.42) & (rn < 1.18)
        zones[ind] = INDUSTRIAL

        # Parcuri: buzunare de zgomot, mai probabile spre margine, niciodata in centru.
        park_noise = fbm(u * 9.0 + 11.0, v * 9.0 - 4.0, 3, seed=seed + 13) * 0.5 + 0.5
        park = (park_noise > 0.70) & (rn > 0.28) & (rn < 1.05)
        zones[park] = PARK

        # Terenul are ultimul cuvant: apa si pantele mari nu se construiesc.
        h = self.world.sample(self.world.h, gx, gy)
        slope = self.world.sample(self.world.slope, gx, gy)
        buildable = (h > 2.0) & (slope < 0.42)
        zones[~buildable] = NONE
        # Panta medie -> parc in loc de cartier (dealurile din oras rup cladirile vanilla).
        steep = (slope > 0.26) & (zones != NONE)
        zones[steep] = PARK

        zones[rn >= 1.05] = NONE

        if self.painted is not None:
            zones = self._apply_painted(zones)

        self.zones = zones
        self.mask = zones != NONE
        return self

    def _apply_painted(self, zones):
        """Suprapune grila pictata in studio (orice rezolutie, 0 = nu schimba nimic)."""
        try:
            painted = np.asarray(self.painted, dtype=np.int32)
        except (TypeError, ValueError):
            return zones
        if painted.ndim != 2 or painted.size == 0:
            return zones
        ph, pw = painted.shape
        iy = np.clip((np.arange(self.n) * ph // self.n), 0, ph - 1)
        ix = np.clip((np.arange(self.n) * pw // self.n), 0, pw - 1)
        big = painted[np.ix_(iy, ix)]
        valid = (big > 0) & (big <= PARK)
        out = zones.copy()
        out[valid] = big[valid].astype(np.uint8)
        return out

    # ------------------------------------------------------------------ raport
    def stats(self) -> dict:
        out = {}
        total = float(self.mask.sum()) or 1.0
        area_cell = self.cell * self.cell
        for zone, name in ZONE_NAMES.items():
            if zone == NONE:
                continue
            count = int((self.zones == zone).sum())
            if count:
                out[name] = {"cells": count, "area_ha": round(count * area_cell / 10000.0, 2),
                             "share": round(count / total, 3)}
        out["built_area_ha"] = round(total * area_cell / 10000.0, 2)
        return out

    def summary(self) -> str:
        parts = []
        for zone, name in ZONE_NAMES.items():
            if zone == NONE:
                continue
            count = int((self.zones == zone).sum())
            if count:
                parts.append(f"{name} {count * self.cell * self.cell / 10000.0:.1f} ha")
        return ", ".join(parts) if parts else "nimic construibil"
