# -*- coding: utf-8 -*-
"""
Aduce in Blender ce ai schimbat in joc cu /mapeditor (<resursa>/editor/objects.json):
  - obiectele puse in joc intra in colectia "Obiecte din joc": modele GTA din biblioteca, iar cladirile/obiectele
    orasului mutate in joc ca si copii ale lor. Exportul FiveM le sare: in joc le pune editorul, din objects.json.
  - obiectele generate ascunse (sau mutate) in joc se ascund si aici (ochiul din Outliner), dar exportul le
    pastreaza in harta: in joc le ascunde editorul, iar un Ctrl+Z acolo le aduce inapoi.

Ruleaza singur la generare (gen_oras.py) si la "Deschide in Blender" din editorul de oras. De mana:
    _blender.bat output\\orase\\oras.blend -P tools\\import_din_joc.py -- --plan output\\orase\\oras.json [--save]
"""
import argparse
import json
import math
import runpy
import sys
import zlib
from pathlib import Path

import bpy
from mathutils import Euler, Matrix, Vector

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
COLL = "Obiecte din joc"
P_FROM_GAME = "fivem_din_joc"        # pus in joc: exportul FiveM il sare
P_HIDDEN = "fivem_ascuns_in_joc"     # generat si ascuns in joc: ascuns aici, dar exportul il pastreaza
DEFAULT_JOC = (6000.0, -2600.0, 25.0)


def resources_dir() -> Path:
    """Ca default_resources_dir() din blender_fivem_export.py."""
    try:
        cfg = json.loads((ROOT / "map.json").read_text(encoding="utf-8"))
        if cfg.get("fivem_resources_dir"):
            return Path(cfg["fivem_resources_dir"])
    except (OSError, ValueError):
        pass
    return ROOT / "output" / "fivem"


def resource_name(name, plan) -> str:
    """Ca resource_name() din tools/oras/server.py."""
    joc = plan.get("joc") or {}
    raw = (joc.get("resursa") or f"oras_{Path(name).name}").lower()
    return "".join(c if c.isalnum() or c in "_-" else "_" for c in raw)


def entity_guid(res, obj_name) -> int:
    """GUID-ul entitatii din .ymap, ca in blender_fivem_export.py (GX._guid(f"{name}/{obj.name}"))."""
    return zlib.crc32(f"{res}/{obj_name}".encode("utf-8")) & 0x7FFFFFFF or 1


def _read(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return default


def _reset():
    """Scoate ce a adus importul trecut (colectia si obiectele ascunse), ca sa nu se dubleze."""
    coll = bpy.data.collections.get(COLL)
    if coll:
        for child in list(coll.children):
            for obj in list(child.objects):
                bpy.data.objects.remove(obj, do_unlink=True)
            bpy.data.collections.remove(child)
        for obj in list(coll.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
    for obj in bpy.data.objects:
        if obj.get(P_HIDDEN):
            del obj[P_HIDDEN]
            try:
                obj.hide_set(False)
            except RuntimeError:
                pass
    return coll


def import_game_edits(plan, name, props=None, log=print, objects_path=None) -> int:
    """Aduce modificarile din joc in scena curenta; intoarce cate obiecte a pus sau ascuns.
    objects_path = alt objects.json (teste); implicit cel al resursei."""
    res = resource_name(name, plan)
    edir = resources_dir() / res / "editor"
    state = _read(objects_path or edir / "objects.json", {})
    objects = [o for o in (state.get("objects") or []) if isinstance(o, dict) and o.get("model")]
    removed = {int(g) for g in (state.get("removed") or [])}
    coll = _reset()
    # texturile schimbate in editor (editor/overrides.json) se vad si aici (tools/tex_overrides.py)
    try:
        joc0 = plan.get("joc") or {}
        txo = runpy.run_path(str(TOOLS / "tex_overrides.py"), run_name="tex_overrides")
        n_tex = txo["apply"](bpy.context.scene, res, txo["load"](resources_dir() / res),
                             (float(joc0.get("x", DEFAULT_JOC[0])), float(joc0.get("y", DEFAULT_JOC[1]))), log)
        if n_tex:
            log(f"IMPORT_JOC {res}: {n_tex} texturi schimbate in editor")
    except Exception as error:      # modificarile de obiecte se aduc oricum
        log(f"IMPORT_JOC avertisment: texturile din editor nu s-au pus: {error}")
    if not objects and not removed:
        log(f"IMPORT_JOC {res}: nimic schimbat in joc")
        return 0

    joc = plan.get("joc") or {}
    offset = Vector((float(joc.get("x", DEFAULT_JOC[0])), float(joc.get("y", DEFAULT_JOC[1])),
                     float(joc.get("z", DEFAULT_JOC[2]))))
    scene = bpy.context.scene
    if coll is None:
        coll = bpy.data.collections.new(COLL)
    if coll.name not in scene.collection.children:
        scene.collection.children.link(coll)

    # obiectele orasului, dupa GUID-ul pe care li-l da exportul; entities.json spune modelul si pozitia din joc
    by_guid = {}
    for obj in scene.objects:
        if not obj.get(P_FROM_GAME):
            by_guid.setdefault(entity_guid(res, obj.name), obj)
    sources = {}     # model al orasului -> (obiect din Blender, pozitia entitatii in joc)
    for entry in _read(edir / "entities.json", []):
        model = str(entry.get("model", "")).lower()
        obj = by_guid.get(int(entry.get("guid", 0)))
        if obj is not None and model.startswith(res + "_") and model not in sources:
            sources[model] = (obj, Vector((float(entry["x"]), float(entry["y"]), float(entry["z"]))))

    n_hidden = 0
    for guid in removed:
        obj = by_guid.get(guid)
        if obj is None:
            continue
        obj[P_HIDDEN] = True
        try:
            obj.hide_set(True)
        except RuntimeError:
            pass
        n_hidden += 1

    if props is None:
        props = runpy.run_path(str(TOOLS / "gta_props.py"), run_name="gta_props")
    gta_models = sorted({str(o["model"]).lower() for o in objects} - set(sources))
    have = set(props["load"](gta_models)) if gta_models else set()

    groups = {}      # grupul din joc ("Parc 2") -> subcolectia lui, ca in fila Harta / Outliner din editor

    def target(grup):
        if not grup:
            return coll
        if grup not in groups:
            groups[grup] = bpy.data.collections.new(f"Din joc: {grup}")
            coll.children.link(groups[grup])
        return groups[grup]

    n_placed = n_missing = 0
    for item in objects:
        model = str(item["model"]).lower()
        grup = str(item.get("grup") or "")
        dest = target(grup)
        pos = Vector((float(item.get("x", 0.0)), float(item.get("y", 0.0)), float(item.get("z", 0.0))))
        rot = Euler((math.radians(float(item.get("rx", 0.0))), math.radians(float(item.get("ry", 0.0))),
                     math.radians(float(item.get("rz", 0.0)))), "XYZ")
        local = pos - offset
        if model in sources:
            # o cladire/un obiect al orasului mutat in joc: copie (acelasi mesh). Exportul ii muta originea in
            # mijlocul geometriei (pos = loc + rot @ shift), deci shift se afla din original si se scade inapoi.
            src, src_pos = sources[model]
            loc0, rot0, scale0 = src.matrix_world.decompose()
            shift = rot0.inverted() @ (src_pos - offset - loc0)
            q = rot.to_quaternion()
            obj = src.copy()
            if P_HIDDEN in obj:         # originalul e ascuns in joc; copia (pozitia noua) nu
                del obj[P_HIDDEN]
            if "harta_unit" in obj:     # copia nu e a generatorului: generarea incrementala n-o sterge cu originalul
                del obj["harta_unit"]
            obj.parent = None
            obj.matrix_world = Matrix.LocRotScale(local - q @ shift, q, scale0)
            dest.objects.link(obj)
        elif model in have:
            obj = props["place"](dest, model, local.x, local.y, local.z, rot.z)
            obj.rotation_euler.x, obj.rotation_euler.y = rot.x, rot.y
        else:
            # modelul nu e in biblioteca (importa-i zona cu IMPORTA_GTA.bat): macar un reper cu numele lui
            obj = bpy.data.objects.new(model, None)
            obj.empty_display_type = "ARROWS"
            obj.location, obj.rotation_euler = local, rot
            dest.objects.link(obj)
            n_missing += 1
        obj[P_FROM_GAME] = str(item.get("id") or "")
        obj["harta_tip"] = "din_joc"
        if grup:
            obj["harta_grup"] = grup
        n_placed += 1

    log(f"IMPORT_JOC {res}: {n_placed} obiecte puse in joc (colectia '{COLL}'"
        + (f", {n_missing} fara model in biblioteca" if n_missing else "") + f"), {n_hidden} ascunse in joc")
    return n_placed + n_hidden


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser(description="Modificarile din /mapeditor -> scena Blender")
    ap.add_argument("--plan", required=True, help="planul orasului (output/orase/<nume>.json)")
    ap.add_argument("--save", action="store_true", help="salveaza .blend-ul dupa import")
    ap.add_argument("--objects", default=None, help="alt objects.json (teste)")
    a = ap.parse_args(argv)
    path = Path(a.plan)
    import_game_edits(json.loads(path.read_text(encoding="utf-8")), path.stem, objects_path=a.objects)
    if a.save:
        bpy.ops.wm.save_mainfile()


if __name__ == "__main__":
    main()
