# -*- coding: utf-8 -*-
"""Imagine de previzualizare a hartii (stil harta DayZ): relief umbrit, straturi, drumuri, sate, copaci."""
import numpy as np

from .dds_writer import write_png
from . import config as C

LAYER_COLORS = np.array([
    [0.36, 0.48, 0.20],   # iarba
    [0.55, 0.42, 0.26],   # pamant
    [0.55, 0.53, 0.50],   # stanca
    [0.80, 0.74, 0.55],   # nisip
])


def _line(img, x0, y0, x1, y1, color, width=1):
    """Linie in pixeli (Bresenham grosier prin eSantionare), cu grosime in pixeli."""
    h, w = img.shape[:2]
    steps = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
    t = np.linspace(0.0, 1.0, max(2, steps * 2))
    xs = np.rint(x0 + (x1 - x0) * t).astype(np.int64)
    ys = np.rint(y0 + (y1 - y0) * t).astype(np.int64)
    r = max(0, int(width) // 2)
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            px = np.clip(xs + dx, 0, w - 1)
            py = np.clip(ys + dy, 0, h - 1)
            img[py, px] = color


BUILDING_COLORS = {
    "tower": (0.20, 0.28, 0.55), "midrise": (0.30, 0.42, 0.72), "lowrise": (0.55, 0.45, 0.72),
    "shop": (0.90, 0.55, 0.20), "house": (0.75, 0.30, 0.25), "warehouse": (0.55, 0.55, 0.58),
    "garage": (0.45, 0.40, 0.35), "filler": (0.70, 0.70, 0.70),
}


def _fill_quad(img, pts, color):
    """Umple un patrulater convex (colturi in pixeli)."""
    h, w = img.shape[:2]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    x0, x1 = max(0, int(min(xs))), min(w - 1, int(max(xs)) + 1)
    y0, y1 = max(0, int(min(ys))), min(h - 1, int(max(ys)) + 1)
    if x1 < x0 or y1 < y0:
        return
    gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
    crosses = []
    for i in range(len(pts)):
        ax, ay = pts[i]
        bx, by = pts[(i + 1) % len(pts)]
        crosses.append((bx - ax) * (gy - ay) - (by - ay) * (gx - ax))
    c = np.stack(crosses)
    inside = np.all(c >= 0, axis=0) | np.all(c <= 0, axis=0)
    img[y0:y1 + 1, x0:x1 + 1][inside] = np.array(color)


def draw_city(img, city, cfg, size: int):
    """Zone colorate, strazi pe rang si conturul loturilor, peste imaginea de relief."""
    if city is None or getattr(city, "plan", None) is None:
        return img
    from .city import roads as CR
    from .city import zoning as CZ

    s = size / cfg.size

    def to_px(x, y):
        return x * s, (cfg.size - y) * s

    # 1. zonele, ca o tenta peste relief (se vede in continuare umbrirea dedesubt)
    zones = city.zones
    px = np.linspace(0, cfg.size - 1e-3, size)
    py = np.linspace(cfg.size - 1e-3, 0, size)
    X, Y = np.meshgrid(px, py)
    zid = zones.at(X, Y)
    for zone, rgb in CZ.ZONE_COLORS.items():
        if zone == CZ.NONE:
            continue
        sel = zid == zone
        if not sel.any():
            continue
        tint = np.array(rgb, dtype=np.float64) / 255.0
        img[sel] = img[sel] * 0.45 + tint * 0.55

    # 2. loturile: contur subtire, ca sa se vada densitatea
    for lot in city.plan.lots:
        if lot.poly is None:
            continue
        color = np.array([0.95, 0.95, 0.92]) if lot.kind == "lot" else np.array([0.55, 0.62, 0.50])
        for k in range(4):
            a = lot.poly[k]
            b = lot.poly[(k + 1) % 4]
            ax, ay = to_px(a[0], a[1])
            bx, by = to_px(b[0], b[1])
            _line(img, ax, ay, bx, by, color, 1)

    # cladirile plasate: amprenta plina, colorata pe categorie
    for building in getattr(city, "buildings", None) or ():
        box = getattr(building, "footprint", None)
        if box:
            _fill_quad(img, [to_px(x, y) for x, y in box], BUILDING_COLORS.get(building.category, (0.8, 0.8, 0.8)))

    # 3. strazile, cu grosimea proportionala cu rangul
    widths = {CR.ARTERY: cfg.city_width_artery, CR.COLLECTOR: cfg.city_width_collector,
              CR.LOCAL: cfg.city_width_local}
    colors = {CR.ARTERY: np.array([0.16, 0.16, 0.18]),
              CR.COLLECTOR: np.array([0.24, 0.24, 0.26]),
              CR.LOCAL: np.array([0.33, 0.33, 0.34])}
    for p0, p1, _z0, _z1, kind, _w in city.grid.edges():
        ax, ay = to_px(p0[0], p0[1])
        bx, by = to_px(p1[0], p1[1])
        _line(img, ax, ay, bx, by, colors[kind], max(1, int(round(widths[kind] * s))))

    return img


def render_map_preview(world, path: str, size: int = 1024, city=None):
    cfg = world.cfg
    n = world.n
    # esantionare pe o grila de `size` pixeli (rand 0 = nord, ca pe o harta)
    px = np.linspace(0, cfg.size - 1e-3, size)
    py = np.linspace(cfg.size - 1e-3, 0, size)
    X, Y = np.meshgrid(px, py)
    h = world.sample(world.h, X, Y)
    nrm = world.normals()
    nx = world.sample(nrm[..., 0], X, Y)
    ny = world.sample(nrm[..., 1], X, Y)
    nz = world.sample(nrm[..., 2], X, Y)
    dom = world.sample(world.dominant.astype(np.float64), X, Y)
    dom_i = np.clip(np.rint(dom), 0, 3).astype(np.int64)
    forest = world.sample(world.forest, X, Y) if world.forest is not None else np.zeros_like(h)
    road = world.sample(world.road_dist, X, Y)
    field = world.sample(world.field_mask, X, Y)

    col = LAYER_COLORS[dom_i]
    col = np.where(field[..., None] > 0.3, col * 0.5 + np.array([0.62, 0.52, 0.30]) * 0.5, col)
    # padure: verde inchis
    col = col * (1 - forest[..., None] * 0.55) + np.array([0.10, 0.30, 0.12]) * forest[..., None] * 0.55
    # umbrire (soare din NV)
    light = np.array([-0.5, 0.5, 0.7])
    light /= np.linalg.norm(light)
    shade = np.clip(nx * light[0] + ny * light[1] + nz * light[2], 0, 1)
    col = col * (0.45 + 0.65 * shade)[..., None]
    # curbe de nivel la 10 m
    contour = (np.abs(((h + 5.0) % 10.0) - 5.0) < 0.15) & (h > 0)
    col = np.where(contour[..., None], col * 0.75, col)
    # drumuri
    col = np.where((road < cfg.road_half_width + 0.5)[..., None], np.array([0.42, 0.33, 0.22]), col)
    # apa
    water = h < 0
    depth = np.clip(-h / cfg.sea_depth, 0, 1)
    wcol = np.array([0.30, 0.50, 0.70]) * (1 - depth[..., None]) + np.array([0.12, 0.25, 0.45]) * depth[..., None]
    col = np.where(water[..., None], wcol, col)
    img = np.clip(col, 0, 1)

    # orasul se deseneaza peste relief, inainte de cladirile de sat
    if city is None:
        city = getattr(world, "city", None)
    if city is not None:
        img = draw_city(img, city, cfg, size)

    # cladiri (patrate rosii) si repere
    s = size / cfg.size
    def stamp(x, y, r, color):
        cx = int(x * s)
        cy = int((cfg.size - y) * s)
        x0, x1 = max(0, cx - r), min(size, cx + r + 1)
        y0, y1 = max(0, cy - r), min(size, cy + r + 1)
        if x1 > x0 and y1 > y0:
            img[y0:y1, x0:x1] = color
    for b in world.buildings:
        stamp(b.x, b.y, max(1, int(3 * s * 2)), np.array([0.85, 0.15, 0.10]))
    for p in world.props:
        if p.name in C.VILLAGE_LANDMARKS:
            stamp(p.x, p.y, max(1, int(2 * s * 2)), np.array([0.95, 0.85, 0.10]))
    write_png(path, img)
    return img
