# -*- coding: utf-8 -*-
"""
Generarea "lumii": heightmap, sate, drumuri (A*), campuri, straturi de textura, vegetatie si props.
Doar numpy (fara Blender), ca sa poata fi testat separat.
Grila: h[iy, ix], ix = x / cell, iy = y / cell; x spre est, y spre nord, z in sus.
"""
import heapq
import math
import numpy as np

from .noise import fbm, ridged, smoothstep
from . import config as C


class Placed:
    """Un obiect plasat in lume (prop vanilla sau cladire custom)."""
    __slots__ = ("name", "x", "y", "z", "yaw", "scale", "lod_dist", "kind")

    def __init__(self, name, x, y, z, yaw=0.0, scale=1.0, lod_dist=200.0, kind="prop"):
        self.name = name
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)
        self.yaw = float(yaw)
        self.scale = float(scale)
        self.lod_dist = float(lod_dist)
        self.kind = kind


class World:
    def __init__(self, cfg: C.MapConfig, building_radii: dict, log=print):
        cfg.validate()
        self.cfg = cfg
        self.log = log
        self.rng = np.random.default_rng(cfg.seed)
        self.n = int(round(cfg.size / cfg.cell)) + 1
        self.coords = np.arange(self.n, dtype=np.float64) * cfg.cell
        self.building_radii = building_radii
        self.h = None
        self.slope = None
        self.road_dist = None
        self.road_target = None
        self.field_mask = None
        self.village_dist = None
        self.building_dist = None
        self.forest = None
        self.w_g = None      # canalul verde al mastii de teren
        self.w_b = None      # canalul albastru
        self.dominant = None  # 0 grass 1 dirt 2 rock 3 sand
        # Masca orasului (dayzgen/city). Cat timp e None, nu exista oras si nimic nu se
        # schimba; cand exista, casele de sat, cAmpurile si vegetatia o ocolesc.
        self.city_mask = None
        self.street_mask = None
        self.park_mask = None
        self.city = None     # CityPlan, daca cfg.city e pornit
        self.villages = []   # dict(center=(x,y), radius, name)
        self.roads = []      # np.ndarray (M,2) esantioane la ~2 m
        self.buildings = []  # Placed (kind="building")
        self.props = []      # Placed (kind="prop")
        self.fields = []     # dict(center, size, angle)

    # ------------------------------------------------------------------ utilitare grila
    def _uv(self):
        x, y = np.meshgrid(self.coords, self.coords)
        return x / self.cfg.size, y / self.cfg.size, x, y

    def sample(self, grid: np.ndarray, x, y):
        """Interpolare biliniara pe grila la coordonatele (x, y) in metri (vectorizat)."""
        c = self.cfg.cell
        fx = np.clip(np.asarray(x, dtype=np.float64) / c, 0, self.n - 1.001)
        fy = np.clip(np.asarray(y, dtype=np.float64) / c, 0, self.n - 1.001)
        ix = np.floor(fx).astype(np.int64)
        iy = np.floor(fy).astype(np.int64)
        tx = fx - ix
        ty = fy - iy
        v00 = grid[iy, ix]
        v10 = grid[iy, ix + 1]
        v01 = grid[iy + 1, ix]
        v11 = grid[iy + 1, ix + 1]
        return (v00 * (1 - tx) + v10 * tx) * (1 - ty) + (v01 * (1 - tx) + v11 * tx) * ty

    def height(self, x, y):
        return self.sample(self.h, x, y)

    def in_city(self, x, y, margin: float = 0.0):
        """
        True unde e orasul (opional cu o margine de siguranta in metri).

        Intoarce False peste tot cAnd nu exista oras, ca restul generatorului sa nu isi
        schimbe comportamentul pe hartile fara oras.
        """
        if self.city_mask is None:
            return np.zeros_like(np.asarray(x, dtype=np.float64), dtype=bool) if np.ndim(x) else False
        hit = self.sample(self.city_mask.astype(np.float64), x, y) > 0.35
        if margin > 0.0:
            # verificam si un inel in jur, ca o casa sa nu se lipeasca de marginea orasului
            ang = np.linspace(0, 2 * np.pi, 6, endpoint=False)
            for a in ang:
                hit = hit | (self.sample(self.city_mask.astype(np.float64),
                                         np.asarray(x) + np.cos(a) * margin,
                                         np.asarray(y) + np.sin(a) * margin) > 0.35)
        return hit

    def _compute_slope(self):
        gy, gx = np.gradient(self.h, self.cfg.cell)
        self.slope = np.sqrt(gx * gx + gy * gy)
        self.grad = (gx, gy)

    def normals(self):
        gx, gy = self.grad
        nx = -gx
        ny = -gy
        nz = np.ones_like(gx)
        l = np.sqrt(nx * nx + ny * ny + nz * nz)
        return np.stack([nx / l, ny / l, nz / l], axis=-1)

    # ------------------------------------------------------------------ 1. relief
    def generate_heightmap(self):
        cfg = self.cfg
        s = cfg.seed
        u, v, x, y = self._uv()
        # domain warp -> forme organice
        wx = fbm(u * 3 + 7.1, v * 3 + 3.3, 4, seed=s + 1)
        wy = fbm(u * 3 - 2.2, v * 3 + 9.7, 4, seed=s + 2)
        uu = u + 0.12 * wx
        vv = v + 0.12 * wy
        scale = max(1.0, cfg.size / 1024.0)  # harti mai mari -> mai multe "dealuri"
        base = fbm(uu * 3.0 * scale, vv * 3.0 * scale, 7, gain=0.5, seed=s) * 0.5 + 0.5
        mount = ridged(uu * 2.2 * scale, vv * 2.2 * scale, 5, seed=s + 5)
        hills_mask = smoothstep(0.45, 0.8, fbm(u * 1.4 * scale, v * 1.4 * scale, 3, seed=s + 9) * 0.5 + 0.5)
        hgt = base * 0.62 + (mount ** 1.7) * 0.45 * hills_mask
        # insula: coborare spre margini, cu coasta neregulata
        d_edge = np.minimum(np.minimum(u, 1 - u), np.minimum(v, 1 - v)) * 2.0
        coast_noise = fbm(u * 7, v * 7, 3, seed=s + 11) * 0.10
        falloff = smoothstep(0.02, 0.30, d_edge + coast_noise)
        hgt = hgt * falloff
        # nivelul marii = 0; tarm la hgt ~ 0.14
        hm = (hgt - 0.14) * cfg.max_height
        # campie mai lina la altitudini mici (DayZ are multe zone plate)
        low = hm > 0
        hm = np.where(low, np.sign(hm) * (np.abs(hm) ** 1.12), hm)
        # fund de mare limitat
        hm = np.maximum(hm, -cfg.sea_depth + fbm(u * 20, v * 20, 2, seed=s + 12) * 1.5)
        self.h = hm
        self._compute_slope()
        land = float((hm > 0).mean())
        self.log(f"  relief: {self.n}x{self.n} vertecsi, inaltime max {hm.max():.1f} m, uscat {land*100:.0f}%")

    # ------------------------------------------------------------------ 2. sate
    def place_villages(self):
        cfg = self.cfg
        u, v, x, y = self._uv()
        d_edge = np.minimum(np.minimum(u, 1 - u), np.minimum(v, 1 - v)) * 2.0
        step = max(1, int(round(16.0 / cfg.cell)))
        for relax in range(4):
            slope_max = 0.12 + relax * 0.05
            hmin = 6.0 - relax * 1.5
            ok = ((self.slope < slope_max) & (self.h > hmin) & (self.h < cfg.max_height * 0.55)
                  & (d_edge > 0.14))
            ok[::step, ::step] &= True
            sub = np.zeros_like(ok)
            sub[::step, ::step] = ok[::step, ::step]
            iy, ix = np.nonzero(sub)
            if len(ix) >= cfg.num_villages * 3:
                break
        cand = np.stack([x[iy, ix], y[iy, ix]], axis=1)
        # scor de "platitudine" in jur (medie slope pe vecinatate) -> preferam zone plate intinse
        flat_local = np.zeros(len(cand))
        r_cells = int(60.0 / cfg.cell)
        for k in range(len(cand)):
            cy, cx = iy[k], ix[k]
            win = self.slope[max(0, cy - r_cells):cy + r_cells + 1, max(0, cx - r_cells):cx + r_cells + 1]
            flat_local[k] = float((win < 0.15).mean())
        chosen = []
        first = int(self.rng.choice(len(cand), p=(flat_local ** 3 + 1e-6) / (flat_local ** 3 + 1e-6).sum()))
        chosen.append(first)
        min_sep = cfg.size / (cfg.num_villages ** 0.5 + 1.0)
        while len(chosen) < cfg.num_villages:
            d = np.full(len(cand), np.inf)
            for ci in chosen:
                d = np.minimum(d, np.hypot(cand[:, 0] - cand[ci, 0], cand[:, 1] - cand[ci, 1]))
            score = np.minimum(d, min_sep * 1.5) * (0.4 + flat_local)
            score[chosen] = -1
            nxt = int(np.argmax(score))
            if score[nxt] <= 0:
                break
            chosen.append(nxt)
        names = ["Novaya", "Stary", "Zelenogorsk", "Kamenka", "Berezino", "Gorka", "Vybor", "Msta",
                 "Pusta", "Guglovo", "Mogilevka", "Kabanino", "Solnichniy", "Elektro", "Cherno", "Balota"]
        for i, ci in enumerate(chosen):
            r = float(self.rng.uniform(*cfg.village_radius))
            self.villages.append({"center": (float(cand[ci, 0]), float(cand[ci, 1])), "radius": r,
                                  "name": names[i % len(names)]})
        self.log(f"  sate: {len(self.villages)} -> " + ", ".join(
            f"{v['name']}({v['center'][0]:.0f},{v['center'][1]:.0f})" for v in self.villages))

    # ------------------------------------------------------------------ 3. drumuri (A* pe grila grosiera)
    def _astar(self, start, goal, hc, cc, water):
        """A* cu 8 vecini pe grila grosiera. hc = inaltimi grosiere, cc = cell grosier."""
        n = hc.shape[0]
        sy, sx = start
        gy, gx = goal
        nbrs = [(-1, 0, 1.0), (1, 0, 1.0), (0, -1, 1.0), (0, 1, 1.0),
                (-1, -1, 1.4142), (-1, 1, 1.4142), (1, -1, 1.4142), (1, 1, 1.4142)]
        g = {start: 0.0}
        came = {}
        openq = [(0.0, start)]
        closed = set()
        while openq:
            f, cur = heapq.heappop(openq)
            if cur == goal:
                break
            if cur in closed:
                continue
            closed.add(cur)
            cy, cx = cur
            hcur = hc[cy, cx]
            for dy, dx, dist in nbrs:
                ny, nx = cy + dy, cx + dx
                if ny < 0 or nx < 0 or ny >= n or nx >= n:
                    continue
                if water[ny, nx]:
                    continue
                dh = abs(hc[ny, nx] - hcur) / (dist * cc)
                cost = dist * (1.0 + 30.0 * dh * dh + 4.0 * dh)
                ng = g[cur] + cost
                nb = (ny, nx)
                if ng < g.get(nb, np.inf):
                    g[nb] = ng
                    came[nb] = cur
                    hh = math.hypot(ny - gy, nx - gx)
                    heapq.heappush(openq, (ng + hh, nb))
        if goal not in came and goal != start:
            return None
        path = [goal]
        while path[-1] != start:
            path.append(came[path[-1]])
        path.reverse()
        return path

    @staticmethod
    def _chaikin(pts: np.ndarray, iters: int = 3) -> np.ndarray:
        for _ in range(iters):
            p = pts
            q = 0.75 * p[:-1] + 0.25 * p[1:]
            r = 0.25 * p[:-1] + 0.75 * p[1:]
            pts = np.vstack([p[:1], np.stack([q, r], axis=1).reshape(-1, 2), p[-1:]])
        return pts

    @staticmethod
    def _resample(pts: np.ndarray, step: float) -> np.ndarray:
        seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
        cum = np.concatenate([[0.0], np.cumsum(seg)])
        total = cum[-1]
        if total < step:
            return pts
        t = np.arange(0.0, total, step)
        xs = np.interp(t, cum, pts[:, 0])
        ys = np.interp(t, cum, pts[:, 1])
        return np.stack([xs, ys], axis=1)

    def build_roads(self):
        cfg = self.cfg
        if len(self.villages) < 1:
            return
        factor = max(1, int(round(16.0 / cfg.cell)))
        hc = self.h[::factor, ::factor]
        cc = cfg.cell * factor
        water = hc < 1.0
        centers = [v["center"] for v in self.villages]
        # arbore de acoperire minima (Kruskal) intre sate
        edges = []
        for i in range(len(centers)):
            for j in range(i + 1, len(centers)):
                d = math.hypot(centers[i][0] - centers[j][0], centers[i][1] - centers[j][1])
                edges.append((d, i, j))
        edges.sort()
        parent = list(range(len(centers)))

        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a

        pairs = []
        for d, i, j in edges:
            if find(i) != find(j):
                parent[find(i)] = find(j)
                pairs.append((i, j))
        # un sat singur: drum scurt "prin sat" catre o directie plata, ca sa avem strada principala
        if len(centers) == 1:
            cx, cy = centers[0]
            r = self.villages[0]["radius"]
            pairs = []
            base_ang = float(self.rng.uniform(0, math.pi))
            for ang in (base_ang, base_ang + math.pi):
                # mergem pe directie pana la apa sau marginea hartii si oprim pe uscat
                ex, ey = cx, cy
                for d in np.arange(r * 1.5, cfg.size, 8.0):
                    tx, ty = cx + math.cos(ang) * d, cy + math.sin(ang) * d
                    if not (cfg.cell * 3 < tx < cfg.size - cfg.cell * 3 and cfg.cell * 3 < ty < cfg.size - cfg.cell * 3):
                        break
                    if float(self.height(tx, ty)) < 3.0:
                        break
                    ex, ey = tx, ty
                if math.hypot(ex - cx, ey - cy) < r:
                    continue
                centers.append((ex, ey))
                pairs.append((0, len(centers) - 1))
        def route(p_from, p_to, label):
            a = (int(round(p_from[1] / cc)), int(round(p_from[0] / cc)))
            b = (int(round(p_to[1] / cc)), int(round(p_to[0] / cc)))
            a = (min(max(a[0], 0), hc.shape[0] - 1), min(max(a[1], 0), hc.shape[1] - 1))
            b = (min(max(b[0], 0), hc.shape[0] - 1), min(max(b[1], 0), hc.shape[1] - 1))
            water[a] = False
            water[b] = False
            path = self._astar(a, b, hc, cc, water)
            if path is None:
                self.log(f"  drum {label}: fara traseu (apa), sar")
                return None
            pts = np.array([(px * cc, py * cc) for (py, px) in path], dtype=np.float64)
            pts[0] = p_from
            pts[-1] = p_to
            if len(pts) >= 3:
                pts = self._chaikin(pts, 3)
            pts = self._resample(pts, 2.0)
            self.roads.append(pts)
            return pts

        for i, j in pairs:
            route(centers[i], centers[j], f"{i}-{j}")
        # strazi laterale in fiecare sat (perpendiculare pe drumul principal), ca sa avem front de case
        main_roads = list(self.roads)
        for vi, vil in enumerate(self.villages):
            cx, cy = vil["center"]
            r = vil["radius"]
            main_dir = None
            for pts in main_roads:
                d = np.hypot(pts[:, 0] - cx, pts[:, 1] - cy)
                k = int(np.argmin(d))
                if d[k] < r and 0 < k < len(pts) - 1:
                    main_dir = pts[k + 1] - pts[k - 1]
                    main_dir = main_dir / (np.linalg.norm(main_dir) + 1e-9)
                    break
            if main_dir is None:
                main_dir = np.array([1.0, 0.0])
            perp = np.array([-main_dir[1], main_dir[0]])
            n_spurs = 2 if r > 85 else 1
            sides = [1.0, -1.0] if n_spurs == 2 else [1.0 if self.rng.random() < 0.5 else -1.0]
            for side in sides:
                ang_jit = float(self.rng.uniform(-0.35, 0.35))
                dvec = np.array([perp[0] * math.cos(ang_jit) - perp[1] * math.sin(ang_jit),
                                 perp[0] * math.sin(ang_jit) + perp[1] * math.cos(ang_jit)]) * side
                length = r * float(self.rng.uniform(1.0, 1.4))
                end = None
                for dd in np.arange(20.0, length, 6.0):
                    tx, ty = cx + dvec[0] * dd, cy + dvec[1] * dd
                    if not (cfg.cell * 3 < tx < cfg.size - cfg.cell * 3 and cfg.cell * 3 < ty < cfg.size - cfg.cell * 3):
                        break
                    if float(self.height(tx, ty)) < 3.0:
                        break
                    end = (tx, ty)
                if end is None or math.hypot(end[0] - cx, end[1] - cy) < 40.0:
                    continue
                route((cx, cy), end, f"sat{vi}-strada")
        self.log(f"  drumuri: {len(self.roads)} trasee, {sum(len(r) for r in self.roads)} esantioane")
        self._apply_roads()

    def _apply_roads(self):
        """Distanta pana la drum + nivelare teren de-a lungul drumului."""
        cfg = self.cfg
        n = self.n
        self.road_dist = np.full((n, n), 1e6)
        if not self.roads:
            self.road_target = self.h.copy()
            return
        all_pts = np.vstack(self.roads)
        # inaltime tinta: media mobila a terenului de-a lungul fiecarui drum
        targets = []
        for pts in self.roads:
            hz = self.height(pts[:, 0], pts[:, 1])
            k = 15
            ker = np.ones(2 * k + 1) / (2 * k + 1)
            pad = np.pad(hz, k, mode="edge")
            targets.append(np.convolve(pad, ker, mode="valid"))
        target = np.concatenate(targets)
        # scatter: pentru fiecare nod din fereastra din jurul esantionului, distanta exacta
        K = int(math.ceil(28.0 / cfg.cell))
        key = np.full((n, n), np.inf)
        sx = all_pts[:, 0] / cfg.cell
        sy = all_pts[:, 1] / cfg.cell
        bx = np.floor(sx).astype(np.int64)
        by = np.floor(sy).astype(np.int64)
        idx = np.arange(len(all_pts), dtype=np.float64)
        for dy in range(-K, K + 2):
            for dx in range(-K, K + 2):
                gx = bx + dx
                gy = by + dy
                ok = (gx >= 0) & (gx < n) & (gy >= 0) & (gy < n)
                d = np.hypot((gx - sx) * cfg.cell, (gy - sy) * cfg.cell)
                kk = np.floor(d * 100.0) * 1e7 + idx
                np.minimum.at(key, (gy[ok], gx[ok]), kk[ok])
        has = np.isfinite(key)
        key_safe = np.where(has, key, 0.0)
        dist = np.where(has, np.floor(key_safe / 1e7) / 100.0, 1e6)
        sid = np.mod(key_safe, 1e7).astype(np.int64)
        self.road_dist = dist
        tgt = target[sid]
        inner = cfg.road_half_width + 1.5
        outer = cfg.road_half_width + 16.0
        blend = smoothstep(outer, inner, dist) * has
        self.h = self.h + (tgt - self.h) * blend
        self._compute_slope()

    # ------------------------------------------------------------------ 4. cladiri in sate
    def _flatten_disc(self, cx, cy, r_in, r_out, z=None):
        cfg = self.cfg
        R = int(math.ceil(r_out / cfg.cell)) + 1
        ix = int(round(cx / cfg.cell))
        iy = int(round(cy / cfg.cell))
        x0, x1 = max(0, ix - R), min(self.n, ix + R + 1)
        y0, y1 = max(0, iy - R), min(self.n, iy + R + 1)
        xs = self.coords[x0:x1][None, :]
        ys = self.coords[y0:y1][:, None]
        d = np.hypot(xs - cx, ys - cy)
        if z is None:
            z = float(self.height(cx, cy))
        blend = smoothstep(r_out, r_in, d)
        self.h[y0:y1, x0:x1] += (z - self.h[y0:y1, x0:x1]) * blend
        return z

    def _building_spot_ok(self, px, py, rb, placed_xy):
        cfg = self.cfg
        if not (rb + 2 < px < cfg.size - rb - 2 and rb + 2 < py < cfg.size - rb - 2):
            return False
        if float(self.height(px, py)) < 2.5:
            return False
        ang = np.linspace(0, 2 * np.pi, 8, endpoint=False)
        ring_h = self.height(px + np.cos(ang) * rb, py + np.sin(ang) * rb)
        if (ring_h.max() - ring_h.min()) > rb * 0.6:
            return False
        if self.sample(self.road_dist, px, py) < cfg.road_half_width + rb + 0.5:
            return False
        if self.in_city(px, py, rb + 6.0):
            return False
        if any(math.hypot(px - qx, py - qy) < rb + qr + 3.0 for (qx, qy, qr) in placed_xy):
            return False
        return True

    def place_buildings(self):
        cfg = self.cfg
        keys = C.BUILDING_KEYS
        weights = {"house_a": 0.48, "house_b": 0.24, "shed": 0.16, "barn": 0.12}
        placed_xy = []
        for vil in self.villages:
            cx, cy = vil["center"]
            r = vil["radius"]
            want = int(self.rng.integers(cfg.houses_per_village[0], cfg.houses_per_village[1] + 1))
            got = 0
            # esantioanele de drum din interiorul satului
            segs = []
            for pts in self.roads:
                d = np.hypot(pts[:, 0] - cx, pts[:, 1] - cy)
                inside = d < r
                if inside.any():
                    segs.append(pts[inside])
            if not segs:
                segs = [np.array([[cx - r * 0.8, cy], [cx + r * 0.8, cy]])]
            side = 1.0
            for pts in segs:
                if len(pts) < 2:
                    continue
                dirs = np.gradient(pts, axis=0)
                dirs /= (np.linalg.norm(dirs, axis=1, keepdims=True) + 1e-9)
                acc = 0.0
                nxt = float(self.rng.uniform(8.0, 16.0))
                for k in range(1, len(pts)):
                    acc += float(np.linalg.norm(pts[k] - pts[k - 1]))
                    if acc < nxt or got >= want:
                        continue
                    acc = 0.0
                    nxt = float(self.rng.uniform(20.0, 30.0))
                    key = str(self.rng.choice(keys, p=[weights[k2] for k2 in keys]))
                    rb = self.building_radii[key]
                    dvec = dirs[k]
                    nvec = np.array([-dvec[1], dvec[0]]) * side
                    side = -side
                    off = cfg.road_half_width + rb + float(self.rng.uniform(3.0, 7.0))
                    px, py = pts[k] + nvec * off
                    if not self._building_spot_ok(px, py, rb, placed_xy):
                        continue
                    yaw = math.atan2(nvec[1], nvec[0]) - math.pi / 2.0
                    z = self._flatten_disc(px, py, rb + 1.5, rb + 9.0)
                    self.buildings.append(Placed(key, px, py, z - 0.05, yaw, 1.0, cfg.lod_dist_building, "building"))
                    placed_xy.append((px, py, rb))
                    got += 1
            # completare: case "in spate", orientate spre cel mai apropiat drum
            all_pts = np.vstack(segs)
            for attempt in range(60):
                if got >= want:
                    break
                key = str(self.rng.choice(keys, p=[weights[k2] for k2 in keys]))
                rb = self.building_radii[key]
                ang = float(self.rng.uniform(0, 2 * np.pi))
                dist = float(self.rng.uniform(r * 0.15, r * 0.95))
                px, py = cx + math.cos(ang) * dist, cy + math.sin(ang) * dist
                d = np.hypot(all_pts[:, 0] - px, all_pts[:, 1] - py)
                k = int(np.argmin(d))
                if d[k] < cfg.road_half_width + rb + 2.0 or d[k] > rb + 22.0:
                    continue
                if not self._building_spot_ok(px, py, rb, placed_xy):
                    continue
                to_road = all_pts[k] - np.array([px, py])
                yaw = math.atan2(-to_road[1], -to_road[0]) - math.pi / 2.0  # fata (-Y local) spre drum
                z = self._flatten_disc(px, py, rb + 1.5, rb + 9.0)
                self.buildings.append(Placed(key, px, py, z - 0.05, yaw, 1.0, cfg.lod_dist_building, "building"))
                placed_xy.append((px, py, rb))
                got += 1
            vil["num_buildings"] = got
        self._compute_slope()
        # distanta pana la cladiri (pentru excluderea vegetatiei)
        n = self.n
        self.building_dist = np.full((n, n), 1e6)
        for b in self.buildings:
            rb = self.building_radii[b.name]
            R = int(math.ceil((rb + 12.0) / cfg.cell)) + 1
            ix = int(round(b.x / cfg.cell))
            iy = int(round(b.y / cfg.cell))
            x0, x1 = max(0, ix - R), min(n, ix + R + 1)
            y0, y1 = max(0, iy - R), min(n, iy + R + 1)
            d = np.hypot(self.coords[x0:x1][None, :] - b.x, self.coords[y0:y1][:, None] - b.y) - rb
            self.building_dist[y0:y1, x0:x1] = np.minimum(self.building_dist[y0:y1, x0:x1], d)
        self.village_dist = np.full((n, n), 1e6)
        x, y = np.meshgrid(self.coords, self.coords)
        for vil in self.villages:
            cx, cy = vil["center"]
            self.village_dist = np.minimum(self.village_dist, np.hypot(x - cx, y - cy) - vil["radius"])
        self.log(f"  cladiri: {len(self.buildings)} in {len(self.villages)} sate")

    # ------------------------------------------------------------------ 5. campuri
    def place_fields(self):
        cfg = self.cfg
        n = self.n
        self.field_mask = np.zeros((n, n))
        for vil in self.villages:
            cx, cy = vil["center"]
            want = int(self.rng.integers(cfg.fields_per_village[0], cfg.fields_per_village[1] + 1))
            got = 0
            for attempt in range(40):
                if got >= want:
                    break
                ang = float(self.rng.uniform(0, 2 * np.pi))
                dist = float(self.rng.uniform(vil["radius"] + 30, vil["radius"] + 140))
                fx, fy = cx + math.cos(ang) * dist, cy + math.sin(ang) * dist
                w, l = float(self.rng.uniform(50, 85)), float(self.rng.uniform(70, 120))
                rot = float(self.rng.uniform(0, np.pi))
                if not (l < fx < cfg.size - l and l < fy < cfg.size - l):
                    continue
                # nodurile din dreptunghi
                R = int(math.ceil(max(w, l) / cfg.cell)) + 1
                ix, iy = int(round(fx / cfg.cell)), int(round(fy / cfg.cell))
                x0, x1 = max(0, ix - R), min(n, ix + R + 1)
                y0, y1 = max(0, iy - R), min(n, iy + R + 1)
                xs = self.coords[x0:x1][None, :] - fx
                ys = self.coords[y0:y1][:, None] - fy
                lx = xs * math.cos(rot) + ys * math.sin(rot)
                ly = -xs * math.sin(rot) + ys * math.cos(rot)
                inside = (np.abs(lx) < l / 2) & (np.abs(ly) < w / 2)
                if inside.sum() < 10:
                    continue
                sl = self.slope[y0:y1, x0:x1][inside]
                hh = self.h[y0:y1, x0:x1][inside]
                rd = self.road_dist[y0:y1, x0:x1][inside]
                bd = self.building_dist[y0:y1, x0:x1][inside]
                if sl.mean() > 0.13 or hh.min() < 3.0 or rd.min() < cfg.road_half_width + 4 or bd.min() < 6:
                    continue
                if any(math.hypot(fx - f["center"][0], fy - f["center"][1]) < (l + f["size"][1]) * 0.6
                       for f in self.fields):
                    continue
                # margine moale a campului
                edge = np.minimum(l / 2 - np.abs(lx), w / 2 - np.abs(ly))
                soft = smoothstep(-1.0, 6.0, edge)
                self.field_mask[y0:y1, x0:x1] = np.maximum(self.field_mask[y0:y1, x0:x1], soft)
                self.fields.append({"center": (fx, fy), "size": (w, l), "angle": rot})
                got += 1
                # baloti de fan in camp
                nb = int(self.rng.integers(4, 12))
                for _ in range(nb):
                    ux = float(self.rng.uniform(-l / 2 + 6, l / 2 - 6))
                    uy = float(self.rng.uniform(-w / 2 + 6, w / 2 - 6))
                    px = fx + ux * math.cos(rot) - uy * math.sin(rot)
                    py = fy + ux * math.sin(rot) + uy * math.cos(rot)
                    self.props.append(Placed(str(self.rng.choice(C.FARM_PROPS[:3])), px, py, 0.0,
                                             float(self.rng.uniform(0, 2 * np.pi)), 1.0,
                                             cfg.lod_dist_small_prop))
        self.log(f"  campuri: {len(self.fields)}")

    # ------------------------------------------------------------------ 6. straturi de textura
    def compute_layers(self):
        cfg = self.cfg
        u, v, x, y = self._uv()
        s = cfg.seed
        rock_noise = fbm(u * 12, v * 12, 4, seed=s + 31) * 0.5 + 0.5
        w_sand = smoothstep(3.2, 0.9, self.h) * smoothstep(0.55, 0.2, self.slope)
        w_rock = smoothstep(0.55, 0.95, self.slope)
        w_rock = np.maximum(w_rock, smoothstep(0.70, 0.95, self.h / max(cfg.max_height, 1.0))
                            * smoothstep(0.45, 0.7, rock_noise) * 0.8)
        road = smoothstep(cfg.road_half_width + 3.0, cfg.road_half_width - 0.8, self.road_dist)
        field = self.field_mask * (0.55 + 0.25 * (fbm(u * 40, v * 40, 3, seed=s + 32) * 0.5 + 0.5))
        village = smoothstep(12.0, -2.0, self.village_dist) * 0.35 * smoothstep(0.35, 0.7, fbm(u * 30, v * 30, 3, seed=s + 33) * 0.5 + 0.5)
        yard = smoothstep(6.0, 0.0, self.building_dist) * 0.7
        w_dirt = np.clip(np.maximum.reduce([road, field, village, yard]), 0, 1)
        # prioritati: nisip > stanca > pamant > iarba
        w_rock = w_rock * (1 - w_sand)
        w_dirt = w_dirt * (1 - w_sand) * (1 - w_rock)
        w_grass = np.clip(1 - w_sand - w_rock - w_dirt, 0, 1)
        self.w_g = np.clip(w_rock + w_sand, 0, 1)
        self.w_b = np.clip(w_dirt + w_sand, 0, 1)
        stack = np.stack([w_grass, w_dirt, w_rock, w_sand], axis=-1)
        self.dominant = np.argmax(stack, axis=-1).astype(np.int8)
        cover = np.bincount(self.dominant.ravel(), minlength=4) / self.dominant.size
        self.log(f"  straturi: iarba {cover[0]*100:.0f}% pamant {cover[1]*100:.0f}% "
                 f"stanca {cover[2]*100:.0f}% nisip {cover[3]*100:.0f}%")

    # ------------------------------------------------------------------ 7. vegetatie & props
    def _jitter_grid(self, spacing: float):
        cfg = self.cfg
        k = int(cfg.size / spacing)
        gx, gy = np.meshgrid(np.arange(k), np.arange(k))
        px = (gx.ravel() + self.rng.random(k * k)) * spacing
        py = (gy.ravel() + self.rng.random(k * k)) * spacing
        return px, py

    def place_vegetation(self):
        cfg = self.cfg
        s = cfg.seed
        u, v, x, y = self._uv()
        fn = fbm(u * 5 * max(1.0, cfg.size / 1024.0), v * 5 * max(1.0, cfg.size / 1024.0), 5, seed=s + 21)
        thr = float(np.quantile(fn, 1.0 - cfg.forest_coverage))
        forest = smoothstep(thr - 0.06, thr + 0.10, fn)
        # fara padure pe drum / in sat / pe camp / pe plaja / pe pante abrupte
        forest *= smoothstep(cfg.road_half_width + 2, cfg.road_half_width + 9, self.road_dist)
        forest *= np.maximum(smoothstep(-5, 20, self.village_dist), 0.15)
        forest *= (1 - smoothstep(0.1, 0.5, self.field_mask))
        forest *= smoothstep(2.0, 5.0, self.h)
        forest *= smoothstep(0.85, 0.6, self.slope)
        forest *= smoothstep(2.0, 6.0, self.building_dist)
        # Fara padure in oras - in afara de parcuri, unde copacii sunt exact ce trebuie.
        if self.city_mask is not None:
            park = self.park_mask if self.park_mask is not None else np.zeros_like(self.city_mask)
            forest = forest * np.where(self.city_mask & ~park, 0.0, 1.0)
        self.forest = forest

        def blocked(px, py, keep_village=False):
            rd = self.sample(self.road_dist, px, py)
            bd = self.sample(self.building_dist, px, py)
            hh = self.height(px, py)
            fm = self.sample(self.field_mask, px, py)
            ok = (rd > cfg.road_half_width + 1.5) & (bd > 2.5) & (hh > 0.6) & (fm < 0.5)
            if not keep_village:
                ok &= self.sample(self.village_dist, px, py) > -5
            if self.city_mask is not None:
                # In oras nu creste nimic de la sine; in parcuri, da.
                in_city = self.sample(self.city_mask.astype(np.float64), px, py) > 0.35
                in_park = (self.sample(self.park_mask.astype(np.float64), px, py) > 0.35
                           if self.park_mask is not None else False)
                on_street = (self.sample(self.street_mask.astype(np.float64), px, py) > 0.2
                             if self.street_mask is not None else False)
                ok &= ~(in_city & ~in_park) & ~on_street
            return ~ok

        rng = self.rng
        count0 = len(self.props)
        # --- padure
        px, py = self._jitter_grid(cfg.tree_spacing)
        dens = self.sample(forest, px, py)
        keep = (rng.random(len(px)) < dens * 0.9) & ~blocked(px, py)
        px, py = px[keep], py[keep]
        hh = self.height(px, py)
        highland = hh > cfg.max_height * 0.5
        r = rng.random(len(px))
        for i in range(len(px)):
            if highland[i] or r[i] < 0.68:
                name = C.TREES_CONIFER[int(rng.integers(len(C.TREES_CONIFER)))]
            elif r[i] < 0.85:
                name = C.TREES_BIRCH[int(rng.integers(len(C.TREES_BIRCH)))]
            else:
                name = C.TREES_BROADLEAF[int(rng.integers(len(C.TREES_BROADLEAF)))]
            self.props.append(Placed(name, px[i], py[i], hh[i] - 0.05, rng.uniform(0, 2 * np.pi),
                                     rng.uniform(0.85, 1.2), cfg.lod_dist_tree))
        n_forest = len(self.props) - count0
        # --- copaci singuratici
        px, py = self._jitter_grid(math.sqrt(cfg.lone_tree_area))
        keep = (self.sample(forest, px, py) < 0.15) & ~blocked(px, py, keep_village=True) & \
               (self.sample(self.slope, px, py) < 0.6)
        for i in np.nonzero(keep)[0]:
            pool = C.TREES_BROADLEAF + C.TREES_BIRCH + C.TREES_CONIFER[:2]
            self.props.append(Placed(pool[int(rng.integers(len(pool)))], px[i], py[i],
                                     float(self.height(px[i], py[i])) - 0.05,
                                     rng.uniform(0, 2 * np.pi), rng.uniform(0.9, 1.25), cfg.lod_dist_tree))
        # --- tufisuri (margini de padure + rar in camp deschis)
        px, py = self._jitter_grid(math.sqrt(cfg.bush_edge_area))
        fv = self.sample(forest, px, py)
        keep = (fv > 0.08) & (fv < 0.6) & ~blocked(px, py, keep_village=True)
        px2, py2 = self._jitter_grid(math.sqrt(cfg.bush_open_area))
        keep2 = ~blocked(px2, py2, keep_village=True)
        for (ax, ay) in ((px[keep], py[keep]), (px2[keep2], py2[keep2])):
            for i in range(len(ax)):
                self.props.append(Placed(C.BUSHES[int(rng.integers(len(C.BUSHES)))], ax[i], ay[i],
                                         float(self.height(ax[i], ay[i])) - 0.1,
                                         rng.uniform(0, 2 * np.pi), rng.uniform(0.8, 1.2), cfg.lod_dist_bush))
        # --- stanci
        px, py = self._jitter_grid(math.sqrt(cfg.rock_slope_area))
        sl = self.sample(self.slope, px, py)
        keep = (sl > 0.42) & (self.height(px, py) > 0.5) & ~blocked(px, py, keep_village=True)
        for i in np.nonzero(keep)[0]:
            self.props.append(Placed(C.ROCKS_BIG[int(rng.integers(len(C.ROCKS_BIG)))], px[i], py[i],
                                     float(self.height(px[i], py[i])) - 0.4,
                                     rng.uniform(0, 2 * np.pi), rng.uniform(0.7, 1.3), cfg.lod_dist_rock))
        px, py = self._jitter_grid(math.sqrt(cfg.rock_open_area))
        keep = ~blocked(px, py, keep_village=True) & (self.sample(self.slope, px, py) < 0.5)
        for i in np.nonzero(keep)[0]:
            self.props.append(Placed(C.ROCKS_SMALL[int(rng.integers(len(C.ROCKS_SMALL)))], px[i], py[i],
                                     float(self.height(px[i], py[i])) - 0.25,
                                     rng.uniform(0, 2 * np.pi), rng.uniform(0.7, 1.2), cfg.lod_dist_rock))
        # --- busteni / cioturi in padure
        px, py = self._jitter_grid(math.sqrt(cfg.forest_debris_area))
        keep = (self.sample(forest, px, py) > 0.5) & ~blocked(px, py)
        for i in np.nonzero(keep)[0]:
            self.props.append(Placed(C.TREES_DEBRIS[int(rng.integers(len(C.TREES_DEBRIS)))], px[i], py[i],
                                     float(self.height(px[i], py[i])) - 0.05,
                                     rng.uniform(0, 2 * np.pi), 1.0, cfg.lod_dist_small_prop))
        self.log(f"  vegetatie: {n_forest} copaci in padure, total props {len(self.props) - count0}")

    def place_village_props(self):
        cfg = self.cfg
        rng = self.rng
        count0 = len(self.props)
        for b in self.buildings:
            rb = self.building_radii[b.name]
            nyard = int(rng.integers(1, 4))
            for _ in range(nyard):
                for attempt in range(6):
                    ang = float(rng.uniform(0, 2 * np.pi))
                    d = rb + float(rng.uniform(1.5, 6.0))
                    px, py = b.x + math.cos(ang) * d, b.y + math.sin(ang) * d
                    if self.sample(self.road_dist, px, py) < cfg.road_half_width + 1.5:
                        continue
                    if self.sample(self.building_dist, px, py) < 1.0:
                        continue
                    self.props.append(Placed(C.YARD_PROPS[int(rng.integers(len(C.YARD_PROPS)))], px, py,
                                             float(self.height(px, py)), float(rng.uniform(0, 2 * np.pi)),
                                             1.0, cfg.lod_dist_small_prop))
                    break
        for vil in self.villages:
            cx, cy = vil["center"]
            r = vil["radius"]
            # reper: moara / turn de apa la marginea satului
            for attempt in range(20):
                ang = float(rng.uniform(0, 2 * np.pi))
                px, py = cx + math.cos(ang) * r * 0.9, cy + math.sin(ang) * r * 0.9
                if not (10 < px < cfg.size - 10 and 10 < py < cfg.size - 10):
                    continue
                if self.sample(self.road_dist, px, py) < cfg.road_half_width + 6:
                    continue
                if self.sample(self.building_dist, px, py) < 6:
                    continue
                if self.sample(self.slope, px, py) > 0.2 or float(self.height(px, py)) < 3:
                    continue
                z = self._flatten_disc(px, py, 5.0, 12.0)
                self.props.append(Placed(C.VILLAGE_LANDMARKS[int(rng.integers(len(C.VILLAGE_LANDMARKS)))],
                                         px, py, z, float(rng.uniform(0, 2 * np.pi)), 1.0, cfg.lod_dist_building))
                break
            # epave de masini pe marginea drumului
            if rng.random() < 0.75:
                for pts in self.roads:
                    d = np.hypot(pts[:, 0] - cx, pts[:, 1] - cy)
                    cand = np.nonzero((d < r * 1.6) & (d > r * 0.3))[0]
                    if len(cand) == 0:
                        continue
                    k = int(rng.choice(cand))
                    if 0 < k < len(pts) - 1:
                        dv = pts[k + 1] - pts[k - 1]
                        dv /= (np.linalg.norm(dv) + 1e-9)
                        nv = np.array([-dv[1], dv[0]]) * (1 if rng.random() < 0.5 else -1)
                        px, py = pts[k] + nv * (cfg.road_half_width + 1.0)
                        if self.sample(self.building_dist, px, py) > 2:
                            yaw = math.atan2(dv[1], dv[0]) + float(rng.uniform(-0.3, 0.3))
                            self.props.append(Placed(C.WRECKS[int(rng.integers(len(C.WRECKS)))], px, py,
                                                     float(self.height(px, py)), yaw, 1.0, cfg.lod_dist_rock))
                    break
        # z pentru balotii pusi inainte de nivelare
        for p in self.props:
            if p.z == 0.0:
                p.z = float(self.height(p.x, p.y))
        self._compute_slope()
        self.log(f"  props sat: {len(self.props) - count0}")

    # ------------------------------------------------------------------ pipeline
    def build_city(self):
        """
        Stratul urban (dayzgen/city), daca `cfg.city` e pornit.

        Ruleaza dupa drumuri si inainte de case/cAmpuri/vegetatie: niveleaza terenul sub
        oras si pune `city_mask` / `street_mask`, pe care restul generatorului le ocoleste.
        """
        if not getattr(self.cfg, "city", False):
            return None
        from .city.plan import CityPlan
        self.city = CityPlan(self.cfg, self, rng=self.rng, log=self.log).build()
        if self.city.plan is None:
            self.city = None
        return self.city

    def clear_city_props(self):
        """
        Plasa de siguranta: scoate orice prop natural ramas pe carosabil sau in oras.

        Fiecare rutina de plasare isi verifica singura conditiile, dar sunt multe si e usor
        sa scape una. Un singur filtru la final garanteaza ca nu creste niciun copac in
        mijlocul strazii, indiferent cine l-a pus acolo.
        """
        if self.city_mask is None or not self.props:
            return 0
        px = np.array([p.x for p in self.props], dtype=np.float64)
        py = np.array([p.y for p in self.props], dtype=np.float64)
        in_city = self.sample(self.city_mask.astype(np.float64), px, py) > 0.35
        in_park = (self.sample(self.park_mask.astype(np.float64), px, py) > 0.35
                   if self.park_mask is not None else np.zeros(len(px), dtype=bool))
        on_street = (self.sample(self.street_mask.astype(np.float64), px, py) > 0.2
                     if self.street_mask is not None else np.zeros(len(px), dtype=bool))
        drop = (in_city & ~in_park) | on_street
        if not drop.any():
            return 0
        self.props = [p for p, bad in zip(self.props, drop) if not bad]
        removed = int(drop.sum())
        self.log(f"  oras: {removed} props scoase de pe strazi / din cvartale")
        return removed

    def generate(self):
        self.log("Generez lumea...")
        self.generate_heightmap()
        self.place_villages()
        self.build_roads()
        self.build_city()
        self.place_buildings()
        self.place_fields()
        self.compute_layers()
        self.place_vegetation()
        self.place_village_props()
        self.clear_city_props()
        # re-esantionam z-urile dupa toate nivelarile
        for p in self.props:
            p.z = float(self.height(p.x, p.y)) + (p.z - float(self.height(p.x, p.y)) if False else 0.0) - (
                0.4 if p.name in C.ROCKS_BIG else 0.25 if p.name in C.ROCKS_SMALL else 0.05)
        for b in self.buildings:
            b.z = float(self.height(b.x, b.y)) - 0.05
        return self

    # ------------------------------------------------------------------ extragere tile
    def tile_count(self) -> int:
        return int(round(self.cfg.size / self.cfg.tile_size))

    def tile_grid(self, ti: int, tj: int, step: int = 1):
        """Sub-grila (inaltimi, normale, g, b, dominant) pentru tile-ul (ti = coloana x, tj = rand y)."""
        cfg = self.cfg
        T = int(round(cfg.tile_size / cfg.cell))
        x0 = ti * T
        y0 = tj * T
        sl = (slice(y0, y0 + T + 1, step), slice(x0, x0 + T + 1, step))
        nrm = self.normals()
        return {
            "h": self.h[sl],
            "n": nrm[sl],
            "g": self.w_g[sl],
            "b": self.w_b[sl],
            "dom": self.dominant[sl],
            "x": self.coords[x0:x0 + T + 1:step],
            "y": self.coords[y0:y0 + T + 1:step],
        }

    def spawn_point(self):
        """Un punct bun de spawn: centrul primului sat, pe drum."""
        if self.villages:
            cx, cy = self.villages[0]["center"]
            if self.roads:
                pts = np.vstack(self.roads)
                k = int(np.argmin(np.hypot(pts[:, 0] - cx, pts[:, 1] - cy)))
                cx, cy = float(pts[k, 0]), float(pts[k, 1])
            return cx, cy, float(self.height(cx, cy)) + 1.0
        c = self.cfg.size / 2
        return c, c, float(self.height(c, c)) + 1.0
