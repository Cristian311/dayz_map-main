# -*- coding: utf-8 -*-
"""
Configuratie / presets pentru generatorul de harta DayZ -> GTA V.
Toate distantele sunt in metri. Coordonatele locale ale hartii pornesc de la (0,0) in coltul SV;
la export se aduna ORIGIN (pozitia in lumea GTA V).
"""
import json
from dataclasses import dataclass, field, fields as _dc_fields


@dataclass
class MapConfig:
    # --- identitate ---
    preset: str = "demo"           # preset-ul de la care s-a pornit (doar informativ / pentru map.json)
    name: str = "dzmap"            # prefix pentru toate fisierele/arhetipurile (litere mici, fara spatii)
    seed: int = 1337

    # --- dimensiuni ---
    size: float = 1024.0           # latura hartii (m); trebuie multiplu de tile_size
    cell: float = 4.0              # distanta intre vertecsi in LOD-ul high (m)
    tile_size: float = 256.0       # latura unui tile de teren (= o entitate / un .ydr)
    max_height: float = 110.0      # inaltimea maxima aproximativa a terenului (m)
    sea_depth: float = 10.0        # cat de jos coboara fundul marii (m)

    # --- pozitia in lumea GTA V (coltul SV al hartii) ---
    origin_x: float = 7000.0
    origin_y: float = -8000.0

    # --- sate / drumuri / campuri ---
    num_villages: int = 2
    village_radius: tuple = (70.0, 110.0)
    houses_per_village: tuple = (5, 9)
    road_half_width: float = 3.2
    fields_per_village: tuple = (1, 2)

    # --- vegetatie (densitati: 1 obiect la N m^2) ---
    forest_coverage: float = 0.42          # fractiunea aproximativa de padure
    tree_spacing: float = 6.0              # distanta medie intre copaci in padure (m)
    lone_tree_area: float = 1400.0
    bush_edge_area: float = 160.0
    bush_open_area: float = 2600.0
    rock_slope_area: float = 320.0
    rock_open_area: float = 3500.0
    forest_debris_area: float = 1600.0     # busteni cazuti / cioturi in padure

    # --- distante de LOD (entitati) ---
    lod_dist_terrain: float = 700.0
    lod_dist_tree: float = 230.0
    lod_dist_bush: float = 120.0
    lod_dist_rock: float = 150.0
    lod_dist_building: float = 350.0
    lod_dist_small_prop: float = 90.0

    # --- texturi ---
    terrain_tex_size: int = 1024
    building_tex_size: int = 512
    terrain_uv_scale: float = 6.0          # o textura de teren se repeta la fiecare N metri

    # --- export ---
    chunk_size: float = 256.0              # latura unui .ymap (chunk de entitati)
    export_gen9: bool = False              # true = exporta si varianta GTA V Enhanced (gen9)
    package_ragemp: bool = False           # true = construieste si dlc.rpf (RAGE:MP); implicit doar FiveM
    keep_scene: bool = True                # pastreaza obiectele in scena (.blend) dupa export
    write_preview_png: bool = True         # scrie si PNG-uri ale texturilor pentru vizualizare
    minimap_px: int = 1024                 # latura imaginii puse pe radar / harta mare (overlay .gfx), max 4096

    # --- cai (folosite de studio / exportul de obiecte manuale) ---
    fivem_resources_dir: str = r"C:\FXServer\server-data\resources\[rrp]"
    custom_objects_file: str = "editor/objects.json"   # relativ la folderul resursei instalate

    def validate(self):
        assert self.size % self.tile_size == 0, "size trebuie sa fie multiplu de tile_size"
        assert self.tile_size % self.cell == 0, "tile_size trebuie sa fie multiplu de cell"
        assert self.chunk_size % self.tile_size == 0 or self.tile_size % self.chunk_size == 0
        assert self.size > 0 and self.cell > 0 and self.tile_size > 0, "dimensiuni pozitive obligatorii"
        assert self.name and self.name == self.name.lower() and " " not in self.name, \
            "name trebuie sa fie litere mici, fara spatii"
        assert self.num_villages >= 0, "num_villages nu poate fi negativ"
        assert self.max_height > 0, "max_height trebuie sa fie pozitiv"

    # ------------------------------------------------------------------ map.json
    def to_dict(self) -> dict:
        out = {}
        for f in _dc_fields(self):
            v = getattr(self, f.name)
            out[f.name] = list(v) if isinstance(v, tuple) else v
        return out

    def to_json(self, path) -> str:
        """Scrie configuratia in <path> (JSON, cheile = numele campurilor)."""
        text = json.dumps(self.to_dict(), indent=2, ensure_ascii=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        return str(path)

    @staticmethod
    def field_names() -> list:
        return [f.name for f in _dc_fields(MapConfig)]

    @classmethod
    def from_dict(cls, data: dict) -> "MapConfig":
        """Porneste de la preset-ul indicat de cheia 'preset' si aplica peste el restul cheilor."""
        import copy as _copy
        if not isinstance(data, dict):
            raise ValueError("map.json trebuie sa contina un obiect JSON")
        preset = data.get("preset", "demo")
        if preset not in PRESETS:
            raise ValueError(f"preset necunoscut: {preset!r} (valori valide: {', '.join(sorted(PRESETS))})")
        cfg = _copy.deepcopy(PRESETS[preset])
        cfg.preset = preset
        known = {f.name for f in _dc_fields(cls)}
        unknown = [k for k in data if k not in known]
        if unknown:
            raise ValueError("chei necunoscute in map.json: " + ", ".join(sorted(unknown)) +
                             "\nchei valide: " + ", ".join(cls.field_names()))
        for k, v in data.items():
            if k == "preset":
                continue
            cur = getattr(cfg, k)
            try:
                if isinstance(cur, tuple):
                    v = tuple(v)
                elif isinstance(cur, bool):
                    v = bool(v)
                elif isinstance(cur, int):
                    v = int(v)
                elif isinstance(cur, float):
                    v = float(v)
                elif isinstance(cur, str):
                    v = str(v)
            except (TypeError, ValueError):
                raise ValueError(f"valoare invalida pentru cheia '{k}': {v!r}")
            setattr(cfg, k, v)
        return cfg

    @classmethod
    def from_json(cls, path) -> "MapConfig":
        try:
            with open(path, "r", encoding="utf-8-sig") as fh:
                data = json.load(fh)
        except FileNotFoundError:
            raise ValueError(f"fisierul de configurare nu exista: {path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON invalid in {path}: {e}")
        return cls.from_dict(data)


PRESETS = {
    # rapid: o bucata de 1 km x 1 km cu 2 sate, paduri si drum -> de testat in joc
    "demo": MapConfig(preset="demo", name="dzdemo", size=1024.0, num_villages=2,
                      houses_per_village=(7, 11), seed=1337),
    # complet: 4 km x 4 km, 10 sate (ruleaza mai mult, ~10-20 min)
    "full": MapConfig(preset="full", name="dzmap", size=4096.0, num_villages=10, houses_per_village=(6, 14),
                      max_height=220.0, seed=2024, keep_scene=False),
    # mic, pentru teste foarte rapide de pipeline
    "tiny": MapConfig(preset="tiny", name="dztiny", size=512.0, num_villages=1, houses_per_village=(3, 5), seed=7,
                      max_height=60.0, terrain_tex_size=512, building_tex_size=256),
}


# ---------------------------------------------------------------------------
# Props vanilla GTA V (verificate in lista oficiala de obiecte). Toate au LOD-uri si coliziuni
# proprii, deci nu costa nimic in plus fata de un model custom.
# ---------------------------------------------------------------------------
TREES_CONIFER = [
    "prop_tree_pine_01", "prop_tree_pine_02",
    "prop_tree_cedar_02", "prop_tree_cedar_03", "prop_tree_cedar_04",
    "prop_tree_cedar_s_01", "prop_tree_cedar_s_02", "prop_tree_cedar_s_04",
    "prop_tree_cedar_s_05", "prop_tree_cedar_s_06",
]
TREES_BIRCH = ["prop_tree_birch_01", "prop_tree_birch_02", "prop_tree_birch_03",
               "prop_tree_birch_03b", "prop_tree_birch_04", "prop_tree_birch_05"]
TREES_BROADLEAF = ["prop_tree_oak_01", "prop_tree_eng_oak_01", "prop_tree_maple_02", "prop_tree_maple_03"]
TREES_DEBRIS = ["prop_tree_fallen_pine_01", "prop_tree_fallen_02", "prop_tree_stump_01",
                "prop_tree_log_01", "prop_tree_log_02", "prop_log_01", "prop_log_02", "prop_log_03"]
BUSHES = ["prop_bush_lrg_01", "prop_bush_lrg_02", "prop_bush_lrg_02b", "prop_bush_lrg_03",
          "prop_bush_lrg_04b", "prop_bush_lrg_04c", "prop_bush_lrg_04d",
          "prop_bush_med_01", "prop_bush_med_02", "prop_bush_med_03", "prop_bush_med_05",
          "prop_bush_med_06", "prop_bush_med_07", "prop_bush_dead_02"]
ROCKS_BIG = ["prop_rock_1_a", "prop_rock_1_b", "prop_rock_1_c", "prop_rock_1_d", "prop_rock_1_e",
             "prop_rock_1_f", "prop_rock_1_g", "prop_rock_1_h", "prop_rock_1_i",
             "prop_rock_4_a", "prop_rock_4_b", "prop_rock_4_c", "prop_rock_4_d", "prop_rock_4_e",
             "prop_rock_4_big", "prop_rock_4_big2", "prop_rock_4_cl_1", "prop_rock_4_cl_2"]
ROCKS_SMALL = ["prop_rock_3_a", "prop_rock_3_b", "prop_rock_3_c", "prop_rock_3_d", "prop_rock_3_e",
               "prop_rock_3_f", "prop_rock_3_g", "prop_rock_3_h", "prop_rock_3_i", "prop_rock_3_j",
               "prop_rock_5_a", "prop_rock_5_b", "prop_rock_5_c", "prop_rock_5_d", "prop_rock_5_e",
               "prop_rock_2_a", "prop_rock_2_c", "prop_rock_2_d", "prop_rock_2_f", "prop_rock_2_g"]
VILLAGE_LANDMARKS = ["prop_rural_windmill", "prop_watertower01", "prop_windmill_01", "prop_watertower02"]
FARM_PROPS = ["prop_haybale_01", "prop_haybale_02", "prop_haybale_03", "prop_haybale_stack_01"]
YARD_PROPS = ["prop_woodpile_01a", "prop_woodpile_01b", "prop_woodpile_02a", "prop_woodpile_03a",
              "prop_woodpile_04a", "prop_wooden_barrel", "prop_barrel_01a", "prop_barrel_02a",
              "prop_barrel_03a", "prop_boxpile_07d", "prop_bench_01a", "prop_wheelbarrow01a",
              "prop_rub_tyre_01", "prop_rub_tyre_02", "prop_bin_01a"]
WRECKS = ["prop_rub_carwreck_2", "prop_rub_carwreck_3", "prop_rub_carwreck_5", "prop_rub_carwreck_7",
          "prop_rub_carwreck_8", "prop_rub_carwreck_9", "prop_rub_carwreck_10", "prop_rub_carwreck_12",
          "prop_rub_carwreck_13", "prop_rub_carwreck_14", "prop_rub_carwreck_15", "prop_rub_carwreck_16"]

# Arhetipuri custom (generate de noi) -> numele finale sunt f"{cfg.name}_{key}"
BUILDING_KEYS = ["house_a", "house_b", "barn", "shed"]
