# -*- coding: utf-8 -*-
"""
Orchestrarea stratului urban: zonare -> strazi -> teren nivelat -> cvartale -> loturi.

Se ruleaza dupa `World.build_roads()` (drumurile inter-localitati exista deja) si inainte
de vegetatie, ca padurea sa nu mai creasca pe strazi. Nu are nevoie de Blender.
"""
from __future__ import annotations

import math

import numpy as np

from . import blocks as B
from . import roads as R
from . import zoning as Z


class CityPlan:
    """Planul complet al orasului, fara nicio geometrie 3D."""

    def __init__(self, cfg, world, rng=None, log=print):
        self.cfg = cfg
        self.world = world
        self.rng = rng if rng is not None else np.random.default_rng(int(cfg.seed) ^ 0x1D0C)
        self.log = log
        self.zones = None
        self.grid = None
        self.plan = None

    @property
    def lots(self):
        return self.plan.buildable() if self.plan else []

    @property
    def center(self):
        return self.zones.center if self.zones else (0.0, 0.0)

    def build(self):
        cfg = self.cfg
        self.log(f"  oras: centru ({cfg.city_center[0]:.2f}, {cfg.city_center[1]:.2f}) "
                 f"= ({self.cfg.city_center[0] * cfg.size:.0f}, {cfg.city_center[1] * cfg.size:.0f}) m, "
                 f"raza {cfg.city_radius:.0f} m")

        painted = cfg.city_zones_painted or None
        self.zones = Z.ZoneField(cfg, self.world, self.rng, painted=painted).build()
        self.log(f"  zone: {self.zones.summary()}")
        if not self.zones.mask.any():
            self.log("  oras: nu exista teren construibil in raza data - sar peste oras")
            return self

        self.grid = self._best_grid()
        self.grid.apply_terrain()
        # Zonarea s-a calculat pe relieful vechi; dupa nivelare pantele s-au schimbat,
        # deci o recalculam ca loturile sa nu moSteneasca decizii luate pe teren dispgrut.
        self.zones.build()

        # Parcurile sunt singura parte a orasului unde vegetatia naturala are voie sa creasca.
        gx, gy = np.meshgrid(self.world.coords, self.world.coords)
        self.world.park_mask = (self.zones.at(gx, gy) == Z.PARK) & self.grid.city_mask

        self.plan = B.BlockPlan(cfg, self.grid, self.zones, self.rng, log=self.log).build()
        return self

    @staticmethod
    def _score(grid) -> int:
        """Cate celule de latice devin cvartale: toate 4 nodurile bune si minim 2 strazi."""
        covered = grid.cell_covered()
        sides = (grid.H[:-1, :].astype(np.int32) + grid.H[1:, :] + grid.V[:, :-1] + grid.V[:, 1:])
        return int((covered & (sides >= 2)).sum())

    def _best_grid(self, tries: int = 8):
        """
        Unghiul gridului decide cat de bine se asaza orasul pe relief: acelasi teren poate da
        5 sau 20 de cvartale. Cand unghiul nu e fixat in config, incercam mai multe si il
        pastram pe cel cu cele mai multe cvartale. Terenul nu e atins pana la alegere.
        """
        cfg = self.cfg
        if cfg.city_angle >= 0:
            return R.CityGrid(cfg, self.world, self.zones, self.rng, log=self.log).build()

        quiet = lambda *args, **kwargs: None  # noqa: E731
        base = float(self.rng.uniform(0, math.pi / 2))
        best, best_score = None, -1
        for k in range(tries):
            angle = (base + k * (math.pi / 2) / tries) % (math.pi / 2)
            grid = R.CityGrid(cfg, self.world, self.zones, self.rng, log=quiet, angle=angle).build()
            score = self._score(grid)
            if score > best_score:
                best, best_score = grid, score
        best.log = self.log
        kinds = best._count_kinds()
        self.log(f"  oras: grid {best.nu}x{best.nv} la {best.step:.0f} m, rotit {math.degrees(best.angle):.0f} grade "
                 f"(cel mai bun din {tries} unghiuri: {best_score} cvartale posibile)")
        self.log(f"  strazi: {sum(kinds.values())} segmente ("
                 + ", ".join(f"{R.KIND_NAMES[k]} {v}" for k, v in sorted(kinds.items())) + ")")
        return best

    # ------------------------------------------------------------------ export
    def to_json(self) -> dict:
        """Planul, pentru studio / depanare (nu intra in resursa FiveM)."""
        if not self.plan:
            return {"city": False}
        cfg = self.cfg
        return {
            "city": True,
            "center": [round(self.center[0], 1), round(self.center[1], 1)],
            "radius": cfg.city_radius,
            "angle_deg": round(np.degrees(self.grid.angle), 1),
            "block": cfg.city_block,
            "origin": [cfg.origin_x, cfg.origin_y],
            "zones": self.zones.stats(),
            "streets": {R.KIND_NAMES[k]: v for k, v in self.grid._count_kinds().items()},
            "blocks": self.plan.stats(),
            "lots": [lot.to_json() for lot in self.plan.buildable()],
        }

    def summary_lines(self) -> list:
        if not self.plan:
            return ["  oras: nimic generat"]
        stats = self.plan.stats()
        out = [f"  oras: {stats['blocks']} cvartale, {stats['lots']} loturi de construit"]
        for name, count in sorted(stats["by_zone"].items(), key=lambda kv: -kv[1]):
            out.append(f"    {name:12s} {count} loturi")
        return out
