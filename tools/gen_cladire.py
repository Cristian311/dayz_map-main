# -*- coding: utf-8 -*-
"""
Genereaza O cladire (sau un rand de cladiri lipite) si o salveaza intr-un fisier, fara tab-ul Harta
(ruleaza in Blender fara interfata).

    GENEREAZA_CLADIRE.bat                       intreaba ce vrei, pe rand
    _blender.bat -b -P gen_cladire.py -- --tip bloc --etaje 6 --seed 42 --interior
    _blender.bat -b -P gen_cladire.py -- --rand --lungime 80 --etaje-min 3 --etaje-max 7

Iese in output\\cladiri\\<nume>.glb (il tragi in Blender) si .blend (File > Append > Object, sau
> Collection pentru un rand, cu materialele Sollumz intacte, bune pentru export in FiveM).
Texturile sunt puse in fisier. Randul: fatadele aliniate pe Y = 0, de la X = -lungime/2 la +lungime/2.
"""
import argparse
import random
import runpy
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parent.parent
gen = runpy.run_path(str(Path(__file__).resolve().parent / "blender_gen_buildings.py"), run_name="gen_cladire")


def clear_scene():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)


def save(name, out, glb=True):
    """Salveaza scena ca <out>/<name>.blend (texturi incluse) si .glb (glb=False: doar .blend, la generarea
    incrementala a orasului; .glb-ul ia cam cat .blend-ul si nu il foloseste exportul FiveM)."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    stem = out / name
    for img in bpy.data.images:
        if img.source == "FILE" and img.packed_file is None and Path(bpy.path.abspath(img.filepath)).is_file():
            img.pack()
    bpy.ops.wm.save_as_mainfile(filepath=str(stem.with_suffix(".blend")), compress=True)
    if not glb:
        return stem.with_suffix(".glb")
    # in .glb materialele cu alpha legat devin "BLEND" si se vede prin ele: ale cladirilor si strazilor devin
    # opace, iar la props (frunze) alpha trece printr-un nod Round, pe care exportul il scrie ca "MASK" (decupaj)
    for mat in bpy.data.materials:
        if mat.node_tree is None:
            continue
        tree = mat.node_tree
        ours = mat.get("harta_gta") is not None or mat.name.startswith("cladire_")
        for link in list(tree.links):
            if link.to_node.type != "BSDF_PRINCIPLED" or link.to_socket.name != "Alpha":
                continue
            if ours:
                tree.links.remove(link)
            elif link.from_node.type != "MATH":
                src, dst = link.from_socket, link.to_socket
                tree.links.remove(link)
                rnd = tree.nodes.new("ShaderNodeMath")
                rnd.operation = "ROUND"
                tree.links.new(src, rnd.inputs[0])
                tree.links.new(rnd.outputs[0], dst)
        if ours:
            for node in tree.nodes:
                if node.type == "BSDF_PRINCIPLED":
                    node.inputs["Alpha"].default_value = 1.0
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(filepath=str(stem.with_suffix(".glb")), export_format="GLB", use_selection=True,
                              export_image_format="AUTO", export_apply=True)
    return stem.with_suffix(".glb")


def row(coll, length, depth, emin, emax, texturi, interior, seed, ends=(False, False),
        jitter=(0.0, 0.0, -2.0, 2.0), name=None, gaps=0.0):
    """Cladiri lipite, fiecare alta (latime, etaje, perete, magazine), sub un obiect gol parinte.
    Local: de la X = -length/2 la +length/2, fatadele pe Y = 0 (spre -Y), adancimea spre +Y.
    ends: capetele randului lipite si ele de alte cladiri (fara ferestre acolo).
    gaps: sansa unei alei de 3-5 m intre doua cladiri (cladirile de langa ea au ferestre spre alee)."""
    rng = random.Random(seed)
    widths, rem = [], length
    while rem > 0.5:
        w = rem if rem <= 18.0 else min(rng.uniform(8.0, 16.0), rem - 8.0)
        widths.append(w)
        rem -= w
    alley = [0.0] * len(widths)
    rg = random.Random(seed ^ 0x5A5A)
    for i in range(len(widths) - 1):
        if rg.random() < gaps:
            g = rg.uniform(3.0, 5.0)
            if widths[i] - g / 2 >= 7.0 and widths[i + 1] - g / 2 >= 7.0:
                widths[i] -= g / 2
                widths[i + 1] -= g / 2
                alley[i] = g
    root = bpy.data.objects.new(name or f"rand_{seed}", None)
    root["harta_tip"] = "rand_cladiri"
    coll.objects.link(root)
    x = -length / 2
    n = len(widths)
    for i, w in enumerate(widths):
        shop = 0 < i < n - 1 and rng.random() < 0.15
        d = max(8.0, depth + rng.choice(jitter))
        p = {"tip": "magazin" if shop else "bloc", "latime": round(w, 2), "adancime": round(d, 2),
             "etaje": 1 if shop else rng.randint(emin, max(emin, emax)),
             "inaltime": 4.5 if shop else rng.choice([3.0, 3.1, 3.2, 3.4]), "acoperis": "plat",
             "interior": interior, "comercial": rng.random() < 0.7, "texturi": texturi,
             "seed": rng.randrange(1, 99999), "rezervor": 0.22,
             "perete": rng.choices(["perete_caramida", "perete_vila", "perete_beton"], [6, 2, 2])[0],
             "lipit": [s for s, ok in (("stanga", (i > 0 and not alley[i - 1]) or (i == 0 and ends[0])),
                                       ("dreapta", (i < n - 1 and not alley[i]) or (i == n - 1 and ends[1]))) if ok]}
        obj, inside = gen["build"](p)
        coll.objects.link(obj)
        obj.parent = root
        obj.location = (x + w / 2, d / 2, 0.0)
        if inside is not None:
            coll.objects.link(inside)
            inside.parent = obj
        x += w + alley[i]
    return root


def build_row(a, seed):
    coll = bpy.data.collections.new(f"rand_{seed}")
    bpy.context.scene.collection.children.link(coll)
    root = row(coll, a.lungime, a.adancime, a.etaje_min, a.etaje_max, a.texturi, a.interior, seed, gaps=a.alei)
    print(f"CLADIRE {root.name}: {len(root.children)} cladiri pe {a.lungime:g} m, etaje {a.etaje_min}-{a.etaje_max}")
    return root.name


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--tip", default="casa", choices=list(gen["DEFAULTS"]))
    ap.add_argument("--latime", type=float, default=0.0)
    ap.add_argument("--adancime", type=float, default=0.0)
    ap.add_argument("--etaje", type=int, default=0)
    ap.add_argument("--inaltime", type=float, default=0.0)
    ap.add_argument("--acoperis", default="auto", choices=["auto", "patru", "doua", "plat"])
    ap.add_argument("--interior", action="store_true")
    ap.add_argument("--fara-magazin", action="store_true", help="bloc fara magazine la parter")
    ap.add_argument("--texturi", default="gta", choices=["gta", "simple"])
    ap.add_argument("--seed", type=int, default=0, help="0 = la intamplare")
    ap.add_argument("--rand", action="store_true", help="rand de cladiri lipite")
    ap.add_argument("--lungime", type=float, default=60.0, help="lungimea randului (m)")
    ap.add_argument("--etaje-min", type=int, default=3)
    ap.add_argument("--etaje-max", type=int, default=7)
    ap.add_argument("--alei", type=float, default=0.0, help="sansa unei alei intre doua cladiri din rand")
    ap.add_argument("--out", default=str(ROOT / "output" / "cladiri"))
    a = ap.parse_args(argv)
    seed = a.seed or random.randint(1, 99999)

    clear_scene()
    if a.rand:
        if not a.adancime:
            a.adancime = 16.0
        name = build_row(a, seed)
    else:
        w, d, n, h = gen["DEFAULTS"][a.tip]
        p = {"tip": a.tip, "latime": a.latime or w, "adancime": a.adancime or d, "etaje": a.etaje or n,
             "inaltime": a.inaltime or h, "acoperis": a.acoperis, "interior": a.interior,
             "comercial": not a.fara_magazin, "texturi": a.texturi, "seed": seed}
        obj, inside = gen["build"](p)
        coll = bpy.data.collections.new(obj.name)
        bpy.context.scene.collection.children.link(coll)
        coll.objects.link(obj)
        if inside is not None:
            coll.objects.link(inside)
            inside.parent = obj
        name = obj.name
        print(f"CLADIRE {obj.name}: {p['latime']:g} x {p['adancime']:g} m, {p['etaje']} etaje, "
              f"{len(obj.data.polygons)} fete{', cu interior' if inside else ''}")
    print(f"CLADIRE_FISIER {save(name, a.out)}")


if __name__ == "__main__":
    main()
