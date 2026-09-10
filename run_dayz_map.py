# -*- coding: utf-8 -*-
"""
Launcher pentru generatorul de harta DayZ -> GTA V.

Din linia de comanda (headless):
    blender -b -P run_dayz_map.py -- --preset demo
    blender -b -P run_dayz_map.py -- --preset full --seed 42 --origin 7000 -8000

Din Blender (Text Editor -> Run Script): seteaza PRESET mai jos si apasa Run.
Presets: tiny (512 m, test), demo (1 km, 2 sate), full (4 km, 10 sate).
"""
import os
import sys

PRESET = "demo"          # folosit cand rulezi din Text Editor
OUTPUT_DIR = None        # None = <folderul acesta>/output

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
if HERE not in sys.path:
    sys.path.insert(0, HERE)
# dependintele python (szio + pymateria) instalate de INSTALEAZA_TOOLS.bat
PYDEPS = os.path.join(HERE, "tools", "pydeps")
if os.path.isdir(PYDEPS) and PYDEPS not in sys.path:
    sys.path.insert(0, PYDEPS)


def _parse_args():
    import argparse
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser(description="DayZ map generator pentru GTA V")
    p.add_argument("--preset", default=None, choices=["tiny", "demo", "full"])
    p.add_argument("--out", default=OUTPUT_DIR)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--size", type=float, default=None, help="latura hartii in metri (multiplu de 256)")
    p.add_argument("--origin", type=float, nargs=2, default=None, metavar=("X", "Y"),
                   help="coltul SV al hartii in lumea GTA V")
    p.add_argument("--name", default=None, help="prefixul fisierelor/arhetipurilor (litere mici)")
    p.add_argument("--gen9", action="store_true", help="exporta si varianta GTA V Enhanced")
    p.add_argument("--ragemp", action="store_true", help="construieste si dlc.rpf pentru RAGE:MP (implicit doar FiveM)")
    p.add_argument("--config", default=None, help="fisier map.json cu setarile (argumentele din linia de comanda au prioritate)")
    return p.parse_args(argv)


def main():
    args = _parse_args()
    from dayzgen.main import run
    cfg_path = args.config
    if cfg_path and not os.path.isabs(cfg_path):
        cfg_path = os.path.join(HERE, cfg_path)
    if cfg_path and not os.path.isfile(cfg_path):
        print(f"Fisierul de configurare nu exista: {cfg_path}")
        raise SystemExit(2)
    out = run(preset=args.preset, out_root=args.out, gen9=True if args.gen9 else None, seed=args.seed,
              size=args.size, origin=tuple(args.origin) if args.origin else None, name=args.name,
              ragemp=True if args.ragemp else None, config=cfg_path)
    print(f"\nRezultatul este in: {out}\n")


if __name__ == "__main__":
    main()
