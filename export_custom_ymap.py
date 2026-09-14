# -*- coding: utf-8 -*-
"""
Exporta obiectele puse manual din editorul in joc, FARA sa regenereze harta si FARA Blender.

Citeste map.json -> folderul resursei FiveM instalate -> editor/objects.json si scrie:
  stream/<nume>_custom.ymap      obiectele adaugate manual
  stream/<nume>_cXX_YY.ymap      chunk-urile generate, rescrise fara entitatile din "removed"
                                 (reconstruite din editor/chunks.json, scris la generare)

Utilizare:
    python export_custom_ymap.py [--config map.json] [--out <folder resursa>] [--dry-run]

Nota: scrierea fisierelor binare GTA V se face cu szio + pymateria din tools\\pydeps. Modulul nativ
pymateria este compilat pentru Python 3.13 (acelasi cu al Blender-ului). Daca Python-ul de sistem nu
il poate incarca, scriptul se re-lanseaza automat cu python.exe-ul din instalarea de Blender.
"""
import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PYDEPS = HERE / "tools" / "pydeps"
for p in (str(HERE), str(PYDEPS)):
    if p not in sys.path:
        sys.path.insert(0, p)

_REEXEC_FLAG = "DAYZGEN_REEXEC"


def _blender_pythons():
    """Cai posibile catre python.exe-ul din Blender (3.13, cu pymateria compatibil)."""
    cands = []
    txt = HERE / "tools" / "blender_path.txt"
    roots = []
    if txt.is_file():
        try:
            bl = Path(txt.read_text(encoding="utf-8", errors="ignore").strip())
            if bl.name.lower().endswith(".exe"):
                roots.append(bl.parent)
        except OSError:
            pass
    for base in (os.environ.get("ProgramFiles", r"C:\Program Files"),
                 os.environ.get("ProgramFiles(x86)", "")):
        bf = Path(base) / "Blender Foundation" if base else None
        if bf and bf.is_dir():
            roots.extend(sorted(bf.iterdir(), reverse=True))
    for root in roots:
        try:
            for ver in sorted(root.iterdir(), reverse=True):
                exe = ver / "python" / "bin" / "python.exe"
                if exe.is_file():
                    cands.append(exe)
        except OSError:
            continue
    return cands


def _ensure_szio():
    """Verifica szio; daca nu merge pe interpretorul curent, reporneste scriptul cu Python-ul Blender."""
    try:
        import szio.gta5  # noqa: F401
        return
    except Exception as e:  # noqa
        first = e
    if os.environ.get(_REEXEC_FLAG) == "1":
        print(f"EROARE: szio/pymateria nu se pot incarca nici cu {sys.executable}: {first!r}")
        raise SystemExit(3)
    import subprocess
    for exe in _blender_pythons():
        env = dict(os.environ, **{_REEXEC_FLAG: "1"})
        print(f"Python-ul de sistem nu poate incarca pymateria; folosesc {exe}", flush=True)
        return sys.exit(subprocess.call([str(exe), str(Path(__file__).resolve())] + sys.argv[1:], env=env))
    print("EROARE: nu am gasit un Python compatibil (3.13) pentru szio/pymateria.")
    print("Instaleaza Blender 5.x sau ruleaza INSTALEAZA_TOOLS.bat.")
    print(f"Detaliu: {first!r}")
    raise SystemExit(3)


def main():
    ap = argparse.ArgumentParser(description="Export obiecte manuale -> .ymap (fara Blender)")
    ap.add_argument("--config", default=str(HERE / "map.json"), help="fisierul map.json")
    ap.add_argument("--out", default=None, help="folderul resursei in care se scrie (implicit cel din map.json)")
    ap.add_argument("--objects", default=None, help="alt fisier objects.json (pentru teste)")
    ap.add_argument("--name", default=None,
                    help="numele hartii din resursa (<nume>_custom.ymap); editorul din joc da numele resursei")
    ap.add_argument("--dry-run", action="store_true", help="doar afiseaza ce ar face")
    args = ap.parse_args()

    from dayzgen.config import MapConfig
    try:
        cfg = MapConfig.from_json(args.config)
    except ValueError as e:
        print(f"EROARE de configurare: {e}")
        raise SystemExit(2)

    res_dir = Path(args.out) if args.out else Path(cfg.fivem_resources_dir) / cfg.name
    obj_path = Path(args.objects) if args.objects else res_dir / cfg.custom_objects_file.replace("\\", "/")
    editor_dir = res_dir / "editor"
    stream = res_dir / "stream"

    if not res_dir.is_dir():
        print(f"EROARE: folderul resursei nu exista: {res_dir}")
        raise SystemExit(2)

    _ensure_szio()
    from dayzgen import gta_export as G

    try:
        objects, removed = G.read_objects_json(obj_path)
    except json.JSONDecodeError as e:
        print(f"EROARE: JSON invalid in {obj_path}: {e}")
        raise SystemExit(2)
    print(f"Resursa:  {res_dir}")
    print(f"Obiecte:  {obj_path} -> {len(objects)} obiecte manuale, {len(removed)} entitati sterse")

    if args.dry_run:
        print("(dry-run: nu scriu nimic)")
        return

    # numele hartii generate efectiv in resursa (chunks.json bate map.json, daca difera)
    chunks_path = editor_dir / "chunks.json"
    chunks_data = None
    if chunks_path.is_file():
        with open(chunks_path, "r", encoding="utf-8-sig") as fh:
            chunks_data = json.load(fh)
        if chunks_data.get("name") and chunks_data["name"] != cfg.name:
            print(f"ATENTIE: map.json spune name={cfg.name}, dar resursa contine harta "
                  f"'{chunks_data['name']}' - folosesc numele din resursa.")
            cfg.name = chunks_data["name"]
    if args.name:
        # orasele din editorul de oras nu au chunks.json: numele vine de la editorul din joc (= resursa)
        cfg.name = args.name

    stream.mkdir(parents=True, exist_ok=True)
    items = G.custom_items(cfg, objects)
    name = G.write_ymap(f"{cfg.name}_custom", items, str(stream), gen9=False)
    print(f"  scris: stream\\{name}.ymap ({len(items)} entitati)")

    if removed:
        if chunks_data is None:
            print(f"ATENTIE: {chunks_path} lipseste - nu pot rescrie chunk-urile generate.")
            print("         Regenereaza harta o data (GENEREAZA_*.bat) ca sa se creeze editor/chunks.json.")
            return
        n = 0
        for ch in chunks_data.get("chunks", []):
            keep = [e for e in ch["entities"] if int(e["guid"]) not in removed]
            if len(keep) == len(ch["entities"]):
                continue
            G.write_ymap(ch["name"], keep, str(stream), gen9=False)
            print(f"  rescris: stream\\{ch['name']}.ymap ({len(ch['entities']) - len(keep)} entitati scoase)")
            n += 1
        if n == 0:
            print("  niciun chunk generat nu a fost afectat")

    # marcam momentul exportului: editorul din joc nu mai spawneaza la runtime obiectele deja coapte
    stamp = G.mark_objects_exported(obj_path)
    if stamp:
        print(f"  exportedAt = {stamp} (scris in {obj_path.name})")

    print("GATA. Restart complet de server (si de client) ca sa se vada schimbarile.")


if __name__ == "__main__":
    main()
    # iesire rapida: evita zgomotul "nanobind: leaked ..." de la inchiderea modulului nativ
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)
