# -*- coding: utf-8 -*-
"""
Texturile schimbate din editorul din joc (/mapeditor -> <resursa>/editor/overrides.json) puse pe obiectele orasului,
la exportul FiveM (blender_fivem_export.py) si la deschiderea in Blender (import_din_joc.py); si lista materialelor
fiecarui obiect pe roluri, pentru editor (entities.json: ce material, textura, normal map, shader si scala are
fiecare rol).

overrides.json: {"<guid>": {"nume": "parc_12", "kind": "curte", "x": .., "y": ..,
                            "roluri": {"iarba": {"tex": "am_grass_green", "scala": 4.0}}}}

O textura schimbata = o copie a materialului rolului (<material>__<textura>) cu textura diffuse (si normal map-ul
ei, daca exista) din biblioteca GTA; UV-urile fetelor rolului se rescaleaza la noua scala. Ce s-a pus se tine minte
pe obiect (P_DONE), deci aplicarea repetata nu dubleaza scala, iar o schimbare stearsa din editor se intoarce.
"""
import json
import re
import zlib
from pathlib import Path

import bpy
from mathutils import Vector

TOOLS = Path(__file__).resolve().parent
LIB = TOOLS.parent / "output" / "gta_asset_library"
P_DONE = "fivem_tex_override"       # {rol: [textura, scala]} puse pe obiect


def guid(res, obj_name) -> int:
    """GUID-ul entitatii din .ymap, ca in blender_fivem_export.py (GX._guid(f"{name}/{obj.name}"))."""
    return zlib.crc32(f"{res}/{obj_name}".encode("utf-8")) & 0x7FFFFFFF or 1


def load(res_dir) -> dict:
    try:
        data = json.loads((Path(res_dir) / "editor" / "overrides.json").read_text(encoding="utf-8-sig"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def roles(obj) -> dict:
    """{rol: (material, metri per repetare)} scris de generator (Mesh.to_object); {} la obiectele fara el."""
    try:
        raw = json.loads(obj.get("harta_roluri") or "{}")
    except (TypeError, ValueError):
        return {}
    return {k: (str(v[0]), float(v[1])) for k, v in raw.items() if isinstance(v, list) and len(v) == 2}


def _image_node(mat, *names):
    if not mat or not mat.node_tree:
        return None
    for n in names:
        node = mat.node_tree.nodes.get(n)
        if node is not None and getattr(node, "image", None) is not None:
            return node
    if names and names[0] == "DiffuseSampler":      # material fara shader GTA: prima imagine
        return next((n for n in mat.node_tree.nodes if n.type == "TEX_IMAGE" and n.image is not None), None)
    return None


def _tex_name(node) -> str:
    if node is None:
        return ""
    name = getattr(node, "sollumz_texture_name", "") or node.image.name
    name = re.sub(r"\.(dds|png|jpg|tga)$", "", name, flags=re.I)
    return re.sub(r"\.\d{3}$", "", name)


def _shader(mat) -> str:
    props = getattr(mat, "shader_properties", None)
    return str(getattr(props, "filename", "") or getattr(props, "name", "") or "")


def mats_info(obj) -> list:
    """[{rol, mat, tex, normal, shader, scala, schimbat}] pentru fiecare material al obiectului."""
    by_mat = {m: (r, s) for r, (m, s) in roles(obj).items()}
    done = _done(obj)
    out = []
    for slot in obj.material_slots:
        mat = slot.material
        if mat is None:
            continue
        base = mat.get("harta_original") or mat.name
        role, scale = by_mat.get(base, (base, 0.0))
        if role in done:
            scale = done[role][1] or scale
        # iarba amestecata (terrain_cb_w_4lyr): textura rolului e stratul 0, celelalte raman
        out.append({"rol": role, "mat": base, "tex": _tex_name(_image_node(mat, "DiffuseSampler", "TextureSampler_layer0")),
                    "normal": _tex_name(_image_node(mat, "BumpSampler", "BumpSampler_layer0")), "shader": _shader(mat),
                    "scala": round(scale, 2), "schimbat": bool(mat.get("harta_override"))})
    return out


SURF_KINDS = {"teren", "strada", "curte", "fundatie", "cladire"}
MAX_TRIS = 6000


# rolurile scrise in suprafete.json: la cladiri peretii, acoperisurile, firmele si vitrinele (ramele, geamurile, usile,
# metalul au sute de mii de triunghiuri si nu se retexturiaza), la strazi asfaltul si trotuarul (si pensula ocoleste pe ele)
KEEP = {"cladire": lambda r: r.startswith(("perete", "acoperis", "firma", "vitrina")) or r == "tabla",
        "strada": lambda r: r in ("asfalt", "trotuar")}


def tris_info(obj, offset, kind="") -> dict:
    """{"o": [x, y, z], rol: [x, y, z, u, v] x 3 pe triunghi, plat}: editorul din joc deseneaza textura aleasa doar
    peste fetele rolului obiectului ales (si pensula nu pune pe strazi). "o" = coltul obiectului in coordonate de
    joc; x, y, z = centimetri fata de el, u, v = UV-ul exportat x 1000 (numere intregi: fisierul e de ~5 ori mai mic).
    {} la obiectele fara UV sau cu prea multe triunghiuri."""
    me = obj.data
    if obj.type != "MESH" or not me.uv_layers:
        return {}
    me.calc_loop_triangles()
    by_mat = {m: r for r, (m, _s) in roles(obj).items()}
    slot_role = {i: by_mat.get(s.material.get("harta_original") or s.material.name,
                               s.material.get("harta_original") or s.material.name)
                 for i, s in enumerate(obj.material_slots) if s.material is not None}
    keep = KEEP.get(kind, lambda r: True)
    # limita e pe fetele care se scriu, nu pe tot obiectul: un bloc are ~8500 de triunghiuri cu rame si balcoane,
    # dar peretii lui sunt cateva sute (altfel niciun bloc nu-si putea schimba textura din joc)
    kept = sum(1 for t in me.loop_triangles if keep(slot_role.get(t.material_index, "")))
    if kept > MAX_TRIS:
        return {}
    uv = me.uv_layers.active.data
    mw = obj.matrix_world
    ox, oy, oz = (list(offset) + [0.0, 0.0, 0.0])[:3]
    o = [round(v, 2) for v in (mw.translation.x + ox, mw.translation.y + oy, mw.translation.z + oz)]
    out = {}
    for t in me.loop_triangles:
        role = slot_role.get(t.material_index)
        if role is None or not keep(role):
            continue
        dst = out.setdefault(role, [])
        for li, vi in zip(t.loops, t.vertices):
            p = mw @ me.vertices[vi].co
            u, v = uv[li].uv
            dst += [round((p.x + ox - o[0]) * 100), round((p.y + oy - o[1]) * 100), round((p.z + oz - o[2]) * 100),
                    round(u * 1000), round(v * 1000)]
    if out:
        out["o"] = o
    return out


def _done(obj) -> dict:
    try:
        return {k: (str(v[0]), float(v[1])) for k, v in json.loads(obj.get(P_DONE) or "{}").items()}
    except (TypeError, ValueError):
        return {}


def _center(obj) -> Vector:
    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    return sum(pts, Vector()) / len(pts)


def _slots(obj, base):
    return [i for i, s in enumerate(obj.material_slots)
            if s.material is not None and (s.material.get("harta_original") or s.material.name) == base]


def _rescale(obj, idx, factor):
    """UV-urile fetelor cu materialele idx inmultite cu factor (UV = metri / scala)."""
    me = obj.data
    if not me.uv_layers or abs(factor - 1.0) < 1e-6:
        return
    uv = me.uv_layers.active.data
    want = set(idx)
    for poly in me.polygons:
        if poly.material_index in want:
            for li in poly.loop_indices:
                uv[li].uv = (uv[li].uv[0] * factor, uv[li].uv[1] * factor)


def _material(orig, tex):
    """Copia materialului orig cu textura tex din biblioteca (una singura pe pereche, refolosita)."""
    key = f"{orig.name}__{tex}"
    new = bpy.data.materials.get(key)
    if new is not None:
        return new
    new = orig.copy()
    new.name = key
    new["harta_original"] = orig.name
    new["harta_override"] = tex
    # sollumz_texture_name nu se scrie: Sollumz il calculeaza din imagine (doar get), iar atribuirea arunca eroare si
    # oprea toate texturile alese in editor
    d = _image_node(new, "DiffuseSampler", "TextureSampler_layer0")
    if d is not None:
        d.image = bpy.data.images.load(str(LIB / f"{tex}.dds"), check_existing=True)
    nodes = new.node_tree.nodes if new.node_tree else {}
    b = nodes.get("BumpSampler") or nodes.get("BumpSampler_layer0")
    nrm = LIB / f"{tex}_n.dds"
    if b is not None and hasattr(b, "image") and nrm.is_file():
        b.image = bpy.data.images.load(str(nrm), check_existing=True)
    return new


def _set_role(obj, role, want, done, log) -> bool:
    """Pune (want = {tex, scala}) sau scoate (want = None) textura unui rol. True daca s-a schimbat ceva."""
    rmap = roles(obj)
    base, gen_scale = rmap.get(role, (role, 0.0))
    idx = _slots(obj, base)
    if not idx:
        log(f"  {obj.name}: nu are rolul {role}")
        return False
    cur_tex, cur_scale = done.get(role, ("", gen_scale))
    orig = bpy.data.materials.get(base)
    if want is None:
        if role not in done:
            return False
        for i in idx:
            if orig is not None:
                obj.material_slots[i].material = orig
        if gen_scale > 0 and cur_scale > 0:
            _rescale(obj, idx, cur_scale / gen_scale)
        del done[role]
        return True
    tex = str(want.get("tex") or "")
    scale = float(want.get("scala") or gen_scale or 0.0)
    if not (LIB / f"{tex}.dds").is_file():
        log(f"  {obj.name}: textura {tex} nu e in biblioteca GTA")
        return False
    if done.get(role) == (tex, scale):
        return False
    if orig is None:
        orig = obj.material_slots[idx[0]].material
    if obj.data.users > 1:
        obj.data = obj.data.copy()          # mesh-ul impartit cu alte obiecte ramane neatins
    new = _material(orig, tex)
    for i in idx:
        obj.material_slots[i].material = new
    if cur_scale > 0 and scale > 0:
        _rescale(obj, idx, cur_scale / scale)
    done[role] = (tex, scale)
    return True


def apply(scene, res, overrides, offset, log=print) -> int:
    """Pune pe obiectele scenei texturile din overrides (si scoate ce s-a pus inainte si nu mai e cerut).
    res = numele resursei (pentru GUID), offset = unde sta orasul in joc (pozitiile din overrides sunt din joc).
    Intoarce cate roluri s-au schimbat."""
    objs = [o for o in scene.objects if o.type == "MESH" and not o.get("fivem_din_joc")]
    by_guid = {}
    for o in objs:
        by_guid.setdefault(guid(res, o.name), o)
    wanted = {}         # obiect -> {rol: want}
    for key, ov in (overrides or {}).items():
        try:
            obj = by_guid.get(int(key))
        except ValueError:
            obj = None
        if obj is None and "x" in ov:
            # regenerat cu alt nume: acelasi fel de obiect in acelasi loc
            p = Vector((float(ov["x"]), float(ov["y"]), 0.0)) - Vector((offset[0], offset[1], 0.0))
            near = [(((_center(o) - p) * Vector((1, 1, 0))).length, o) for o in objs
                    if o.get("harta_tip") == ov.get("kind")]
            near = [t for t in near if t[0] < 3.0]
            obj = min(near, key=lambda t: t[0])[1] if near else None
        if obj is None:
            log(f"  textura schimbata pentru {ov.get('nume', key)}: obiectul nu mai exista (ramane in overrides.json)")
            continue
        wanted.setdefault(obj.name, {}).update(ov.get("roluri") or {})
    # fundatia unei cladiri e un obiect separat (<cladire>_fundatie, rol "soclu"): urmeaza soclul ales pe cladire,
    # daca n-are ea alta textura aleasa (altfel casa isi schimba soclul si fundatia de sub el ramanea la fel)
    for name, want in list(wanted.items()):
        base = scene.objects.get(name + "_fundatie")
        if base is not None and "soclu" in want and "soclu" not in wanted.get(base.name, {}):
            wanted.setdefault(base.name, {})["soclu"] = want["soclu"]
    changed = 0
    for o in objs:
        done = _done(o)
        want = wanted.get(o.name, {})
        if not done and not want:
            continue
        for role in set(done) | set(want):
            changed += _set_role(o, role, want.get(role), done, log)
        if done:
            o[P_DONE] = json.dumps({k: list(v) for k, v in done.items()})
        elif P_DONE in o:
            del o[P_DONE]
    return changed
