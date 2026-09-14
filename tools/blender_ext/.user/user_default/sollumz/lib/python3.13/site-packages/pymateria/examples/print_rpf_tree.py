import argparse
import sys
from collections import defaultdict
from pathlib import Path
from pymateria.rpf7 import (
    PackFile,
    PackFileEntry,
    PackFileEntryArchive,
    PackFileEntryDirectory,
    PackFileEntryFile,
    PackFileEntryResource,
)


def format_size(n: int) -> str:
    if n < 1024:
        return f"{n}B"
    size = float(n)
    for unit in ("KiB", "MiB", "GiB", "TiB"):
        size /= 1024
        if size < 1024:
            return f"{size:.1f}{unit}"
    return f"{size:.1f}PiB"


def _sort_key(entry: PackFileEntry) -> tuple[int, str]:
    if isinstance(entry, PackFileEntryDirectory):
        rank = 0
    elif isinstance(entry, PackFileEntryArchive):
        rank = 1
    else:
        rank = 2
    return (rank, entry.name.lower())


def _label_for(entry: PackFileEntry) -> str:
    if isinstance(entry, PackFileEntryDirectory):
        return f"{entry.name}/"
    if isinstance(entry, PackFileEntryArchive):
        return f"{entry.name} [archive, {format_size(entry.size_compressed)}]"
    if isinstance(entry, PackFileEntryResource):
        return f"{entry.name} [resource v{entry.resource_version}, {format_size(entry.size)}]"
    if isinstance(entry, PackFileEntryFile):
        return f"{entry.name} [{format_size(entry.size)}]"
    return entry.name


def _walk(
    children: dict[str, list[tuple[PackFileEntry, str]]],
    parent_key: str,
    current_prefix: str,
    expand_archives: bool,
    out: list[str],
) -> None:
    kids = children.get(parent_key)
    if not kids:
        return
    last_idx = len(kids) - 1
    for i, (entry, path_str) in enumerate(kids):
        last = i == last_idx
        connector = "└── " if last else "├── "
        extension = "    " if last else "│   "
        out.append(f"{current_prefix}{connector}{_label_for(entry)}")

        if isinstance(entry, PackFileEntryDirectory):
            _walk(children, path_str, current_prefix + extension, expand_archives, out)
        elif isinstance(entry, PackFileEntryArchive) and expand_archives:
            try:
                nested = entry.archive
            except Exception as exc:
                out.append(f"{current_prefix}{extension}<could not open: {exc}>")
                continue
            render_pack_file(nested, current_prefix + extension, expand_archives, out)


def render_pack_file(
    pf: PackFile, prefix: str, expand_archives: bool, out: list[str]
) -> None:
    # Group entries by parent. The path_str is cached alongside each entry so
    # `e.path` is marshalled from C++ exactly once per entry; parent and the
    # directory-recursion key are derived by string slicing.
    children: dict[str, list[tuple[PackFileEntry, str]]] = defaultdict(list)
    for e in pf.entries:
        path_str = e.path.as_posix()
        if path_str in ("", "."):
            # Skip the implicit root directory entry — it has an empty path
            # and would group itself as a child of "." (causing infinite recursion).
            continue
        sep = path_str.rfind("/")
        parent_key = path_str[:sep] if sep != -1 else "."
        children[parent_key].append((e, path_str))

    for kids in children.values():
        kids.sort(key=lambda pair: _sort_key(pair[0]))

    _walk(children, ".", prefix, expand_archives, out)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Recursively find every .rpf under a directory and print its directory/file tree."
    )
    parser.add_argument(
        "directory", type=Path, help="Directory to scan recursively for .rpf files"
    )
    parser.add_argument(
        "--no-expand-archives",
        dest="expand_archives",
        action="store_false",
        help="Render nested RPFs as leaves instead of recursing into them",
    )
    args = parser.parse_args()

    # Ensure UTF-8 output so the box-drawing characters survive redirection
    # on Windows (where stdout otherwise defaults to cp1252).
    sys.stdout.reconfigure(encoding="utf-8")

    if not args.directory.is_dir():
        print(f"Not a directory: {args.directory}", file=sys.stderr)
        return 1

    rpf_files = sorted(args.directory.rglob("*.rpf"))
    if not rpf_files:
        print(f"No .rpf files found under {args.directory}", file=sys.stderr)
        return 0

    write = sys.stdout.write
    for rpf_path in rpf_files:
        rel = rpf_path.relative_to(args.directory)
        write(f"\n{rel}\n")
        try:
            pf = PackFile.import_rpf(rpf_path)
        except Exception as exc:
            print(f"  <failed to open: {exc}>", file=sys.stderr)
            continue
        out: list[str] = []
        render_pack_file(pf, "", args.expand_archives, out)
        if out:
            write("\n".join(out))
            write("\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
