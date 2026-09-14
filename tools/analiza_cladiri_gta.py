# -*- coding: utf-8 -*-
"""
Analizeaza cladirile GTA intregi din biblioteca (output/gta_asset_library/_assets.*.blend, cele marcate "solid" in
dayzgen/data/catalog.json): ce perete, ce geamuri, ce ornamente si ce acoperis folosesc impreuna, cat de mari sunt
geamurile si cum e pusa textura pe ele (o fereastra pe toata textura, o bucata dintr-un atlas sau o banda care se
repeta), la ce distanta sunt ferestrele (traveea) si cat de inalt e un etaj.

Rezultatul, output/analiza_cladiri_gta.json, il citeste blender_gen_buildings.py (geamuri GTA potrivite peretelui).

Rulare:  tools\\_blender.bat -b -P tools\\analiza_cladiri_gta.py [-- --limit 5]
"""
import collections
import json
import math
import re
import sys
import time
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / "output" / "gta_asset_library"
CATALOG = ROOT / "dayzgen" / "data" / "catalog.json"
OUT = ROOT / "output" / "analiza_cladiri_gta.json"

WIN_RE = re.compile(r"win|glass|glazing|curtain|shopfront|storefront")
ROOF_RE = re.compile(r"roof|felt|slate|shingle|gravel")
DOOR_RE = re.compile(r"door|shutter|garage")
# decaluri, firme, vegetatie, bucati mici: nu spun nimic despre peretele cladirii
SKIP_RE = re.compile(r"sign|billboard|decal|grime|dirt|drip|graffiti|logo|poster|leak|stain|shadow|ivy|foliage|"
                     r"_lod|vent|pipe|cable|wire|light|lamp|neon|metal_bits|detail|ao_|_ao")


def arg(name, default=None):
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return argv[argv.index(name) + 1] if name in argv and argv.index(name) + 1 < len(argv) else default


def tex_of(mat):
    """(textura difuza fara .dds, shader .sps)"""
    if mat is None or mat.node_tree is None:
        return None, ""
    shader = getattr(getattr(mat, "shader_properties", None), "filename", "") or ""
    node = mat.node_tree.nodes.get("DiffuseSampler")
    img = node.image if node is not None and node.type == "TEX_IMAGE" else None
    if img is None:
        return None, shader
    return Path(img.filepath or img.name).stem.split(".dds")[0], shader


def mesh_arrays(me):
    try:
        me.calc_loop_triangles()
    except Exception:
        pass
    nt = len(me.loop_triangles)
    co = np.empty(len(me.vertices) * 3, np.float64)
    me.vertices.foreach_get("co", co)
    tv = np.empty(nt * 3, np.int64)
    me.loop_triangles.foreach_get("vertices", tv)
    tl = np.empty(nt * 3, np.int64)
    me.loop_triangles.foreach_get("loops", tl)
    tm = np.empty(nt, np.int64)
    me.loop_triangles.foreach_get("material_index", tm)
    uv = np.zeros(len(me.loops) * 2, np.float64)
    if me.uv_layers:
        me.uv_layers[0].data.foreach_get("uv", uv)
    return co.reshape(-1, 3), tv.reshape(-1, 3), tl.reshape(-1, 3), tm, uv.reshape(-1, 2)


def islands(tris):
    """Grupuri de triunghiuri legate prin varfuri comune (tris: [[v0, v1, v2]] cu indicii lor in lista data)."""
    parent = {}

    def find(a):
        while parent.setdefault(a, a) != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for t in tris:
        ra = find(int(t[0]))
        for v in t[1:]:
            rb = find(int(v))
            if rb != ra:
                parent[rb] = ra
    groups = collections.defaultdict(list)
    for i, t in enumerate(tris):
        groups[find(int(t[0]))].append(i)
    return list(groups.values())


def analyze(obj, info, src):
    """src = fisierul .blend al bibliotecii: materialul se poate aduce de acolo, cu texturile impachetate in el."""
    me = obj.data
    co, tv, tl, tm, uv = mesh_arrays(me)
    if not len(tv):
        return None
    p0, p1, p2 = co[tv[:, 0]], co[tv[:, 1]], co[tv[:, 2]]
    cr = np.cross(p1 - p0, p2 - p0)
    ln = np.linalg.norm(cr, axis=1)
    area = ln / 2
    nrm = cr / np.maximum(ln, 1e-12)[:, None]
    u0, u1, u2 = uv[tl[:, 0]], uv[tl[:, 1]], uv[tl[:, 2]]
    uva = np.abs((u1[:, 0] - u0[:, 0]) * (u2[:, 1] - u0[:, 1]) - (u2[:, 0] - u0[:, 0]) * (u1[:, 1] - u0[:, 1])) / 2
    vert = np.abs(nrm[:, 2]) < 0.3
    up = nrm[:, 2] > 0.7
    zmin = float(co[:, 2].min())
    mats = []
    for mi, mat in enumerate(me.materials):
        tex, shader = tex_of(mat)
        sel = tm == mi
        if tex is None or not sel.any():
            continue
        a_v, a_u = float(area[sel & vert].sum()), float(area[sel & up].sum())
        ok = sel & vert & (area > 0.05) & (uva > 1e-9)
        rep = float(np.median(1.0 / np.sqrt(uva[ok] / area[ok]))) if ok.sum() >= 2 else 0.0
        low = tex.lower()
        role = ("geam" if WIN_RE.search(low) or "glass" in shader or "window" in shader else
                "usa" if DOOR_RE.search(low) else "skip" if SKIP_RE.search(low) else
                "acoperis" if a_u > a_v and (ROOF_RE.search(low) or a_u > 20) else "perete")
        mats.append({"i": mi, "tex": tex, "shader": shader, "role": role, "av": a_v, "au": a_u, "rep": rep,
                     "src": [src, mat.name]})
    # geamurile: fiecare grup de triunghiuri legate, vertical, e o fereastra (sau o banda de ferestre)
    wins = []
    for m in mats:
        if m["role"] != "geam":
            continue
        idx = np.nonzero((tm == m["i"]) & vert & (area > 1e-4))[0]
        if len(idx) > 4000:
            idx = idx[:4000]
        for g in islands(tv[idx]):
            ti = idx[g]
            a = float(area[ti].sum())
            if a < 0.25:
                continue
            n = (nrm[ti] * area[ti][:, None]).sum(0)
            nh = math.hypot(n[0], n[1])
            if nh < 1e-6:
                continue
            nx, ny = n[0] / nh, n[1] / nh
            pts = co[tv[ti].ravel()]            # colturile triunghiurilor, cu UV-ul fiecaruia
            uvs = uv[tl[ti].ravel()]
            us = pts[:, 0] * -ny + pts[:, 1] * nx
            w, h = float(np.ptp(us)), float(np.ptp(pts[:, 2]))
            if w < 0.3 or h < 0.3:
                continue
            su, sv = float(np.ptp(uvs[:, 0])), float(np.ptp(uvs[:, 1]))
            ou, ov = float(uvs[:, 0].min()), float(uvs[:, 1].min())
            # cum sta textura pe geam: v creste in sus (1) sau in jos (-1); u in sensul fatadei; 90 = intoarsa
            zc, uc = pts[:, 2] - pts[:, 2].mean(), us - us.mean()
            cu, cv = uvs[:, 0] - uvs[:, 0].mean(), uvs[:, 1] - uvs[:, 1].mean()
            turned = abs(float(zc @ cu)) > abs(float(zc @ cv))
            wins.append({"tex": m["tex"], "sh": m["shader"], "src": m["src"], "w": w, "h": h, "z": float(pts[:, 2].min()) - zmin, "rect": a / max(w * h, 1e-6),
                         "c": float(us.mean()), "ang": round(math.degrees(math.atan2(ny, nx)) / 15.0),
                         "off": round(float((pts[:, :2] @ np.array([nx, ny])).mean()) / 0.5),
                         "su": su, "sv": sv, "ou": ou - math.floor(ou), "ov": ov - math.floor(ov),
                         "vz": 90 if turned else (1 if float(zc @ cv) >= 0 else -1),
                         "uu": 1 if float(uc @ cu) >= 0 else -1})
    # ritmul: ferestrele de pe acelasi plan, pe randuri (acelasi z jos)
    bays, floors = [], []
    single = [x for x in wins if x["rect"] > 0.7 and x["w"] < 4.0 and x["h"] < 4.0]
    planes = collections.defaultdict(list)
    for x in single:
        planes[(x["ang"], x["off"])].append(x)
    for items in planes.values():
        rows = []
        for x in sorted(items, key=lambda x: x["z"]):
            if rows and abs(rows[-1][0]["z"] - x["z"]) < 0.25:
                rows[-1].append(x)
            else:
                rows.append([x])
        for r in rows:
            cs = sorted(x["c"] for x in r)
            bays += [b - a for a, b in zip(cs, cs[1:]) if 1.0 < b - a < 9.0]
        zs = [r[0]["z"] for r in rows]
        floors += [b - a for a, b in zip(zs, zs[1:]) if 2.4 < b - a < 6.5]
    walls = sorted((m for m in mats if m["role"] == "perete"), key=lambda m: -m["av"])
    roofs = sorted((m for m in mats if m["role"] == "acoperis"), key=lambda m: -m["au"])
    wa = collections.Counter()
    for x in wins:
        wa[x["tex"]] += x["w"] * x["h"]
    lo, hi = info["min"], info["max"]
    return {"name": obj.name, "cat": info.get("cat"), "style": info.get("style"),
            "size": [round(hi[i] - lo[i], 1) for i in range(3)],
            "wall": walls[0]["tex"] if walls and walls[0]["av"] > 15 else None,
            "walls": [[m["tex"], round(m["av"], 1), round(m["rep"], 2), m["shader"]] for m in walls[:5]],
            "roof": roofs[0]["tex"] if roofs else None,
            "windows": [[t, round(a, 1)] for t, a in wa.most_common(6)],
            "bay": round(float(np.median(bays)), 2) if len(bays) >= 3 else None,
            "floor": round(float(np.median(floors)), 2) if len(floors) >= 2 else None,
            "win": [round(float(np.median([x["w"] for x in single])), 2),
                    round(float(np.median([x["h"] for x in single])), 2)] if len(single) >= 3 else None,
            "_wins": wins, "_mats": mats}


def summarize(buildings):
    walls, windows = {}, {}
    for b in buildings:
        tags = (b["cat"], b["style"])
        for m in b["_mats"]:
            if m["role"] != "perete" or m["av"] < 5:
                continue
            w = walls.setdefault(m["tex"], {"shader": m["shader"], "src": m["src"], "rep": [], "area": 0.0, "n": 0,
                                            "cat": collections.Counter(), "style": collections.Counter()})
            w["rep"].append(m["rep"])
            w["area"] += m["av"]
            w["n"] += 1
            w["cat"][tags[0]] += 1
            w["style"][tags[1]] += 1
        seen = set()
        for x in b["_wins"]:
            w = windows.setdefault(x["tex"], {"shader": x["sh"], "src": x["src"], "samples": [], "n": 0, "cat": collections.Counter(),
                                              "style": collections.Counter(), "walls": collections.Counter()})
            if len(w["samples"]) < 400:
                w["samples"].append(x)
            if x["tex"] not in seen:
                seen.add(x["tex"])
                w["n"] += 1
                w["cat"][tags[0]] += 1
                w["style"][tags[1]] += 1
                for t, _a, _r, _s in b["walls"][:2]:
                    w["walls"][t] += 1
    out_w = {}
    for t, w in walls.items():
        reps = [r for r in w["rep"] if r > 0]
        out_w[t] = {"shader": w["shader"], "src": w["src"], "rep": round(float(np.median(reps)), 2) if reps else 0.0,
                    "area": round(w["area"]), "n": w["n"], "cat": dict(w["cat"]), "style": dict(w["style"])}
    out_g = {}
    for t, w in windows.items():
        s = w["samples"]
        rects = [x for x in s if x["rect"] > 0.7]
        kinds = collections.Counter("fereastra" if 0.85 < x["su"] < 1.15 and 0.85 < x["sv"] < 1.15 else
                                    "atlas" if x["su"] <= 0.85 and x["sv"] <= 1.15 else "banda" for x in rects)
        # bucatile de textura folosite ca o fereastra: pozitia in textura (1/16), marimea reala, cum sta pe geam
        by_cell = collections.defaultdict(list)
        for x in rects:
            if 0.05 < x["su"] <= 1.15 and 0.05 < x["sv"] <= 1.15:
                by_cell[(round(x["ou"] * 16) / 16, round(x["ov"] * 16) / 16, round(x["su"] * 16) / 16,
                         round(x["sv"] * 16) / 16)].append(x)
        cells = sorted(by_cell.items(), key=lambda kv: -len(kv[1]))[:8]
        tiled = [x for x in rects if x["su"] > 1.15 or x["sv"] > 1.15]
        out_g[t] = {"n": w["n"], "kind": kinds.most_common(1)[0][0] if kinds else None, "kinds": dict(kinds),
                    "w": round(float(np.median([x["w"] for x in rects])), 2) if rects else None,
                    "h": round(float(np.median([x["h"] for x in rects])), 2) if rects else None,
                    "cells": [{"uv": list(k), "n": len(xs), "w": round(float(np.median([x["w"] for x in xs])), 2),
                               "h": round(float(np.median([x["h"] for x in xs])), 2),
                               "vz": collections.Counter(x["vz"] for x in xs).most_common(1)[0][0],
                               "uu": collections.Counter(x["uu"] for x in xs).most_common(1)[0][0],
                               "z": round(float(np.median([x["z"] for x in xs])), 1)} for k, xs in cells],
                    "shader": w.get("shader", ""), "src": w["src"],
                    "rep": [round(float(np.median([x["w"] / x["su"] for x in tiled])), 2),
                            round(float(np.median([x["h"] / max(x["sv"], 1e-3) for x in tiled])), 2)] if tiled else None,
                    "cat": dict(w["cat"]), "style": dict(w["style"]), "walls": dict(w["walls"].most_common(12))}
    return out_w, out_g


def main():
    limit = int(arg("--limit", "0") or 0)
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    wanted = collections.defaultdict(dict)
    for a in data.get("archetypes") or ():
        tags = a.get("tags") or []
        if "solid" in tags:
            for t in tags:
                if t.startswith("ytyp:"):
                    wanted[t[5:]][a["name"]] = a
    files = [(y, LIB / f"_assets.{y}.blend") for y in sorted(wanted) if (LIB / f"_assets.{y}.blend").is_file()]
    missing = len(wanted) - len(files)
    if limit:
        files = files[:limit]
    print(f"ANALIZA {len(files)} fisiere ({missing} zone neimportate)", flush=True)
    buildings, t0 = [], time.time()
    for k, (ytyp, path) in enumerate(files):
        names = wanted[ytyp]
        with bpy.data.libraries.load(str(path), link=False) as (src, dst):
            dst.objects = [n for n in src.objects if n in names]
        objs = [o for o in dst.objects if o is not None]
        for o in objs:
            if o.type != "MESH":
                continue
            try:
                b = analyze(o, names[o.name], path.name)
            except Exception as error:
                print(f"  {o.name}: {error}", flush=True)
                b = None
            if b:
                buildings.append(b)
        ids = objs + [o.data for o in objs if o.data] + list(bpy.data.materials) + list(bpy.data.images)
        bpy.data.batch_remove(ids)
        for lib in list(bpy.data.libraries):
            try:
                bpy.data.libraries.remove(lib)
            except Exception:
                pass
        print(f"ANALIZA {k + 1}/{len(files)} {ytyp}: {len(objs)} cladiri, {time.time() - t0:.0f} s", flush=True)
    walls, windows = summarize(buildings)
    for b in buildings:
        b.pop("_mats")
        b.pop("_wins")
    OUT.write_text(json.dumps({"buildings": buildings, "walls": walls, "windows": windows}, indent=1), encoding="utf-8")
    print(f"ANALIZA gata: {len(buildings)} cladiri, {len(walls)} pereti, {len(windows)} texturi de geam -> {OUT}", flush=True)


main()
