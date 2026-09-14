# -*- coding: utf-8 -*-
"""
Export binar direct (fara CodeWalker) prin szio + pymateria:
  - .ytd  (dictionare de texturi din DDS-urile noastre)
  - .ytyp (arhetipuri pentru tile-urile de teren si cladiri)
  - .ymap (entitati: teren + props vanilla + cladiri, impartite pe chunk-uri pentru streaming)
  - impachetare: folder FiveM (stream/) si dlc.rpf pentru RAGE:MP
"""
import json
import math
import os
import shutil
import zlib
from pathlib import Path

import numpy as np

from . import config as C

# dimensiuni aproximative (raza XY, inaltime) pentru props vanilla -> extents de streaming
PROP_EXTENT = {"tree": (11.0, 26.0), "bush": (3.5, 3.0), "rock": (6.0, 5.0), "landmark": (14.0, 22.0),
               "small": (2.5, 2.5), "wreck": (4.0, 2.0)}
# model necunoscut (pus manual din editor): raza 5 m, inaltime 5 m
PROP_EXTENT_DEFAULT = (5.0, 5.0)


def _rot_quat(rx: float = 0.0, ry: float = 0.0, rz: float = 0.0, degrees: bool = True):
    """
    Cuaternionul (w, x, y, z) asa cum il asteapta o entitate .ymap: rotatia Euler in ordinea
    GTA (rx, ry, rz aplicati X->Y->Z) INVERSATA, ca in CodeWalker / Sollumz.
    Pentru rx=ry=0 rezultatul este identic cu Quaternion((0,0,1), yaw).inverted().
    """
    if degrees:
        rx, ry, rz = math.radians(rx), math.radians(ry), math.radians(rz)
    cx, sx = math.cos(rx * 0.5), math.sin(rx * 0.5)
    cy, sy = math.cos(ry * 0.5), math.sin(ry * 0.5)
    cz, sz = math.cos(rz * 0.5), math.sin(rz * 0.5)
    w = cz * cy * cx + sz * sy * sx
    x = cz * cy * sx - sz * sy * cx
    y = cz * sy * cx + sz * cy * sx
    z = sz * cy * cx - cz * sy * sx
    return (w, -x, -y, -z)   # inversul (cuaternion unitar) = conjugatul


def _kind_of(name: str) -> str:
    if name.startswith("prop_tree_") or name.startswith("prop_log"):
        return "tree" if "fallen" not in name and "stump" not in name and "log" not in name else "small"
    if name.startswith("prop_bush_"):
        return "bush"
    if name.startswith("prop_rock_"):
        return "rock"
    if name in C.VILLAGE_LANDMARKS:
        return "landmark"
    if name.startswith("prop_rub_carwreck"):
        return "wreck"
    return "small"


def _targets(gen9: bool):
    from szio.gta5 import AssetTarget, AssetFormat, AssetVersion
    return (AssetTarget(AssetFormat.NATIVE, AssetVersion.GEN9 if gen9 else AssetVersion.GEN8),)


def _guid(text: str) -> int:
    return zlib.crc32(text.encode("utf-8")) & 0x7FFFFFFF or 1


# ----------------------------------------------------------------------------------------- YTD

def export_ytds(cfg: C.MapConfig, texs: dict, out_dir: str, gen9: bool, log=print) -> dict:
    """Doua dictionare: <name>_terrain si <name>_buildings. Returneaza {cheie_textura: nume_ytd}."""
    from szio.gta5 import AssetTextureDictionary, EmbeddedTexture, save_asset
    from szio.types import DataSource
    groups = {
        f"{cfg.name}_terrain": ["grass", "dirt", "rock", "sand"],
        f"{cfg.name}_buildings": ["plaster", "wood", "brick", "rooftile", "metal", "window", "door"],
    }
    tex_to_ytd = {}
    for ytd_name, keys in groups.items():
        textures = {}
        for k in keys:
            info = texs[k]
            for tname, path in ((info["name"], info["diffuse"]), (info["name_n"], info["normal"])):
                textures[tname] = EmbeddedTexture(tname, info["size"], info["size"],
                                                  DataSource.create(path, tname + ".dds"))
            tex_to_ytd[k] = ytd_name
        save_asset(AssetTextureDictionary(textures=textures), _targets(gen9), Path(out_dir), ytd_name)
        log(f"  ytd: {ytd_name} ({len(textures)} texturi)")
    return tex_to_ytd


# ----------------------------------------------------------------------------------------- YTYP

def export_ytyp(cfg: C.MapConfig, bounds: dict, tile_names: dict, building_names: dict, out_dir: str,
                gen9: bool, log=print) -> str:
    from szio.gta5 import AssetMapTypes, Archetype, ArchetypeType, ArchetypeAssetType, save_asset
    from mathutils import Vector
    archetypes = []

    def arch(name, txd, lod_dist):
        bmin, bmax = bounds[name]
        bmin = Vector((float(bmin[0]), float(bmin[1]), float(bmin[2])))
        bmax = Vector((float(bmax[0]), float(bmax[1]), float(bmax[2])))
        center = (bmin + bmax) * 0.5
        radius = (bmax - bmin).length * 0.5
        return Archetype(
            name=name, type=ArchetypeType.BASE, flags=32, lod_dist=float(lod_dist), special_attribute=0,
            hd_texture_dist=60.0, texture_dictionary=txd, clip_dictionary="", drawable_dictionary="",
            physics_dictionary="", bb_min=bmin, bb_max=bmax, bs_center=center, bs_radius=float(radius),
            asset_name=name, asset_type=ArchetypeAssetType.DRAWABLE, extensions=[],
        )

    for name in tile_names.values():
        archetypes.append(arch(name, f"{cfg.name}_terrain", cfg.lod_dist_terrain))
    for name in building_names.values():
        archetypes.append(arch(name, f"{cfg.name}_buildings", cfg.lod_dist_building))
    ytyp_name = f"{cfg.name}_types"
    save_asset(AssetMapTypes(name=ytyp_name, archetypes=archetypes), _targets(gen9), Path(out_dir), ytyp_name)
    log(f"  ytyp: {ytyp_name} ({len(archetypes)} arhetipuri)")
    return ytyp_name


# ----------------------------------------------------------------------------------------- YMAP

ENTITY_FLAGS_STATIC = (1 << 5) | (1 << 19) | (1 << 20)   # IS_STATIC | CAST_STATIC_SHADOWS | CAST_DYNAMIC_SHADOWS


def _make_entity(it: dict):
    """Construieste o entitate szio dintr-un dict (coordonate deja mondiale)."""
    from szio.gta5 import Entity, EntityFlags, EntityLodLevel, EntityPriorityLevel
    from szio.types import Vector, Quaternion
    return Entity(
        archetype_name=it["archetype"], position=Vector(tuple(it["pos"])), rotation=Quaternion(tuple(it["rot"])),
        scale_xy=float(it["scale"][0]), scale_z=float(it["scale"][1]),
        flags=EntityFlags(int(it.get("flags", ENTITY_FLAGS_STATIC))), guid=int(it["guid"]), parent_index=-1,
        lod_dist=float(it["lod"]), child_lod_dist=0.0,
        lod_level=EntityLodLevel[it.get("lod_level", "ORPHANHD")],
        priority_level=EntityPriorityLevel[it.get("priority", "REQUIRED")],
        num_children=0, ambient_occlusion_multiplier=255, artificial_ambient_occlusion=255, tint_value=0,
        extensions=[],
    )


def write_ymap(map_name: str, items: list, out_dir: str, gen9: bool = False):
    """
    Scrie <map_name>.ymap din lista de dict-uri:
      {archetype, pos:[x,y,z], rot:[w,x,y,z], scale:[xy,z], lod, bb:[[..],[..]], guid, flags, lod_level, priority}
    `bb` sunt extents-urile LOCALE ale entitatii (relativ la pozitie), pentru extents-urile de streaming.
    """
    from szio.gta5 import AssetMapData, MapContentFlags, MapFlags, save_asset
    from szio.types import Vector
    entities = []
    emin = np.array([np.inf, np.inf, np.inf])
    emax = -emin.copy()
    smin = emin.copy()
    smax = emax.copy()
    for it in items:
        entities.append(_make_entity(it))
        pos = np.asarray(it["pos"], dtype=np.float64)
        wmin = pos + np.asarray(it["bb"][0], dtype=np.float64)
        wmax = pos + np.asarray(it["bb"][1], dtype=np.float64)
        emin = np.minimum(emin, wmin)
        emax = np.maximum(emax, wmax)
        smin = np.minimum(smin, wmin - it["lod"])
        smax = np.maximum(smax, wmax + it["lod"])
    if not entities:
        emin = emax = smin = smax = np.zeros(3)
    md = AssetMapData(
        name=map_name, parent_name="", flags=MapFlags(0), content_flags=MapContentFlags.HAS_ENTITIES_HD,
        streaming_extents=(Vector(tuple(smin.tolist())), Vector(tuple(smax.tolist()))),
        entities_extents=(Vector(tuple(emin.tolist())), Vector(tuple(emax.tolist()))),
        entities=entities,
    )
    save_asset(md, _targets(gen9), Path(out_dir), map_name)
    return map_name


def custom_items(cfg: C.MapConfig, objects: list) -> list:
    """Transforma lista din editor/objects.json in items pentru write_ymap."""
    items = []
    for i, o in enumerate(objects):
        model = str(o["model"])
        rxy, hz = PROP_EXTENT.get(_kind_of(model), PROP_EXTENT_DEFAULT)
        oid = str(o.get("id") or f"{model}:{i}")
        items.append(dict(
            archetype=model, pos=[float(o["x"]), float(o["y"]), float(o["z"])],
            rot=list(_rot_quat(float(o.get("rx", 0.0)), float(o.get("ry", 0.0)), float(o.get("rz", 0.0)))),
            scale=[float(o.get("scale", 1.0)), float(o.get("scale", 1.0))],
            lod=float(o.get("lod", cfg.lod_dist_small_prop)),
            bb=[[-rxy, -rxy, -1.0], [rxy, rxy, hz]],
            guid=_guid(f"{cfg.name}_custom:{oid}"), flags=ENTITY_FLAGS_STATIC,
            lod_level="ORPHANHD", priority="REQUIRED",
        ))
    return items


def read_objects_json(path) -> tuple:
    """Returneaza (obiecte, guid-uri sterse). Fisier lipsa -> ([], set())."""
    p = Path(path)
    if not p.is_file():
        return [], set()
    with open(p, "r", encoding="utf-8-sig") as fh:
        data = json.load(fh)
    objs = data.get("objects") or []
    removed = set(int(g) for g in (data.get("removed") or []))
    return objs, removed


def mark_objects_exported(path, when_ms: int | None = None) -> int:
    """
    Scrie "exportedAt" (epoch in MILISECUNDE) in objects.json, pastrand neatinse
    "objects", "removed" si orice alte chei. Editorul din joc spawneaza la runtime doar
    obiectele mai noi decat aceasta valoare (restul sunt deja in .ymap-ul exportat).
    """
    import time
    p = Path(path)
    if not p.is_file():
        return 0
    with open(p, "r", encoding="utf-8-sig") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        return 0
    stamp = int(when_ms if when_ms is not None else time.time() * 1000)
    data["exportedAt"] = stamp
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, p)
    return stamp


def export_ymaps(cfg: C.MapConfig, world, bounds: dict, tile_names: dict, building_names: dict,
                 out_dir: str, gen9: bool, log=print, removed: set | None = None,
                 custom_objects: list | None = None, editor_dir: str | None = None) -> list:
    removed = set(removed or ())
    ox, oy = cfg.origin_x, cfg.origin_y
    chunk = cfg.chunk_size
    nchunks = int(math.ceil(cfg.size / chunk))
    # entitati per chunk: [(archetype, x, y, z, yaw, scale, lod_dist, (rxy, hz) extents)]
    per_chunk = {}

    def add(cx, cy, item):
        key = (min(max(int(cx // chunk), 0), nchunks - 1), min(max(int(cy // chunk), 0), nchunks - 1))
        per_chunk.setdefault(key, []).append(item)

    # teren: o entitate per tile, in chunk-ul in care cade centrul tile-ului
    for (ti, tj), name in tile_names.items():
        cx = (ti + 0.5) * cfg.tile_size
        cy = (tj + 0.5) * cfg.tile_size
        bmin, bmax = bounds[name]
        add(cx, cy, dict(name=name, x=cx, y=cy, z=0.0, yaw=0.0, scale=1.0, lod=cfg.lod_dist_terrain,
                         bb=(np.array(bmin), np.array(bmax)), terrain=True, kind="terrain"))
    # cladiri custom
    for b in world.buildings:
        name = building_names[b.name]
        bmin, bmax = bounds[name]
        r = float(max(abs(bmin[0]), abs(bmax[0]), abs(bmin[1]), abs(bmax[1]))) * 1.42
        add(b.x, b.y, dict(name=name, x=b.x, y=b.y, z=b.z, yaw=b.yaw, scale=1.0, lod=cfg.lod_dist_building,
                           bb=(np.array([-r, -r, float(bmin[2])]), np.array([r, r, float(bmax[2])])),
                           kind="building"))
    # props vanilla
    for p in world.props:
        kind = _kind_of(p.name)
        rxy, hz = PROP_EXTENT.get(kind, PROP_EXTENT_DEFAULT)
        rxy *= p.scale
        hz *= p.scale
        add(p.x, p.y, dict(name=p.name, x=p.x, y=p.y, z=p.z, yaw=p.yaw, scale=p.scale, lod=p.lod_dist,
                           bb=(np.array([-rxy, -rxy, -1.0]), np.array([rxy, rxy, hz])), kind=kind))

    names = []
    total = 0
    skipped = 0
    chunks_json = []
    entities_json = []
    for (ci, cj), items in sorted(per_chunk.items()):
        map_name = f"{cfg.name}_c{ci:02d}_{cj:02d}"
        out_items = []
        for k, it in enumerate(items):
            # GUID determinist: crc32("<map>:<index>:<arhetip>"); indexul e stabil pentru un seed/config dat
            guid = _guid(f"{map_name}:{k}:{it['name']}")
            if guid in removed:
                skipped += 1
                continue
            bmin, bmax = it["bb"]
            rec = dict(
                archetype=it["name"], pos=[it["x"] + ox, it["y"] + oy, it["z"]],
                rot=list(_rot_quat(0.0, 0.0, it["yaw"], degrees=False)),
                scale=[it["scale"], it["scale"]], lod=float(it["lod"]),
                bb=[[float(v) for v in bmin], [float(v) for v in bmax]],
                guid=guid, flags=ENTITY_FLAGS_STATIC, lod_level="ORPHANHD", priority="REQUIRED",
            )
            out_items.append(rec)
            if not it.get("terrain"):
                entities_json.append(dict(guid=guid, model=str(it["name"]).lower(),
                                          x=rec["pos"][0], y=rec["pos"][1],
                                          z=rec["pos"][2], rz=math.degrees(it["yaw"]) % 360.0,
                                          kind=it.get("kind", "prop")))
        write_ymap(map_name, out_items, out_dir, gen9)
        chunks_json.append(dict(name=map_name, entities=out_items))
        names.append(map_name)
        total += len(out_items)
    log(f"  ymap: {len(names)} chunk-uri, {total} entitati" + (f" ({skipped} sterse din editor)" if skipped else ""))

    # ymap separat pentru obiectele puse manual din editorul in joc
    citems = custom_items(cfg, custom_objects or [])
    custom_name = f"{cfg.name}_custom"
    write_ymap(custom_name, citems, out_dir, gen9)
    names.append(custom_name)
    log(f"  ymap manual: {custom_name} ({len(citems)} obiecte)")

    if editor_dir:
        ed = Path(editor_dir)
        ed.mkdir(parents=True, exist_ok=True)
        (ed / "entities.json").write_text(json.dumps(entities_json, indent=1), encoding="utf-8")
        (ed / "chunks.json").write_text(json.dumps(
            dict(version=1, name=cfg.name, origin=[ox, oy], custom_map=custom_name, chunks=chunks_json),
            indent=1), encoding="utf-8")
        log(f"  editor: entities.json ({len(entities_json)} entitati) + chunks.json -> {ed}")
    return names


# ----------------------------------------------------------------------------------------- packaging

def _asset_files(asset_dir: str):
    return sorted(p for p in Path(asset_dir).iterdir()
                  if p.suffix.lower() in (".ydr", ".ybn", ".ytd", ".ytyp", ".ymap"))


def minimap_client_script(cfg: C.MapConfig, gfx_rel: str, w_px: int, h_px: int) -> str:
    """Script client (JS) pus in resursa: incarca overlay-ul .gfx si il aseaza pe radar/harta mare."""
    from .minimap_swf import overlay_display_args
    x, y, sx, sy = overlay_display_args(cfg.origin_x, cfg.origin_y, cfg.size, w_px, h_px)
    return f"""/* Harta {cfg.name} pe radar si pe harta mare (pauza): overlay Scaleform cu imaginea generata.
   Generat de dayz_map_gen - nu edita de mana, se rescrie la fiecare generare. */
const FILE = '{gfx_rel}';
const X = {x:.1f}, Y = {y:.1f}, SCALE_X = {sx:.4f}, SCALE_Y = {sy:.4f};   // 100 = 1 px per metru
let overlay = -1;
const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function showOverlay() {{
    // minimap-ul exista doar dupa ce jucatorul e in lume
    while (!NetworkIsPlayerActive(PlayerId())) await wait(500);
    overlay = AddMinimapOverlay(FILE);
    const started = GetGameTimer();
    while (!HasMinimapOverlayLoaded(overlay)) {{
        if (GetGameTimer() - started > 60000) {{
            console.log(`[{cfg.name}] overlay-ul de minimap nu s-a incarcat: ${{FILE}}`);
            return;
        }}
        await wait(100);
    }}
    SetMinimapOverlayDisplay(overlay, X, Y, SCALE_X, SCALE_Y, 100.0);
    console.log(`[{cfg.name}] minimap overlay ${{overlay}} din ${{FILE}} afisat la X=${{X}} Y=${{Y}} scara=${{SCALE_X}} (vezi F8)`);
}}

setTimeout(showOverlay, 1000);

// comenzi de test (F8 / chat): /minimap_test = un dreptunghi rosu in locul hartii (fara imagine: daca el apare si
// harta nu, jocul refuza imaginea); /minimap_y = intoarce semnul lui Y; /minimap_scale <n> = alta scara
let test = -1, ySign = 1.0, scale = SCALE_X;
const tests = {{}};
function place(id) {{ if (id >= 0) SetMinimapOverlayDisplay(id, X, Y * ySign, scale, scale, 100.0); }}
RegisterCommand('minimap_test', async (src, args) => {{
    const kind = (args[0] || 'a').toLowerCase();       // a = GFX+ExporterInfo, b = SWF simplu, c = GFX simplu
    if (kind === 'd') return showTexture('commonmenu', 'shop_tick_icon');
    if (kind === 'e') return showTexture(`${{NAME}}_map`, `${{NAME}}_map`);
    const file = FILE.replace('.gfx', `_test_${{kind}}.gfx`);
    if (!(kind in tests)) {{
        tests[kind] = AddMinimapOverlay(file);
        while (!HasMinimapOverlayLoaded(tests[kind])) await wait(100);
    }}
    test = tests[kind];
    place(test);
    console.log(`[{cfg.name}] test overlay ${{test}} din ${{file}} la X=${{X}} Y=${{Y * ySign}} scara=${{scale}}`);
}}, false);
// varianta cu textura din .ytd, prin incarcatorul cu ActionScript (<nume>_loader.gfx):
//   minimap_test d = o bifa din jocul de baza (commonmenu/shop_tick_icon) intinsa peste oras
//   minimap_test e = harta noastra (textura <nume>_map din stream/<nume>_map.ytd)
//   minimap_tex <txd> <txn> = orice textura
let loader = -1, tiles = 0;
const NAME = GetCurrentResourceName();
async function showTexture(txd, txn) {{
    if (loader < 0) {{
        loader = AddMinimapOverlay(FILE.replace('_minimap.gfx', '_loader.gfx'));
        while (!HasMinimapOverlayLoaded(loader)) await wait(100);
        SetMinimapOverlayDisplay(loader, 0.0, 0.0, 100.0, 100.0, 100.0);
    }}
    RequestStreamedTextureDict(txd, false);
    const t0 = GetGameTimer();
    while (!HasStreamedTextureDictLoaded(txd)) {{
        if (GetGameTimer() - t0 > 8000) {{ console.log(`[{cfg.name}] textura ${{txd}} nu s-a incarcat`); return; }}
        await wait(50);
    }}
    const [tw, th] = GetTextureResolution(txd, txn);
    const sizeM = SCALE_X * {w_px} / 100.0;                 // latura hartii, in metri
    const sx = sizeM / Math.max(tw, 1) * 100.0, sy = sizeM / Math.max(th, 1) * 100.0;
    CallMinimapScaleformFunction(loader, 'ADD_SCALED_OVERLAY');
    ScaleformMovieMethodAddParamTextureNameString(txd);
    ScaleformMovieMethodAddParamTextureNameString(txn);
    ScaleformMovieMethodAddParamFloat(X);               // coltul de nord-vest, in coordonate de joc
    ScaleformMovieMethodAddParamFloat(-Y);
    ScaleformMovieMethodAddParamFloat(0.0);
    ScaleformMovieMethodAddParamFloat(sx);
    ScaleformMovieMethodAddParamFloat(sy);
    ScaleformMovieMethodAddParamInt(100);
    ScaleformMovieMethodAddParamBool(false);
    EndScaleformMovieMethod();
    tiles++;
    console.log(`[{cfg.name}] textura ${{txd}}/${{txn}} (${{tw}}x${{th}}) pusa la X=${{X}} Y=${{-Y}} scara=${{sx.toFixed(1)}}`);
}}
RegisterCommand('minimap_tex', (src, args) => {{ if (args.length >= 2) showTexture(args[0], args[1]); }}, false);
RegisterCommand('minimap_y', () => {{ ySign = -ySign; place(overlay); place(test); console.log(`[{cfg.name}] Y=${{Y * ySign}}`); }}, false);
RegisterCommand('minimap_scale', (src, args) => {{
    scale = parseFloat(args[0]) || SCALE_X; place(overlay); place(test); console.log(`[{cfg.name}] scara=${{scale}}`);
}}, false);

on('onResourceStop', (name) => {{
    if (name !== GetCurrentResourceName()) return;
    for (const id of [overlay, loader, ...Object.values(tests)]) {{
        if (id < 0) continue;
        if (typeof RemoveMinimapOverlay === 'function') RemoveMinimapOverlay(id);
        else SetMinimapOverlayDisplay(id, X, Y, SCALE_X, SCALE_Y, 0.0);
    }}
}});
"""


def minimap_loader_script(name: str, loader: str, tex: str, west: float, north: float, size: float) -> str:
    """Script client (JS): harta ca textura din stream/<tex>.ytd, pusa pe radar si pe harta mare de <loader>
    (incarcatorul Scaleform MINIMAP_LOADER.gfx din resursa "Extra Map Tiles" de L1CKS / Lughworks). Singura metoda
    verificata in joc: un .swf scris de noi, cu imaginea inauntru, se incarca dar nu se deseneaza."""
    return f"""/* Harta {name} pe radar si pe harta mare: textura {tex} din stream/{tex}.ytd, pusa de {loader}
   (incarcator Scaleform din resursa Extra Map Tiles, L1CKS / Lughworks). Generat la export - nu edita de mana. */
const LOADER = '{loader}', TXD = '{tex}', TXN = '{tex}';
const WEST = {west:.1f}, NORTH = {north:.1f}, SIZE = {size:.1f};   // coltul de nord-vest si latura, in metri
let overlay = -1;
const blips = [];
const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function show() {{
    while (!NetworkIsPlayerActive(PlayerId())) await wait(500);
    overlay = AddMinimapOverlay(LOADER);
    while (!HasMinimapOverlayLoaded(overlay)) await wait(100);
    SetMinimapOverlayDisplay(overlay, 0.0, 0.0, 100.0, 100.0, 100.0);
    RequestStreamedTextureDict(TXD, false);
    const started = GetGameTimer();
    while (!HasStreamedTextureDictLoaded(TXD)) {{
        if (GetGameTimer() - started > 15000) {{
            console.log(`[{name}] textura hartii nu s-a incarcat: ${{TXD}}.ytd`);
            return;
        }}
        await wait(50);
    }}
    const [tw, th] = GetTextureResolution(TXD, TXN);
    CallMinimapScaleformFunction(overlay, 'ADD_SCALED_OVERLAY');
    ScaleformMovieMethodAddParamTextureNameString(TXD);
    ScaleformMovieMethodAddParamTextureNameString(TXN);
    ScaleformMovieMethodAddParamFloat(WEST);
    ScaleformMovieMethodAddParamFloat(NORTH);
    ScaleformMovieMethodAddParamFloat(0.0);                                  // rotire
    ScaleformMovieMethodAddParamFloat(SIZE / Math.max(tw, 1) * 100.0);        // 100 = 1 px pe metru
    ScaleformMovieMethodAddParamFloat(SIZE / Math.max(th, 1) * 100.0);
    ScaleformMovieMethodAddParamInt(100);                                    // opacitate
    ScaleformMovieMethodAddParamBool(false);                                 // ancorat in coltul de nord-vest
    EndScaleformMovieMethod();
    SetStreamedTextureDictAsNoLongerNeeded(TXD);
    // harta mare din pauza se deruleaza doar pana la ultimul blip: patru blipuri invizibile in colturile orasului
    for (const [x, y] of [[WEST, NORTH], [WEST + SIZE, NORTH], [WEST, NORTH - SIZE], [WEST + SIZE, NORTH - SIZE]]) {{
        const blip = AddBlipForCoord(x, y, 1.0);
        SetBlipDisplay(blip, 4);
        SetBlipAlpha(blip, 0);
        blips.push(blip);
    }}
    console.log(`[{name}] harta pe minimap: ${{TXD}} (${{tw}}x${{th}}) la X=${{WEST}} Y=${{NORTH}}, latura ${{SIZE}} m`);
}}

setTimeout(show, 1000);

on('onResourceStop', (res) => {{
    if (res !== GetCurrentResourceName()) return;
    if (overlay >= 0) {{
        CallMinimapScaleformFunction(overlay, 'REM_OVERLAY');
        ScaleformMovieMethodAddParamInt(0);
        EndScaleformMovieMethod();
    }}
    for (const blip of blips) RemoveBlip(blip);
}});
"""


def package_fivem(cfg: C.MapConfig, asset_dir: str, out_dir: str, ytyp_name: str, log=print,
                  editor_dir: str | None = None, minimap_file: str | None = None) -> str:
    res_dir = Path(out_dir) / "fivem" / cfg.name
    stream = res_dir / "stream"
    # pastram obiectele puse manual din editor, daca resursa a mai fost impachetata o data
    keep = None
    old_obj = res_dir / cfg.custom_objects_file.replace("\\", "/")
    if old_obj.is_file():
        keep = old_obj.read_bytes()
    if res_dir.exists():
        shutil.rmtree(res_dir)
    stream.mkdir(parents=True)
    for f in _asset_files(asset_dir):
        shutil.copy2(f, stream / f.name)
    if editor_dir and Path(editor_dir).is_dir():
        shutil.copytree(editor_dir, res_dir / "editor", dirs_exist_ok=True)
    if keep is not None:
        old_obj.parent.mkdir(parents=True, exist_ok=True)
        old_obj.write_bytes(keep)
    nybn = sum(1 for f in _asset_files(asset_dir) if f.suffix.lower() == ".ybn")
    if nybn == 0:
        log("  ATENTIE: nu exista fisiere .ybn -> nimic nu va fi solid in joc!")

    # overlay de minimap (radar + harta mare) + scriptul client care il aseaza in lume
    minimap_lua = ""
    if minimap_file and Path(minimap_file).is_file():
        gfx_rel = f"minimap/{Path(minimap_file).name}"
        (res_dir / "minimap").mkdir(exist_ok=True)
        shutil.copy2(minimap_file, res_dir / gfx_rel)
        px = int(cfg.minimap_px)
        (res_dir / "client").mkdir(exist_ok=True)
        (res_dir / "client" / "minimap.js").write_text(minimap_client_script(cfg, gfx_rel, px, px), encoding="utf-8")
        minimap_lua = f"""
-- harta pe radar / harta mare: overlay Scaleform (AddMinimapOverlay) + scriptul care il pozitioneaza
files {{ '{gfx_rel}' }}
client_script 'client/minimap.js'
"""
        log(f"  minimap: {gfx_rel} + client/minimap.js")

    manifest = f"""fx_version 'cerulean'
game 'gta5'

author 'dayz_map_gen'
description 'Harta stil DayZ generata procedural ({cfg.name})'

this_is_a_map 'yes'

-- arhetipurile custom (teren + cladiri) trebuie cerute explicit
data_file 'DLC_ITYP_REQUEST' 'stream/{ytyp_name}.ytyp'
{minimap_lua}"""
    (res_dir / "fxmanifest.lua").write_text(manifest, encoding="utf-8")
    log(f"  FiveM: {res_dir}")
    return str(res_dir)


def _content_xml(dlc: str, inner: str, ytyp_name: str) -> str:
    rpf = f"dlc_{dlc}:/x64/levels/gta5/{inner}/{inner}.rpf"
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<CDataFileMgr__ContentsOfDataFileXml>
  <disabledFiles />
  <includedXmlFiles />
  <includedDataFiles />
  <dataFiles>
    <Item>
      <filename>{rpf}</filename>
      <fileType>RPF_FILE</fileType>
      <overlay value="false" />
      <disabled value="true" />
      <persistent value="false" />
    </Item>
    <Item>
      <filename>{rpf}/{ytyp_name}.ytyp</filename>
      <fileType>DLC_ITYP_REQUEST</fileType>
      <overlay value="false" />
      <disabled value="true" />
      <persistent value="true" />
    </Item>
  </dataFiles>
  <contentChangeSets>
    <Item>
      <changeSetName>{dlc}_AUTOGEN</changeSetName>
      <mapChangeSetData />
      <filesToInvalidate />
      <filesToDisable />
      <filesToEnable>
        <Item>{rpf}</Item>
        <Item>{rpf}/{ytyp_name}.ytyp</Item>
      </filesToEnable>
      <txdToLoad />
      <txdToUnload />
      <residentResources />
      <unregisterResources />
      <requiresLoadingScreen value="false" />
      <useCacheLoader value="false" />
    </Item>
  </contentChangeSets>
  <patchFiles />
</CDataFileMgr__ContentsOfDataFileXml>
"""


def _setup2_xml(dlc: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<SSetupData>
  <deviceName>dlc_{dlc}</deviceName>
  <datFile>content.xml</datFile>
  <timeStamp>01/01/2026 00:00:00</timeStamp>
  <nameHash>{dlc}</nameHash>
  <contentChangeSets />
  <contentChangeSetGroups>
    <Item>
      <NameHash>GROUP_STARTUP</NameHash>
      <ContentChangeSets>
        <Item>{dlc}_AUTOGEN</Item>
      </ContentChangeSets>
    </Item>
  </contentChangeSetGroups>
  <startupScript />
  <scriptCallstackSize value="0" />
  <type>EXTRACONTENT_COMPAT_PACK</type>
  <order value="1000" />
  <minorOrder value="0" />
  <isLevelPack value="false" />
  <dependencyPackHash />
  <requiredVersion />
  <subPackCount value="0" />
</SSetupData>
"""


def package_ragemp(cfg: C.MapConfig, asset_dir: str, out_dir: str, ytyp_name: str, log=print) -> str:
    """Construieste dlc.rpf (RPF7, necriptat) cu pymateria: content.xml + setup2.xml + rpf interior cu asset-urile."""
    from pymateria.rpf7 import (PackFile, PackFileEntryDirectory, PackFileEntryFile, PackFileEntryResource,
                                PackFileEntryArchive)
    dlc = cfg.name
    pack_dir = Path(out_dir) / "ragemp" / "dlcpacks" / dlc
    pack_dir.mkdir(parents=True, exist_ok=True)
    pf = PackFile.create()

    def add(entry):
        pf.add_entry(entry, True)
        return entry

    def add_dir(parent_pf, path):
        e = PackFileEntryDirectory(parent_pf, path)
        parent_pf.add_entry(e, True)
        return e

    add(PackFileEntryFile.create(pf, "content.xml", _content_xml(dlc, dlc, ytyp_name).encode("utf-8")))
    add(PackFileEntryFile.create(pf, "setup2.xml", _setup2_xml(dlc).encode("utf-8")))
    add_dir(pf, "x64")
    add_dir(pf, "x64/levels")
    add_dir(pf, "x64/levels/gta5")
    add_dir(pf, f"x64/levels/gta5/{dlc}")
    inner_entry = add(PackFileEntryArchive.create(pf, f"x64/levels/gta5/{dlc}/{dlc}.rpf"))
    inner = inner_entry.archive
    n = 0
    for f in _asset_files(asset_dir):
        inner.add_entry(PackFileEntryResource.create(inner, f.name, str(f)), True)
        n += 1
    rpf_path = pack_dir / "dlc.rpf"
    with open(rpf_path, "wb") as fh:
        PackFile.export_rpf(pf, fh)
    log(f"  RAGE:MP: {rpf_path} ({n} fisiere, {rpf_path.stat().st_size // 1024} KB)")
    return str(rpf_path)
