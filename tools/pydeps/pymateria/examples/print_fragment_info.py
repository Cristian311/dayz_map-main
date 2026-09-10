import argparse
import numpy as np
import sys
from pathlib import Path
from pymateria import rsc7
from pymateria.gta5 import (
    HashResolver,
    gen8,
    gen9,
)


def print_fragment_info(fragment: gen8.Fragment | gen9.Fragment):
    is_gen8 = isinstance(fragment, gen8.Fragment)
    print(f"               Name: {fragment.tune_name}")
    print(f"           Drawable: {fragment.drawable}")
    print(f"    Extra Drawables: {fragment.extra_drawables}")
    print(f"                     {fragment.extra_drawable_names}")
    print(f"Unbroken Elasticity: {fragment.unbroken_elasticity}")
    print(f"     Gravity Factor: {fragment.gravity_factor}")
    print(f"    Buoyancy Factor: {fragment.buoyancy_factor}")


def read_rsc7_header(file: Path) -> rsc7.Header | None:
    with file.open("rb") as f:
        data = f.read(rsc7.Header.HEADER_SIZE)
        if len(data) < rsc7.Header.HEADER_SIZE:
            return None
        return rsc7.Header(data)


def main():
    parser = argparse.ArgumentParser(description="Fragment Info")
    parser.add_argument("file", type=Path, help="Path to the YFT file")
    parser.add_argument(
        "-nt", type=Path, help="Directory with .nametable files to load", required=False)
    args = parser.parse_args()

    nt: Path | None = args.nt
    if nt and nt.is_dir():
        for file in nt.glob("*.nametable"):
            if file.is_file():
                HashResolver.instance.load_nametable(
                    file.read_text(encoding="utf-8"))

    header = read_rsc7_header(args.file)
    if not header:
        print("Invalid RSC7 header.")
        sys.exit(1)

    np.set_printoptions(suppress=True)

    ext = args.file.suffix
    ver = header.version
    match (ext, ver):
        case (".yft", gen8.Fragment.RSC_VERSION):
            print("Gen8 Fragment")
            fragment = gen8.Fragment.import_rsc(args.file).result
            print_fragment_info(fragment)
        case (".yft", gen9.Fragment.RSC_VERSION):
            print("Gen9 Fragment")
            fragment = gen9.Fragment.import_rsc(args.file).result
            print_fragment_info(fragment)
        case (".yft", _):
            print(f"Unknown version {ver} in RSC7 header.")
            sys.exit(1)
        case _:
            print(f"Unsupported file extension '{ext}'")
            sys.exit(1)


if __name__ == "__main__":
    main()
