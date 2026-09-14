import argparse
import sys
import io
from pathlib import Path
from pymateria import rsc7
from pymateria.gta5 import (
    ImageType,
    gen8,
    gen9,
)
try:
    import tkinter as tk
    from tkinter import ttk
    IS_TKINTER_AVAILABLE = True
except ImportError:
    IS_TKINTER_AVAILABLE = False


def read_rsc7_header(file: Path) -> rsc7.Header | None:
    with file.open("rb") as f:
        data = f.read(rsc7.Header.HEADER_SIZE)
        if len(data) < rsc7.Header.HEADER_SIZE:
            return None
        return rsc7.Header(data)


def main():
    parser = argparse.ArgumentParser(description="TXD Viewer")
    parser.add_argument("file", type=Path, help="Path to the YTD file")
    args = parser.parse_args()

    header = read_rsc7_header(args.file)
    if not header:
        print("Invalid RSC7 header.")
        sys.exit(1)

    ext = args.file.suffix
    ver = header.version
    match (ext, ver):
        case (".ytd", gen8.TextureDictionary.RSC_VERSION):
            print("Gen8 Texture Dictionary")
            txd = gen8.TextureDictionary.import_rsc(args.file).result
        case (".ytd", gen9.TextureDictionary.RSC_VERSION):
            print("Gen9 Texture Dictionary")
            txd = gen9.TextureDictionary.import_rsc(args.file).result
        case (".ytd", _):
            print(f"Unknown version {ver} in RSC7 header.")
            sys.exit(1)
        case _:
            print(f"Unsupported file extension '{ext}'")
            sys.exit(1)

    if IS_TKINTER_AVAILABLE:
        root = tk.Tk()
        root.title(f"TXD Viewer: {args.file.name}")
        root.geometry("512x800")

    images = []
    for tex_hash, tex in txd.textures.items():
        print(f"{tex_hash}:  {tex.name}")
        print(f"        {tex.width}x{tex.height}x{tex.depth}")
        print(f"        {len(tex.mips)} mip(s)")
        print(f"        {tex.format}")

        if IS_TKINTER_AVAILABLE:
            try:
                image_data = io.BytesIO()
                tex.export_wic_image(image_data, ImageType.PNG)
                image_data = image_data.getvalue()
                img = tk.PhotoImage(data=image_data)
                images.append((tex.name, img))
            except RuntimeError as e:
                print(f"    Error: {e}", file=sys.stderr)

    if not IS_TKINTER_AVAILABLE:
        print()
        print("Tkinter is not available, cannot open TXD viewer. Please, make sure Python is installed with Tkinter support.")
        print()
        return

    if images:
        canvas = tk.Canvas(root)
        scrollbar = ttk.Scrollbar(
            root, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        # Configure canvas
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Display images
        for name, img in images:
            label = ttk.Label(scrollable_frame, text=name)
            label.config(font=("TkDefaultFont", 25))
            label.pack()
            label = ttk.Label(scrollable_frame, image=img)
            label.image = img  # Keep a reference to avoid garbage collection
            label.pack(pady=10)
    else:
        tk.Label(root, text="No images found in the specified folder.").pack()

    root.mainloop()


if __name__ == "__main__":
    main()
