# -*- coding: utf-8 -*-
"""
Deschide orasul generat in Blender, cu cladirile reale din GTA V.

    blender -b -P tools\\blender_city_scene.py -- --city output\\dzdemo_oras [--render]

Construieste terenul orasului din terrain.npz, importa <nume>_city.ymap cu Sollumz (fiecare
entitate devine modelul real din biblioteca facuta de blender_build_library.py), pune o
camera si un soare si salveaza <nume>_city.blend. Cu --render scrie si render.png.

In .blend poti muta, sterge sau adauga cladiri (Asset Browser > GTA5), apoi exporti .ymap-ul
cu Sollumz (selecteaza ymap-ul in panoul Sollumz > Export).
"""
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _sollumz_setup import setup_sollumz  # noqa: E402

PARK = 6
COLORS = {
    "grass": (0.20, 0.32, 0.12, 1.0),
    "park": (0.14, 0.30, 0.10, 1.0),
    "city": (0.55, 0.54, 0.51, 1.0),
    "street": (0.07, 0.07, 0.08, 1.0),
}


def cli_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = {"city": None, "render": "--render" in argv, "margin": 60.0}
    for i, value in enumerate(argv):
        if value == "--city" and i + 1 < len(argv):
            out["city"] = argv[i + 1]
        if value == "--margin" and i + 1 < len(argv):
            out["margin"] = float(argv[i + 1])
    return out


def build_terrain(npz_path: Path, margin: float):
    data = np.load(npz_path)
    h, city, street, zones = data["h"], data["city"], data["street"], data["zones"]
    cell = float(data["cell"])
    ox, oy = (float(v) for v in data["origin"])

    iy, ix = np.nonzero(city)
    pad = int(margin / cell)
    if len(ix):
        x0, x1 = max(0, ix.min() - pad), min(h.shape[1] - 1, ix.max() + pad)
        y0, y1 = max(0, iy.min() - pad), min(h.shape[0] - 1, iy.max() + pad)
    else:
        x0, y0, x1, y1 = 0, 0, h.shape[1] - 1, h.shape[0] - 1

    sub = h[y0:y1 + 1, x0:x1 + 1]
    ny, nx = sub.shape
    xs = np.arange(x0, x1 + 1) * cell + ox
    ys = np.arange(y0, y1 + 1) * cell + oy
    X, Y = np.meshgrid(xs, ys)
    verts = np.stack([X.ravel(), Y.ravel(), sub.ravel()], axis=1)
    idx = np.arange(ny * nx).reshape(ny, nx)
    faces = np.stack([idx[:-1, :-1].ravel(), idx[:-1, 1:].ravel(), idx[1:, 1:].ravel(), idx[1:, :-1].ravel()], axis=1)

    mesh = bpy.data.meshes.new("oras_teren")
    mesh.from_pydata(verts.tolist(), [], faces.tolist())
    mesh.update()

    colors = np.tile(np.array(COLORS["grass"], dtype=np.float32), (ny * nx, 1))
    c = city[y0:y1 + 1, x0:x1 + 1].ravel()
    z = zones[y0:y1 + 1, x0:x1 + 1].ravel()
    s = street[y0:y1 + 1, x0:x1 + 1].ravel()
    colors[c] = COLORS["city"]
    colors[c & (z == PARK)] = COLORS["park"]
    colors[s] = COLORS["street"]
    attr = mesh.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
    attr.data.foreach_set("color", colors.ravel())

    mat = bpy.data.materials.new("oras_teren")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    col_node = nodes.new("ShaderNodeVertexColor")
    col_node.layer_name = "Col"
    mat.node_tree.links.new(col_node.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.95
    mesh.materials.append(mat)

    obj = bpy.data.objects.new("oras_teren", mesh)
    bpy.context.scene.collection.objects.link(obj)
    center = Vector((float(xs.mean()), float(ys.mean()), float(np.median(sub))))
    extent = float(max(xs[-1] - xs[0], ys[-1] - ys[0]))
    return obj, center, extent


def setup_view(center: Vector, extent: float):
    scene = bpy.context.scene
    cam_data = bpy.data.cameras.new("oras_camera")
    cam_data.clip_end = 20000.0
    cam_data.lens = 32.0
    cam = bpy.data.objects.new("oras_camera", cam_data)
    scene.collection.objects.link(cam)
    dist = extent * 0.75
    cam.location = center + Vector((-dist * 0.55, -dist * 0.75, dist * 0.55))
    cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam

    sun_data = bpy.data.lights.new("oras_soare", "SUN")
    sun_data.energy = 4.0
    sun = bpy.data.objects.new("oras_soare", sun_data)
    sun.rotation_euler = (math.radians(50), 0.0, math.radians(35))
    scene.collection.objects.link(sun)

    world = scene.world or bpy.data.worlds.new("oras_cer")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.55, 0.65, 0.80, 1.0)
        bg.inputs["Strength"].default_value = 0.9


def render(path: Path):
    scene = bpy.context.scene
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 900
    scene.render.filepath = str(path)
    for engine in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT", "BLENDER_WORKBENCH"):
        try:
            scene.render.engine = engine
            break
        except TypeError:
            continue
    if scene.render.engine == "BLENDER_WORKBENCH":
        scene.display.shading.color_type = "TEXTURE"
    bpy.ops.render.render(write_still=True)
    print(f"render ({scene.render.engine}): {path}")


def main():
    args = cli_args()
    if not args["city"]:
        print("EROARE: da --city output\\<nume>_oras")
        return 1
    city_dir = Path(args["city"]).resolve()
    ymaps = sorted(city_dir.glob("*_city.ymap"))
    if not ymaps or not (city_dir / "terrain.npz").is_file():
        print(f"EROARE: lipsesc *_city.ymap sau terrain.npz in {city_dir} (ruleaza generate_city.py)")
        return 1

    setup_sollumz(save_prefs=False)
    # Scena goala, dar cu preferintele pastrate: read_factory_settings ar sterge si biblioteca.
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)

    _terrain, center, extent = build_terrain(city_dir / "terrain.npz", args["margin"])
    before = set(bpy.data.objects)
    bpy.ops.sollumz.import_assets(directory=str(city_dir), files=[{"name": ymaps[0].name}])
    new = [o for o in bpy.data.objects if o not in before]
    with_mesh = sum(1 for o in new if o.type == "MESH" or any(ch.type == "MESH" for ch in o.children_recursive))
    print(f"ymap importat: {len(new)} obiecte noi, {with_mesh} cu geometrie reala din biblioteca")

    setup_view(center, extent)
    blend = city_dir / f"{ymaps[0].stem}.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    print(f"scena salvata: {blend}")
    if args["render"]:
        render(city_dir / "render.png")
    return 0


if __name__ == "__main__":
    code = 1
    try:
        code = main()
    finally:
        sys.stdout.flush()
    sys.exit(code)
