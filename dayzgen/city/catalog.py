# -*- coding: utf-8 -*-
"""
Catalog de arhetipuri GTA V vanilla folosite ca cladiri de oras.

De ce: cladirile bune nu se pot genera procedural la calitatea GTA V. Ce se poate face
e sa folosim modelele care exista deja in joc (au LOD-uri, coliziuni, texturi de artist)
si sa le asezam corect pe loturi. Modulul asta tine "fisa tehnica" a fiecarui model:
cat de mare e amprenta, cat e inalt, cat coboara sub 0, ce categorie/stil are.

Cutiile (bbox) NU se pot ghici din numele modelului - se masoara in joc cu
`GetModelDimensions` (vezi resursa mapeditor, comanda /catalogscan) sau se importa
din XML-urile de .ytyp exportate cu CodeWalker (tools/import_ytyp_xml.py).

Fisierul rezultat: dayzgen/data/catalog.json
"""
from __future__ import annotations

import json
import math
import os
import random
from dataclasses import dataclass, field

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
CATALOG_PATH = os.path.join(DATA_DIR, "catalog.json")
CANDIDATES_PATH = os.path.join(DATA_DIR, "candidates.json")

# Categoriile pe care le foloseste plasatorul. Ordinea conteaza pentru auto-clasificare
# (prima care se potriveste castiga).
CATEGORIES = (
    "tower",       # zgarie-nori / bloc inalt (> 40 m)
    "midrise",     # bloc 15-40 m
    "lowrise",     # 2-4 etaje cu parter comercial
    "shop",        # magazin / benzinarie / fast-food, o singura cota
    "house",       # casa individuala de suburbie
    "warehouse",   # hala / depozit industrial
    "garage",      # garaj / anexa mica
    "filler",      # zid, gard de cvartal, bucata de fatada, orice umplutura
    "prop",        # mobilier urban / vegetatie (`prop_*`) - nu e cladire, dar are nevoie de cote
    "unknown",
)

# Prefixele modelelor care nu sunt niciodata cladiri, oricat de mari ar fi cutia lor.
PROP_PREFIXES = ("prop_", "p_", "v_", "ba_prop_", "xm_prop_", "sf_prop_", "h4_prop_",
                 "ch_prop_", "vw_prop_", "xs_prop_", "sm_prop_", "gr_prop_", "bkr_prop_",
                 "imp_prop_", "tr_prop_", "apa_prop_", "hei_prop_", "ex_prop_", "w_")

STYLES = ("downtown", "vinewood", "suburb", "industrial", "beach", "country", "any")

# Cuvinte din numele modelului care tradeaza categoria. Se aplica INAINTE de reguli pe
# dimensiuni, pentru ca numele e mai de incredere decat cutia (o hala si un bloc turtit
# au aceeasi cutie).
NAME_HINTS = (
    ("warehouse", ("wareh", "hangar", "factory", "_fact", "depot", "silo", "storage")),
    ("garage", ("garage", "carport", "shed", "_anex", "outhouse")),
    ("shop", ("shop", "store", "market", "_gas", "petrol", "diner", "burger", "liquor",
              "pharm", "barber", "laundr", "kiosk", "cafe", "restaur")),
    ("house", ("house", "_res_", "bungalow", "villa", "cottage", "trailer", "_hut")),
    ("tower", ("tower", "skysc", "_hitower")),
    ("midrise", ("apart", "office", "_offi", "hotel", "motel", "tenem", "block")),
    ("filler", ("wall", "fence", "_fnc", "facade", "_fasad", "billb", "roofdet", "_awn")),
)

# Stilul se ghiceste din prefixul de zona folosit de Rockstar in numele modelelor de harta.
STYLE_PREFIXES = (
    ("downtown", ("dt1_", "dt2_", "kt1_", "hw1_", "sm_", "mp_apa_", "apa_")),
    ("vinewood", ("bh1_", "vw_", "bh2_", "bh3_", "bh4_")),
    ("suburb", ("mw_", "ch1_", "ch2_", "ch3_", "sc1_", "lr_")),
    ("industrial", ("id1_", "id2_", "ind_", "ap1_", "port_")),
    ("beach", ("vb_", "bay_", "vespu", "ch_")),
    ("country", ("cs1_", "cs2_", "cs3_", "cs4_", "cs5_", "cs6_", "cs7_", "cs8_",
                 "ss1_", "po1_", "gr_", "farm_")),
)


def _num(value, fallback=0.0) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return float(fallback)
    return out if math.isfinite(out) else float(fallback)


@dataclass
class Archetype:
    """Un model de harta gata de asezat pe un lot."""

    name: str
    bb_min: tuple = (0.0, 0.0, 0.0)
    bb_max: tuple = (0.0, 0.0, 0.0)
    category: str = "unknown"
    style: str = "any"
    # Rotatie (grade) care trebuie adaugata ca fata cladirii sa arate spre -Y local.
    # Se regleaza manual din joc; nu se poate deduce din cutie.
    yaw_offset: float = 0.0
    lod_dist: float = 0.0
    verified: bool = False          # masurat efectiv in joc
    blocked: bool = False           # pus pe lista neagra (arata prost / e rupt)
    notes: str = ""
    tags: tuple = field(default_factory=tuple)

    # ---------------------------------------------------------------- dimensiuni
    @property
    def sx(self) -> float:
        return abs(self.bb_max[0] - self.bb_min[0])

    @property
    def sy(self) -> float:
        return abs(self.bb_max[1] - self.bb_min[1])

    @property
    def height(self) -> float:
        return abs(self.bb_max[2] - self.bb_min[2])

    @property
    def footprint(self) -> float:
        return self.sx * self.sy

    @property
    def base_z(self) -> float:
        """Cat coboara modelul sub originea lui. La asezare: z_lume = z_teren - bb_min.z."""
        return float(self.bb_min[2])

    @property
    def center_xy(self) -> tuple:
        """Centrul amprentei relativ la originea modelului (rar e (0,0))."""
        return ((self.bb_min[0] + self.bb_max[0]) * 0.5,
                (self.bb_min[1] + self.bb_max[1]) * 0.5)

    def usable(self) -> bool:
        return (not self.blocked) and self.sx > 0.5 and self.sy > 0.5 and self.height > 0.5

    # ---------------------------------------------------------------- serializare
    def to_json(self) -> dict:
        out = {
            "name": self.name,
            "min": [round(v, 3) for v in self.bb_min],
            "max": [round(v, 3) for v in self.bb_max],
            "cat": self.category,
            "style": self.style,
        }
        if self.yaw_offset:
            out["yaw"] = round(self.yaw_offset, 1)
        if self.lod_dist:
            out["lod"] = round(self.lod_dist, 1)
        if self.verified:
            out["ok"] = True
        if self.blocked:
            out["blocked"] = True
        if self.notes:
            out["notes"] = self.notes
        if self.tags:
            out["tags"] = list(self.tags)
        return out

    @classmethod
    def from_json(cls, raw: dict) -> "Archetype":
        name = str(raw.get("name", "")).strip().lower()
        mn = raw.get("min") or [0.0, 0.0, 0.0]
        mx = raw.get("max") or [0.0, 0.0, 0.0]
        arch = cls(
            name=name,
            bb_min=tuple(_num(v) for v in (list(mn) + [0, 0, 0])[:3]),
            bb_max=tuple(_num(v) for v in (list(mx) + [0, 0, 0])[:3]),
            category=str(raw.get("cat") or "unknown"),
            style=str(raw.get("style") or "any"),
            yaw_offset=_num(raw.get("yaw"), 0.0),
            lod_dist=_num(raw.get("lod"), 0.0),
            verified=bool(raw.get("ok")),
            blocked=bool(raw.get("blocked")),
            notes=str(raw.get("notes") or ""),
            tags=tuple(str(t) for t in (raw.get("tags") or ())),
        )
        if arch.category not in CATEGORIES:
            arch.category = "unknown"
        if arch.style not in STYLES:
            arch.style = "any"
        return arch


def classify(name: str, sx: float, sy: float, height: float) -> str:
    """Categorie ghicita din nume + dimensiuni. Se poate corecta manual in catalog.json."""
    low = (name or "").lower()
    # Mobilierul urban si vegetatia sunt props, nu cladiri: un stalp de iluminat are 7 m
    # inaltime si 1 m amprenta, adica exact profilul unui "garaj" pentru regulile de mai jos.
    if low.startswith(PROP_PREFIXES):
        return "prop"

    for category, needles in NAME_HINTS:
        if any(n in low for n in needles):
            # O "casa" de 50 m inaltime nu e casa; numele bate, dar nu orbeste.
            if category == "house" and height > 14.0:
                break
            if category == "garage" and (height > 9.0 or sx * sy > 400.0):
                break
            return category

    area = sx * sy
    if height >= 40.0:
        return "tower"
    if height >= 15.0:
        return "midrise"
    if height >= 9.0:
        return "warehouse" if area >= 600.0 else "lowrise"
    if height >= 4.0:
        if area >= 500.0:
            return "warehouse"
        if area >= 55.0:
            return "house"
        return "garage"
    if height >= 1.5 and area >= 30.0:
        return "shop"
    return "filler"


def guess_style(name: str) -> str:
    low = (name or "").lower()
    for style, prefixes in STYLE_PREFIXES:
        if any(low.startswith(p) for p in prefixes):
            return style
    for style, prefixes in STYLE_PREFIXES:
        if any(p in low for p in prefixes):
            return style
    return "any"


class Catalog:
    """Colectia de arhetipuri + interogarile de care are nevoie plasatorul."""

    def __init__(self, archetypes=None, path: str | None = None):
        self.path = path or CATALOG_PATH
        self.items: dict[str, Archetype] = {}
        for arch in archetypes or ():
            self.items[arch.name] = arch
        self._index: dict[tuple, list] = {}

    # ---------------------------------------------------------------- I/O
    @classmethod
    def load(cls, path: str | None = None, required: bool = False) -> "Catalog":
        target = path or CATALOG_PATH
        if not os.path.isfile(target):
            if required:
                raise FileNotFoundError(
                    f"Catalogul de arhetipuri lipseste: {target}\n"
                    "Ruleaza /catalogscan in joc (mapeditor) sau "
                    "tools/import_ytyp_xml.py pe un export CodeWalker."
                )
            return cls(path=target)

        with open(target, "r", encoding="utf-8") as handle:
            raw = json.load(handle)

        items = []
        for entry in raw.get("archetypes") or ():
            arch = Archetype.from_json(entry)
            if arch.name:
                items.append(arch)
        out = cls(items, path=target)
        out.meta = {k: v for k, v in raw.items() if k != "archetypes"}
        return out

    def save(self, path: str | None = None) -> str:
        target = path or self.path
        os.makedirs(os.path.dirname(target), exist_ok=True)
        payload = {
            "version": 1,
            "count": len(self.items),
            "archetypes": [self.items[k].to_json() for k in sorted(self.items)],
        }
        with open(target, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=1, ensure_ascii=False)
        return target

    # ---------------------------------------------------------------- populare
    def add(self, arch: Archetype, overwrite_labels: bool = False) -> Archetype:
        """Adauga sau actualizeaza. Etichetele manuale (cat/style/yaw/blocked) se pastreaza."""
        old = self.items.get(arch.name)
        if old is not None and not overwrite_labels:
            # O verificare din joc ramane valabila; un import din fisiere nu o anuleaza.
            arch.verified = arch.verified or old.verified
            arch.category = old.category if old.category != "unknown" else arch.category
            arch.style = old.style if old.style != "any" else arch.style
            arch.yaw_offset = old.yaw_offset or arch.yaw_offset
            arch.blocked = old.blocked or arch.blocked
            arch.notes = old.notes or arch.notes
            if old.tags and not arch.tags:
                arch.tags = old.tags
        self.items[arch.name] = arch
        self._index.clear()
        return arch

    def add_measurement(self, name: str, bb_min, bb_max, lod_dist: float = 0.0,
                        verified: bool | None = True) -> Archetype:
        """
        O cutie masurata -> arhetip clasificat automat.

        `verified`: True = masurat in joc (se incarca sigur); False/None = citit din fisiere,
        nu stim inca daca se incarca oriunde. None pastreaza starea veche daca exista.
        """
        name = str(name).strip().lower()
        bb_min = tuple(_num(v) for v in bb_min)
        bb_max = tuple(_num(v) for v in bb_max)
        sx = abs(bb_max[0] - bb_min[0])
        sy = abs(bb_max[1] - bb_min[1])
        hz = abs(bb_max[2] - bb_min[2])
        old = self.items.get(name)
        if verified is None:
            is_ok = bool(old.verified) if old is not None else False
        else:
            is_ok = bool(verified)
        arch = Archetype(
            name=name,
            bb_min=bb_min,
            bb_max=bb_max,
            category=classify(name, sx, sy, hz),
            style=guess_style(name),
            lod_dist=_num(lod_dist, 0.0),
            verified=is_ok,
        )
        return self.add(arch)

    def reclassify(self, only_unknown: bool = True) -> int:
        """Re-aplica regulile automate (dupa ce s-au schimbat pragurile)."""
        changed = 0
        for arch in self.items.values():
            if only_unknown and arch.category != "unknown":
                continue
            new = classify(arch.name, arch.sx, arch.sy, arch.height)
            if new != arch.category:
                arch.category = new
                changed += 1
            if arch.style == "any":
                arch.style = guess_style(arch.name)
        if changed:
            self._index.clear()
        return changed

    # ---------------------------------------------------------------- interogari
    def by_category(self, category: str, style: str | None = None) -> list:
        key = (category, style or "")
        cached = self._index.get(key)
        if cached is not None:
            return cached
        out = [a for a in self.items.values()
               if a.category == category and a.usable()
               and (not style or a.style in (style, "any"))]
        out.sort(key=lambda a: a.name)
        self._index[key] = out
        return out

    def fit(self, width: float, depth: float, categories, style: str | None = None,
            tolerance: float = 0.15, min_fill: float = 0.45) -> list:
        """
        Arhetipurile care intra intr-un lot de `width` x `depth` (width = de-a lungul strazii).

        Intoarce [(arhetip, yaw_extra, fill)] sortat descrescator dupa cat de bine umple lotul.
        `yaw_extra` e 0 sau 90 (modelul rotit ca sa intre). `tolerance` = cat poate depasi
        modelul lotul (cladirile vanilla au adesea trotuar/scari in cutie).
        `min_fill` taie cladirile ridicol de mici pentru lotul dat.
        """
        if width <= 0.5 or depth <= 0.5:
            return []
        wmax = width * (1.0 + tolerance)
        dmax = depth * (1.0 + tolerance)
        lot_area = width * depth
        out = []

        wanted = (categories,) if isinstance(categories, str) else tuple(categories)
        for category in wanted:
            for arch in self.by_category(category, style):
                for yaw_extra, (ax, ay) in ((0.0, (arch.sx, arch.sy)), (90.0, (arch.sy, arch.sx))):
                    if ax > wmax or ay > dmax:
                        continue
                    fill = (ax * ay) / lot_area if lot_area > 0 else 0.0
                    if fill < min_fill:
                        continue
                    out.append((arch, yaw_extra, min(fill, 1.0)))
                    break  # o singura orientare per arhetip (prima care intra)

        out.sort(key=lambda item: -item[2])
        return out

    def pick(self, width: float, depth: float, categories, rng: random.Random,
             style: str | None = None, tolerance: float = 0.15, min_fill: float = 0.45,
             top: int = 8):
        """Alege aleator dintre cele mai bune `top` potriviri. None daca nu intra nimic."""
        options = self.fit(width, depth, categories, style, tolerance, min_fill)
        if not options:
            return None
        pool = options[:max(1, top)]
        return pool[rng.randrange(len(pool))]

    # ---------------------------------------------------------------- diverse
    def stats(self) -> dict:
        out = {"total": len(self.items), "verified": 0, "blocked": 0}
        for arch in self.items.values():
            if arch.verified:
                out["verified"] += 1
            if arch.blocked:
                out["blocked"] += 1
            out[arch.category] = out.get(arch.category, 0) + 1
        return out

    def names(self) -> list:
        return sorted(self.items)

    def __len__(self) -> int:
        return len(self.items)

    def __contains__(self, name) -> bool:
        return str(name).strip().lower() in self.items

    def __getitem__(self, name) -> Archetype:
        return self.items[str(name).strip().lower()]
