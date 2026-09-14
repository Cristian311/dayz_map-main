# -*- coding: utf-8 -*-
"""
Generator de cladiri pentru Blender (tab-ul Harta, sectiunea "5. Genereaza cladire").

Alegi tipul (vila, casa, bloc de caramida, magazin, hala), dimensiunile, etajele, acoperisul, interiorul si
seed-ul; apare o cladire noua la cursorul 3D, gata de export ca model propriu (cu coliziune). Stilul e luat
din cladirile GTA din biblioteca: ferestre adancite in perete cu glaf si buiandrug, soclu, cornise, pietre de
colt la vile, acoperis cu streasina si bordura, blocuri de caramida cu scari de incendiu, magazin la parter,
copertine si rezervor de apa pe acoperis (Liberty City), hale cu rulouri.

Texturi: "GTA" ia materialele originale din biblioteca (tigla, tencuiala, caramida, beton, tabla, geamuri,
usi, rulouri); "simple" foloseste texturile generatorului. Fiecare material are un nume clar (perete,
acoperis, geam...), deci il poti schimba oricand in Material Properties.

Interior "simplu": pereti cu grosime, podele si tavane pe fiecare etaj, scara, pereti despartitori cu goluri
de usa, usa de la intrare deschisa; totul intr-un obiect separat (copilul cladirii), pe care il poti ascunde.
"""
import json
import math
import random
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parent.parent
LIB = ROOT / "output" / "gta_asset_library"
MAT_INDEX = LIB / "_materiale_cladiri.json"
TEX_DIR = ROOT / "output" / "harta_texturi"

# Materialele GTA potrivite pentru fiecare rol: (nume in biblioteca, metri per repetare; 0 = o data pe fata)
GTA_MATS = {
    # fara vb_09_rsd_hh_extstuccol: in joc isi foloseste culoarea si ca luciu, pete albe sub felinare
    # peretii: variantele adaugate si metrii lor per repetare vin din analiza_cladiri_gta.py (cat de mare e textura pe
    # cladirile GTA); fara cele cu nuanta (_tnt: au nevoie de paleta lor) si fara im_wall_brick_32 (piatra gri inchis
    # cu dungi, casele ieseau posomorate)
    "perete_vila": [("rb_bh1_wall_concrete_painted_orange", 3.0), ("im_wall_plaster32", 3.0),
                    ("sc01_rnad_wall_0003", 3.0), ("im_wall_plaster39", 3.0), ("sc01_rnad_wall_0002", 3.0),
                    ("ag_im_wallwhite_tiled", 3.0), ("cm_wall02", 2.0), ("im_wall01", 3.0)],
    "perete_caramida": [("al_brick_001", 1.6), ("ss1_01_rsn_rls_brick_0001", 1.6), ("cmk_wall_brick_x1", 3.0),
                        ("rsn_mh_whitebricktile01", 1.9), ("im_wall_brick_34", 2.0), ("rsn_am_im_wall_brick_36", 2.9)],
    "perete_beton": [("im_wall_concrete32", 3.0), ("rsn_mh_wall_concrete_0001", 4.4),
                     ("rsn_am_wall_concrete_0005_d", 1.7), ("hw_rncm_concbase_001", 3.0), ("hw_23_rsn_sjm_conc5", 3.0),
                     ("kt1_13_lm_concrete_01_d", 4.5), ("dt1_21_rnbj_concrete_02", 2.2)],
    "perete_lemn": [("im_wood_panels_08", 2.0), ("bh1_16_wood_planks_01", 2.0)],
    "soclu": [("dc_pavement_plainsmall01", 2.0), ("im_wall_concrete32", 3.0)],
    "ornament": [("ck_balwin_concrete_trim", 1.5), ("ss1_01_rsn_rls_ledge_0001", 1.5)],
    "acoperis_tigla": [("rsn_am_dc_roof_tile_01", 2.5), ("os_ml_bhroof_0002", 2.5), ("_ml_bhroof02", 2.5)],
    "acoperis_ardezie": [("kt1_10_roofslate_001", 2.0), ("nxg_kt1_10_slateroof_d", 2.0)],
    "acoperis_plat": [("im_roof04", 4.0), ("kt1_12_feltroof_01a", 4.0)],
    "tabla": [("ap1_01_corrugone", 3.0), ("rsn_dc_metal_0001", 2.0)],
    "metal": [("rsn_dc_metal_0001", 2.0)],
    # "geam" nu are variante fixe aici: fiecare cladire isi alege geamul GTA potrivit peretelui (gta_window, din
    # output/analiza_cladiri_gta.json), cu bucata lui de atlas (Mesh.cells); fara analiza ramane sticla noastra
    # fara im_interiorfake_02: e o poza de camera bej facuta pentru shader-ul de interior fals; pusa plat pe geam
    # arata in joc ca peretele. Geamurile de noapte folosesc sticla noastra luminata (emissivenight)
    "geam_noapte": [],
    "sticla": [("mc_window_0006", 0.0)],
    "usa": [("ss1_01_rsn_rls_frontdoor_0001", 0.0)],
    "usa_metal": [("os_ml_iddoor_0009", 0.0)],
    "rulou": [("kt1_15_metalshutter_01_d", 0.0)],
    "copertina": [("dt1_16_rsd_dr_aawning_01", 0.0), ("rsn_tf_metalawning", 0.0)],
    # firmele de deasupra vitrinelor si vitrinele cu magazinul pictat: bucati taiate din atlasele jocului de
    # tools/crop_firme.py (firma_*.dds, vitrina_*.dds); "vitrina_inchisa" = rulou tras, afise
    "firma": [("firma_gentstyle", 0.0), ("firma_sneaker", 0.0), ("firma_liquor", 0.0), ("firma_autos", 0.0),
              ("firma_forlease", 0.0), ("firma_fashion", 0.0)],
    "vitrina": [("vitrina_vb17_0", 0.0), ("vitrina_vb17_1", 0.0), ("vitrina_vb17_3", 0.0), ("vitrina_vb17w_0", 0.0),
                ("vitrina_vb17w_1", 0.0), ("vitrina_hw1_a", 0.0), ("vitrina_hw1_c", 0.0), ("vitrina_hw1_d", 0.0),
                ("vitrina_dt05", 0.0)],
    "vitrina_inchisa": [("vitrina_inchis_vb17", 0.0), ("vitrina_inchis_bh33", 0.0)],
    "podea": [("im_floortiles04", 2.0), ("os_ml_bhpfloor_0001", 2.0)],
    "interior": [("im_wall_plaster32", 3.0)],
    "tavan": [("im_roof_underside003", 3.0)],
    # strazi (gen_strada.py); marcajele GTA sunt atlase, deci raman culori plate
    # im_road_* au linii desenate in textura, im_kerbs* dungi rosii: se folosesc asfalt de parcare si beton
    "asfalt": [("dc_parking_tarmac_01", 6.0), ("dc_parking_tarmac_03", 6.0)],
    "trotuar": [("dc_sidewalk004", 3.0), ("im_sidewalk003", 3.0), ("im_sidewalk010", 3.0)],
    "bordura": [("im_wall_concrete32", 2.0)],
    # iarba GTA (parcuri, gazon, teren): textura noastra generata iesea inchisa, noaptea parea beton
    "iarba": [("im_grass02", 4.0), ("im_grass03", 4.0), ("am_grass_green", 4.0)],
    # uzura asfaltului (gen_oras.road_wear): materialele decal ale jocului, cu shader-ul lor (decal / normal_spec_decal);
    # peticele si capacele n-au transparenta in textura: marginea lor se estompeaza din alfa varfurilor, ca in joc
    "uzura_fisuri": [("cracks_01_dmcracks_01_tm", 0.0)],
    "uzura_pete": [("ap1_01decals_roadspots_01_dmap1_decals_roadspots_01_tm", 0.0)],
    "uzura_ulei": [("et_oilstainet_oilstain_a", 0.0)],
    "uzura_margine": [("im_road_damage_001im_road_damage_001_a", 0.0)],
    "uzura_petic1": [("im_road_damage_002", 0.0)],
    "uzura_petic2": [("im_road_damage_03", 0.0)],
    "uzura_petic3": [("dc_road_damage_dirt_002", 0.0)],
    "uzura_canal": [("im_drains02", 0.0)],        # atlas: capac rotund stanga sus, gratar patrat dreapta sus
    # pete pe iarba (gen_oras.grass_spots): tot decaluri ale jocului (decal / normal_decal), pamant, frunze, urme
    # natura de la marginea orasului (gen_oras, suprafetele plaja / camp / padure): texturi de teren ale jocului,
    # aduse ca material simplu (Materials._plain) fiindca nu exista ca material separat in biblioteca
    "nisip": [("cs_rsn_sl_bchsand_02", 6.0), ("cs_rsn_sl_bchsand_03", 6.0), ("rsn_os_beachsoftprints", 6.0)],
    "pata_pamant1": [("rsn_am_dirttreesurround_2rsn_am_dirttreesurround_2_a", 0.0)],
    "pata_pamant2": [("im_ground_dirt002", 0.0)],
    "pata_pamant3": [("og_cs_dirtscrub_d4", 0.0)],
    "pata_frunze1": [("rsn_am_ground_dirt_leaflitter", 0.0)],
    "pata_frunze2": [("rsn_am_ground_dirt_leaflitter_2", 0.0)],
    "pata_urma": [("ap1_01decal_bdyshp_dirt_02sm_dmap1_01decal_bdyshp_dirt_02_sm", 0.0)],
    # murdarie pe cladiri (gen_oras.building_grime): dare de apa, decal.sps. Fara "murdarie_baza": mh_grime_bridges01
    # e beton bej, pe perete iesea un soclu vopsit, nu murdarie (randare de test); alta textura potrivita n-am gasit
    # (dunga de la baza se pune doar daca rolul are material)
    "murdarie_dare1": [("mh_longdrips01mh_longdrips01a", 0.0)],
    "murdarie_dare2": [("rsn_dc_drips_0001rsn_dc_drips_0001_a", 0.0)],
    "murdarie_dare3": [("rsn_id1_21_mh_drips2rsn_id1_21_mh_drips2a", 0.0)],
    "murdarie_dare4": [("mw_leaking_conct_01mw_leaking_conct_01_a", 0.0)],
}
# varianta "simple": textura generata (dayzgen/textures.py) si metri per repetare
SIMPLE_MATS = {
    "perete_vila": ("plaster", 3.0), "perete_caramida": ("brick", 2.0), "perete_beton": ("plaster", 3.0),
    "perete_lemn": ("wood", 2.0), "soclu": ("rock", 2.0), "ornament": ("plaster", 1.5),
    "acoperis_tigla": ("rooftile", 2.0), "acoperis_ardezie": ("rooftile", 2.0), "acoperis_plat": ("rock", 4.0),
    "tabla": ("metal", 2.0), "metal": ("metal", 2.0), "geam": ("glass", 0.0), "geam_noapte": ("glass", 0.0),
    "sticla": ("glass", 0.0), "usa": ("door", 0.0), "usa_metal": ("door", 0.0), "rulou": ("metal", 0.0),
    "copertina": ("wood", 0.0), "firma": ("plaster", 0.0), "vitrina": ("glass", 0.0), "vitrina_inchisa": ("metal", 0.0),
    "podea": ("wood", 2.0), "interior": ("plaster", 3.0), "tavan": ("plaster", 3.0),
    "asfalt": ("asphalt", 4.0), "trotuar": ("plaster", 2.0), "bordura": ("plaster", 1.0),
    "marcaj_alb": ("alb", 0.0), "marcaj_galben": ("galben", 0.0), "iarba": ("grass", 4.0),
    # bordura vopsita (marcajele strazii din editor): rosu = oprirea interzisa, galben = doar incarcare
    "bordura_rosie": ("rosu", 1.0), "bordura_galbena": ("galben", 1.0),
}
# numele materialelor in scena (ce vezi in Material Properties)
SLOT_NAMES = {
    "perete_vila": "perete", "perete_caramida": "perete", "perete_beton": "perete", "perete_lemn": "perete",
    "vitrina_inchisa": "vitrina",
    "acoperis_tigla": "acoperis", "acoperis_ardezie": "acoperis", "acoperis_plat": "acoperis", "tabla": "tabla",
    "usa_metal": "usa",
}


def _glass_rgb(size=128):
    """Sticla albastruie, mult mai deschisa sus (cerul reflectat), cu o dunga de reflexie pe diagonala; destul de
    deschisa cat sa nu se confunde cu peretele noaptea, in joc."""
    yy = np.linspace(1.0, 0.0, size)[:, None]
    xx = np.linspace(0.0, 1.0, size)[None, :]
    base = np.array([0.14, 0.2, 0.27]) + np.array([0.36, 0.42, 0.48]) * (yy ** 1.2)[..., None]
    band = np.clip(1.0 - np.abs((xx + yy * 0.6) - 0.75) * 6.0, 0.0, 1.0)[..., None] * 0.2
    return np.clip(base + band, 0.0, 1.0)


def _asphalt_rgb(size=256):
    grain = np.random.RandomState(7).rand(size, size)
    return np.clip(0.17 + grain[..., None] * np.array([0.07, 0.07, 0.075]), 0.0, 1.0)


# texturi generate aici, nu in dayzgen/textures.py
SPECIAL_TEX = {"glass": _glass_rgb, "asphalt": _asphalt_rgb,
               "alb": lambda: np.ones((16, 16, 3)) * np.array([0.88, 0.88, 0.84]),
               "galben": lambda: np.ones((16, 16, 3)) * np.array([0.9, 0.68, 0.12]),
               "rosu": lambda: np.ones((16, 16, 3)) * np.array([0.72, 0.16, 0.13])}


# ------------------------------------------------------------------------------------------ materiale

def _index_library(names: set) -> dict:
    """{nume material: fisier .blend} pentru materialele cerute; cautarea se face o data si se tine minte."""
    cache = {}
    if MAT_INDEX.is_file():
        try:
            cache = json.loads(MAT_INDEX.read_text(encoding="utf-8"))
        except ValueError:
            cache = {}
    files = sorted(str(p) for p in LIB.glob("_assets.*.blend"))
    if cache.get("files") != len(files) or not names <= set(cache.get("seen", [])):
        found = {}
        for path in files:
            with bpy.data.libraries.load(path) as (src, _dst):
                for mat in src.materials:
                    base = mat.split(".")[0] if mat.rsplit(".", 1)[-1].isdigit() else mat
                    if base in names and base not in found:
                        found[base] = (path, mat)
        cache = {"files": len(files), "seen": sorted(names), "mats": found}
        MAT_INDEX.parent.mkdir(parents=True, exist_ok=True)
        MAT_INDEX.write_text(json.dumps(cache, indent=1), encoding="utf-8")
    return cache.get("mats", {})


def _images_on_disk(mat) -> bool:
    """Toate texturile materialului se gasesc (una lipsa iese roz in Blender si gri in joc)."""
    for node in (mat.node_tree.nodes if mat.node_tree else []):
        img = node.image if node.type == "TEX_IMAGE" else None
        if img is not None and img.packed_file is None and not Path(bpy.path.abspath(img.filepath)).is_file():
            print(f"[cladiri] {mat.name}: lipseste textura {img.filepath}")
            return False
    return True


_GTA_MATS = {}      # harta_gta -> materialul adus deja in scena (cautat prin toate materialele, la fiecare cladire, lua ~40 s)


def _gta_mat(name):
    """Materialul jocului adus deja in scena (proprietatea harta_gta), sau None."""
    mat = _GTA_MATS.get(name)
    if mat is not None:
        try:
            if mat.get("harta_gta") == name and mat.library is None:
                return mat
        except ReferenceError:      # sters din scena intre timp
            pass
    _GTA_MATS.clear()
    for m in bpy.data.materials:
        g = m.get("harta_gta")
        if g and m.library is None:
            _GTA_MATS.setdefault(g, m)
    return _GTA_MATS.get(name)


class Materials:
    """Rolurile (perete, acoperis, geam...) -> materiale in scena, alese dupa seed dintre variantele GTA."""

    # rolurile de sol care isi aleg alta varianta in fiecare cvartal (gen_oras pune variant = id-ul cvartalului);
    # strazile raman cu o singura varianta pe oras, altfel asfaltul ar parea petice
    VARY_ROLES = ("iarba", "trotuar", "asfalt")

    def __init__(self, mode: str, rng: random.Random):
        self.mode = mode
        self.rng = rng
        self.chosen = {}
        self.variant = None
        # alegerea pe rol nu depinde de ordinea in care se cer rolurile: generarea incrementala (gen_oras) reface doar
        # unele strazi / cvartale, iar peretii si trotuarele lor trebuie sa iasa la fel ca ale celor ramase
        self.key = ",".join(str(v) for v in rng.getstate()[1][:6])
        self.index = _index_library({n for opts in GTA_MATS.values() for n, _ in opts}) if mode == "gta" else {}
        if mode == "gta":
            # materialele gasite de analiza sub alt nume decat textura: din .blend-ul in care apar
            walls = gta_analysis().get("walls") or {}
            for opts in GTA_MATS.values():
                for n, _s in opts:
                    src = (walls.get(n) or {}).get("src")
                    if n not in self.index and src and (LIB / src[0]).is_file():
                        self.index[n] = (str(LIB / src[0]), src[1])
        self._ok = {}
        self.blend = False      # iarba amestecata ca terenul GTA (gen_oras il porneste dupa plan.iarba_amestec)

    @staticmethod
    def base(role: str) -> str:
        """"firma2" -> "firma": aceleasi variante, alta alegere (firmele magazinelor de pe aceeasi cladire difera)."""
        return role.rstrip("0123456789")

    def has(self, role: str) -> bool:
        """Rolul are material GTA adus, cu toate texturile pe disc. Uzura asfaltului n-are varianta simpla: fara
        materialul jocului nu se pune deloc."""
        role = self.base(role)
        if role not in self._ok:
            names = [n for n, _ in GTA_MATS.get(role, []) if self._known(n)] if self.mode == "gta" else []
            mats = [self._append(n) for n in names]
            self._ok[role] = bool(mats) and all(m is not None and _images_on_disk(m) for m in mats)
        return self._ok[role]

    def get(self, role: str):
        """(material, metri per repetare) pentru un rol."""
        var = self.variant if role in self.VARY_ROLES else None
        key = role if var is None else (role, var)
        if key in self.chosen:
            return self.chosen[key]
        mat, scale = None, 0.0
        base = self.base(role)
        if self.mode == "gta":
            options = [(n, s) for n, s in GTA_MATS.get(base, []) if self._known(n)]
            if options:
                rng = random.Random(f"{self.key}:{role}") if var is None else random.Random(f"{role}:{var}")
                name, scale = rng.choice(options)
                mat = self._terrain(name) if role == "iarba" and self.blend else None
                if mat is None:
                    mat = self._append(name)
        if mat is None:
            key_s, scale = SIMPLE_MATS[base]
            mat = self._simple(base, key_s)
        self.chosen[key] = (mat, scale)
        return self.chosen[key]

    def _known(self, name):
        """Materialul jocului e in biblioteca, sau macar textura lui (se face material simplu din ea)."""
        return name in self.index or (LIB / f"{name}.dds").is_file()

    def _plain(self, name):
        """Material simplu din textura bibliotecii (normal.sps cu normala ei, altfel default.sps): texturile de teren
        ale jocului (nisip, iarba salbatica) nu exista ca material separat."""
        mat = _gta_mat(name)
        if mat is not None:
            return mat
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        from dayzgen.blender_build import SollumzAPI
        nrm = LIB / f"{name}_n.dds"
        mat = SollumzAPI().sm.create_shader("normal.sps" if nrm.is_file() else "default.sps")
        mat.name = f"gta_{name}"
        mat["harta_gta"] = name
        _GTA_MATS[name] = mat
        d = mat.node_tree.nodes.get("DiffuseSampler")
        if d is not None:
            d.image = bpy.data.images.load(str(LIB / f"{name}.dds"), check_existing=True)
        b = mat.node_tree.nodes.get("BumpSampler")
        if b is not None and nrm.is_file():
            b.image = bpy.data.images.load(str(nrm), check_existing=True)
        return mat

    def _append(self, name):
        # adus o data, refolosit de toate cladirile (in biblioteca numele au uneori sufix .001)
        if name not in self.index:
            return self._plain(name)
        mat = _gta_mat(name)
        if mat is not None:
            return mat
        path, inner = self.index[name]
        try:
            with bpy.data.libraries.load(path, link=False) as (_src, dst):
                dst.materials = [inner]
        except Exception as error:
            print(f"[cladiri] materialul {name} nu s-a putut aduce: {error}")
            return None
        mat = dst.materials[0]
        mat["harta_gta"] = name
        _GTA_MATS[name] = mat
        return mat

    # straturile 1-3 ale ierbii amestecate: alta iarba, pamant, frunze (stratul 0 = iarba aleasa pentru cvartal)
    # (im_ground_dirt002 e pietris gri deschis: in iarba ieseau pete albe; dc_rsn_cs2_02_soil_02 e pamant brun)
    BLEND_LAYERS = ("cs_rsn_sl_wetlandsgrass3", "dc_rsn_cs2_02_soil_02", "rsn_am_ground_dirt_leaflitter")

    def _terrain(self, grass):
        """Iarba ca terenul GTA (terrain_cb_w_4lyr): 4 texturi amestecate dupa Color 2 a varfurilor (albastru:
        stratul 0 / 1 si 2 / 3, verde: perechea 0-1 / 2-3), pictata de gen_oras.paint_blend. None = lipsesc texturi."""
        name = f"iarba_amestec_{grass}"
        mat = bpy.data.materials.get(name)
        if mat is not None:
            return mat
        layers = [grass, *self.BLEND_LAYERS]
        if not all((LIB / f"{t}.dds").is_file() for t in layers):
            return None
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        from dayzgen.blender_build import SollumzAPI
        mat = SollumzAPI().sm.create_shader("terrain_cb_w_4lyr.sps")
        mat.name = name
        for i, t in enumerate(layers):
            d = mat.node_tree.nodes.get(f"TextureSampler_layer{i}")
            if d is not None:
                d.image = bpy.data.images.load(str(LIB / f"{t}.dds"), check_existing=True)
            nrm = LIB / f"{t}_n.dds"
            if not nrm.is_file():
                nrm = LIB / ("im_grass02_n.dds" if i < 2 else "im_ground_dirt002_n.dds")
            b = mat.node_tree.nodes.get(f"BumpSampler_layer{i}")
            if b is not None and nrm.is_file():
                b.image = bpy.data.images.load(str(nrm), check_existing=True)
        return mat

    def _simple(self, role, key):
        name = f"cladire_{SLOT_NAMES.get(role, role)}_{key}"
        # doar geamurile "de noapte" au shader-ul GTA de ferestre luminate; celelalte raman stinse (toate aprinse
        # nu e realist). Care geam e aprins se alege fereastra cu fereastra, in build / build_tower
        lit = role == "geam_noapte"
        mat = bpy.data.materials.get(name)
        if mat is not None:
            # materialul ramas in .blend de la generarea trecuta (incremental): daca are alt shader decat trebuie
            # acum (geamurile stinse erau si ele luminate), se reface, altfel schimbarea nu ajungea niciodata in joc
            was_lit = bool(mat.node_tree and mat.node_tree.nodes.get("emissiveMultiplier"))
            if was_lit == lit:
                return mat
            mat.name = name + ".vechi"
            bpy.data.materials.remove(mat)
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        from dayzgen import textures
        from dayzgen.dds_writer import write_dds
        from dayzgen.blender_build import SollumzAPI
        path = TEX_DIR / f"cladire_{key}.dds"
        if not path.is_file():
            TEX_DIR.mkdir(parents=True, exist_ok=True)
            if key in SPECIAL_TEX:
                rgb = SPECIAL_TEX[key]()
            else:
                rgb, _normal = {**textures.TERRAIN_TEXTURES, **textures.BUILDING_TEXTURES}[key](256, 11)
            write_dds(str(path), rgb, "DXT1")
        mat = SollumzAPI().sm.create_shader("emissivenight.sps" if lit else "default.sps")
        mat.name = name
        node = mat.node_tree.nodes.get("DiffuseSampler")
        if node is not None:
            node.image = bpy.data.images.load(str(path), check_existing=True)
        em = mat.node_tree.nodes.get("emissiveMultiplier")
        if lit and em is not None:
            em.set_float(1.6)
        return mat


# ------------------------------------------------------------------------------------------ geamuri GTA

ANALYSIS = ROOT / "output" / "analiza_cladiri_gta.json"      # tools/analiza_cladiri_gta.py
# tipul generatorului -> cladirile GTA cu care seamana: (categorii, stiluri) din catalog
GTA_LIKE = {"vila": ({"house", "lowrise", "midrise"}, {"vinewood"}),
            "casa": ({"house", "lowrise"}, {"suburb", "country", "beach", "vinewood"}),
            "bloc": ({"midrise", "lowrise"}, {"downtown", "beach", "vinewood", "any"}),
            "magazin": ({"shop", "lowrise", "midrise"}, {"downtown", "beach", "suburb", "vinewood", "any"}),
            "turn": ({"tower", "midrise"}, {"downtown"})}
# shadere cu care textura nu se poate pune opac pe un geam: transparente, decaluri, deja aprinse
BAD_WIN_SHADER = ("glass", "decal", "alpha", "cutout", "emissive", "cloth", "mirror")
# atlase cu firme si vitrine: bucata aleasa iesea uneori o firma sau o usa
BAD_WIN_NAME = ("sign", "mart", "logo", "shop", "garage", "door")
_ANALYSIS = None


def gta_analysis() -> dict:
    global _ANALYSIS
    if _ANALYSIS is None:
        try:
            _ANALYSIS = json.loads(ANALYSIS.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _ANALYSIS = {}
    return _ANALYSIS


def _tex_name(mat) -> str:
    return (mat.get("harta_gta") or mat.name) if mat is not None else ""


def gta_window(rng, tip, wall_tex):
    """Geamul GTA al unei cladiri: (textura, (u0, v0, su, sv, vz, uu), latime, inaltime) sau None. Candidatii: texturi
    folosite pe cladirile GTA ca o fereastra intreaga sau ca bucata de atlas, de marimea unei ferestre. Scorul: de cate
    ori apare textura langa peretele ales (x4), plus cladirile GTA de acelasi fel (categorie, stil) pe care apare."""
    cats, styles = GTA_LIKE.get(tip, (set(), set()))
    options, weights = [], []
    for tex, g in (gta_analysis().get("windows") or {}).items():
        if g.get("kind") not in ("fereastra", "atlas") or any(s in (g.get("shader") or "") for s in BAD_WIN_SHADER):
            continue
        src = g.get("src")      # [fisierul .blend al bibliotecii, materialul]: texturile sunt impachetate acolo
        if tex.endswith("_a") or any(s in tex.lower() for s in BAD_WIN_NAME):
            continue
        if not ((LIB / f"{tex}.dds").is_file() or (src and (LIB / src[0]).is_file())):
            continue
        # z = cat de sus sta bucata pe cladirile GTA: cele de la sol (sub 0.6 m) sunt usi si vitrine
        cells = [c for c in g.get("cells") or () if c["n"] >= 3 and 0.6 <= c["w"] <= 2.6 and 0.8 <= c["h"] <= 3.0
                 and c["h"] >= c["w"] * 0.7 and c.get("z", 1.0) >= 0.6]
        if not cells:
            continue
        score = (4.0 * (g.get("walls") or {}).get(wall_tex, 0) + sum(v for k, v in (g.get("cat") or {}).items() if k in cats)
                 + sum(v for k, v in (g.get("style") or {}).items() if k in styles))
        if score > 0:
            options.append((tex, cells, src))
            weights.append(score)
    if not options:
        return None
    tex, cells, src = rng.choices(options, weights)[0]
    c = rng.choices(cells, [x["n"] for x in cells])[0]
    return tex, tuple(c["uv"]) + (c["vz"], c["uu"]), c["w"], c["h"], src


def use_gta_window(materials, m, win):
    """Rolurile geam / geam_noapte ale cladirii iau textura GTA aleasa (noaptea aceeasi textura, aprinsa), iar fetele
    lor doar bucata ei de atlas. m.win = (latime, inaltime) reale ale ferestrei."""
    tex, cell, src = win[0], win[1], win[4]
    if src and tex not in materials.index and (LIB / src[0]).is_file():
        materials.index[tex] = (str(LIB / src[0]), src[1])      # materialul jocului, adus din .blend-ul lui
    day = materials._append(tex)
    if day is None or not _images_on_disk(day):
        return
    node = day.node_tree.nodes.get("DiffuseSampler") if day.node_tree else None
    img = node.image if node is not None and node.type == "TEX_IMAGE" else None
    if img is None or not (img.packed_file or img.has_data or Path(bpy.path.abspath(img.filepath)).is_file()):
        return          # textura lipsa (in .blend-ul bibliotecii): ramane sticla noastra
    name = f"gta_{tex}_noapte"
    lit = bpy.data.materials.get(name)
    if lit is None:
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        from dayzgen.blender_build import SollumzAPI
        lit = SollumzAPI().sm.create_shader("emissivenight.sps")
        lit.name = name
        d = lit.node_tree.nodes.get("DiffuseSampler")
        if d is not None and img is not None:
            d.image = img
        em = lit.node_tree.nodes.get("emissiveMultiplier")
        if em is not None:
            em.set_float(1.6)
    materials.chosen["geam"] = (day, 0.0)
    materials.chosen["geam_noapte"] = (lit, 0.0)
    m.cells["geam"] = m.cells["geam_noapte"] = tuple(cell)
    m.win = (win[2], win[3])


# ------------------------------------------------------------------------------------------ geometrie

class Mesh:
    """Fete cu rol de material si UV-uri: proiectate pe cutie (metri) sau intinse pe fata (geamuri, usi)."""

    def __init__(self, materials: Materials):
        self.materials = materials
        self.verts, self.faces, self.roles, self.uvs = [], [], [], []
        self.alpha = {}         # fata -> alfa pe fiecare colt (decalurile isi estompeaza marginile); lipsa = 1
        # (sfert de tura, deplasare u, deplasare v) pe obiect: placile vecine nu mai au textura aliniata
        self.uv_turn = None
        # deplasarea adaugata la tot ce se construieste (etajul retras e un dreptunghi centrat, mutat spre spate)
        self.shift = Vector((0.0, 0.0, 0.0))
        # rol -> (u0, v0, su, sv, vz, uu): fata intinsa ia doar bucata asta din textura (geamurile GTA sunt atlase:
        # mai multe ferestre intr-o textura); vz -1 = textura e cu susul in jos, 90 = intoarsa; uu -1 = in oglinda
        self.cells = {}
        self.win = None         # (latime, inaltime) ale geamului GTA ales (use_gta_window)
        self.shop_i = 0         # al catelea magazin de la parter (vitrina si firma lui isi iau alta varianta)

    def face(self, pts, role, uv=None, alpha=None):
        """pts: colturi (Vector) in sens trigonometric vazut dinspre fata vizibila; alpha: cate unul pe colt."""
        if alpha is not None:
            self.alpha[len(self.faces)] = list(alpha)
        pts = [Vector(p) + self.shift for p in pts]
        if uv is None and role in self.cells and len(pts) == 4:
            uv = self._cell_uv(self.cells[role])
        if uv is None:
            _mat, scale = self.materials.get(role)
            uv = self._box_uv(pts, scale) if scale > 0 else self._stretch_uv(pts)
        base = len(self.verts)
        self.verts += pts
        self.faces.append(tuple(range(base, base + len(pts))))
        self.roles.append(role)
        self.uvs.append(uv)

    @staticmethod
    def _normal(pts):
        n = (pts[1] - pts[0]).cross(pts[2] - pts[0])
        return n.normalized() if n.length > 1e-9 else Vector((0.0, 0.0, 1.0))

    def _box_uv(self, pts, scale):
        n = self._normal(pts)
        ax, ay, az = abs(n.x), abs(n.y), abs(n.z)
        flat = az >= ax and az >= ay
        out = []
        for p in pts:
            if flat:
                u, v = p.x, p.y if n.z > 0 else -p.y
            elif ax >= ay:
                u, v = (p.y if n.x > 0 else -p.y), p.z
            else:
                u, v = (-p.x if n.y > 0 else p.x), p.z
            u, v = u / scale, v / scale
            if self.uv_turn is not None:
                k, du, dv = self.uv_turn
                if flat:        # solul se roteste cu un sfert de tura; peretii doar se deplaseaza (caramida orizontala)
                    u, v = ((u, v), (-v, u), (-u, -v), (v, -u))[k]
                    v += dv
                u += du
            out.append((u, v))
        return out

    @staticmethod
    def _cell_uv(cell):
        """UV-urile colturilor (stanga jos, dreapta jos, dreapta sus, stanga sus) pentru bucata de atlas."""
        u0, v0, su, sv, vz, uu = cell
        a, b = (u0, u0 + su) if uu >= 0 else (u0 + su, u0)
        if vz == 90:        # textura culcata: u urca pe verticala
            return [(u0, v0 + sv), (u0, v0), (u0 + su, v0), (u0 + su, v0 + sv)]
        lo, hi = (v0, v0 + sv) if vz >= 0 else (v0 + sv, v0)
        return [(a, lo), (b, lo), (b, hi), (a, hi)]

    def _stretch_uv(self, pts):
        if len(pts) == 4:
            return [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
        return [(0.0, 0.0), (1.0, 0.0), (0.5, 1.0)][:len(pts)]

    def quad(self, a, b, c, d, role, uv=None):
        self.face([a, b, c, d], role, uv)

    def box(self, x0, y0, z0, x1, y1, z1, role, bottom=False):
        """Cutie aliniata la axe, cu fetele spre exterior."""
        p = [Vector((x, y, z)) for z in (z0, z1) for y in (y0, y1) for x in (x0, x1)]
        self.quad(p[4], p[5], p[7], p[6], role)            # sus
        self.quad(p[0], p[1], p[5], p[4], role)            # fata (-Y)
        self.quad(p[3], p[2], p[6], p[7], role)            # spate (+Y)
        self.quad(p[2], p[0], p[4], p[6], role)            # stanga (-X)
        self.quad(p[1], p[3], p[7], p[5], role)            # dreapta (+X)
        if bottom:
            self.quad(p[0], p[2], p[3], p[1], role)

    def to_object(self, name):
        me = bpy.data.meshes.new(name)
        me.from_pydata([tuple(v) for v in self.verts], [], self.faces)
        slots = list(dict.fromkeys(self.roles))
        for role in slots:
            me.materials.append(self.materials.get(role)[0])
        me.polygons.foreach_set("material_index", np.array([slots.index(r) for r in self.roles], dtype=np.int32))
        uv_layer = me.uv_layers.new(name="UVMap 0")
        flat = [c for uv in self.uvs for pt in uv for c in pt]
        uv_layer.data.foreach_set("uv", np.array(flat, dtype=np.float32))
        color = me.color_attributes.new(name="Color 1", type="BYTE_COLOR", domain="CORNER")
        rgba = np.ones((len(me.loops), 4), dtype=np.float32)
        if self.alpha:
            rgba[:, 3] = [x for i, f in enumerate(self.faces) for x in self.alpha.get(i, (1.0,) * len(f))]
        color.data.foreach_set("color_srgb", rgba.ravel())
        if any(self.materials.get(r)[0].name.startswith("iarba_amestec") for r in slots):
            # iarba amestecata: Color 2 = cat din fiecare strat; negru = doar stratul 0 (gen_oras.paint_blend picteaza)
            blend = me.color_attributes.new(name="Color 2", type="BYTE_COLOR", domain="CORNER")
            blend.data.foreach_set("color_srgb", np.tile(np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32), len(me.loops)))
        me.validate()
        me.update()
        obj = bpy.data.objects.new(name, me)
        # rolul fiecarui material si scala lui: editorul din joc le arata si le schimba (tools/tex_overrides.py)
        obj["harta_roluri"] = json.dumps({r: [self.materials.get(r)[0].name, self.materials.get(r)[1]] for r in slots})
        return obj


class Facade:
    """O latura a amprentei: de la a la b (sens trigonometric), cu normala spre exterior.
    Coordonate pe fatada: u de-a lungul ei (m de la a), z inaltimea, d adancimea spre interior (+) sau
    spre exterior (-)."""

    def __init__(self, a, b, name):
        self.a = Vector((a[0], a[1], 0.0))
        self.b = Vector((b[0], b[1], 0.0))
        self.length = (self.b - self.a).length
        self.t = (self.b - self.a) / self.length
        self.n = Vector((self.t.y, -self.t.x, 0.0))
        self.name = name

    def p(self, u, z, d=0.0):
        return self.a + self.t * u + Vector((0.0, 0.0, z)) - self.n * d

    def box(self, m, u0, u1, d0, d1, z0, z1, role):
        """Cutie pe fatada: u0..u1 de-a lungul, d0..d1 adancime (negativ = iese in afara), z0..z1. Cele de deasupra
        solului (balcoane, aparate de aer conditionat, cornise) au si fata de jos: de pe strada se vedea prin ele."""
        pts = [self.p(u, 0.0, d) for u in (u0, u1) for d in (d0, d1)]
        m.box(min(p.x for p in pts), min(p.y for p in pts), z0, max(p.x for p in pts), max(p.y for p in pts), z1, role,
              bottom=z0 > 0.05)


def rect_facades(hw, hd):
    """Cele 4 fatade ale dreptunghiului centrat: fata (-Y), dreapta (+X), spate (+Y), stanga (-X)."""
    return [Facade((-hw, -hd), (hw, -hd), "fata"), Facade((hw, -hd), (hw, hd), "dreapta"),
            Facade((hw, hd), (-hw, hd), "spate"), Facade((-hw, hd), (-hw, -hd), "stanga")]


def frame(m, f, u0, u1, v0, v1, d, kind):
    """Rama si montanti chiar in fata geamului (d = adancimea geamului in perete)."""
    b, d0, d1 = 0.06, d - 0.05, d
    f.box(m, u0, u1, d0, d1, v1 - b, v1, "ornament")
    f.box(m, u0, u0 + b, d0, d1, v0, v1, "ornament")
    f.box(m, u1 - b, u1, d0, d1, v0, v1, "ornament")
    if kind in ("fereastra", "vitrina", "balcon"):
        f.box(m, u0, u1, d0, d1, v0, v0 + b, "ornament")
    if kind in ("fereastra", "balcon"):
        if u1 - u0 > 0.9:
            c = (u0 + u1) / 2
            f.box(m, c - b / 2, c + b / 2, d0, d1, v0, v1, "ornament")
        if v1 - v0 > 1.4:
            z = v0 + (v1 - v0) * 0.68
            f.box(m, u0, u1, d0, d1, z - b / 2, z + b / 2, "ornament")
    elif kind == "vitrina":
        n = max(1, int((u1 - u0) / 1.3))
        for i in range(1, n):
            c = u0 + (u1 - u0) * i / n
            f.box(m, c - b / 2, c + b / 2, d0, d1, v0, v1, "ornament")


def wall_band(m, f, z0, z1, openings, role, thickness=0.0, inner_role="interior", glass="geam", depth=0.18,
              door="usa", frames=True):
    """Banda de perete z0..z1 pe fatada f, cu goluri adancite. openings: (u0, u1, v0, v1, fel), fel in
    "fereastra", "usa", "gol", "vitrina", "rulou". thickness > 0 = perete cu grosime si fata interioara.
    frames=False: fara rame si montanti (etajele de sus ale turnurilor: de jos nu se vad, iar fetele conteaza);
    frames="usi": doar la usi si vitrine (geamurile GTA au rama desenata in textura)."""
    full = thickness if thickness > 0 else depth
    u = 0.0
    for u0, u1, v0, v1, kind in sorted(openings):
        if u0 > u + 1e-4:
            m.quad(f.p(u, z0), f.p(u0, z0), f.p(u0, z1), f.p(u, z1), role)
        if v0 > z0 + 1e-4:
            m.quad(f.p(u0, z0), f.p(u1, z0), f.p(u1, v0), f.p(u0, v0), role)
        if v1 < z1 - 1e-4:
            m.quad(f.p(u0, v1), f.p(u1, v1), f.p(u1, z1), f.p(u0, z1), role)
        # glaful: laturile golului, pe adancimea peretelui
        side = role if thickness > 0 else "ornament"
        m.quad(f.p(u0, v0), f.p(u0, v0, full), f.p(u0, v1, full), f.p(u0, v1), side)
        m.quad(f.p(u1, v0), f.p(u1, v1), f.p(u1, v1, full), f.p(u1, v0, full), side)
        if v0 > z0 + 1e-4 or kind != "usa":
            m.quad(f.p(u0, v0), f.p(u1, v0), f.p(u1, v0, full), f.p(u0, v0, full), side)
        m.quad(f.p(u0, v1), f.p(u0, v1, full), f.p(u1, v1, full), f.p(u1, v1), side)
        # ce e in gol: geam, usa, rulou, vitrina (sau nimic la "gol", pe unde se intra)
        g = glass() if callable(glass) else glass      # functie = alege geamul fereastra cu fereastra
        # vitrina e lata: bucata de atlas a geamului GTA (m.cells) intinsa pe ea iesea un grilaj urias
        back = {"fereastra": g, "balcon": g, "vitrina": "sticla" if thickness > 0 or "geam" in m.cells else g, "usa": door,
                "rulou": "rulou", "vitrina_inchisa": "vitrina_inchisa"}.get(kind)
        painted = kind in ("vitrina", "vitrina_inchisa") and thickness <= 0 and m.materials.has(kind)
        if painted:
            # vitrina GTA cu magazinul pictat (sau inchisa cu rulou): alta varianta la fiecare magazin, fara rame
            back = ("", "2", "3")[m.shop_i % 3].join([kind, ""]) if kind == "vitrina" else kind
            m.shop_i += 1
        if back is not None and not (kind == "usa" and thickness > 0):
            d = full * 0.5 if thickness > 0 else depth
            m.quad(f.p(u0, v0, d), f.p(u1, v0, d), f.p(u1, v1, d), f.p(u0, v1, d), back)
            if thickness > 0:
                m.quad(f.p(u1, v0, d), f.p(u0, v0, d), f.p(u0, v1, d), f.p(u1, v1, d), back)
            if frames and (frames != "usi" or kind != "fereastra") and not painted:
                frame(m, f, u0, u1, v0, v1, d, kind)
        u = u1
    if u < f.length - 1e-4:
        m.quad(f.p(u, z0), f.p(f.length, z0), f.p(f.length, z1), f.p(u, z1), role)
    if thickness > 0:
        # fata dinspre interior, cu aceleasi goluri (normala spre interior)
        u = 0.0
        t = thickness
        for u0, u1, v0, v1, _kind in sorted(openings):
            if u0 > u + 1e-4:
                m.quad(f.p(u0, z0, t), f.p(u, z0, t), f.p(u, z1, t), f.p(u0, z1, t), inner_role)
            if v0 > z0 + 1e-4:
                m.quad(f.p(u1, z0, t), f.p(u0, z0, t), f.p(u0, v0, t), f.p(u1, v0, t), inner_role)
            if v1 < z1 - 1e-4:
                m.quad(f.p(u1, v1, t), f.p(u0, v1, t), f.p(u0, z1, t), f.p(u1, z1, t), inner_role)
            u = u1
        if u < f.length - 1e-4:
            m.quad(f.p(f.length, z0, t), f.p(u, z0, t), f.p(u, z1, t), f.p(f.length, z1, t), inner_role)


def window_trim(m, f, u0, u1, v0, v1, style):
    """Glaf exterior sub fereastra si buiandrug (sau cheie de bolta la vile) deasupra."""
    f.box(m, u0 - 0.08, u1 + 0.08, -0.07, 0.02, v0 - 0.09, v0, "ornament")
    if style == "caramida":
        f.box(m, u0 - 0.12, u1 + 0.12, -0.05, 0.02, v1, v1 + 0.28, "ornament")
    elif style == "vila":
        f.box(m, u0 - 0.06, u1 + 0.06, -0.04, 0.02, v1, v1 + 0.12, "ornament")


def ring(m, hw, hd, z0, z1, out, role, gaps=None, lipit=()):
    """Brau in jurul dreptunghiului (soclu, cornisa), iesit `out` m in afara; gaps: {fatada: [(u0, u1)]}.
    lipit: fatadele lipite de o cladire vecina (fara brau, iar cel de pe fatadele alaturate se opreste la colt)."""
    fs = rect_facades(hw, hd)
    for i, f in enumerate(fs):
        if f.name in lipit:
            continue
        end = f.length if fs[(i + 1) % 4].name in lipit else f.length + out
        cuts = sorted((gaps or {}).get(f.name, []))
        u = 0.0 if fs[i - 1].name in lipit else -out
        for g0, g1 in cuts + [(end, end)]:
            if g0 > u + 1e-3:
                f.box(m, u, min(g0, end), -out, 0.05, z0, z1, role)
            u = g1


def quoins(m, hw, hd, z0, z1, role="ornament"):
    """Pietre de colt alternante (vilele din Vinewood)."""
    for f in rect_facades(hw, hd):
        z, k = z0, 0
        while z + 0.3 <= z1:
            w = 0.55 if k % 2 == 0 else 0.35
            f.box(m, -0.03, w, -0.04, 0.02, z, z + 0.32, role)
            f.box(m, f.length - w, f.length + 0.03, -0.04, 0.02, z, z + 0.32, role)
            z += 0.36
            k += 1


def _rot(p, ang):
    c, s = math.cos(ang), math.sin(ang)
    return Vector((p[0] * c - p[1] * s, p[0] * s + p[1] * c, p[2]))


def roof_pitched(m, hw, hd, z, rise, over, kind, role, wall_role):
    """Acoperis in patru ape ("patru") sau in doua ape ("doua"), cu streasina, bordura si tavan dedesubt.
    Coama merge pe latura lunga."""
    ang = 0.0
    if hd > hw:
        hw, hd, ang = hd, hw, math.pi / 2
    R = lambda *p: _rot(p, ang)
    o = ox = over
    gable = kind == "doua"
    e0, e1, e2, e3 = R(-hw - ox, -hd - o, z), R(hw + ox, -hd - o, z), R(hw + ox, hd + o, z), R(-hw - ox, hd + o, z)
    top = z + rise
    if gable:
        r0, r1 = R(-hw - ox, 0.0, top), R(hw + ox, 0.0, top)
    else:
        rx = max(hw - hd, 0.0)
        r0, r1 = R(-rx, 0.0, top), R(rx, 0.0, top)
    # UV-uri pe panta: randurile de tigla paralele cu streasina, pe toate fetele
    scale = m.materials.get(role)[1] or 2.5

    def slope(*pts):
        u_axis = (pts[1] - pts[0]).normalized()
        v_axis = Mesh._normal(list(pts)).cross(u_axis)
        m.face(list(pts), role, [((p - pts[0]).dot(u_axis) / scale, (p - pts[0]).dot(v_axis) / scale) for p in pts])

    slope(e0, e1, r1, r0)
    slope(e2, e3, r0, r1)
    if gable:
        # frontoanele (perete pana sub coama); sub streasina de la capete se vede dosul acoperisului
        m.face([R(hw, -hd, z), R(hw, hd, z), R(hw, 0.0, top)], wall_role)
        m.face([R(-hw, hd, z), R(-hw, -hd, z), R(-hw, 0.0, top)], wall_role)
        m.quad(r0, r1, e1, e0, "tavan")
        m.quad(r1, r0, e3, e2, "tavan")
        # tavanul streasinii doar pe laturile lungi, intre frontoane
        m.quad(R(-hw, -hd - o, z), R(-hw, -hd, z), R(hw, -hd, z), R(hw, -hd - o, z), "tavan")
        m.quad(R(hw, hd + o, z), R(hw, hd, z), R(-hw, hd, z), R(-hw, hd + o, z), "tavan")
    else:
        slope(e1, e2, r1)
        slope(e3, e0, r0)
        m.quad(e0, e3, e2, e1, "tavan")   # tavanul streasinii, vazut de jos
    # bordura (fascia) de jur imprejur
    drop = Vector((0.0, 0.0, -0.22))
    for a, b in ((e0, e1), (e1, e2), (e2, e3), (e3, e0)):
        m.quad(a + drop, b + drop, b, a, "ornament")


def roof_flat(m, hw, hd, z, parapet, wall_role, cornice=True, thickness=0.3, lipit=()):
    """Acoperis plat cu atic (parapet), cornisa si glafuri pe atic."""
    m.quad(Vector((-hw, -hd, z)), Vector((hw, -hd, z)), Vector((hw, hd, z)), Vector((-hw, hd, z)), "acoperis_plat")
    if parapet > 0:
        t = thickness
        m.box(-hw, -hd, z, hw, -hd + t, z + parapet, wall_role)
        m.box(-hw, hd - t, z, hw, hd, z + parapet, wall_role)
        m.box(-hw, -hd + t, z, -hw + t, hd - t, z + parapet, wall_role)
        m.box(hw - t, -hd + t, z, hw, hd - t, z + parapet, wall_role)
        ring(m, hw, hd, z + parapet, z + parapet + 0.12, 0.06, "ornament", lipit=lipit)
    if cornice:
        ring(m, hw, hd, z - 0.45, z - 0.1, 0.35, "ornament", lipit=lipit)


def cylinder(m, cx, cy, z0, z1, r, role, segments=12, cap=True):
    pts = [(cx + r * math.cos(2 * math.pi * i / segments), cy + r * math.sin(2 * math.pi * i / segments))
           for i in range(segments)]
    for i in range(segments):
        (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % segments]
        m.quad(Vector((x0, y0, z0)), Vector((x1, y1, z0)), Vector((x1, y1, z1)), Vector((x0, y0, z1)), role)
    if cap:
        m.face([Vector((x, y, z1)) for x, y in pts], role)


def water_tower(m, cx, cy, z):
    """Rezervorul de apa de pe blocurile din New York / Liberty City: butoi de lemn pe picioare de metal."""
    r = 1.8
    for sx in (-1, 1):
        for sy in (-1, 1):
            m.box(cx + sx * 1.2 - 0.1, cy + sy * 1.2 - 0.1, z, cx + sx * 1.2 + 0.1, cy + sy * 1.2 + 0.1, z + 3.0, "metal")
    m.box(cx - 1.4, cy - 1.4, z + 2.9, cx + 1.4, cy + 1.4, z + 3.05, "metal")
    cylinder(m, cx, cy, z + 3.05, z + 6.3, r, "perete_lemn", cap=False)
    segments = 12
    ring_pts = [Vector((cx + (r + 0.1) * math.cos(2 * math.pi * i / segments),
                        cy + (r + 0.1) * math.sin(2 * math.pi * i / segments), z + 6.3)) for i in range(segments)]
    apex = Vector((cx, cy, z + 7.6))
    for i in range(segments):
        m.face([ring_pts[i], ring_pts[(i + 1) % segments], apex], "metal")


def awning(m, f, u0, u1, z_top, depth=1.1, drop=0.5, role="copertina"):
    """Copertina inclinata peste un gol, cu laturi triunghiulare si fata de dedesubt."""
    a, b = f.p(u0 - 0.15, z_top), f.p(u1 + 0.15, z_top)
    c, d = f.p(u1 + 0.15, z_top - drop, -depth), f.p(u0 - 0.15, z_top - drop, -depth)
    m.quad(d, c, b, a, role)
    m.quad(a, b, c, d, role)
    m.face([a, d, f.p(u0 - 0.15, z_top - drop)], role)
    m.face([b, f.p(u1 + 0.15, z_top - drop), c], role)


def fire_escape(m, f, u0, u1, floors, floor_h, ground_h):
    """Scara de incendiu pe fatada: platforme cu balustrada la fiecare etaj, scari inclinate intre ele."""
    depth = 1.3
    for k in range(1, floors):
        z = ground_h + (k - 1) * floor_h
        f.box(m, u0, u1, -depth, 0.0, z - 0.06, z, "metal")
        f.box(m, u0, u1, -depth - 0.04, -depth, z + 0.95, z + 1.0, "metal")
        for uu in (u0, u1 - 0.04):
            f.box(m, uu, uu + 0.04, -depth, 0.0, z + 0.95, z + 1.0, "metal")
        uu = u0
        while uu <= u1:
            f.box(m, uu, uu + 0.04, -depth - 0.04, -depth, z, z + 0.95, "metal")
            uu += 1.1
        if k < floors - 1:
            # scara spre platforma de deasupra, pe diagonala
            a0, a1 = (u0 + 0.2, u0 + 0.9) if k % 2 else (u1 - 0.9, u1 - 0.2)
            z1 = z + floor_h
            b0, b1 = (u1 - 1.6, u1 - 0.9) if k % 2 else (u0 + 0.9, u0 + 1.6)
            p = [f.p(a0, z, -0.3), f.p(a1, z, -0.3), f.p(b1, z1, -0.3 - 0.0), f.p(b0, z1, -0.3)]
            q = [f.p(a0, z, -0.9), f.p(a1, z, -0.9), f.p(b1, z1, -0.9), f.p(b0, z1, -0.9)]
            m.quad(p[0], p[1], p[2], p[3], "metal")
            m.quad(p[1], p[0], p[3], p[2], "metal")
            m.quad(q[1], q[0], q[3], q[2], "metal")
            m.quad(q[0], q[1], q[2], q[3], "metal")
    # scara verticala de jos, ridicata (ca in filme)
    z = ground_h
    f.box(m, u0 + 0.2, u0 + 0.25, -depth + 0.2, -depth + 0.25, 2.4, z, "metal")
    f.box(m, u0 + 0.7, u0 + 0.75, -depth + 0.2, -depth + 0.25, 2.4, z, "metal")


def railing(m, f, u0, u1, z, depth, style, wall_role):
    """Balustrada balconului pe cele trei laturi libere: "grila" (mana curenta, stalpi, doua bare), "plin" (parapet
    de zid), "sticla" (panouri intre stalpi) sau "baluster" (balustri de piatra, la vile)."""
    h, d0 = 1.0, -depth
    if style == "plin":
        f.box(m, u0, u1, d0, d0 + 0.12, z, z + h, wall_role)
        f.box(m, u0, u0 + 0.12, d0 + 0.12, 0.0, z, z + h, wall_role)
        f.box(m, u1 - 0.12, u1, d0 + 0.12, 0.0, z, z + h, wall_role)
        f.box(m, u0 - 0.03, u1 + 0.03, d0 - 0.03, d0 + 0.15, z + h, z + h + 0.06, "ornament")
        return
    rail = "ornament" if style == "baluster" else "metal"
    t = 0.1 if style == "baluster" else 0.05
    f.box(m, u0, u1, d0, d0 + t, z + h - t, z + h, rail)
    f.box(m, u0, u0 + t, d0 + t, 0.0, z + h - t, z + h, rail)
    f.box(m, u1 - t, u1, d0 + t, 0.0, z + h - t, z + h, rail)
    if style == "baluster":
        for a, b, fixed in ((u0, u1, None), (d0, 0.0, u0), (d0, 0.0, u1)):
            k = a + 0.18
            while k < b - 0.12:
                if fixed is None:
                    f.box(m, k - 0.05, k + 0.05, d0 + 0.01, d0 + 0.09, z, z + h - t, "ornament")
                else:
                    f.box(m, fixed + 0.01 if fixed == u0 else fixed - 0.09, fixed + 0.09 if fixed == u0 else fixed - 0.01,
                          k - 0.05, k + 0.05, z, z + h - t, "ornament")
                k += 0.3
        return
    posts = max(2, int((u1 - u0) / 1.2) + 1)
    for i in range(posts):
        u = u0 + (u1 - u0 - 0.05) * i / (posts - 1)
        f.box(m, u, u + 0.05, d0, d0 + 0.05, z, z + h - t, "metal")
    if style == "sticla":
        lo, hi = z + 0.08, z + h - t
        for a, b in ((f.p(u0, 0, d0 + 0.03), f.p(u1, 0, d0 + 0.03)), (f.p(u1 - 0.03, 0, d0), f.p(u1 - 0.03, 0, 0.0)),
                     (f.p(u0 + 0.03, 0, 0.0), f.p(u0 + 0.03, 0, d0))):
            p = [a + Vector((0, 0, lo)), b + Vector((0, 0, lo)), b + Vector((0, 0, hi)), a + Vector((0, 0, hi))]
            m.face(p, "sticla")
            m.face(p[::-1], "sticla")
    else:
        for zz in (z + 0.12, z + 0.5):
            f.box(m, u0, u1, d0, d0 + 0.04, zz, zz + 0.04, "metal")
            f.box(m, u0, u0 + 0.04, d0, 0.0, zz, zz + 0.04, "metal")
            f.box(m, u1 - 0.04, u1, d0, 0.0, zz, zz + 0.04, "metal")


def balcony(m, f, u0, u1, z, depth, style, wall_role, columns=False):
    """Balcon pe fatada la inaltimea z (podeaua etajului): placa, console sau coloane pana la sol, balustrada."""
    f.box(m, u0, u1, -depth, 0.0, z - 0.2, z, "ornament")
    if columns:
        # portic: doua coloane de la sol sub colturile balconului (vilele din Vinewood)
        for u in (u0 + 0.35, u1 - 0.35):
            c = f.p(u, 0.0, -depth + 0.3)
            cylinder(m, c.x, c.y, 0.0, z - 0.2, 0.2, "ornament", segments=10)
    elif style in ("baluster", "plin"):
        for u in (u0 + 0.2, u1 - 0.4):
            f.box(m, u, u + 0.2, -depth + 0.15, 0.0, z - 0.55, z - 0.2, "ornament")
    railing(m, f, u0, u1, z, depth, style, wall_role)


def veranda(m, f, u0, u1, z_roof, depth, roof_role):
    """Veranda casei: podea joasa, stalpi albi, acoperis intr-o apa lipit de perete, cu fascia si tavan."""
    f.box(m, u0, u1, -depth, 0.0, 0.0, 0.35, "soclu")
    lo = z_roof - 0.35
    n = max(2, int((u1 - u0) / 2.4) + 1)
    for i in range(n):
        u = u0 + 0.12 + (u1 - u0 - 0.24) * i / (n - 1)
        f.box(m, u - 0.09, u + 0.09, -depth + 0.05, -depth + 0.23, 0.35, lo, "ornament")
    a, b = f.p(u0 - 0.2, z_roof), f.p(u1 + 0.2, z_roof)
    c, d = f.p(u1 + 0.2, lo, -depth - 0.3), f.p(u0 - 0.2, lo, -depth - 0.3)
    m.quad(d, c, b, a, roof_role)
    m.quad(a, b, c, d, "tavan")
    m.quad(f.p(u0 - 0.2, lo - 0.2, -depth - 0.3), f.p(u1 + 0.2, lo - 0.2, -depth - 0.3), c, d, "ornament")


# ------------------------------------------------------------------------------------------ cladiri

TYPES = (("vila", "Vila (Vinewood)", "Tencuiala, pietre de colt, acoperis in patru ape cu tigla"),
         ("casa", "Casa", "Casa de cartier, acoperis in doua ape, veranda, garaj"),
         ("bloc", "Bloc de caramida", "Bloc stil Liberty City: caramida, cornisa, scara de incendiu, magazine la parter"),
         ("magazin", "Magazin", "Un nivel, vitrina, copertina, firma deasupra"),
         ("hala", "Hala", "Hala industriala cu rulouri si acoperis de tabla"),
         ("turn", "Turn (centru)", "Turn inalt: hotel de caramida, birouri cu benzi de geam sau perete de sticla"))
# latime, adancime, etaje (din medianele cladirilor GTA intregi din catalog), inaltime etaj: masurata intre randurile
# de ferestre ale cladirilor GTA (analiza_cladiri_gta.py: midrise 3.78 m, turnuri 3.65 m, case 3.07 m)
DEFAULTS = {"vila": (20.0, 13.0, 2, 3.6), "casa": (12.0, 9.0, 1, 3.0), "bloc": (16.0, 20.0, 5, 3.5),
            "magazin": (14.0, 12.0, 1, 4.5), "hala": (30.0, 40.0, 1, 8.0), "turn": (26.0, 24.0, 16, 3.6)}
STYLE = {"vila": "vila", "casa": "vila", "bloc": "caramida", "magazin": "beton", "hala": "beton", "turn": "beton"}
# traveea (distanta dintre ferestre); blocuri si turnuri tot din masuratori (2.52 m, 2.82 m)
BAY = {"vila": 3.4, "casa": 3.2, "bloc": 2.5, "magazin": 4.0, "hala": 6.0, "turn": 2.8}


def _centers(length, bay, margin):
    n = max(1, int((length - 2 * margin) / bay))
    step = (length - 2 * margin) / n
    return [margin + step * (i + 0.5) for i in range(n)]


def _levels(p):
    """[(z jos, inaltime)] pentru fiecare etaj; parterul blocurilor si magazinelor e mai inalt."""
    h = p["inaltime"]
    ground = max(h, 4.2) if p["tip"] in ("bloc",) else h
    levels = [(0.0, ground)]
    for k in range(1, p["etaje"]):
        levels.append((ground + (k - 1) * h, h))
    return levels


def _roof_kind(p):
    if p["acoperis"] != "auto":
        return p["acoperis"]
    return {"vila": "patru", "casa": "doua", "bloc": "plat", "magazin": "plat", "hala": "doua"}[p["tip"]]


def _openings(rng, p, facades, levels, ground=True, win=None):
    """{fatada: [[goluri pe etaj]]}: ferestre in ritmul fatadelor GTA, apoi usi, vitrine, rulouri.
    ground=False: doar ferestre (etajul retras de pe acoperis nu are intrare). win = (latime, inaltime) ale geamului
    GTA ales: ferestrele iau marimea lui (textura nu se deformeaza)."""
    tip = p["tip"]
    bay = BAY[tip] * rng.uniform(0.92, 1.1)
    # fara geam GTA: marimile masurate pe cladirile GTA (midrise 1.33 x 1.72 m)
    ww = {"vila": 1.25, "casa": 1.1, "bloc": 1.3, "magazin": 1.4, "hala": 2.4}[tip] * rng.uniform(0.9, 1.15)
    wh = {"vila": 1.9, "casa": 1.35, "bloc": 1.75, "magazin": 1.3, "hala": 1.0}[tip] * rng.uniform(0.92, 1.08)
    if win and tip != "hala":
        ww, wh = win
        bay = max(bay, ww + 0.9)
    ops = {f.name: [[] for _ in levels] for f in facades}
    front_centers = []
    for f in facades:
        centers = _centers(f.length, bay, 1.0)
        if f.name == "fata":
            front_centers = centers
        side = f.name in ("stanga", "dreapta")
        skip = rng.random() * (0.5 if side else 0.2)
        for li, (z0, h) in enumerate(levels):
            if tip == "hala":
                z_w = z0 + h - 2.2        # ferestre sus, sub streasina
                if side:
                    for c in centers:
                        ops[f.name][li].append([c - ww / 2, c + ww / 2, z_w, z_w + wh, "fereastra"])
                continue
            for c in centers:
                if rng.random() < skip:
                    continue
                sill = 0.95 if tip != "magazin" else 1.2
                top = min(z0 + sill + wh, z0 + h - 0.45)
                w2 = ww * (top - z0 - sill) / wh if win else ww      # etaj prea jos: geamul GTA isi pastreaza proportia
                ops[f.name][li].append([c - w2 / 2, c + w2 / 2, z0 + sill, top, "fereastra"])
    front = ops["fata"][0]
    z0, g = levels[0]
    if not ground:
        pass
    elif tip in ("bloc", "magazin") and (tip == "magazin" or p["comercial"]):
        # parterul comercial: vitrine late pe toata fata, usa la mijloc sau pe o latura; unele magazine inchise
        # (rulou tras), cu alt sir aleator ca restul cladirii sa nu se schimbe
        front.clear()
        shut = random.Random(f"rulou:{p['seed']}")
        door_i = len(front_centers) // 2 if tip == "magazin" else rng.randrange(len(front_centers))
        step = front_centers[1] - front_centers[0] if len(front_centers) > 1 else BAY[tip]
        for i, c in enumerate(front_centers):
            if i == door_i:
                front.append([c - 0.6, c + 0.6, z0, z0 + 2.4, "usa"])
            elif tip == "bloc" and shut.random() < 0.2:
                front.append([c - step / 2 + 0.3, c + step / 2 - 0.3, z0 + 0.05, z0 + g - 1.25, "vitrina_inchisa"])
            else:
                front.append([c - step / 2 + 0.3, c + step / 2 - 0.3, z0 + 0.45, z0 + g - 1.25, "vitrina"])
    elif tip == "hala":
        n = max(1, min(3, int(facades[0].length // 12)))
        width = min(5.0, (facades[0].length - 2) / n - 1.0)
        for i in range(n):
            c = facades[0].length * (i + 1) / (n + 1)
            front.append([c - width / 2, c + width / 2, z0, z0 + min(5.0, g - 1.5), "rulou"])
        front.append([0.8, 1.8, z0, z0 + 2.2, "usa"])
    else:
        # usa de la intrare: la mijloc (vila) sau pe o travee aleasa de seed
        c = front_centers[len(front_centers) // 2] if tip == "vila" else rng.choice(front_centers)
        width = 1.5 if tip == "vila" else 1.1
        front[:] = [o for o in front if o[1] < c - width / 2 - 0.3 or o[0] > c + width / 2 + 0.3]
        front.append([c - width / 2, c + width / 2, z0, z0 + (2.6 if tip == "vila" else 2.2), "usa"])
        if tip == "casa" and p["etaje"] == 1 and facades[0].length >= 11 and rng.random() < 0.6:
            # garaj la un capat
            gx = facades[0].length - 3.8 if c < facades[0].length / 2 else 0.8
            front[:] = [o for o in front if o[1] < gx - 0.3 or o[0] > gx + 3.3]
            front.append([gx, gx + 3.0, z0, z0 + 2.3, "rulou"])
    for name in p.get("lipit", ()):
        ops[name] = [[] for _ in levels]   # perete lipit de vecin: fara goluri
    for f in facades:
        for level in ops[f.name]:
            level.sort()
    return ops


def _balconies(rng, p, facades, ops, levels, lipit, top_skip=False):
    """Unele ferestre de la etaj devin usi de balcon (in ops). Intoarce ([(fatada, u0, u1, z, adancime, coloane)],
    stilul balustradei, banda): blocurile pe coloane de travee sau in banda pe toata fatada, vilele un balcon
    central (uneori pe coloane), casele cu etaj unul mic. p["balcoane"] alege planul (niciunul / coloane / banda /
    centru / unul); lipsa = dupa seed."""
    tip = p["tip"]
    last = len(levels) - (1 if top_skip else 0)
    if last < 2 or tip in ("magazin", "hala"):
        return [], "grila", False
    plan = p.get("balcoane")
    if tip == "bloc":
        plan = plan or rng.choice(["coloane", "coloane", "banda", "niciunul"])
        style = rng.choice(["grila", "grila", "plin", "sticla"])
    elif tip == "vila":
        plan = plan or ("centru" if rng.random() < 0.75 else "niciunul")
        style = rng.choice(["baluster", "baluster", "plin"])
    else:
        plan = plan or ("unul" if rng.random() < 0.4 else "niciunul")
        style = rng.choice(["grila", "plin"])
    if plan == "niciunul":
        return [], style, False
    depth = rng.uniform(1.1, 1.6)
    every, out = rng.choice([1, 2, 2, 3]), []
    phase = rng.randrange(every)
    for f in facades:
        if f.name in lipit or f.name in ("stanga", "dreapta"):
            continue
        if f.name == "spate" and (tip != "bloc" or rng.random() < 0.5):
            continue
        cols = sorted({round((o[0] + o[1]) / 2, 2) for lvl in ops[f.name][1:last] for o in lvl if o[4] == "fereastra"})
        if not cols:
            continue
        if plan == "centru":
            # deasupra usii de la intrare (sau la mijlocul fatadei, daca pe fatada asta nu e usa)
            doors = [(o[0] + o[1]) / 2 for o in ops[f.name][0] if o[4] == "usa"]
            target = doors[0] if doors else f.length / 2
            chosen, used = {min(cols, key=lambda c: abs(c - target))}, [1]
        elif plan == "unul":
            chosen, used = {rng.choice(cols)}, [1]
        else:
            chosen = set(cols) if plan == "banda" else {c for i, c in enumerate(cols) if i % every == phase}
            used = range(1, last)
        for li in used:
            z0, h = levels[li]
            for o in ops[f.name][li]:
                c = round((o[0] + o[1]) / 2, 2)
                if o[4] != "fereastra" or c not in chosen:
                    continue
                w = max(o[1] - o[0], 1.0)
                o[:] = [c - w / 2, c + w / 2, z0 + 0.02, min(z0 + 2.3, z0 + h - 0.35), "balcon"]
                if plan != "banda":
                    extra = 1.6 if plan == "centru" else 0.5
                    out.append((f, c - w / 2 - extra, c + w / 2 + extra, z0, depth, plan == "centru" and rng.random() < 0.6))
            if plan == "banda":
                out.append((f, 0.5, f.length - 0.5, z0, depth, False))
    return out, style, plan == "banda"


def _stairs(m, x_hi, y0, y1, z0, h):
    """Scara dreapta care urca spre -X, de la x_hi; intoarce capatul de sus (x) pentru golul din placa."""
    steps = max(8, int(math.ceil(h / 0.18)))
    rise = h / steps
    run = 0.27
    for i in range(steps):
        x1 = x_hi - i * run
        m.box(x1 - run, y0, z0, x1, y1, z0 + (i + 1) * rise, "podea")
    return x_hi - steps * run


def _partition(m, a, b, axis, fixed, z0, z1, gaps, t=0.12):
    """Perete despartitor de la a la b pe axa data, cu goluri de usa (2,1 m)."""
    cuts = sorted(gaps)
    u = a
    for g0, g1 in cuts + [(b, b)]:
        if g0 > u + 0.05:
            if axis == "x":
                m.box(u, fixed - t / 2, z0, g0, fixed + t / 2, z1, "interior")
            else:
                m.box(fixed - t / 2, u, z0, fixed + t / 2, g0, z1, "interior")
        if g1 > g0 and g1 < b:
            if axis == "x":
                m.box(g0, fixed - t / 2, z0 + 2.1, g1, fixed + t / 2, z1, "interior")
            else:
                m.box(fixed - t / 2, g0, z0 + 2.1, fixed + t / 2, g1, z1, "interior")
        u = max(u, g1)


def _interior(rng, m, hw, hd, levels, t, top):
    """Podele si tavane cu gol de scara, scari, pereti despartitori cu goluri de usa."""
    ix0, ix1, iy0, iy1 = -hw + t, hw - t, -hd + t, hd - t
    sw = 1.1
    sy0, sy1 = iy1 - sw, iy1
    m.quad(Vector((ix0, iy0, 0.03)), Vector((ix1, iy0, 0.03)), Vector((ix1, iy1, 0.03)), Vector((ix0, iy1, 0.03)), "podea")
    for li, (z0, h) in enumerate(levels):
        if li + 1 < len(levels):
            x_top = _stairs(m, ix1 - 0.2, sy0, sy1, z0, h)
            zf = z0 + h
            # placa de deasupra (podea sus, tavan jos), cu gol peste scara
            for x0, x1, y0, y1 in ((ix0, ix1, iy0, sy0), (ix0, x_top - 0.3, sy0, iy1)):
                m.box(x0, y0, zf - 0.22, x1, y1, zf, "podea")
                m.quad(Vector((x0, y0, zf - 0.22)), Vector((x0, y1, zf - 0.22)), Vector((x1, y1, zf - 0.22)),
                       Vector((x1, y0, zf - 0.22)), "tavan")
        # pereti despartitori: fata / spate, apoi camere pe fata
        split = rng.uniform(iy0 + 3.0, max(iy0 + 3.0, sy0 - 1.2))
        if split < sy0 - 0.8 and ix1 - ix0 > 5.0:
            gaps = [(g, g + 0.95) for g in (rng.uniform(ix0 + 0.6, (ix0 + ix1) / 2 - 1.0),
                                             rng.uniform((ix0 + ix1) / 2, ix1 - 1.6))]
            _partition(m, ix0, ix1, "x", split, z0 + 0.03, z0 + h - 0.22, gaps)
            n_rooms = 1 + int((ix1 - ix0) / 5.5)
            for k in range(1, n_rooms):
                x = ix0 + (ix1 - ix0) * k / n_rooms + rng.uniform(-0.6, 0.6)
                g = rng.uniform(iy0 + 0.6, split - 1.6)
                _partition(m, iy0, split, "y", x, z0 + 0.03, z0 + h - 0.22, [(g, g + 0.95)])
    # tavanul ultimului etaj
    m.quad(Vector((ix0, iy0, top - 0.02)), Vector((ix0, iy1, top - 0.02)), Vector((ix1, iy1, top - 0.02)),
           Vector((ix1, iy0, top - 0.02)), "tavan")


# ------------------------------------------------------------------------------------------ turnuri (centru)

TOWER_STYLES = ("hotel", "birouri", "sticla")


def _tower_levels(p):
    """Parterul inalt (vitrine), apoi etajele."""
    h = p["inaltime"]
    g = max(h + 1.2, 4.6)
    return [(0.0, g)] + [(g + (k - 1) * h, h) for k in range(1, max(3, int(p["etaje"])))]


def _storefront(rng, f, z0, g):
    """Parterul spre strada: vitrine late pe travee de ~4.5 m si o usa dubla."""
    centers = _centers(f.length, 4.5, 0.8)
    door = rng.randrange(len(centers))
    step = centers[1] - centers[0] if len(centers) > 1 else f.length - 1.6
    out = []
    for i, c in enumerate(centers):
        if i == door:
            out.append([c - 0.9, c + 0.9, z0, z0 + 2.7, "usa"])
        else:
            out.append([c - step / 2 + 0.35, c + step / 2 - 0.35, z0 + 0.5, z0 + g - 1.0, "vitrina"])
    return out


def mullions(m, f, u0, u1, z0, z1, step, d=0.18, role="metal"):
    """Montanti verticali in fata geamului (d = adancimea geamului), la ~step m."""
    n = max(1, int(round((u1 - u0) / step)))
    for i in range(1, n):
        u = u0 + (u1 - u0) * i / n
        f.box(m, u - 0.04, u + 0.04, d - 0.06, d, z0, z1, role)


def _tower_hotel(rng, m, p, facades, levels, lipit, hw, hd, top, glass):
    """Hotelul de caramida din centru (Templar Hotel): baza de piatra cu vitrine, trunchi de caramida cu ferestre
    doua cate doua, ultimele etaje deschise la culoare, cornisa grea, firma pe acoperis, scara de incendiu."""
    body = p.get("perete") if p.get("perete") in ("perete_caramida", "perete_beton") else "perete_caramida"
    stone = "perete_vila"
    n, g = len(levels), levels[0][1]
    crown = 2 if n > 6 else 1
    pair = rng.random() < 0.55
    bay = rng.uniform(2.5, 3.0) * (2 if pair else 1)
    ww = rng.uniform(1.1, 1.35)         # turnurile GTA: geamuri de 1.32 x 2.09 m
    wh = 2.0
    if m.win:           # geamul GTA ales: marimea lui reala
        ww, wh = m.win
        bay = max(bay, 2 * ww + 1.0 if pair else ww + 0.9)
    doors = {}
    for f in facades:
        centers = _centers(f.length, bay, 1.0)
        for li, (z0, h) in enumerate(levels):
            if f.name in lipit:
                ops = []
            elif li == 0:
                ops = (_storefront(rng, f, z0, h) if f.name == "fata"
                       else [[c - 0.8, c + 0.8, z0 + 1.6, z0 + h - 0.6, "fereastra"] for c in centers[::2]])
                doors[f.name] = [(o[0], o[1]) for o in ops if o[4] == "usa"]
            else:
                v1 = min(z0 + 0.9 + wh, z0 + h - 0.4)
                ops = []
                for c in centers:
                    if pair:
                        ops += [[c - ww - 0.12, c - 0.12, z0 + 0.9, v1, "fereastra"], [c + 0.12, c + ww + 0.12, z0 + 0.9, v1, "fereastra"]]
                    else:
                        ops.append([c - ww / 2, c + ww / 2, z0 + 0.9, v1, "fereastra"])
            role = stone if li < 2 or li >= n - crown else body
            wall_band(m, f, z0, z0 + h, ops, role, glass=glass(li), frames=("usi" if m.win else True) if li < 3 else False)
            for u0, u1, v0, v1, kind in ops:
                if kind == "fereastra" and li > 0:
                    window_trim(m, f, u0, u1, v0, v1, "caramida" if role == body else "vila")
                elif kind == "vitrina" and rng.random() < 0.5:
                    awning(m, f, u0, u1, v1 + 0.5)
    z2 = levels[min(2, n - 1)][0]
    ring(m, hw, hd, 0.0, 0.45, 0.05, "soclu", doors, lipit)
    ring(m, hw, hd, z2 - 0.4, z2 + 0.05, 0.25, "ornament", lipit=lipit)          # brau peste baza de piatra
    zc = levels[n - crown][0]
    ring(m, hw, hd, zc - 0.25, zc + 0.05, 0.15, "ornament", lipit=lipit)
    if not lipit:
        quoins(m, hw, hd, 0.45, z2 - 0.4)
    roof_flat(m, hw, hd, top, 1.2, body, cornice=True, lipit=lipit)
    ring(m, hw, hd, top - 1.0, top - 0.45, 0.7, "ornament", lipit=lipit)          # cornisa grea
    m.quad(Vector((-hw, -hd, top - 0.02)), Vector((-hw, hd, top - 0.02)), Vector((hw, hd, top - 0.02)),
           Vector((hw, -hd, top - 0.02)), "tavan")
    m.box(-hw + 1.5, hd - 4.5, top, -hw + 4.5, hd - 1.5, top + 2.8, body)         # iesirea scarii
    if rng.random() < 0.3 and hw > 5 and hd > 5:
        water_tower(m, rng.uniform(0.0, hw - 3.0), rng.uniform(-hd + 3.0, 0.0), top)
    if rng.random() < 0.65 and "fata" not in lipit:
        # firma pe acoperis: stalpi de metal si panoul
        f = facades[0]
        a, b = f.length * 0.2, f.length * 0.8
        for u in (a, (a + b) / 2, b):
            f.box(m, u - 0.06, u + 0.06, 1.0, 1.12, top + 1.2, top + 5.2, "metal")
        f.box(m, a, b, 1.12, 1.2, top + 2.6, top + 5.0, "metal")
    side = [f for f in (facades[1], facades[3]) if f.name not in lipit]
    if side and rng.random() < 0.6:
        f = rng.choice(side)
        span = min(f.length - 2.0, 6.0)
        u0 = rng.uniform(1.0, f.length - span - 1.0)
        fire_escape(m, f, u0, u0 + span, n, levels[1][1], g)
    return body


def _tower_office(rng, m, p, facades, levels, lipit, hw, hd, top, glass):
    """Turnul de birouri anii '70 (langa Pillbox Hill): placi de beton iesite la fiecare etaj, benzi continue de
    geam cu montanti, parter retras intre stalpi, ultimele etaje in trepte cu terase spre strada."""
    concrete = "perete_beton"
    n, g = len(levels), levels[0][1]
    steps = rng.choice([0, 2, 3]) if n > 6 and "fata" not in lipit else 0
    step = rng.uniform(2.2, 3.0)
    slab = rng.uniform(0.45, 0.8)
    inset = 0.0 if lipit else 1.5
    for f in rect_facades(hw - inset, hd - inset):
        if f.name in lipit:
            ops = []
        elif f.name == "fata":
            c = f.length / 2
            ops = [[0.4, c - 1.3, 0.15, g - 0.5, "vitrina"], [c - 1.0, c + 1.0, 0.0, 2.7, "usa"],
                   [c + 1.3, f.length - 0.4, 0.15, g - 0.5, "vitrina"]]
        else:
            ops = [[0.4, f.length - 0.4, 0.15, g - 0.5, "vitrina"]]
        wall_band(m, f, 0.0, g, ops, concrete, glass="sticla")
    if inset:
        # stalpii de pe contur si tavanul galeriei de sub primul etaj
        for f in facades:
            k = max(1, round((f.length - 0.8) / 6.0))
            for i in range(k):
                u = 0.4 + (f.length - 0.8) * i / k
                f.box(m, u - 0.3, u + 0.3, 0.2, 0.8, 0.0, g, concrete)
        m.quad(Vector((-hw, -hd, g - 0.3)), Vector((-hw, hd, g - 0.3)), Vector((hw, hd, g - 0.3)), Vector((hw, -hd, g - 0.3)), "tavan")
    s_prev = 0.0
    for li in range(1, n):
        z0, h = levels[li]
        s = step * max(0, li - (n - 1 - steps)) if steps else 0.0
        if s > s_prev:
            # terasa in fata treptei: podea si balustrada de sticla pe margine
            m.quad(Vector((-hw, -hd + s_prev, z0)), Vector((hw, -hd + s_prev, z0)), Vector((hw, -hd + s, z0)),
                   Vector((-hw, -hd + s, z0)), "acoperis_plat")
            railing(m, Facade((-hw, -hd + s), (hw, -hd + s), "fata"), 0.1, 2 * hw - 0.1, z0, s - s_prev, "sticla", concrete)
            s_prev = s
        m.shift = Vector((0.0, s / 2, 0.0))
        rd = hd - s / 2
        for f in rect_facades(hw, rd):
            if f.name in lipit:
                wall_band(m, f, z0, z0 + h, [], concrete)
                continue
            v0, v1 = z0 + 0.95, z0 + h - 0.4
            wall_band(m, f, z0, z0 + h, [[0.35, f.length - 0.35, v0, v1, "fereastra"]], concrete, glass=glass(li),
                      frames=False)
            if s:       # etajele in trepte au montantii lor; restul, un montant pe toata inaltimea (mai jos)
                mullions(m, f, 0.35, f.length - 0.35, v0, v1, 1.5)
        ring(m, hw, rd, z0 - 0.3, z0 + 0.02, slab, "ornament", lipit=lipit)       # placa etajului, iesita
        m.shift = Vector((0.0, 0.0, 0.0))
    # montantii etajelor drepte: prin spaleti trec in spatele peretelui, deci se vad doar pe benzile de geam
    z_steps = levels[n - steps][0] if steps else top
    for f in facades:
        if f.name not in lipit:
            mullions(m, f, 0.35, f.length - 0.35, levels[1][0], z_steps, 1.5)
    s = s_prev
    m.shift = Vector((0.0, s / 2, 0.0))
    rd = hd - s / 2
    ring(m, hw, rd, top - 0.3, top + 0.02, slab, "ornament", lipit=lipit)
    roof_flat(m, hw, rd, top, 1.0, concrete, cornice=False, lipit=lipit)
    m.quad(Vector((-hw, -rd, top - 0.32)), Vector((-hw, rd, top - 0.32)), Vector((hw, rd, top - 0.32)),
           Vector((hw, -rd, top - 0.32)), "tavan")
    m.box(-hw + 2.0, rd - 5.0, top, -hw + 6.0, rd - 1.5, top + 3.0, concrete)       # casa liftului
    for _ in range(rng.randint(2, 4)):
        x, y = rng.uniform(-hw + 2, hw - 3), rng.uniform(-rd + 2, rd - 3)
        m.box(x, y, top, x + 1.6, y + 1.1, top + 1.2, "metal")
    m.shift = Vector((0.0, 0.0, 0.0))
    return concrete


def _tower_glass(rng, m, p, facades, levels, lipit, hw, hd, top, glass):
    """Turnul de sticla din centru: soclu de piatra cu vitrine, perete cortina (panouri de geam intre montanti, o
    banda la fiecare placa), varful mai ingust cu terasa, aripioare si antena."""
    stone = rng.choice(["perete_beton", "perete_vila"])
    n = len(levels)
    podium = 2 if n > 8 else 1
    crown = rng.choice([2, 3]) if n > 10 else 0
    inset = rng.uniform(1.5, 2.5) if crown else 0.0
    col = rng.uniform(1.4, 1.8)           # latimea unui panou de geam
    doors = {}
    for li, (z0, h) in enumerate(levels):
        c = inset if crown and li >= n - crown else 0.0
        if c and li == n - crown:
            roof_flat(m, hw, hd, z0, 1.1, stone, cornice=False, lipit=lipit)         # terasa din jurul varfului
        for f in rect_facades(hw - c, hd - c):
            if f.name in lipit and not c:
                wall_band(m, f, z0, z0 + h, [], stone)
                continue
            if li < podium:
                ops = (_storefront(rng, f, z0, h) if li == 0 and f.name == "fata"
                       else [[0.5, f.length - 0.5, z0 + 0.6, z0 + h - 0.6, "vitrina"]])
                if li == 0:
                    doors[f.name] = [(o[0], o[1]) for o in ops if o[4] == "usa"]
                wall_band(m, f, z0, z0 + h, ops, stone, glass="sticla" if li == 0 else glass(li))
                continue
            k = max(1, round(f.length / col))
            pick = glass(li)
            for i in range(k):
                u0, u1 = f.length * i / k, f.length * (i + 1) / k
                role = pick() if callable(pick) else pick
                m.quad(f.p(u0, z0 + 0.3, 0.06), f.p(u1, z0 + 0.3, 0.06), f.p(u1, z0 + h, 0.06), f.p(u0, z0 + h, 0.06), role)
            f.box(m, 0.0, f.length, -0.04, 0.06, z0, z0 + 0.3, "metal")              # banda la placa
    z_a = levels[podium][0]
    z_b = levels[n - crown][0] if crown else top
    # montantii verticali: un stalp pe toata inaltimea pe fiecare linie de panouri
    for c, z0, z1 in ((0.0, z_a, z_b), (inset, z_b, top)) if crown else ((0.0, z_a, top),):
        for f in rect_facades(hw - c, hd - c):
            if f.name in lipit and not c:
                continue
            k = max(1, round(f.length / col))
            for i in range(k + 1):
                u = f.length * i / k
                f.box(m, u - 0.05, u + 0.05, -0.1, 0.06, z0, z1, "metal")
    ring(m, hw, hd, 0.0, 0.45, 0.05, "soclu", doors, lipit)
    ring(m, hw, hd, z_a - 0.4, z_a + 0.05, 0.3, "ornament", lipit=lipit)            # brau peste soclu
    rw, rd = hw - inset, hd - inset
    roof_flat(m, rw, rd, top, 1.4, stone, cornice=False)
    m.quad(Vector((-rw, -rd, top - 0.02)), Vector((-rw, rd, top - 0.02)), Vector((rw, rd, top - 0.02)),
           Vector((rw, -rd, top - 0.02)), "tavan")
    if rng.random() < 0.5:
        # aripioare verticale pe marginea acoperisului (coroana)
        for f in rect_facades(rw, rd):
            k = max(1, int(f.length / 3.0))
            for i in range(1, k):
                u = f.length * i / k
                f.box(m, u - 0.12, u + 0.12, -0.35, 0.1, top, top + 2.6, "metal")
    m.box(-0.12, -0.12, top, 0.12, 0.12, top + rng.uniform(6.0, 14.0), "metal")      # antena
    cylinder(m, rw * 0.5, -rd * 0.4, top, top + 1.0, 0.6, "metal", segments=10)
    return stone


def build_tower(p):
    """Turn de centru, dupa cladirile din Los Santos: "hotel", "birouri" sau "sticla" (p["stil"]; lipsa = dupa
    seed). Fara interior. (obiect, None), ca build()."""
    rng = random.Random(p["seed"])
    materials = Materials(p["texturi"], rng)
    stil = p.get("stil") if p.get("stil") in TOWER_STYLES else rng.choice(TOWER_STYLES)
    lipit = tuple(p.get("lipit", ()))
    hw, hd = p["latime"] / 2, p["adancime"] / 2
    levels = _tower_levels(p)
    top = levels[-1][0] + levels[-1][1]
    lit = rng.uniform(0.15, 0.45)       # pastrat: tine sirul lui rng la fel ca inainte
    # ferestrele aprinse noaptea: 6-22% din geamuri, alese unul cate unul, cu alt rng (restul cladirii nu se schimba)
    lamp = random.Random(p["seed"] * 7 + 1)
    share = 0.06 + (lit - 0.15) / 0.30 * 0.16
    glass = lambda li: (lambda: "geam_noapte" if li > 0 and lamp.random() < share else "geam")
    m = Mesh(materials)
    if stil == "hotel" and materials.mode == "gta" and p.get("geam_gta", True):
        body = p.get("perete") if p.get("perete") in ("perete_caramida", "perete_beton") else "perete_caramida"
        win = gta_window(random.Random(f"geam:{p['seed']}"), "turn", _tex_name(materials.get(body)[0]))
        if win:
            use_gta_window(materials, m, win)
    fn = {"hotel": _tower_hotel, "birouri": _tower_office, "sticla": _tower_glass}[stil]
    wall = fn(rng, m, p, rect_facades(hw, hd), levels, lipit, hw, hd, top, glass)
    obj = m.to_object(f"turn_{stil}_{p['seed']}")
    obj["harta_tip"] = "cladire"
    obj["harta_gen"] = json.dumps(p)
    obj["fivem_lod"] = 1200.0       # turnurile se vad de departe (silueta orasului), nu doar de la 300 m
    wall_mat, wall_scale = materials.get(wall)
    obj["perete_mat"], obj["perete_scala"] = wall_mat.name, float(wall_scale)
    return obj, None


def build(p):
    """Cladirea dupa parametri: (obiect exterior, obiect interior sau None). Originea = mijlocul bazei."""
    if p["tip"] == "turn":
        return build_tower(p)
    rng = random.Random(p["seed"])
    tip = p["tip"]
    materials = Materials(p["texturi"], rng)
    # casele: tencuiala sau caramida, fara scanduri / paleti
    wall = {"vila": "perete_vila", "casa": rng.choice(["perete_vila", "perete_caramida"]), "bloc": "perete_caramida",
            "magazin": rng.choice(["perete_beton", "perete_caramida"]), "hala": "perete_beton"}[tip]
    wall = p.get("perete") or wall
    lipit = tuple(p.get("lipit", ()))
    hw, hd = p["latime"] / 2, p["adancime"] / 2
    levels = _levels(p)
    top = levels[-1][0] + levels[-1][1]
    thick = 0.25 if p["interior"] else 0.0
    ext = Mesh(materials)
    inner = Mesh(materials) if p["interior"] else None
    facades = rect_facades(hw, hd)
    # geamul GTA potrivit peretelui (cu alt sir aleator: restul cladirii iese la fel ca inainte)
    if materials.mode == "gta" and tip != "hala" and not p["interior"] and p.get("geam_gta", True):
        win = gta_window(random.Random(f"geam:{p['seed']}"), tip, _tex_name(materials.get(wall)[0]))
        if win:
            use_gta_window(materials, ext, win)
    ops = _openings(rng, p, facades, levels, win=ext.win)
    kind = _roof_kind(p)
    roof_role = "tabla" if tip == "hala" else ("acoperis_ardezie" if tip == "casa" and rng.random() < 0.35 else "acoperis_tigla")
    # etajul de sus retras de la strada, cu terasa in fata (blocurile inalte); p["retras"] il cere sau il opreste
    retras = p.get("retras")
    if retras is None:
        retras = tip == "bloc" and len(levels) >= 4 and rng.random() < 0.35
    s = rng.uniform(2.0, 3.2) if retras and not p["interior"] and "fata" not in lipit and hd > 4.0 else 0.0
    up_shift = Vector((0.0, s / 2, 0.0))
    bands = [(li, z0, h, facades, {f.name: ops[f.name][li] for f in facades}) for li, (z0, h) in enumerate(levels)]
    if s:
        up_facades = rect_facades(hw, hd - s / 2)
        up_ops = _openings(rng, p, up_facades, levels[-1:], ground=False, win=ext.win)
        bands[-1] = (len(levels) - 1, levels[-1][0], levels[-1][1], up_facades,
                     {f.name: up_ops[f.name][0] for f in up_facades})
    balconies, rail, strip = _balconies(rng, p, facades, ops, levels, lipit, bool(s))
    rng.random()        # era "night" (toata cladirea aprinsa); pastrat ca sirul lui rng sa ramana la fel
    # ferestrele aprinse noaptea: cateva geamuri alese la intamplare (5-25% din cladire), cu alt rng
    lamp = random.Random(p["seed"] * 7 + 1)
    share = lamp.uniform(0.05, 0.25)
    shutters = tip in ("vila", "casa") and rng.random() < 0.4
    ac = tip in ("bloc", "magazin") and rng.random() < 0.5
    porch = (tip == "casa" and "fata" not in lipit and not any(o[4] == "rulou" for o in ops["fata"][0])
             and rng.random() < 0.55)
    sign_i = 0
    for li, z0, h, fs, level_ops in bands:
        ext.shift = up_shift if s and li == len(levels) - 1 else Vector((0.0, 0.0, 0.0))
        for f in fs:
            lvl = level_ops[f.name]
            glass = "sticla" if p["interior"] else (lambda: "geam_noapte" if lamp.random() < share else "geam")
            wall_band(ext, f, z0, z0 + h, [tuple(o) for o in lvl], wall, thick, glass=glass,
                      door="usa_metal" if tip == "hala" else "usa", frames="usi" if ext.win else True)
            for u0, u1, v0, v1, okind in lvl:
                if okind == "fereastra":
                    window_trim(ext, f, u0, u1, v0, v1, STYLE[tip])
                    if shutters:
                        w = (u1 - u0) / 2
                        f.box(ext, u0 - w - 0.03, u0 - 0.03, -0.07, 0.0, v0, v1, "perete_lemn")
                        f.box(ext, u1 + 0.03, u1 + w + 0.03, -0.07, 0.0, v0, v1, "perete_lemn")
                    elif tip == "vila" and li > 0 and rng.random() < 0.35:
                        awning(ext, f, u0, u1, v1 + 0.35, depth=0.6, drop=0.35)
                    if ac and li > 0 and rng.random() < 0.15:
                        c = (u0 + u1) / 2     # aparat de aer conditionat sub fereastra
                        f.box(ext, c - 0.38, c + 0.38, -0.5, 0.0, v0 - 0.62, v0 - 0.14, "metal")
                elif okind in ("vitrina", "vitrina_inchisa"):
                    if okind == "vitrina":
                        awning(ext, f, u0, u1, v1 + 0.4)
                    if li == 0 and ext.materials.has("firma"):
                        # firma magazinului: placa deasupra copertinei, alta la fiecare magazin
                        if tip == "magazin":
                            zb, zt, dd = top + 0.25, top + 1.35, -0.15     # pe panoul de deasupra vitrinelor
                        else:
                            zt = min(v1 + 1.15, levels[0][1] - 0.3)
                            zb, dd = zt - 0.6, 0.0
                        f.box(ext, u0 - 0.15, u1 + 0.15, dd - 0.12, dd, zb, zt, ("firma", "firma2", "firma3")[sign_i % 3])
                        sign_i += 1
                elif okind == "usa":
                    if tip == "vila":
                        # ancadrament de piatra si trepte
                        f.box(ext, u0 - 0.35, u0, -0.12, 0.02, 0.0, v1 + 0.35, "ornament")
                        f.box(ext, u1, u1 + 0.35, -0.12, 0.02, 0.0, v1 + 0.35, "ornament")
                        f.box(ext, u0 - 0.35, u1 + 0.35, -0.14, 0.02, v1, v1 + 0.45, "ornament")
                    if li == 0:
                        f.box(ext, u0 - 0.4, u1 + 0.4, -0.7, 0.0, 0.0, 0.08, "soclu")   # prag in fata usii
                    if tip == "casa" and porch and f.name == "fata" and li == 0:
                        width = min(f.length - 1.0, rng.uniform(4.5, 8.0))
                        a = min(max(0.4, (u0 + u1) / 2 - width / 2), f.length - 0.4 - width)
                        veranda(ext, f, a, a + width, levels[0][1] - 0.15, 2.2, roof_role)
                    elif tip == "casa":
                        awning(ext, f, u0 - 0.6, u1 + 0.6, v1 + 0.5, depth=1.6, drop=0.3)
    ext.shift = Vector((0.0, 0.0, 0.0))
    for f, u0, u1, z, depth, columns in balconies:
        balcony(ext, f, max(u0, 0.3), min(u1, f.length - 0.3), z, depth, rail, wall, columns)
    # soclu cu goluri la usi, brauri, pietre de colt
    gaps = {f.name: [(o[0], o[1]) for o in ops[f.name][0] if o[4] in ("usa", "rulou", "gol", "vitrina_inchisa")]
            for f in facades}
    if tip != "hala":
        ring(ext, hw, hd, 0.0, 0.45, 0.05, "soclu", gaps, lipit)
    if tip == "vila":
        quoins(ext, hw, hd, 0.45, top)
    if tip == "bloc":
        ring(ext, hw, hd, levels[0][1] - 0.25, levels[0][1] + 0.05, 0.12, "ornament", lipit=lipit)
    z_body = levels[-1][0] if s else top      # pana aici cladirea e pe tot dreptunghiul
    if tip == "bloc" and rng.random() < 0.45:
        # brau la fiecare etaj
        for z0, _h in levels[2:len(levels) - (1 if s else 0)]:
            ring(ext, hw, hd, z0 - 0.1, z0 + 0.08, 0.06, "ornament", lipit=lipit)
    if tip in ("bloc", "magazin") and not strip and "fata" not in lipit and rng.random() < 0.35:
        # pilastri intre travee, pe fata (de la parterul comercial in sus)
        rows = ops["fata"][1:len(levels) - (1 if s else 0)] if tip == "bloc" else ops["fata"][:1]
        cols = sorted({round((o[0] + o[1]) / 2, 2) for lvl in rows for o in lvl if o[4] in ("fereastra", "balcon", "vitrina")})
        z_from = levels[0][1] if tip == "bloc" else 0.45
        for a, b in zip(cols, cols[1:]):
            u = (a + b) / 2
            facades[0].box(ext, u - 0.22, u + 0.22, -0.12, 0.0, z_from, z_body, "ornament")
    rw, rd = hw, hd       # dreptunghiul pe care sta acoperisul
    if s:
        # terasa din fata etajului retras: acoperisul partii late, parapet plin pe marginea libera, cornisa
        zt = levels[-1][0]
        ext.quad(Vector((-hw, -hd, zt)), Vector((hw, -hd, zt)), Vector((hw, hd, zt)), Vector((-hw, hd, zt)), "acoperis_plat")
        ext.quad(Vector((-hw, -hd, zt - 0.02)), Vector((-hw, hd, zt - 0.02)), Vector((hw, hd, zt - 0.02)),
                 Vector((hw, -hd, zt - 0.02)), "tavan")
        facades[0].box(ext, 0.0, facades[0].length, 0.0, 0.3, zt, zt + 1.0, wall)
        if "stanga" not in lipit:
            ext.box(-hw, -hd + 0.3, zt, -hw + 0.3, -hd + s, zt + 1.0, wall)
        if "dreapta" not in lipit:
            ext.box(hw - 0.3, -hd + 0.3, zt, hw, -hd + s, zt + 1.0, wall)
        facades[0].box(ext, -0.06, facades[0].length + 0.06, -0.06, 0.3, zt + 1.0, zt + 1.12, "ornament")
        ring(ext, hw, hd, zt - 0.45, zt - 0.1, 0.35, "ornament", lipit=lipit)
        ext.shift = up_shift
        rd = hd - s / 2
    if kind == "plat":
        parapet = 1.1 if tip == "bloc" else 0.8
        roof_flat(ext, rw, rd, top, parapet, wall, cornice=tip in ("bloc", "vila"), lipit=lipit)
        if inner is None:
            ext.quad(Vector((-rw, -rd, top - 0.02)), Vector((-rw, rd, top - 0.02)), Vector((rw, rd, top - 0.02)),
                     Vector((rw, -rd, top - 0.02)), "tavan")
        if tip == "magazin":
            # firma: panou inalt deasupra vitrinei
            facades[0].box(ext, 0.0, facades[0].length, -0.15, 0.3, top, top + 1.6, wall)
        if tip == "bloc":
            ext.box(-rw + 1.5, rd - 4.5, top, -rw + 4.5, rd - 1.5, top + 2.6, wall)   # iesirea scarii pe acoperis
            for _ in range(rng.randint(1, 3)):
                x, y = rng.uniform(-rw + 2, rw - 3), rng.uniform(-rd + 2, rd - 6)
                ext.box(x, y, top, x + 1.2, y + 0.9, top + 0.9, "metal")
            if rng.random() < p.get("rezervor", 0.55) and rw > 4 and rd > 5:
                water_tower(ext, rng.uniform(0.0, rw - 3.0), rng.uniform(-rd + 3.0, 0.0), top)
        if tip in ("bloc", "magazin") and rw > 3 and rd > 3:
            # guri de aerisire si o antena
            for _ in range(rng.randint(0, 2)):
                x, y = rng.uniform(-rw + 1.5, rw - 1.5), rng.uniform(-rd + 1.5, rd - 1.5)
                cylinder(ext, x, y, top, top + rng.uniform(0.6, 1.2), 0.25, "metal", segments=8)
            if rng.random() < 0.5:
                x, y = rng.uniform(-rw + 1.0, rw - 1.0), rng.uniform(-rd + 1.0, rd - 1.0)
                ext.box(x - 0.04, y - 0.04, top, x + 0.04, y + 0.04, top + rng.uniform(2.0, 4.0), "metal")
    else:
        rise = min(rw, rd) * (0.12 if tip == "hala" else 0.55 if kind == "patru" else 0.6)
        over = 0.35 if tip == "hala" else rng.uniform(0.45, 0.7)
        roof_pitched(ext, rw, rd, top, rise, over, kind, roof_role, wall)
        if tip in ("vila", "casa") and rng.random() < 0.8:
            cx, cy = rng.uniform(-rw * 0.5, rw * 0.5), rng.uniform(-rd * 0.3, rd * 0.3)
            ext.box(cx - 0.45, cy - 0.45, top - 0.5, cx + 0.45, cy + 0.45, top + rise + 0.9, wall)
            ext.box(cx - 0.55, cy - 0.55, top + rise + 0.9, cx + 0.55, cy + 0.55, top + rise + 1.05, "ornament")
    ext.shift = Vector((0.0, 0.0, 0.0))
    if tip == "bloc" and len(levels) > 2 and rng.random() < p.get("scara_incendiu", 0.75):
        # nu pe fatada cu balcoane si nu pe cea lipita de vecin
        busy = {b[0].name for b in balconies}
        free = [f for f in facades[:2] if f.name not in lipit and f.name not in busy]
        if free:
            f = free[0] if rng.random() < 0.6 else free[-1]
            span = min(f.length - 2.0, BAY["bloc"] * 2.5)
            u0 = rng.uniform(1.0, f.length - span - 1.0)
            fire_escape(ext, f, u0, u0 + span, len(levels) - (1 if s else 0), levels[1][1], levels[0][1])
    if inner is not None:
        _interior(rng, inner, hw, hd, levels, thick, top)
    name = f"{tip}_{p['seed']}"
    obj = ext.to_object(name)
    obj["harta_tip"] = "cladire"
    obj["harta_gen"] = json.dumps(p)
    wall_mat, wall_scale = materials.get(wall)
    obj["perete_mat"], obj["perete_scala"] = wall_mat.name, float(wall_scale)   # fundatia ia peretele casei
    inside = None
    if inner is not None and inner.faces:
        inside = inner.to_object(f"{name}_interior")
        inside["harta_tip"] = "cladire_interior"
    return obj, inside


# ------------------------------------------------------------------------------------------ interfata

COLLECTION = "Cladiri generate"


def params_of(s) -> dict:
    return {"tip": s.tip, "latime": round(s.latime, 2), "adancime": round(s.adancime, 2), "etaje": s.etaje,
            "inaltime": round(s.inaltime, 2), "acoperis": s.acoperis, "interior": s.interior,
            "comercial": s.comercial, "texturi": s.texturi, "seed": s.seed}


def generated(obj):
    """Cladirea generata din care face parte obiectul (el insusi sau parintele lui), sau None."""
    while obj is not None and obj.get("harta_tip") != "cladire":
        obj = obj.parent
    return obj


def place(context, p, matrix=None):
    """Genereaza cladirea si o pune in scena (la cursorul 3D sau in locul uneia vechi), selectata."""
    obj, inside = build(p)
    coll = bpy.data.collections.get(COLLECTION) or bpy.data.collections.new(COLLECTION)
    if coll.name not in context.scene.collection.children:
        context.scene.collection.children.link(coll)
    coll.objects.link(obj)
    if inside is not None:
        coll.objects.link(inside)
        inside.parent = obj
    if matrix is not None:
        obj.matrix_world = matrix
    else:
        obj.location = context.scene.cursor.location
    for other in context.selected_objects:
        other.select_set(False)
    obj.select_set(True)
    context.view_layer.objects.active = obj
    return obj


def remove(obj):
    for child in list(obj.children_recursive):
        bpy.data.objects.remove(child)
    bpy.data.objects.remove(obj)


def _drop(context):
    """Pe teren, cu unealta "Pune pe sol" din tab-ul Harta (daca exista teren)."""
    if hasattr(bpy.ops, "harta") and hasattr(bpy.ops.harta, "drop"):
        try:
            bpy.ops.harta.drop()
        except RuntimeError:
            pass


def _on_type(self, _context):
    self.latime, self.adancime, self.etaje, self.inaltime = DEFAULTS[self.tip]


class CladireSettings(bpy.types.PropertyGroup):
    tip: bpy.props.EnumProperty(name="Tip", items=TYPES, default="vila", update=_on_type)
    latime: bpy.props.FloatProperty(name="Latime", default=20.0, min=4.0, max=120.0, subtype="DISTANCE")
    adancime: bpy.props.FloatProperty(name="Adancime", default=13.0, min=4.0, max=120.0, subtype="DISTANCE")
    etaje: bpy.props.IntProperty(name="Etaje", default=2, min=1, max=12)
    inaltime: bpy.props.FloatProperty(name="Inaltime etaj", default=3.6, min=2.6, max=10.0, subtype="DISTANCE")
    acoperis: bpy.props.EnumProperty(name="Acoperis", default="auto", items=(
        ("auto", "Acoperis dupa tip", ""), ("patru", "In patru ape", ""), ("doua", "In doua ape", ""),
        ("plat", "Plat, cu atic", "")))
    interior: bpy.props.BoolProperty(name="Interior (se poate intra)", default=False,
                                     description="Podele, scari, camere cu goluri de usa; usa de la intrare e deschisa")
    comercial: bpy.props.BoolProperty(name="Magazine la parter", default=True)
    texturi: bpy.props.EnumProperty(name="Texturi", default="gta", items=(
        ("gta", "GTA", "Materialele originale din biblioteca GTA"),
        ("simple", "Simple", "Texturile generatorului, usor de inlocuit")))
    seed: bpy.props.IntProperty(name="Seed", default=1, min=0)


class CLADIRE_OT_generate(bpy.types.Operator):
    bl_idname = "cladire.generate"
    bl_label = "Genereaza"
    bl_description = "Cladire noua la cursorul 3D (Shift + click dreapta pe teren muta cursorul)"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        p = params_of(context.scene.harta_cladire)
        obj = place(context, p)
        _drop(context)
        self.report({"INFO"}, f"{obj.name}: {p['latime']:.0f} x {p['adancime']:.0f} m, {p['etaje']} etaje")
        return {"FINISHED"}


class CLADIRE_OT_new_seed(bpy.types.Operator):
    bl_idname = "cladire.new_seed"
    bl_label = "Seed nou"
    bl_description = "Seed la intamplare: refaci cladirea selectata (pe loc) sau generezi una noua"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        s = context.scene.harta_cladire
        s.seed = random.randint(1, 999999)
        old = generated(context.active_object)
        if old is not None and old.select_get():
            matrix = old.matrix_world.copy()
            remove(old)
            place(context, params_of(s), matrix)
        else:
            place(context, params_of(s))
            _drop(context)
        return {"FINISHED"}


class CLADIRE_OT_apply(bpy.types.Operator):
    bl_idname = "cladire.apply"
    bl_label = "Refa cu setarile de sus"
    bl_description = "Refaci cladirea selectata, pe acelasi loc, cu setarile din panou"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return generated(context.active_object) is not None

    def execute(self, context):
        old = generated(context.active_object)
        matrix = old.matrix_world.copy()
        remove(old)
        place(context, params_of(context.scene.harta_cladire), matrix)
        return {"FINISHED"}


class CLADIRE_OT_read(bpy.types.Operator):
    bl_idname = "cladire.read"
    bl_label = "Ia setarile ei"
    bl_description = "Pune in panou setarile cladirii selectate (tip, marime, seed...)"

    @classmethod
    def poll(cls, context):
        return generated(context.active_object) is not None

    def execute(self, context):
        p = json.loads(generated(context.active_object)["harta_gen"])
        s = context.scene.harta_cladire
        s.tip = p["tip"]                  # intai tipul: el pune dimensiunile implicite
        for key in ("latime", "adancime", "etaje", "inaltime", "acoperis", "interior", "comercial", "texturi", "seed"):
            setattr(s, key, p[key])
        return {"FINISHED"}


class HARTA_PT_cladiri(bpy.types.Panel):
    bl_label = "5. Genereaza cladire"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Harta"
    bl_order = 50

    def draw(self, context):
        s = context.scene.harta_cladire
        layout = self.layout
        layout.prop(s, "tip", text="")
        col = layout.column(align=True)
        col.prop(s, "latime")
        col.prop(s, "adancime")
        col.prop(s, "etaje")
        col.prop(s, "inaltime")
        layout.prop(s, "acoperis", text="")
        layout.row().prop(s, "texturi", expand=True)
        layout.prop(s, "interior")
        if s.tip == "bloc":
            layout.prop(s, "comercial")
        row = layout.row(align=True)
        row.prop(s, "seed")
        row.operator("cladire.new_seed", text="", icon="FILE_REFRESH")
        layout.operator("cladire.generate", icon="HOME")
        old = generated(context.active_object)
        if old is not None:
            box = layout.box()
            box.label(text=f"Selectata: {old.name}")
            row = box.row(align=True)
            row.operator("cladire.apply", icon="FILE_REFRESH")
            row.operator("cladire.read", icon="IMPORT")
        layout.label(text="Shift + click dreapta = unde apare", icon="INFO")


CLASSES = (CladireSettings, CLADIRE_OT_generate, CLADIRE_OT_new_seed, CLADIRE_OT_apply, CLADIRE_OT_read,
           HARTA_PT_cladiri)


def register():
    for cls in CLASSES:
        old = getattr(bpy.types, cls.__name__, None)
        if old is not None:
            try:
                bpy.utils.unregister_class(old)
            except RuntimeError:
                pass
        bpy.utils.register_class(cls)
    bpy.types.Scene.harta_cladire = bpy.props.PointerProperty(type=CladireSettings)


if __name__ == "__main__":
    register()
