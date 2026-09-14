import argparse
from pathlib import Path
from pymateria.gta5 import (
    ArchetypeDefinition,
    ArchetypeDefinitionTime,
    ArchetypeDefinitionMlo,
)
from pymateria.gta5.gen8 import MapTypes


def print_archetype_info(arch: ArchetypeDefinition):
    arch_type = (
        "MLO" if isinstance(arch, ArchetypeDefinitionMlo) else
        "Time" if isinstance(arch, ArchetypeDefinitionTime) else
        "Base"
    )
    print(f"              Type: {arch_type}")
    print(f"              Name: {arch.name.string_or_placeholder}")
    print(f"             Flags: {arch.flags}")
    print(f" Special Attribute: {arch.special_attribute}")
    print(f"      Bounding Box: {arch.bounding_box}")
    print(f"   Bounding Sphere: {arch.bounding_sphere}")

    if isinstance(arch, ArchetypeDefinitionTime):
        print(f"        Time Flags: {arch.time_flags}")

    if isinstance(arch, ArchetypeDefinitionMlo):
        print(f"         MLO Flags: {arch.mlo_flags}")
        print( "               MLO:")
        print(f"                   {len(arch.rooms)} rooms")
        print(f"                   {len(arch.portals)} portals")
        print(f"                   {len(arch.entities)} entities")
        print(f"                   {len(arch.entity_sets)} entity sets")

    print(f"        Extensions: {len(arch.extensions)} {[type(e).__name__ for e in arch.extensions]}")


def main():
    parser = argparse.ArgumentParser(description="Archetypes Info")
    parser.add_argument("file", type=Path, help="Path to the YTYP file")
    args = parser.parse_args()

    typ = MapTypes.import_rsc(args.file).result
    for i, arch in enumerate(typ.archetypes):
        print(f"#{i}")
        print_archetype_info(arch)


if __name__ == "__main__":
    main()
