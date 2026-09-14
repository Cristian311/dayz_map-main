# -*- coding: utf-8 -*-
"""
De unde ia catalogul numele de modele pe care sa le masoare in joc.

Problema: numele arhetipurilor de harta din GTA V nu se pot enumera cu nicio functie de
joc. Soluitia practica, in ordinea calitatii:

1. `tools/import_ytyp_xml.py` pe un export CodeWalker al .ytyp-urilor -> nume EXACTE
   plus cutiile, fara sa fie nevoie de scanare in joc. Cel mai bun, dar cere CodeWalker.
2. Un fisier text cu nume de modele (ex. ObjectList.ini de la Menyoo, orice lista de
   obiecte GTA V) pus in `dayzgen/data/namelists/*.txt` - o linie per nume.
3. Generarea combinatorica de mai jos, validata in joc cu `IsModelInCdimage`.
   Numele de harta ale Rockstar respecta in mare `<zona>_<NN>_<ceva>`, deci un spatiu de
   cateva sute de mii de combinatii prinde o parte buna din cladiri. Ce nu exista e
   aruncat de joc instant, deci ghicitul nu costa decat cateva secunde de scanare.

Modulul scrie o *specificatie compacta* (prefixe / numere / sufixe), nu lista desfasurata:
clientul o desfasoara singur, ca sa nu trimitem megabytes catre joc.
"""
from __future__ import annotations

import glob
import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
NAMELIST_DIR = os.path.join(DATA_DIR, "namelists")

# Prefixele de zona folosite de Rockstar in numele modelelor de harta.
# hei_/mp_ sunt variantele din DLC-uri (Heists, After Hours...).
ZONE_PREFIXES = (
    "dt1", "dt2",                                     # downtown Los Santos
    "bh1", "bh2", "bh3", "bh4",                       # Vinewood / Rockford Hills
    "kt1", "hw1", "sm",                               # Korean town, Hawick, Strawberry
    "id1", "id2", "ind1",                             # industrial / docuri
    "vb", "vbca", "bay",                              # Vespucci beach
    "mw", "lr", "sc1", "ch1", "ch2", "ch3",           # suburbii / Chumash / Senora
    "cs1", "cs2", "cs3", "cs4", "cs5", "cs6", "cs7", "cs8",   # countryside
    "ss1", "po1", "gr", "ap1",                        # Sandy Shores, Paleto, Grapeseed, aeroport
    "hei_dt1", "hei_bh1", "hei_sm", "hei_kt1",        # variante Heists
    "mp_apa", "apa", "xm_", "sf_",                    # DLC-uri
)

# Sufixele descriptive. Cele generice (bld1..) prind cele mai multe cladiri; cuvintele
# sunt cele care apar des in numele Rockstar.
SUFFIX_WORDS = (
    "bld", "bld1", "bld2", "bld3", "bld4", "bld5", "bld6", "bld7", "bld8", "bld9",
    "bld_a", "bld_b", "bld_c", "bld_d", "bld_e", "bld_f",
    "bldg", "bldg1", "bldg2", "bldg3", "bldg4",
    "build", "build1", "build2", "build3", "build4", "build5", "build6",
    "building", "building1", "building2", "building3", "building4",
    "house", "house1", "house2", "house3", "house4", "house5", "house6",
    "hse", "hse1", "hse2", "hse3",
    "shop", "shop1", "shop2", "shop3", "shop4", "shops", "store", "store1", "store2",
    "office", "office1", "office2", "office3", "offices",
    "apart", "apart1", "apart2", "apart3", "apartment", "apts",
    "tower", "tower1", "tower2", "hotel", "motel", "motel1",
    "warehouse", "warehouse1", "warehouse2", "wareh", "hangar", "hangar1",
    "factory", "factory1", "depot", "storage", "silo", "silo1",
    "garage", "garage1", "garage2", "carpark", "carpark1", "parking",
    "mall", "market", "market1", "diner", "bar", "bank", "church", "school",
    "station", "station1", "gas", "gasstation", "petrol",
    "block", "block1", "block2", "block3", "tenement", "tenement1",
    "front", "facade", "facade1", "fasade", "wall", "wall1", "wall2",
    "roof", "roof1", "details", "detail", "props", "prop", "extra", "extras",
    "main", "main1", "core", "base", "shell", "sides", "side", "back", "backs",
    "a", "b", "c", "d", "e", "f", "01", "02", "03", "04", "05",
)

# "Numarul de bloc" folosit intre zona si descriere.
BLOCK_NUMBERS = tuple(f"{i:02d}" for i in range(1, 50))

# Prop-uri de mobilier urban - astea le stiu sigur ca exista si sunt necesare oricum in
# faza de mobilier. Se masoara la fel ca restul (garduri/stalpi au nevoie de lungime exacta).
URBAN_PROPS = (
    # iluminat si semnalizare
    "prop_streetlight_01", "prop_streetlight_01b", "prop_streetlight_02",
    "prop_streetlight_03", "prop_streetlight_03b", "prop_streetlight_03c",
    "prop_streetlight_04", "prop_streetlight_05", "prop_streetlight_07a",
    "prop_streetlight_08", "prop_streetlight_09", "prop_streetlight_10",
    "prop_streetlight_11a", "prop_streetlight_12a",
    "prop_traffic_01a", "prop_traffic_01b", "prop_traffic_01d",
    "prop_traffic_02a", "prop_traffic_02b", "prop_traffic_03a", "prop_traffic_03b",
    "prop_traffic_lightset_01",
    "prop_sign_road_01a", "prop_sign_road_02a", "prop_sign_road_03a",
    "prop_sign_road_05a", "prop_sign_road_06a", "prop_sign_road_restriction_02",
    # trotuar
    "prop_bench_01a", "prop_bench_01b", "prop_bench_01c", "prop_bench_02",
    "prop_bench_03", "prop_bench_04", "prop_bench_05", "prop_bench_06",
    "prop_bin_01a", "prop_bin_02a", "prop_bin_03a", "prop_bin_04a", "prop_bin_05a",
    "prop_bin_06a", "prop_bin_07a", "prop_bin_07b", "prop_bin_07c", "prop_bin_08a",
    "prop_bin_08open", "prop_bin_09a", "prop_bin_10a", "prop_bin_10b", "prop_bin_11a",
    "prop_bin_12a", "prop_bin_13a", "prop_bin_14a", "prop_bin_14b",
    "prop_fireydrant_1a", "prop_fireydrant_1b", "prop_fireydrant_1c",
    "prop_fireydrant_2a", "prop_fireydrant_3a", "prop_fireydrant_3b",
    "prop_parknmeter_01", "prop_parknmeter_02",
    "prop_phonebox_01a", "prop_phonebox_02", "prop_phonebox_03", "prop_phonebox_04",
    "prop_postbox_01a", "prop_news_disp_02a", "prop_news_disp_02b",
    "prop_news_disp_03a", "prop_news_disp_05a", "prop_news_disp_06a",
    "prop_busstop_02", "prop_busstop_04", "prop_busstop_05",
    "prop_bus_stop_sign", "prop_bollard_01a", "prop_bollard_02a",
    "prop_consign_01a", "prop_consign_02a", "prop_consign_03a",
    "prop_cablespool_01", "prop_elecbox_01a", "prop_elecbox_02a", "prop_elecbox_03a",
    "prop_elecbox_05a", "prop_elecbox_06", "prop_elecbox_09", "prop_elecbox_11a",
    "prop_elecbox_12a", "prop_elecbox_13a", "prop_elecbox_14",
    "prop_air_conditioner_01", "prop_air_conditioner_02", "prop_air_conditioner_03",
    "prop_air_conditioner_04", "prop_air_conditioner_05", "prop_air_conditioner_06",
    "prop_dumpster_01a", "prop_dumpster_02a", "prop_dumpster_02b",
    "prop_dumpster_3a", "prop_dumpster_4a", "prop_dumpster_4b",
    "prop_skip_01a", "prop_skip_02a", "prop_skip_03", "prop_skip_04a", "prop_skip_05a",
    "prop_pallet_01a", "prop_pallet_02a", "prop_boxpile_01a", "prop_boxpile_02a",
    "prop_crate_02a", "prop_crate_03a", "prop_container_01a", "prop_container_01b",
    "prop_container_02a", "prop_container_03a", "prop_container_05a",
    # garduri urbane
    "prop_fnclink_01a", "prop_fnclink_01b", "prop_fnclink_01c", "prop_fnclink_01d",
    "prop_fnclink_02a", "prop_fnclink_02b", "prop_fnclink_02c", "prop_fnclink_02d",
    "prop_fnclink_03a", "prop_fnclink_03b", "prop_fnclink_03c", "prop_fnclink_03d",
    "prop_fnclink_03e", "prop_fnclink_03f", "prop_fnclink_03g", "prop_fnclink_03h",
    "prop_fnclink_04a", "prop_fnclink_04b", "prop_fnclink_04c", "prop_fnclink_04d",
    "prop_fnclink_05a", "prop_fnclink_05b", "prop_fnclink_05crnr1",
    "prop_fnclink_05crnr2", "prop_fnclink_05gate1", "prop_fnclink_05gate2",
    "prop_fncconc_01a", "prop_fncconc_02a", "prop_fncconc_03a", "prop_fncconc_04a",
    "prop_fncconc_05a", "prop_fncwood_01a", "prop_fncwood_02a", "prop_fncwood_03a",
    "prop_fncwood_04a", "prop_fncwood_05a", "prop_fncwood_06a", "prop_fncwood_08a",
    "prop_fncwood_09a", "prop_fncwood_13a", "prop_fncwood_14a",
    "prop_fnc_railing_01a", "prop_fnc_railing_02a",
    "prop_barrier_work05", "prop_barrier_work06a", "prop_mp_barrier_01",
    "prop_mp_barrier_02b",
    # vegetatie de aliniament
    "prop_tree_birch_01", "prop_tree_birch_02", "prop_tree_birch_03",
    "prop_tree_birch_04", "prop_tree_cedar_02", "prop_tree_cedar_03",
    "prop_tree_cedar_04", "prop_tree_cedar_s_01", "prop_tree_cedar_s_02",
    "prop_tree_cypress_01", "prop_tree_eng_oak_01", "prop_tree_eucalip_01",
    "prop_tree_fallen_pine_01", "prop_tree_jacada_01", "prop_tree_jacada_02",
    "prop_tree_lficus_02", "prop_tree_lficus_03", "prop_tree_lficus_05",
    "prop_tree_lficus_06", "prop_tree_maple_02", "prop_tree_maple_03",
    "prop_tree_mquite_01", "prop_tree_oak_01", "prop_tree_olive_01",
    "prop_tree_pine_01", "prop_tree_pine_02", "prop_palm_fan_02_b",
    "prop_palm_fan_03_c", "prop_palm_fan_04_b", "prop_palm_huge_01a",
    "prop_palm_med_01a", "prop_palm_sm_01a", "prop_palm_sm_01d",
    "prop_bush_lrg_01a", "prop_bush_lrg_02", "prop_bush_lrg_04b",
    "prop_bush_med_01", "prop_bush_med_03", "prop_bush_med_05",
    "prop_plant_01a", "prop_plant_fern_02a", "prop_flowerpot_01",
    "prop_flowerpot_03", "prop_flowerpot_04", "prop_plantpot_01",
    # parcare / marcaje
    "prop_roadcone02a", "prop_roadcone01a", "prop_ped_crossing_sign",
    "prop_mp_cone_01", "prop_wall_light_10a", "prop_wall_light_12a",
)


def expand(prefixes=None, numbers=None, suffixes=None) -> list:
    """Lista desfasurata de candidati (folosita doar de importatoare/teste, nu de client)."""
    prefixes = tuple(prefixes or ZONE_PREFIXES)
    numbers = tuple(numbers or BLOCK_NUMBERS)
    suffixes = tuple(suffixes or SUFFIX_WORDS)
    out = []
    for prefix in prefixes:
        base = prefix if prefix.endswith("_") else prefix + "_"
        for suffix in suffixes:
            out.append(base + suffix)
            for number in numbers:
                out.append(f"{base}{number}_{suffix}")
    return out


def load_namelists(directory: str | None = None) -> list:
    """Nume citite din `dayzgen/data/namelists/*.txt` (o linie per nume; `#` = comentariu)."""
    target = directory or NAMELIST_DIR
    if not os.path.isdir(target):
        return []
    out = []
    for path in sorted(glob.glob(os.path.join(target, "*.txt"))
                       + glob.glob(os.path.join(target, "*.ini"))):
        with open(path, "r", encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                line = line.strip()
                if not line or line.startswith(("#", ";", "[")):
                    continue
                # ObjectList.ini de la Menyoo are si coloane extra separate de virgula/tab
                name = line.split(",")[0].split("\t")[0].strip().lower()
                if 2 <= len(name) <= 64 and all(
                        c.isalnum() or c == "_" for c in name):
                    out.append(name)
    seen = set()
    unique = []
    for name in out:
        if name not in seen:
            seen.add(name)
            unique.append(name)
    return unique


def build_spec(extra_literal=()) -> dict:
    """
    Specificatia compacta trimisa scanerului din joc.

    `literal` = nume exacte (prop-uri + orice lista de nume gasita pe disc).
    `patterns` = combinatoriile pe care clientul le desfasoara singur.
    """
    # Cladirile importate din fisierele jocului au deja cutia exacta: scanerul doar confirma
    # ca se incarca oriunde pe harta (`verify`), fara sa le mai incarce si masoare.
    verify = []
    try:
        from .catalog import Catalog
        verify = sorted(a.name for a in Catalog.load().items.values() if not a.verified and not a.blocked)
    except Exception:
        verify = []
    literal = (list(URBAN_PROPS) + load_namelists()
               + [str(n).strip().lower() for n in extra_literal])
    seen = set(verify)
    unique = []
    for name in literal:
        if name and name not in seen:
            seen.add(name)
            unique.append(name)

    combos = len(ZONE_PREFIXES) * len(SUFFIX_WORDS) * (1 + len(BLOCK_NUMBERS))
    return {
        "version": 2,
        "verify": verify,
        "literal": unique,
        "patterns": {
            "prefixes": list(ZONE_PREFIXES),
            "numbers": list(BLOCK_NUMBERS),
            "suffixes": list(SUFFIX_WORDS),
        },
        "estimate": combos + len(unique) + len(verify),
        "note": ("Clientul desfasoara <prefix>_<suffix> si <prefix>_<NN>_<suffix>, "
                 "verifica fiecare nume cu IsModelInCdimage si masoara doar ce exista."),
    }


def write_spec(path: str | None = None, extra_literal=()) -> str:
    target = path or os.path.join(DATA_DIR, "candidates.json")
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8") as handle:
        json.dump(build_spec(extra_literal), handle, indent=1, ensure_ascii=False)
    return target
