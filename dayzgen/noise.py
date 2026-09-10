# -*- coding: utf-8 -*-
"""
Zgomot procedural 2D vectorizat (numpy): Perlin, fBm, ridged, tileable.
Nu depinde de Blender -> se poate testa cu python simplu.
"""
import numpy as np


def _hash2(ix: np.ndarray, iy: np.ndarray, seed: int) -> np.ndarray:
    """Hash intreg determinist -> uint32 pentru fiecare nod al retelei."""
    seed_term = np.uint32((int(seed) * 2246822519) & 0xFFFFFFFF)
    with np.errstate(over="ignore"):
        h = (ix.astype(np.uint32) * np.uint32(374761393)
             + iy.astype(np.uint32) * np.uint32(668265263)
             + seed_term)
    h = (h ^ (h >> np.uint32(13))) * np.uint32(1274126177)
    h = h ^ (h >> np.uint32(16))
    return h


_GRAD_X = np.array([1.0, -1.0, 0.0, 0.0, 0.7071, -0.7071, 0.7071, -0.7071])
_GRAD_Y = np.array([0.0, 0.0, 1.0, -1.0, 0.7071, 0.7071, -0.7071, -0.7071])


def _grad(h: np.ndarray, dx: np.ndarray, dy: np.ndarray) -> np.ndarray:
    """Produs scalar cu un gradient pseudo-aleator (8 directii)."""
    g = (h & np.uint32(7)).astype(np.intp)
    return _GRAD_X[g] * dx + _GRAD_Y[g] * dy


def perlin(x: np.ndarray, y: np.ndarray, seed: int = 0, period: int | None = None) -> np.ndarray:
    """
    Perlin 2D in intervalul aproximativ [-1, 1].
    x, y: coordonate (float) in "celule" de retea.
    period: daca e setat, zgomotul este periodic (tileable) cu perioada data (in celule).
    """
    x0 = np.floor(x)
    y0 = np.floor(y)
    fx = x - x0
    fy = y - y0
    ix = x0.astype(np.int64)
    iy = y0.astype(np.int64)
    ix1 = ix + 1
    iy1 = iy + 1
    if period is not None:
        ix = np.mod(ix, period)
        iy = np.mod(iy, period)
        ix1 = np.mod(ix1, period)
        iy1 = np.mod(iy1, period)

    n00 = _grad(_hash2(ix, iy, seed), fx, fy)
    n10 = _grad(_hash2(ix1, iy, seed), fx - 1.0, fy)
    n01 = _grad(_hash2(ix, iy1, seed), fx, fy - 1.0)
    n11 = _grad(_hash2(ix1, iy1, seed), fx - 1.0, fy - 1.0)

    # fade quintic
    u = fx * fx * fx * (fx * (fx * 6.0 - 15.0) + 10.0)
    v = fy * fy * fy * (fy * (fy * 6.0 - 15.0) + 10.0)

    nx0 = n00 + u * (n10 - n00)
    nx1 = n01 + u * (n11 - n01)
    return (nx0 + v * (nx1 - nx0)) * 1.4142  # normalizare aproximativa la [-1,1]


def fbm(x: np.ndarray, y: np.ndarray, octaves: int = 6, lacunarity: float = 2.0,
        gain: float = 0.5, seed: int = 0, period: int | None = None) -> np.ndarray:
    """Fractal Brownian Motion, rezultat aproximativ in [-1, 1]."""
    total = np.zeros_like(x, dtype=np.float64)
    amp = 1.0
    norm = 0.0
    freq = 1.0
    p = period
    for i in range(octaves):
        total += amp * perlin(x * freq, y * freq, seed + i * 101, p)
        norm += amp
        amp *= gain
        freq *= lacunarity
        if p is not None:
            p = int(p * lacunarity)
    return total / norm


def ridged(x: np.ndarray, y: np.ndarray, octaves: int = 5, lacunarity: float = 2.0,
           gain: float = 0.5, seed: int = 0, period: int | None = None) -> np.ndarray:
    """Ridged multifractal (creste de munte), rezultat in [0, 1]."""
    total = np.zeros_like(x, dtype=np.float64)
    amp = 1.0
    norm = 0.0
    freq = 1.0
    weight = 1.0
    p = period
    for i in range(octaves):
        n = perlin(x * freq, y * freq, seed + i * 131, p)
        n = 1.0 - np.abs(n)
        n = n * n * weight
        weight = np.clip(n * 2.0, 0.0, 1.0)
        total += n * amp
        norm += amp
        amp *= gain
        freq *= lacunarity
        if p is not None:
            p = int(p * lacunarity)
    return np.clip(total / norm, 0.0, 1.0)


def smoothstep(e0: float, e1: float, x: np.ndarray) -> np.ndarray:
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def remap01(a: np.ndarray) -> np.ndarray:
    mn = float(a.min())
    mx = float(a.max())
    if mx - mn < 1e-9:
        return np.zeros_like(a)
    return (a - mn) / (mx - mn)


def voronoi_f1(x: np.ndarray, y: np.ndarray, seed: int = 0, period: int | None = None) -> np.ndarray:
    """Distanta pana la cel mai apropiat punct Worley (pentru pietre/celule). Rezultat ~[0, 1]."""
    x0 = np.floor(x).astype(np.int64)
    y0 = np.floor(y).astype(np.int64)
    fx = x - np.floor(x)
    fy = y - np.floor(y)
    best = np.full(x.shape, 9.0)
    for oy in (-1, 0, 1):
        for ox in (-1, 0, 1):
            cx = x0 + ox
            cy = y0 + oy
            if period is not None:
                cx = np.mod(cx, period)
                cy = np.mod(cy, period)
            h = _hash2(cx, cy, seed)
            px = ((h & np.uint32(0xFFFF)).astype(np.float64) / 65535.0)
            py = (((h >> np.uint32(16)) & np.uint32(0xFFFF)).astype(np.float64) / 65535.0)
            dx = ox + px - fx
            dy = oy + py - fy
            d = dx * dx + dy * dy
            best = np.minimum(best, d)
    return np.clip(np.sqrt(best), 0.0, 1.0)
