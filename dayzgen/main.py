# -*- coding: utf-8 -*-
"""
Orchestrare: texturi -> lume -> obiecte Blender -> export .ydr (Sollumz) -> ytd/ytyp/ymap (szio) -> pachete.
Se ruleaza din Blender (vezi run_dayz_map.py).
"""
import copy
import os
import time
from pathlib import Path

from . import config as C
from . import textures, buildings, terrain


def _log_factory(log_path):
    f = open(log_path, "a", encoding="utf-8")

    def log(msg):
        line = f"[{time.strftime('%H:%M:%S')}] {msg}"
        print(line, flush=True)
        f.write(line + "\n")
        f.flush()
    return log


def run(preset: str | None = "demo", out_root: str | None = None, gen9: bool | None = None, seed: int | None = None,
        size: float | None = None, origin: tuple | None = None, name: str | None = None,
        ragemp: bool | None = None, config: str | None = None):
    if config:
        import json as _json
        with open(config, "r", encoding="utf-8-sig") as fh:
            data = _json.load(fh)
        if preset:                      # --preset din linia de comanda bate cheia "preset" din map.json
            data["preset"] = preset
        cfg = C.MapConfig.from_dict(data)
        preset = cfg.preset
    else:
        preset = preset or "demo"
        cfg = copy.deepcopy(C.PRESETS[preset])
        cfg.preset = preset
    if gen9 is not None:
        cfg.export_gen9 = gen9
    if ragemp is not None:
        cfg.package_ragemp = ragemp
    if seed is not None:
        cfg.seed = int(seed)
    if size is not None:
        cfg.size = float(size)
    if origin is not None:
        cfg.origin_x, cfg.origin_y = float(origin[0]), float(origin[1])
    if name:
        cfg.name = name.lower()
    cfg.validate()

    out_root = Path(out_root) if out_root else Path(__file__).resolve().parent.parent / "output"
    out = out_root / cfg.name
    tex_dir = out / "textures"
    asset_dir = out / "assets"
    out.mkdir(parents=True, exist_ok=True)
    asset_dir.mkdir(exist_ok=True)
    log = _log_factory(out / "log.txt")
    t0 = time.time()
    log(f"=== DayZ map gen: preset={preset} name={cfg.name} size={cfg.size:.0f}m seed={cfg.seed} ===")

    # 1. texturi
    log("Texturi...")
    texs = textures.generate_texture_set(str(tex_dir), cfg.name, cfg.seed, cfg.terrain_tex_size,
                                         cfg.building_tex_size, write_png_preview=True, log=log)

    # 2. cladiri (geometrie)
    bdefs = buildings.build_all()
    radii = {k: v["radius"] for k, v in bdefs.items()}

    # 3. lumea
    world = terrain.World(cfg, radii, log=log).generate()
    preview_img = None
    try:
        from .preview import render_map_preview
        preview_img = render_map_preview(world, str(out / "harta_preview.png"), size=int(cfg.minimap_px))
        log(f"  previzualizare harta: {out / 'harta_preview.png'}")
    except Exception as e:  # noqa
        log(f"  previzualizarea a esuat (nu e critica): {e!r}")

    # aceeasi imagine, ca overlay Scaleform pentru radar + harta mare (AddMinimapOverlay in FiveM)
    minimap_file = None
    if preview_img is not None:
        try:
            from .minimap_swf import write_minimap_gfx
            (out / "minimap").mkdir(exist_ok=True)
            minimap_file = str(out / "minimap" / f"{cfg.name}_minimap.gfx")
            write_minimap_gfx(preview_img, minimap_file)
            log(f"  minimap overlay: {minimap_file}")
        except Exception as e:  # noqa
            log(f"  minimap-ul a esuat (nu e critic): {e!r}")
            minimap_file = None

    # 4. Blender + Sollumz
    from . import blender_build, gta_export
    log("Construiesc scena Blender...")
    bb = blender_build.BlenderBuilder(cfg, world, texs, bdefs, log=log)
    bb.setup_scene()
    bb.build_buildings()
    bb.build_tiles()
    bb.build_collisions()

    # obiectele puse manual din editorul in joc + entitatile sterse de acolo
    installed = Path(cfg.fivem_resources_dir) / cfg.name / cfg.custom_objects_file.replace("\\", "/")
    local_obj = out / "fivem" / cfg.name / cfg.custom_objects_file.replace("\\", "/")
    obj_src = installed if installed.is_file() else local_obj
    t_read_ms = int(time.time() * 1000)
    try:
        custom_objects, removed = gta_export.read_objects_json(obj_src)
        if custom_objects or removed:
            log(f"  editor: {len(custom_objects)} obiecte manuale, {len(removed)} entitati sterse ({obj_src})")
    except Exception as e:  # noqa
        log(f"  ATENTIE: nu am putut citi {obj_src}: {e!r}")
        custom_objects, removed = [], set()

    variants = [("assets", False)]
    if cfg.export_gen9:
        variants.append(("assets_gen9", True))
    results = {}
    for sub, gen9_flag in variants:
        adir = out / sub
        adir.mkdir(exist_ok=True)
        bb.export_drawables(str(adir), gen9=gen9_flag)
        log("Export ytd / ytyp / ymap ...")
        gta_export.export_ytds(cfg, texs, str(adir), gen9_flag, log=log)
        ytyp_name = gta_export.export_ytyp(cfg, bb.bounds, bb.tile_names, bb.building_names, str(adir), gen9_flag, log=log)
        edir = out / ("editor" if not gen9_flag else "editor_gen9")
        ymaps = gta_export.export_ymaps(cfg, world, bb.bounds, bb.tile_names, bb.building_names, str(adir),
                                        gen9_flag, log=log, removed=removed, custom_objects=custom_objects,
                                        editor_dir=str(edir))
        log("Impachetare...")
        pk_out = out if not gen9_flag else out / "gen9"
        fivem = gta_export.package_fivem(cfg, str(adir), str(pk_out), ytyp_name, log=log, editor_dir=str(edir),
                                         minimap_file=minimap_file)
        ragemp = None
        if cfg.package_ragemp:
            try:
                ragemp = gta_export.package_ragemp(cfg, str(adir), str(pk_out), ytyp_name, log=log)
            except Exception as e:  # noqa
                log(f"  dlc.rpf a esuat: {e!r}")
        # obiectele manuale sunt acum "coapte" in <name>_custom.ymap: marcam momentul in copia
        # impachetata (nu in cea din server - ajunge acolo cand copiezi resursa)
        packed_obj = Path(fivem) / cfg.custom_objects_file.replace("\\", "/")
        if not packed_obj.is_file() and obj_src.is_file():
            packed_obj.parent.mkdir(parents=True, exist_ok=True)
            packed_obj.write_bytes(obj_src.read_bytes())
        if packed_obj.is_file():
            gta_export.mark_objects_exported(packed_obj, t_read_ms)
        results[sub] = dict(fivem=fivem, ragemp=ragemp, ymaps=ymaps, ytyp=ytyp_name)

    if cfg.keep_scene:
        bb.save_blend(str(out / f"{cfg.name}.blend"))

    # 5. rezumat
    sx, sy, sz = world.spawn_point()
    wx, wy = sx + cfg.origin_x, sy + cfg.origin_y
    lines = [
        f"Harta: {cfg.name}  ({cfg.size:.0f} x {cfg.size:.0f} m, seed {cfg.seed})",
        f"Pozitie in lumea GTA V: X {cfg.origin_x:.0f}..{cfg.origin_x + cfg.size:.0f}, "
        f"Y {cfg.origin_y:.0f}..{cfg.origin_y + cfg.size:.0f}",
        f"SPAWN (centrul satului {world.villages[0]['name'] if world.villages else ''}): "
        f"X={wx:.1f} Y={wy:.1f} Z={sz:.1f}",
        "",
        f"Sate: " + ", ".join(f"{v['name']} ({v['center'][0] + cfg.origin_x:.0f}, {v['center'][1] + cfg.origin_y:.0f})"
                             for v in world.villages),
        f"Cladiri: {len(world.buildings)}   Props vanilla: {len(world.props)}   Drumuri: {len(world.roads)}",
        f"Tile-uri teren: {len(bb.tile_names)}   Chunk-uri ymap: {len(results['assets']['ymaps'])}",
        f"Coliziuni statice: {len(bb.composites)} fisiere .ybn (fara ele nimic nu e solid in joc)",
        "",
        "INSTALARE FiveM:",
        "  1. copiaza folderul " + results["assets"]["fivem"],
        "     in resources/ (ex: " + str(Path(cfg.fivem_resources_dir) / cfg.name) + ")",
        "  2. adauga in server.cfg:  ensure " + cfg.name,
        "  3. RESTART COMPLET de server (nu doar 'refresh'/'restart resursa' - fisierele de streaming",
        "     si coliziunile .ybn se incarca doar la pornirea serverului si a clientului),",
        "     apoi intra in joc si da teleport la coordonatele de mai sus:",
        f"     /tp {wx:.1f} {wy:.1f} {sz:.1f}    (sau, dintr-un script client: SetEntityCoords(PlayerPedId(), {wx:.1f}, {wy:.1f}, {sz:.1f}, false, false, false, false))",
    ] + ([
        "dlc.rpf (RAGE:MP): output/" + cfg.name + "/ragemp/dlcpacks/" + cfg.name + "/dlc.rpf",
    ] if results["assets"]["ragemp"] else []) + [
        f"Timp total: {time.time() - t0:.0f} s",
    ]
    (out / "REZUMAT.txt").write_text("\n".join(lines), encoding="utf-8")
    for ln in lines:
        log(ln)
    log("=== GATA ===")
    return str(out)
