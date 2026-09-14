"""Access to GTA5 formats."""

from collections.abc import Iterable, Iterator, Mapping, Sequence
import enum
import io
import os
from typing import Annotated, overload

import numpy
from numpy.typing import NDArray

from . import gen8 as gen8, gen9 as gen9
import pymateria
import pymateria.pso
import pymateria.rsc7


class HashString:
    @overload
    def __init__(self) -> None: ...

    @overload
    def __init__(self, arg: int, /) -> None: ...

    @overload
    def __init__(self, arg: int, /) -> None: ...

    @overload
    def __init__(self, arg: str, /) -> None: ...

    @property
    def hash(self) -> int: ...

    @hash.setter
    def hash(self, arg: int, /) -> None: ...

    @property
    def string(self) -> str | None: ...

    @string.setter
    def string(self, arg: str, /) -> None: ...

    @property
    def string_or_placeholder(self) -> str: ...

    @property
    def is_empty(self) -> bool: ...

    def __eq__(self, arg: HashString, /) -> bool: ...

    def __ne__(self, arg: HashString, /) -> bool: ...

    def __le__(self, arg: HashString, /) -> bool: ...

    def __ge__(self, arg: HashString, /) -> bool: ...

    def __lt__(self, arg: HashString, /) -> bool: ...

    def __gt__(self, arg: HashString, /) -> bool: ...

    def __hash__(self) -> int: ...

    def __repr__(self) -> str: ...

    empty: pymateria.gta5.HashString = ...
    """Hash for the empty string."""

class CombinedHashString:
    @overload
    def __init__(self) -> None: ...

    @overload
    def __init__(self, arg: int, /) -> None: ...

    @overload
    def __init__(self, arg: int, /) -> None: ...

    @overload
    def __init__(self, arg: str, /) -> None: ...

    @property
    def hash(self) -> int: ...

    @hash.setter
    def hash(self, arg: int, /) -> None: ...

    @property
    def string(self) -> str: ...

    @string.setter
    def string(self, arg: str, /) -> None: ...

    @property
    def string_or_placeholder(self) -> str: ...

    @property
    def has_string(self) -> bool: ...

    @property
    def is_empty(self) -> bool: ...

    def __eq__(self, arg: CombinedHashString, /) -> bool: ...

    def __ne__(self, arg: CombinedHashString, /) -> bool: ...

    def __le__(self, arg: CombinedHashString, /) -> bool: ...

    def __ge__(self, arg: CombinedHashString, /) -> bool: ...

    def __lt__(self, arg: CombinedHashString, /) -> bool: ...

    def __gt__(self, arg: CombinedHashString, /) -> bool: ...

    def __hash__(self) -> int: ...

    def __repr__(self) -> str: ...

    empty: pymateria.gta5.CombinedHashString = ...
    """Hash for the empty string."""

class HashResolver:
    def __init__(self) -> None: ...

    class NametableSeparator(enum.Enum):
        NEWLINE = 0

        NULLCHAR = 1

    def resolve_string(self, arg: int, /) -> str | None: ...

    def add_string(self, arg: str, /) -> int: ...

    def reset(self) -> None: ...

    def load_nametable(self, arg: str, /) -> None: ...

    def save_nametable(self, separator: HashResolver.NametableSeparator = NametableSeparator.NEWLINE) -> str: ...

    instance: pymateria.gta5.HashResolver = ...
    """The global shared HashResolver instance. Used by HashString."""

class CollisionFlags(enum.Flag):
    DEFAULT_TYPE = 1

    MAP_TYPE_WEAPON = 2

    MAP_TYPE_MOVER = 4

    MAP_TYPE_HORSE = 8

    MAP_TYPE_COVER = 16

    MAP_TYPE_VEHICLE = 32

    VEHICLE_NON_BVH_TYPE = 64

    VEHICLE_BVH_TYPE = 128

    BOX_VEHICLE_TYPE = 256

    PED_TYPE = 512

    RAGDOLL_TYPE = 1024

    HORSE_TYPE = 2048

    HORSE_RAGDOLL_TYPE = 4096

    OBJECT_TYPE = 8192

    ENVCLOTH_OBJECT_TYPE = 16384

    PLANT_TYPE = 32768

    PROJECTILE_TYPE = 65536

    EXPLOSION_TYPE = 131072

    PICKUP_TYPE = 262144

    FOLIAGE_TYPE = 524288

    FORKLIFT_FORKS_TYPE = 1048576

    WEAPON_TEST = 2097152

    CAMERA_TEST = 4194304

    AI_TEST = 8388608

    SCRIPT_TEST = 16777216

    WHEEL_TEST = 33554432

    GLASS_TYPE = 67108864

    RIVER_TYPE = 134217728

    SMOKE_TYPE = 268435456

    UNSMASHED_TYPE = 536870912

    STAIR_SLOPE_TYPE = 1073741824

    DEEP_SURFACE_TYPE = 2147483648

class BoundType(enum.Enum):
    SPHERE = 0

    CAPSULE = 1

    BOX = 3

    GEOMETRY = 4

    BVH = 8

    COMPOSITE = 10

    TRIANGLE = 11

    DISC = 12

    CYLINDER = 13

    PLANE = 15

class Bound:
    """Base class for collision bounds."""

    @property
    def part_index(self) -> int: ...

    @part_index.setter
    def part_index(self, arg: int, /) -> None: ...

    @property
    def position(self) -> pymateria.Vector3f: ...

    @position.setter
    def position(self, arg: pymateria.Vector3f, /) -> None: ...

    @property
    def center_of_gravity_offset(self) -> pymateria.Vector3f: ...

    @center_of_gravity_offset.setter
    def center_of_gravity_offset(self, arg: pymateria.Vector3f, /) -> None: ...

    @property
    def material_id_packed(self) -> int: ...

    @material_id_packed.setter
    def material_id_packed(self, arg: int, /) -> None: ...

    @property
    def angular_inertia(self) -> pymateria.Vector3f | None: ...

    @angular_inertia.setter
    def angular_inertia(self, arg: pymateria.Vector3f | None) -> None: ...

    @property
    def volume(self) -> float | None: ...

    @volume.setter
    def volume(self, arg: float | None) -> None: ...

    @property
    def margin(self) -> float | None: ...

    @margin.setter
    def margin(self, arg: float | None) -> None: ...

    @property
    def flags(self) -> int: ...

    @flags.setter
    def flags(self, arg: int, /) -> None: ...

    @property
    def type(self) -> BoundType: ...

    @property
    def material_id(self) -> int: ...

    @material_id.setter
    def material_id(self, arg: int, /) -> None: ...

    @property
    def procedural_id(self) -> int: ...

    @procedural_id.setter
    def procedural_id(self, arg: int, /) -> None: ...

    @property
    def room_id(self) -> int: ...

    @room_id.setter
    def room_id(self, arg: int, /) -> None: ...

    @property
    def ped_density(self) -> int: ...

    @ped_density.setter
    def ped_density(self, arg: int, /) -> None: ...

    @property
    def poly_flags(self) -> int: ...

    @poly_flags.setter
    def poly_flags(self, arg: int, /) -> None: ...

    @property
    def material_color_index(self) -> int: ...

    @material_color_index.setter
    def material_color_index(self, arg: int, /) -> None: ...

    class DeserializationResult(pymateria.SharedResult):
        def __init__(self) -> None: ...

        @property
        def result(self) -> Bound: ...

        @result.setter
        def result(self, arg: Bound, /) -> None: ...

        @property
        def deserializer(self) -> pymateria.rsc7.Deserializer: ...

    RSC_VERSION: int = ...
    """Resource version of this asset format."""

    @overload
    @staticmethod
    def import_rsc(file_path: str | os.PathLike, settings: pymateria.ImportSettings | None = None) -> Bound.DeserializationResult: ...

    @overload
    @staticmethod
    def import_rsc(stream: io.IOBase, settings: pymateria.ImportSettings | None = None) -> Bound.DeserializationResult: ...

    @overload
    @staticmethod
    def export_rsc(instance: Bound, file_path: str | os.PathLike, settings: pymateria.ExportSettings | None = None) -> pymateria.SerializationResultRsc7: ...

    @overload
    @staticmethod
    def export_rsc(instance: Bound, stream: io.IOBase, settings: pymateria.ExportSettings | None = None) -> pymateria.SerializationResultRsc7: ...

class BoundList:
    @overload
    def __init__(self) -> None:
        """Default constructor"""

    @overload
    def __init__(self, arg: BoundList) -> None:
        """Copy constructor"""

    @overload
    def __init__(self, arg: Iterable[Bound], /) -> None:
        """Construct from an iterable object"""

    def __len__(self) -> int: ...

    def __bool__(self) -> bool:
        """Check whether the vector is nonempty"""

    def __repr__(self) -> str: ...

    def __iter__(self) -> Iterator[Bound]: ...

    @overload
    def __getitem__(self, arg: int, /) -> Bound: ...

    @overload
    def __getitem__(self, arg: slice, /) -> BoundList: ...

    def clear(self) -> None:
        """Remove all items from list."""

    def append(self, arg: Bound, /) -> None:
        """Append `arg` to the end of the list."""

    def insert(self, arg0: int, arg1: Bound, /) -> None:
        """Insert object `arg1` before index `arg0`."""

    def pop(self, index: int = -1) -> Bound:
        """Remove and return item at `index` (default last)."""

    def extend(self, arg: BoundList, /) -> None:
        """Extend `self` by appending elements from `arg`."""

    @overload
    def __setitem__(self, arg0: int, arg1: Bound, /) -> None: ...

    @overload
    def __setitem__(self, arg0: slice, arg1: BoundList, /) -> None: ...

    @overload
    def __delitem__(self, arg: int, /) -> None: ...

    @overload
    def __delitem__(self, arg: slice, /) -> None: ...

    def __eq__(self, arg: object, /) -> bool: ...

    def __ne__(self, arg: object, /) -> bool: ...

    @overload
    def __contains__(self, arg: Bound, /) -> bool: ...

    @overload
    def __contains__(self, arg: object, /) -> bool: ...

    def count(self, arg: Bound, /) -> int:
        """Return number of occurrences of `arg`."""

    def remove(self, arg: Bound, /) -> None:
        """Remove first occurrence of `arg`."""

class BoundCompositeElement:
    def __init__(self) -> None: ...

    @property
    def bound(self) -> Bound: ...

    @bound.setter
    def bound(self, arg: Bound | None) -> None: ...

    @property
    def matrix(self) -> pymateria.Matrix34: ...

    @matrix.setter
    def matrix(self, arg: pymateria.Matrix34, /) -> None: ...

    @property
    def type_flags(self) -> CollisionFlags: ...

    @type_flags.setter
    def type_flags(self, arg: CollisionFlags, /) -> None: ...

    @property
    def include_flags(self) -> CollisionFlags: ...

    @include_flags.setter
    def include_flags(self, arg: CollisionFlags, /) -> None: ...

class BoundCompositeElementList:
    @overload
    def __init__(self) -> None:
        """Default constructor"""

    @overload
    def __init__(self, arg: BoundCompositeElementList) -> None:
        """Copy constructor"""

    @overload
    def __init__(self, arg: Iterable[BoundCompositeElement], /) -> None:
        """Construct from an iterable object"""

    def __len__(self) -> int: ...

    def __bool__(self) -> bool:
        """Check whether the vector is nonempty"""

    def __repr__(self) -> str: ...

    def __iter__(self) -> Iterator[BoundCompositeElement]: ...

    @overload
    def __getitem__(self, arg: int, /) -> BoundCompositeElement: ...

    @overload
    def __getitem__(self, arg: slice, /) -> BoundCompositeElementList: ...

    def clear(self) -> None:
        """Remove all items from list."""

    def append(self, arg: BoundCompositeElement, /) -> None:
        """Append `arg` to the end of the list."""

    def insert(self, arg0: int, arg1: BoundCompositeElement, /) -> None:
        """Insert object `arg1` before index `arg0`."""

    def pop(self, index: int = -1) -> BoundCompositeElement:
        """Remove and return item at `index` (default last)."""

    def extend(self, arg: BoundCompositeElementList, /) -> None:
        """Extend `self` by appending elements from `arg`."""

    @overload
    def __setitem__(self, arg0: int, arg1: BoundCompositeElement, /) -> None: ...

    @overload
    def __setitem__(self, arg0: slice, arg1: BoundCompositeElementList, /) -> None: ...

    @overload
    def __delitem__(self, arg: int, /) -> None: ...

    @overload
    def __delitem__(self, arg: slice, /) -> None: ...

class BoundComposite(Bound):
    def __init__(self) -> None: ...

    @property
    def bounds(self) -> BoundCompositeElementList: ...

    @bounds.setter
    def bounds(self, arg: BoundCompositeElementList, /) -> None: ...

    @property
    def generate_bvh(self) -> bool: ...

    @generate_bvh.setter
    def generate_bvh(self, arg: bool, /) -> None: ...

class BoundBox(Bound):
    def __init__(self) -> None: ...

    @property
    def min(self) -> pymateria.Vector3f: ...

    @min.setter
    def min(self, arg: pymateria.Vector3f, /) -> None: ...

    @property
    def max(self) -> pymateria.Vector3f: ...

    @max.setter
    def max(self, arg: pymateria.Vector3f, /) -> None: ...

class BoundCapsule(Bound):
    def __init__(self) -> None: ...

    @property
    def radius(self) -> float: ...

    @radius.setter
    def radius(self, arg: float, /) -> None: ...

    @property
    def length(self) -> float: ...

    @length.setter
    def length(self, arg: float, /) -> None: ...

    @property
    def half_height(self) -> float: ...

    @half_height.setter
    def half_height(self, arg: float, /) -> None: ...

class BoundCylinder(Bound):
    def __init__(self) -> None: ...

    @property
    def radius(self) -> float: ...

    @radius.setter
    def radius(self, arg: float, /) -> None: ...

    @property
    def height(self) -> float: ...

    @height.setter
    def height(self, arg: float, /) -> None: ...

class BoundDisc(Bound):
    def __init__(self) -> None: ...

    @property
    def radius(self) -> float: ...

    @radius.setter
    def radius(self, arg: float, /) -> None: ...

class BoundSphere(Bound):
    def __init__(self) -> None: ...

    @property
    def radius(self) -> float: ...

    @radius.setter
    def radius(self, arg: float, /) -> None: ...

class BoundPlane(Bound):
    def __init__(self) -> None: ...

    @property
    def normal(self) -> pymateria.Vector3f: ...

    @normal.setter
    def normal(self, arg: pymateria.Vector3f, /) -> None: ...

class BoundPrimitiveType(enum.Enum):
    POLYGON = 0

    SPHERE = 1

    CAPSULE = 2

    BOX = 3

    CYLINDER = 4

class BoundPrimitive:
    """Base class for geometry primitives."""

    @property
    def material_id(self) -> int: ...

    @material_id.setter
    def material_id(self, arg: int, /) -> None: ...

    @property
    def material_color(self) -> pymateria.ColorRGBA: ...

    @material_color.setter
    def material_color(self, arg: pymateria.ColorRGBA, /) -> None: ...

    @property
    def type(self) -> BoundPrimitiveType: ...

class BoundPrimitivePolygonVertexIndex:
    def __init__(self) -> None: ...

    @property
    def index(self) -> int: ...

    @index.setter
    def index(self, arg: int, /) -> None: ...

    @property
    def normal_code(self) -> int: ...

    @normal_code.setter
    def normal_code(self, arg: int, /) -> None: ...

class BoundPrimitivePolygon(BoundPrimitive):
    def __init__(self) -> None: ...

    @property
    def indices(self) -> list[BoundPrimitivePolygonVertexIndex]: ...

    @indices.setter
    def indices(self, arg: Sequence[BoundPrimitivePolygonVertexIndex], /) -> None: ...

class BoundPrimitiveSphere(BoundPrimitive):
    def __init__(self) -> None: ...

    @property
    def center_index(self) -> int: ...

    @center_index.setter
    def center_index(self, arg: int, /) -> None: ...

    @property
    def radius(self) -> float: ...

    @radius.setter
    def radius(self, arg: float, /) -> None: ...

class BoundPrimitiveCapsule(BoundPrimitive):
    def __init__(self) -> None: ...

    @property
    def end_index0(self) -> int: ...

    @end_index0.setter
    def end_index0(self, arg: int, /) -> None: ...

    @property
    def end_index1(self) -> int: ...

    @end_index1.setter
    def end_index1(self, arg: int, /) -> None: ...

    @property
    def radius(self) -> float: ...

    @radius.setter
    def radius(self, arg: float, /) -> None: ...

class BoundPrimitiveBox(BoundPrimitive):
    def __init__(self) -> None: ...

    @property
    def vertex_indices(self) -> list[int]: ...

    @vertex_indices.setter
    def vertex_indices(self, arg: Sequence[int], /) -> None: ...

class BoundPrimitiveCylinder(BoundPrimitive):
    def __init__(self) -> None: ...

    @property
    def end_index0(self) -> int: ...

    @end_index0.setter
    def end_index0(self, arg: int, /) -> None: ...

    @property
    def end_index1(self) -> int: ...

    @end_index1.setter
    def end_index1(self, arg: int, /) -> None: ...

    @property
    def radius(self) -> float: ...

    @radius.setter
    def radius(self, arg: float, /) -> None: ...

class BoundVertex:
    def __init__(self) -> None: ...

    @property
    def position(self) -> pymateria.Vector3f: ...

    @position.setter
    def position(self, arg: pymateria.Vector3f, /) -> None: ...

    @property
    def second_surface_displacement(self) -> float: ...

    @second_surface_displacement.setter
    def second_surface_displacement(self, arg: float, /) -> None: ...

    @property
    def color(self) -> pymateria.ColorRGBA: ...

    @color.setter
    def color(self, arg: pymateria.ColorRGBA, /) -> None: ...

class BoundVertexList:
    @overload
    def __init__(self) -> None:
        """Default constructor"""

    @overload
    def __init__(self, arg: BoundVertexList) -> None:
        """Copy constructor"""

    @overload
    def __init__(self, arg: Iterable[BoundVertex], /) -> None:
        """Construct from an iterable object"""

    def __len__(self) -> int: ...

    def __bool__(self) -> bool:
        """Check whether the vector is nonempty"""

    def __repr__(self) -> str: ...

    def __iter__(self) -> Iterator[BoundVertex]: ...

    @overload
    def __getitem__(self, arg: int, /) -> BoundVertex: ...

    @overload
    def __getitem__(self, arg: slice, /) -> BoundVertexList: ...

    def clear(self) -> None:
        """Remove all items from list."""

    def append(self, arg: BoundVertex, /) -> None:
        """Append `arg` to the end of the list."""

    def insert(self, arg0: int, arg1: BoundVertex, /) -> None:
        """Insert object `arg1` before index `arg0`."""

    def pop(self, index: int = -1) -> BoundVertex:
        """Remove and return item at `index` (default last)."""

    def extend(self, arg: BoundVertexList, /) -> None:
        """Extend `self` by appending elements from `arg`."""

    @overload
    def __setitem__(self, arg0: int, arg1: BoundVertex, /) -> None: ...

    @overload
    def __setitem__(self, arg0: slice, arg1: BoundVertexList, /) -> None: ...

    @overload
    def __delitem__(self, arg: int, /) -> None: ...

    @overload
    def __delitem__(self, arg: slice, /) -> None: ...

class BoundGeometry(Bound):
    def __init__(self) -> None: ...

    @property
    def vertices(self) -> BoundVertexList: ...

    @vertices.setter
    def vertices(self, arg: BoundVertexList, /) -> None: ...

    @property
    def generate_bvh(self) -> bool: ...

    @generate_bvh.setter
    def generate_bvh(self, arg: bool, /) -> None: ...

    @property
    def use_second_surface(self) -> bool: ...

    @use_second_surface.setter
    def use_second_surface(self, arg: bool, /) -> None: ...

    @property
    def use_vertex_colors(self) -> bool: ...

    @use_vertex_colors.setter
    def use_vertex_colors(self, arg: bool, /) -> None: ...

    @property
    def use_material_colors(self) -> bool: ...

    @use_material_colors.setter
    def use_material_colors(self, arg: bool, /) -> None: ...

    @property
    def bounding_box(self) -> pymateria.AABB3f | None: ...

    @bounding_box.setter
    def bounding_box(self, arg: pymateria.AABB3f | None) -> None: ...

    class PrimitivesAccessor:
        def __len__(self) -> int: ...

        def __bool__(self) -> bool: ...

        def __getitem__(self, arg: int, /) -> BoundPrimitive: ...

        def __setitem__(self, arg0: int, arg1: BoundPrimitive, /) -> None: ...

        def clear(self) -> None: ...

        def append(self, arg: BoundPrimitive, /) -> None: ...

        def insert(self, arg0: int, arg1: BoundPrimitive, /) -> None: ...

        def pop(self, index: int = -1) -> BoundPrimitive: ...

        def __delitem__(self, arg: int, /) -> None: ...

    @property
    def primitives(self) -> BoundGeometry.PrimitivesAccessor: ...

class ImageType(enum.Enum):
    PNG = 0

    JPEG = 1

    BMP = 2

class TextureMip:
    def __init__(self) -> None: ...

    class LayerAccessor:
        def __len__(self) -> int: ...

        def __bool__(self) -> bool: ...

        def __getitem__(self, arg: int, /) -> Annotated[NDArray[numpy.uint8], dict(order='C')]: ...

        def __setitem__(self, arg0: int, arg1: Annotated[NDArray[numpy.uint8], dict(order='C', writable=False)], /) -> None: ...

        def clear(self) -> None: ...

        def append(self, arg: Annotated[NDArray[numpy.uint8], dict(order='C', writable=False)], /) -> None: ...

        def insert(self, arg0: int, arg1: Annotated[NDArray[numpy.uint8], dict(order='C', writable=False)], /) -> None: ...

        def pop(self, index: int = -1) -> Annotated[NDArray[numpy.uint8], dict(order='C')]: ...

        def __delitem__(self, arg: int, /) -> None: ...

    @property
    def layers(self) -> TextureMip.LayerAccessor: ...

class TextureMipList:
    @overload
    def __init__(self) -> None:
        """Default constructor"""

    @overload
    def __init__(self, arg: TextureMipList) -> None:
        """Copy constructor"""

    @overload
    def __init__(self, arg: Iterable[TextureMip], /) -> None:
        """Construct from an iterable object"""

    def __len__(self) -> int: ...

    def __bool__(self) -> bool:
        """Check whether the vector is nonempty"""

    def __repr__(self) -> str: ...

    def __iter__(self) -> Iterator[TextureMip]: ...

    @overload
    def __getitem__(self, arg: int, /) -> TextureMip: ...

    @overload
    def __getitem__(self, arg: slice, /) -> TextureMipList: ...

    def clear(self) -> None:
        """Remove all items from list."""

    def append(self, arg: TextureMip, /) -> None:
        """Append `arg` to the end of the list."""

    def insert(self, arg0: int, arg1: TextureMip, /) -> None:
        """Insert object `arg1` before index `arg0`."""

    def pop(self, index: int = -1) -> TextureMip:
        """Remove and return item at `index` (default last)."""

    def extend(self, arg: TextureMipList, /) -> None:
        """Extend `self` by appending elements from `arg`."""

    @overload
    def __setitem__(self, arg0: int, arg1: TextureMip, /) -> None: ...

    @overload
    def __setitem__(self, arg0: slice, arg1: TextureMipList, /) -> None: ...

    @overload
    def __delitem__(self, arg: int, /) -> None: ...

    @overload
    def __delitem__(self, arg: slice, /) -> None: ...

    def __eq__(self, arg: object, /) -> bool: ...

    def __ne__(self, arg: object, /) -> bool: ...

    @overload
    def __contains__(self, arg: TextureMip, /) -> bool: ...

    @overload
    def __contains__(self, arg: object, /) -> bool: ...

    def count(self, arg: TextureMip, /) -> int:
        """Return number of occurrences of `arg`."""

    def remove(self, arg: TextureMip, /) -> None:
        """Remove first occurrence of `arg`."""

class BoneJointDofs(enum.Enum):
    JOINT_1_DOF = 1

    JOINT_3_DOF = 3

class BoneJointControlPoint:
    @overload
    def __init__(self) -> None: ...

    @overload
    def __init__(self, max_swing: float, min_twist: float, max_twist: float) -> None: ...

    @property
    def max_swing(self) -> float: ...

    @max_swing.setter
    def max_swing(self, arg: float, /) -> None: ...

    @property
    def min_twist(self) -> float: ...

    @min_twist.setter
    def min_twist(self, arg: float, /) -> None: ...

    @property
    def max_twist(self) -> float: ...

    @max_twist.setter
    def max_twist(self, arg: float, /) -> None: ...

class BoneRotationLimit:
    def __init__(self) -> None: ...

    @property
    def bone_id(self) -> int: ...

    @bone_id.setter
    def bone_id(self, arg: int, /) -> None: ...

    @property
    def num_control_points(self) -> int: ...

    @num_control_points.setter
    def num_control_points(self, arg: int, /) -> None: ...

    @property
    def control_points(self) -> tuple[BoneJointControlPoint, BoneJointControlPoint, BoneJointControlPoint, BoneJointControlPoint, BoneJointControlPoint, BoneJointControlPoint, BoneJointControlPoint, BoneJointControlPoint]: ...

    @control_points.setter
    def control_points(self, arg: tuple[BoneJointControlPoint, BoneJointControlPoint, BoneJointControlPoint, BoneJointControlPoint, BoneJointControlPoint, BoneJointControlPoint, BoneJointControlPoint, BoneJointControlPoint], /) -> None: ...

    @property
    def degrees_of_freedom(self) -> BoneJointDofs: ...

    @degrees_of_freedom.setter
    def degrees_of_freedom(self, arg: BoneJointDofs, /) -> None: ...

    @property
    def zero_rotation(self) -> pymateria.Quaternion: ...

    @zero_rotation.setter
    def zero_rotation(self, arg: pymateria.Quaternion, /) -> None: ...

    @property
    def twist_axis(self) -> pymateria.Vector3f: ...

    @twist_axis.setter
    def twist_axis(self, arg: pymateria.Vector3f, /) -> None: ...

    @property
    def twist_limit_min(self) -> float: ...

    @twist_limit_min.setter
    def twist_limit_min(self, arg: float, /) -> None: ...

    @property
    def twist_limit_max(self) -> float: ...

    @twist_limit_max.setter
    def twist_limit_max(self, arg: float, /) -> None: ...

    @property
    def soft_limit_scale(self) -> float: ...

    @soft_limit_scale.setter
    def soft_limit_scale(self, arg: float, /) -> None: ...

    @property
    def use_twist_limits(self) -> bool: ...

    @use_twist_limits.setter
    def use_twist_limits(self, arg: bool, /) -> None: ...

    @property
    def use_euler_angles(self) -> bool: ...

    @use_euler_angles.setter
    def use_euler_angles(self, arg: bool, /) -> None: ...

    @property
    def use_per_control_point_twist_limits(self) -> bool: ...

    @use_per_control_point_twist_limits.setter
    def use_per_control_point_twist_limits(self, arg: bool, /) -> None: ...

class BoneTranslationLimit:
    def __init__(self) -> None: ...

    @property
    def bone_id(self) -> int: ...

    @bone_id.setter
    def bone_id(self, arg: int, /) -> None: ...

    @property
    def min(self) -> pymateria.Vector3f: ...

    @min.setter
    def min(self, arg: pymateria.Vector3f, /) -> None: ...

    @property
    def max(self) -> pymateria.Vector3f: ...

    @max.setter
    def max(self, arg: pymateria.Vector3f, /) -> None: ...

class BoneScaleLimit:
    def __init__(self) -> None: ...

    @property
    def bone_id(self) -> int: ...

    @bone_id.setter
    def bone_id(self, arg: int, /) -> None: ...

    @property
    def min(self) -> pymateria.Vector3f: ...

    @min.setter
    def min(self, arg: pymateria.Vector3f, /) -> None: ...

    @property
    def max(self) -> pymateria.Vector3f: ...

    @max.setter
    def max(self, arg: pymateria.Vector3f, /) -> None: ...

class Bone:
    def __init__(self) -> None: ...

    @property
    def id(self) -> int: ...

    @id.setter
    def id(self, arg: int, /) -> None: ...

    @property
    def name(self) -> str: ...

    @name.setter
    def name(self, arg: str, /) -> None: ...

    @property
    def default_rotation(self) -> pymateria.Quaternion: ...

    @default_rotation.setter
    def default_rotation(self, arg: pymateria.Quaternion, /) -> None: ...

    @property
    def default_translation(self) -> pymateria.Vector4f: ...

    @default_translation.setter
    def default_translation(self, arg: pymateria.Vector4f, /) -> None: ...

    @property
    def default_scale(self) -> pymateria.Vector4f: ...

    @default_scale.setter
    def default_scale(self, arg: pymateria.Vector4f, /) -> None: ...

    @property
    def degrees_of_freedom(self) -> int: ...

    @degrees_of_freedom.setter
    def degrees_of_freedom(self, arg: int, /) -> None: ...

    @property
    def rotation_limit(self) -> BoneRotationLimit | None: ...

    @rotation_limit.setter
    def rotation_limit(self, arg: BoneRotationLimit | None) -> None: ...

    @property
    def translation_limit(self) -> BoneTranslationLimit | None: ...

    @translation_limit.setter
    def translation_limit(self, arg: BoneTranslationLimit | None) -> None: ...

    @property
    def scale_limit(self) -> BoneScaleLimit | None: ...

    @scale_limit.setter
    def scale_limit(self, arg: BoneScaleLimit | None) -> None: ...

    @property
    def children(self) -> BoneList: ...

    @children.setter
    def children(self, arg: BoneList, /) -> None: ...

    def get_final_dofs(self) -> int: ...

    def get_signature_non_chiral(self) -> int: ...

class BoneList:
    @overload
    def __init__(self) -> None:
        """Default constructor"""

    @overload
    def __init__(self, arg: BoneList) -> None:
        """Copy constructor"""

    @overload
    def __init__(self, arg: Iterable[Bone], /) -> None:
        """Construct from an iterable object"""

    def __len__(self) -> int: ...

    def __bool__(self) -> bool:
        """Check whether the vector is nonempty"""

    def __repr__(self) -> str: ...

    def __iter__(self) -> Iterator[Bone]: ...

    @overload
    def __getitem__(self, arg: int, /) -> Bone: ...

    @overload
    def __getitem__(self, arg: slice, /) -> BoneList: ...

    def clear(self) -> None:
        """Remove all items from list."""

    def append(self, arg: Bone, /) -> None:
        """Append `arg` to the end of the list."""

    def insert(self, arg0: int, arg1: Bone, /) -> None:
        """Insert object `arg1` before index `arg0`."""

    def pop(self, index: int = -1) -> Bone:
        """Remove and return item at `index` (default last)."""

    def extend(self, arg: BoneList, /) -> None:
        """Extend `self` by appending elements from `arg`."""

    @overload
    def __setitem__(self, arg0: int, arg1: Bone, /) -> None: ...

    @overload
    def __setitem__(self, arg0: slice, arg1: BoneList, /) -> None: ...

    @overload
    def __delitem__(self, arg: int, /) -> None: ...

    @overload
    def __delitem__(self, arg: slice, /) -> None: ...

    def __eq__(self, arg: object, /) -> bool: ...

    def __ne__(self, arg: object, /) -> bool: ...

    @overload
    def __contains__(self, arg: Bone, /) -> bool: ...

    @overload
    def __contains__(self, arg: object, /) -> bool: ...

    def count(self, arg: Bone, /) -> int:
        """Return number of occurrences of `arg`."""

    def remove(self, arg: Bone, /) -> None:
        """Remove first occurrence of `arg`."""

    @property
    def signature(self) -> int: ...

    @property
    def non_chiral_signature(self) -> int: ...

    @property
    def comprehensive_signature(self) -> int: ...

class Skeleton:
    def __init__(self) -> None: ...

    @property
    def root_bone(self) -> Bone: ...

    @root_bone.setter
    def root_bone(self, arg: Bone, /) -> None: ...

    def get_bones(self) -> BoneList: ...

    @staticmethod
    def get_signature(arg: BoneList, /) -> int: ...

    @staticmethod
    def get_non_chiral_signature(arg: BoneList, /) -> int: ...

    @staticmethod
    def get_comprehensive_signature(arg: BoneList, /) -> int: ...

class LightFlashiness(enum.Enum):
    CONSTANT = 0

    RANDOM = 1

    RANDOM_OVERRIDE_IF_WET = 2

    ONCE_SECOND = 3

    TWICE_SECOND = 4

    FIVE_SECOND = 5

    RANDOM_FLASHINESS = 6

    OFF = 7

    UNUSED1 = 8

    ALARM = 9

    ON_WHEN_RAINING = 10

    CYCLE_1 = 11

    CYCLE_2 = 12

    CYCLE_3 = 13

    DISCO = 14

    CANDLE = 15

    PLANE = 16

    FIRE = 17

    THRESHOLD = 18

    ELECTRIC = 19

    STROBE = 20

class LightFlags(enum.Flag):
    INTERIOR_ONLY = 1

    EXTERIOR_ONLY = 2

    DONT_USE_IN_CUTSCENE = 4

    VEHICLE = 8

    FX = 16

    TEXTURE_PROJECTION = 32

    CAST_SHADOWS = 64

    CAST_STATIC_GEOM_SHADOWS = 128

    CAST_DYNAMIC_GEOM_SHADOWS = 256

    CALC_FROM_SUN = 512

    ENABLE_BUZZING = 1024

    FORCE_BUZZING = 2048

    DRAW_VOLUME = 4096

    NO_SPECULAR = 8192

    BOTH_INTERIOR_AND_EXTERIOR = 16384

    CORONA_ONLY = 32768

    NOT_IN_REFLECTION = 65536

    ONLY_IN_REFLECTION = 131072

    USE_CULL_PLANE = 262144

    USE_VOLUME_OUTER_COLOUR = 524288

    CAST_HIGHER_RES_SHADOWS = 1048576

    CAST_ONLY_LOWRES_SHADOWS = 2097152

    FAR_LOD_LIGHT = 4194304

    DONT_LIGHT_ALPHA = 8388608

    CAST_SHADOWS_IF_POSSIBLE = 16777216

    CUTSCENE = 33554432

    MOVING_LIGHT_SOURCE = 67108864

    USE_VEHICLE_TWIN = 134217728

    FORCE_MEDIUM_LOD_LIGHT = 268435456

    CORONA_ONLY_LOD_LIGHT = 536870912

    DELAY_RENDER = 1073741824

    ALREADY_TESTED_FOR_OCCLUSION = 2147483648

class LightType(enum.Enum):
    NONE = 0

    POINT = 1

    SPOT = 2

    CAPSULE = 4

    DIRECTIONAL = 8

    AO_VOLUME = 16

class TimeFlags(enum.Flag):
    HOUR_00 = 1

    HOUR_01 = 2

    HOUR_02 = 4

    HOUR_03 = 8

    HOUR_04 = 16

    HOUR_05 = 32

    HOUR_06 = 64

    HOUR_07 = 128

    HOUR_08 = 256

    HOUR_09 = 512

    HOUR_10 = 1024

    HOUR_11 = 2048

    HOUR_12 = 4096

    HOUR_13 = 8192

    HOUR_14 = 16384

    HOUR_15 = 32768

    HOUR_16 = 65536

    HOUR_17 = 131072

    HOUR_18 = 262144

    HOUR_19 = 524288

    HOUR_20 = 1048576

    HOUR_21 = 2097152

    HOUR_22 = 4194304

    HOUR_23 = 8388608

    DAY = 130944

    NIGHT = 14680191

    ALWAYS = 14811135

    FLIP_WHILE_VISIBLE = 16777216

class LightCullingPlane:
    def __init__(self) -> None: ...

    @property
    def normal(self) -> pymateria.Vector3f: ...

    @normal.setter
    def normal(self, arg: pymateria.Vector3f, /) -> None: ...

    @property
    def distance(self) -> float: ...

    @distance.setter
    def distance(self, arg: float, /) -> None: ...

class Light:
    def __init__(self) -> None: ...

    @property
    def position(self) -> pymateria.Vector3f: ...

    @position.setter
    def position(self, arg: pymateria.Vector3f, /) -> None: ...

    @property
    def falloff_exponent(self) -> float: ...

    @falloff_exponent.setter
    def falloff_exponent(self, arg: float, /) -> None: ...

    @property
    def color(self) -> pymateria.ColorRGB: ...

    @color.setter
    def color(self, arg: pymateria.ColorRGB, /) -> None: ...

    @property
    def flashiness(self) -> LightFlashiness: ...

    @flashiness.setter
    def flashiness(self, arg: LightFlashiness, /) -> None: ...

    @property
    def intensity(self) -> float: ...

    @intensity.setter
    def intensity(self, arg: float, /) -> None: ...

    @property
    def flags(self) -> LightFlags: ...

    @flags.setter
    def flags(self, arg: LightFlags, /) -> None: ...

    @property
    def bone_tag(self) -> int: ...

    @bone_tag.setter
    def bone_tag(self, arg: int, /) -> None: ...

    @property
    def type(self) -> LightType: ...

    @type.setter
    def type(self, arg: LightType, /) -> None: ...

    @property
    def group_id(self) -> int: ...

    @group_id.setter
    def group_id(self, arg: int, /) -> None: ...

    @property
    def time_flags(self) -> TimeFlags: ...

    @time_flags.setter
    def time_flags(self, arg: TimeFlags, /) -> None: ...

    @property
    def falloff(self) -> float: ...

    @falloff.setter
    def falloff(self, arg: float, /) -> None: ...

    @property
    def culling_plane(self) -> LightCullingPlane | None: ...

    @culling_plane.setter
    def culling_plane(self, arg: LightCullingPlane | None) -> None: ...

    @property
    def shadow_blur(self) -> int: ...

    @shadow_blur.setter
    def shadow_blur(self, arg: int, /) -> None: ...

    @property
    def shadow_near_clip(self) -> float: ...

    @shadow_near_clip.setter
    def shadow_near_clip(self, arg: float, /) -> None: ...

    @property
    def volume_intensity(self) -> float: ...

    @volume_intensity.setter
    def volume_intensity(self, arg: float, /) -> None: ...

    @property
    def volume_size_scale(self) -> float: ...

    @volume_size_scale.setter
    def volume_size_scale(self, arg: float, /) -> None: ...

    @property
    def volume_outer_color(self) -> pymateria.ColorRGB: ...

    @volume_outer_color.setter
    def volume_outer_color(self, arg: pymateria.ColorRGB, /) -> None: ...

    @property
    def volume_outer_intensity(self) -> float: ...

    @volume_outer_intensity.setter
    def volume_outer_intensity(self, arg: float, /) -> None: ...

    @property
    def volume_outer_exponent(self) -> float: ...

    @volume_outer_exponent.setter
    def volume_outer_exponent(self, arg: float, /) -> None: ...

    @property
    def light_fade_distance(self) -> int: ...

    @light_fade_distance.setter
    def light_fade_distance(self, arg: int, /) -> None: ...

    @property
    def shadow_fade_distance(self) -> int: ...

    @shadow_fade_distance.setter
    def shadow_fade_distance(self, arg: int, /) -> None: ...

    @property
    def specular_fade_distance(self) -> int: ...

    @specular_fade_distance.setter
    def specular_fade_distance(self, arg: int, /) -> None: ...

    @property
    def volumetric_fade_distance(self) -> int: ...

    @volumetric_fade_distance.setter
    def volumetric_fade_distance(self, arg: int, /) -> None: ...

    @property
    def light_hash(self) -> int: ...

    @light_hash.setter
    def light_hash(self, arg: int, /) -> None: ...

    @property
    def corona_size(self) -> float: ...

    @corona_size.setter
    def corona_size(self, arg: float, /) -> None: ...

    @property
    def corona_intensity(self) -> float: ...

    @corona_intensity.setter
    def corona_intensity(self, arg: float, /) -> None: ...

    @property
    def corona_zbias(self) -> float: ...

    @corona_zbias.setter
    def corona_zbias(self, arg: float, /) -> None: ...

    @property
    def direction(self) -> pymateria.Vector3f: ...

    @direction.setter
    def direction(self, arg: pymateria.Vector3f, /) -> None: ...

    @property
    def tangent(self) -> pymateria.Vector3f: ...

    @tangent.setter
    def tangent(self, arg: pymateria.Vector3f, /) -> None: ...

    @property
    def cone_inner_angle(self) -> float: ...

    @cone_inner_angle.setter
    def cone_inner_angle(self, arg: float, /) -> None: ...

    @property
    def cone_outer_angle(self) -> float: ...

    @cone_outer_angle.setter
    def cone_outer_angle(self, arg: float, /) -> None: ...

    @property
    def extents(self) -> pymateria.Vector3f: ...

    @extents.setter
    def extents(self, arg: pymateria.Vector3f, /) -> None: ...

    @property
    def projected_texture_key(self) -> int: ...

    @projected_texture_key.setter
    def projected_texture_key(self, arg: int, /) -> None: ...

class LightList:
    @overload
    def __init__(self) -> None:
        """Default constructor"""

    @overload
    def __init__(self, arg: LightList) -> None:
        """Copy constructor"""

    @overload
    def __init__(self, arg: Iterable[Light], /) -> None:
        """Construct from an iterable object"""

    def __len__(self) -> int: ...

    def __bool__(self) -> bool:
        """Check whether the vector is nonempty"""

    def __repr__(self) -> str: ...

    def __iter__(self) -> Iterator[Light]: ...

    @overload
    def __getitem__(self, arg: int, /) -> Light: ...

    @overload
    def __getitem__(self, arg: slice, /) -> LightList: ...

    def clear(self) -> None:
        """Remove all items from list."""

    def append(self, arg: Light, /) -> None:
        """Append `arg` to the end of the list."""

    def insert(self, arg0: int, arg1: Light, /) -> None:
        """Insert object `arg1` before index `arg0`."""

    def pop(self, index: int = -1) -> Light:
        """Remove and return item at `index` (default last)."""

    def extend(self, arg: LightList, /) -> None:
        """Extend `self` by appending elements from `arg`."""

    @overload
    def __setitem__(self, arg0: int, arg1: Light, /) -> None: ...

    @overload
    def __setitem__(self, arg0: slice, arg1: LightList, /) -> None: ...

    @overload
    def __delitem__(self, arg: int, /) -> None: ...

    @overload
    def __delitem__(self, arg: slice, /) -> None: ...

    def __eq__(self, arg: object, /) -> bool: ...

    def __ne__(self, arg: object, /) -> bool: ...

    @overload
    def __contains__(self, arg: Light, /) -> bool: ...

    @overload
    def __contains__(self, arg: object, /) -> bool: ...

    def count(self, arg: Light, /) -> int:
        """Return number of occurrences of `arg`."""

    def remove(self, arg: Light, /) -> None:
        """Remove first occurrence of `arg`."""

class ShaderDrawBucket(enum.Enum):
    OPAQUE = 0

    ALPHA = 1

    DECAL = 2

    CUTOUT = 3

    NOSPLASH = 4

    NOWATER = 5

    WATER = 6

    DISPLACEMENT_ALPHA = 7

    MODEL_DEFAULT = 8

    MODEL_SHADOW = 9

    MODEL_REFLECTION = 10

    MODEL_MIRROR = 11

    MODEL_WATER = 12

class PrimitiveType(enum.Enum):
    POINTS = 0

    LINES = 1

    LINE_STRIP = 2

    TRIS = 3

    STRI_STRIP = 4

    TRI_FAN = 5

    QUADS = 6

    RECTS = 7

    TRIS_ADJ = 8

class ModelFlags(enum.Flag):
    MODEL_RELATIVE = 1

    RESOURCED = 2

class LodType(enum.Enum):
    HIGH = 0

    MED = 1

    LOW = 2

    VLOW = 3

class MatrixSet:
    def __init__(self) -> None: ...

    @property
    def is_skinned(self) -> bool: ...

    @is_skinned.setter
    def is_skinned(self, arg: bool, /) -> None: ...

    @property
    def matrices(self) -> list[pymateria.Matrix43]: ...

    @matrices.setter
    def matrices(self, arg: Sequence[pymateria.Matrix43], /) -> None: ...

class ExtraBound:
    def __init__(self, bound: Bound | None = None, matrix: pymateria.Matrix34 = ...) -> None: ...

    @property
    def bound(self) -> Bound: ...

    @bound.setter
    def bound(self, arg: Bound | None) -> None: ...

    @property
    def matrix(self) -> pymateria.Matrix34: ...

    @matrix.setter
    def matrix(self, arg: pymateria.Matrix34, /) -> None: ...

class ExtraBoundList:
    @overload
    def __init__(self) -> None:
        """Default constructor"""

    @overload
    def __init__(self, arg: ExtraBoundList) -> None:
        """Copy constructor"""

    @overload
    def __init__(self, arg: Iterable[ExtraBound], /) -> None:
        """Construct from an iterable object"""

    def __len__(self) -> int: ...

    def __bool__(self) -> bool:
        """Check whether the vector is nonempty"""

    def __repr__(self) -> str: ...

    def __iter__(self) -> Iterator[ExtraBound]: ...

    @overload
    def __getitem__(self, arg: int, /) -> ExtraBound: ...

    @overload
    def __getitem__(self, arg: slice, /) -> ExtraBoundList: ...

    def clear(self) -> None:
        """Remove all items from list."""

    def append(self, arg: ExtraBound, /) -> None:
        """Append `arg` to the end of the list."""

    def insert(self, arg0: int, arg1: ExtraBound, /) -> None:
        """Insert object `arg1` before index `arg0`."""

    def pop(self, index: int = -1) -> ExtraBound:
        """Remove and return item at `index` (default last)."""

    def extend(self, arg: ExtraBoundList, /) -> None:
        """Extend `self` by appending elements from `arg`."""

    @overload
    def __setitem__(self, arg0: int, arg1: ExtraBound, /) -> None: ...

    @overload
    def __setitem__(self, arg0: slice, arg1: ExtraBoundList, /) -> None: ...

    @overload
    def __delitem__(self, arg: int, /) -> None: ...

    @overload
    def __delitem__(self, arg: slice, /) -> None: ...

    def __eq__(self, arg: object, /) -> bool: ...

    def __ne__(self, arg: object, /) -> bool: ...

    @overload
    def __contains__(self, arg: ExtraBound, /) -> bool: ...

    @overload
    def __contains__(self, arg: object, /) -> bool: ...

    def count(self, arg: ExtraBound, /) -> int:
        """Return number of occurrences of `arg`."""

    def remove(self, arg: ExtraBound, /) -> None:
        """Remove first occurrence of `arg`."""

class SkeletonType(enum.Enum):
    NONE = 0

    SKEL = 1

class FragmentTypeGroup:
    def __init__(self) -> None: ...

    @property
    def name(self) -> str: ...

    @name.setter
    def name(self, arg: str, /) -> None: ...

    @property
    def use_death_event_set(self) -> bool: ...

    @use_death_event_set.setter
    def use_death_event_set(self, arg: bool, /) -> None: ...

    @property
    def use_death_event_player(self) -> bool: ...

    @use_death_event_player.setter
    def use_death_event_player(self, arg: bool, /) -> None: ...

    @property
    def strength(self) -> float: ...

    @strength.setter
    def strength(self, arg: float, /) -> None: ...

    @property
    def force_transmission_scale_up(self) -> float: ...

    @force_transmission_scale_up.setter
    def force_transmission_scale_up(self, arg: float, /) -> None: ...

    @property
    def force_transmission_scale_down(self) -> float: ...

    @force_transmission_scale_down.setter
    def force_transmission_scale_down(self, arg: float, /) -> None: ...

    @property
    def joint_stiffness(self) -> float: ...

    @joint_stiffness.setter
    def joint_stiffness(self, arg: float, /) -> None: ...

    @property
    def min_soft_angle1(self) -> float: ...

    @min_soft_angle1.setter
    def min_soft_angle1(self, arg: float, /) -> None: ...

    @property
    def max_soft_angle1(self) -> float: ...

    @max_soft_angle1.setter
    def max_soft_angle1(self, arg: float, /) -> None: ...

    @property
    def max_soft_angle2(self) -> float: ...

    @max_soft_angle2.setter
    def max_soft_angle2(self, arg: float, /) -> None: ...

    @property
    def max_soft_angle3(self) -> float: ...

    @max_soft_angle3.setter
    def max_soft_angle3(self, arg: float, /) -> None: ...

    @property
    def rotation_speed(self) -> float: ...

    @rotation_speed.setter
    def rotation_speed(self, arg: float, /) -> None: ...

    @property
    def rotation_strength(self) -> float: ...

    @rotation_strength.setter
    def rotation_strength(self, arg: float, /) -> None: ...

    @property
    def restoring_strength(self) -> float: ...

    @restoring_strength.setter
    def restoring_strength(self, arg: float, /) -> None: ...

    @property
    def restoring_max_torque(self) -> float: ...

    @restoring_max_torque.setter
    def restoring_max_torque(self, arg: float, /) -> None: ...

    @property
    def latch_strength(self) -> float: ...

    @latch_strength.setter
    def latch_strength(self, arg: float, /) -> None: ...

    @property
    def total_undamaged_mass(self) -> float: ...

    @total_undamaged_mass.setter
    def total_undamaged_mass(self, arg: float, /) -> None: ...

    @property
    def total_damaged_mass(self) -> float: ...

    @total_damaged_mass.setter
    def total_damaged_mass(self, arg: float, /) -> None: ...

    @property
    def min_damage_force(self) -> float: ...

    @min_damage_force.setter
    def min_damage_force(self, arg: float, /) -> None: ...

    @property
    def damage_health(self) -> float: ...

    @damage_health.setter
    def damage_health(self, arg: float, /) -> None: ...

    @property
    def weapon_health(self) -> float: ...

    @weapon_health.setter
    def weapon_health(self, arg: float, /) -> None: ...

    @property
    def weapon_scale(self) -> float: ...

    @weapon_scale.setter
    def weapon_scale(self, arg: float, /) -> None: ...

    @property
    def vehicle_scale(self) -> float: ...

    @vehicle_scale.setter
    def vehicle_scale(self, arg: float, /) -> None: ...

    @property
    def ped_scale(self) -> float: ...

    @ped_scale.setter
    def ped_scale(self, arg: float, /) -> None: ...

    @property
    def ragdoll_scale(self) -> float: ...

    @ragdoll_scale.setter
    def ragdoll_scale(self, arg: float, /) -> None: ...

    @property
    def explosion_scale(self) -> float: ...

    @explosion_scale.setter
    def explosion_scale(self, arg: float, /) -> None: ...

    @property
    def object_scale(self) -> float: ...

    @object_scale.setter
    def object_scale(self, arg: float, /) -> None: ...

    @property
    def ped_inv_mass_scale(self) -> float: ...

    @ped_inv_mass_scale.setter
    def ped_inv_mass_scale(self, arg: float, /) -> None: ...

    @property
    def melee_scale(self) -> float: ...

    @melee_scale.setter
    def melee_scale(self, arg: float, /) -> None: ...

    @property
    def preset_applied(self) -> int: ...

    @preset_applied.setter
    def preset_applied(self, arg: int, /) -> None: ...

    @property
    def flags(self) -> int: ...

    @flags.setter
    def flags(self, arg: int, /) -> None: ...

    @property
    def glass_model_and_type(self) -> int: ...

    @glass_model_and_type.setter
    def glass_model_and_type(self, arg: int, /) -> None: ...

    @property
    def glass_pane_model_info_index(self) -> int: ...

    @glass_pane_model_info_index.setter
    def glass_pane_model_info_index(self, arg: int, /) -> None: ...

    @property
    def child_groups_pointers_index(self) -> int: ...

    @child_groups_pointers_index.setter
    def child_groups_pointers_index(self, arg: int, /) -> None: ...

    @property
    def parent_group_pointer_index(self) -> int: ...

    @parent_group_pointer_index.setter
    def parent_group_pointer_index(self, arg: int, /) -> None: ...

    @property
    def child_index(self) -> int: ...

    @child_index.setter
    def child_index(self, arg: int, /) -> None: ...

    @property
    def num_children(self) -> int: ...

    @num_children.setter
    def num_children(self, arg: int, /) -> None: ...

    @property
    def num_child_groups(self) -> int: ...

    @num_child_groups.setter
    def num_child_groups(self, arg: int, /) -> None: ...

    def __repr__(self) -> str: ...

class FragmentTypeGroupList:
    @overload
    def __init__(self) -> None:
        """Default constructor"""

    @overload
    def __init__(self, arg: FragmentTypeGroupList) -> None:
        """Copy constructor"""

    @overload
    def __init__(self, arg: Iterable[FragmentTypeGroup], /) -> None:
        """Construct from an iterable object"""

    def __len__(self) -> int: ...

    def __bool__(self) -> bool:
        """Check whether the vector is nonempty"""

    def __repr__(self) -> str: ...

    def __iter__(self) -> Iterator[FragmentTypeGroup]: ...

    @overload
    def __getitem__(self, arg: int, /) -> FragmentTypeGroup: ...

    @overload
    def __getitem__(self, arg: slice, /) -> FragmentTypeGroupList: ...

    def clear(self) -> None:
        """Remove all items from list."""

    def append(self, arg: FragmentTypeGroup, /) -> None:
        """Append `arg` to the end of the list."""

    def insert(self, arg0: int, arg1: FragmentTypeGroup, /) -> None:
        """Insert object `arg1` before index `arg0`."""

    def pop(self, index: int = -1) -> FragmentTypeGroup:
        """Remove and return item at `index` (default last)."""

    def extend(self, arg: FragmentTypeGroupList, /) -> None:
        """Extend `self` by appending elements from `arg`."""

    @overload
    def __setitem__(self, arg0: int, arg1: FragmentTypeGroup, /) -> None: ...

    @overload
    def __setitem__(self, arg0: slice, arg1: FragmentTypeGroupList, /) -> None: ...

    @overload
    def __delitem__(self, arg: int, /) -> None: ...

    @overload
    def __delitem__(self, arg: slice, /) -> None: ...

    def __eq__(self, arg: object, /) -> bool: ...

    def __ne__(self, arg: object, /) -> bool: ...

    @overload
    def __contains__(self, arg: FragmentTypeGroup, /) -> bool: ...

    @overload
    def __contains__(self, arg: object, /) -> bool: ...

    def count(self, arg: FragmentTypeGroup, /) -> int:
        """Return number of occurrences of `arg`."""

    def remove(self, arg: FragmentTypeGroup, /) -> None:
        """Remove first occurrence of `arg`."""

class FragmentPhJointType:
    @property
    def stiffness(self) -> float: ...

    @stiffness.setter
    def stiffness(self, arg: float, /) -> None: ...

    @property
    def enforce_acceded_limits(self) -> bool: ...

    @enforce_acceded_limits.setter
    def enforce_acceded_limits(self, arg: bool, /) -> None: ...

    @property
    def parent_link_index(self) -> int: ...

    @parent_link_index.setter
    def parent_link_index(self, arg: int, /) -> None: ...

    @property
    def child_link_index(self) -> int: ...

    @child_link_index.setter
    def child_link_index(self, arg: int, /) -> None: ...

    @property
    def orient_parent(self) -> pymateria.Matrix34: ...

    @orient_parent.setter
    def orient_parent(self, arg: pymateria.Matrix34, /) -> None: ...

    @property
    def orient_child(self) -> pymateria.Matrix34: ...

    @orient_child.setter
    def orient_child(self, arg: pymateria.Matrix34, /) -> None: ...

    @property
    def type(self) -> int: ...

class FragmentPhJointType1Dof(FragmentPhJointType):
    def __init__(self) -> None: ...

    @property
    def hard_angle_min(self) -> float: ...

    @hard_angle_min.setter
    def hard_angle_min(self, arg: float, /) -> None: ...

    @property
    def hard_angle_max(self) -> float: ...

    @hard_angle_max.setter
    def hard_angle_max(self, arg: float, /) -> None: ...

    @property
    def max_muscle_torque(self) -> float: ...

    @max_muscle_torque.setter
    def max_muscle_torque(self, arg: float, /) -> None: ...

    @property
    def min_muscle_torque(self) -> float: ...

    @min_muscle_torque.setter
    def min_muscle_torque(self, arg: float, /) -> None: ...

class FragmentPhJointType3Dof(FragmentPhJointType):
    def __init__(self) -> None: ...

    @property
    def hard_first_lean_angle_max(self) -> float: ...

    @hard_first_lean_angle_max.setter
    def hard_first_lean_angle_max(self, arg: float, /) -> None: ...

    @property
    def hard_second_lean_angle_max(self) -> float: ...

    @hard_second_lean_angle_max.setter
    def hard_second_lean_angle_max(self, arg: float, /) -> None: ...

    @property
    def hard_twist_angle_max(self) -> float: ...

    @hard_twist_angle_max.setter
    def hard_twist_angle_max(self, arg: float, /) -> None: ...

    @property
    def twist_offset(self) -> float: ...

    @twist_offset.setter
    def twist_offset(self, arg: float, /) -> None: ...

    @property
    def use_child_for_twist_axis(self) -> bool: ...

    @use_child_for_twist_axis.setter
    def use_child_for_twist_axis(self, arg: bool, /) -> None: ...

    @property
    def max_muscle_torque(self) -> pymateria.Vector3f: ...

    @max_muscle_torque.setter
    def max_muscle_torque(self, arg: pymateria.Vector3f, /) -> None: ...

    @property
    def min_muscle_torque(self) -> pymateria.Vector3f: ...

    @min_muscle_torque.setter
    def min_muscle_torque(self, arg: pymateria.Vector3f, /) -> None: ...

class FragmentPhJointTypePrismatic(FragmentPhJointType):
    def __init__(self) -> None: ...

    @property
    def hard_limit_min(self) -> float: ...

    @hard_limit_min.setter
    def hard_limit_min(self, arg: float, /) -> None: ...

    @property
    def hard_limit_max(self) -> float: ...

    @hard_limit_max.setter
    def hard_limit_max(self, arg: float, /) -> None: ...

    @property
    def max_muscle_force(self) -> float: ...

    @max_muscle_force.setter
    def max_muscle_force(self, arg: float, /) -> None: ...

    @property
    def min_muscle_force(self) -> float: ...

    @min_muscle_force.setter
    def min_muscle_force(self, arg: float, /) -> None: ...

class FragmentPhArticulatedBodyNode:
    def __init__(self) -> None: ...

    @property
    def joint_type(self) -> FragmentPhJointType: ...

    @joint_type.setter
    def joint_type(self, arg: FragmentPhJointType, /) -> None: ...

    @property
    def parent_index(self) -> int: ...

    @parent_index.setter
    def parent_index(self, arg: int, /) -> None: ...

    @property
    def ang_inertia(self) -> pymateria.Vector3f: ...

    @ang_inertia.setter
    def ang_inertia(self, arg: pymateria.Vector3f, /) -> None: ...

    @property
    def mass(self) -> float: ...

    @mass.setter
    def mass(self, arg: float, /) -> None: ...

class FragmentPhArticulatedBodyNodeList:
    @overload
    def __init__(self) -> None:
        """Default constructor"""

    @overload
    def __init__(self, arg: FragmentPhArticulatedBodyNodeList) -> None:
        """Copy constructor"""

    @overload
    def __init__(self, arg: Iterable[FragmentPhArticulatedBodyNode], /) -> None:
        """Construct from an iterable object"""

    def __len__(self) -> int: ...

    def __bool__(self) -> bool:
        """Check whether the vector is nonempty"""

    def __repr__(self) -> str: ...

    def __iter__(self) -> Iterator[FragmentPhArticulatedBodyNode]: ...

    @overload
    def __getitem__(self, arg: int, /) -> FragmentPhArticulatedBodyNode: ...

    @overload
    def __getitem__(self, arg: slice, /) -> FragmentPhArticulatedBodyNodeList: ...

    def clear(self) -> None:
        """Remove all items from list."""

    def append(self, arg: FragmentPhArticulatedBodyNode, /) -> None:
        """Append `arg` to the end of the list."""

    def insert(self, arg0: int, arg1: FragmentPhArticulatedBodyNode, /) -> None:
        """Insert object `arg1` before index `arg0`."""

    def pop(self, index: int = -1) -> FragmentPhArticulatedBodyNode:
        """Remove and return item at `index` (default last)."""

    def extend(self, arg: FragmentPhArticulatedBodyNodeList, /) -> None:
        """Extend `self` by appending elements from `arg`."""

    @overload
    def __setitem__(self, arg0: int, arg1: FragmentPhArticulatedBodyNode, /) -> None: ...

    @overload
    def __setitem__(self, arg0: slice, arg1: FragmentPhArticulatedBodyNodeList, /) -> None: ...

    @overload
    def __delitem__(self, arg: int, /) -> None: ...

    @overload
    def __delitem__(self, arg: slice, /) -> None: ...

class FragmentPhArticulatedBodyType:
    def __init__(self) -> None: ...

    @property
    def nodes(self) -> FragmentPhArticulatedBodyNodeList: ...

    @nodes.setter
    def nodes(self, arg: FragmentPhArticulatedBodyNodeList, /) -> None: ...

    @property
    def gravity_factor(self) -> float: ...

    @gravity_factor.setter
    def gravity_factor(self, arg: float, /) -> None: ...

class FragmentPhArchetypeDamp:
    def __init__(self) -> None: ...

    @property
    def filename(self) -> str: ...

    @filename.setter
    def filename(self, arg: str, /) -> None: ...

    @property
    def bounds(self) -> Bound: ...

    @bounds.setter
    def bounds(self, arg: Bound, /) -> None: ...

    @property
    def type_flags(self) -> CollisionFlags: ...

    @type_flags.setter
    def type_flags(self, arg: CollisionFlags, /) -> None: ...

    @property
    def include_flags(self) -> CollisionFlags: ...

    @include_flags.setter
    def include_flags(self, arg: CollisionFlags, /) -> None: ...

    @property
    def property_flags(self) -> int: ...

    @property_flags.setter
    def property_flags(self, arg: int, /) -> None: ...

    @property
    def mass(self) -> float: ...

    @mass.setter
    def mass(self, arg: float, /) -> None: ...

    @property
    def inv_mass(self) -> float: ...

    @inv_mass.setter
    def inv_mass(self, arg: float, /) -> None: ...

    @property
    def gravity_factor(self) -> float: ...

    @gravity_factor.setter
    def gravity_factor(self, arg: float, /) -> None: ...

    @property
    def max_speed(self) -> float: ...

    @max_speed.setter
    def max_speed(self, arg: float, /) -> None: ...

    @property
    def max_ang_speed(self) -> float: ...

    @max_ang_speed.setter
    def max_ang_speed(self, arg: float, /) -> None: ...

    @property
    def buoyancy_factor(self) -> float: ...

    @buoyancy_factor.setter
    def buoyancy_factor(self, arg: float, /) -> None: ...

    @property
    def ang_inertia(self) -> pymateria.Vector3f: ...

    @ang_inertia.setter
    def ang_inertia(self, arg: pymateria.Vector3f, /) -> None: ...

    @property
    def inv_ang_inertia(self) -> pymateria.Vector3f: ...

    @inv_ang_inertia.setter
    def inv_ang_inertia(self, arg: pymateria.Vector3f, /) -> None: ...

    @property
    def damping_constant(self) -> tuple[pymateria.Vector3f, pymateria.Vector3f, pymateria.Vector3f, pymateria.Vector3f, pymateria.Vector3f, pymateria.Vector3f]: ...

    @damping_constant.setter
    def damping_constant(self, arg: tuple[pymateria.Vector3f, pymateria.Vector3f, pymateria.Vector3f, pymateria.Vector3f, pymateria.Vector3f, pymateria.Vector3f], /) -> None: ...

class FragmentEnvClothTuning:
    def __init__(self) -> None: ...

    @property
    def rotation_rate(self) -> float: ...

    @rotation_rate.setter
    def rotation_rate(self, arg: float, /) -> None: ...

    @property
    def angle_threshold(self) -> float: ...

    @angle_threshold.setter
    def angle_threshold(self, arg: float, /) -> None: ...

    @property
    def flags(self) -> int: ...

    @flags.setter
    def flags(self, arg: int, /) -> None: ...

    @property
    def weight(self) -> float: ...

    @weight.setter
    def weight(self, arg: float, /) -> None: ...

    @property
    def distance_threshold(self) -> float: ...

    @distance_threshold.setter
    def distance_threshold(self, arg: float, /) -> None: ...

    @property
    def extra_force(self) -> pymateria.Vector4f: ...

    @extra_force.setter
    def extra_force(self, arg: pymateria.Vector4f, /) -> None: ...

    @property
    def pin_vert(self) -> int: ...

    @pin_vert.setter
    def pin_vert(self, arg: int, /) -> None: ...

    @property
    def non_pin_vert0(self) -> int: ...

    @non_pin_vert0.setter
    def non_pin_vert0(self, arg: int, /) -> None: ...

    @property
    def non_pin_vert1(self) -> int: ...

    @non_pin_vert1.setter
    def non_pin_vert1(self, arg: int, /) -> None: ...

class Window:
    def __init__(self) -> None: ...

    @property
    def basis(self) -> pymateria.Matrix34: ...

    @basis.setter
    def basis(self, arg: pymateria.Matrix34, /) -> None: ...

    @property
    def tag(self) -> int: ...

    @tag.setter
    def tag(self, arg: int, /) -> None: ...

    @property
    def component_id(self) -> int: ...

    @component_id.setter
    def component_id(self, arg: int, /) -> None: ...

    @property
    def geom_index(self) -> int: ...

    @geom_index.setter
    def geom_index(self, arg: int, /) -> None: ...

    @property
    def data_cols(self) -> int: ...

    @data_cols.setter
    def data_cols(self, arg: int, /) -> None: ...

    @property
    def data_rows(self) -> int: ...

    @data_rows.setter
    def data_rows(self, arg: int, /) -> None: ...

    @property
    def scale(self) -> float: ...

    @scale.setter
    def scale(self, arg: float, /) -> None: ...

    @property
    def flags(self) -> int: ...

    @flags.setter
    def flags(self, arg: int, /) -> None: ...

    @property
    def data_rle(self) -> bytes: ...

    @data_rle.setter
    def data_rle(self, arg: bytes, /) -> None: ...

    @property
    def min(self) -> float: ...

    @min.setter
    def min(self, arg: float, /) -> None: ...

    @property
    def max(self) -> float: ...

    @max.setter
    def max(self, arg: float, /) -> None: ...

class WindowProxy:
    def __init__(self) -> None: ...

    @property
    def basis(self) -> pymateria.Matrix34: ...

    @basis.setter
    def basis(self, arg: pymateria.Matrix34, /) -> None: ...

    @property
    def component_id(self) -> int: ...

    @component_id.setter
    def component_id(self, arg: int, /) -> None: ...

    @property
    def data_w(self) -> int: ...

    @data_w.setter
    def data_w(self, arg: int, /) -> None: ...

    @property
    def data_h(self) -> int: ...

    @data_h.setter
    def data_h(self, arg: int, /) -> None: ...

    @property
    def data(self) -> list[float]: ...

    @data.setter
    def data(self, arg: Sequence[float], /) -> None: ...

    @property
    def window(self) -> Window: ...

    @window.setter
    def window(self, arg: Window, /) -> None: ...

class WindowProxyList:
    @overload
    def __init__(self) -> None:
        """Default constructor"""

    @overload
    def __init__(self, arg: WindowProxyList) -> None:
        """Copy constructor"""

    @overload
    def __init__(self, arg: Iterable[WindowProxy], /) -> None:
        """Construct from an iterable object"""

    def __len__(self) -> int: ...

    def __bool__(self) -> bool:
        """Check whether the vector is nonempty"""

    def __repr__(self) -> str: ...

    def __iter__(self) -> Iterator[WindowProxy]: ...

    @overload
    def __getitem__(self, arg: int, /) -> WindowProxy: ...

    @overload
    def __getitem__(self, arg: slice, /) -> WindowProxyList: ...

    def clear(self) -> None:
        """Remove all items from list."""

    def append(self, arg: WindowProxy, /) -> None:
        """Append `arg` to the end of the list."""

    def insert(self, arg0: int, arg1: WindowProxy, /) -> None:
        """Insert object `arg1` before index `arg0`."""

    def pop(self, index: int = -1) -> WindowProxy:
        """Remove and return item at `index` (default last)."""

    def extend(self, arg: WindowProxyList, /) -> None:
        """Extend `self` by appending elements from `arg`."""

    @overload
    def __setitem__(self, arg0: int, arg1: WindowProxy, /) -> None: ...

    @overload
    def __setitem__(self, arg0: slice, arg1: WindowProxyList, /) -> None: ...

    @overload
    def __delitem__(self, arg: int, /) -> None: ...

    @overload
    def __delitem__(self, arg: slice, /) -> None: ...

class EdgeData:
    def __init__(self) -> None: ...

    @property
    def vert_index1(self) -> int: ...

    @vert_index1.setter
    def vert_index1(self, arg: int, /) -> None: ...

    @property
    def vert_index2(self) -> int: ...

    @vert_index2.setter
    def vert_index2(self, arg: int, /) -> None: ...

    @property
    def edge_length(self) -> float: ...

    @edge_length.setter
    def edge_length(self, arg: float, /) -> None: ...

    @property
    def weight(self) -> float: ...

    @weight.setter
    def weight(self, arg: float, /) -> None: ...

    @property
    def compression_weight(self) -> float: ...

    @compression_weight.setter
    def compression_weight(self, arg: float, /) -> None: ...

class VerletCloth:
    def __init__(self) -> None: ...

    @property
    def bb_min(self) -> pymateria.Vector4f: ...

    @bb_min.setter
    def bb_min(self, arg: pymateria.Vector4f, /) -> None: ...

    @property
    def bb_max(self) -> pymateria.Vector4f: ...

    @bb_max.setter
    def bb_max(self, arg: pymateria.Vector4f, /) -> None: ...

    @property
    def vert_positions(self) -> list[pymateria.Vector3f]: ...

    @vert_positions.setter
    def vert_positions(self, arg: Sequence[pymateria.Vector3f], /) -> None: ...

    @property
    def vert_normals(self) -> list[pymateria.Vector3f]: ...

    @vert_normals.setter
    def vert_normals(self, arg: Sequence[pymateria.Vector3f], /) -> None: ...

    @property
    def num_pinned_verts(self) -> int: ...

    @num_pinned_verts.setter
    def num_pinned_verts(self, arg: int, /) -> None: ...

    @property
    def max_delta_length(self) -> float: ...

    @max_delta_length.setter
    def max_delta_length(self, arg: float, /) -> None: ...

    @property
    def niterations(self) -> int: ...

    @niterations.setter
    def niterations(self, arg: int, /) -> None: ...

    @property
    def edge_data(self) -> list[EdgeData]: ...

    @edge_data.setter
    def edge_data(self, arg: Sequence[EdgeData], /) -> None: ...

    @property
    def custom_edge_data(self) -> list[EdgeData]: ...

    @custom_edge_data.setter
    def custom_edge_data(self, arg: Sequence[EdgeData], /) -> None: ...

    @property
    def bits(self) -> list[int]: ...

    @bits.setter
    def bits(self, arg: Sequence[int], /) -> None: ...

    @property
    def cloth_weight(self) -> float: ...

    @cloth_weight.setter
    def cloth_weight(self, arg: float, /) -> None: ...

    @property
    def switch_distance_up(self) -> float: ...

    @switch_distance_up.setter
    def switch_distance_up(self, arg: float, /) -> None: ...

    @property
    def switch_distance_down(self) -> float: ...

    @switch_distance_down.setter
    def switch_distance_down(self, arg: float, /) -> None: ...

    @property
    def flags(self) -> int: ...

    @flags.setter
    def flags(self, arg: int, /) -> None: ...

    @property
    def custom_bound(self) -> Bound: ...

    @custom_bound.setter
    def custom_bound(self, arg: Bound | None) -> None: ...

class VerletClothList:
    @overload
    def __init__(self) -> None:
        """Default constructor"""

    @overload
    def __init__(self, arg: VerletClothList) -> None:
        """Copy constructor"""

    @overload
    def __init__(self, arg: Iterable[VerletCloth], /) -> None:
        """Construct from an iterable object"""

    def __len__(self) -> int: ...

    def __bool__(self) -> bool:
        """Check whether the vector is nonempty"""

    def __repr__(self) -> str: ...

    def __iter__(self) -> Iterator[VerletCloth]: ...

    @overload
    def __getitem__(self, arg: int, /) -> VerletCloth: ...

    @overload
    def __getitem__(self, arg: slice, /) -> VerletClothList: ...

    def clear(self) -> None:
        """Remove all items from list."""

    def append(self, arg: VerletCloth, /) -> None:
        """Append `arg` to the end of the list."""

    def insert(self, arg0: int, arg1: VerletCloth, /) -> None:
        """Insert object `arg1` before index `arg0`."""

    def pop(self, index: int = -1) -> VerletCloth:
        """Remove and return item at `index` (default last)."""

    def extend(self, arg: VerletClothList, /) -> None:
        """Extend `self` by appending elements from `arg`."""

    @overload
    def __setitem__(self, arg0: int, arg1: VerletCloth, /) -> None: ...

    @overload
    def __setitem__(self, arg0: slice, arg1: VerletClothList, /) -> None: ...

    @overload
    def __delitem__(self, arg: int, /) -> None: ...

    @overload
    def __delitem__(self, arg: slice, /) -> None: ...

    def __eq__(self, arg: object, /) -> bool: ...

    def __ne__(self, arg: object, /) -> bool: ...

    @overload
    def __contains__(self, arg: VerletCloth, /) -> bool: ...

    @overload
    def __contains__(self, arg: object, /) -> bool: ...

    def count(self, arg: VerletCloth, /) -> int:
        """Return number of occurrences of `arg`."""

    def remove(self, arg: VerletCloth, /) -> None:
        """Remove first occurrence of `arg`."""

class ClothBridgeSimGFX:
    def __init__(self) -> None: ...

    @property
    def verts(self) -> list[int]: ...

    @verts.setter
    def verts(self, arg: Sequence[int], /) -> None: ...

    @property
    def pin_radius(self) -> dict[int, list[float]]: ...

    @pin_radius.setter
    def pin_radius(self, arg: Mapping[int, Sequence[float]], /) -> None: ...

    @property
    def vertex_weight(self) -> dict[int, list[float]]: ...

    @vertex_weight.setter
    def vertex_weight(self, arg: Mapping[int, Sequence[float]], /) -> None: ...

    @property
    def inflation_scale(self) -> dict[int, list[float]]: ...

    @inflation_scale.setter
    def inflation_scale(self, arg: Mapping[int, Sequence[float]], /) -> None: ...

    @property
    def cloth_display_map(self) -> dict[int, list[int]]: ...

    @cloth_display_map.setter
    def cloth_display_map(self, arg: Mapping[int, Sequence[int]], /) -> None: ...

    @property
    def pinnable_verts(self) -> list[int]: ...

    @pinnable_verts.setter
    def pinnable_verts(self, arg: Sequence[int], /) -> None: ...

class MorphData:
    def __init__(self) -> None: ...

    @property
    def weights(self) -> list[pymateria.Vector4f]: ...

    @weights.setter
    def weights(self, arg: Sequence[pymateria.Vector4f], /) -> None: ...

    @property
    def vtx_index(self) -> list[int]: ...

    @vtx_index.setter
    def vtx_index(self, arg: Sequence[int], /) -> None: ...

    @property
    def morph_index0(self) -> list[int]: ...

    @morph_index0.setter
    def morph_index0(self, arg: Sequence[int], /) -> None: ...

    @property
    def morph_index1(self) -> list[int]: ...

    @morph_index1.setter
    def morph_index1(self, arg: Sequence[int], /) -> None: ...

    @property
    def morph_index2(self) -> list[int]: ...

    @morph_index2.setter
    def morph_index2(self, arg: Sequence[int], /) -> None: ...

class MorphMapData:
    def __init__(self) -> None: ...

    @property
    def mmap(self) -> dict[int, MorphData]: ...

    @mmap.setter
    def mmap(self, arg: Mapping[int, MorphData], /) -> None: ...

    @property
    def imap(self) -> dict[int, list[int]]: ...

    @imap.setter
    def imap(self, arg: Mapping[int, Sequence[int]], /) -> None: ...

    @property
    def count(self) -> int: ...

    @count.setter
    def count(self, arg: int, /) -> None: ...

class MorphController:
    def __init__(self) -> None: ...

    @property
    def map_data(self) -> dict[int, MorphMapData]: ...

    @map_data.setter
    def map_data(self, arg: Mapping[int, MorphMapData], /) -> None: ...

class ClothController:
    def __init__(self) -> None: ...

    @property
    def bridge_sim_gfx(self) -> ClothBridgeSimGFX: ...

    @bridge_sim_gfx.setter
    def bridge_sim_gfx(self, arg: ClothBridgeSimGFX | None) -> None: ...

    @property
    def morph_controller(self) -> MorphController: ...

    @morph_controller.setter
    def morph_controller(self, arg: MorphController | None) -> None: ...

    @property
    def cloth(self) -> VerletClothList: ...

    @cloth.setter
    def cloth(self, arg: VerletClothList, /) -> None: ...

    @property
    def flags(self) -> int: ...

    @flags.setter
    def flags(self, arg: int, /) -> None: ...

    @property
    def name(self) -> CombinedHashString: ...

    @name.setter
    def name(self, arg: CombinedHashString, /) -> None: ...

class BindingInfo:
    @overload
    def __init__(self) -> None: ...

    @overload
    def __init__(self, weights: pymateria.Vector4f, indices: tuple[int, int, int, int]) -> None: ...

    @property
    def weights(self) -> pymateria.Vector4f: ...

    @weights.setter
    def weights(self, arg: pymateria.Vector4f, /) -> None: ...

    @property
    def indices(self) -> tuple[int, int, int, int]: ...

    @indices.setter
    def indices(self, arg: tuple[int, int, int, int], /) -> None: ...

class CharacterClothController(ClothController):
    def __init__(self) -> None: ...

    @property
    def pinning_radius_scale(self) -> float: ...

    @pinning_radius_scale.setter
    def pinning_radius_scale(self, arg: float, /) -> None: ...

    @property
    def indices(self) -> list[int]: ...

    @indices.setter
    def indices(self, arg: Sequence[int], /) -> None: ...

    @property
    def position(self) -> list[pymateria.Vector4f]: ...

    @position.setter
    def position(self, arg: Sequence[pymateria.Vector4f], /) -> None: ...

    @property
    def pin_radius_threshold(self) -> float: ...

    @pin_radius_threshold.setter
    def pin_radius_threshold(self, arg: float, /) -> None: ...

    @property
    def bone_id(self) -> list[int]: ...

    @bone_id.setter
    def bone_id(self, arg: Sequence[int], /) -> None: ...

    @property
    def bone_index(self) -> list[int]: ...

    @bone_index.setter
    def bone_index(self, arg: Sequence[int], /) -> None: ...

    @property
    def binding_info(self) -> list[BindingInfo]: ...

    @binding_info.setter
    def binding_info(self, arg: Sequence[BindingInfo], /) -> None: ...

    @property
    def force_pin(self) -> int: ...

    @force_pin.setter
    def force_pin(self, arg: int, /) -> None: ...

    @property
    def flags(self) -> int: ...

    @flags.setter
    def flags(self, arg: int, /) -> None: ...

    @property
    def package_index(self) -> int: ...

    @package_index.setter
    def package_index(self, arg: int, /) -> None: ...

    @property
    def wind_scale(self) -> float: ...

    @wind_scale.setter
    def wind_scale(self, arg: float, /) -> None: ...

class CharacterCloth:
    def __init__(self) -> None: ...

    @property
    def poses(self) -> list[pymateria.Vector3f]: ...

    @poses.setter
    def poses(self, arg: Sequence[pymateria.Vector3f], /) -> None: ...

    @property
    def controller(self) -> CharacterClothController: ...

    @controller.setter
    def controller(self, arg: CharacterClothController | None) -> None: ...

    @property
    def composite_bounds(self) -> BoundComposite: ...

    @composite_bounds.setter
    def composite_bounds(self, arg: BoundComposite | None) -> None: ...

    @property
    def bone_id(self) -> list[int]: ...

    @bone_id.setter
    def bone_id(self, arg: Sequence[int], /) -> None: ...

    @property
    def bone_index(self) -> list[int]: ...

    @bone_index.setter
    def bone_index(self, arg: Sequence[int], /) -> None: ...

    @property
    def force(self) -> pymateria.Vector3f: ...

    @force.setter
    def force(self, arg: pymateria.Vector3f, /) -> None: ...

    @property
    def parent_matrix(self) -> pymateria.Matrix34: ...

    @parent_matrix.setter
    def parent_matrix(self, arg: pymateria.Matrix34, /) -> None: ...

    @property
    def entity_vertices_ptr(self) -> pymateria.Vector3f: ...

    @entity_vertices_ptr.setter
    def entity_vertices_ptr(self, arg: pymateria.Vector3f, /) -> None: ...

    @property
    def entity_parent_matrix_ptr(self) -> pymateria.Matrix34: ...

    @entity_parent_matrix_ptr.setter
    def entity_parent_matrix_ptr(self, arg: pymateria.Matrix34, /) -> None: ...

    @property
    def bound_composite_ref(self) -> int: ...

    @bound_composite_ref.setter
    def bound_composite_ref(self, arg: int, /) -> None: ...

    @property
    def character_cloth_type(self) -> int: ...

    @character_cloth_type.setter
    def character_cloth_type(self, arg: int, /) -> None: ...

    @property
    def is_active(self) -> bool: ...

    @is_active.setter
    def is_active(self, arg: bool, /) -> None: ...

    @property
    def negate_force(self) -> bool: ...

    @negate_force.setter
    def negate_force(self, arg: bool, /) -> None: ...

    @property
    def lock_counter(self) -> int: ...

    @lock_counter.setter
    def lock_counter(self, arg: int, /) -> None: ...

class ClothDictionary:
    def __init__(self) -> None: ...

    class Map:
        @overload
        def __init__(self) -> None:
            """Default constructor"""

        @overload
        def __init__(self, arg: ClothDictionary.Map) -> None:
            """Copy constructor"""

        @overload
        def __init__(self, arg: dict[HashString, CharacterCloth], /) -> None:
            """Construct from a dictionary"""

        def __len__(self) -> int: ...

        def __bool__(self) -> bool:
            """Check whether the map is nonempty"""

        def __repr__(self) -> str: ...

        @overload
        def __contains__(self, arg: HashString, /) -> bool: ...

        @overload
        def __contains__(self, arg: object, /) -> bool: ...

        def __iter__(self) -> Iterator[HashString]: ...

        def __getitem__(self, arg: HashString, /) -> CharacterCloth: ...

        def __delitem__(self, arg: HashString, /) -> None: ...

        def clear(self) -> None:
            """Remove all items"""

        def __setitem__(self, arg0: HashString, arg1: CharacterCloth, /) -> None: ...

        def update(self, arg: ClothDictionary.Map, /) -> None:
            """Update the map with element from `arg`"""

        def __eq__(self, arg: object, /) -> bool: ...

        def __ne__(self, arg: object, /) -> bool: ...

        class ItemView:
            def __len__(self) -> int: ...

            def __iter__(self) -> Iterator[tuple[HashString, CharacterCloth]]: ...

        class KeyView:
            @overload
            def __contains__(self, arg: HashString, /) -> bool: ...

            @overload
            def __contains__(self, arg: object, /) -> bool: ...

            def __len__(self) -> int: ...

            def __iter__(self) -> Iterator[HashString]: ...

        class ValueView:
            def __len__(self) -> int: ...

            def __iter__(self) -> Iterator[CharacterCloth]: ...

        def keys(self) -> ClothDictionary.Map.KeyView:
            """Returns an iterable view of the map's keys."""

        def values(self) -> ClothDictionary.Map.ValueView:
            """Returns an iterable view of the map's values."""

        def items(self) -> ClothDictionary.Map.ItemView:
            """Returns an iterable view of the map's items."""

    @property
    def cloths(self) -> ClothDictionary.Map: ...

    @cloths.setter
    def cloths(self, arg: ClothDictionary.Map, /) -> None: ...

    class DeserializationResult(pymateria.SharedResult):
        def __init__(self) -> None: ...

        @property
        def result(self) -> ClothDictionary: ...

        @result.setter
        def result(self, arg: ClothDictionary, /) -> None: ...

        @property
        def deserializer(self) -> pymateria.rsc7.Deserializer: ...

    RSC_VERSION: int = ...
    """Resource version of this asset format."""

    @overload
    @staticmethod
    def import_rsc(file_path: str | os.PathLike, settings: pymateria.ImportSettings | None = None) -> ClothDictionary.DeserializationResult: ...

    @overload
    @staticmethod
    def import_rsc(stream: io.IOBase, settings: pymateria.ImportSettings | None = None) -> ClothDictionary.DeserializationResult: ...

    @overload
    @staticmethod
    def export_rsc(instance: ClothDictionary, file_path: str | os.PathLike, settings: pymateria.ExportSettings | None = None) -> pymateria.SerializationResultRsc7: ...

    @overload
    @staticmethod
    def export_rsc(instance: ClothDictionary, stream: io.IOBase, settings: pymateria.ExportSettings | None = None) -> pymateria.SerializationResultRsc7: ...

class Extension:
    @property
    def name(self) -> CombinedHashString: ...

    @name.setter
    def name(self, arg: CombinedHashString, /) -> None: ...

    @property
    def offset_position(self) -> pymateria.Vector3f: ...

    @offset_position.setter
    def offset_position(self, arg: pymateria.Vector3f, /) -> None: ...

class ExtensionList:
    @overload
    def __init__(self) -> None:
        """Default constructor"""

    @overload
    def __init__(self, arg: ExtensionList) -> None:
        """Copy constructor"""

    @overload
    def __init__(self, arg: Iterable[Extension], /) -> None:
        """Construct from an iterable object"""

    def __len__(self) -> int: ...

    def __bool__(self) -> bool:
        """Check whether the vector is nonempty"""

    def __repr__(self) -> str: ...

    def __iter__(self) -> Iterator[Extension]: ...

    @overload
    def __getitem__(self, arg: int, /) -> Extension: ...

    @overload
    def __getitem__(self, arg: slice, /) -> ExtensionList: ...

    def clear(self) -> None:
        """Remove all items from list."""

    def append(self, arg: Extension, /) -> None:
        """Append `arg` to the end of the list."""

    def insert(self, arg0: int, arg1: Extension, /) -> None:
        """Insert object `arg1` before index `arg0`."""

    def pop(self, index: int = -1) -> Extension:
        """Remove and return item at `index` (default last)."""

    def extend(self, arg: ExtensionList, /) -> None:
        """Extend `self` by appending elements from `arg`."""

    @overload
    def __setitem__(self, arg0: int, arg1: Extension, /) -> None: ...

    @overload
    def __setitem__(self, arg0: slice, arg1: ExtensionList, /) -> None: ...

    @overload
    def __delitem__(self, arg: int, /) -> None: ...

    @overload
    def __delitem__(self, arg: slice, /) -> None: ...

    def __eq__(self, arg: object, /) -> bool: ...

    def __ne__(self, arg: object, /) -> bool: ...

    @overload
    def __contains__(self, arg: Extension, /) -> bool: ...

    @overload
    def __contains__(self, arg: object, /) -> bool: ...

    def count(self, arg: Extension, /) -> int:
        """Return number of occurrences of `arg`."""

    def remove(self, arg: Extension, /) -> None:
        """Remove first occurrence of `arg`."""

class LadderMaterialType(enum.Enum):
    METAL_SOLID_LADDER = 0

    METAL_LIGHT_LADDER = 1

    WOODEN_LADDER = 2

class WindDisturbanceType(enum.Enum):
    HEMISPHERE = 0

class LightShaftDensityType(enum.Enum):
    CONSTANT = 0

    SOFT = 1

    SOFT_SHADOW = 2

    SOFT_SHADOW_HD = 3

    LINEAR = 4

    LINEAR_GRADIENT = 5

    QUADRATIC = 6

    QUADRATIC_GRADIENT = 7

class LightShaftVolumeType(enum.Enum):
    SHAFT = 0

    CYLINDER = 1

class SpawnPointAvailability(enum.Enum):
    BOTH = 0

    ONLY_SP = 1

    ONLY_MP = 2

class LightDefinition(Light):
    def __init__(self) -> None: ...

class LightDefinitionList:
    @overload
    def __init__(self) -> None:
        """Default constructor"""

    @overload
    def __init__(self, arg: LightDefinitionList) -> None:
        """Copy constructor"""

    @overload
    def __init__(self, arg: Iterable[LightDefinition], /) -> None:
        """Construct from an iterable object"""

    def __len__(self) -> int: ...

    def __bool__(self) -> bool:
        """Check whether the vector is nonempty"""

    def __repr__(self) -> str: ...

    def __iter__(self) -> Iterator[LightDefinition]: ...

    @overload
    def __getitem__(self, arg: int, /) -> LightDefinition: ...

    @overload
    def __getitem__(self, arg: slice, /) -> LightDefinitionList: ...

    def clear(self) -> None:
        """Remove all items from list."""

    def append(self, arg: LightDefinition, /) -> None:
        """Append `arg` to the end of the list."""

    def insert(self, arg0: int, arg1: LightDefinition, /) -> None:
        """Insert object `arg1` before index `arg0`."""

    def pop(self, index: int = -1) -> LightDefinition:
        """Remove and return item at `index` (default last)."""

    def extend(self, arg: LightDefinitionList, /) -> None:
        """Extend `self` by appending elements from `arg`."""

    @overload
    def __setitem__(self, arg0: int, arg1: LightDefinition, /) -> None: ...

    @overload
    def __setitem__(self, arg0: slice, arg1: LightDefinitionList, /) -> None: ...

    @overload
    def __delitem__(self, arg: int, /) -> None: ...

    @overload
    def __delitem__(self, arg: slice, /) -> None: ...

    def __eq__(self, arg: object, /) -> bool: ...

    def __ne__(self, arg: object, /) -> bool: ...

    @overload
    def __contains__(self, arg: LightDefinition, /) -> bool: ...

    @overload
    def __contains__(self, arg: object, /) -> bool: ...

    def count(self, arg: LightDefinition, /) -> int:
        """Return number of occurrences of `arg`."""

    def remove(self, arg: LightDefinition, /) -> None:
        """Remove first occurrence of `arg`."""

class BoundCapsuleDefinition:
    @property
    def owner_name(self) -> str: ...

    @owner_name.setter
    def owner_name(self, arg: str, /) -> None: ...

    @property
    def rotation(self) -> pymateria.Quaternion: ...

    @rotation.setter
    def rotation(self, arg: pymateria.Quaternion, /) -> None: ...

    @property
    def position(self) -> pymateria.Vector3f: ...

    @position.setter
    def position(self, arg: pymateria.Vector3f, /) -> None: ...

    @property
    def normal(self) -> pymateria.Vector3f: ...

    @normal.setter
    def normal(self, arg: pymateria.Vector3f, /) -> None: ...

    @property
    def capsule_radius(self) -> float: ...

    @capsule_radius.setter
    def capsule_radius(self, arg: float, /) -> None: ...

    @property
    def capsule_length(self) -> float: ...

    @capsule_length.setter
    def capsule_length(self, arg: float, /) -> None: ...

    @property
    def capsule_half_height(self) -> float: ...

    @capsule_half_height.setter
    def capsule_half_height(self, arg: float, /) -> None: ...

    @property
    def capsule_half_width(self) -> float: ...

    @capsule_half_width.setter
    def capsule_half_width(self, arg: float, /) -> None: ...

    @property
    def flags(self) -> int: ...

    @flags.setter
    def flags(self, arg: int, /) -> None: ...

class BoundCapsuleDefinitionList:
    @overload
    def __init__(self) -> None:
        """Default constructor"""

    @overload
    def __init__(self, arg: BoundCapsuleDefinitionList) -> None:
        """Copy constructor"""

    @overload
    def __init__(self, arg: Iterable[BoundCapsuleDefinition], /) -> None:
        """Construct from an iterable object"""

    def __len__(self) -> int: ...

    def __bool__(self) -> bool:
        """Check whether the vector is nonempty"""

    def __repr__(self) -> str: ...

    def __iter__(self) -> Iterator[BoundCapsuleDefinition]: ...

    @overload
    def __getitem__(self, arg: int, /) -> BoundCapsuleDefinition: ...

    @overload
    def __getitem__(self, arg: slice, /) -> BoundCapsuleDefinitionList: ...

    def clear(self) -> None:
        """Remove all items from list."""

    def append(self, arg: BoundCapsuleDefinition, /) -> None:
        """Append `arg` to the end of the list."""

    def insert(self, arg0: int, arg1: BoundCapsuleDefinition, /) -> None:
        """Insert object `arg1` before index `arg0`."""

    def pop(self, index: int = -1) -> BoundCapsuleDefinition:
        """Remove and return item at `index` (default last)."""

    def extend(self, arg: BoundCapsuleDefinitionList, /) -> None:
        """Extend `self` by appending elements from `arg`."""

    @overload
    def __setitem__(self, arg0: int, arg1: BoundCapsuleDefinition, /) -> None: ...

    @overload
    def __setitem__(self, arg0: slice, arg1: BoundCapsuleDefinitionList, /) -> None: ...

    @overload
    def __delitem__(self, arg: int, /) -> None: ...

    @overload
    def __delitem__(self, arg: slice, /) -> None: ...

    def __eq__(self, arg: object, /) -> bool: ...

    def __ne__(self, arg: object, /) -> bool: ...

    @overload
    def __contains__(self, arg: BoundCapsuleDefinition, /) -> bool: ...

    @overload
    def __contains__(self, arg: object, /) -> bool: ...

    def count(self, arg: BoundCapsuleDefinition, /) -> int:
        """Return number of occurrences of `arg`."""

    def remove(self, arg: BoundCapsuleDefinition, /) -> None:
        """Remove first occurrence of `arg`."""

class ExtensionAudioCollisionSettings(Extension):
    def __init__(self) -> None: ...

    PSO_CLASS: int = ...
    """PSO class identifier hash."""

    @property
    def settings(self) -> CombinedHashString: ...

    @settings.setter
    def settings(self, arg: CombinedHashString, /) -> None: ...

class ExtensionAudioEmitter(Extension):
    def __init__(self) -> None: ...

    PSO_CLASS: int = ...
    """PSO class identifier hash."""

    @property
    def offset_rotation(self) -> pymateria.Quaternion: ...

    @offset_rotation.setter
    def offset_rotation(self, arg: pymateria.Quaternion, /) -> None: ...

    @property
    def effect_hash(self) -> CombinedHashString: ...

    @effect_hash.setter
    def effect_hash(self, arg: CombinedHashString, /) -> None: ...

class ExtensionBuoyancy(Extension):
    def __init__(self) -> None: ...

    PSO_CLASS: int = ...
    """PSO class identifier hash."""

class ExtensionClimbHandHold(Extension):
    def __init__(self) -> None: ...

    PSO_CLASS: int = ...
    """PSO class identifier hash."""

    @property
    def left(self) -> pymateria.Vector3f: ...

    @left.setter
    def left(self, arg: pymateria.Vector3f, /) -> None: ...

    @property
    def right(self) -> pymateria.Vector3f: ...

    @right.setter
    def right(self, arg: pymateria.Vector3f, /) -> None: ...

    @property
    def normal(self) -> pymateria.Vector3f: ...

    @normal.setter
    def normal(self, arg: pymateria.Vector3f, /) -> None: ...

class ExtensionDecal(Extension):
    def __init__(self) -> None: ...

    PSO_CLASS: int = ...
    """PSO class identifier hash."""

    @property
    def offset_rotation(self) -> pymateria.Quaternion: ...

    @offset_rotation.setter
    def offset_rotation(self, arg: pymateria.Quaternion, /) -> None: ...

    @property
    def decal_name(self) -> str: ...

    @decal_name.setter
    def decal_name(self, arg: str, /) -> None: ...

    @property
    def decal_type(self) -> int: ...

    @decal_type.setter
    def decal_type(self, arg: int, /) -> None: ...

    @property
    def bone_tag(self) -> int: ...

    @bone_tag.setter
    def bone_tag(self, arg: int, /) -> None: ...

    @property
    def scale(self) -> float: ...

    @scale.setter
    def scale(self, arg: float, /) -> None: ...

    @property
    def probability(self) -> int: ...

    @probability.setter
    def probability(self, arg: int, /) -> None: ...

    @property
    def flags(self) -> int: ...

    @flags.setter
    def flags(self, arg: int, /) -> None: ...

class ExtensionDoor(Extension):
    def __init__(self) -> None: ...

    PSO_CLASS: int = ...
    """PSO class identifier hash."""

    @property
    def starts_locked(self) -> bool: ...

    @starts_locked.setter
    def starts_locked(self, arg: bool, /) -> None: ...

    @property
    def can_break(self) -> bool: ...

    @can_break.setter
    def can_break(self, arg: bool, /) -> None: ...

    @property
    def limit_angle(self) -> float | None: ...

    @limit_angle.setter
    def limit_angle(self, arg: float | None) -> None: ...

    @property
    def door_target_ratio(self) -> float: ...

    @door_target_ratio.setter
    def door_target_ratio(self, arg: float, /) -> None: ...

    @property
    def audio_hash(self) -> CombinedHashString: ...

    @audio_hash.setter
    def audio_hash(self, arg: CombinedHashString, /) -> None: ...

class ExtensionExplosionEffect(Extension):
    def __init__(self) -> None: ...

    PSO_CLASS: int = ...
    """PSO class identifier hash."""

    @property
    def offset_rotation(self) -> pymateria.Quaternion: ...

    @offset_rotation.setter
    def offset_rotation(self, arg: pymateria.Quaternion, /) -> None: ...

    @property
    def explosion_name(self) -> str: ...

    @explosion_name.setter
    def explosion_name(self, arg: str, /) -> None: ...

    @property
    def bone_tag(self) -> int: ...

    @bone_tag.setter
    def bone_tag(self, arg: int, /) -> None: ...

    @property
    def explosion_tag(self) -> int: ...

    @explosion_tag.setter
    def explosion_tag(self, arg: int, /) -> None: ...

    @property
    def explosion_type(self) -> int: ...

    @explosion_type.setter
    def explosion_type(self, arg: int, /) -> None: ...

    @property
    def flags(self) -> int: ...

    @flags.setter
    def flags(self, arg: int, /) -> None: ...

class ExtensionExpression(Extension):
    def __init__(self) -> None: ...

    PSO_CLASS: int = ...
    """PSO class identifier hash."""

    @property
    def expression_dictionary_name(self) -> CombinedHashString: ...

    @expression_dictionary_name.setter
    def expression_dictionary_name(self, arg: CombinedHashString, /) -> None: ...

    @property
    def expression_name(self) -> CombinedHashString: ...

    @expression_name.setter
    def expression_name(self, arg: CombinedHashString, /) -> None: ...

    @property
    def creature_metadata_name(self) -> CombinedHashString: ...

    @creature_metadata_name.setter
    def creature_metadata_name(self, arg: CombinedHashString, /) -> None: ...

    @property
    def initialize_on_collision(self) -> bool: ...

    @initialize_on_collision.setter
    def initialize_on_collision(self, arg: bool, /) -> None: ...

class ExtensionLadder(Extension):
    def __init__(self) -> None: ...

    PSO_CLASS: int = ...
    """PSO class identifier hash."""

    @property
    def bottom(self) -> pymateria.Vector3f: ...

    @bottom.setter
    def bottom(self, arg: pymateria.Vector3f, /) -> None: ...

    @property
    def top(self) -> pymateria.Vector3f: ...

    @top.setter
    def top(self, arg: pymateria.Vector3f, /) -> None: ...

    @property
    def normal(self) -> pymateria.Vector3f: ...

    @normal.setter
    def normal(self, arg: pymateria.Vector3f, /) -> None: ...

    @property
    def material_type(self) -> LadderMaterialType: ...

    @material_type.setter
    def material_type(self, arg: LadderMaterialType, /) -> None: ...

    @property
    def template_string(self) -> CombinedHashString: ...

    @template_string.setter
    def template_string(self, arg: CombinedHashString, /) -> None: ...

    @property
    def can_get_off_at_top(self) -> bool: ...

    @can_get_off_at_top.setter
    def can_get_off_at_top(self, arg: bool, /) -> None: ...

    @property
    def can_get_off_at_bottom(self) -> bool: ...

    @can_get_off_at_bottom.setter
    def can_get_off_at_bottom(self, arg: bool, /) -> None: ...

class ExtensionLight(Extension):
    def __init__(self) -> None: ...

    PSO_CLASS: int = ...
    """PSO class identifier hash."""

class ExtensionLightEffect(Extension):
    def __init__(self) -> None: ...

    PSO_CLASS: int = ...
    """PSO class identifier hash."""

    @property
    def instances(self) -> LightDefinitionList: ...

    @instances.setter
    def instances(self, arg: LightDefinitionList, /) -> None: ...

class ExtensionLightShaft(Extension):
    def __init__(self) -> None: ...

    PSO_CLASS: int = ...
    """PSO class identifier hash."""

    @property
    def corners(self) -> tuple[pymateria.Vector3f, pymateria.Vector3f, pymateria.Vector3f, pymateria.Vector3f]: ...

    @corners.setter
    def corners(self, arg: tuple[pymateria.Vector3f, pymateria.Vector3f, pymateria.Vector3f, pymateria.Vector3f], /) -> None: ...

    @property
    def direction(self) -> pymateria.Vector3f: ...

    @direction.setter
    def direction(self, arg: pymateria.Vector3f, /) -> None: ...

    @property
    def direction_amount(self) -> float: ...

    @direction_amount.setter
    def direction_amount(self, arg: float, /) -> None: ...

    @property
    def length(self) -> float: ...

    @length.setter
    def length(self, arg: float, /) -> None: ...

    @property
    def fade_in_time_start(self) -> float: ...

    @fade_in_time_start.setter
    def fade_in_time_start(self, arg: float, /) -> None: ...

    @property
    def fade_in_time_end(self) -> float: ...

    @fade_in_time_end.setter
    def fade_in_time_end(self, arg: float, /) -> None: ...

    @property
    def fade_out_time_start(self) -> float: ...

    @fade_out_time_start.setter
    def fade_out_time_start(self, arg: float, /) -> None: ...

    @property
    def fade_out_time_end(self) -> float: ...

    @fade_out_time_end.setter
    def fade_out_time_end(self, arg: float, /) -> None: ...

    @property
    def fade_distance_start(self) -> float: ...

    @fade_distance_start.setter
    def fade_distance_start(self, arg: float, /) -> None: ...

    @property
    def fade_distance_end(self) -> float: ...

    @fade_distance_end.setter
    def fade_distance_end(self, arg: float, /) -> None: ...

    @property
    def color(self) -> pymateria.ColorRGBA: ...

    @color.setter
    def color(self, arg: pymateria.ColorRGBA, /) -> None: ...

    @property
    def intensity(self) -> float: ...

    @intensity.setter
    def intensity(self, arg: float, /) -> None: ...

    @property
    def flashiness(self) -> LightFlashiness: ...

    @flashiness.setter
    def flashiness(self, arg: LightFlashiness, /) -> None: ...

    @property
    def flags(self) -> int: ...

    @flags.setter
    def flags(self, arg: int, /) -> None: ...

    @property
    def density_type(self) -> LightShaftDensityType: ...

    @density_type.setter
    def density_type(self, arg: LightShaftDensityType, /) -> None: ...

    @property
    def volume_type(self) -> LightShaftVolumeType: ...

    @volume_type.setter
    def volume_type(self, arg: LightShaftVolumeType, /) -> None: ...

    @property
    def softness(self) -> float: ...

    @softness.setter
    def softness(self, arg: float, /) -> None: ...

    @property
    def scale_by_sun_intensity(self) -> bool: ...

    @scale_by_sun_intensity.setter
    def scale_by_sun_intensity(self, arg: bool, /) -> None: ...

class ExtensionParticleEffect(Extension):
    def __init__(self) -> None: ...

    PSO_CLASS: int = ...
    """PSO class identifier hash."""

    @property
    def offset_rotation(self) -> pymateria.Quaternion: ...

    @offset_rotation.setter
    def offset_rotation(self, arg: pymateria.Quaternion, /) -> None: ...

    @property
    def fx_name(self) -> str: ...

    @fx_name.setter
    def fx_name(self, arg: str, /) -> None: ...

    @property
    def fx_type(self) -> int: ...

    @fx_type.setter
    def fx_type(self, arg: int, /) -> None: ...

    @property
    def bone_tag(self) -> int: ...

    @bone_tag.setter
    def bone_tag(self, arg: int, /) -> None: ...

    @property
    def scale(self) -> float: ...

    @scale.setter
    def scale(self, arg: float, /) -> None: ...

    @property
    def probability(self) -> int: ...

    @probability.setter
    def probability(self, arg: int, /) -> None: ...

    @property
    def flags(self) -> int: ...

    @flags.setter
    def flags(self, arg: int, /) -> None: ...

    @property
    def tint_color(self) -> pymateria.ColorRGBA | None: ...

    @tint_color.setter
    def tint_color(self, arg: pymateria.ColorRGBA | None) -> None: ...

class ExtensionProcObject(Extension):
    def __init__(self) -> None: ...

    PSO_CLASS: int = ...
    """PSO class identifier hash."""

    @property
    def radius_inner(self) -> float: ...

    @radius_inner.setter
    def radius_inner(self, arg: float, /) -> None: ...

    @property
    def radius_outer(self) -> float: ...

    @radius_outer.setter
    def radius_outer(self, arg: float, /) -> None: ...

    @property
    def spacing(self) -> float: ...

    @spacing.setter
    def spacing(self, arg: float, /) -> None: ...

    @property
    def min_scale(self) -> float: ...

    @min_scale.setter
    def min_scale(self, arg: float, /) -> None: ...

    @property
    def max_scale(self) -> float: ...

    @max_scale.setter
    def max_scale(self, arg: float, /) -> None: ...

    @property
    def min_scale_z(self) -> float: ...

    @min_scale_z.setter
    def min_scale_z(self, arg: float, /) -> None: ...

    @property
    def max_scale_z(self) -> float: ...

    @max_scale_z.setter
    def max_scale_z(self, arg: float, /) -> None: ...

    @property
    def min_z_offset(self) -> float: ...

    @min_z_offset.setter
    def min_z_offset(self, arg: float, /) -> None: ...

    @property
    def max_z_offset(self) -> float: ...

    @max_z_offset.setter
    def max_z_offset(self, arg: float, /) -> None: ...

    @property
    def object_hash(self) -> CombinedHashString: ...

    @object_hash.setter
    def object_hash(self, arg: CombinedHashString, /) -> None: ...

    @property
    def flags(self) -> int: ...

    @flags.setter
    def flags(self, arg: int, /) -> None: ...

class ExtensionScript(Extension):
    def __init__(self) -> None: ...

    PSO_CLASS: int = ...
    """PSO class identifier hash."""

    @property
    def script_name(self) -> str: ...

    @script_name.setter
    def script_name(self, arg: str, /) -> None: ...

    @property
    def children(self) -> list[ExtensionScript.Child]: ...

    @children.setter
    def children(self, arg: Sequence[ExtensionScript.Child], /) -> None: ...

    class Child:
        def __init__(self) -> None: ...

        @property
        def position(self) -> pymateria.Vector3f: ...

        @position.setter
        def position(self, arg: pymateria.Vector3f, /) -> None: ...

        @property
        def rotation_z(self) -> float: ...

        @rotation_z.setter
        def rotation_z(self, arg: float, /) -> None: ...

class ExtensionScrollbars(Extension):
    def __init__(self) -> None: ...

    PSO_CLASS: int = ...
    """PSO class identifier hash."""

    @property
    def height(self) -> float: ...

    @height.setter
    def height(self, arg: float, /) -> None: ...

    @property
    def scrollbars_type(self) -> int: ...

    @scrollbars_type.setter
    def scrollbars_type(self, arg: int, /) -> None: ...

    @property
    def points(self) -> list[pymateria.Vector3f]: ...

    @points.setter
    def points(self, arg: Sequence[pymateria.Vector3f], /) -> None: ...

class ExtensionSpawnPoint(Extension):
    def __init__(self) -> None: ...

    PSO_CLASS: int = ...
    """PSO class identifier hash."""

    @property
    def offset_rotation(self) -> pymateria.Quaternion: ...

    @offset_rotation.setter
    def offset_rotation(self, arg: pymateria.Quaternion, /) -> None: ...

    @property
    def spawn_type(self) -> CombinedHashString: ...

    @spawn_type.setter
    def spawn_type(self, arg: CombinedHashString, /) -> None: ...

    @property
    def ped_type(self) -> CombinedHashString: ...

    @ped_type.setter
    def ped_type(self, arg: CombinedHashString, /) -> None: ...

    @property
    def group(self) -> CombinedHashString: ...

    @group.setter
    def group(self, arg: CombinedHashString, /) -> None: ...

    @property
    def interior(self) -> CombinedHashString: ...

    @interior.setter
    def interior(self, arg: CombinedHashString, /) -> None: ...

    @property
    def required_imap(self) -> CombinedHashString: ...

    @required_imap.setter
    def required_imap(self, arg: CombinedHashString, /) -> None: ...

    @property
    def availability(self) -> SpawnPointAvailability: ...

    @availability.setter
    def availability(self, arg: SpawnPointAvailability, /) -> None: ...

    @property
    def probability(self) -> float: ...

    @probability.setter
    def probability(self, arg: float, /) -> None: ...

    @property
    def time_till_ped_leaves(self) -> float: ...

    @time_till_ped_leaves.setter
    def time_till_ped_leaves(self, arg: float, /) -> None: ...

    @property
    def radius(self) -> float: ...

    @radius.setter
    def radius(self, arg: float, /) -> None: ...

    @property
    def start(self) -> int: ...

    @start.setter
    def start(self, arg: int, /) -> None: ...

    @property
    def end(self) -> int: ...

    @end.setter
    def end(self, arg: int, /) -> None: ...

    @property
    def flags(self) -> int: ...

    @flags.setter
    def flags(self, arg: int, /) -> None: ...

    @property
    def high_priority(self) -> bool: ...

    @high_priority.setter
    def high_priority(self, arg: bool, /) -> None: ...

    @property
    def extended_range(self) -> bool: ...

    @extended_range.setter
    def extended_range(self, arg: bool, /) -> None: ...

    @property
    def short_range(self) -> bool: ...

    @short_range.setter
    def short_range(self, arg: bool, /) -> None: ...

class ExtensionSpawnPointOverride(Extension):
    def __init__(self) -> None: ...

    PSO_CLASS: int = ...
    """PSO class identifier hash."""

    @property
    def scenario_type(self) -> CombinedHashString: ...

    @scenario_type.setter
    def scenario_type(self, arg: CombinedHashString, /) -> None: ...

    @property
    def time_start_override(self) -> int: ...

    @time_start_override.setter
    def time_start_override(self, arg: int, /) -> None: ...

    @property
    def time_end_override(self) -> int: ...

    @time_end_override.setter
    def time_end_override(self, arg: int, /) -> None: ...

    @property
    def group(self) -> CombinedHashString: ...

    @group.setter
    def group(self, arg: CombinedHashString, /) -> None: ...

    @property
    def model_set(self) -> CombinedHashString: ...

    @model_set.setter
    def model_set(self, arg: CombinedHashString, /) -> None: ...

    @property
    def availability(self) -> SpawnPointAvailability: ...

    @availability.setter
    def availability(self, arg: SpawnPointAvailability, /) -> None: ...

    @property
    def flags(self) -> int: ...

    @flags.setter
    def flags(self, arg: int, /) -> None: ...

    @property
    def radius(self) -> float: ...

    @radius.setter
    def radius(self, arg: float, /) -> None: ...

    @property
    def time_till_ped_leaves(self) -> float: ...

    @time_till_ped_leaves.setter
    def time_till_ped_leaves(self, arg: float, /) -> None: ...

class ExtensionSwayableEffect(Extension):
    def __init__(self) -> None: ...

    PSO_CLASS: int = ...
    """PSO class identifier hash."""

    @property
    def bone_tag(self) -> int: ...

    @bone_tag.setter
    def bone_tag(self, arg: int, /) -> None: ...

    @property
    def low_wind_speed(self) -> float: ...

    @low_wind_speed.setter
    def low_wind_speed(self, arg: float, /) -> None: ...

    @property
    def low_wind_amplitude(self) -> float: ...

    @low_wind_amplitude.setter
    def low_wind_amplitude(self, arg: float, /) -> None: ...

    @property
    def high_wind_speed(self) -> float: ...

    @high_wind_speed.setter
    def high_wind_speed(self, arg: float, /) -> None: ...

    @property
    def high_wind_amplitude(self) -> float: ...

    @high_wind_amplitude.setter
    def high_wind_amplitude(self, arg: float, /) -> None: ...

class ExtensionVerletClothCustomBounds(Extension):
    def __init__(self) -> None: ...

    PSO_CLASS: int = ...
    """PSO class identifier hash."""

    @property
    def collision_data(self) -> BoundCapsuleDefinitionList: ...

    @collision_data.setter
    def collision_data(self, arg: BoundCapsuleDefinitionList, /) -> None: ...

class ExtensionWalkDontWalk(Extension):
    def __init__(self) -> None: ...

    PSO_CLASS: int = ...
    """PSO class identifier hash."""

class ExtensionWindDisturbance(Extension):
    def __init__(self) -> None: ...

    PSO_CLASS: int = ...
    """PSO class identifier hash."""

    @property
    def offset_rotation(self) -> pymateria.Quaternion: ...

    @offset_rotation.setter
    def offset_rotation(self, arg: pymateria.Quaternion, /) -> None: ...

    @property
    def disturbance_type(self) -> WindDisturbanceType: ...

    @disturbance_type.setter
    def disturbance_type(self, arg: WindDisturbanceType, /) -> None: ...

    @property
    def bone_tag(self) -> int: ...

    @bone_tag.setter
    def bone_tag(self, arg: int, /) -> None: ...

    @property
    def size(self) -> pymateria.Vector4f: ...

    @size.setter
    def size(self, arg: pymateria.Vector4f, /) -> None: ...

    @property
    def strength(self) -> float: ...

    @strength.setter
    def strength(self, arg: float, /) -> None: ...

    @property
    def flags(self) -> int: ...

    @flags.setter
    def flags(self, arg: int, /) -> None: ...

class ArchetypeAssetType(enum.Enum):
    UNINITIALIZED = 0

    FRAGMENT = 1

    DRAWABLE = 2

    DRAWABLE_DICTIONARY = 3

    ASSETLESS = 4

class ArchetypeDefinition:
    def __init__(self) -> None: ...

    @property
    def lod_distance(self) -> float: ...

    @lod_distance.setter
    def lod_distance(self, arg: float, /) -> None: ...

    @property
    def flags(self) -> int: ...

    @flags.setter
    def flags(self, arg: int, /) -> None: ...

    @property
    def special_attribute(self) -> int: ...

    @special_attribute.setter
    def special_attribute(self, arg: int, /) -> None: ...

    @property
    def bounding_box(self) -> pymateria.AABB3f: ...

    @bounding_box.setter
    def bounding_box(self, arg: pymateria.AABB3f, /) -> None: ...

    @property
    def bounding_sphere(self) -> pymateria.Sphere: ...

    @bounding_sphere.setter
    def bounding_sphere(self, arg: pymateria.Sphere, /) -> None: ...

    @property
    def hd_texture_distance(self) -> float: ...

    @hd_texture_distance.setter
    def hd_texture_distance(self, arg: float, /) -> None: ...

    @property
    def name(self) -> CombinedHashString: ...

    @name.setter
    def name(self, arg: CombinedHashString, /) -> None: ...

    @property
    def texture_dictionary(self) -> CombinedHashString: ...

    @texture_dictionary.setter
    def texture_dictionary(self, arg: CombinedHashString, /) -> None: ...

    @property
    def clip_dictionary(self) -> CombinedHashString: ...

    @clip_dictionary.setter
    def clip_dictionary(self, arg: CombinedHashString, /) -> None: ...

    @property
    def drawable_dictionary(self) -> CombinedHashString: ...

    @drawable_dictionary.setter
    def drawable_dictionary(self, arg: CombinedHashString, /) -> None: ...

    @property
    def physics_dictionary(self) -> CombinedHashString: ...

    @physics_dictionary.setter
    def physics_dictionary(self, arg: CombinedHashString, /) -> None: ...

    @property
    def asset_type(self) -> ArchetypeAssetType: ...

    @asset_type.setter
    def asset_type(self, arg: ArchetypeAssetType, /) -> None: ...

    @property
    def asset_name(self) -> CombinedHashString: ...

    @asset_name.setter
    def asset_name(self, arg: CombinedHashString, /) -> None: ...

    @property
    def extensions(self) -> ExtensionList: ...

    @extensions.setter
    def extensions(self, arg: ExtensionList, /) -> None: ...

    def __repr__(self) -> str: ...

class ArchetypeDefinitionList:
    @overload
    def __init__(self) -> None:
        """Default constructor"""

    @overload
    def __init__(self, arg: ArchetypeDefinitionList) -> None:
        """Copy constructor"""

    @overload
    def __init__(self, arg: Iterable[ArchetypeDefinition], /) -> None:
        """Construct from an iterable object"""

    def __len__(self) -> int: ...

    def __bool__(self) -> bool:
        """Check whether the vector is nonempty"""

    def __repr__(self) -> str: ...

    def __iter__(self) -> Iterator[ArchetypeDefinition]: ...

    @overload
    def __getitem__(self, arg: int, /) -> ArchetypeDefinition: ...

    @overload
    def __getitem__(self, arg: slice, /) -> ArchetypeDefinitionList: ...

    def clear(self) -> None:
        """Remove all items from list."""

    def append(self, arg: ArchetypeDefinition, /) -> None:
        """Append `arg` to the end of the list."""

    def insert(self, arg0: int, arg1: ArchetypeDefinition, /) -> None:
        """Insert object `arg1` before index `arg0`."""

    def pop(self, index: int = -1) -> ArchetypeDefinition:
        """Remove and return item at `index` (default last)."""

    def extend(self, arg: ArchetypeDefinitionList, /) -> None:
        """Extend `self` by appending elements from `arg`."""

    @overload
    def __setitem__(self, arg0: int, arg1: ArchetypeDefinition, /) -> None: ...

    @overload
    def __setitem__(self, arg0: slice, arg1: ArchetypeDefinitionList, /) -> None: ...

    @overload
    def __delitem__(self, arg: int, /) -> None: ...

    @overload
    def __delitem__(self, arg: slice, /) -> None: ...

    def __eq__(self, arg: object, /) -> bool: ...

    def __ne__(self, arg: object, /) -> bool: ...

    @overload
    def __contains__(self, arg: ArchetypeDefinition, /) -> bool: ...

    @overload
    def __contains__(self, arg: object, /) -> bool: ...

    def count(self, arg: ArchetypeDefinition, /) -> int:
        """Return number of occurrences of `arg`."""

    def remove(self, arg: ArchetypeDefinition, /) -> None:
        """Remove first occurrence of `arg`."""

class ArchetypeDefinitionTime(ArchetypeDefinition):
    def __init__(self) -> None: ...

    @property
    def time_flags(self) -> TimeFlags: ...

    @time_flags.setter
    def time_flags(self, arg: TimeFlags, /) -> None: ...

    def __repr__(self) -> str: ...

class ArchetypeDefinitionMlo(ArchetypeDefinition):
    def __init__(self) -> None: ...

    @property
    def mlo_flags(self) -> int: ...

    @mlo_flags.setter
    def mlo_flags(self, arg: int, /) -> None: ...

    @property
    def entities(self) -> ArchetypeEntityBaseList: ...

    @entities.setter
    def entities(self, arg: ArchetypeEntityBaseList, /) -> None: ...

    @property
    def rooms(self) -> MloRoomDefinitionList: ...

    @rooms.setter
    def rooms(self, arg: MloRoomDefinitionList, /) -> None: ...

    @property
    def portals(self) -> MloPortalDefinitionList: ...

    @portals.setter
    def portals(self, arg: MloPortalDefinitionList, /) -> None: ...

    @property
    def entity_sets(self) -> MloEntitySetList: ...

    @entity_sets.setter
    def entity_sets(self, arg: MloEntitySetList, /) -> None: ...

    @property
    def timecycle_modifiers(self) -> MloTimeCycleModifierList: ...

    @timecycle_modifiers.setter
    def timecycle_modifiers(self, arg: MloTimeCycleModifierList, /) -> None: ...

    def __repr__(self) -> str: ...

class ArchetypeLodType(enum.Enum):
    HD = 0

    LOD = 1

    SLOD1 = 2

    SLOD2 = 3

    SLOD3 = 4

    ORPHANHD = 5

    SLOD4 = 6

class PriorityLevel(enum.Enum):
    REQUIRED = 0

    OPTIONAL_HIGH = 1

    OPTIONAL_MEDIUM = 2

    OPTIONAL_LOW = 3

class ArchetypeEntityBase:
    def __init__(self) -> None: ...

    @property
    def archetype_name(self) -> CombinedHashString: ...

    @archetype_name.setter
    def archetype_name(self, arg: CombinedHashString, /) -> None: ...

    @property
    def flags(self) -> int: ...

    @flags.setter
    def flags(self, arg: int, /) -> None: ...

    @property
    def guid(self) -> int: ...

    @guid.setter
    def guid(self, arg: int, /) -> None: ...

    @property
    def position(self) -> pymateria.Vector3f: ...

    @position.setter
    def position(self, arg: pymateria.Vector3f, /) -> None: ...

    @property
    def rotation(self) -> pymateria.Quaternion: ...

    @rotation.setter
    def rotation(self, arg: pymateria.Quaternion, /) -> None: ...

    @property
    def scale_xy(self) -> float: ...

    @scale_xy.setter
    def scale_xy(self, arg: float, /) -> None: ...

    @property
    def scale_z(self) -> float: ...

    @scale_z.setter
    def scale_z(self, arg: float, /) -> None: ...

    @property
    def parent_index(self) -> int: ...

    @parent_index.setter
    def parent_index(self, arg: int, /) -> None: ...

    @property
    def lod_distance(self) -> float: ...

    @lod_distance.setter
    def lod_distance(self, arg: float, /) -> None: ...

    @property
    def child_lod_distance(self) -> float: ...

    @child_lod_distance.setter
    def child_lod_distance(self, arg: float, /) -> None: ...

    @property
    def lod_level(self) -> ArchetypeLodType: ...

    @lod_level.setter
    def lod_level(self, arg: ArchetypeLodType, /) -> None: ...

    @property
    def num_children(self) -> int: ...

    @num_children.setter
    def num_children(self, arg: int, /) -> None: ...

    @property
    def priority_level(self) -> PriorityLevel: ...

    @priority_level.setter
    def priority_level(self, arg: PriorityLevel, /) -> None: ...

    @property
    def extensions(self) -> ExtensionList: ...

    @extensions.setter
    def extensions(self, arg: ExtensionList, /) -> None: ...

    def __repr__(self) -> str: ...

class ArchetypeEntityBaseList:
    @overload
    def __init__(self) -> None:
        """Default constructor"""

    @overload
    def __init__(self, arg: ArchetypeEntityBaseList) -> None:
        """Copy constructor"""

    @overload
    def __init__(self, arg: Iterable[ArchetypeEntityBase], /) -> None:
        """Construct from an iterable object"""

    def __len__(self) -> int: ...

    def __bool__(self) -> bool:
        """Check whether the vector is nonempty"""

    def __repr__(self) -> str: ...

    def __iter__(self) -> Iterator[ArchetypeEntityBase]: ...

    @overload
    def __getitem__(self, arg: int, /) -> ArchetypeEntityBase: ...

    @overload
    def __getitem__(self, arg: slice, /) -> ArchetypeEntityBaseList: ...

    def clear(self) -> None:
        """Remove all items from list."""

    def append(self, arg: ArchetypeEntityBase, /) -> None:
        """Append `arg` to the end of the list."""

    def insert(self, arg0: int, arg1: ArchetypeEntityBase, /) -> None:
        """Insert object `arg1` before index `arg0`."""

    def pop(self, index: int = -1) -> ArchetypeEntityBase:
        """Remove and return item at `index` (default last)."""

    def extend(self, arg: ArchetypeEntityBaseList, /) -> None:
        """Extend `self` by appending elements from `arg`."""

    @overload
    def __setitem__(self, arg0: int, arg1: ArchetypeEntityBase, /) -> None: ...

    @overload
    def __setitem__(self, arg0: slice, arg1: ArchetypeEntityBaseList, /) -> None: ...

    @overload
    def __delitem__(self, arg: int, /) -> None: ...

    @overload
    def __delitem__(self, arg: slice, /) -> None: ...

    def __eq__(self, arg: object, /) -> bool: ...

    def __ne__(self, arg: object, /) -> bool: ...

    @overload
    def __contains__(self, arg: ArchetypeEntityBase, /) -> bool: ...

    @overload
    def __contains__(self, arg: object, /) -> bool: ...

    def count(self, arg: ArchetypeEntityBase, /) -> int:
        """Return number of occurrences of `arg`."""

    def remove(self, arg: ArchetypeEntityBase, /) -> None:
        """Remove first occurrence of `arg`."""

class ArchetypeEntity(ArchetypeEntityBase):
    def __init__(self) -> None: ...

    @property
    def ambient_occlusion_multiplier(self) -> int: ...

    @ambient_occlusion_multiplier.setter
    def ambient_occlusion_multiplier(self, arg: int, /) -> None: ...

    @property
    def artificial_ambient_occlusion(self) -> int: ...

    @artificial_ambient_occlusion.setter
    def artificial_ambient_occlusion(self, arg: int, /) -> None: ...

    @property
    def tint_value(self) -> int: ...

    @tint_value.setter
    def tint_value(self, arg: int, /) -> None: ...

    def __repr__(self) -> str: ...

class ArchetypeEntityMloInstance(ArchetypeEntity):
    def __init__(self) -> None: ...

    @property
    def group_id(self) -> int: ...

    @group_id.setter
    def group_id(self, arg: int, /) -> None: ...

    @property
    def floor_id(self) -> int: ...

    @floor_id.setter
    def floor_id(self, arg: int, /) -> None: ...

    @property
    def default_entity_sets(self) -> list[CombinedHashString]: ...

    @default_entity_sets.setter
    def default_entity_sets(self, arg: Sequence[CombinedHashString], /) -> None: ...

    @property
    def num_exit_portals(self) -> int: ...

    @num_exit_portals.setter
    def num_exit_portals(self, arg: int, /) -> None: ...

    @property
    def mlo_inst_flags(self) -> int: ...

    @mlo_inst_flags.setter
    def mlo_inst_flags(self, arg: int, /) -> None: ...

    def __repr__(self) -> str: ...

class MloRoomDefinition:
    def __init__(self) -> None: ...

    @property
    def name(self) -> str: ...

    @name.setter
    def name(self, arg: str, /) -> None: ...

    @property
    def bounding_box(self) -> pymateria.AABB3f: ...

    @bounding_box.setter
    def bounding_box(self, arg: pymateria.AABB3f, /) -> None: ...

    @property
    def blend(self) -> float: ...

    @blend.setter
    def blend(self, arg: float, /) -> None: ...

    @property
    def timecycle_name(self) -> CombinedHashString: ...

    @timecycle_name.setter
    def timecycle_name(self, arg: CombinedHashString, /) -> None: ...

    @property
    def secondary_timecycle_name(self) -> CombinedHashString: ...

    @secondary_timecycle_name.setter
    def secondary_timecycle_name(self, arg: CombinedHashString, /) -> None: ...

    @property
    def flags(self) -> int: ...

    @flags.setter
    def flags(self, arg: int, /) -> None: ...

    @property
    def portal_count(self) -> int: ...

    @portal_count.setter
    def portal_count(self, arg: int, /) -> None: ...

    @property
    def floor_id(self) -> int: ...

    @floor_id.setter
    def floor_id(self, arg: int, /) -> None: ...

    @property
    def exterior_visibility_depth(self) -> int: ...

    @exterior_visibility_depth.setter
    def exterior_visibility_depth(self, arg: int, /) -> None: ...

    @property
    def attached_objects(self) -> list[int]: ...

    @attached_objects.setter
    def attached_objects(self, arg: Sequence[int], /) -> None: ...

    def __repr__(self) -> str: ...

class MloRoomDefinitionList:
    @overload
    def __init__(self) -> None:
        """Default constructor"""

    @overload
    def __init__(self, arg: MloRoomDefinitionList) -> None:
        """Copy constructor"""

    @overload
    def __init__(self, arg: Iterable[MloRoomDefinition], /) -> None:
        """Construct from an iterable object"""

    def __len__(self) -> int: ...

    def __bool__(self) -> bool:
        """Check whether the vector is nonempty"""

    def __repr__(self) -> str: ...

    def __iter__(self) -> Iterator[MloRoomDefinition]: ...

    @overload
    def __getitem__(self, arg: int, /) -> MloRoomDefinition: ...

    @overload
    def __getitem__(self, arg: slice, /) -> MloRoomDefinitionList: ...

    def clear(self) -> None:
        """Remove all items from list."""

    def append(self, arg: MloRoomDefinition, /) -> None:
        """Append `arg` to the end of the list."""

    def insert(self, arg0: int, arg1: MloRoomDefinition, /) -> None:
        """Insert object `arg1` before index `arg0`."""

    def pop(self, index: int = -1) -> MloRoomDefinition:
        """Remove and return item at `index` (default last)."""

    def extend(self, arg: MloRoomDefinitionList, /) -> None:
        """Extend `self` by appending elements from `arg`."""

    @overload
    def __setitem__(self, arg0: int, arg1: MloRoomDefinition, /) -> None: ...

    @overload
    def __setitem__(self, arg0: slice, arg1: MloRoomDefinitionList, /) -> None: ...

    @overload
    def __delitem__(self, arg: int, /) -> None: ...

    @overload
    def __delitem__(self, arg: slice, /) -> None: ...

    def __eq__(self, arg: object, /) -> bool: ...

    def __ne__(self, arg: object, /) -> bool: ...

    @overload
    def __contains__(self, arg: MloRoomDefinition, /) -> bool: ...

    @overload
    def __contains__(self, arg: object, /) -> bool: ...

    def count(self, arg: MloRoomDefinition, /) -> int:
        """Return number of occurrences of `arg`."""

    def remove(self, arg: MloRoomDefinition, /) -> None:
        """Remove first occurrence of `arg`."""

class MloPortalDefinition:
    def __init__(self) -> None: ...

    @property
    def room_from(self) -> int: ...

    @room_from.setter
    def room_from(self, arg: int, /) -> None: ...

    @property
    def room_to(self) -> int: ...

    @room_to.setter
    def room_to(self, arg: int, /) -> None: ...

    @property
    def flags(self) -> int: ...

    @flags.setter
    def flags(self, arg: int, /) -> None: ...

    @property
    def mirror_priority(self) -> int: ...

    @mirror_priority.setter
    def mirror_priority(self, arg: int, /) -> None: ...

    @property
    def opacity(self) -> int: ...

    @opacity.setter
    def opacity(self, arg: int, /) -> None: ...

    @property
    def audio_occlusion(self) -> int: ...

    @audio_occlusion.setter
    def audio_occlusion(self, arg: int, /) -> None: ...

    @property
    def corners(self) -> list[pymateria.Vector3f]: ...

    @corners.setter
    def corners(self, arg: Sequence[pymateria.Vector3f], /) -> None: ...

    @property
    def attached_objects(self) -> list[int]: ...

    @attached_objects.setter
    def attached_objects(self, arg: Sequence[int], /) -> None: ...

    def __repr__(self) -> str: ...

class MloPortalDefinitionList:
    @overload
    def __init__(self) -> None:
        """Default constructor"""

    @overload
    def __init__(self, arg: MloPortalDefinitionList) -> None:
        """Copy constructor"""

    @overload
    def __init__(self, arg: Iterable[MloPortalDefinition], /) -> None:
        """Construct from an iterable object"""

    def __len__(self) -> int: ...

    def __bool__(self) -> bool:
        """Check whether the vector is nonempty"""

    def __repr__(self) -> str: ...

    def __iter__(self) -> Iterator[MloPortalDefinition]: ...

    @overload
    def __getitem__(self, arg: int, /) -> MloPortalDefinition: ...

    @overload
    def __getitem__(self, arg: slice, /) -> MloPortalDefinitionList: ...

    def clear(self) -> None:
        """Remove all items from list."""

    def append(self, arg: MloPortalDefinition, /) -> None:
        """Append `arg` to the end of the list."""

    def insert(self, arg0: int, arg1: MloPortalDefinition, /) -> None:
        """Insert object `arg1` before index `arg0`."""

    def pop(self, index: int = -1) -> MloPortalDefinition:
        """Remove and return item at `index` (default last)."""

    def extend(self, arg: MloPortalDefinitionList, /) -> None:
        """Extend `self` by appending elements from `arg`."""

    @overload
    def __setitem__(self, arg0: int, arg1: MloPortalDefinition, /) -> None: ...

    @overload
    def __setitem__(self, arg0: slice, arg1: MloPortalDefinitionList, /) -> None: ...

    @overload
    def __delitem__(self, arg: int, /) -> None: ...

    @overload
    def __delitem__(self, arg: slice, /) -> None: ...

    def __eq__(self, arg: object, /) -> bool: ...

    def __ne__(self, arg: object, /) -> bool: ...

    @overload
    def __contains__(self, arg: MloPortalDefinition, /) -> bool: ...

    @overload
    def __contains__(self, arg: object, /) -> bool: ...

    def count(self, arg: MloPortalDefinition, /) -> int:
        """Return number of occurrences of `arg`."""

    def remove(self, arg: MloPortalDefinition, /) -> None:
        """Remove first occurrence of `arg`."""

class MloEntitySet:
    def __init__(self) -> None: ...

    @property
    def name(self) -> CombinedHashString: ...

    @name.setter
    def name(self, arg: CombinedHashString, /) -> None: ...

    @property
    def locations(self) -> list[int]: ...

    @locations.setter
    def locations(self, arg: Sequence[int], /) -> None: ...

    @property
    def entities(self) -> ArchetypeEntityBaseList: ...

    @entities.setter
    def entities(self, arg: ArchetypeEntityBaseList, /) -> None: ...

    def __repr__(self) -> str: ...

class MloEntitySetList:
    @overload
    def __init__(self) -> None:
        """Default constructor"""

    @overload
    def __init__(self, arg: MloEntitySetList) -> None:
        """Copy constructor"""

    @overload
    def __init__(self, arg: Iterable[MloEntitySet], /) -> None:
        """Construct from an iterable object"""

    def __len__(self) -> int: ...

    def __bool__(self) -> bool:
        """Check whether the vector is nonempty"""

    def __repr__(self) -> str: ...

    def __iter__(self) -> Iterator[MloEntitySet]: ...

    @overload
    def __getitem__(self, arg: int, /) -> MloEntitySet: ...

    @overload
    def __getitem__(self, arg: slice, /) -> MloEntitySetList: ...

    def clear(self) -> None:
        """Remove all items from list."""

    def append(self, arg: MloEntitySet, /) -> None:
        """Append `arg` to the end of the list."""

    def insert(self, arg0: int, arg1: MloEntitySet, /) -> None:
        """Insert object `arg1` before index `arg0`."""

    def pop(self, index: int = -1) -> MloEntitySet:
        """Remove and return item at `index` (default last)."""

    def extend(self, arg: MloEntitySetList, /) -> None:
        """Extend `self` by appending elements from `arg`."""

    @overload
    def __setitem__(self, arg0: int, arg1: MloEntitySet, /) -> None: ...

    @overload
    def __setitem__(self, arg0: slice, arg1: MloEntitySetList, /) -> None: ...

    @overload
    def __delitem__(self, arg: int, /) -> None: ...

    @overload
    def __delitem__(self, arg: slice, /) -> None: ...

    def __eq__(self, arg: object, /) -> bool: ...

    def __ne__(self, arg: object, /) -> bool: ...

    @overload
    def __contains__(self, arg: MloEntitySet, /) -> bool: ...

    @overload
    def __contains__(self, arg: object, /) -> bool: ...

    def count(self, arg: MloEntitySet, /) -> int:
        """Return number of occurrences of `arg`."""

    def remove(self, arg: MloEntitySet, /) -> None:
        """Remove first occurrence of `arg`."""

class MloTimeCycleModifier:
    def __init__(self) -> None: ...

    @property
    def name(self) -> CombinedHashString: ...

    @name.setter
    def name(self, arg: CombinedHashString, /) -> None: ...

    @property
    def sphere(self) -> pymateria.Sphere: ...

    @sphere.setter
    def sphere(self, arg: pymateria.Sphere, /) -> None: ...

    @property
    def percentage(self) -> float: ...

    @percentage.setter
    def percentage(self, arg: float, /) -> None: ...

    @property
    def range(self) -> float: ...

    @range.setter
    def range(self, arg: float, /) -> None: ...

    @property
    def start_hour(self) -> int: ...

    @start_hour.setter
    def start_hour(self, arg: int, /) -> None: ...

    @property
    def end_hour(self) -> int: ...

    @end_hour.setter
    def end_hour(self, arg: int, /) -> None: ...

    def __repr__(self) -> str: ...

class MloTimeCycleModifierList:
    @overload
    def __init__(self) -> None:
        """Default constructor"""

    @overload
    def __init__(self, arg: MloTimeCycleModifierList) -> None:
        """Copy constructor"""

    @overload
    def __init__(self, arg: Iterable[MloTimeCycleModifier], /) -> None:
        """Construct from an iterable object"""

    def __len__(self) -> int: ...

    def __bool__(self) -> bool:
        """Check whether the vector is nonempty"""

    def __repr__(self) -> str: ...

    def __iter__(self) -> Iterator[MloTimeCycleModifier]: ...

    @overload
    def __getitem__(self, arg: int, /) -> MloTimeCycleModifier: ...

    @overload
    def __getitem__(self, arg: slice, /) -> MloTimeCycleModifierList: ...

    def clear(self) -> None:
        """Remove all items from list."""

    def append(self, arg: MloTimeCycleModifier, /) -> None:
        """Append `arg` to the end of the list."""

    def insert(self, arg0: int, arg1: MloTimeCycleModifier, /) -> None:
        """Insert object `arg1` before index `arg0`."""

    def pop(self, index: int = -1) -> MloTimeCycleModifier:
        """Remove and return item at `index` (default last)."""

    def extend(self, arg: MloTimeCycleModifierList, /) -> None:
        """Extend `self` by appending elements from `arg`."""

    @overload
    def __setitem__(self, arg0: int, arg1: MloTimeCycleModifier, /) -> None: ...

    @overload
    def __setitem__(self, arg0: slice, arg1: MloTimeCycleModifierList, /) -> None: ...

    @overload
    def __delitem__(self, arg: int, /) -> None: ...

    @overload
    def __delitem__(self, arg: slice, /) -> None: ...

    def __eq__(self, arg: object, /) -> bool: ...

    def __ne__(self, arg: object, /) -> bool: ...

    @overload
    def __contains__(self, arg: MloTimeCycleModifier, /) -> bool: ...

    @overload
    def __contains__(self, arg: object, /) -> bool: ...

    def count(self, arg: MloTimeCycleModifier, /) -> int:
        """Return number of occurrences of `arg`."""

    def remove(self, arg: MloTimeCycleModifier, /) -> None:
        """Remove first occurrence of `arg`."""

class CompositeEntityType:
    @property
    def name(self) -> str: ...

    @name.setter
    def name(self, arg: str, /) -> None: ...

    @property
    def lod_distance(self) -> float: ...

    @lod_distance.setter
    def lod_distance(self, arg: float, /) -> None: ...

    @property
    def flags(self) -> int: ...

    @flags.setter
    def flags(self, arg: int, /) -> None: ...

    @property
    def special_attribute(self) -> int: ...

    @special_attribute.setter
    def special_attribute(self, arg: int, /) -> None: ...

    @property
    def bounding_box(self) -> pymateria.AABB3f: ...

    @bounding_box.setter
    def bounding_box(self, arg: pymateria.AABB3f, /) -> None: ...

    @property
    def bounding_sphere(self) -> pymateria.Sphere: ...

    @bounding_sphere.setter
    def bounding_sphere(self, arg: pymateria.Sphere, /) -> None: ...

class CompositeEntityTypeList:
    @overload
    def __init__(self) -> None:
        """Default constructor"""

    @overload
    def __init__(self, arg: CompositeEntityTypeList) -> None:
        """Copy constructor"""

    @overload
    def __init__(self, arg: Iterable[CompositeEntityType], /) -> None:
        """Construct from an iterable object"""

    def __len__(self) -> int: ...

    def __bool__(self) -> bool:
        """Check whether the vector is nonempty"""

    def __repr__(self) -> str: ...

    def __iter__(self) -> Iterator[CompositeEntityType]: ...

    @overload
    def __getitem__(self, arg: int, /) -> CompositeEntityType: ...

    @overload
    def __getitem__(self, arg: slice, /) -> CompositeEntityTypeList: ...

    def clear(self) -> None:
        """Remove all items from list."""

    def append(self, arg: CompositeEntityType, /) -> None:
        """Append `arg` to the end of the list."""

    def insert(self, arg0: int, arg1: CompositeEntityType, /) -> None:
        """Insert object `arg1` before index `arg0`."""

    def pop(self, index: int = -1) -> CompositeEntityType:
        """Remove and return item at `index` (default last)."""

    def extend(self, arg: CompositeEntityTypeList, /) -> None:
        """Extend `self` by appending elements from `arg`."""

    @overload
    def __setitem__(self, arg0: int, arg1: CompositeEntityType, /) -> None: ...

    @overload
    def __setitem__(self, arg0: slice, arg1: CompositeEntityTypeList, /) -> None: ...

    @overload
    def __delitem__(self, arg: int, /) -> None: ...

    @overload
    def __delitem__(self, arg: slice, /) -> None: ...

    def __eq__(self, arg: object, /) -> bool: ...

    def __ne__(self, arg: object, /) -> bool: ...

    @overload
    def __contains__(self, arg: CompositeEntityType, /) -> bool: ...

    @overload
    def __contains__(self, arg: object, /) -> bool: ...

    def count(self, arg: CompositeEntityType, /) -> int:
        """Return number of occurrences of `arg`."""

    def remove(self, arg: CompositeEntityType, /) -> None:
        """Remove first occurrence of `arg`."""

class LodLightCategory(enum.Enum):
    SMALL = 0

    MEDIUM = 1

    LARGE = 2

    COUNT = 3

class OccludeModelFlags(enum.Flag):
    FLAG_WATER_ONLY = 1

class BoxOccluder:
    def __init__(self) -> None: ...

    @property
    def center(self) -> pymateria.Vector3s16: ...

    @center.setter
    def center(self, arg: pymateria.Vector3s16, /) -> None: ...

    @property
    def cos_z(self) -> int: ...

    @cos_z.setter
    def cos_z(self, arg: int, /) -> None: ...

    @property
    def sin_z(self) -> int: ...

    @sin_z.setter
    def sin_z(self, arg: int, /) -> None: ...

    @property
    def length(self) -> int: ...

    @length.setter
    def length(self, arg: int, /) -> None: ...

    @property
    def width(self) -> int: ...

    @width.setter
    def width(self, arg: int, /) -> None: ...

    @property
    def height(self) -> int: ...

    @height.setter
    def height(self, arg: int, /) -> None: ...

class BoxOccluderList:
    @overload
    def __init__(self) -> None:
        """Default constructor"""

    @overload
    def __init__(self, arg: BoxOccluderList) -> None:
        """Copy constructor"""

    @overload
    def __init__(self, arg: Iterable[BoxOccluder], /) -> None:
        """Construct from an iterable object"""

    def __len__(self) -> int: ...

    def __bool__(self) -> bool:
        """Check whether the vector is nonempty"""

    def __repr__(self) -> str: ...

    def __iter__(self) -> Iterator[BoxOccluder]: ...

    @overload
    def __getitem__(self, arg: int, /) -> BoxOccluder: ...

    @overload
    def __getitem__(self, arg: slice, /) -> BoxOccluderList: ...

    def clear(self) -> None:
        """Remove all items from list."""

    def append(self, arg: BoxOccluder, /) -> None:
        """Append `arg` to the end of the list."""

    def insert(self, arg0: int, arg1: BoxOccluder, /) -> None:
        """Insert object `arg1` before index `arg0`."""

    def pop(self, index: int = -1) -> BoxOccluder:
        """Remove and return item at `index` (default last)."""

    def extend(self, arg: BoxOccluderList, /) -> None:
        """Extend `self` by appending elements from `arg`."""

    @overload
    def __setitem__(self, arg0: int, arg1: BoxOccluder, /) -> None: ...

    @overload
    def __setitem__(self, arg0: slice, arg1: BoxOccluderList, /) -> None: ...

    @overload
    def __delitem__(self, arg: int, /) -> None: ...

    @overload
    def __delitem__(self, arg: slice, /) -> None: ...

class ContainerLOD:
    def __init__(self) -> None: ...

    @property
    def name(self) -> CombinedHashString: ...

    @name.setter
    def name(self, arg: CombinedHashString, /) -> None: ...

    @property
    def parent_index(self) -> int: ...

    @parent_index.setter
    def parent_index(self, arg: int, /) -> None: ...

class ContainerLODList:
    @overload
    def __init__(self) -> None:
        """Default constructor"""

    @overload
    def __init__(self, arg: ContainerLODList) -> None:
        """Copy constructor"""

    @overload
    def __init__(self, arg: Iterable[ContainerLOD], /) -> None:
        """Construct from an iterable object"""

    def __len__(self) -> int: ...

    def __bool__(self) -> bool:
        """Check whether the vector is nonempty"""

    def __repr__(self) -> str: ...

    def __iter__(self) -> Iterator[ContainerLOD]: ...

    @overload
    def __getitem__(self, arg: int, /) -> ContainerLOD: ...

    @overload
    def __getitem__(self, arg: slice, /) -> ContainerLODList: ...

    def clear(self) -> None:
        """Remove all items from list."""

    def append(self, arg: ContainerLOD, /) -> None:
        """Append `arg` to the end of the list."""

    def insert(self, arg0: int, arg1: ContainerLOD, /) -> None:
        """Insert object `arg1` before index `arg0`."""

    def pop(self, index: int = -1) -> ContainerLOD:
        """Remove and return item at `index` (default last)."""

    def extend(self, arg: ContainerLODList, /) -> None:
        """Extend `self` by appending elements from `arg`."""

    @overload
    def __setitem__(self, arg0: int, arg1: ContainerLOD, /) -> None: ...

    @overload
    def __setitem__(self, arg0: slice, arg1: ContainerLODList, /) -> None: ...

    @overload
    def __delitem__(self, arg: int, /) -> None: ...

    @overload
    def __delitem__(self, arg: slice, /) -> None: ...

class CarGenerator:
    def __init__(self) -> None: ...

    @property
    def position(self) -> pymateria.Vector3f: ...

    @position.setter
    def position(self, arg: pymateria.Vector3f, /) -> None: ...

    @property
    def orient(self) -> pymateria.Vector2f: ...

    @orient.setter
    def orient(self, arg: pymateria.Vector2f, /) -> None: ...

    @property
    def perpendicular_length(self) -> float: ...

    @perpendicular_length.setter
    def perpendicular_length(self, arg: float, /) -> None: ...

    @property
    def car_model(self) -> CombinedHashString: ...

    @car_model.setter
    def car_model(self, arg: CombinedHashString, /) -> None: ...

    @property
    def flags(self) -> int: ...

    @flags.setter
    def flags(self, arg: int, /) -> None: ...

    @property
    def body_color_remap_1(self) -> int: ...

    @body_color_remap_1.setter
    def body_color_remap_1(self, arg: int, /) -> None: ...

    @property
    def body_color_remap_2(self) -> int: ...

    @body_color_remap_2.setter
    def body_color_remap_2(self, arg: int, /) -> None: ...

    @property
    def body_color_remap_3(self) -> int: ...

    @body_color_remap_3.setter
    def body_color_remap_3(self, arg: int, /) -> None: ...

    @property
    def body_color_remap_4(self) -> int: ...

    @body_color_remap_4.setter
    def body_color_remap_4(self, arg: int, /) -> None: ...

    @property
    def pop_group(self) -> CombinedHashString: ...

    @pop_group.setter
    def pop_group(self, arg: CombinedHashString, /) -> None: ...

    @property
    def livery(self) -> int: ...

    @livery.setter
    def livery(self, arg: int, /) -> None: ...

class CarGeneratorList:
    @overload
    def __init__(self) -> None:
        """Default constructor"""

    @overload
    def __init__(self, arg: CarGeneratorList) -> None:
        """Copy constructor"""

    @overload
    def __init__(self, arg: Iterable[CarGenerator], /) -> None:
        """Construct from an iterable object"""

    def __len__(self) -> int: ...

    def __bool__(self) -> bool:
        """Check whether the vector is nonempty"""

    def __repr__(self) -> str: ...

    def __iter__(self) -> Iterator[CarGenerator]: ...

    @overload
    def __getitem__(self, arg: int, /) -> CarGenerator: ...

    @overload
    def __getitem__(self, arg: slice, /) -> CarGeneratorList: ...

    def clear(self) -> None:
        """Remove all items from list."""

    def append(self, arg: CarGenerator, /) -> None:
        """Append `arg` to the end of the list."""

    def insert(self, arg0: int, arg1: CarGenerator, /) -> None:
        """Insert object `arg1` before index `arg0`."""

    def pop(self, index: int = -1) -> CarGenerator:
        """Remove and return item at `index` (default last)."""

    def extend(self, arg: CarGeneratorList, /) -> None:
        """Extend `self` by appending elements from `arg`."""

    @overload
    def __setitem__(self, arg0: int, arg1: CarGenerator, /) -> None: ...

    @overload
    def __setitem__(self, arg0: slice, arg1: CarGeneratorList, /) -> None: ...

    @overload
    def __delitem__(self, arg: int, /) -> None: ...

    @overload
    def __delitem__(self, arg: slice, /) -> None: ...

class TimeCycleModifier:
    def __init__(self) -> None: ...

    @property
    def name(self) -> CombinedHashString: ...

    @name.setter
    def name(self, arg: CombinedHashString, /) -> None: ...

    @property
    def min_extents(self) -> pymateria.Vector3f: ...

    @min_extents.setter
    def min_extents(self, arg: pymateria.Vector3f, /) -> None: ...

    @property
    def max_extents(self) -> pymateria.Vector3f: ...

    @max_extents.setter
    def max_extents(self, arg: pymateria.Vector3f, /) -> None: ...

    @property
    def percentage(self) -> float: ...

    @percentage.setter
    def percentage(self, arg: float, /) -> None: ...

    @property
    def range(self) -> float: ...

    @range.setter
    def range(self, arg: float, /) -> None: ...

    @property
    def start_hour(self) -> int: ...

    @start_hour.setter
    def start_hour(self, arg: int, /) -> None: ...

    @property
    def end_hour(self) -> int: ...

    @end_hour.setter
    def end_hour(self, arg: int, /) -> None: ...

class TimeCycleModifierList:
    @overload
    def __init__(self) -> None:
        """Default constructor"""

    @overload
    def __init__(self, arg: TimeCycleModifierList) -> None:
        """Copy constructor"""

    @overload
    def __init__(self, arg: Iterable[TimeCycleModifier], /) -> None:
        """Construct from an iterable object"""

    def __len__(self) -> int: ...

    def __bool__(self) -> bool:
        """Check whether the vector is nonempty"""

    def __repr__(self) -> str: ...

    def __iter__(self) -> Iterator[TimeCycleModifier]: ...

    @overload
    def __getitem__(self, arg: int, /) -> TimeCycleModifier: ...

    @overload
    def __getitem__(self, arg: slice, /) -> TimeCycleModifierList: ...

    def clear(self) -> None:
        """Remove all items from list."""

    def append(self, arg: TimeCycleModifier, /) -> None:
        """Append `arg` to the end of the list."""

    def insert(self, arg0: int, arg1: TimeCycleModifier, /) -> None:
        """Insert object `arg1` before index `arg0`."""

    def pop(self, index: int = -1) -> TimeCycleModifier:
        """Remove and return item at `index` (default last)."""

    def extend(self, arg: TimeCycleModifierList, /) -> None:
        """Extend `self` by appending elements from `arg`."""

    @overload
    def __setitem__(self, arg0: int, arg1: TimeCycleModifier, /) -> None: ...

    @overload
    def __setitem__(self, arg0: slice, arg1: TimeCycleModifierList, /) -> None: ...

    @overload
    def __delitem__(self, arg: int, /) -> None: ...

    @overload
    def __delitem__(self, arg: slice, /) -> None: ...

class PropInstance:
    def __init__(self) -> None: ...

    @property
    def matrix(self) -> pymateria.Matrix34: ...

    @matrix.setter
    def matrix(self, arg: pymateria.Matrix34, /) -> None: ...

    @property
    def tint(self) -> pymateria.ColorRGBA: ...

    @tint.setter
    def tint(self, arg: pymateria.ColorRGBA, /) -> None: ...

    @property
    def index(self) -> int: ...

    @index.setter
    def index(self, arg: int, /) -> None: ...

class GrassInstance:
    def __init__(self) -> None: ...

    @property
    def position(self) -> pymateria.Vector3u16: ...

    @position.setter
    def position(self, arg: pymateria.Vector3u16, /) -> None: ...

    @property
    def normal(self) -> pymateria.Vector2u8: ...

    @normal.setter
    def normal(self, arg: pymateria.Vector2u8, /) -> None: ...

    @property
    def color(self) -> pymateria.ColorRGB: ...

    @color.setter
    def color(self, arg: pymateria.ColorRGB, /) -> None: ...

    @property
    def scale(self) -> int: ...

    @scale.setter
    def scale(self, arg: int, /) -> None: ...

    @property
    def ambient_occlusion(self) -> int: ...

    @ambient_occlusion.setter
    def ambient_occlusion(self, arg: int, /) -> None: ...

class OccludeModel:
    def __init__(self) -> None: ...

    @property
    def flags(self) -> OccludeModelFlags: ...

    @flags.setter
    def flags(self, arg: OccludeModelFlags, /) -> None: ...

    @property
    def float_vertex_format(self) -> bool: ...

    @float_vertex_format.setter
    def float_vertex_format(self, arg: bool, /) -> None: ...

    @property
    def vertices(self) -> list[pymateria.Vector3f]: ...

    @vertices.setter
    def vertices(self, arg: Sequence[pymateria.Vector3f], /) -> None: ...

    @property
    def tris(self) -> list[pymateria.Vector3u8]: ...

    @tris.setter
    def tris(self, arg: Sequence[pymateria.Vector3u8], /) -> None: ...

class OccludeModelList:
    @overload
    def __init__(self) -> None:
        """Default constructor"""

    @overload
    def __init__(self, arg: OccludeModelList) -> None:
        """Copy constructor"""

    @overload
    def __init__(self, arg: Iterable[OccludeModel], /) -> None:
        """Construct from an iterable object"""

    def __len__(self) -> int: ...

    def __bool__(self) -> bool:
        """Check whether the vector is nonempty"""

    def __repr__(self) -> str: ...

    def __iter__(self) -> Iterator[OccludeModel]: ...

    @overload
    def __getitem__(self, arg: int, /) -> OccludeModel: ...

    @overload
    def __getitem__(self, arg: slice, /) -> OccludeModelList: ...

    def clear(self) -> None:
        """Remove all items from list."""

    def append(self, arg: OccludeModel, /) -> None:
        """Append `arg` to the end of the list."""

    def insert(self, arg0: int, arg1: OccludeModel, /) -> None:
        """Insert object `arg1` before index `arg0`."""

    def pop(self, index: int = -1) -> OccludeModel:
        """Remove and return item at `index` (default last)."""

    def extend(self, arg: OccludeModelList, /) -> None:
        """Extend `self` by appending elements from `arg`."""

    @overload
    def __setitem__(self, arg0: int, arg1: OccludeModel, /) -> None: ...

    @overload
    def __setitem__(self, arg0: slice, arg1: OccludeModelList, /) -> None: ...

    @overload
    def __delitem__(self, arg: int, /) -> None: ...

    @overload
    def __delitem__(self, arg: slice, /) -> None: ...

class MapDataDescription:
    def __init__(self) -> None: ...

    @property
    def version(self) -> int: ...

    @version.setter
    def version(self, arg: int, /) -> None: ...

    @property
    def flags(self) -> int: ...

    @flags.setter
    def flags(self, arg: int, /) -> None: ...

    @property
    def name(self) -> str | None: ...

    @name.setter
    def name(self, arg: str | None) -> None: ...

    @property
    def exported_by(self) -> str | None: ...

    @exported_by.setter
    def exported_by(self, arg: str | None) -> None: ...

    @property
    def owner(self) -> str | None: ...

    @owner.setter
    def owner(self, arg: str | None) -> None: ...

    @property
    def time(self) -> str | None: ...

    @time.setter
    def time(self, arg: str | None) -> None: ...

class PropInstanceList:
    def __init__(self) -> None: ...

    @property
    def instances(self) -> PropInstanceList.InstanceList: ...

    @instances.setter
    def instances(self, arg: PropInstanceList.InstanceList, /) -> None: ...

    @property
    def batch_aabb(self) -> pymateria.AABB3f: ...

    @batch_aabb.setter
    def batch_aabb(self, arg: pymateria.AABB3f, /) -> None: ...

    @property
    def archetype_name(self) -> CombinedHashString: ...

    @archetype_name.setter
    def archetype_name(self, arg: CombinedHashString, /) -> None: ...

    @property
    def lod_dist(self) -> int: ...

    @lod_dist.setter
    def lod_dist(self, arg: int, /) -> None: ...

    class InstanceList:
        @overload
        def __init__(self) -> None:
            """Default constructor"""

        @overload
        def __init__(self, arg: PropInstanceList.InstanceList) -> None:
            """Copy constructor"""

        @overload
        def __init__(self, arg: Iterable[PropInstance], /) -> None:
            """Construct from an iterable object"""

        def __len__(self) -> int: ...

        def __bool__(self) -> bool:
            """Check whether the vector is nonempty"""

        def __repr__(self) -> str: ...

        def __iter__(self) -> Iterator[PropInstance]: ...

        @overload
        def __getitem__(self, arg: int, /) -> PropInstance: ...

        @overload
        def __getitem__(self, arg: slice, /) -> PropInstanceList.InstanceList: ...

        def clear(self) -> None:
            """Remove all items from list."""

        def append(self, arg: PropInstance, /) -> None:
            """Append `arg` to the end of the list."""

        def insert(self, arg0: int, arg1: PropInstance, /) -> None:
            """Insert object `arg1` before index `arg0`."""

        def pop(self, index: int = -1) -> PropInstance:
            """Remove and return item at `index` (default last)."""

        def extend(self, arg: PropInstanceList.InstanceList, /) -> None:
            """Extend `self` by appending elements from `arg`."""

        @overload
        def __setitem__(self, arg0: int, arg1: PropInstance, /) -> None: ...

        @overload
        def __setitem__(self, arg0: slice, arg1: PropInstanceList.InstanceList, /) -> None: ...

        @overload
        def __delitem__(self, arg: int, /) -> None: ...

        @overload
        def __delitem__(self, arg: slice, /) -> None: ...

class PropInstanceListList:
    @overload
    def __init__(self) -> None:
        """Default constructor"""

    @overload
    def __init__(self, arg: PropInstanceListList) -> None:
        """Copy constructor"""

    @overload
    def __init__(self, arg: Iterable[PropInstanceList], /) -> None:
        """Construct from an iterable object"""

    def __len__(self) -> int: ...

    def __bool__(self) -> bool:
        """Check whether the vector is nonempty"""

    def __repr__(self) -> str: ...

    def __iter__(self) -> Iterator[PropInstanceList]: ...

    @overload
    def __getitem__(self, arg: int, /) -> PropInstanceList: ...

    @overload
    def __getitem__(self, arg: slice, /) -> PropInstanceListList: ...

    def clear(self) -> None:
        """Remove all items from list."""

    def append(self, arg: PropInstanceList, /) -> None:
        """Append `arg` to the end of the list."""

    def insert(self, arg0: int, arg1: PropInstanceList, /) -> None:
        """Insert object `arg1` before index `arg0`."""

    def pop(self, index: int = -1) -> PropInstanceList:
        """Remove and return item at `index` (default last)."""

    def extend(self, arg: PropInstanceListList, /) -> None:
        """Extend `self` by appending elements from `arg`."""

    @overload
    def __setitem__(self, arg0: int, arg1: PropInstanceList, /) -> None: ...

    @overload
    def __setitem__(self, arg0: slice, arg1: PropInstanceListList, /) -> None: ...

    @overload
    def __delitem__(self, arg: int, /) -> None: ...

    @overload
    def __delitem__(self, arg: slice, /) -> None: ...

class GrassInstanceList:
    def __init__(self) -> None: ...

    @property
    def instances(self) -> GrassInstanceList.InstanceList: ...

    @instances.setter
    def instances(self, arg: GrassInstanceList.InstanceList, /) -> None: ...

    @property
    def batch_aabb(self) -> pymateria.AABB3f: ...

    @batch_aabb.setter
    def batch_aabb(self, arg: pymateria.AABB3f, /) -> None: ...

    @property
    def scale_range(self) -> pymateria.Vector3f: ...

    @scale_range.setter
    def scale_range(self, arg: pymateria.Vector3f, /) -> None: ...

    @property
    def archetype_name(self) -> CombinedHashString: ...

    @archetype_name.setter
    def archetype_name(self, arg: CombinedHashString, /) -> None: ...

    @property
    def lod_dist(self) -> int: ...

    @lod_dist.setter
    def lod_dist(self, arg: int, /) -> None: ...

    @property
    def lod_fade_start_dist(self) -> float: ...

    @lod_fade_start_dist.setter
    def lod_fade_start_dist(self, arg: float, /) -> None: ...

    @property
    def lod_inst_fade_range(self) -> float: ...

    @lod_inst_fade_range.setter
    def lod_inst_fade_range(self, arg: float, /) -> None: ...

    @property
    def orient_to_terrain(self) -> float: ...

    @orient_to_terrain.setter
    def orient_to_terrain(self, arg: float, /) -> None: ...

    class InstanceList:
        @overload
        def __init__(self) -> None:
            """Default constructor"""

        @overload
        def __init__(self, arg: GrassInstanceList.InstanceList) -> None:
            """Copy constructor"""

        @overload
        def __init__(self, arg: Iterable[GrassInstance], /) -> None:
            """Construct from an iterable object"""

        def __len__(self) -> int: ...

        def __bool__(self) -> bool:
            """Check whether the vector is nonempty"""

        def __repr__(self) -> str: ...

        def __iter__(self) -> Iterator[GrassInstance]: ...

        @overload
        def __getitem__(self, arg: int, /) -> GrassInstance: ...

        @overload
        def __getitem__(self, arg: slice, /) -> GrassInstanceList.InstanceList: ...

        def clear(self) -> None:
            """Remove all items from list."""

        def append(self, arg: GrassInstance, /) -> None:
            """Append `arg` to the end of the list."""

        def insert(self, arg0: int, arg1: GrassInstance, /) -> None:
            """Insert object `arg1` before index `arg0`."""

        def pop(self, index: int = -1) -> GrassInstance:
            """Remove and return item at `index` (default last)."""

        def extend(self, arg: GrassInstanceList.InstanceList, /) -> None:
            """Extend `self` by appending elements from `arg`."""

        @overload
        def __setitem__(self, arg0: int, arg1: GrassInstance, /) -> None: ...

        @overload
        def __setitem__(self, arg0: slice, arg1: GrassInstanceList.InstanceList, /) -> None: ...

        @overload
        def __delitem__(self, arg: int, /) -> None: ...

        @overload
        def __delitem__(self, arg: slice, /) -> None: ...

class GrassInstanceListList:
    @overload
    def __init__(self) -> None:
        """Default constructor"""

    @overload
    def __init__(self, arg: GrassInstanceListList) -> None:
        """Copy constructor"""

    @overload
    def __init__(self, arg: Iterable[GrassInstanceList], /) -> None:
        """Construct from an iterable object"""

    def __len__(self) -> int: ...

    def __bool__(self) -> bool:
        """Check whether the vector is nonempty"""

    def __repr__(self) -> str: ...

    def __iter__(self) -> Iterator[GrassInstanceList]: ...

    @overload
    def __getitem__(self, arg: int, /) -> GrassInstanceList: ...

    @overload
    def __getitem__(self, arg: slice, /) -> GrassInstanceListList: ...

    def clear(self) -> None:
        """Remove all items from list."""

    def append(self, arg: GrassInstanceList, /) -> None:
        """Append `arg` to the end of the list."""

    def insert(self, arg0: int, arg1: GrassInstanceList, /) -> None:
        """Insert object `arg1` before index `arg0`."""

    def pop(self, index: int = -1) -> GrassInstanceList:
        """Remove and return item at `index` (default last)."""

    def extend(self, arg: GrassInstanceListList, /) -> None:
        """Extend `self` by appending elements from `arg`."""

    @overload
    def __setitem__(self, arg0: int, arg1: GrassInstanceList, /) -> None: ...

    @overload
    def __setitem__(self, arg0: slice, arg1: GrassInstanceListList, /) -> None: ...

    @overload
    def __delitem__(self, arg: int, /) -> None: ...

    @overload
    def __delitem__(self, arg: slice, /) -> None: ...

class InstancedMapData:
    def __init__(self) -> None: ...

    @property
    def imap_link(self) -> CombinedHashString: ...

    @imap_link.setter
    def imap_link(self, arg: CombinedHashString, /) -> None: ...

    @property
    def prop_instance_lists(self) -> PropInstanceListList: ...

    @prop_instance_lists.setter
    def prop_instance_lists(self, arg: PropInstanceListList, /) -> None: ...

    @property
    def grass_instance_lists(self) -> GrassInstanceListList: ...

    @grass_instance_lists.setter
    def grass_instance_lists(self, arg: GrassInstanceListList, /) -> None: ...

class DistantLODLights:
    def __init__(self) -> None: ...

    @property
    def lights(self) -> DistantLODLights.LightList: ...

    @lights.setter
    def lights(self, arg: DistantLODLights.LightList, /) -> None: ...

    @property
    def category(self) -> LodLightCategory: ...

    @category.setter
    def category(self, arg: LodLightCategory, /) -> None: ...

    class Light:
        def __init__(self) -> None: ...

        @property
        def position(self) -> pymateria.Vector3f: ...

        @position.setter
        def position(self, arg: pymateria.Vector3f, /) -> None: ...

        @property
        def color(self) -> pymateria.ColorRGBA: ...

        @color.setter
        def color(self, arg: pymateria.ColorRGBA, /) -> None: ...

        @property
        def is_street_light(self) -> bool: ...

        @is_street_light.setter
        def is_street_light(self, arg: bool, /) -> None: ...

    class LightList:
        @overload
        def __init__(self) -> None:
            """Default constructor"""

        @overload
        def __init__(self, arg: DistantLODLights.LightList) -> None:
            """Copy constructor"""

        @overload
        def __init__(self, arg: Iterable[DistantLODLights.Light], /) -> None:
            """Construct from an iterable object"""

        def __len__(self) -> int: ...

        def __bool__(self) -> bool:
            """Check whether the vector is nonempty"""

        def __repr__(self) -> str: ...

        def __iter__(self) -> Iterator[DistantLODLights.Light]: ...

        @overload
        def __getitem__(self, arg: int, /) -> DistantLODLights.Light: ...

        @overload
        def __getitem__(self, arg: slice, /) -> DistantLODLights.LightList: ...

        def clear(self) -> None:
            """Remove all items from list."""

        def append(self, arg: DistantLODLights.Light, /) -> None:
            """Append `arg` to the end of the list."""

        def insert(self, arg0: int, arg1: DistantLODLights.Light, /) -> None:
            """Insert object `arg1` before index `arg0`."""

        def pop(self, index: int = -1) -> DistantLODLights.Light:
            """Remove and return item at `index` (default last)."""

        def extend(self, arg: DistantLODLights.LightList, /) -> None:
            """Extend `self` by appending elements from `arg`."""

        @overload
        def __setitem__(self, arg0: int, arg1: DistantLODLights.Light, /) -> None: ...

        @overload
        def __setitem__(self, arg0: slice, arg1: DistantLODLights.LightList, /) -> None: ...

        @overload
        def __delitem__(self, arg: int, /) -> None: ...

        @overload
        def __delitem__(self, arg: slice, /) -> None: ...

class LODLights:
    def __init__(self) -> None: ...

    @property
    def lights(self) -> LODLights.LightList: ...

    @lights.setter
    def lights(self, arg: LODLights.LightList, /) -> None: ...

    class Light:
        def __init__(self) -> None: ...

        @property
        def direction(self) -> pymateria.Vector3f: ...

        @direction.setter
        def direction(self, arg: pymateria.Vector3f, /) -> None: ...

        @property
        def falloff(self) -> float: ...

        @falloff.setter
        def falloff(self, arg: float, /) -> None: ...

        @property
        def falloff_exponent(self) -> float: ...

        @falloff_exponent.setter
        def falloff_exponent(self, arg: float, /) -> None: ...

        @property
        def time_and_state_flags(self) -> int: ...

        @time_and_state_flags.setter
        def time_and_state_flags(self, arg: int, /) -> None: ...

        @property
        def hash(self) -> int: ...

        @hash.setter
        def hash(self, arg: int, /) -> None: ...

        @property
        def cone_inner_angle(self) -> int: ...

        @cone_inner_angle.setter
        def cone_inner_angle(self, arg: int, /) -> None: ...

        @property
        def cone_outer_angle_or_cap_ext(self) -> int: ...

        @cone_outer_angle_or_cap_ext.setter
        def cone_outer_angle_or_cap_ext(self, arg: int, /) -> None: ...

        @property
        def corona_intensity(self) -> int: ...

        @corona_intensity.setter
        def corona_intensity(self, arg: int, /) -> None: ...

    class LightList:
        @overload
        def __init__(self) -> None:
            """Default constructor"""

        @overload
        def __init__(self, arg: LODLights.LightList) -> None:
            """Copy constructor"""

        @overload
        def __init__(self, arg: Iterable[LODLights.Light], /) -> None:
            """Construct from an iterable object"""

        def __len__(self) -> int: ...

        def __bool__(self) -> bool:
            """Check whether the vector is nonempty"""

        def __repr__(self) -> str: ...

        def __iter__(self) -> Iterator[LODLights.Light]: ...

        @overload
        def __getitem__(self, arg: int, /) -> LODLights.Light: ...

        @overload
        def __getitem__(self, arg: slice, /) -> LODLights.LightList: ...

        def clear(self) -> None:
            """Remove all items from list."""

        def append(self, arg: LODLights.Light, /) -> None:
            """Append `arg` to the end of the list."""

        def insert(self, arg0: int, arg1: LODLights.Light, /) -> None:
            """Insert object `arg1` before index `arg0`."""

        def pop(self, index: int = -1) -> LODLights.Light:
            """Remove and return item at `index` (default last)."""

        def extend(self, arg: LODLights.LightList, /) -> None:
            """Extend `self` by appending elements from `arg`."""

        @overload
        def __setitem__(self, arg0: int, arg1: LODLights.Light, /) -> None: ...

        @overload
        def __setitem__(self, arg0: slice, arg1: LODLights.LightList, /) -> None: ...

        @overload
        def __delitem__(self, arg: int, /) -> None: ...

        @overload
        def __delitem__(self, arg: slice, /) -> None: ...

class MapData:
    def __init__(self) -> None: ...

    @property
    def name(self) -> CombinedHashString: ...

    @name.setter
    def name(self, arg: CombinedHashString, /) -> None: ...

    @property
    def parent(self) -> CombinedHashString: ...

    @parent.setter
    def parent(self, arg: CombinedHashString, /) -> None: ...

    @property
    def flags(self) -> int: ...

    @flags.setter
    def flags(self, arg: int, /) -> None: ...

    @property
    def content_flags(self) -> int: ...

    @content_flags.setter
    def content_flags(self, arg: int, /) -> None: ...

    @property
    def streaming_extents_min(self) -> pymateria.Vector3f: ...

    @streaming_extents_min.setter
    def streaming_extents_min(self, arg: pymateria.Vector3f, /) -> None: ...

    @property
    def streaming_extents_max(self) -> pymateria.Vector3f: ...

    @streaming_extents_max.setter
    def streaming_extents_max(self, arg: pymateria.Vector3f, /) -> None: ...

    @property
    def entities_extents_min(self) -> pymateria.Vector3f: ...

    @entities_extents_min.setter
    def entities_extents_min(self, arg: pymateria.Vector3f, /) -> None: ...

    @property
    def entities_extents_max(self) -> pymateria.Vector3f: ...

    @entities_extents_max.setter
    def entities_extents_max(self, arg: pymateria.Vector3f, /) -> None: ...

    @property
    def entities(self) -> ArchetypeEntityBaseList: ...

    @entities.setter
    def entities(self, arg: ArchetypeEntityBaseList, /) -> None: ...

    @property
    def container_lods(self) -> ContainerLODList: ...

    @container_lods.setter
    def container_lods(self, arg: ContainerLODList, /) -> None: ...

    @property
    def box_occluders(self) -> BoxOccluderList: ...

    @box_occluders.setter
    def box_occluders(self, arg: BoxOccluderList, /) -> None: ...

    @property
    def occlude_models(self) -> OccludeModelList: ...

    @occlude_models.setter
    def occlude_models(self, arg: OccludeModelList, /) -> None: ...

    @property
    def physics_dictionaries(self) -> list[CombinedHashString]: ...

    @physics_dictionaries.setter
    def physics_dictionaries(self, arg: Sequence[CombinedHashString], /) -> None: ...

    @property
    def instanced_data(self) -> InstancedMapData: ...

    @instanced_data.setter
    def instanced_data(self, arg: InstancedMapData, /) -> None: ...

    @property
    def distant_lod_lights(self) -> DistantLODLights: ...

    @distant_lod_lights.setter
    def distant_lod_lights(self, arg: DistantLODLights, /) -> None: ...

    @property
    def lod_lights(self) -> LODLights: ...

    @lod_lights.setter
    def lod_lights(self, arg: LODLights, /) -> None: ...

    @property
    def car_generators(self) -> CarGeneratorList: ...

    @car_generators.setter
    def car_generators(self, arg: CarGeneratorList, /) -> None: ...

    @property
    def time_cycle_modifiers(self) -> TimeCycleModifierList: ...

    @time_cycle_modifiers.setter
    def time_cycle_modifiers(self, arg: TimeCycleModifierList, /) -> None: ...

    @property
    def description(self) -> MapDataDescription: ...

    @description.setter
    def description(self, arg: MapDataDescription, /) -> None: ...

    def __repr__(self) -> str: ...

    class DeserializationResult(pymateria.SharedResult):
        def __init__(self) -> None: ...

        @property
        def result(self) -> MapData: ...

        @result.setter
        def result(self, arg: MapData, /) -> None: ...

        @property
        def deserializer(self) -> pymateria.pso.Deserializer: ...

    RSC_VERSION: int = ...
    """Resource version of this asset format."""

    @overload
    @staticmethod
    def import_rsc(file_path: str | os.PathLike, settings: pymateria.ImportSettings | None = None) -> MapData.DeserializationResult: ...

    @overload
    @staticmethod
    def import_rsc(stream: io.IOBase, settings: pymateria.ImportSettings | None = None) -> MapData.DeserializationResult: ...

    @overload
    @staticmethod
    def export_rsc(instance: MapData, file_path: str | os.PathLike, settings: pymateria.ExportSettings | None = None) -> pymateria.SerializationResultPso: ...

    @overload
    @staticmethod
    def export_rsc(instance: MapData, stream: io.IOBase, settings: pymateria.ExportSettings | None = None) -> pymateria.SerializationResultPso: ...
