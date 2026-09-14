# -*- coding: utf-8 -*-
"""
Organizeaza biblioteca de modele GTA V din Asset Browser pe categorii pe intelesul omului
(Case, Blocuri, Turnuri, Magazine, Hale, Garaje, Garduri, Vegetatie, Mobilier stradal...), in loc de
numele fisierelor din joc (indust_01_metadata_008_strm).

Pentru fiecare .blend din biblioteca: pune fiecare model in catalogul categoriei lui (din
dayzgen/data/catalog.json si din numele modelului), ii scrie etichete (marime, stil, "intreaga") si o
descriere cu dimensiunile. Bucatile de cladire (nemasurate ca intregi) merg in "Bucati (avansat)", ca
lista principala sa fie curata. Fisierele deja organizate nu se mai deschid (_organizate.json).

Ruleaza automat la finalul lui blender_build_library.py; separat:
    tools\\_blender.bat -b -P tools\\blender_library_catalogs.py -- [--lib <folder>] [--force]
"""
import json
import re
import sys
import time
import uuid
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from dayzgen.city.catalog import PROP_PREFIXES, classify, guess_style  # noqa: E402

LIB_DEFAULT = ROOT / "output" / "gta_asset_library"
TOP = "GTA V"
STATE_FILE = "_organizate.json"     # fisierele organizate + cataloagele folosite
CATS = {
    "house": "Case",
    "lowrise": "Cladiri mici (2-4 etaje)",
    "midrise": "Blocuri",
    "tower": "Turnuri",
    "shop": "Magazine si benzinarii",
    "warehouse": "Hale si depozite",
    "garage": "Garaje si anexe",
    "filler": "Ziduri si umplutura",
    "unknown": "Diverse",
}
PIECES = "Bucati (avansat)"
# categoriile de props, dupa cuvinte din nume (prima potrivire castiga)
PROP_CATS = (
    ("Garduri si porti", ("fnc", "fence", "gate", "railing", "barrier", "bollard", "wall_")),
    ("Vegetatie", ("tree", "palm", "bush", "plant", "cactus", "cacti", "hedge", "flower", "veg_", "grass", "log_",
                   "shrub", "fern", "ivy", "weed", "pot_plant", "potted")),
    ("Stalpi si semne", ("streetlight", "lamppost", "lamp_post", "sign", "traffic", "tl_", "billboard", "pole",
                         "postbox", "parking_meter", "parkingmeter", "elecbox", "electric", "telegraph", "cctv")),
    ("Mobilier stradal", ("bench", "bin", "dumpster", "hydrant", "bus_stop", "busstop", "table", "chair", "seat",
                          "picnic", "vend", "atm", "phonebox", "newsstand", "kiosk", "umbrella", "planter",
                          "bike_rack", "bikerack", "rubbish", "litter", "cone", "skip", "trolley")),
    ("Pietre si stanci", ("rock", "stone", "boulder", "cliff")),
    ("Santier si industrial", ("construction", "scaffold", "crane", "container", "pallet", "crate", "barrel",
                               "drum", "pipe", "tank", "generator", "forklift", "conveyor", "girder", "cement",
                               "sack", "tyre", "tire", "toolbox", "cable", "reel")),
    ("Interior si mobila", ("sofa", "couch", "bed", "desk", "shelf", "cabinet", "fridge", "cooker", "oven",
                            "toilet", "sink", "bath", "tv_", "lamp", "counter", "stool", "wardrobe", "rug",
                            "mattress", "curtain", "kitchen", "office", "bar_")),
    ("Vehicule si diverse", ("car", "boat", "trailer", "wreck", "plane", "heli")),
)
SIZE_TAGS = ((6.0, "mic"), (25.0, "mediu"), (float("inf"), "mare"))
STYLE_RO = {"downtown": "centru", "vinewood": "vinewood", "suburb": "suburbie", "industrial": "industrial",
            "beach": "plaja", "country": "rural"}


def cli_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    lib = LIB_DEFAULT
    if "--lib" in argv and argv.index("--lib") + 1 < len(argv):
        lib = Path(argv[argv.index("--lib") + 1]).resolve()
    return lib, "--force" in argv


def load_catalog() -> dict:
    """{nume model: intrare} din catalogul generatorului (categorie, cutie, etichete)."""
    path = ROOT / "dayzgen" / "data" / "catalog.json"
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {a["name"].lower(): a for a in data.get("archetypes") or () if a.get("name")}


class Cats:
    """blender_assets.cats.txt (uuid:cale) + starea din _organizate.json. Uuid-ul unei categorii se
    calculeaza din cale, deci e mereu acelasi: daca Sollumz rescrie .cats.txt cand construieste
    biblioteca, rularea urmatoare pune la loc exact aceleasi cataloage."""

    def __init__(self, lib: Path):
        self.path = lib / "blender_assets.cats.txt"
        self.state_path = lib / STATE_FILE
        self.by_path = {}
        if self.path.is_file():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and not line.startswith("VERSION"):
                    uid, cpath, _ = line.split(":", 2)
                    self.by_path[cpath] = uid
        state = {}
        if self.state_path.is_file():
            try:
                state = json.loads(self.state_path.read_text(encoding="utf-8"))
            except ValueError:
                state = {}
        self.done = set(state.get("files") or ())
        self.used = set()
        for cpath in state.get("catalogs") or ():
            self.get(*cpath.split("/"))

    @staticmethod
    def uid(cpath: str) -> str:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, "gta-v-generator/" + cpath))

    def get(self, *parts) -> str:
        for i in range(1, len(parts) + 1):
            cpath = "/".join(parts[:i])
            self.by_path[cpath] = self.uid(cpath)
            self.used.add(cpath)
        return self.by_path["/".join(parts)]

    def save(self, keep_old: bool):
        lines = ["VERSION 1", ""]
        for cpath in sorted(self.by_path):
            if not keep_old and cpath not in self.used:
                continue      # cataloagele Sollumz pe fisiere .ytyp dispar cand toate fisierele sunt organizate
            lines.append(f"{self.by_path[cpath]}:{cpath}:{cpath.replace('/', '-')}")
        self.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        state = {"files": sorted(self.done), "catalogs": sorted(self.used)}
        self.state_path.write_text(json.dumps(state, indent=1), encoding="utf-8")


def prop_category(name: str) -> str:
    for label, needles in PROP_CATS:
        if any(n in name for n in needles):
            return label
    return "Diverse props"


def describe(obj, entry: dict | None):
    """(cale de catalog sub radacina, etichete, descriere) pentru un model din biblioteca."""
    name = obj.name.lower()
    sx, sy, sz = (float(d) for d in obj.dimensions)
    tags = list((entry or {}).get("tags") or [])
    if entry:
        category = entry.get("cat") or "unknown"
        style = entry.get("style") or "any"
        lo, hi = entry.get("min"), entry.get("max")
        if lo and hi:
            sx, sy, sz = (float(hi[i]) - float(lo[i]) for i in range(3))
    else:
        category = classify(name, sx, sy, sz)
        style = guess_style(name)
    if category == "prop" or name.startswith(PROP_PREFIXES):
        path = ("Props", prop_category(name))
    elif re.search(r"_s?lod\d*$", name) or "_lod_" in name:
        path = (PIECES, "LOD-uri")
    elif category in ("filler", "unknown") or "solid" not in tags:
        # nemasurata ca intreaga: cel mai probabil o bucata (acoperis, fatada, detaliu)
        path = (PIECES, CATS.get(category, CATS["unknown"]))
    else:
        path = (CATS.get(category, CATS["unknown"]),)
    big = max(sx, sy, sz)
    out_tags = [next(t for limit, t in SIZE_TAGS if big < limit)]
    if style in STYLE_RO:
        out_tags.append(STYLE_RO[style])
    if "solid" in tags:
        out_tags.append("intreaga")
    if "haslod" in tags:
        out_tags.append("are_lod")
    desc = f"{sx:.0f} x {sy:.0f} m, {sz:.0f} m inaltime"
    ytyp = next((t[5:] for t in tags if t.startswith("ytyp:")), None)
    if ytyp:
        desc += f" | {ytyp}"
    return path, out_tags, desc


def organize_file(path: Path, cats: Cats, catalog: dict) -> dict:
    bpy.ops.wm.open_mainfile(filepath=str(path), load_ui=False)
    counts = {}
    for obj in bpy.data.objects:
        ad = obj.asset_data
        if ad is None:
            continue
        parts, tags, desc = describe(obj, catalog.get(obj.name.lower()))
        ad.catalog_id = cats.get(TOP, *parts)
        ad.description = desc
        for tag in list(ad.tags):
            ad.tags.remove(tag)
        for tag in tags:
            ad.tags.new(tag, skip_if_exists=True)
        key = "/".join(parts)
        counts[key] = counts.get(key, 0) + 1
    bpy.ops.wm.save_mainfile(filepath=str(path))
    return counts


def organize(lib: Path, force: bool = False, log=print) -> int:
    files = sorted(lib.glob("_assets.*.blend"))
    if not files:
        log(f"biblioteca {lib} nu are fisiere .blend")
        return 0
    cats = Cats(lib)
    todo = [f for f in files if force or f.name not in cats.done]
    if not todo:
        cats.save(keep_old=False)     # pune la loc cataloagele, daca Sollumz a rescris fisierul
        log("toate fisierele bibliotecii sunt deja organizate pe categorii")
        return 0
    catalog = load_catalog()
    log(f"organizez {len(todo)} fisiere din biblioteca pe categorii ({len(catalog)} modele in catalog)")
    started = time.time()
    total = {}
    for n, path in enumerate(todo, 1):
        counts = organize_file(path, cats, catalog)
        for k, v in counts.items():
            total[k] = total.get(k, 0) + v
        cats.done.add(path.name)
        cats.save(keep_old=any(f.name not in cats.done for f in files))
        log(f"  {n}/{len(todo)} {path.name}: {sum(counts.values())} modele ({time.time() - started:.0f} s)")
    log("modele pe categorii:")
    for key, count in sorted(total.items(), key=lambda kv: -kv[1]):
        log(f"  {count:6d}  {key}")
    return len(todo)


if __name__ == "__main__":
    lib_dir, force_all = cli_args()
    organize(lib_dir, force_all)
