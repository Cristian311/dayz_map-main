# -*- coding: utf-8 -*-
"""
Firme si vitrine de magazin din GTA, taiate din atlasele jocului (o textura cu multe firme) in fisiere separate,
output/gta_asset_library/firma_*.dds si vitrina_*.dds. Le folosesc generatorul de cladiri (rolurile "firma" si
"vitrina" din blender_gen_buildings.GTA_MATS) si paleta editorului din joc (paleta_texturi.py, familia "Firme"),
deci o firma se schimba din joc ca orice alta textura.

Bucatile (u0, v0, latime, inaltime, in fractiuni din textura) sunt alese de mana, dupa planse cu atlasele.
Rulare:  tools\\_blender.bat -b -P tools\\crop_firme.py      (scrie si output/firme_plansa.png, de verificare)
"""
import re
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / "output" / "gta_asset_library"

# (textura din biblioteca, prefixul fisierelor, [(nume, u0, v0, su, sv)])
# (verificate pe plansa; randurile din mh_rsn_id2_13_sign2amo si o parte din celelalte erau decalate si au fost scoase)
CROPS = [
    ("dt1_16_signs", "firma", [("gentstyle", 0, 0.75, 1, 0.25)]),
    ("ngx_id1_09_rb_signs", "firma", [("sneaker", 0, 0.75, 1, 0.25), ("liquor", 0, 0.5, 1, 0.25),
                                      ("autos", 0, 0.25, 1, 0.25), ("forlease", 0, 0, 1, 0.25)]),
    ("rsn_mh_dt1_17_fashionsign_mlw", "firma", [("fashion", 0, 0, 1, 0.25)]),
    # vitrine deschise (magazin pictat in geam) si inchise (rulou tras, afis)
    ("vb_17_stores_windoors_d", "vitrina", [("vb17_0", 0, 0, 0.25, 0.5), ("vb17_1", 0.25, 0, 0.25, 0.5),
                                           ("vb17_3", 0.75, 0, 0.25, 0.5), ("vb17w_0", 0, 0.5, 0.25, 0.5),
                                           ("vb17w_1", 0.25, 0.5, 0.25, 0.5), ("inchis_vb17", 0.5, 0, 0.25, 0.5)]),
    ("hw1_1_nr_ja_win2combi", "vitrina", [("hw1_a", 0, 0.5, 0.5, 0.5), ("hw1_c", 0, 0, 0.5, 0.5),
                                          ("hw1_d", 0.5, 0, 0.5, 0.5)]),
    ("bh1_33_rsn_mjg_winpr01", "vitrina", [("inchis_bh33", 0, 0.5, 1, 0.5)]),
    ("dt1_05_rsn_dc_window_0002", "vitrina", [("dt05", 0, 0.6875, 1, 0.3125)]),
]
# numele tuturor bucatilor, pentru generator si paleta (fara sa citeasca fisierele)
FIRME = [f"firma_{n}" for _t, p, cells in CROPS if p == "firma" for n, *_ in cells]
VITRINE = [f"vitrina_{n}" for _t, p, cells in CROPS if p == "vitrina" for n, *_ in cells if not n.startswith("inchis")]
VITRINE_INCHISE = [f"vitrina_{n}" for _t, p, cells in CROPS if p == "vitrina" for n, *_ in cells if n.startswith("inchis")]


def find_materials(wanted):
    where = {}
    for path in sorted(LIB.glob("_assets.*.blend")):
        with bpy.data.libraries.load(str(path)) as (src, _dst):
            for m in src.materials:
                base = re.sub(r"\.\d{3}$", "", m)
                if base in wanted and base not in where:
                    where[base] = (path, m)
        if len(where) == len(wanted):
            break
    return where


def main():
    import sys
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from dayzgen.dds_writer import write_dds
    for old in list(LIB.glob("firma_*.dds")) + list(LIB.glob("vitrina_*.dds")):
        old.unlink()        # bucatile scoase din lista nu raman pe disc
    where = find_materials({t for t, _p, _c in CROPS})
    tiles, names = [], []
    for tex, prefix, cells in CROPS:
        if tex not in where:
            print(f"CROP lipsa in biblioteca: {tex}")
            continue
        path, mname = where[tex]
        with bpy.data.libraries.load(str(path), link=False) as (_s, dst):
            dst.materials = [mname]
        mat = dst.materials[0]
        node = mat.node_tree.nodes.get("DiffuseSampler") if mat and mat.node_tree else None
        img = node.image if node is not None else None
        if img is None:
            print(f"CROP fara imagine: {tex}")
            continue
        W, H = tuple(img.size)
        px = np.array(img.pixels[:], np.float32).reshape(H, W, 4)      # randurile de jos in sus, ca UV-ul
        for name, u0, v0, su, sv in cells:
            x0, y0 = int(round(u0 * W)), int(round(v0 * H))
            w, h = max(4, int(su * W) // 4 * 4), max(4, int(sv * H) // 4 * 4)
            crop = px[y0:y0 + h, x0:x0 + w, :3]
            out = f"{prefix}_{name}"
            write_dds(str(LIB / f"{out}.dds"), np.ascontiguousarray(crop[::-1]), "DXT1")
            names.append(out)
            tiles.append(crop)
            print(f"CROP {out}.dds {w}x{h}")
    # plansa de verificare: fiecare bucata pe un rand, latita la 512 px
    S = 512
    rows = []
    for crop in tiles:
        h, w = crop.shape[:2]
        hh = max(16, int(round(h * S / w)))
        ys = (np.arange(hh) * h / hh).astype(int)
        xs = (np.arange(S) * w / S).astype(int)
        rows.append(crop[ys][:, xs])
        rows.append(np.ones((4, S, 3), np.float32) * np.array([1, 0, 1], np.float32))
    sheet = np.concatenate(rows[::-1], axis=0)
    im = bpy.data.images.new("sheet", S, sheet.shape[0])
    im.pixels[:] = np.concatenate([sheet, np.ones(sheet.shape[:2] + (1,), np.float32)], axis=2).ravel()
    im.filepath_raw = str(ROOT / "output" / "firme_plansa.png")
    im.file_format = "PNG"
    im.save()
    (ROOT / "output" / "firme_plansa.txt").write_text("\n".join(names), encoding="utf-8")
    print(f"CROP gata: {len(names)} fisiere; plansa output/firme_plansa.png (de sus in jos, in ordinea din .txt)")


if __name__ == "__main__":
    main()
