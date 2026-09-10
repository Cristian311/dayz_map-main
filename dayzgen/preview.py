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


def render_map_preview(world, path: str, size: int = 1024):
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
    return path
