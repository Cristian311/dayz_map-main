import argparse
from pathlib import Path
from pymateria.gta5 import (
    Bound,
    BoundComposite,
    BoundType,
    BoundGeometry,
)


def print_bound_info(bound: Bound):
    print(f"      Python Class: {type(bound)}")
    print(f"              Type: {bound.type}")
    print(f"          Position: {bound.position}")
    print(f"               CoG: {bound.center_of_gravity_offset}")
    print(f"Material ID Packed: {bound.material_id_packed:016X}")
    print(f"   Angular Inertia: {bound.angular_inertia}")
    print(f"            Volume: {bound.volume}")
    print(f"            Margin: {bound.margin}")
    print(f"             Flags: {bound.flags}")

    if isinstance(bound, BoundGeometry):
        print(f"             Primitives: {len(bound.primitives)}")
        for i in range(min(5, len(bound.primitives))):
            print(f"                     #{i}: {bound.primitives[i].type}")


def main():
    parser = argparse.ArgumentParser(description="Bound Info")
    parser.add_argument("file", type=Path, help="Path to the YBN file")
    args = parser.parse_args()

    bound: BoundComposite = Bound.import_rsc(args.file).result

    print_bound_info(bound)
    print("+++++++++++++++++++++++++++++++++")
    if bound.type == BoundType.COMPOSITE:
        for i, child in enumerate(bound.bounds):
            print(f"#{i}")
            print_bound_info(child.bound)
            print(f"            Matrix: {child.matrix}")
            print(f"        Type Flags: {child.type_flags}")
            print(f"     Include Flags: {child.include_flags}")
            print("+++++++++++++++++++++++++++++++++")


if __name__ == "__main__":
    main()
