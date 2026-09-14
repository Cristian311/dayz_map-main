# -*- coding: utf-8 -*-
"""
Masoara cat de "plina" e fiecare cladire din catalog, direct din geometria ei din joc.

O cladire adevarata are acoperis: vazuta de sus, suprafetele orizontale acopera aproape toata
amprenta. Schelele, cadrele, balustradele, macaralele si ramele de semne au si ele LOD propriu
(deci trec de filtrul `haslod`), dar acopera foarte putin. Scriptul incarca modelul fiecarui
arhetip (nivelul de detaliu cel mai mare), proiecteaza de sus triunghiurile orizontale pe o grila
de 0,5 m peste amprenta si scrie in catalog:

    cov:NN   procentul din amprenta acoperit de acoperis sau planseu
    solid    daca procentul trece pragul

    python tools\\measure_solidity.py                 doar arhetipurile `haslod` (cele folosite)
    python tools\\measure_solidity.py --all           tot catalogul (sare peste ce e deja masurat)
    python tools\\measure_solidity.py --all --force   remasoara tot
    python tools\\measure_solidity.py --threshold 45       (implicit 40)
    python tools\\measure_solidity.py --rethreshold 45     doar reaplica pragul pe procentele masurate

Citeste arhivele cu szio + pymateria, deci ruleaza cu Python-ul din Blender (se re-lanseaza singur).
"""
import glob
import importlib.util
import math
import os
import subprocess
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools", "pydeps"))


def _game_tool():
    spec = importlib.util.spec_from_file_location("cfg_game", os.path.join(ROOT, "tools", "catalog_from_game.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def ensure_pymateria(tool):
    try:
        import pymateria  # noqa: F401
        return
    except Exception:
        pass
    if os.environ.get("DZ_RELAUNCHED") == "1":
        print("EROARE: pymateria nu se incarca nici cu Python-ul din Blender.")
        raise SystemExit(2)
    exe = tool.blender_python()
    if not exe:
        print("EROARE: nu gasesc Python-ul din Blender.")
        raise SystemExit(2)
    print(f"(re-lansez cu {exe})", flush=True)
    code = subprocess.call([exe, os.path.abspath(__file__)] + sys.argv[1:], env=dict(os.environ, DZ_RELAUNCHED="1"))
    raise SystemExit(code)


def roof_coverage(drawable, bb_min, bb_max, cell=0.5, min_nz=0.35):
    """Fractiunea din amprenta (bbox XY) acoperita, vazut de sus, de triunghiuri orizontale."""
    models = getattr(drawable, "models", None)
    if not models:
        return None
    lod = models.get(0) if hasattr(models, "get") else None
    if not lod:
        lod = next(iter(models.values()))
    tris = []
    for model in (lod if isinstance(lod, (list, tuple)) else [lod]):
        for geom in model.geometries:
            vb, ib = geom.vertex_buffer, geom.index_buffer
            if vb is None or ib is None or len(ib) < 3:
                continue
            pos = np.asarray(vb["Position"], dtype=np.float64).reshape(-1, 3)
            idx = np.asarray(ib, dtype=np.int64)
            idx = idx[: len(idx) - len(idx) % 3].reshape(-1, 3)
            tris.append(pos[idx])
    if not tris:
        return None
    tri = np.concatenate(tris)
    normal = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    length = np.linalg.norm(normal, axis=1)
    keep = (length > 1e-6) & (np.abs(normal[:, 2]) >= min_nz * np.maximum(length, 1e-12))
    tri = tri[keep]
    # Doar suprafetele de deasupra unui sfert din inaltime conteaza ca acoperis. Altfel un covor
    # de iarba, o umbra sau o piscina (plane la sol, acoperire totala) ar parea cladiri perfecte.
    z_cut = float(bb_min[2]) + 0.25 * (float(bb_max[2]) - float(bb_min[2]))
    tri = tri[tri[:, :, 2].mean(axis=1) >= z_cut]

    x0, y0 = float(bb_min[0]), float(bb_min[1])
    nx = max(1, int(math.ceil((float(bb_max[0]) - x0) / cell)))
    ny = max(1, int(math.ceil((float(bb_max[1]) - y0) / cell)))
    covered = np.zeros((ny, nx), dtype=bool)
    if not len(tri):
        return 0.0

    xs, ys = tri[:, :, 0], tri[:, :, 1]
    # Triunghiurile mai mici decat o celula: doar celula centrului lor (vectorizat).
    small = ((xs.max(1) - xs.min(1)) < cell) & ((ys.max(1) - ys.min(1)) < cell)
    ci = np.clip(((xs[small].mean(1) - x0) / cell).astype(np.int64), 0, nx - 1)
    cj = np.clip(((ys[small].mean(1) - y0) / cell).astype(np.int64), 0, ny - 1)
    covered[cj, ci] = True

    for t in tri[~small]:
        txs, tys = t[:, 0], t[:, 1]
        i0 = max(0, int((txs.min() - x0) / cell))
        i1 = min(nx - 1, int((txs.max() - x0) / cell))
        j0 = max(0, int((tys.min() - y0) / cell))
        j1 = min(ny - 1, int((tys.max() - y0) / cell))
        if i1 < i0 or j1 < j0:
            continue
        gx, gy = np.meshgrid(x0 + (np.arange(i0, i1 + 1) + 0.5) * cell, y0 + (np.arange(j0, j1 + 1) + 0.5) * cell)
        (ax, ay), (bx, by), (cx, cy) = t[0, :2], t[1, :2], t[2, :2]
        d = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(d) < 1e-9:
            continue
        l1 = ((by - cy) * (gx - cx) + (cx - bx) * (gy - cy)) / d
        l2 = ((cy - ay) * (gx - cx) + (ax - cx) * (gy - cy)) / d
        covered[j0:j1 + 1, i0:i1 + 1] |= (l1 >= -1e-6) & (l2 >= -1e-6) & (l1 + l2 <= 1.0 + 1e-6)
    return float(covered.mean())


def rethreshold(threshold: float) -> int:
    """Reaplica pragul pe etichetele `cov:NN` deja masurate, fara sa reincarce modelele."""
    from dayzgen.city import catalog as C
    cat = C.Catalog.load(required=True)
    solid = 0
    for arch in cat.items.values():
        pct = next((int(t[4:]) for t in arch.tags if t.startswith("cov:")), None)
        if pct is None:
            continue
        tags = [t for t in arch.tags if t != "solid"]
        if pct >= threshold:
            tags.append("solid")
            solid += 1
        arch.tags = tuple(tags)
    cat.save()
    print(f"prag {threshold:.0f}%: {solid} modele solide")
    return 0


def main(argv) -> int:
    if "--rethreshold" in argv:
        return rethreshold(float(argv[argv.index("--rethreshold") + 1]))
    tool = _game_tool()
    ensure_pymateria(tool)
    import szio
    from szio import rpf, vfs
    from dayzgen.city import catalog as C

    # Masurat pe exemple cunoscute: bucatile (schele, cadre) stau sub 30%, cladirile reale intre
    # 26% si 64% (acoperisul e adesea un arhetip separat). 40% taie banda de bucati.
    threshold = 40.0
    if "--threshold" in argv:
        threshold = float(argv[argv.index("--threshold") + 1])
    root = tool.gta_dir(argv)
    if not root:
        print("Nu gasesc GTA V (--gta \"<cale>\").")
        return 1

    cat = C.Catalog.load(required=True)
    targets = [a for a in cat.items.values() if "--all" in argv or "haslod" in a.tags]
    # Ce e deja masurat nu se remasoara (--force remasoara tot).
    if "--force" not in argv:
        targets = [a for a in targets if not any(t.startswith("cov:") for t in a.tags)]
    print(f"{len(targets)} arhetipuri de masurat, prag {threshold:.0f}%")

    t0 = time.time()
    index = {}
    tops = sorted(glob.glob(os.path.join(root, "x64*.rpf")))
    update = os.path.join(root, "update", "update.rpf")
    if os.path.isfile(update):
        tops.append(update)
    for top in tops:
        try:
            archive = rpf.open_rpf(top)
        except Exception:
            continue
        for parts, path in tool.iter_files(archive, [], (".ydr",)):
            if tool.wanted_area(parts, path, tool.DEFAULT_AREAS):
                index[os.path.basename(path)[:-4].lower()] = (top, parts, path)
        vfs.clear_archive_cache()
    print(f"{len(index)} modele .ydr indexate ({time.time() - t0:.0f} s)", flush=True)

    measured = 0
    missing = 0
    solid = 0
    buckets = [0] * 11
    for n, arch in enumerate(targets):
        loc = index.get(arch.name)
        drawable = None
        if loc is not None:
            try:
                drawable = szio.try_load_asset(vfs.VPath(loc[0], *loc[1], loc[2]))
            except Exception:
                drawable = None
        cov = roof_coverage(drawable, arch.bb_min, arch.bb_max) if drawable is not None else None
        if cov is None:
            missing += 1
            continue
        pct = int(round(cov * 100))
        tags = [t for t in arch.tags if not t.startswith("cov:") and t != "solid"]
        tags.append(f"cov:{pct}")
        if pct >= threshold:
            tags.append("solid")
            solid += 1
        arch.tags = tuple(tags)
        buckets[min(10, pct // 10)] += 1
        measured += 1
        if (n + 1) % 200 == 0:
            vfs.clear_archive_cache()
            print(f"  {n + 1}/{len(targets)} ({time.time() - t0:.0f} s)", flush=True)

    cat.save()
    print(f"\nmasurate {measured}, fara model .ydr {missing}, solide {solid} (prag {threshold:.0f}%)")
    print("distributie acoperis: " + "  ".join(f"{i * 10}%:{c}" for i, c in enumerate(buckets)))
    print(f"durata {time.time() - t0:.0f} s")
    return 0


if __name__ == "__main__":
    exit_code = main(sys.argv[1:])
    sys.stdout.flush()
    os._exit(exit_code)
