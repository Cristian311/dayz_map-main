# -*- coding: utf-8 -*-
"""
Reteaua stradala a orasului.

Ideea: un grid regulat, dar *indoit* de un cAmp de zgomot neted, rotit cu un unghi
oarecare. Gridul da ordinea (cvartale dreptunghiulare, intersectii in cruce - fara asta
loturile ies degenerate si cladirile vanilla nu au cum sa se alinieze), iar indoirea si
stergerea selectiva a strazilor locale dau neregularitatea care face orasul credibil.

Ierarhie pe aceeasi latice: la fiecare `city_artery_every` linii o artera, la fiecare a
doua o colectoare, restul strazi locale. Zonele rare (suburbie, industrial) pierd o parte
din strazile locale, deci cvartalele lor ies mari, ca in realitate.

Partea importanta pentru cladiri: **cotele**. Inaltimea fiecarui nod de latice se
relaxeaza pana cand nicio strada nu depaseste `city_max_grade`, apoi tot terenul orasului
devine interpolarea biliniara a cotelor de nod. Asa strazile si cvartalele sunt de acord
intre ele si nu mai apar cladiri vanilla infipte in deal sau plutind.
"""
from __future__ import annotations

import math

import numpy as np

from ..noise import fbm
from . import zoning as Z

ARTERY = 1
COLLECTOR = 2
LOCAL = 3

KIND_NAMES = {ARTERY: "artera", COLLECTOR: "colectoare", LOCAL: "locala"}


class CityGrid:
    """Latice de strazi + cote, peste `world` si zonarea `zones`."""

    def __init__(self, cfg, world, zones: "Z.ZoneField", rng, log=print, angle=None):
        self.cfg = cfg
        self.world = world
        self.zones = zones
        self.rng = rng
        self.log = log

        self.center = zones.center
        self.step = float(cfg.city_block)
        if angle is not None:
            self.angle = float(angle)
        else:
            self.angle = (float(rng.uniform(0, math.pi / 2)) if cfg.city_angle < 0
                          else math.radians(float(cfg.city_angle)))
        self.warp_amp = float(cfg.city_warp) * self.step
        # Scara deformarii: sub ~2 cvartale liniile se indoaie vizibil de la un cvartal la
        # altul. Daca o facem mult mai mare, zgomotul devine o simpla translatie a intregului
        # oras si strazile arata perfect drepte.
        self.warp_scale = max(120.0, self.step * 1.8)
        self._wseed = int(cfg.seed) ^ 0x3B9F

        extent = float(cfg.city_radius) * 1.35
        half = int(math.ceil(extent / self.step))
        self.nu = 2 * half + 1
        self.nv = 2 * half + 1
        self.iu0 = half            # indicele nodului din centru
        self.iv0 = half

        self.P = None              # (nv, nu, 2) poziti in metri, coordonate locale de harta
        self.Zh = None             # (nv, nu) cote
        self.valid = None          # (nv, nu) bool
        self.H = None              # (nv, nu-1) exista strada intre (i,j)-(i+1,j)
        self.V = None              # (nv-1, nu) exista strada intre (i,j)-(i,j+1)
        self.Hk = None             # (nv, nu-1) tipul strazii
        self.Vk = None
        self.street_mask = None    # bool pe grila terenului: carosabil + trotuar
        self.city_mask = None      # bool pe grila terenului: suprafata orasului
        self.height_field = None   # (n, n) cotele orasului (doar informativ)

    # ------------------------------------------------------------------ geometrie
    def _warp(self, u, v):
        """Deplasarea care indoaie gridul. Neteda in (u,v), deci liniile rAmAn curbe continue."""
        if self.warp_amp <= 0.0:
            zero = np.zeros_like(np.asarray(u, dtype=np.float64))
            return zero, zero
        s = self.warp_scale
        du = fbm(np.asarray(u) / s + 4.7, np.asarray(v) / s - 2.3, 3, seed=self._wseed)
        dv = fbm(np.asarray(u) / s - 8.1, np.asarray(v) / s + 6.9, 3, seed=self._wseed + 101)
        return du * self.warp_amp, dv * self.warp_amp

    def _to_world(self, u, v):
        ca, sa = math.cos(self.angle), math.sin(self.angle)
        du, dv = self._warp(u, v)
        cx, cy = self.center
        x = cx + u * ca - v * sa + du
        y = cy + u * sa + v * ca + dv
        return x, y

    def _to_lattice(self, x, y, iters: int = 4):
        """Invers aproximativ al lui `_to_world`: (x,y) -> indici continui (fi, fj)."""
        ca, sa = math.cos(self.angle), math.sin(self.angle)
        cx, cy = self.center
        dx = np.asarray(x, dtype=np.float64) - cx
        dy = np.asarray(y, dtype=np.float64) - cy
        u = dx * ca + dy * sa
        v = -dx * sa + dy * ca
        # Punct fix: deplasarea e mica si neteda, deci converge in 2-3 pasi.
        for _ in range(max(1, iters)):
            du, dv = self._warp(u, v)
            ax = dx - du
            ay = dy - dv
            u = ax * ca + ay * sa
            v = -ax * sa + ay * ca
        return u / self.step + self.iu0, v / self.step + self.iv0

    def _line_kind(self, index: int) -> int:
        every = max(2, int(self.cfg.city_artery_every))
        # Indicii se raporteaza la centru, ca artera principala sa treaca prin centru.
        rel = index - self.iu0
        if rel % every == 0:
            return ARTERY
        if rel % 2 == 0:
            return COLLECTOR
        return LOCAL

    def width_of(self, kind: int) -> float:
        cfg = self.cfg
        if kind == ARTERY:
            return float(cfg.city_width_artery)
        if kind == COLLECTOR:
            return float(cfg.city_width_collector)
        return float(cfg.city_width_local)

    # ------------------------------------------------------------------ construire
    def build(self):
        self.log(f"  oras: grid {self.nu}x{self.nv} la {self.step:.0f} m, "
                 f"rotit {math.degrees(self.angle):.0f} grade")
        self._build_nodes()
        self._build_edges()
        self._relax_heights()
        self._keep_largest_component()
        self._prune()
        kinds = self._count_kinds()
        self.log(f"  strazi: {sum(kinds.values())} segmente ("
                 + ", ".join(f"{KIND_NAMES[k]} {v}" for k, v in sorted(kinds.items())) + ")")
        return self

    def _build_nodes(self):
        u = (np.arange(self.nu, dtype=np.float64) - self.iu0) * self.step
        v = (np.arange(self.nv, dtype=np.float64) - self.iv0) * self.step
        uu, vv = np.meshgrid(u, v)
        x, y = self._to_world(uu, vv)
        self.P = np.stack([x, y], axis=-1)

        margin = self.step * 0.5
        cfg = self.cfg
        inside_map = ((x > margin) & (x < cfg.size - margin)
                      & (y > margin) & (y < cfg.size - margin))
        self.valid = inside_map & self.zones.inside(x, y)
        self.Zh = self.world.sample(self.world.h, np.clip(x, 0, cfg.size), np.clip(y, 0, cfg.size))
        self.Zh = np.asarray(self.Zh, dtype=np.float64)

    def _build_edges(self):
        nv, nu = self.nv, self.nu
        vh = self.valid
        # O strada exista daca ambele capete sunt bune.
        self.H = vh[:, :-1] & vh[:, 1:]
        self.V = vh[:-1, :] & vh[1:, :]

        # Tipul vine din indicele liniei pe care sta strada.
        row_kind = np.array([self._line_kind(j) for j in range(nv)], dtype=np.uint8)
        col_kind = np.array([self._line_kind(i) for i in range(nu)], dtype=np.uint8)
        self.Hk = np.repeat(row_kind[:, None], nu - 1, axis=1)
        self.Vk = np.repeat(col_kind[None, :], nv - 1, axis=0)

        # Strazile locale se rarefiaza in functie de zona de la mijlocul segmentului.
        self._thin_local(self.H, self.Hk, axis=0)
        self._thin_local(self.V, self.Vk, axis=1)

    def _thin_local(self, exists, kinds, axis: int):
        """Sterge o parte din strazile locale, cu probabilitatea data de zona."""
        if axis == 0:
            mid = 0.5 * (self.P[:, :-1, :] + self.P[:, 1:, :])
        else:
            mid = 0.5 * (self.P[:-1, :, :] + self.P[1:, :, :])
        zone = self.zones.at(mid[..., 0], mid[..., 1])
        keep_prob = np.ones(zone.shape, dtype=np.float64)
        for z in Z.ZONE_NAMES:
            if z == Z.NONE:
                continue
            keep_prob[zone == z] = float(Z.rules_for(z).get("keep_local_streets", 1.0))
        roll = self.rng.random(zone.shape)
        drop = (kinds == LOCAL) & (roll > keep_prob)
        exists &= ~drop

    # ------------------------------------------------------------------ cote
    def _relax_heights(self):
        """
        Aduce cotele nodurilor la o forma in care nicio strada nu depaseste panta maxima.

        Trei forte, aplicate iterativ: netezire intre vecini, limitarea pantei pe fiecare
        segment si o atractie slaba spre teren (ca orasul sa nu devina un platou plutitor).
        """
        cfg = self.cfg
        max_grade = float(cfg.city_max_grade)
        z = self.Zh.copy()
        terrain = self.Zh.copy()
        valid = self.valid
        if not valid.any():
            return

        # Lungimile reale ale segmentelor (gridul e indoit, deci nu sunt egale).
        dH = np.linalg.norm(self.P[:, 1:, :] - self.P[:, :-1, :], axis=-1)
        dV = np.linalg.norm(self.P[1:, :, :] - self.P[:-1, :, :], axis=-1)
        okH = self.H
        okV = self.V

        for _ in range(120):
            acc = np.zeros_like(z)
            cnt = np.zeros_like(z)
            # netezire de-a lungul strazilor existente
            acc[:, :-1] += np.where(okH, z[:, 1:], 0.0)
            cnt[:, :-1] += okH
            acc[:, 1:] += np.where(okH, z[:, :-1], 0.0)
            cnt[:, 1:] += okH
            acc[:-1, :] += np.where(okV, z[1:, :], 0.0)
            cnt[:-1, :] += okV
            acc[1:, :] += np.where(okV, z[:-1, :], 0.0)
            cnt[1:, :] += okV
            has = cnt > 0
            smooth = np.where(has, acc / np.maximum(cnt, 1.0), z)
            z = np.where(has, z * 0.72 + smooth * 0.28, z)

            # atractie spre teren
            z += (terrain - z) * 0.05

            # limitarea pantei: corectii simetrice, mediate ca sa nu oscileze
            corr = np.zeros_like(z)
            ccnt = np.zeros_like(z)
            for (ok, dist, a_slice, b_slice) in (
                    (okH, dH, (slice(None), slice(0, -1)), (slice(None), slice(1, None))),
                    (okV, dV, (slice(0, -1), slice(None)), (slice(1, None), slice(None)))):
                dz = z[b_slice] - z[a_slice]
                limit = max_grade * np.maximum(dist, 1e-3)
                excess = np.abs(dz) - limit
                over = ok & (excess > 0)
                if not over.any():
                    continue
                push = np.where(over, np.sign(dz) * excess * 0.5, 0.0)
                corr[a_slice] += push
                ccnt[a_slice] += over
                corr[b_slice] -= push
                ccnt[b_slice] += over
            moved = ccnt > 0
            z = np.where(moved, z + corr / np.maximum(ccnt, 1.0), z)

        # Nu lasam strazile sub apa.
        z = np.maximum(z, 1.6)
        self.Zh = np.where(valid, z, terrain)

        grade = self._max_grade()
        self.log(f"  cote strazi: panta maxima {grade * 100:.1f}% (limita {max_grade * 100:.1f}%), "
                 f"abatere fata de teren max {np.abs(self.Zh - terrain)[valid].max():.1f} m")

    def _max_grade(self) -> float:
        out = 0.0
        for (ok, a, b) in ((self.H, (slice(None), slice(0, -1)), (slice(None), slice(1, None))),
                           (self.V, (slice(0, -1), slice(None)), (slice(1, None), slice(None)))):
            if not ok.any():
                continue
            dist = np.linalg.norm(self.P[b] - self.P[a], axis=-1)
            dz = np.abs(self.Zh[b] - self.Zh[a])
            g = np.where(ok & (dist > 1e-3), dz / np.maximum(dist, 1e-3), 0.0)
            out = max(out, float(g.max()))
        return out

    # ------------------------------------------------------------------ topologie
    def _degree(self):
        deg = np.zeros((self.nv, self.nu), dtype=np.int32)
        deg[:, :-1] += self.H
        deg[:, 1:] += self.H
        deg[:-1, :] += self.V
        deg[1:, :] += self.V
        return deg

    def _keep_largest_component(self):
        """Fragmentele izolate de strada arata ca un bug; pastram doar reteaua principala."""
        deg = self._degree()
        label = np.where(deg > 0, -1, -2)   # -1 = de vizitat, -2 = fara strazi
        best = None
        best_size = 0
        current = 0
        for j in range(self.nv):
            for i in range(self.nu):
                if label[j, i] != -1:
                    continue
                stack = [(j, i)]
                label[j, i] = current
                size = 0
                while stack:
                    cj, ci = stack.pop()
                    size += 1
                    if ci > 0 and self.H[cj, ci - 1] and label[cj, ci - 1] == -1:
                        label[cj, ci - 1] = current
                        stack.append((cj, ci - 1))
                    if ci < self.nu - 1 and self.H[cj, ci] and label[cj, ci + 1] == -1:
                        label[cj, ci + 1] = current
                        stack.append((cj, ci + 1))
                    if cj > 0 and self.V[cj - 1, ci] and label[cj - 1, ci] == -1:
                        label[cj - 1, ci] = current
                        stack.append((cj - 1, ci))
                    if cj < self.nv - 1 and self.V[cj, ci] and label[cj + 1, ci] == -1:
                        label[cj + 1, ci] = current
                        stack.append((cj + 1, ci))
                if size > best_size:
                    best_size = size
                    best = current
                current += 1

        if best is None:
            return
        keep = label == best
        self.H &= keep[:, :-1] & keep[:, 1:]
        self.V &= keep[:-1, :] & keep[1:, :]
        self.valid &= keep

    def _prune(self):
        """
        Taie capetele moarte care nu au sens. Un cul-de-sac e credibil in suburbie,
        dar o artera care se opreste in cAmp nu e.
        """
        for _ in range(6):
            deg = self._degree()
            ends = (deg == 1) & self.valid
            if not ends.any():
                break
            zone = self.zones.at(self.P[..., 0], self.P[..., 1])
            # Un cul-de-sac e credibil doar daca e o stradela intr-un cartier rar.
            # O artera care se opreste in cAmp arata ca un drum neterminat.
            local_deg = np.zeros_like(deg)
            local_deg[:, :-1] += self.H & (self.Hk == LOCAL)
            local_deg[:, 1:] += self.H & (self.Hk == LOCAL)
            local_deg[:-1, :] += self.V & (self.Vk == LOCAL)
            local_deg[1:, :] += self.V & (self.Vk == LOCAL)
            allowed = ((zone == Z.SUBURB) | (zone == Z.INDUSTRIAL)) & (local_deg == deg)
            cut = ends & ~allowed
            if not cut.any():
                break
            # Segmentul care atinge un capat mort nepermis dispare, indiferent de rang:
            # o artera care se termina in cAmp arata mai rau decat una mai scurta.
            self.H &= ~(cut[:, :-1] | cut[:, 1:])
            self.V &= ~(cut[:-1, :] | cut[1:, :])
        deg = self._degree()
        self.valid &= deg > 0

    def _count_kinds(self) -> dict:
        out = {}
        for kinds, exists in ((self.Hk, self.H), (self.Vk, self.V)):
            for kind in (ARTERY, COLLECTOR, LOCAL):
                count = int(((kinds == kind) & exists).sum())
                if count:
                    out[kind] = out.get(kind, 0) + count
        return out

    # ------------------------------------------------------------------ iterare
    def edges(self):
        """(p0, p1, z0, z1, kind, width) pentru fiecare segment de strada existent."""
        for j in range(self.nv):
            for i in range(self.nu - 1):
                if not self.H[j, i]:
                    continue
                kind = int(self.Hk[j, i])
                yield (self.P[j, i], self.P[j, i + 1], float(self.Zh[j, i]), float(self.Zh[j, i + 1]),
                       kind, self.width_of(kind))
        for j in range(self.nv - 1):
            for i in range(self.nu):
                if not self.V[j, i]:
                    continue
                kind = int(self.Vk[j, i])
                yield (self.P[j, i], self.P[j + 1, i], float(self.Zh[j, i]), float(self.Zh[j + 1, i]),
                       kind, self.width_of(kind))

    def polylines(self):
        """Strazile grupate pe linii continue (pentru mobilier urban si mesh de asfalt)."""
        out = []
        for j in range(self.nv):
            run = []
            for i in range(self.nu - 1):
                if self.H[j, i]:
                    if not run:
                        run.append((j, i))
                    run.append((j, i + 1))
                elif run:
                    out.append((self._run_points(run), int(self.Hk[j, run[0][1]])))
                    run = []
            if run:
                out.append((self._run_points(run), int(self.Hk[j, run[0][1]])))
        for i in range(self.nu):
            run = []
            for j in range(self.nv - 1):
                if self.V[j, i]:
                    if not run:
                        run.append((j, i))
                    run.append((j + 1, i))
                elif run:
                    out.append((self._run_points(run), int(self.Vk[run[0][0], i])))
                    run = []
            if run:
                out.append((self._run_points(run), int(self.Vk[run[0][0], i])))
        return [(pts, kind) for pts, kind in out if len(pts) >= 2]

    def _run_points(self, run):
        pts = []
        for (j, i) in run:
            pts.append((float(self.P[j, i, 0]), float(self.P[j, i, 1]), float(self.Zh[j, i])))
        return np.array(pts, dtype=np.float64)

    # ------------------------------------------------------------------ teren
    def height_at(self, x, y):
        """Cota orasului in (x, y): interpolare biliniara a cotelor de nod."""
        fi, fj = self._to_lattice(x, y)
        i0 = np.clip(np.floor(fi).astype(np.int64), 0, self.nu - 2)
        j0 = np.clip(np.floor(fj).astype(np.int64), 0, self.nv - 2)
        tx = np.clip(fi - i0, 0.0, 1.0)
        ty = np.clip(fj - j0, 0.0, 1.0)
        z00 = self.Zh[j0, i0]
        z10 = self.Zh[j0, i0 + 1]
        z01 = self.Zh[j0 + 1, i0]
        z11 = self.Zh[j0 + 1, i0 + 1]
        return (z00 * (1 - tx) + z10 * tx) * (1 - ty) + (z01 * (1 - tx) + z11 * tx) * ty

    def cell_covered(self):
        """(nv-1, nu-1) bool: celula de latice are toate cele 4 noduri bune."""
        v = self.valid
        return v[:-1, :-1] & v[:-1, 1:] & v[1:, :-1] & v[1:, 1:]

    def apply_terrain(self):
        """
        Inlocuieste relieful din oras cu cAmpul de cote al laticei, cu trecere lina la margine.

        Efect secundar important: `city_mask` si `street_mask` pe grila terenului - le
        folosesc vegetatia (nu vrem copaci in mijlocul strazii) si plasatorul de cladiri.
        """
        world = self.world
        cfg = self.cfg
        n = world.n
        coords = world.coords
        gx, gy = np.meshgrid(coords, coords)

        # Acoperire: celulele de latice complet valide, transformate in masca pe teren.
        fi, fj = self._to_lattice(gx, gy)
        covered = self.cell_covered()
        ci = np.clip(np.floor(fi).astype(np.int64), 0, self.nu - 2)
        cj = np.clip(np.floor(fj).astype(np.int64), 0, self.nv - 2)
        in_range = (fi > -0.001) & (fi < self.nu - 0.999) & (fj > -0.001) & (fj < self.nv - 0.999)
        inside = covered[cj, ci] & in_range
        self.city_mask = inside

        if not inside.any():
            self.log("  oras: nicio celula valida (teren prea abrupt sau raza prea mica)")
            self.street_mask = np.zeros((n, n), dtype=bool)
            return self

        # Blend neted: masca binara netezita de cateva ori (trecere de ~20 m la margine).
        w = inside.astype(np.float64)
        for _ in range(max(2, int(round(10.0 / cfg.cell)))):
            w = (w
                 + np.roll(w, 1, 0) + np.roll(w, -1, 0)
                 + np.roll(w, 1, 1) + np.roll(w, -1, 1)) / 5.0
        w = np.clip(w, 0.0, 1.0)
        w[~inside] = np.minimum(w[~inside], 0.75)   # afara nu ridicam terenul complet

        city_z = self.height_at(gx, gy)
        self.height_field = city_z
        world.h = world.h * (1.0 - w) + city_z * w
        world._compute_slope()

        self.street_mask = self._rasterize_streets(n, coords)
        # Restul generatorului (case de sat, cAmpuri, vegetatie) citeste mastile de aici.
        world.city_mask = self.city_mask
        world.street_mask = self.street_mask
        area = float(inside.sum()) * cfg.cell * cfg.cell / 10000.0
        self.log(f"  teren oras: {area:.1f} ha nivelate, "
                 f"{float(self.street_mask.mean()) * 100:.1f}% din harta e carosabil/trotuar")
        return self

    def _rasterize_streets(self, n: int, coords):
        """Masca de carosabil + trotuar, folosita ca sa nu punem nimic pe strada."""
        cfg = self.cfg
        mask = np.zeros((n, n), dtype=bool)
        cell = cfg.cell
        pad = float(cfg.city_sidewalk)

        for p0, p1, _z0, _z1, _kind, width in self.edges():
            half = width * 0.5 + pad
            x0, y0 = float(p0[0]), float(p0[1])
            x1, y1 = float(p1[0]), float(p1[1])
            lo_x = max(0, int(math.floor((min(x0, x1) - half) / cell)))
            hi_x = min(n - 1, int(math.ceil((max(x0, x1) + half) / cell)))
            lo_y = max(0, int(math.floor((min(y0, y1) - half) / cell)))
            hi_y = min(n - 1, int(math.ceil((max(y0, y1) + half) / cell)))
            if lo_x > hi_x or lo_y > hi_y:
                continue
            xs = coords[lo_x:hi_x + 1][None, :]
            ys = coords[lo_y:hi_y + 1][:, None]
            dx = x1 - x0
            dy = y1 - y0
            length2 = dx * dx + dy * dy
            if length2 < 1e-6:
                continue
            t = np.clip(((xs - x0) * dx + (ys - y0) * dy) / length2, 0.0, 1.0)
            px = x0 + t * dx
            py = y0 + t * dy
            near = (xs - px) ** 2 + (ys - py) ** 2 <= half * half
            mask[lo_y:hi_y + 1, lo_x:hi_x + 1] |= near
        return mask
