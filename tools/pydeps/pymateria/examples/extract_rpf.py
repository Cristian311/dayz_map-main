import argparse
import sys
from pathlib import Path
from pymateria.rpf7 import (
    PackFile,
    PackFileEntryArchive,
    PackFileEntryDirectory,
    PackFileEntryFile,
    PackFileEntryResource,
)


def extract_pack_file(pf: PackFile, out_base: Path) -> int:
    """Extract every entry of `pf` into `out_base`, recursing into nested RPFs.

    Each entry's `path` is already relative to its own pack file's root, so a
    nested archive is simply re-based at its own directory. Returns the number
    of files written.
    """
    count = 0
    for e in pf.entries:
        path_str = e.path.as_posix()
        if path_str in ("", "."):
            # Skip the implicit root directory entry (empty path).
            continue
        target = out_base / path_str

        # PackFileEntryArchive derives from PackFileEntryFile, so it must be
        # checked first. A nested RPF becomes a directory we recurse into.
        if isinstance(e, PackFileEntryArchive):
            target.mkdir(parents=True, exist_ok=True)
            try:
                nested = e.archive
            except Exception as exc:
                print(f"  <could not open {path_str}: {exc}>", file=sys.stderr)
                continue
            count += extract_pack_file(nested, target)
        elif isinstance(e, PackFileEntryDirectory):
            target.mkdir(parents=True, exist_ok=True)
        elif isinstance(e, (PackFileEntryFile, PackFileEntryResource)):
            target.parent.mkdir(parents=True, exist_ok=True)
            e.export(target)
            count += 1
    return count


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Recursively extract every file from one or more RPF archives. "
        "Nested RPFs are extracted as directories."
    )
    parser.add_argument(
        "archives", type=Path, nargs="+", help="One or more .rpf files to extract"
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("."),
        help="Output directory; each archive is extracted into its own subfolder "
        "(default: current directory)",
    )
    args = parser.parse_args()

    # Ensure UTF-8 output so file names survive redirection on Windows
    # (where stdout otherwise defaults to cp1252).
    sys.stdout.reconfigure(encoding="utf-8")

    had_error = False
    for archive_path in args.archives:
        if not archive_path.is_file():
            print(f"Not a file: {archive_path}", file=sys.stderr)
            had_error = True
            continue

        # Keep the full name (including .rpf) so the top-level folder mirrors
        # how nested archives are materialized.
        dest = args.output / archive_path.name
        try:
            pf = PackFile.import_rpf(archive_path)
        except Exception as exc:
            print(f"Failed to open {archive_path}: {exc}", file=sys.stderr)
            had_error = True
            continue

        n = extract_pack_file(pf, dest)
        print(f"{archive_path} -> {dest}/ ({n} files)")

    return 1 if had_error else 0


if __name__ == "__main__":
    sys.exit(main())
