# -*- coding: utf-8 -*-
"""
Exporta scena din Blender direct intr-o resursa FiveM de harta (.ymap, .ytyp, .ydr, .ybn, fxmanifest.lua).

Ce se intampla cu fiecare obiect vizibil din scena:
  - modelele trase din biblioteca "GTA V (generator)" raman referinte la jocul original: in resursa ajung
    doar numele modelului, pozitia, rotatia si scala; geometria si texturile vin din joc;
  - orice alt obiect (mesh-uri facute sau sculptate de tine, generate de scripturi) devine model nou (.ydr),
    cu materialele trecute pe shader-e GTA si texturile convertite in DDS, incorporate in model;
  - coliziunea statica (.ybn) se coace din geometrie, pentru modelele noi si pentru cladirile GTA, care in
    afara locului lor original nu au coliziune.

Cladirile GTA din fisierele .ytyp incarcate la cerere (numele se termina in "_strm") ar aparea doar langa
locul lor original din Los Santos. Exportul le copiaza definitia in .ytyp-ul resursei sub un nume nou
(<resursa>_<model>), care foloseste acelasi model si aceleasi texturi din joc.

In Blender pornit cu BLENDER_EDITOR.bat: bara laterala din viewport (tasta N), tab-ul FiveM. Exportul
ruleaza intr-un Blender separat, pe o copie a scenei, deci scena deschisa nu se modifica.

Fara interfata:
    blender -b oras.blend -P tools\\blender_fivem_export.py -- --name oras_meu [--out <folder resurse>]
        [--offset x,y,z] [--lod 300] [--selected lista.txt] [--no-gta-col] [--result rezultat.json]
"""
import copy
import dataclasses
import glob
import hashlib
import importlib
import importlib.util
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parent.parent
TMP_ROOT = ROOT / "output" / "fivem_export"
YTYP_INDEX = ROOT / "output" / "ytyp_index.json"
MARKER = ".export_blender"          # fisier-semn: resursa a fost scrisa de acest export si poate fi rescrisa

GTA_INFO = "sz_asset_archetype_info"     # pus de Sollumz pe modelele din biblioteca GTA
GTA_OWN_COL = "sz_asset_collisions"      # modelul are coliziune proprie (props)
P_NEW = "fivem_model_nou"                # model GTA exportat totusi ca model nou (de ex. dupa ce l-ai sculptat)
P_NOCOL = "fivem_fara_coliziune"         # obiect fara coliziune (decor)

CELL = 200.0             # metri; fiecare celula are propriul .ymap si propriul .ybn
MAX_COL_TRIS = 6000      # triunghiuri de coliziune per model, dupa simplificare
BIG_MODEL = 10.0         # m; modelele mai mari (cladiri) primesc distanta minima de vizibilitate
# memoria unui model in joc: ~86 octeti pe colt de fata (plaja de 340k colturi = 28 MiB in FiveM); peste 16 MiB
# FiveM avertizeaza ca modelul se poate incarca greu sau deloc
LOOP_BYTES = 86
MAX_MODEL_MIB = 12
MESH_TYPES = {"MESH", "CURVE", "SURFACE", "META", "FONT"}
COL_MATERIAL = "CONCRETE"
# Iarba 3D a jocului (fire, buruieni, flori): GTA o creste singur, langa camera, pe coliziunile cu material de iarba
# si "procedural id" (data/materials/procedural.meta; lista in sollumz ybn/procids.json). Aleasa dupa textura fetei
# (iarba / nisip / pamant) si dupa obiect (padure, camp, teren, restul orasului). Schimbi aici = alta iarba.
COL_V = 2                # intra in amprenta celulelor de coliziune: schimbat = toate .ybn-urile se refac o data
PROC_GRASS = {"padure": ("GRASS_LONG", 159),   # Forest_Grass
              "camp": ("GRASS_LONG", 160),     # Meadow_green_mix
              "teren": ("GRASS", 139),         # MED_AM_Grass_Lush_Med
              "oras": ("GRASS", 148)}          # MED_AM_Grass_Lush_SHORT: gazon, curti, parcuri
PROC_SAND = ("SAND_LOOSE", 142)                # Dunes_Grasses_Plants
PROC_DIRT = ("DIRT_TRACK", 74)                 # City_Weeds_01_SPARSE
GRASS_WORDS = ("grass", "iarba", "gazon", "lawn", "meadow", "wetland")
SAND_WORDS = ("sand", "nisip", "beach")
DIRT_WORDS = ("dirt", "soil", "pamant", "mud")


class ExportError(Exception):
    pass


def progress(f, text):
    """Cat s-a facut (0..1) si etapa, pentru bara din editorul de oras."""
    print(f"PROGRES {f:.3f} {text}", flush=True)


# ------------------------------------------------------------------------------------------ obiecte

def strip_suffix(name: str) -> str:
    return re.sub(r"\.\d{3,}$", "", name)


def safe_name(text: str) -> str:
    """Nume bun pentru fisierele si arhetipurile GTA: litere mici, cifre si _."""
    return re.sub(r"[^a-z0-9_]+", "_", text.lower()).strip("_") or "obiect"


def gta_info(obj):
    """Datele modelului GTA puse de Sollumz pe obiectele din biblioteca; None pentru obiectele tale."""
    for holder in (obj, obj.data, getattr(obj, "instance_collection", None)):
        text = holder.get(GTA_INFO) if holder is not None else None
        if text:
            try:
                return json.loads(text)
            except ValueError:
                return None
    return None


def gta_name(obj) -> str:
    """Numele modelului din joc: din mesh-ul bibliotecii (<model>.mesh), altfel din numele obiectului."""
    data = obj.data
    if data is not None and data.get(GTA_INFO):
        base = strip_suffix(data.name)
        if base.endswith(".mesh"):
            return base[:-5].lower()
    return strip_suffix(obj.name).lower()


def classify(obj):
    """'gta' (referinta la joc), 'nou' (model exportat), 'mlo' (interior GTA, nesuportat) sau None."""
    if obj.type == "EMPTY":
        return "mlo" if obj.instance_type == "COLLECTION" and gta_info(obj) else None
    if obj.type not in MESH_TYPES or obj.get("harta_tip") in ("linie", "previzualizare"):
        return None      # liniile desenate cu tab-ul Harta sunt doar ghidaje; marea din orasele generate e doar de vazut
    if str(getattr(obj, "sollum_type", "")).startswith("sollumz_bound"):
        return None      # coliziuni Sollumz facute de mana
    if gta_info(obj) is not None and not obj.get(P_NEW):
        return "gta"
    return "nou"


def exportable(obj) -> bool:
    """Vizibil in scena, plus obiectele generate ascunse doar pentru ca in joc le-a ascuns /mapeditor (in joc le
    ascunde tot el; raman in harta ca un Ctrl+Z de acolo sa le aduca inapoi). Obiectele puse in joc, aduse de
    tools/import_din_joc.py, nu se exporta: le pune editorul din joc din objects.json."""
    if obj.get("fivem_din_joc") is not None:
        return False
    return obj.visible_get() or bool(obj.get("fivem_ascuns_in_joc"))


def default_resources_dir() -> str:
    try:
        cfg = json.loads((ROOT / "map.json").read_text(encoding="utf-8"))
        if cfg.get("fivem_resources_dir"):
            return cfg["fivem_resources_dir"]
    except (OSError, ValueError):
        pass
    return str(ROOT / "output" / "fivem")


def _load_tool(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def ymap_rotation(rot):
    """Rotatia unei entitati .ymap: cuaternionul invers (w, x, y, z), ca in Sollumz si CodeWalker."""
    q = rot.inverted()
    return [q.w, q.x, q.y, q.z]


def world_extents(bb_min, bb_max, rot, scale):
    """Cutia modelului (scalata si rotita) ca extents aliniate la axe, relative la pozitie."""
    pts = [rot @ Vector((x * scale[0], y * scale[1], z * scale[2]))
           for x in (bb_min[0], bb_max[0]) for y in (bb_min[1], bb_max[1]) for z in (bb_min[2], bb_max[2])]
    return [[min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)]]


def cell_of(pos):
    return (math.floor(pos[0] / CELL), math.floor(pos[1] / CELL))


def unique_name(base: str, used: set) -> str:
    base = base[:56]
    name = base
    k = 2
    while name in used:
        name = f"{base}_{k}"
        k += 1
    used.add(name)
    return name


# ------------------------------------------------------------------------------------------ mesh-uri

def set_materials(me, mats):
    """Inlocuieste materialele mesh-ului pastrand indicii fetelor (materials.clear() i-ar reseta la 0)."""
    if not mats:
        return
    for i, mat in enumerate(mats):
        if i < len(me.materials):
            me.materials[i] = mat
        else:
            me.materials.append(mat)
    while len(me.materials) > len(mats):
        me.materials.pop(index=len(me.materials) - 1)


def model_mesh(obj, scale, name):
    """Geometria finala a obiectului (cu modificatori), cu scala aplicata; rotatia si pozitia raman pe entitate."""
    if obj.type == "MESH" and not obj.modifiers:
        # fara modificatori geometria e chiar obj.data, iar copia e instantanee. Prin depsgraph, fiecare mesh nou
        # facea Blender sa reevalueze toata scena: ~0.2 s pe obiect intr-un oras de 3000 de obiecte
        me = obj.data.copy()
    else:
        depsgraph = bpy.context.evaluated_depsgraph_get()
        me = bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph), preserve_all_data_layers=True,
                                             depsgraph=depsgraph)
    me.name = name
    # materialele legate de obiect (nu de mesh) nu vin singure. Se pun slot cu slot, NU cu materials.clear():
    # in Blender 4 clear() sterge si indicii de material ai fetelor, deci toate fetele ramaneau pe primul slot
    # (geamurile luau textura peretelui, iarba parcului textura trotuarului, marcajele dispareau)
    set_materials(me, [slot.material for slot in obj.material_slots])
    me.transform(Matrix.Diagonal((scale[0], scale[1], scale[2], 1.0)))
    if scale[0] * scale[1] * scale[2] < 0:
        # oglindirea intoarce fetele pe dos
        import bmesh
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
        bm.to_mesh(me)
        bm.free()
    prepare_attributes(me)
    return me


def has_faces(obj) -> bool:
    """Curbele si liniile fara grosime nu au fete: nu se pot exporta ca modele."""
    if obj.type == "MESH" and not obj.modifiers:
        return len(obj.data.polygons) > 0
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = evaluated.to_mesh()
    try:
        return me is not None and len(me.polygons) > 0
    finally:
        evaluated.to_mesh_clear()


def mesh_digest(me) -> str:
    """Amprenta unui model gata de conversie (geometrie, UV, culori, materiale si texturile lor): acelasi model la
    exportul urmator = acelasi .ydr, deci nu se mai converteste (export incremental)."""
    h = hashlib.sha1()
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", co)
    h.update(np.round(co, 3).tobytes())
    for data, attr in ((me.polygons, "loop_total"), (me.polygons, "material_index"), (me.loops, "vertex_index")):
        arr = np.empty(len(data), np.int32)
        data.foreach_get(attr, arr)
        h.update(arr.tobytes())
    for layer in me.uv_layers:
        uv = np.empty(len(me.loops) * 2, np.float32)
        layer.data.foreach_get("uv", uv)
        h.update(np.round(uv, 4).tobytes())
    for ca in getattr(me, "color_attributes", []):
        vals = np.empty(len(ca.data) * 4, np.float32)
        ca.data.foreach_get("color", vals)
        h.update(np.round(vals, 3).tobytes())
    for mat in me.materials:
        h.update((mat.name if mat else "-").encode("utf-8"))
        # si shader-ul: acelasi nume de material cu alt shader (geam stins in loc de geam luminat) = alt .ydr
        props = getattr(mat, "shader_properties", None) if mat is not None else None
        h.update(str(getattr(props, "filename", "")).encode("utf-8"))
        if mat is not None and mat.node_tree:
            for node in mat.node_tree.nodes:
                if node.type == "TEX_IMAGE" and node.image is not None:
                    h.update(f"{node.name}={node.image.name}|{node.image.filepath}".encode("utf-8"))
    return h.hexdigest()


def box_uv(me, size=4.0):
    """UV-uri proiectate pe cutie (o repetare la 4 m), pentru mesh-urile fara UV."""
    uv = me.uv_layers.new(name="UVMap 0")
    if not len(me.polygons):
        return
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    vi = np.empty(len(me.loops), np.int32)
    me.loops.foreach_get("vertex_index", vi)
    normals = np.empty(len(me.polygons) * 3, np.float32)
    me.polygons.foreach_get("normal", normals)
    totals = np.empty(len(me.polygons), np.int32)
    me.polygons.foreach_get("loop_total", totals)
    axis = np.abs(normals.reshape(-1, 3)).argmax(1)[np.repeat(np.arange(len(totals)), totals)]
    p = co[vi]
    u = np.where(axis == 0, p[:, 1], p[:, 0])
    v = np.where(axis == 2, p[:, 1], p[:, 2])
    uv.data.foreach_set("uv", (np.stack([u, v], 1) / size).astype(np.float32).ravel())


def prepare_attributes(me):
    """Straturile pe care Sollumz le cauta dupa nume: "UVMap 0", "UVMap 1"... si "Color 1"."""
    if len(me.uv_layers) == 0:
        box_uv(me)
    layers = list(me.uv_layers)
    for i, layer in enumerate(layers):
        layer.name = f"__uv{i}"
    for i, layer in enumerate(layers):
        layer.name = f"UVMap {i}"
    if "Color 1" not in me.color_attributes:
        attr = me.color_attributes.new(name="Color 1", type="BYTE_COLOR", domain="CORNER")
        attr.data.foreach_set("color_srgb", np.ones(len(me.loops) * 4, dtype=np.float32))


def cluster_mesh(me, name, limit=MAX_COL_TRIS, want_mats=False):
    """Coliziune simplificata prin gruparea varfurilor pe o grila (numpy, milisecunde): ramele, glafurile si
    ornamentele de cativa cm se topesc in perete. Decimate lua ~0.2 s pe cladire si tot ramanea la 15000 de
    triunghiuri, fiindca bucatile separate (ramele) nu se pot reduce. Grila creste pana raman <= limit.
    want_mats: -> (mesh, materialul fiecarei fete noi, din triunghiul original din care vine)."""
    co = np.empty(len(me.vertices) * 3, np.float64)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    tris = np.empty(len(me.loop_triangles) * 3, np.int32)
    me.loop_triangles.foreach_get("vertices", tris)
    tris = tris.reshape(-1, 3).astype(np.int64)
    tri_mat = np.zeros(len(me.loop_triangles), np.int32)
    if want_mats and len(tri_mat):
        me.loop_triangles.foreach_get("material_index", tri_mat)
    lo = co.min(0)
    cell = 0.25
    while True:
        # celula (i, j, k) -> o singura cheie int64: np.unique pe 1D e de zeci de ori mai rapid decat pe randuri
        q = np.floor((co - lo) / cell).astype(np.int64)
        _, inv, counts = np.unique((q[:, 0] << 42) | (q[:, 1] << 21) | q[:, 2], return_inverse=True,
                                   return_counts=True)
        inv = inv.reshape(-1)
        t = inv[tris]
        keep = (t[:, 0] != t[:, 1]) & (t[:, 1] != t[:, 2]) & (t[:, 0] != t[:, 2])
        t, m = t[keep], tri_mat[keep]
        if len(t):
            s = np.sort(t, axis=1)
            n = len(counts)
            _, first = np.unique((s[:, 0] * n + s[:, 1]) * n + s[:, 2], return_index=True)
            order = np.sort(first)
            t, m = t[order], m[order]
        if len(t) <= limit:
            break
        cell *= 1.5       # terenul mare ajunge la celule de cativa metri (grila lui e oricum de 6 m)
    pos = np.zeros((len(counts), 3))
    np.add.at(pos, inv, co)
    pos /= counts[:, None]            # fiecare grup = media varfurilor lui (peretii raman in planul lor)
    used, remap = np.unique(t, return_inverse=True)
    out = bpy.data.meshes.new(name)
    out.from_pydata(pos[used].tolist(), [], remap.reshape(-1, 3).tolist())
    return (out, m) if want_mats else out


def _mat_words(mat):
    words = [mat.name]
    if mat.node_tree:
        words += [n.image.name for n in mat.node_tree.nodes if n.type == "TEX_IMAGE" and n.image is not None]
    return " ".join(words).lower()


def collision_picker(sz):
    """-> pick(obiect, material vizual) = materialul de coliziune al fetelor cu materialul asta: beton, sau iarba /
    nisip / pamant cu iarba 3D a jocului (PROC_*)."""
    cache = {}

    def pick(obj, mat):
        kind = (COL_MATERIAL, 0)
        words = _mat_words(mat) if mat is not None else ""
        if any(w in words for w in GRASS_WORDS):
            n = obj.name.lower()
            kind = PROC_GRASS["padure" if n.startswith("padure") else "camp" if n.startswith("camp")
                              else "teren" if n.startswith("teren") else "oras"]
        elif any(w in words for w in SAND_WORDS):
            kind = PROC_SAND
        elif any(w in words for w in DIRT_WORDS):
            kind = PROC_DIRT
        if kind not in cache:
            if kind[1] == 0:
                cache[kind] = sz.collision_material(kind[0])
            else:
                col = sz.cm.create_collision_material_from_index(sz._col_index.get(kind[0], 0))
                col.collision_properties.procedural_id = kind[1]
                col.name = f"col_{kind[0].lower()}_{kind[1]}"
                cache[kind] = col
        return cache[kind]
    return pick


def local_collision(obj, scale, col_mat, name, base=None):
    """Geometria obiectului cu scala aplicata (fara rotatie si pozitie), simplificata pentru coliziune.
    base = modelul deja facut de model_mesh (scalat si intors, daca era oglindit): se copiaza, nu se reevalueaza."""
    import bmesh
    if base is not None:
        me = base.copy()
    elif obj.type == "MESH" and not obj.modifiers:
        me = obj.data.copy()
    else:
        depsgraph = bpy.context.evaluated_depsgraph_get()
        me = bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph), depsgraph=depsgraph)
    me.name = name
    if base is None:
        me.transform(Matrix.Diagonal((scale[0], scale[1], scale[2], 1.0)))
        if scale[0] * scale[1] * scale[2] < 0:
            bm = bmesh.new()
            bm.from_mesh(me)
            bmesh.ops.reverse_faces(bm, faces=bm.faces)
            bm.to_mesh(me)
            bm.free()
    me.calc_loop_triangles()
    # parcurile cer coliziunea exacta: simplificata, suprafata lor netezita pe deal devenea cu trepte
    limit = int(obj.get("fivem_col_max") or MAX_COL_TRIS)
    src = list(me.materials)
    # peste 32767 de varfuri pe BVH nu mai e o problema: split_collision taie coliziunea in bucati
    if len(me.loop_triangles) > limit:
        # mesh-urile mari (cladirile generate: 40-50 mii de triunghiuri): grupare pe grila, fara bmesh/Decimate
        small, face_src = cluster_mesh(me, name, want_mats=True)
        bpy.data.meshes.remove(me)
        me = small
    else:
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.02)
        # fara dissolve_limit: pe mesh-urile dese ale cladirilor GTA ruleaza zeci de minute
        bmesh.ops.triangulate(bm, faces=bm.faces)
        bm.to_mesh(me)
        bm.free()
        face_src = np.zeros(len(me.polygons), np.int32)
        if len(me.polygons):
            me.polygons.foreach_get("material_index", face_src)
    # materialul de coliziune al fiecarei fete, dupa materialul ei vizual (col_mat(obiect, material) = iarba 3D pe
    # iarba, vezi collision_picker); un material de coliziune dat direct = acelasi pe tot
    picks = [col_mat(obj, s) for s in src] if callable(col_mat) else [col_mat] * len(src)
    if not picks:
        picks = [col_mat(obj, None) if callable(col_mat) else col_mat]
    uniq = list(dict.fromkeys(picks))
    idx = np.array([uniq.index(p) for p in picks], dtype=np.int32)
    me.materials.clear()
    for mat in uniq:
        me.materials.append(mat)
    if len(me.polygons):
        me.polygons.foreach_set("material_index", idx[np.clip(face_src, 0, len(idx) - 1)].astype(np.int32))
    return me


MAX_BVH_TRIS = 30000     # un BVH din .ybn primeste cel mult 32767 de primitive


def split_collision(me):
    """Mesh-ul de coliziune in bucati de cel mult MAX_BVH_TRIS triunghiuri, taiate pe axa cea mai lunga (fiecare
    bucata devine un BVH al compozitului). Parcurile cu coliziune exacta trec de limita."""
    me.calc_loop_triangles()
    n = len(me.loop_triangles)
    if n <= MAX_BVH_TRIS:
        return [me]
    co = np.empty(len(me.vertices) * 3, np.float64)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    tris = np.empty(n * 3, np.int64)
    me.loop_triangles.foreach_get("vertices", tris)
    tris = tris.reshape(-1, 3)
    tri_mat = np.empty(n, np.int32)
    me.loop_triangles.foreach_get("material_index", tri_mat)
    centers = co[tris].mean(axis=1)
    axis = int(np.argmax(np.ptp(centers[:, :2], axis=0)))
    order = np.argsort(centers[:, axis], kind="stable")
    parts = []
    for k, chunk in enumerate(np.array_split(order, -(-n // MAX_BVH_TRIS))):
        t = tris[chunk]
        used, remap = np.unique(t, return_inverse=True)
        out = bpy.data.meshes.new(f"{me.name}_{k}")
        out.from_pydata(co[used].tolist(), [], remap.reshape(-1, 3).tolist())
        for mat in me.materials:
            out.materials.append(mat)
        # materialul fiecarui triunghi (iarba / beton) ramane si pe bucati
        out.polygons.foreach_set("material_index", tri_mat[chunk])
        parts.append(out)
    bpy.data.meshes.remove(me)
    return parts


def placed_collision(local, pos, rot, name):
    """Copia coliziunii locale mutata in coordonate mondiale (asa o cere .ybn-ul static)."""
    me = local.copy()
    me.name = name
    me.transform(Matrix.Translation(pos) @ rot.to_matrix().to_4x4())
    return me


def mesh_bounds(me):
    if not len(me.vertices):
        return Vector((0.0, 0.0, 0.0)), Vector((0.0, 0.0, 0.0))
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    return Vector(co.min(0).tolist()), Vector(co.max(0).tolist())


# ------------------------------------------------------------------------------------------ materiale

def _srgb(c: float) -> float:
    c = min(max(c, 0.0), 1.0)
    return c * 12.92 if c <= 0.0031308 else 1.055 * c ** (1.0 / 2.4) - 0.055


def _pow2(v: int) -> int:
    return int(min(2048, max(4, 2 ** round(math.log2(max(v, 1))))))


def base_color(mat):
    """Culoarea de baza a unui material Blender obisnuit (None daca vine dintr-o textura)."""
    if mat.node_tree:
        for node in mat.node_tree.nodes:
            if node.type == "BSDF_PRINCIPLED":
                socket = node.inputs.get("Base Color")
                if socket is not None and not socket.is_linked:
                    return tuple(socket.default_value)
                return None
    return tuple(mat.diffuse_color)


class Materials:
    """Trece materialele modelelor noi pe shader-e GTA si pregateste texturile (DDS incorporate in .ydr)."""

    def __init__(self, sz, pkg, tex_dir: Path, warnings: list):
        from dayzgen.dds_writer import write_dds
        self.sz = sz
        self.write_dds = write_dds
        self.converter = importlib.import_module(f"{pkg}.ydr.operators.materials").MaterialConverter
        self.pkg = pkg
        self.shared = {}     # nume textura -> imagine: toate merg intr-un singur .ytd, nu copiate in fiecare .ydr
        self.tex_dir = tex_dir
        self.warnings = warnings
        self.images = {}
        self.tex_names = set()
        self.default = None
        tex_dir.mkdir(parents=True, exist_ok=True)

    def convert_all(self, meshes):
        # materialele originale ale fiecarui mesh, dupa nume: conversia Sollumz poate inlocui originalul
        slots = {me.name: [m.name if m else None for m in me.materials] for me in meshes}
        mapping = {}
        for name in sorted({n for names in slots.values() for n in names if n}):
            mapping[name] = self.convert(bpy.data.materials[name])
        for me in meshes:
            names = slots[me.name] or [None]
            # slot cu slot, nu clear(): clear() reseteaza indicii de material ai fetelor
            set_materials(me, [mapping[name] if name else self.default_material() for name in names])

    def convert(self, mat):
        if mat.sollum_type != "sollumz_material_shader":
            color = base_color(mat)
            holder = bpy.data.objects.new("_material", bpy.data.meshes.new("_material"))
            bpy.context.scene.collection.objects.link(holder)
            holder.data.materials.append(mat)
            try:
                new = self.converter(holder, mat).auto_convert()
            except Exception as error:
                self.warnings.append(f"materialul {mat.name} nu s-a putut converti ({error}); pun default.sps")
                new = None
            if new is None:
                new = self.sz.sm.create_shader("default.sps")
            bpy.data.objects.remove(holder)
            self.fill_empty_diffuse(new, color)
            mat = new
        self.prepare_textures(mat)
        return mat

    def default_material(self):
        if self.default is None:
            self.default = self.sz.sm.create_shader("default.sps")
            self.default.name = "fivem_default"
            self.fill_empty_diffuse(self.default, (0.5, 0.5, 0.5, 1.0))
            self.prepare_textures(self.default)
        return self.default

    def fill_empty_diffuse(self, mat, color):
        node = mat.node_tree.nodes.get("DiffuseSampler") if mat.node_tree else None
        if node is not None and getattr(node, "image", None) is None:
            node.image = self.color_image(color or (0.5, 0.5, 0.5, 1.0))

    def prepare_textures(self, mat):
        if not mat.node_tree:
            return
        for node in mat.node_tree.nodes:
            if node.type == "TEX_IMAGE" and node.image is not None:
                node.image = self.dds_image(node.image)
                node.texture_properties.embedded = False
                tname = node.sollumz_texture_name
                if not tname:
                    continue
                old = self.shared.setdefault(tname, node.image)
                if old is not node.image:
                    self.warnings.append(f"doua texturi diferite se numesc {tname}; ramane {old.name}")

    def write_ytd(self, out_dir: Path, ytd_name: str, targets):
        """Texturile tuturor modelelor noi intr-un singur .ytd. Inainte fiecare .ydr isi ducea copia lui (1-2 MB
        pe cladire): resursa era de zeci de ori mai mare si jocul incarca cladirile greu."""
        if not self.shared:
            return 0
        from szio.gta5 import AssetTextureDictionary, EmbeddedTexture, save_asset
        extract = importlib.import_module(f"{self.pkg}.ytd.ytdexport").extract_texture_dds_data_source
        textures = {}
        for tname, img in sorted(self.shared.items()):
            w, h = img.size
            textures[tname] = EmbeddedTexture(tname, w, h, extract(img, tname))
        save_asset(AssetTextureDictionary(textures=textures), targets, out_dir, ytd_name)
        return len(textures)

    def _tex_name(self, base: str) -> str:
        return unique_name(safe_name(base)[:40], self.tex_names)

    def color_image(self, color):
        rgb = tuple(int(round(_srgb(c) * 255)) for c in color[:3])
        name = "fivem_%02x%02x%02x" % rgb
        if name in self.images:
            return self.images[name]
        pixels = np.empty((8, 8, 4), np.float32)
        pixels[:] = [c / 255.0 for c in rgb] + [1.0]
        path = self.tex_dir / f"{name}.dds"
        self.write_dds(str(path), pixels, "DXT1")
        img = bpy.data.images.load(str(path), check_existing=False)
        img.name = name
        self.images[name] = img
        return img

    def dds_image(self, img):
        if img.name in self.images:
            return self.images[img.name]
        packed = img.packed_file
        path = Path(bpy.path.abspath(img.filepath)) if img.filepath else None
        if packed is not None:
            is_dds = packed.data[:4] == b"DDS "
        else:
            is_dds = path is not None and path.suffix.lower() == ".dds" and path.is_file()
        out = img if is_dds else self.convert_image(img)
        self.images[img.name] = out
        return out

    def convert_image(self, img):
        """PNG/JPG/generata -> DDS (DXT1, sau DXT5 daca are transparenta), latura putere a lui 2."""
        w, h = img.size
        if w == 0 or h == 0:
            self.warnings.append(f"textura {img.name} nu se poate citi; pun gri")
            return self.color_image((0.5, 0.5, 0.5, 1.0))
        nw, nh = _pow2(w), _pow2(h)
        src = img
        if (nw, nh) != (w, h):
            src = img.copy()
            src.scale(nw, nh)
        pixels = np.empty(nw * nh * 4, np.float32)
        src.pixels.foreach_get(pixels)
        if src is not img:
            bpy.data.images.remove(src)
        rgba = pixels.reshape(nh, nw, 4)[::-1]       # Blender tine randurile de jos in sus
        if img.is_float and img.colorspace_settings.name not in ("Non-Color", "Raw"):
            rgba = np.concatenate([np.vectorize(_srgb)(rgba[..., :3]), rgba[..., 3:]], axis=-1)
        alpha = img.alpha_mode != "NONE" and float(rgba[..., 3].min()) < 0.99
        name = self._tex_name(Path(img.name).stem)
        path = self.tex_dir / f"{name}.dds"
        self.write_dds(str(path), np.ascontiguousarray(rgba), "DXT5" if alpha else "DXT1")
        out = bpy.data.images.load(str(path), check_existing=False)
        out.name = name
        if img.colorspace_settings.name in ("Non-Color", "Raw"):
            out.colorspace_settings.name = "Non-Color"
        return out


# ------------------------------------------------------------------------------------------ arhetipuri GTA

def _arch_hash(name: str) -> int:
    from szio.jenkhash import name_to_hash
    low = name.lower()
    if low.startswith("hash_"):
        try:
            return int(low[5:], 16)
        except ValueError:
            pass
    return name_to_hash(low)


def _clone(obj, **changes):
    if dataclasses.is_dataclass(obj):
        return dataclasses.replace(obj, **changes)
    new = copy.copy(obj)
    for key, value in changes.items():
        setattr(new, key, value)
    return new


def ytyp_locations(game: str, wanted: list, log) -> dict:
    """Unde sunt fisierele .ytyp cerute in arhivele jocului: {nume: [arhiva, arhive imbricate..., fisier]}.
    Indexul se construieste o singura data (output/ytyp_index.json); DLC-urile se cauta doar la nevoie."""
    cache = {}
    if YTYP_INDEX.is_file():
        try:
            cache = json.loads(YTYP_INDEX.read_text(encoding="utf-8"))
        except ValueError:
            cache = {}
    if cache.get("game") != game:
        cache = {"game": game, "files": {}, "scanned": []}
    groups = [
        ("baza", sorted(glob.glob(os.path.join(game, "x64*.rpf"))) + [os.path.join(game, "update", "update.rpf")]),
        ("dlc", sorted(glob.glob(os.path.join(game, "update", "x64", "dlcpacks", "*", "dlc*.rpf")))),
    ]
    for group, tops in groups:
        if group in cache["scanned"] or all(n in cache["files"] for n in wanted):
            continue
        log(f"  caut fisierele .ytyp in arhivele jocului ({group}; doar prima data)...")
        cg = _load_tool("catalog_from_game")
        from szio import rpf
        for top in tops:
            if not os.path.isfile(top):
                continue
            try:
                archive = rpf.open_rpf(top)
            except Exception:
                continue
            for parts, path in cg.iter_ytyp(archive, []):
                cache["files"][Path(path).stem.lower()] = [top, *parts, path]
        cache["scanned"].append(group)
        YTYP_INDEX.parent.mkdir(parents=True, exist_ok=True)
        YTYP_INDEX.write_text(json.dumps(cache), encoding="utf-8")
    return {n: cache["files"].get(n) for n in wanted}


def vanilla_copies(refs, prefix: str, lod_min: float, log, warnings: list) -> dict:
    """{model: arhetip copiat cu numele <prefix>_<model>} pentru modelele din .ytyp-uri incarcate la cerere."""
    want = {}
    for name, info in refs:
        ytyp = str(info.get("ytyp") or "").lower()
        if ytyp.endswith("_strm") and info.get("type") != "MLO":
            want.setdefault(ytyp, {})[_arch_hash(name)] = name
    if not want:
        return {}
    game = _load_tool("catalog_from_game").gta_dir([])
    if not game or not os.path.isdir(game):
        warnings.append("nu gasesc GTA V (CitizenFX.ini): cladirile GTA se vad doar langa locul lor original")
        return {}
    import szio
    from szio import vfs
    from szio.gta5 import ArchetypeAssetType
    where = ytyp_locations(game, sorted(want), log)
    copies = {}
    for ytyp, names in want.items():
        types = None
        if where.get(ytyp):
            try:
                types = szio.try_load_asset(vfs.VPath(*where[ytyp]))
            except Exception:
                types = None
        if types is None or not hasattr(types, "archetypes"):
            warnings.append(f"nu pot citi {ytyp}.ytyp din joc: {len(names)} modele se vad doar langa locul original")
            continue
        for arch in types.archetypes:
            key = _arch_hash(arch.name)
            name = names.get(key)
            if name is None:
                continue
            if arch.asset_type not in (ArchetypeAssetType.DRAWABLE, ArchetypeAssetType.FRAGMENT):
                warnings.append(f"{name}: model din dictionar .ydd, se vede doar langa locul lui original")
                continue
            asset = arch.asset_name or name
            if asset.lower().startswith("hash_") and _arch_hash(asset) == key:
                asset = name
            big = max(arch.bb_max[i] - arch.bb_min[i] for i in range(3)) >= BIG_MODEL
            lod = max(float(arch.lod_dist), lod_min) if big else float(arch.lod_dist)
            copies[name] = _clone(arch, name=f"{prefix}_{name}", lod_dist=lod, asset_name=asset)
    return copies


def has_own_collision(obj, arch) -> bool:
    if arch is not None and getattr(arch, "physics_dictionary", ""):
        return True
    return any(holder is not None and holder.get(GTA_OWN_COL) for holder in (obj, obj.data))


def custom_archetype(name, lo, hi, lod, txd=""):
    from szio.gta5 import Archetype, ArchetypeAssetType, ArchetypeType
    return Archetype(
        name=name, type=ArchetypeType.BASE, flags=32, lod_dist=float(lod), special_attribute=0,
        hd_texture_dist=60.0, texture_dictionary=txd, clip_dictionary="", drawable_dictionary="",
        physics_dictionary="", bb_min=lo, bb_max=hi, bs_center=(lo + hi) * 0.5,
        bs_radius=float((hi - lo).length * 0.5), asset_name=name, asset_type=ArchetypeAssetType.DRAWABLE,
        extensions=[],
    )


def write_minimap(info_text, res_dir: Path, name: str, offset, log, warnings):
    """Harta de sus scrisa de gen_oras.py (proprietatea fivem_minimap a scenei), ca overlay pe radar si pe harta
    mare: minimap/<nume>_minimap.gfx + client/minimap.js. Intoarce calea .gfx-ului in resursa, sau None."""
    try:
        info = json.loads(info_text)
    except (TypeError, ValueError):
        return None
    png = Path(info.get("png", ""))
    if not png.is_file():
        warnings.append(f"harta pentru minimap lipseste ({png}); genereaza orasul din nou")
        return None
    loader_src = Path(__file__).resolve().parent / "oras" / "minimap_loader.gfx"
    if not loader_src.is_file():
        warnings.append(f"lipseste {loader_src}: orasul nu apare pe minimap")
        return None
    from dayzgen import gta_export as GX
    from dayzgen.dds_writer import write_dds
    from szio.gta5 import AssetTextureDictionary, EmbeddedTexture, save_asset
    from szio.types import DataSource
    img = bpy.data.images.load(str(png), check_existing=False)
    w, h = img.size
    pixels = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(pixels)
    bpy.data.images.remove(img)
    # Metoda care merge in joc: harta ca textura intr-un .ytd (DXT5, marea transparenta), pusa pe radar de un
    # incarcator Scaleform cu ActionScript (MINIMAP_LOADER.gfx din resursa "Extra Map Tiles", L1CKS / Lughworks).
    # Un .swf scris de noi cu imaginea inauntru se incarca, dar jocul nu il deseneaza (testat).
    for old in list(res_dir.glob("*_minimap*.gfx")) + [res_dir / "minimap"]:
        if old.is_dir():
            shutil.rmtree(old)
        elif old.is_file():
            old.unlink()
    tex = f"{name}_map"
    dds = TMP_ROOT / name / f"{tex}.dds"
    dds.parent.mkdir(parents=True, exist_ok=True)
    write_dds(str(dds), np.ascontiguousarray(pixels.reshape(h, w, 4)[::-1]), "DXT5")
    save_asset(AssetTextureDictionary(textures={tex: EmbeddedTexture(tex, w, h, DataSource.create(str(dds), tex + ".dds"))}),
               GX._targets(False), res_dir / "stream", tex)
    rel = f"{name}_loader.gfx"
    shutil.copy2(loader_src, res_dir / rel)
    west = float(info["x0"]) + offset.x
    size = float(info["size"])
    north = float(info["y0"]) + offset.y + size
    (res_dir / "client").mkdir(exist_ok=True)
    (res_dir / "client" / "minimap.js").write_text(GX.minimap_loader_script(name, rel, tex, west, north, size),
                                                   encoding="utf-8")
    log(f"  minimap: stream/{tex}.ytd + {rel} + client/minimap.js")
    return rel


def write_gps(net_text, res_dir: Path, offset, log) -> bool:
    """Reteaua de strazi scrisa de gen_oras.py (proprietatea fivem_drumuri a scenei), in coordonatele jocului, pusa
    in client/gps.js (tools/oras/gps_client.js): traseu GPS pe strazile orasului pana la waypoint."""
    try:
        net = json.loads(net_text)
    except (TypeError, ValueError):
        return False
    src = Path(__file__).resolve().parent / "oras" / "gps_client.js"
    if not net.get("r") or not src.is_file():
        return False

    def game(p):
        return [round(p[0] + offset.x, 1), round(p[1] + offset.y, 1), round(p[2] + offset.z, 1)]

    net = {"j": {k: game(p) for k, p in net["j"].items()}, "r": [[a, b, [game(p) for p in pts]] for a, b, pts in net["r"]]}
    (res_dir / "client").mkdir(exist_ok=True)
    (res_dir / "client" / "gps.js").write_text(
        src.read_text(encoding="utf-8").replace("/*NET*/null", json.dumps(net, separators=(",", ":"))), encoding="utf-8")
    log(f"  GPS: client/gps.js ({len(net['r'])} strazi, {len(net['j'])} intersectii)")
    return True


WATER_SRC = ROOT / "output" / "gta_water.xml"    # water.xml-ul jocului (tools/gta_water.py il scoate din common.rpf)
WATER_AREA = (-4000.0, 4500.0, -4000.0, 8000.0)  # doar aici accepta FiveM apa noua (SetWaterAreaClipRect nu se mareste)
WATER_JS = """// Lacurile si raurile orasului (apa la nivelul solului): water.xml = apa jocului + ele, scris de exportul din
// Blender. LoadWaterFromPath inlocuieste apa jocului cu fisierul; ResetWater o pune la loc cand harta se opreste.
const RES = GetCurrentResourceName();
setTimeout(() => {
    if (!LoadWaterFromPath(RES, 'water.xml')) console.log(`[${RES}] water.xml nu s-a incarcat`);
}, 0);
on('onClientResourceStop', (res) => {
    if (res === RES) ResetWater();
});
"""


def lake_rects(poly, step=2.0, pad=2.0, tol=4.0):
    """Poligonul unui lac ca dreptunghiuri aliniate la axe (quad-urile de apa ale jocului): randuri de `step` m, cu
    bucatile dintre marginile poligonului marite cu `pad` m (se ascund sub mal), pe grila de `step` m. Randurile
    care difera cu cel mult `tol` m se unesc (bucata mai lata intra tot sub mal): mai putine quad-uri."""
    lo, hi = (lambda v: math.floor(v / step) * step), (lambda v: math.ceil(v / step) * step)
    ymin, ymax = min(p[1] for p in poly), max(p[1] for p in poly)
    rects, cur = [], None       # cur = [y0, y1, [(x0, x1), ...]]

    def close():
        if cur:
            rects.extend((a, b, cur[0], cur[1]) for a, b in cur[2])
    def row_x(yc):
        yc = min(max(yc, ymin + 1e-3), ymax - 1e-3)
        return sorted(ax + (yc - ay) * (bx - ax) / (by - ay)
                      for (ax, ay), (bx, by) in zip(poly, poly[1:] + poly[:1]) if (ay > yc) != (by > yc))
    y = lo(ymin - pad)
    while y < ymax + pad:
        # marginile randului si mijlocul lui: la varfuri si pe laturile oblice conteaza bucata cea mai lata
        mid = row_x(y + step / 2)
        cuts = [c for c in (row_x(y + 0.01), mid, row_x(y + step - 0.01)) if len(c) == len(mid)]
        spans = [(lo(min(c[i] for c in cuts) - pad), hi(max(c[i + 1] for c in cuts) + pad))
                 for i in range(0, len(mid) - 1, 2)]
        if cur and len(cur[2]) == len(spans) and all(abs(a - c) <= tol and abs(b - d) <= tol
                                                     for (a, b), (c, d) in zip(cur[2], spans)):
            cur[1] = y + step
            cur[2] = [(min(a, c), max(b, d)) for (a, b), (c, d) in zip(cur[2], spans)]
        else:
            close()
            cur = [y, y + step, spans] if spans else None
        y += step
    close()
    return rects


def cut_rect(q, r):
    """Quad-ul q (x0, x1, y0, y1) fara dreptunghiul r: pana la 4 bucati."""
    x0, x1, y0, y1 = q
    rx0, rx1, ry0, ry1 = r
    if rx0 >= x1 or rx1 <= x0 or ry0 >= y1 or ry1 <= y0:
        return [q]
    out = [p for p in ((x0, rx0, y0, y1), (rx1, x1, y0, y1)) if p[1] > p[0]]
    mx0, mx1 = max(x0, rx0), min(x1, rx1)
    out += [p for p in ((mx0, mx1, y0, ry0), (mx0, mx1, ry1, y1)) if p[3] > p[2]]
    return out


def write_water(lakes_text, res_dir: Path, offset, log, warnings) -> bool:
    """Lacurile / raurile orasului (proprietatea fivem_apa a scenei, de la gen_oras.py: apa la nivelul solului) in
    water.xml-ul resursei: apa jocului cu o gaura sub fiecare lac, plus quad-urile lacurilor la inaltimea lor. Fara
    lacuri, fisierele de data trecuta se sterg (harta ramane cu apa jocului)."""
    import xml.etree.ElementTree as ET
    target, js = res_dir / "water.xml", res_dir / "client" / "water.js"

    def none():
        target.unlink(missing_ok=True)
        js.unlink(missing_ok=True)
        return False
    try:
        lakes = json.loads(lakes_text) if lakes_text else []
    except (TypeError, ValueError):
        lakes = []
    if not lakes:
        return none()
    if not WATER_SRC.is_file():
        try:
            import gta_water        # tools/ e in sys.path (run_export)
            gta_water.extract()
        except Exception as error:  # noqa: BLE001
            warnings.append(f"lacurile nu intra in joc: nu am water.xml-ul jocului ({error}); ruleaza tools/gta_water.py")
            return none()
    tree = ET.parse(WATER_SRC)
    quads = tree.getroot().find("WaterQuads")
    new, holes = [], []
    for lake in lakes:
        rects = lake_rects([(p[0] + offset.x, p[1] + offset.y) for p in lake["poligon"]])
        if not rects:
            continue
        bx0, bx1 = min(r[0] for r in rects), max(r[1] for r in rects)
        by0, by1 = min(r[2] for r in rects), max(r[3] for r in rects)
        if bx0 < WATER_AREA[0] or bx1 > WATER_AREA[1] or by0 < WATER_AREA[2] or by1 > WATER_AREA[3]:
            warnings.append("un lac e in afara zonei in care jocul accepta apa noua (x -4000..4500, y -4000..8000): "
                            "acolo apa ramane marea. Muta orasul (editorul de oras, In joc: x, y)")
            continue
        # gaura din apa jocului: pe grila de 8 m a quad-urilor originale, sub oras (nu se vede)
        holes.append((8 * math.floor(bx0 / 8), 8 * math.ceil(bx1 / 8), 8 * math.floor(by0 / 8), 8 * math.ceil(by1 / 8)))
        new += [(r, float(lake["z"]) + offset.z) for r in rects]
    if not new:
        return none()

    def item(src, r, z=None):
        it = copy.deepcopy(src)
        for tag, v in zip(("minX", "maxX", "minY", "maxY"), r):
            it.find(tag).set("value", str(int(round(v))))
        if z is not None:
            it.find("z").set("value", f"{z:.3f}")
            it.find("Type").set("value", "0")
        return it
    kept = []
    for it in list(quads):
        box = tuple(float(it.find(t).get("value")) for t in ("minX", "maxX", "minY", "maxY"))
        pieces = [box]
        for h in holes:
            pieces = [p for q in pieces for p in cut_rect(q, h)]
        kept += [it] if pieces == [box] else [item(it, p) for p in pieces]
    template = quads[0]
    quads[:] = kept + [item(template, r, z) for r, z in new]
    tree.write(target, encoding="UTF-8", xml_declaration=True)
    js.parent.mkdir(exist_ok=True)
    js.write_text(WATER_JS, encoding="utf-8")
    log(f"  apa: water.xml ({len(holes)} lacuri, {len(new)} quad-uri de lac, {len(quads)} in total) + client/water.js")
    return True


# ------------------------------------------------------------------------------------------ export

def run_export(opts: dict, log=print) -> dict:
    started = time.time()
    warnings = []
    for path in (ROOT / "tools", ROOT):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    from _sollumz_setup import setup_sollumz
    pkg = setup_sollumz(save_prefs=False)
    from dayzgen import gta_export as GX
    from dayzgen.blender_build import DEFAULT_FLAGS1, DEFAULT_FLAGS2, SollumzAPI
    sz = SollumzAPI(log)

    name = safe_name(opts["name"])
    res_dir = Path(opts["out"]) / name
    if res_dir.is_dir() and any(res_dir.iterdir()) and not (res_dir / MARKER).is_file():
        raise ExportError(f"{res_dir} exista si nu a fost scris de acest export; alege alt nume de resursa")
    offset = Vector(opts["offset"])
    lod = float(opts["lod"])
    scene = bpy.context.scene
    # export incremental: editor/export_cache.json tine amprenta fiecarui model (.ydr) si a fiecarei celule de
    # coliziune (.ybn); ce nu s-a schimbat de data trecuta ramane cum e in stream/ si nu se mai converteste
    stream = res_dir / "stream"
    cache_path = res_dir / "editor" / "export_cache.json"
    code = hashlib.sha1(SCRIPT.read_bytes() + (SCRIPT.parent / "tex_overrides.py").read_bytes()).hexdigest()
    try:
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cache = {}
    inc = (not opts.get("full") and opts.get("selected") is None and cache.get("code") == code
           and cache.get("offset") == [round(v, 3) for v in offset] and stream.is_dir())
    if not inc:
        cache = {}
    log("  export " + ("incremental: refac doar modelele si coliziunile schimbate" if inc else "complet"))
    # texturile schimbate din editorul din joc (editor/overrides.json), pe obiectele lor, inainte de conversie
    import tex_overrides as TXO
    n_tex = TXO.apply(scene, name, TXO.load(res_dir), offset, log)
    if n_tex:
        log(f"  texturi schimbate in editor: {n_tex} roluri")

    objs = [o for o in scene.objects if exportable(o)]
    if opts.get("selected") is not None:
        chosen = set(opts["selected"])
        objs = [o for o in objs if o.name in chosen]
    kinds = {o.name: classify(o) for o in objs}
    refs = [o for o in objs if kinds[o.name] == "gta"]
    news = [o for o in objs if kinds[o.name] == "nou"]
    faceless = [o.name for o in news if not has_faces(o)]
    if faceless:
        news = [o for o in news if o.name not in faceless]
        log(f"  {len(faceless)} obiecte fara fete (curbe, linii) nu se exporta")
    mlo = [o.name for o in objs if kinds[o.name] == "mlo"]
    if mlo:
        warnings.append(f"interioarele GTA (MLO) nu se exporta inca: {', '.join(mlo[:5])}")
    if not refs and not news:
        raise ExportError("nu am gasit obiecte de exportat (se exporta doar obiectele vizibile)")
    log(f"  {len(refs)} obiecte GTA, {len(news)} obiecte proprii")
    progress(0.02, "obiecte GTA")

    ref_data = [(gta_name(o), gta_info(o)) for o in refs]
    copies = vanilla_copies(ref_data, name, lod, log, warnings)
    if copies:
        log(f"  {len(copies)} modele GTA copiate in .ytyp-ul resursei (vizibile oriunde pe harta)")

    col_mat = collision_picker(sz)      # beton, sau iarba / nisip / pamant cu iarba 3D a jocului
    entities = {}       # celula -> entitati pentru write_ymap
    collisions = {}     # celula -> mesh-uri de coliziune in coordonate mondiale
    col_local = {}      # (model, scala) -> coliziune locala simplificata
    guids = set()
    editor_list = []    # editor/entities.json: map editorul din joc recunoaste (ascunde, muta) obiectele
    surfaces = {}       # editor/suprafete.json: triunghiurile pe roluri ale suprafetelor si cladirilor (guid -> rol)

    def add_entity(obj, archetype, pos, rot, scale_xy, scale_z, lod_dist, extents):
        guid = GX._guid(f"{name}/{obj.name}")
        while guid in guids:
            guid = (guid + 1) & 0x7FFFFFFF or 1
        guids.add(guid)
        coll_name = obj.users_collection[0].name if obj.users_collection else ""
        entities.setdefault(cell_of(pos), []).append({
            "archetype": archetype, "pos": list(pos), "rot": ymap_rotation(rot),
            "scale": [scale_xy, scale_z], "lod": float(lod_dist), "bb": extents, "guid": guid,
        })
        editor_list.append({"guid": guid, "model": str(archetype).lower(), "x": round(pos[0], 3),
                            "y": round(pos[1], 3), "z": round(pos[2], 3),
                            "rz": round(math.degrees(rot.to_euler().z), 2), "lod": round(float(lod_dist), 1),
                            "kind": str(obj.get("harta_tip") or ""),
                            # grupul din generator ("Parc 2") sau colectia din Blender ("Strazi", "Teren")
                            "cat": coll_name,
                            # cutia fata de pozitie: casele si copacii din ymap nu sunt entitati de script, deci
                            # editorul le recunoaste dupa punctul atins de click, in cutia lor
                            "bb": [[round(v, 2) for v in extents[0]], [round(v, 2) for v in extents[1]]],
                            "grup": str(obj.get("harta_grup") or coll_name),
                            # rolurile materialelor (iarba, alei, perete...): textura, normal map, shader, scala
                            "mats": TXO.mats_info(obj) if obj.get("harta_tip") else []})
        if obj.get("harta_tip") in TXO.SURF_KINDS:
            surfaces[str(guid)] = TXO.tris_info(obj, offset, obj.get("harta_tip"))

    col_items = {}      # celula -> [(amprenta, obiect, cheie, scala, pozitie, rotatie, mesh de baza)]

    def add_collision(obj, key, scale, pos, rot, base=None, sig=""):
        """Tine minte coliziunea obiectului; se coace mai jos, doar in celulele schimbate de la exportul trecut."""
        if obj.get(P_NOCOL):
            return False
        mark = [sig or str(key[0]), [round(v, 3) for v in scale], [round(v, 3) for v in pos],
                [round(v, 5) for v in rot], obj.get("fivem_col_max")]
        col_items.setdefault(cell_of(pos), []).append((mark, obj, key, scale, pos, rot, base))
        return True

    n_col_gta = 0
    for k, (obj, (arch, info)) in enumerate(zip(refs, ref_data)):
        loc, rot, scale = obj.matrix_world.decompose()
        pos = loc + offset
        sxy, sz_ = abs(scale.x), abs(scale.z)
        if abs(abs(scale.x) - abs(scale.y)) > 1e-3 * max(1.0, sxy):
            warnings.append(f"{obj.name}: GTA are aceeasi scala pe X si Y; folosesc X ({scale.x:.3f})")
        if scale.x < 0 or scale.y < 0 or scale.z < 0:
            warnings.append(f"{obj.name}: oglindirea (scala negativa) nu exista in GTA; o ignor")
        arch_copy = copies.get(arch)
        bb_min, bb_max = info.get("bb_min") or (0, 0, 0), info.get("bb_max") or (0, 0, 0)
        big = max(bb_max[i] - bb_min[i] for i in range(3)) >= BIG_MODEL
        lod_dist = float(arch_copy.lod_dist) if arch_copy else float(info.get("lod_dist") or 100.0)
        if big:
            lod_dist = max(lod_dist, lod)
        add_entity(obj, arch_copy.name if arch_copy else arch, pos, rot, sxy, sz_, lod_dist,
                   world_extents(bb_min, bb_max, rot, (sxy, sxy, sz_)))
        if opts["gta_col"] and not has_own_collision(obj, arch_copy):
            skey = (arch, round(sxy, 4), round(sz_, 4))
            n_col_gta += add_collision(obj, skey, (sxy, sxy, sz_), pos, rot)
        if (k + 1) % 100 == 0:
            log(f"  GTA: {k + 1}/{len(refs)}")
            progress(0.02 + 0.08 * (k + 1) / len(refs), f"obiecte GTA {k + 1} din {len(refs)}")

    groups = {}
    used = set()
    for k, obj in enumerate(news):
        if k % 25 == 0:
            progress(0.1 + 0.2 * k / len(news), f"modele proprii {k} din {len(news)}")
        loc, rot, scale = obj.matrix_world.decompose()
        skey = tuple(round(s, 4) for s in scale)
        # obiectele care impart acelasi mesh (Alt+D), fara modificatori si cu aceeasi scala, impart modelul
        key = (obj.data.name, skey) if obj.type == "MESH" and not obj.modifiers else (obj.name, skey)
        group = groups.get(key)
        if group is None:
            arch = unique_name(f"{name}_{safe_name(strip_suffix(obj.name))}", used)
            me = model_mesh(obj, scale, f"{arch}.mesh")
            mib = len(me.loops) * LOOP_BYTES / 2 ** 20
            if mib > MAX_MODEL_MIB:
                warnings.append(f"{obj.name}: ~{mib:.0f} MiB in joc (FiveM avertizeaza peste 16): taie-l in bucati "
                                f"sau Decimate")
            lo, hi = mesh_bounds(me)
            # originea modelului in mijlocul geometriei: GTA masoara distanta de vizibilitate de la pozitia
            # entitatii, iar strazile/terenul desenate in coordonatele lumii au originea departe (0, 0, 0), deci
            # dispareau cand te indepartai de ea; si coliziunile lor ajungeau toate in celula originii
            shift = (lo + hi) * 0.5
            if shift.length > 1.0:
                me.transform(Matrix.Translation(-shift))
                lo, hi = lo - shift, hi - shift
            else:
                shift = Vector((0.0, 0.0, 0.0))
            group = groups[key] = {"name": arch, "mesh": me, "lo": lo, "hi": hi, "shift": shift,
                                   "radius": (hi - lo).length * 0.5, "hash": mesh_digest(me)}
        pos = loc + rot @ group["shift"] + offset
        # distanta de vizibilitate proprie (de ex. teren: 1500 m), altfel cea din panou; plus raza obiectului,
        # ca marginile unui obiect mare (teren, strada lunga) sa nu dispara inaintea mijlocului
        obj_lod = float(obj.get("fivem_lod") or lod) + group["radius"]
        group["lod"] = max(group.get("lod", 0.0), obj_lod)
        add_entity(obj, group["name"], pos, rot, 1.0, 1.0, obj_lod,
                   world_extents(group["lo"], group["hi"], rot, (1.0, 1.0, 1.0)))
        add_collision(obj, key, tuple(scale), pos, rot, group["mesh"], sig=group["hash"])

    # coliziunile: o celula cu aceleasi obiecte in aceleasi locuri ca data trecuta isi pastreaza .ybn-ul (si numele
    # lui); celelalte se coc acum, cu nume nou (vezi stamp mai jos)
    old_cells = cache.get("cells", {})
    cell_marks = {cell: hashlib.sha1(json.dumps([COL_V] + sorted(json.dumps(it[0]) for it in items)).encode("utf-8")).hexdigest()
                  for cell, items in col_items.items()}
    keep_cells = {}
    for cell in sorted(col_items):
        old = old_cells.get(str(cell))
        if inc and old and old.get("hash") == cell_marks[cell] and (stream / f"{old['ybn']}.ybn").is_file():
            keep_cells[cell] = old["ybn"]
            continue
        for _mark, obj, key, scale, pos, rot, base in col_items[cell]:
            if key not in col_local:
                col_local[key] = local_collision(obj, scale, col_mat, f"{key[0]}.col", base)
            if len(col_local[key].polygons):
                collisions.setdefault(cell, []).append(placed_collision(col_local[key], pos, rot, f"{obj.name}.col"))
    if inc:
        log(f"  coliziuni: {len(keep_cells)} celule neschimbate, {len(collisions)} de refacut")

    # Scena copiata devine doar ce scriem: modelele noi (drawable-uri Sollumz) si coliziunile (compozite).
    for obj in list(scene.objects):
        if obj.library is None:
            bpy.data.objects.remove(obj, do_unlink=True)
    for child in list(scene.collection.children):
        scene.collection.children.unlink(child)
    bpy.context.view_layer.active_layer_collection = bpy.context.view_layer.layer_collection

    progress(0.3, "materiale si texturi")
    materials = Materials(sz, pkg, TMP_ROOT / name / "texturi", warnings)
    materials.convert_all([g["mesh"] for g in groups.values()])
    # toate texturile intra in .ytd (si cele ale modelelor neschimbate); daca numele lor s-au mutat intre imagini,
    # un .ydr vechi ar lua alta textura: atunci se refac toate modelele
    tex_sig = {t: img.name for t, img in materials.shared.items()}
    same_tex = inc and cache.get("tex") == tex_sig
    if inc and not same_tex:
        log("  texturile s-au schimbat: refac toate modelele")
    changed = {g["name"] for g in groups.values()
               if not same_tex or cache.get("models", {}).get(g["name"]) != g["hash"]
               or not (stream / f"{g['name']}.ydr").is_file()}
    if inc:
        log(f"  modele: {len(groups) - len(changed)} neschimbate, {len(changed)} de refacut")
    for k, group in enumerate(groups.values()):
        if group["name"] not in changed:
            continue
        if k % 25 == 0:
            progress(0.33 + 0.1 * k / len(groups), f"pregatesc modelele {k} din {len(groups)}")
        obj = bpy.data.objects.new(group["name"], group["mesh"])
        scene.collection.objects.link(obj)
        drawable = sz.dh.convert_obj_to_drawable(obj)
        drawable.name = group["name"]
        dp = drawable.drawable_properties
        dp.lod_dist_high = dp.lod_dist_med = dp.lod_dist_low = dp.lod_dist_vlow = 9998.0

    progress(0.43, "coliziuni")
    composites = []
    # nume nou la fiecare export: un joc ramas deschis dupa restartul serverului tine in memorie coliziunea veche
    # sub numele vechi, iar un .ybn schimbat cu acelasi nume il prabuseste la reconectare (gta-streaming-five)
    stamp = format(int(time.time()) & 0xFFFFF, "05x")
    new_cells = {}
    for n, cell in enumerate(sorted(collisions)):
        comp = bpy.data.objects.new(f"{name}_col{stamp}_{n:02d}", None)
        new_cells[cell] = comp.name.lower()
        comp.empty_display_size = 0
        comp.sollum_type = sz.SollumType.BOUND_COMPOSITE
        scene.collection.objects.link(comp)
        for k, me in enumerate(m for big in collisions[cell] for m in split_collision(big)):
            poly = bpy.data.objects.new(f"{comp.name}_{k:03d}", me)
            scene.collection.objects.link(poly)
            bvh = sz.bh.convert_obj_to_bvh(poly, scene.sz_default_flag_preset_name)
            bvh.parent = comp
            bvh.location = (0.0, 0.0, 0.0)
        # daca preset-ul de flag-uri nu s-a aplicat (fara interfata), punem flag-urile coliziunii statice
        for child in comp.children_recursive:
            if not hasattr(child, "composite_flags1"):
                continue
            names = list(type(child.composite_flags1).__annotations__.keys())
            if not any(getattr(child.composite_flags1, f) for f in names):
                for f in DEFAULT_FLAGS1:
                    if f in names:
                        setattr(child.composite_flags1, f, True)
                for f in DEFAULT_FLAGS2:
                    if f in names:
                        setattr(child.composite_flags2, f, True)
        composites.append(comp)

    stream = res_dir / "stream"
    res_dir.mkdir(parents=True, exist_ok=True)
    # semnul intai: un export intrerupt de aici incolo poate fi rescris de urmatorul
    (res_dir / MARKER).write_text(time.strftime("%Y-%m-%d %H:%M:%S") + "\n", encoding="utf-8")
    # obiectele puse cu editorul din joc si deja coapte (butonul Export din /mapeditor) raman: objects.json le
    # socoteste in ymap, deci fara el ar disparea din joc
    custom_ymap = stream / f"{name}_custom.ymap"
    custom_bytes = custom_ymap.read_bytes() if custom_ymap.is_file() else None
    if stream.exists() and not inc:
        shutil.rmtree(stream)
    stream.mkdir(parents=True, exist_ok=True)
    if custom_bytes is not None and not custom_ymap.is_file():
        custom_ymap.write_bytes(custom_bytes)
        log(f"  pastrez {custom_ymap.name} (obiectele din editorul din joc)")
    if changed or composites:
        log(f"  export Sollumz: {len(changed)} modele, {len(composites)} fisiere de coliziune")
        # de aici Sollumz scrie cate o linie "successfully exported" pe fisier: serverul le numara (45% -> 95%)
        print(f"PROGRES_PASI 0.45 0.95 {len(changed) + len(composites)} scriu fisierele GTA", flush=True)
        bpy.ops.sollumz.export_assets(directory=str(stream), direct_export=True, use_custom_settings=True,
                                      target_formats={"NATIVE"}, target_versions={"GEN8"},
                                      limit_to_selected=False, apply_transforms=False)
    missing = [f"{g['name']}.ydr" for g in groups.values() if not (stream / f"{g['name']}.ydr").is_file()]
    missing += [f"{c.name.lower()}.ybn" for c in composites if not (stream / f"{c.name.lower()}.ybn").is_file()]
    if missing:
        raise ExportError(f"Sollumz nu a scris {len(missing)} fisiere, ex: {', '.join(missing[:4])}")
    txd = f"{name}_tex"
    n_tex = materials.write_ytd(stream, txd, GX._targets(False)) if groups else 0
    if n_tex:
        log(f"  {txd}.ytd: {n_tex} texturi, comune tuturor modelelor noi")
    else:
        txd = ""

    progress(0.96, "harti .ymap si .ytyp")
    ymaps = []
    for n, cell in enumerate(sorted(entities)):
        ymaps.append(GX.write_ymap(f"{name}_{n:02d}", entities[cell], str(stream)))
    archetypes = list(copies.values()) + [custom_archetype(g["name"], g["lo"], g["hi"], g.get("lod", lod), txd)
                                          for g in groups.values()]
    ytyp_name = f"{name}_types"
    if archetypes:
        from szio.gta5 import AssetMapTypes, save_asset
        save_asset(AssetMapTypes(name=ytyp_name, archetypes=archetypes), GX._targets(False), stream, ytyp_name)

    manifest = ["fx_version 'cerulean'", "game 'gta5'", "",
                "author 'dayz_map_gen (export din Blender)'", f"description 'Harta {name}, exportata din Blender'",
                "", "this_is_a_map 'yes'"]
    if archetypes:
        manifest += ["", "-- modelele noi si copiile cladirilor GTA",
                     f"data_file 'DLC_ITYP_REQUEST' 'stream/{ytyp_name}.ytyp'"]
    minimap = write_minimap(scene.get("fivem_minimap"), res_dir, name, offset, log, warnings)
    if minimap:
        manifest += ["", "-- harta pe radar si pe harta mare: textura din stream/*_map.ytd, pusa de incarcatorul Scaleform",
                     f"files {{ '{minimap}' }}", "client_script 'client/minimap.js'"]
    if write_gps(scene.get("fivem_drumuri"), res_dir, offset, log):
        manifest += ["", "-- GPS pe strazile orasului: traseul pana la waypoint", "client_script 'client/gps.js'"]
    if write_water(scene.get("fivem_apa"), res_dir, offset, log, warnings):
        manifest += ["", "-- lacurile orasului (apa la nivelul solului): apa jocului + ele, incarcata de client/water.js",
                     "files { 'water.xml' }", "client_script 'client/water.js'"]
    (res_dir / "fxmanifest.lua").write_text("\n".join(manifest) + "\n", encoding="utf-8")
    (res_dir / "editor").mkdir(exist_ok=True)       # objects.json de acolo e al editorului: nu se atinge
    (res_dir / "editor" / "entities.json").write_text(json.dumps(editor_list), encoding="utf-8")
    (res_dir / "editor" / "suprafete.json").write_text(json.dumps(surfaces, separators=(",", ":")), encoding="utf-8")
    # fisierele ramase de la exportul trecut si care nu mai sunt ale nimanui (modele sterse, celule golite, .ymap-uri
    # in plus): jocul le-ar incarca in continuare
    wanted = ({f"{g['name']}.ydr".lower() for g in groups.values()}
              | {f"{v}.ybn" for v in list(keep_cells.values()) + list(new_cells.values())}
              | {f"{name}_{n:02d}.ymap".lower() for n in range(len(ymaps))} | {custom_ymap.name.lower()})
    orphans = [f for f in stream.iterdir() if f.suffix.lower() in (".ydr", ".ybn", ".ymap") and f.name.lower() not in wanted]
    for f in orphans:
        f.unlink()
    if orphans:
        log(f"  sterse din stream: {len(orphans)} fisiere ramase de data trecuta")
    cells_out = {str(c): {"hash": cell_marks[c], "ybn": keep_cells.get(c) or new_cells[c]}
                 for c in col_items if c in keep_cells or c in new_cells}
    cache_path.write_text(json.dumps({"code": code, "offset": [round(v, 3) for v in offset],
                                      "models": {g["name"]: g["hash"] for g in groups.values()},
                                      "cells": cells_out, "tex": tex_sig}), encoding="utf-8")
    (res_dir / MARKER).write_text(time.strftime("%Y-%m-%d %H:%M:%S") + "\n", encoding="utf-8")
    # ultimul: mapeditor il urmareste si reporneste harta in joc (fara reconectare)
    (res_dir / "editor" / "export_done.json").write_text(json.dumps({
        "time": time.time(), "incremental": inc, "models": len(changed), "cells": len(composites),
        "seconds": round(time.time() - started, 1)}), encoding="utf-8")

    summary = {
        "ok": True, "name": name, "res_dir": str(res_dir), "gta": len(refs), "gta_copied": len(copies),
        "gta_col": n_col_gta, "models": len(groups), "model_objects": len(news), "ybn": len(composites),
        "ymap": len(ymaps), "seconds": round(time.time() - started, 1), "warnings": warnings,
        "incremental": inc, "changed_models": len(changed), "kept_cells": len(keep_cells),
    }
    log(f"  gata: {res_dir}")
    return summary


def parse_cli(argv: list) -> dict:
    opts = {"name": None, "out": default_resources_dir(), "offset": (0.0, 0.0, 0.0), "lod": 300.0,
            "gta_col": True, "selected": None, "result": None}
    i = 0
    while i < len(argv):
        key = argv[i]
        value = argv[i + 1] if i + 1 < len(argv) else None
        if key == "--no-gta-col":
            opts["gta_col"] = False
        elif key == "--full":           # fara export incremental: se reconverteste tot
            opts["full"] = True
        elif key in ("--name", "--out", "--result") and value is not None:
            opts[key[2:]] = value
            i += 1
        elif key == "--offset" and value:
            opts["offset"] = tuple(float(v) for v in value.split(","))
            i += 1
        elif key == "--lod" and value:
            opts["lod"] = float(value)
            i += 1
        elif key == "--selected" and value:
            opts["selected"] = [s.strip() for s in Path(value).read_text(encoding="utf-8").splitlines() if s.strip()]
            i += 1
        i += 1
    return opts


def main_cli(argv: list) -> int:
    opts = parse_cli(argv)
    try:
        if not opts["name"]:
            raise ExportError("lipseste --name <resursa>")
        summary = run_export(opts, log=lambda text: print(text, flush=True))
    except Exception as error:
        import traceback
        traceback.print_exc()
        summary = {"ok": False, "error": str(error)}
    if opts.get("result"):
        Path(opts["result"]).write_text(json.dumps(summary, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=1, ensure_ascii=False), flush=True)
    return 0 if summary.get("ok") else 1


# ------------------------------------------------------------------------------------------ interfata

STATE = {"proc": None, "lines": [], "started": 0.0, "result": None, "log": None, "handle": None}


def _redraw():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()


def summary_lines(summary: dict, log_path: str) -> list:
    if not summary.get("ok"):
        return [f"EROARE: {summary.get('error', 'necunoscuta')}", f"detalii: {log_path}"]
    lines = [
        f"Gata in {summary['seconds']} s: {summary['res_dir']}",
        f"GTA: {summary['gta']} obiecte ({summary['gta_copied']} modele copiate in .ytyp)",
        f"Modele noi: {summary['models']} ({summary['model_objects']} obiecte)",
        f"Coliziune: {summary['ybn']} fisiere .ybn; harta: {summary['ymap']} fisiere .ymap",
        f"In server.cfg, o singura data: ensure {summary['name']}",
    ]
    warnings = summary.get("warnings") or []
    if warnings:
        lines.append(f"{len(warnings)} atentionari (toate in {log_path}):")
        lines += warnings[:4]
    return lines


def _poll():
    proc = STATE["proc"]
    if proc is None:
        return None
    if proc.poll() is None:
        STATE["lines"] = [f"Export in curs... {time.time() - STATE['started']:.0f} s"]
        _redraw()
        return 1.0
    STATE["proc"] = None
    if STATE["handle"] is not None:
        STATE["handle"].close()
        STATE["handle"] = None
    try:
        summary = json.loads(Path(STATE["result"]).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        summary = {"ok": False, "error": f"exportul s-a oprit (cod {proc.returncode})"}
    STATE["lines"] = summary_lines(summary, STATE["log"])
    _redraw()
    return None


class FivemExportSettings(bpy.types.PropertyGroup):
    res_name: bpy.props.StringProperty(
        name="Resursa", default="oras_meu", description="Numele resursei FiveM (folderul si prefixul fisierelor)")
    out_dir: bpy.props.StringProperty(
        name="Folder", subtype="DIR_PATH", default=default_resources_dir(),
        description="Folderul cu resurse al serverului FiveM")
    offset: bpy.props.FloatVectorProperty(
        name="Mutare", size=3, subtype="TRANSLATION",
        description="Se adauga la toate pozitiile. Coordonatele din Blender sunt chiar coordonatele din GTA")
    lod: bpy.props.FloatProperty(
        name="Vizibile de la", default=300.0, min=50.0, max=3000.0, subtype="DISTANCE",
        description="Distanta minima de la care se vad cladirile si modelele noi")
    gta_col: bpy.props.BoolProperty(
        name="Coliziune pentru cladirile GTA", default=True,
        description="Coace coliziunea cladirilor GTA, care in afara locului lor original nu sunt solide")
    only_selected: bpy.props.BoolProperty(name="Doar selectia", default=False)


class FIVEM_OT_check(bpy.types.Operator):
    bl_idname = "fivem.check"
    bl_label = "Verifica"
    bl_description = "Numara ce se exporta si cum, fara sa scrie nimic"

    def execute(self, context):
        settings = context.scene.fivem_export
        objs = [o for o in context.scene.objects if exportable(o)]
        if settings.only_selected:
            objs = [o for o in objs if o.select_get()]
        refs = [o for o in objs if classify(o) == "gta"]
        news = [o for o in objs if classify(o) == "nou"]
        strm = {gta_name(o) for o in refs if str(gta_info(o).get("ytyp", "")).lower().endswith("_strm")}
        lines = [f"GTA: {len(refs)} obiecte, {len({gta_name(o) for o in refs})} modele diferite",
                 f"   din care {len(strm)} se copiaza in .ytyp-ul resursei",
                 f"Modele noi: {len(news)} obiecte"]
        nocol = sum(1 for o in objs if o.get(P_NOCOL))
        if nocol:
            lines.append(f"Fara coliziune: {nocol} obiecte")
        mlo = [o.name for o in objs if classify(o) == "mlo"]
        if mlo:
            lines.append(f"Interioare GTA nesuportate: {len(mlo)}")
        bad = [o.name for o in refs
               if abs(abs(o.matrix_world.to_scale().x) - abs(o.matrix_world.to_scale().y)) > 1e-3]
        if bad:
            lines.append(f"Scala X diferita de Y (GTA ia X): {', '.join(bad[:3])}")
        STATE["lines"] = lines
        return {"FINISHED"}


class FIVEM_OT_flag(bpy.types.Operator):
    bl_idname = "fivem.flag"
    bl_label = "Comuta"
    bl_options = {"REGISTER", "UNDO"}
    flag: bpy.props.StringProperty()

    @classmethod
    def description(cls, context, props):
        return {P_NEW: "Obiectele GTA selectate se exporta ca modele noi (de exemplu dupa ce le-ai sculptat)",
                P_NOCOL: "Obiectele selectate nu primesc coliziune (decor prin care se poate trece)"}.get(props.flag, "")

    def execute(self, context):
        objs = context.selected_objects
        if not objs:
            self.report({"WARNING"}, "Selecteaza intai obiectele")
            return {"CANCELLED"}
        value = not all(o.get(self.flag) for o in objs)
        for obj in objs:
            if value:
                obj[self.flag] = True
            elif self.flag in obj:
                del obj[self.flag]
        return {"FINISHED"}


class FIVEM_OT_export(bpy.types.Operator):
    bl_idname = "fivem.export"
    bl_label = "Exporta in FiveM"
    bl_description = "Scrie resursa FiveM a hartii, intr-un Blender separat; scena deschisa nu se schimba"

    @classmethod
    def poll(cls, context):
        return STATE["proc"] is None

    def execute(self, context):
        settings = context.scene.fivem_export
        name = safe_name(settings.res_name)
        out = bpy.path.abspath(settings.out_dir).rstrip("\\/")
        if not out:
            self.report({"ERROR"}, "Alege folderul cu resurse")
            return {"CANCELLED"}
        tmp = TMP_ROOT / name
        tmp.mkdir(parents=True, exist_ok=True)
        blend = tmp / "scena.blend"
        result = tmp / "rezultat.json"
        if result.exists():
            result.unlink()
        # copia include si ce ai modificat si n-ai salvat; fisierul tau ramane cum era
        bpy.ops.wm.save_as_mainfile(filepath=str(blend), copy=True)
        cmd = [bpy.app.binary_path, "-b", str(blend), "-P", str(SCRIPT), "--", "--name", name, "--out", out,
               "--offset", ",".join(f"{v:.4f}" for v in settings.offset), "--lod", f"{settings.lod:.1f}",
               "--result", str(result)]
        if not settings.gta_col:
            cmd.append("--no-gta-col")
        if settings.only_selected:
            selection = tmp / "selectie.txt"
            selection.write_text("\n".join(o.name for o in context.selected_objects), encoding="utf-8")
            cmd += ["--selected", str(selection)]
        log_path = tmp / "export.log"
        handle = open(log_path, "w", encoding="utf-8")
        proc = subprocess.Popen(cmd, stdout=handle, stderr=subprocess.STDOUT,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        STATE.update(proc=proc, started=time.time(), result=str(result), log=str(log_path), handle=handle,
                     lines=["Export pornit..."])
        bpy.app.timers.register(_poll, first_interval=1.0)
        return {"FINISHED"}


class FIVEM_PT_export(bpy.types.Panel):
    bl_label = "Export FiveM"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Harta"
    bl_order = 100          # sub uneltele de harta, in acelasi tab

    def draw(self, context):
        layout = self.layout
        settings = context.scene.fivem_export
        col = layout.column(align=True)
        col.prop(settings, "res_name")
        col.prop(settings, "out_dir")
        layout.prop(settings, "offset")
        col = layout.column(align=True)
        col.prop(settings, "lod")
        col.prop(settings, "gta_col")
        col.prop(settings, "only_selected")

        obj = context.active_object
        box = layout.box()
        kind = classify(obj) if obj is not None else None
        if obj is None:
            box.label(text="Niciun obiect activ")
        elif kind == "gta":
            box.label(text=f"Model GTA: {gta_name(obj)}", icon="LINKED")
            box.label(text=f"din {gta_info(obj).get('ytyp', '?')}")
        elif kind == "nou":
            box.label(text=f"Model nou: {obj.name}", icon="MESH_DATA")
        elif kind == "mlo":
            box.label(text=f"{obj.name}: interior GTA, nu se exporta inca", icon="ERROR")
        else:
            box.label(text=f"{obj.name}: nu se exporta", icon="X")
        if obj is not None:
            row = box.row(align=True)
            if gta_info(obj) is not None:
                row.operator("fivem.flag", text="Model nou", depress=bool(obj.get(P_NEW))).flag = P_NEW
            row.operator("fivem.flag", text="Fara coliziune", depress=bool(obj.get(P_NOCOL))).flag = P_NOCOL

        row = layout.row(align=True)
        row.operator("fivem.check", icon="VIEWZOOM")
        row.operator("fivem.export", icon="EXPORT")
        for line in STATE["lines"]:
            layout.label(text=line)


CLASSES = (FivemExportSettings, FIVEM_OT_check, FIVEM_OT_flag, FIVEM_OT_export, FIVEM_PT_export)


def register():
    for cls in CLASSES:
        old = getattr(bpy.types, cls.__name__, None)
        if old is not None:
            try:
                bpy.utils.unregister_class(old)
            except RuntimeError:
                pass
        bpy.utils.register_class(cls)
    bpy.types.Scene.fivem_export = bpy.props.PointerProperty(type=FivemExportSettings)


if __name__ == "__main__":
    ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if bpy.app.background and "--name" in ARGV:
        sys.exit(main_cli(ARGV))
    register()
