"""RAGE Pack File 7 archive format."""

import enum
import io
import os
import pathlib
from typing import overload

import pymateria
import pymateria.rsc7


class PackFileEncryptionType(enum.Enum):
    NONE = 0

    TFIT = 1

    AES = 2

class PackFileEntryType(enum.Enum):
    DIRECTORY = 0

    RESOURCE = 1

    FILE = 2

    ARCHIVE = 3

class PackFileEntry:
    @property
    def type(self) -> PackFileEntryType: ...

    @property
    def path(self) -> pathlib.PurePosixPath: ...

    @path.setter
    def path(self, arg: str | pathlib.PurePosixPath, /) -> None: ...

    @property
    def name(self) -> str: ...

    @property
    def extension(self) -> str: ...

    @property
    def parent(self) -> PackFile: ...

    def set_name(self, name: str) -> None: ...

    @overload
    @staticmethod
    def import_file(parent: PackFile, path_in_archive: str | pathlib.PurePosixPath, stream: io.IOBase, filename: str) -> PackFileEntry: ...

    @overload
    @staticmethod
    def import_file(parent: PackFile, path_in_archive: str | pathlib.PurePosixPath, path: str | os.PathLike) -> PackFileEntry: ...

class PackFileEntryDirectory(PackFileEntry):
    def __init__(self, parent: PackFile, path_in_archive: str | pathlib.PurePosixPath) -> None: ...

class PackFileEntryFile(PackFileEntry):
    @property
    def size(self) -> int: ...

    @property
    def size_compressed(self) -> int: ...

    @overload
    def export(self, stream: io.IOBase) -> None: ...

    @overload
    def export(self, path: str | os.PathLike) -> None: ...

    @overload
    def export(self) -> pymateria.Buffer: ...

    def export_compressed(self) -> pymateria.Buffer: ...

    @overload
    @staticmethod
    def create(parent: PackFile, path_in_archive: str | pathlib.PurePosixPath, data: bytes) -> PackFileEntryFile: ...

    @overload
    @staticmethod
    def create(parent: PackFile, path_in_archive: str | pathlib.PurePosixPath, stream: io.IOBase) -> PackFileEntryFile: ...

    @overload
    @staticmethod
    def create(parent: PackFile, path_in_archive: str | pathlib.PurePosixPath, path: str | os.PathLike) -> PackFileEntryFile: ...

class PackFileEntryResource(PackFileEntry):
    @property
    def header(self) -> pymateria.rsc7.Header: ...

    @property
    def resource_version(self) -> int: ...

    @property
    def size(self) -> int: ...

    @property
    def raw_buffer(self) -> pymateria.Buffer: ...

    @overload
    def export(self, stream: io.IOBase) -> None: ...

    @overload
    def export(self, path: str | os.PathLike) -> None: ...

    @overload
    def export(self) -> pymateria.Buffer: ...

    @overload
    @staticmethod
    def create(parent: PackFile, path_in_archive: str | pathlib.PurePosixPath, data: bytes) -> PackFileEntryResource: ...

    @overload
    @staticmethod
    def create(parent: PackFile, path_in_archive: str | pathlib.PurePosixPath, stream: io.IOBase) -> PackFileEntryResource: ...

    @overload
    @staticmethod
    def create(parent: PackFile, path_in_archive: str | pathlib.PurePosixPath, path: str | os.PathLike) -> PackFileEntryResource: ...

class PackFileEntryArchive(PackFileEntryFile):
    @property
    def archive(self) -> PackFile:
        """Get the nested PackFile. Lazy-loads on first access."""

    @overload
    @staticmethod
    def create(parent: PackFile, path_in_archive: str | pathlib.PurePosixPath) -> PackFileEntryArchive: ...

    @overload
    @staticmethod
    def create(parent: PackFile, path_in_archive: str | pathlib.PurePosixPath, filename: str, data: bytes) -> PackFileEntryArchive: ...

    @overload
    @staticmethod
    def create(parent: PackFile, path_in_archive: str | pathlib.PurePosixPath, filename: str, stream: io.IOBase) -> PackFileEntryArchive: ...

    @overload
    @staticmethod
    def create(parent: PackFile, path_in_archive: str | pathlib.PurePosixPath, filename: str, path: str | os.PathLike) -> PackFileEntryArchive: ...

class PackFile:
    class NestedArchiveEntry:
        def __init__(self) -> None: ...

        @property
        def full_path(self) -> pathlib.PurePosixPath: ...

        @full_path.setter
        def full_path(self, arg: str | pathlib.PurePosixPath, /) -> None: ...

        @property
        def entry(self) -> PackFileEntry: ...

        @entry.setter
        def entry(self, arg: PackFileEntry, /) -> None: ...

    @property
    def source_path(self) -> pathlib.Path | None: ...

    @property
    def source_buffer(self) -> pymateria.Buffer: ...

    @property
    def source_filename(self) -> str: ...

    @property
    def source_offset(self) -> int: ...

    @property
    def entries(self) -> list[PackFileEntry]: ...

    @property
    def root(self) -> PackFileEntryDirectory: ...

    def get_all_entries(self) -> list[PackFile.NestedArchiveEntry]: ...

    def get_by_path(self, path: str | pathlib.PurePosixPath, nested_archives: bool = True) -> PackFileEntry: ...

    def find_by_name(self, name: str, nested_archives: bool = False) -> list[PackFileEntry]: ...

    def find_by_extension(self, ext: str, nested_archives: bool = False) -> list[PackFileEntry]: ...

    def add_entry(self, entry: PackFileEntry, allow_override: bool) -> None: ...

    def remove_entry(self, entry: PackFileEntry) -> bool: ...

    @staticmethod
    def create() -> PackFile: ...

    @overload
    @staticmethod
    def import_rpf(file_path: str | os.PathLike, override_filename: str = '') -> PackFile: ...

    @overload
    @staticmethod
    def import_rpf(stream: io.IOBase, filename: str) -> PackFile: ...

    @overload
    @staticmethod
    def import_rpf(buffer: pymateria.Buffer, filename: str) -> PackFile: ...

    @overload
    @staticmethod
    def import_rpf(file_path: str | os.PathLike, offset: int, size: int, filename: str) -> PackFile: ...

    @staticmethod
    def export_rpf(pack_file: PackFile, stream: io.IOBase) -> None: ...

    @staticmethod
    def calculate_export_size(pack_file: PackFile) -> int: ...
