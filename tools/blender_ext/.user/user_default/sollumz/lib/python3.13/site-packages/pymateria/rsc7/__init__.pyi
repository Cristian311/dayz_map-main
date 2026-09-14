from typing import overload

import pymateria


class Header:
    @overload
    def __init__(self) -> None: ...

    @overload
    def __init__(self, arg: bytes, /) -> None: ...

    class Sizes:
        def __init__(self) -> None: ...

        @property
        def leaf_shift(self) -> int: ...

        @leaf_shift.setter
        def leaf_shift(self, arg: int, /) -> None: ...

        @property
        def head_16_count(self) -> int: ...

        @head_16_count.setter
        def head_16_count(self, arg: int, /) -> None: ...

        @property
        def head_8_count(self) -> int: ...

        @head_8_count.setter
        def head_8_count(self, arg: int, /) -> None: ...

        @property
        def head_4_count(self) -> int: ...

        @head_4_count.setter
        def head_4_count(self, arg: int, /) -> None: ...

        @property
        def head_2_count(self) -> int: ...

        @head_2_count.setter
        def head_2_count(self, arg: int, /) -> None: ...

        @property
        def base_count(self) -> int: ...

        @base_count.setter
        def base_count(self, arg: int, /) -> None: ...

        @property
        def has_tail2(self) -> bool: ...

        @has_tail2.setter
        def has_tail2(self, arg: bool, /) -> None: ...

        @property
        def has_tail4(self) -> bool: ...

        @has_tail4.setter
        def has_tail4(self, arg: bool, /) -> None: ...

        @property
        def has_tail8(self) -> bool: ...

        @has_tail8.setter
        def has_tail8(self, arg: bool, /) -> None: ...

        @property
        def has_tail16(self) -> bool: ...

        @has_tail16.setter
        def has_tail16(self, arg: bool, /) -> None: ...

        @property
        def version(self) -> int: ...

        @version.setter
        def version(self, arg: int, /) -> None: ...

        @property
        def count(self) -> int:
            """Get total number of buckets."""

        @property
        def size(self) -> int:
            """Get total size of all buckets in bytes."""

        @property
        def base_size(self) -> int:
            """
            Get base bucket size in bytes. All bucket sizes are base size shifted left or right up to 4.
            """

        @property
        def largest_chunk_size(self) -> int:
            """Get size of the largest bucket in bytes."""

        def get_count(self, shift: int) -> int:
            """
            Get count of buckets of specific shift. E.g. passing 0 will count buckets of base size, passing 1 will count 2x base size buckets, 2 will count 4x, etc...
            """

    @property
    def magic(self) -> int:
        """Reset magic value (force structure to be "valid")."""

    @magic.setter
    def magic(self, arg: int, /) -> None: ...

    @property
    def version(self) -> int: ...

    @version.setter
    def version(self, arg: int, /) -> None: ...

    @property
    def virtual_sizes(self) -> Header.Sizes: ...

    @virtual_sizes.setter
    def virtual_sizes(self, arg: Header.Sizes, /) -> None: ...

    @property
    def physical_sizes(self) -> Header.Sizes: ...

    @physical_sizes.setter
    def physical_sizes(self, arg: Header.Sizes, /) -> None: ...

    @property
    def is_valid(self) -> bool:
        """Check if structure is valid (magic value is matching)."""

    def __bool__(self) -> bool: ...

    def reset_magic(self) -> None: ...

    @property
    def split_version(self) -> int:
        """
        RSC7 header has two version values, one is stored as a plain number, and one is split between size bitflags. This returns the split version.
        """

    @split_version.setter
    def split_version(self, arg: int, /) -> None: ...

    def set_versions(self, arg: int, /) -> None: ...

    def is_valid_addr(self, arg: int, /) -> bool:
        """Check if virtual address is a valid RSC7 address in this file."""

    def resolve_addr(self, arg: int, /) -> tuple[bool, int]:
        """
        Resolve virtual RSC7 address into a space (virtual or physical) and a local virtual address inside that space. Returns a tuple containing a bool (true if virtual, false if physical) and an integer (local address inside the space).
        """

    def resolve_addr_offset(self, arg: int, /) -> int: ...

    def to_bytes(self) -> bytes: ...

    HEADER_SIZE: int = ...
    """Size of the RSC7 header in bytes."""

    LEAF_SIZE: int = ...
    """Size of a leaf bucket in bytes."""

    RSC7_MAGIC: int = ...
    """Magic number identifying an RSC7 header."""

    RSC7_ESCROW_MAGIC: int = ...
    """Magic number identifying an escrowed RSC7 header."""

    FIXED_VIRTUAL_BASE: int = ...
    """Base virtual address used by RSC7 resources."""

    FIXED_PHYSICAL_BASE: int = ...
    """Base physical address used by RSC7 resources."""

    RESOURCE_16N_BITS: int = ...
    """(arg: object, /) -> int"""

    RESOURCE_8N_BITS: int = ...
    """(arg: object, /) -> int"""

    RESOURCE_4N_BITS: int = ...
    """(arg: object, /) -> int"""

    RESOURCE_2N_BITS: int = ...
    """(arg: object, /) -> int"""

    RESOURCE_N_BITS: int = ...
    """(arg: object, /) -> int"""

class Serializer:
    @property
    def messages(self) -> pymateria.DiagnosticMessages: ...

    @property
    def metadata(self) -> pymateria.UserMetadata: ...

    @property
    def virtual_alignment(self) -> int: ...

    @property
    def physical_alignment(self) -> int: ...

    @property
    def ignore_pg_base(self) -> bool: ...

    @property
    def relaxed(self) -> bool: ...

    @property
    def target(self) -> pymateria.AssetTarget: ...

class Deserializer:
    @property
    def header(self) -> Header: ...

    @property
    def metadata(self) -> pymateria.Metadata:
        """The metadata embedded in the file, or None if not present."""

    @property
    def messages(self) -> pymateria.DiagnosticMessages: ...

    @property
    def relaxed(self) -> bool: ...

    @property
    def target(self) -> pymateria.AssetTarget: ...
