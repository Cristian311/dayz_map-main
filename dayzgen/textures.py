# -*- coding: utf-8 -*-
"""
Texturi procedurale tileable (grass, dirt, rock, sand + materiale pentru cladiri) si normal maps,
scrise ca DDS (DXT1 / DXT5 cu mipmap-uri) gata de folosit in GTA V.
Doar numpy - nu depinde de Blender.
"""
import os
import numpy as np

from .noise import fbm, ridged, voronoi_f1, smoothstep, _hash2
from .dds_writer import write_dds, write_png


# ----------------------------------------------------------------------------- utilitare

def _grid(size: int):
    v, u = np.mgrid[0:size, 0:size].astype(np.float64) / size
    return u, v  # u = x (coloana), v = y (rand), ambele in [0,1)


def _lerp(a, b, t):
    t = np.asarray(t)[..., None] if np.ndim(t) == 2 else t
    return a + (b - a) * t


def _col(r, g, b):
    return np.array([r, g, b], dtype=np.float64)


def _solid(size, rgb):
    return np.ones((size, size, 3)) * np.asarray(rgb)[None, None, :]


def height_to_normal(h: np.ndarray, strength: float = 2.0) -> np.ndarray:
    """
    Normal map tangent-space (conventie DirectX: verde = -Y), din inaltime [0,1], wrap-around (tileable).
    Returneaza RGB float [0,1].
    """
    dx = (np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)) * 0.5 * strength * h.shape[1] / 256.0
    dy = (np.roll(h, -1, axis=0) - np.roll(h, 1, axis=0)) * 0.5 * strength * h.shape[0] / 256.0
    nx = -dx
    ny = dy          # DirectX: +Y in textura = in jos
    nz = np.ones_like(h)
    l = np.sqrt(nx * nx + ny * ny + nz * nz)
    n = np.stack([nx / l, ny / l, nz / l], axis=2)
    return n * 0.5 + 0.5


def _blur3(a: np.ndarray, passes: int = 1) -> np.ndarray:
    for _ in range(passes):
        a = (a + np.roll(a, 1, 0) + np.roll(a, -1, 0) + np.roll(a, 1, 1) + np.roll(a, -1, 1)) / 5.0
    return a


# ----------------------------------------------------------------------------- teren

def tex_grass(size: int, seed: int):
    u, v = _grid(size)
    patches = fbm(u * 4, v * 4, 5, seed=seed + 1, period=4) * 0.5 + 0.5
    detail = fbm(u * 64, v * 64, 4, seed=seed + 2, period=64)
    fine = fbm(u * 200, v * 200, 2, seed=seed + 3, period=200)
    dry = smoothstep(0.55, 0.8, fbm(u * 6, v * 6, 4, seed=seed + 4, period=6) * 0.5 + 0.5)

    c_dark = _col(0.20, 0.29, 0.10)
    c_light = _col(0.36, 0.42, 0.15)
    c_dry = _col(0.50, 0.44, 0.22)
    col = _lerp(c_dark, c_light, patches)
    col = _lerp(col, c_dry, dry * 0.8)
    lum = 1.0 + detail * 0.22 + fine * 0.10
    col = col * lum[..., None]
    h = (detail * 0.5 + 0.5) * 0.5 + (fine * 0.5 + 0.5) * 0.5
    return np.clip(col, 0, 1), height_to_normal(h, 1.6)


def tex_dirt(size: int, seed: int):
    u, v = _grid(size)
    mottle = fbm(u * 8, v * 8, 5, seed=seed + 11, period=8) * 0.5 + 0.5
    damp = smoothstep(0.55, 0.85, fbm(u * 3, v * 3, 3, seed=seed + 12, period=3) * 0.5 + 0.5)
    fine = fbm(u * 160, v * 160, 3, seed=seed + 13, period=160)
    pebbles = voronoi_f1(u * 48, v * 48, seed=seed + 14, period=48)
    stone = smoothstep(0.30, 0.16, pebbles)  # 1 in centrul pietricelelor
    stone_mask = stone * smoothstep(0.35, 0.7, fbm(u * 12, v * 12, 3, seed=seed + 15, period=12) * 0.5 + 0.5)

    c_a = _col(0.36, 0.28, 0.18)
    c_b = _col(0.50, 0.41, 0.28)
    c_damp = _col(0.24, 0.18, 0.12)
    c_stone = _col(0.55, 0.52, 0.47)
    col = _lerp(c_a, c_b, mottle)
    col = _lerp(col, c_damp, damp * 0.7)
    col = _lerp(col, c_stone, stone_mask)
    col = col * (1.0 + fine * 0.14)[..., None]
    h = (mottle * 0.4 + (fine * 0.5 + 0.5) * 0.3 + stone_mask * 0.6)
    return np.clip(col, 0, 1), height_to_normal(h, 2.2)


def tex_rock(size: int, seed: int):
    u, v = _grid(size)
    cracks = ridged(u * 6, v * 6, 5, seed=seed + 21, period=6)
    strata = np.sin((v * 14 + fbm(u * 3, v * 3, 3, seed=seed + 22, period=3) * 0.6) * 2 * np.pi) * 0.5 + 0.5
    mottle = fbm(u * 10, v * 10, 4, seed=seed + 23, period=10) * 0.5 + 0.5
    fine = fbm(u * 120, v * 120, 3, seed=seed + 24, period=120)
    crack_lines = smoothstep(0.62, 0.9, cracks)

    c_a = _col(0.40, 0.38, 0.35)
    c_b = _col(0.56, 0.53, 0.48)
    c_brown = _col(0.45, 0.36, 0.28)
    col = _lerp(c_a, c_b, mottle)
    col = _lerp(col, c_brown, smoothstep(0.6, 0.9, fbm(u * 2, v * 2, 3, seed=seed + 25, period=2) * 0.5 + 0.5) * 0.5)
    col = col * (0.85 + strata * 0.25)[..., None]
    col = col * (1.0 - crack_lines * 0.55)[..., None]
    col = col * (1.0 + fine * 0.10)[..., None]
    h = 1.0 - crack_lines * 0.8 + strata * 0.15 + (fine * 0.5 + 0.5) * 0.15
    return np.clip(col, 0, 1), height_to_normal(h / h.max(), 3.0)


def tex_sand(size: int, seed: int):
    u, v = _grid(size)
    grain = fbm(u * 220, v * 220, 2, seed=seed + 31, period=220)
    ripples = np.sin((u * 10 + fbm(u * 4, v * 4, 3, seed=seed + 32, period=4) * 0.8) * 2 * np.pi) * 0.5 + 0.5
    mottle = fbm(u * 5, v * 5, 4, seed=seed + 33, period=5) * 0.5 + 0.5
    c_a = _col(0.70, 0.63, 0.46)
    c_b = _col(0.80, 0.74, 0.56)
    col = _lerp(c_a, c_b, mottle)
    col = col * (0.94 + ripples * 0.10 + grain * 0.06)[..., None]
    h = ripples * 0.6 + (grain * 0.5 + 0.5) * 0.4
    return np.clip(col, 0, 1), height_to_normal(h, 1.2)


# ----------------------------------------------------------------------------- cladiri

def tex_plaster(size: int, seed: int):
    u, v = _grid(size)
    stains = fbm(u * 3, v * 3, 5, seed=seed + 41, period=3) * 0.5 + 0.5
    streaks = fbm(u * 24, v * 2, 4, seed=seed + 42, period=24) * 0.5 + 0.5
    fine = fbm(u * 140, v * 140, 3, seed=seed + 43, period=140)
    cracks = smoothstep(0.75, 0.95, ridged(u * 5, v * 5, 4, seed=seed + 44, period=5))
    # randul 0 al imaginii = partea de sus in fisier -> baza peretelui (uv v=0) cade pe v_grid ~ 1
    damp = smoothstep(0.45, 0.97, v) * 0.8
    c_base = _col(0.80, 0.76, 0.66)
    c_dirty = _col(0.55, 0.52, 0.44)
    col = _lerp(c_base, c_dirty, np.clip(stains * 0.5 + damp * 0.5 + streaks * 0.2, 0, 1))
    col = col * (1.0 + fine * 0.08)[..., None]
    col = col * (1.0 - cracks * 0.5)[..., None]
    h = 0.5 + fine * 0.3 - cracks * 0.6
    return np.clip(col, 0, 1), height_to_normal(h - h.min(), 1.5)


def _plank_ids(coord: np.ndarray, n: int):
    return np.floor(coord * n).astype(np.int64)


def tex_wood(size: int, seed: int):
    u, v = _grid(size)
    n_planks = 8
    pid = _plank_ids(u, n_planks)
    pv = np.floor(v * 2).astype(np.int64)  # scanduri de 1/2 din inaltime
    hsh = _hash2(pid, pv, seed + 51)
    plank_shade = ((hsh & np.uint32(0xFF)).astype(np.float64) / 255.0) * 0.35 + 0.65
    grain = fbm(u * 6 + pid * 3.7, v * 90, 4, seed=seed + 52, period=None) * 0.5 + 0.5
    grain = np.sin(grain * 8 + u * 3) * 0.5 + 0.5
    edge_u = np.abs((u * n_planks) % 1.0 - 0.5) * 2  # 1 la margine
    edge_v = np.abs((v * 2) % 1.0 - 0.5) * 2
    gap = np.maximum(smoothstep(0.93, 1.0, edge_u), smoothstep(0.97, 1.0, edge_v))
    c_a = _col(0.42, 0.30, 0.18)
    c_b = _col(0.60, 0.46, 0.30)
    col = _lerp(c_a, c_b, grain * 0.7)
    col = col * plank_shade[..., None]
    col = col * (1.0 - gap * 0.7)[..., None]
    h = 0.7 + grain * 0.15 - gap * 0.7 + plank_shade * 0.1
    return np.clip(col, 0, 1), height_to_normal(h - h.min(), 2.0)


def tex_brick(size: int, seed: int):
    u, v = _grid(size)
    rows = 12
    cols = 6
    row = np.floor(v * rows).astype(np.int64)
    off = (row % 2) * 0.5
    bu = (u * cols + off)
    colid = np.floor(bu).astype(np.int64)
    fu = bu % 1.0
    fv = (v * rows) % 1.0
    mortar_w = 0.10
    mortar = np.maximum(smoothstep(1.0 - mortar_w, 1.0, fu) + smoothstep(mortar_w, 0.0, fu),
                        smoothstep(1.0 - mortar_w * 1.6, 1.0, fv) + smoothstep(mortar_w * 1.6, 0.0, fv))
    mortar = np.clip(mortar, 0, 1)
    hsh = _hash2(colid, row, seed + 61)
    shade = ((hsh & np.uint32(0xFF)).astype(np.float64) / 255.0)
    fine = fbm(u * 120, v * 120, 3, seed=seed + 62, period=120)
    c_a = _col(0.55, 0.27, 0.20)
    c_b = _col(0.70, 0.42, 0.30)
    c_m = _col(0.66, 0.63, 0.58)
    col = _lerp(c_a, c_b, shade)
    col = col * (1.0 + fine * 0.10)[..., None]
    col = _lerp(col, c_m, mortar)
    h = 1.0 - mortar * 0.8 + fine * 0.08
    return np.clip(col, 0, 1), height_to_normal(h - h.min(), 2.5)


def tex_rooftile(size: int, seed: int):
    u, v = _grid(size)
    rows = 10
    cols = 6
    row = np.floor(v * rows).astype(np.int64)
    off = (row % 2) * 0.5
    tu = (u * cols + off) % 1.0
    tv = (v * rows) % 1.0
    curve = np.cos((tu - 0.5) * np.pi)          # profil rotunjit pe latime
    lip = smoothstep(0.0, 0.18, tv)              # umbra sub randul de sus
    colid = np.floor(u * cols + off).astype(np.int64)
    hsh = _hash2(colid, row, seed + 71)
    shade = ((hsh & np.uint32(0xFF)).astype(np.float64) / 255.0)
    moss = smoothstep(0.6, 0.9, fbm(u * 5, v * 5, 4, seed=seed + 72, period=5) * 0.5 + 0.5)
    fine = fbm(u * 100, v * 100, 3, seed=seed + 73, period=100)
    c_a = _col(0.50, 0.26, 0.18)
    c_b = _col(0.66, 0.38, 0.26)
    c_moss = _col(0.35, 0.40, 0.20)
    col = _lerp(c_a, c_b, shade)
    col = _lerp(col, c_moss, moss * 0.6)
    col = col * (0.75 + curve * 0.3)[..., None] * (0.6 + lip * 0.4)[..., None] * (1.0 + fine * 0.08)[..., None]
    h = curve * 0.5 + lip * 0.5
    return np.clip(col, 0, 1), height_to_normal(h, 2.5)


def tex_metal(size: int, seed: int):
    u, v = _grid(size)
    ridges = np.sin(u * 2 * np.pi * 16) * 0.5 + 0.5
    rust = smoothstep(0.55, 0.85, fbm(u * 4, v * 4, 5, seed=seed + 81, period=4) * 0.5 + 0.5)
    streak = fbm(u * 30, v * 1.5, 3, seed=seed + 82, period=30) * 0.5 + 0.5
    fine = fbm(u * 150, v * 150, 2, seed=seed + 83, period=150)
    c_a = _col(0.52, 0.54, 0.56)
    c_rust = _col(0.45, 0.24, 0.14)
    col = _lerp(c_a, c_rust, np.clip(rust + streak * 0.25 * rust, 0, 1))
    col = col * (0.8 + ridges * 0.3)[..., None] * (1.0 + fine * 0.06)[..., None]
    h = ridges * 0.8 + rust * 0.1
    return np.clip(col, 0, 1), height_to_normal(h, 2.0)


def tex_window(size: int, seed: int):
    u, v = _grid(size)
    frame = 0.08
    is_frame = (u < frame) | (u > 1 - frame) | (v < frame) | (v > 1 - frame)
    bar = (np.abs(u - 0.5) < 0.025) | (np.abs(v - 0.5) < 0.025)
    glass_grad = (1.0 - v) * 0.5 + u * 0.2
    fine = fbm(u * 40, v * 40, 3, seed=seed + 91, period=40)
    c_glass = _col(0.15, 0.20, 0.25)
    c_hi = _col(0.45, 0.52, 0.60)
    col = _lerp(c_glass, c_hi, glass_grad * 0.7 + fine * 0.1)
    c_frame = _col(0.30, 0.22, 0.15)
    col = np.where((is_frame | bar)[..., None], c_frame[None, None, :], col)
    h = np.where(is_frame | bar, 1.0, 0.3)
    return np.clip(col, 0, 1), height_to_normal(_blur3(h), 2.0)


def tex_door(size: int, seed: int):
    u, v = _grid(size)
    n_planks = 5
    pid = _plank_ids(u, n_planks)
    hsh = _hash2(pid, np.zeros_like(pid), seed + 101)
    shade = ((hsh & np.uint32(0xFF)).astype(np.float64) / 255.0) * 0.3 + 0.7
    grain = fbm(u * 5 + pid * 2.1, v * 60, 4, seed=seed + 102) * 0.5 + 0.5
    edge_u = np.abs((u * n_planks) % 1.0 - 0.5) * 2
    gap = smoothstep(0.92, 1.0, edge_u)
    frame = 0.07
    is_frame = (u < frame) | (u > 1 - frame) | (v < frame)  # v mic = partea de sus a usii
    cross = (np.abs(v - 0.30) < 0.03) | (np.abs(v - 0.72) < 0.03)
    c_a = _col(0.30, 0.20, 0.12)
    c_b = _col(0.45, 0.32, 0.20)
    col = _lerp(c_a, c_b, grain * 0.6) * shade[..., None] * (1.0 - gap * 0.6)[..., None]
    col = np.where((is_frame | cross)[..., None], _col(0.22, 0.15, 0.10)[None, None, :], col)
    handle = ((u - 0.85) ** 2 + (v - 0.48) ** 2) < 0.0006
    col = np.where(handle[..., None], _col(0.6, 0.6, 0.55)[None, None, :], col)
    h = 0.6 + grain * 0.1 - gap * 0.6 + np.where(is_frame | cross, 0.4, 0.0)
    return np.clip(col, 0, 1), height_to_normal(h - h.min(), 2.0)


# ----------------------------------------------------------------------------- set complet

TERRAIN_TEXTURES = {
    "grass": tex_grass,
    "dirt": tex_dirt,
    "rock": tex_rock,
    "sand": tex_sand,
}

BUILDING_TEXTURES = {
    "plaster": tex_plaster,
    "wood": tex_wood,
    "brick": tex_brick,
    "rooftile": tex_rooftile,
    "metal": tex_metal,
    "window": tex_window,
    "door": tex_door,
}


def generate_texture_set(out_dir: str, prefix: str, seed: int, terrain_size: int, building_size: int,
                         write_png_preview: bool = True, log=print) -> dict:
    """
    Genereaza toate texturile ca DDS in out_dir. Returneaza {cheie: {"diffuse": path, "normal": path,
    "name": nume_textura, "name_n": nume_normal}}.
    """
    os.makedirs(out_dir, exist_ok=True)
    result = {}
    jobs = [(k, f, terrain_size) for k, f in TERRAIN_TEXTURES.items()]
    jobs += [(k, f, building_size) for k, f in BUILDING_TEXTURES.items()]
    for key, fn, size in jobs:
        name = f"{prefix}_{key}"
        name_n = f"{prefix}_{key}_n"
        diff_path = os.path.join(out_dir, name + ".dds")
        norm_path = os.path.join(out_dir, name_n + ".dds")
        if os.path.exists(diff_path) and os.path.exists(norm_path):
            log(f"  textura {name}: exista deja, sar peste")
        else:
            col, nrm = fn(size, seed)
            write_dds(diff_path, col, "DXT1")
            write_dds(norm_path, nrm, "DXT5")
            if write_png_preview:
                write_png(os.path.join(out_dir, name + ".png"), col)
            log(f"  textura {name}: {size}x{size} OK")
        result[key] = {"diffuse": diff_path, "normal": norm_path, "name": name, "name_n": name_n,
                       "size": size}
    return result
