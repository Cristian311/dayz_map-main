import argparse
import numpy as np
import sys
from pathlib import Path
from pymateria import rsc7
from pymateria.gta5 import (
    Bone,
    PrimitiveType,
    HashResolver,
    gen8,
    gen9,
)

import ctypes


def print_drawable_info(drawable: gen8.Drawable | gen9.Drawable):
    is_gen8 = isinstance(drawable, gen8.Drawable)
    print(f"        Name: {drawable.name}")
    if drawable.skeleton is None:
        print("    Skeleton: None")
    else:
        print("    Skeleton:")

        def print_bone(b: Bone, parent: Bone | None = None, is_last_child: bool = False, prefix: str = ""):
            connector = "" if parent is None else "└── " if is_last_child else "├── "
            print(f"{prefix}{connector}{b.name}  (id={b.id})")
            n = len(b.children)
            extension = "    " if is_last_child or parent is None else "│   "
            prefix += extension
            for i, c in enumerate(b.children):
                print_bone(c, b, i == (n - 1), prefix)

        print_bone(drawable.skeleton.root_bone, prefix=" " * 10)

    print(
        f"       Bound: {drawable.bound.type.name if drawable.bound is not None else None}")

    print("     Shaders:")
    if is_gen8:
        for i, s in enumerate(drawable.shader_group.shaders):
            print(
                f"        [{i}] shader={s.basis_shader} material={s.basis_material}  ("
                f"{len(s.parameters)} parameter(s), "
                f"draw_bucket={s.draw_bucket.name}, draw_bucket_mask={s.draw_bucket_mask:04X}, "
                f"is_instanced={s.is_instanced}"
                ")"
            )
            for j, p in enumerate(s.parameters):
                print(
                    f"            [{j}] parameter={p.name}   data={p.data}"
                )
    else:
        for i, s in enumerate(drawable.shader_group.shaders):
            print(
                f"        [{i}] shader={s.basis_hash}  ("
                f"{s.parameters.sampler_count} sampler parameter(s), "
                f"{s.parameters.buffer_count} buffer parameter(s), "
                f"{s.parameters.resource_count} resource parameter(s), "
                f"draw_bucket={s.draw_bucket.name}, draw_bucket_mask={s.draw_bucket_mask:04X}, "
                f"is_instanced={s.is_instanced}, "
                f"max_render_threads={s.max_render_threads}, "
                f"user_flags={s.user_flags}"
                ")"
            )
            info = gen9.ShaderRegistry.instance.get_shader(s.basis_hash.hash)

            print("              Buffers")
            for buff_info in info.buffers:
                name = buff_info.name
                buff = s.parameters.get_buffer_by_name(name)
                buff_data_ptr = buff.data
                buff_data = buff_data_ptr.contents
                print(f"                {name} ({buff.raw_data.size} bytes)")
                for field_name, _ in buff_data._fields_:
                    field_value = getattr(buff_data, field_name)
                    if isinstance(field_value, ctypes.Array):
                        # Convert to NumPy array to view the array contents when printing
                        field_value = np.ctypeslib.as_array(field_value)
                    print(f"                  {field_name} = {field_value}")

            print("              Resources")
            for res_info in info.resources:
                name = res_info.name
                res = s.parameters.get_resource_by_name(name)
                print(f"                {name} = {res}")

    if drawable.shader_group.texture_dictionary is None:
        print("Embedded Txd: None")
    else:
        print("Embedded Txd:")
        for tex_hash, tex in drawable.shader_group.texture_dictionary.textures.items():
            print(f"        [{tex_hash}] name={tex.name}  ({tex})")

    print("        Lods:")
    for lod_level, lod in drawable.lods.items():
        num_geom = sum(len(m.geometries) for m in lod.models)
        num_tris = sum(
            len(g.ib.indices)
            if g.primitive_type == PrimitiveType.TRIS
            else 0
            for m in lod.models
            for g in m.geometries
        ) // 3
        num_verts = sum(
            g.vb.num_vertices
            for m in lod.models
            for g in m.geometries
        )

        print(
            f"        [{lod_level.name}:{lod.lod_threshold}] {len(lod.models)} models,  {num_geom} geometries,  {num_tris} polygons,  {num_verts} vertices"
        )
        for m in lod.models:
            for g in m.geometries:
                fvf = g.vb.fvf
                print(
                    f"          FVF   {fvf.vertex_data_size} bytes/vertex   dtype={np.dtype(fvf.dtype)}")
                for c in sorted(fvf.channels, key=lambda c: c.value):
                    ty = fvf.get_channel_size_type(c).name
                    size = fvf.get_channel_size(c)
                    offset = fvf.get_channel_offset(c)
                    print(
                        f"           {c.name}\t{ty}\toffset={offset}\tsize={size}")

                buffer_raw = g.vb.buffer_raw
                buffer = g.vb.buffer
                # print(f"          IB       {repr(g.ib.indices)}")
                print(f"          VB (raw) {repr(buffer_raw)}")
                # print(f"          VB       {repr(buffer)}")


def read_rsc7_header(file: Path) -> rsc7.Header | None:
    with file.open("rb") as f:
        data = f.read(rsc7.Header.HEADER_SIZE)
        if len(data) < rsc7.Header.HEADER_SIZE:
            return None
        return rsc7.Header(data)


def main():
    parser = argparse.ArgumentParser(description="Drawable Info")
    parser.add_argument("file", type=Path, help="Path to the YDR or YDD file")
    parser.add_argument(
        "-nt", type=Path, help="Directory with .nametable files to load", required=False)
    args = parser.parse_args()

    nt: Path = args.nt
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
        case (".ydr", gen8.Drawable.RSC_VERSION):
            print("Gen8 Drawable")
            drawable = gen8.Drawable.import_rsc(args.file).result
            print_drawable_info(drawable)
        case (".ydr", gen9.Drawable.RSC_VERSION):
            print("Gen9 Drawable")
            drawable = gen9.Drawable.import_rsc(args.file).result
            print_drawable_info(drawable)
        case (".ydd", gen8.DrawableDictionary.RSC_VERSION):
            print("Gen8 Drawable Dictionary")
            dwd = gen8.DrawableDictionary.import_rsc(args.file).result
            for key, drawable in dwd.drawables.items():
                print(f"#{key}")
                print_drawable_info(drawable)
                print("+++++++++++++++++++++++++++++++++")
        case (".ydd", gen9.DrawableDictionary.RSC_VERSION):
            print("Gen9 Drawable Dictionary")
            dwd = gen9.DrawableDictionary.import_rsc(args.file).result
            for key, drawable in dwd.drawables.items():
                print(f"#{key}")
                print_drawable_info(drawable)
                print("+++++++++++++++++++++++++++++++++")
        case (".ydr" | ".ydd", _):
            print(f"Unknown version {ver} in RSC7 header.")
            sys.exit(1)
        case _:
            print(f"Unsupported file extension '{ext}'")
            sys.exit(1)


if __name__ == "__main__":
    main()
