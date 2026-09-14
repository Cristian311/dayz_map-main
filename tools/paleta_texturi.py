# -*- coding: utf-8 -*-
"""
Paleta de texturi GTA pentru editorul din joc (/mapeditor): toate texturile de suprafata din biblioteca extrasa
(output/gta_asset_library/*.dds), pe familii, in cateva .ytd-uri streamate de rrp_mapeditor (fiecare sub 16 MB,
limita de streaming FiveM). Editorul le pune in locul texturilor orasului cu AddReplaceTexture (previzualizare cu
lumina reala); exportul orasului (tools/tex_overrides.py) ia textura aleasa tot din biblioteca, dupa nume.

Scrie in resursa editorului:
  stream/rrp_paleta.ytd, rrp_paleta_2.ytd, ...   texturile, 256 px DXT1 (~12 MB pe fisier)
  nui/paleta/<textura>.jpg                        miniaturile pentru grila din editor (96 px)
  paleta.json    {"familii": [{"id", "nume", "texturi": [{"tex", "scala", "normal", "txd"}]}]}

Rulare (o data, sau cand biblioteca are texturi noi):  tools\\_blender.bat -b -P tools\\paleta_texturi.py [-- --out <resursa>]
"""
import json
import re
import struct
import sys
from pathlib import Path

import bpy
import numpy as np

SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parent.parent
LIB = ROOT / "output" / "gta_asset_library"
TXD = "rrp_paleta"
SIZE, THUMB = 256, 96
PER_TXD = 280           # 280 x 44 KB = ~12 MB pe .ytd (FiveM nu streameaza fisiere peste 16 MB)

# (id, nume in editor, metri per repetare, texturi alese de mana). Cele alese de mana stau primele in familia lor
# (se repeta bine); dupa ele vin singure celelalte texturi din biblioteca, dupa cuvintele din nume (MATCH).
FAMILIES = [
    ("iarba", "Iarba", 4.0, [
        "im_grass02", "im_grass02v", "im_grass03", "im_grass05", "im_grass07b", "im_grass10b", "im_grass10c",
        "im_grass11b", "im_grass13b", "im_grass13c", "im_grass014b", "am_grass_green", "am_grass_lawn",
        "dh_ch02_grass_01", "cs_rsn_sl_lushgrassrock2", "cs_rsn_sl_wetlandsgrass3", "cs_tf_rsn_trazgrass1",
        "tf_rsn_drygrass3", "rsn_os_grassthick", "am_glue_grassdirt", "cs_rsn_sl_canyongrassdirt_01"]),
    ("pamant", "Pamant, pietris, nisip", 4.0, [
        "im_ground_dirt001", "im_ground_dirt002", "im_ground_dirt004", "am_glue_dirtbrown",
        "rsn_am_ground_dirt_leaflitter", "rsn_am_ground_dirt_leaflitter_2", "dc_rsn_cs2_02_soil_02",
        "cs_rsn_tf_lushsoilscree", "rsn_et_gravel003", "city_dh_ch02_gravel_01", "dh_ch02_gravel_01",
        "cs_rsn_sl_desgravel_0001", "cs_rsn_sl_bchsand_02", "cs_rsn_sl_bchsand_03", "og_cs_dirtscrub_d4",
        "rn_tf_mudbank_002"]),
    ("pavaj", "Pavaj, trotuar, dale", 3.0, [
        "dc_sidewalk001", "dc_sidewalk002", "dc_sidewalk004", "im_sidewalk01", "im_sidewalk02", "im_sidewalk003",
        "im_sidewalk006", "im_sidewalk007", "im_sidewalk009", "im_sidewalk010", "im_sidewalk011", "im_sidewalk012",
        "im_sidewalk013", "im_sidewalk014", "im_sidewalk015", "im_sidewalk017", "im_sidewalk018", "im_sidewalk019",
        "im_sidewalk020", "bh1_04_rsn_rls_sidewalk_0001", "rsn_dc_archedcobbles_0001", "rsn_dc_ground_tiles_0001",
        "rsn_dc_tiles_0001", "am_ap_concreteslabs_dark2", "am_ap_concreteslabs3_dark2", "im_ground_bricks02",
        "im_ground_bricks03", "rsn_am_teracottatile_03", "rsn_ns_teracottatile_0001",
        "sm1_22_rsn_dc_concretewalkway_0001"]),
    ("asfalt", "Asfalt", 6.0, [
        "dc_parking_tarmac_01", "dc_parking_tarmac_02", "dc_parking_tarmac_03", "dc_parking_tarmac_04",
        "et_tarmacbusted02", "rsn_os_beachtarmac", "rsn_os_beachtarmac_02", "cs_rsn_sl_road_0007"]),
    ("caramida", "Caramida", 1.6, [
        "im_wall_brick_31", "im_wall_brick_32", "im_wall_brick_36", "im_wall_brick_37", "dt1_19_rsd_dr_abrick_02",
        "hw11_rk_rsn_newbrick", "hw11_rk_rsn_taxibrick", "rsn_et_brick003", "rsn_mh_whitebricktile01",
        "rsn_am_bricktile_01", "bt1_01_brkwall7"]),
    ("tencuiala", "Tencuiala, beton", 3.0, [
        "im_wall_plaster32", "im_wall_plaster34", "im_wall_plaster35", "im_wall_plaster38", "im_wall_plaster48",
        "im_wall_concrete31", "im_wall_concrete32", "im_wall_concrete32_lite", "im_concrete03", "im_concrete05",
        "im_concrete09", "im_concrete11", "im_concrete15", "im_concrete17", "im_concrete19", "im_concrete25",
        "im_concrete29", "im_concrete31", "env_stucco", "env_smooth_concrete2", "hw13_rk_rsn_newrender",
        "rsn_mh_wall_concrete_0001", "rsn_am_wall_concrete_painted_white", "rsn_am_wall_concrete_painted_red",
        "rsn_am_wall_concrete_painted_black", "mw_concwall_01", "im_wall01", "im_wall03", "im_wall11", "im_wall12",
        "im_wall14", "im_wall16", "im_wall21", "im_wall26"]),
    ("acoperis", "Acoperis", 3.0, [
        "im_roof01", "im_roof04", "im_roof05", "im_roof06", "im_roof07", "im_roof08", "im_roof11",
        "kt1_12_feltroof_01a", "rsn_am_dc_roof_tile_01", "rsn_dc_roofgravel_001", "os_ml_ssroof_0001",
        "os_ml_idroof_0001", "sjm_metalroof1", "indust_metroof1", "rsn_os_copperroof_001", "bh1_17_rsn_ql_roof_0001",
        "id2_11_rntg_roof_0001"]),
    ("lemn", "Lemn", 2.0, ["im_wood_panels_08", "bh1_16_wood_planks_01"]),
    ("metal", "Metal, tabla", 2.0, ["ap1_01_corrugone", "rsn_dc_metal_0001"]),
    # firmele si vitrinele magazinelor (tools/crop_firme.py): intinse pe toata placa / vitrina (scala 0)
    ("firme", "Firme si vitrine", 0.0, sorted(p.stem for p in LIB.glob("firma_*.dds"))
     + sorted(p.stem for p in LIB.glob("vitrina_*.dds"))),
    ("altele", "Altele", 3.0, []),
]
# familia unei texturi din biblioteca dupa nume, in ordinea asta (roof_tile e acoperis, nu pavaj; wall_brick e
# caramida, nu tencuiala)
MATCH = [
    ("acoperis", r"roof|shingle|slate"),
    ("iarba", r"grass|lawn|turf|moss|meadow"),
    ("asfalt", r"tarmac|asphalt|runway|road"),
    ("caramida", r"brick|brk"),
    ("pavaj", r"sidewalk|pavement|pave|tile|cobble|slab|walkway|plaza|footpath|floor"),
    ("lemn", r"wood|plank|timber|board|deck"),
    ("metal", r"metal|corrug|steel|iron|rust|shutter"),
    ("tencuiala", r"plaster|concrete|conc|stucco|render|cement|wall|marble"),
    ("pamant", r"dirt|soil|mud|sand|gravel|grvl|ground|scree|scrub|rock|stone|pebble"),
]
# nu sunt texturi de suprafata: harti de relief / luciu / masca, LOD-uri, ferestre, firme, fire, decaluri, plante
SKIP = re.compile(
    r"(_n|_nm|_nrm|_norm|_normal|_s|_spec|_sp|_h|_a|_alpha|_lod|_slod|_pal|_em|_emissive|_bump|_mask|_detail|_ao|_msk)"
    r"(\d*|_\w{0,3})$"
    r"|mask|superlod|slod|decal|window|_win_|glass|sign|brand|logo|poster|graffiti|wire|strip|cable|neon|light|lamp|"
    r"shadow|cloud|sky|water|leaf|foliage|tree|bush|plant|flower|hedge|ivy|palm|fence|elecbox|_dm|_tm$")


def resources_dir() -> Path:
    """Folderul cu resursele FiveM (ca import_din_joc.resources_dir)."""
    try:
        cfg = json.loads((ROOT / "map.json").read_text(encoding="utf-8"))
        if cfg.get("fivem_resources_dir"):
            return Path(cfg["fivem_resources_dir"])
    except (OSError, ValueError):
        pass
    return Path(r"C:\FXServer\server-data\resources\[rrp]")


def known_scales() -> dict:
    """Metri per repetare pentru texturile folosite deja de generator (GTA_MATS)."""
    out = {}
    try:
        import runpy
        mats = runpy.run_path(str(ROOT / "tools" / "blender_gen_buildings.py"), run_name="paleta")["GTA_MATS"]
        for opts in mats.values():
            for name, scale in opts:
                if scale > 0:
                    out.setdefault(name, scale)
    except Exception as error:      # paleta merge si cu scalele familiilor
        print(f"PALETA avertisment: nu am citit GTA_MATS ({error})")
    return out


def surface_texture(path: Path) -> bool:
    """O textura de suprafata: DXT1 (fara alfa: decalurile si plantele au), cel putin 128 px, cel mult 2:1."""
    if SKIP.search(path.stem.lower()):
        return False
    try:
        with path.open("rb") as f:
            head = f.read(128)
    except OSError:
        return False
    if head[:4] != b"DDS " or head[84:88] != b"DXT1":
        return False
    h, w = struct.unpack("<II", head[12:20])
    return min(w, h) >= 128 and max(w, h) <= 2 * min(w, h)


def family_of(tex: str) -> str:
    for fid, rx in MATCH:
        if re.search(rx, tex):
            return fid
    return "altele"


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    res = Path(argv[argv.index("--out") + 1]) if "--out" in argv else resources_dir() / "rrp_mapeditor"
    for path in (ROOT / "tools", ROOT):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    from _sollumz_setup import setup_sollumz
    setup_sollumz(save_prefs=False)
    from dayzgen import gta_export as GX
    from dayzgen.dds_writer import write_dds
    from szio.gta5 import AssetTextureDictionary, EmbeddedTexture, save_asset
    from szio.types import DataSource

    tmp = ROOT / "output" / "paleta_tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    thumbs = res / "nui" / "paleta"
    thumbs.mkdir(parents=True, exist_ok=True)
    stream = res / "stream"
    stream.mkdir(parents=True, exist_ok=True)
    for old in list(thumbs.glob("*.png")) + list(stream.glob(f"{TXD}_*.ytd")):     # miniaturile vechi, .ytd-urile in plus
        old.unlink()
    scales = known_scales()

    # alese de mana, apoi tot restul bibliotecii, pe familii
    names = {fid: list(picked) for fid, _n, _s, picked in FAMILIES}
    taken = {t for picked in names.values() for t in picked}
    for path in sorted(LIB.glob("*.dds")):
        tex = path.stem.lower()
        if tex not in taken and surface_texture(path):
            names[family_of(tex)].append(tex)
            taken.add(tex)

    textures, families, missing, count = [], [], [], 0
    for fid, fname, fscale, _picked in FAMILIES:
        rows = []
        for tex in names[fid]:
            src = LIB / f"{tex}.dds"
            if not src.is_file():
                missing.append(tex)
                continue
            try:
                img = bpy.data.images.load(str(src), check_existing=False)
                img.scale(SIZE, SIZE)
                px = np.empty(SIZE * SIZE * 4, np.float32)
                img.pixels.foreach_get(px)
            except Exception as error:      # format pe care Blender nu-l citeste (BC7): sare
                print(f"PALETA sar {tex}: {error}")
                missing.append(tex)
                continue
            rgb = px.reshape(SIZE, SIZE, 4)[::-1, :, :3]       # Blender tine randurile de jos in sus
            dds = tmp / f"{tex}.dds"
            write_dds(str(dds), np.ascontiguousarray(rgb), "DXT1")
            txd = TXD if count < PER_TXD else f"{TXD}_{count // PER_TXD + 1}"
            textures.append((txd, EmbeddedTexture(tex, SIZE, SIZE, DataSource.create(str(dds), tex + ".dds"))))
            count += 1
            img.scale(THUMB, THUMB)
            img.filepath_raw = str(thumbs / f"{tex}.jpg")
            img.file_format = "JPEG"
            try:
                img.save(quality=80)
            except TypeError:
                img.save()
            bpy.data.images.remove(img)
            rows.append({"tex": tex, "scala": scales.get(tex, fscale), "normal": (LIB / f"{tex}_n.dds").is_file(),
                         "txd": txd})
            if count % 50 == 0:
                print(f"PALETA {count} texturi...", flush=True)
        if rows:
            families.append({"id": fid, "nume": fname, "texturi": rows})
    by_txd = {}
    for txd, tex in textures:
        by_txd.setdefault(txd, {})[tex.name] = tex
    for txd, group in by_txd.items():
        save_asset(AssetTextureDictionary(textures=group), GX._targets(False), stream, txd)
    (res / "paleta.json").write_text(json.dumps({"txd": TXD, "familii": families}, indent=1), encoding="utf-8")
    print(f"PALETA {count} texturi in {len(by_txd)} fisiere .ytd ({', '.join(by_txd)}), "
          f"{sum(len(f['texturi']) for f in families)} in paleta.json; familii: "
          + ", ".join(f"{f['id']} {len(f['texturi'])}" for f in families)
          + (f"; lipsesc {len(missing)}: {', '.join(missing[:8])}" if missing else ""))


main()
