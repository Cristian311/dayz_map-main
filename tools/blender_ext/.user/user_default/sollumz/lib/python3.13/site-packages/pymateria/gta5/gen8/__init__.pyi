from collections.abc import Iterable, Iterator, Sequence, Set
import enum
import io
import os
from typing import Annotated, overload

import numpy
from numpy.typing import NDArray

import pymateria
import pymateria.gta5
import pymateria.pso
import pymateria.rsc7


class TextureFormat(enum.Enum):
    UNKNOWN = 0

    R8G8B8 = 20

    A8R8G8B8 = 21

    X8R8G8B8 = 22

    R5G6B5 = 23

    X1R5G5B5 = 24

    A1R5G5B5 = 25

    A4R4G4B4 = 26

    R3G3B2 = 27

    A8 = 28

    A8R3G3B2 = 29

    X4R4G4B4 = 30

    A2B10G10R10 = 31

    A8B8G8R8 = 32

    X8B8G8R8 = 33

    G16R16 = 34

    A2R10G10B10 = 35

    A16B16G16R16 = 36

    A8P8 = 40

    P8 = 41

    L8 = 50

    A8L8 = 51

    A4L4 = 52

    V8U8 = 60

    L6V5U5 = 61

    X8L8V8U8 = 62

    Q8W8V8U8 = 63

    V16U16 = 64

    A2W10V10U10 = 67

    UYVY = 1498831189

    R8G8_B8G8 = 1195525970

    YUY2 = 844715353

    G8R8_G8B8 = 1111970375

    DXT1 = 827611204

    DXT2 = 844388420

    DXT3 = 861165636

    DXT4 = 877942852

    DXT5 = 894720068

    CTX1 = 827872323

    DXT3A = 861165633

    DXT3A_1111 = 861155649

    DXT5A = 826889281

    DXN = 843666497

    BC6 = 540427074

    BC7 = 540492610

    R8 = 538982482

    R16 = 540422482

    G8R8 = 944912455

    D16_LOCKABLE = 70

    D32 = 71

    D15S1 = 73

    D24S8 = 75

    D24X8 = 77

    D24X4S4 = 79

    D16 = 80

    D32F_LOCKABLE = 82

    D24FS8 = 83

    D32_LOCKABLE = 84

    S8_LOCKABLE = 85

    L16 = 81

    VERTEXDATA = 100

    INDEX16 = 101

    INDEX32 = 102

    Q16W16V16U16 = 110

    MULTI2_ARGB8 = 827606349

    R16F = 111

    G16R16F = 112

    A16B16G16R16F = 113

    R32F = 114

    G32R32F = 115

    A32B32G32R32F = 116

    CxV8U8 = 117

    A1 = 118

    A2B10G10R10_XR_BIAS = 119

    BINARYBUFFER = 199

class TextureType(enum.Enum):
    STANDARD = 0

    CUBE = 1

    DEPTH = 2

    VOLUME = 3

class TextureTemplateType(enum.Enum):
    UNKNOWN = 0

    DEFAULT = 1

    TERRAIN = 2

    CLOUDDENSITY = 3

    CLOUDNORMAL = 4

    CABLE = 5

    FENCE = 6

    ENVEFF = 7

    SCRIPT = 8

    WATERFLOW = 9

    WATERFOAM = 10

    WATERFOG = 11

    WATEROCEAN = 12

    WATER = 13

    FOAMOPACITY = 14

    FOAM = 15

    DIFFUSEMIPSHARPEN = 16

    DIFFUSEDETAIL = 17

    DIFFUSEDARK = 18

    DIFFUSEALPHAOPAQUE = 19

    DIFFUSE = 20

    DETAIL = 21

    NORMAL = 22

    SPECULAR = 23

    EMISSIVE = 24

    TINTPALETTE = 25

    SKIPPROCESSING = 26

    DONOTOPTIMIZE = 27

    TEST = 28

class TextureTemplateTypeFlags(enum.Flag):
    NOT_HALF = 1

    HD_SPLIT = 2

    FULL = 4

    MAPS_HALF = 8

class TextureBase:
    @property
    def name(self) -> str: ...

    @name.setter
    def name(self, arg: str, /) -> None: ...

    @property
    def layer_count(self) -> int: ...

    @layer_count.setter
    def layer_count(self, arg: int, /) -> None: ...

    @property
    def template_type(self) -> TextureTemplateType: ...

    @template_type.setter
    def template_type(self, arg: TextureTemplateType, /) -> None: ...

    @property
    def template_flags(self) -> TextureTemplateTypeFlags: ...

    @template_flags.setter
    def template_flags(self, arg: TextureTemplateTypeFlags, /) -> None: ...

    @property
    def is_reference(self) -> bool: ...

class Texture(TextureBase):
    def __init__(self) -> None: ...

    @property
    def width(self) -> int: ...

    @width.setter
    def width(self, arg: int, /) -> None: ...

    @property
    def height(self) -> int: ...

    @height.setter
    def height(self, arg: int, /) -> None: ...

    @property
    def depth(self) -> int: ...

    @depth.setter
    def depth(self, arg: int, /) -> None: ...

    @property
    def type(self) -> TextureType: ...

    @type.setter
    def type(self, arg: TextureType, /) -> None: ...

    @property
    def format(self) -> TextureFormat: ...

    @format.setter
    def format(self, arg: TextureFormat, /) -> None: ...

    @property
    def mips(self) -> pymateria.gta5.TextureMipList: ...

    @mips.setter
    def mips(self, arg: pymateria.gta5.TextureMipList, /) -> None: ...

    @property
    def is_srgb(self) -> bool: ...

    @is_srgb.setter
    def is_srgb(self, arg: bool, /) -> None: ...

    @overload
    def export_dds(self, arg: str | os.PathLike, /) -> None: ...

    @overload
    def export_dds(self, arg: io.IOBase, /) -> None: ...

    @overload
    def export_wic_image(self, arg0: str | os.PathLike, arg1: pymateria.gta5.ImageType, /) -> None: ...

    @overload
    def export_wic_image(self, arg0: io.IOBase, arg1: pymateria.gta5.ImageType, /) -> None: ...

    @overload
    def import_dds(self, arg: str | os.PathLike, /) -> None: ...

    @overload
    def import_dds(self, arg: io.IOBase, /) -> None: ...

    @overload
    def import_wic_image(self, arg: str | os.PathLike, /) -> None: ...

    @overload
    def import_wic_image(self, arg: io.IOBase, /) -> None: ...

    def generate_mips(self, levels: int = 0) -> None: ...

    def __repr__(self) -> str: ...

class TextureReference(TextureBase):
    def __init__(self) -> None: ...

    def __repr__(self) -> str: ...

class TextureDictionary:
    def __init__(self) -> None: ...

    class Map:
        @overload
        def __init__(self) -> None:
            """Default constructor"""

        @overload
        def __init__(self, arg: TextureDictionary.Map) -> None:
            """Copy constructor"""

        @overload
        def __init__(self, arg: dict[pymateria.gta5.HashString, Texture], /) -> None:
            """Construct from a dictionary"""

        def __len__(self) -> int: ...

        def __bool__(self) -> bool:
            """Check whether the map is nonempty"""

        def __repr__(self) -> str: ...

        @overload
        def __contains__(self, arg: pymateria.gta5.HashString, /) -> bool: ...

        @overload
        def __contains__(self, arg: object, /) -> bool: ...

        def __iter__(self) -> Iterator[pymateria.gta5.HashString]: ...

        def __getitem__(self, arg: pymateria.gta5.HashString, /) -> Texture: ...

        def __delitem__(self, arg: pymateria.gta5.HashString, /) -> None: ...

        def clear(self) -> None:
            """Remove all items"""

        def __setitem__(self, arg0: pymateria.gta5.HashString, arg1: Texture, /) -> None: ...

        def update(self, arg: TextureDictionary.Map, /) -> None:
            """Update the map with element from `arg`"""

        def __eq__(self, arg: object, /) -> bool: ...

        def __ne__(self, arg: object, /) -> bool: ...

        class ItemView:
            def __len__(self) -> int: ...

            def __iter__(self) -> Iterator[tuple[pymateria.gta5.HashString, Texture]]: ...

        class KeyView:
            @overload
            def __contains__(self, arg: pymateria.gta5.HashString, /) -> bool: ...

            @overload
            def __contains__(self, arg: object, /) -> bool: ...

            def __len__(self) -> int: ...

            def __iter__(self) -> Iterator[pymateria.gta5.HashString]: ...

        class ValueView:
            def __len__(self) -> int: ...

            def __iter__(self) -> Iterator[Texture]: ...

        def keys(self) -> TextureDictionary.Map.KeyView:
            """Returns an iterable view of the map's keys."""

        def values(self) -> TextureDictionary.Map.ValueView:
            """Returns an iterable view of the map's values."""

        def items(self) -> TextureDictionary.Map.ItemView:
            """Returns an iterable view of the map's items."""

    @property
    def textures(self) -> TextureDictionary.Map: ...

    @textures.setter
    def textures(self, arg: TextureDictionary.Map, /) -> None: ...

    class DeserializationResult(pymateria.SharedResult):
        def __init__(self) -> None: ...

        @property
        def result(self) -> TextureDictionary: ...

        @result.setter
        def result(self, arg: TextureDictionary, /) -> None: ...

        @property
        def deserializer(self) -> pymateria.rsc7.Deserializer: ...

    RSC_VERSION: int = ...
    """Resource version of this asset format."""

    @overload
    @staticmethod
    def import_rsc(file_path: str | os.PathLike, settings: pymateria.ImportSettings | None = None) -> TextureDictionary.DeserializationResult: ...

    @overload
    @staticmethod
    def import_rsc(stream: io.IOBase, settings: pymateria.ImportSettings | None = None) -> TextureDictionary.DeserializationResult: ...

    @overload
    @staticmethod
    def export_rsc(instance: TextureDictionary, file_path: str | os.PathLike, settings: pymateria.ExportSettings | None = None) -> pymateria.SerializationResultRsc7: ...

    @overload
    @staticmethod
    def export_rsc(instance: TextureDictionary, stream: io.IOBase, settings: pymateria.ExportSettings | None = None) -> pymateria.SerializationResultRsc7: ...

class ShaderVariableType(enum.Enum):
    NONE = 0

    INT_DONTUSE = 1

    FLOAT = 2

    VECTOR2 = 3

    VECTOR3 = 4

    VECTOR4 = 5

    TEXTURE = 6

    BOOL_DONTUSE = 7

    MATRIX43 = 8

    MATRIX44 = 9

    STRING = 10

    INT = 11

    INT2 = 12

    INT3 = 13

    INT4 = 14

    STRUCTUREDBUFFER = 15

    SAMPLERSTATE = 16

    UNUSED1 = 17

    UNUSED2 = 18

    UNUSED3 = 19

    UNUSED4 = 20

    UAV_STRUCTURED = 21

    UAV_TEXTURE = 22

    BYTEADDRESSBUFFER = 23

    UAV_BYTEADDRESS = 24

class ShaderLocalInfo:
    def __init__(self, name: str, semantic: str, type: ShaderVariableType) -> None: ...

    @property
    def name(self) -> str: ...

    @name.setter
    def name(self, arg: str, /) -> None: ...

    @property
    def hash(self) -> int: ...

    @hash.setter
    def hash(self, arg: int, /) -> None: ...

    @property
    def semantic(self) -> str: ...

    @semantic.setter
    def semantic(self, arg: str, /) -> None: ...

    @property
    def semantic_hash(self) -> int: ...

    @semantic_hash.setter
    def semantic_hash(self, arg: int, /) -> None: ...

    @property
    def type(self) -> ShaderVariableType: ...

    @type.setter
    def type(self, arg: ShaderVariableType, /) -> None: ...

    @property
    def data_size(self) -> int: ...

    @data_size.setter
    def data_size(self, arg: int, /) -> None: ...

    @property
    def alloc_size(self) -> int: ...

    @alloc_size.setter
    def alloc_size(self, arg: int, /) -> None: ...

    @property
    def register(self) -> int: ...

    @register.setter
    def register(self, arg: int, /) -> None: ...

    @property
    def default_value(self) -> list[int]: ...

    @default_value.setter
    def default_value(self, arg: Sequence[int], /) -> None: ...

    def __repr__(self) -> str: ...

class ShaderInfo:
    def __init__(self) -> None: ...

    @property
    def name(self) -> str: ...

    @name.setter
    def name(self, arg: str, /) -> None: ...

    @property
    def hash(self) -> int: ...

    @hash.setter
    def hash(self, arg: int, /) -> None: ...

    @property
    def locals(self) -> list[ShaderLocalInfo]: ...

    @locals.setter
    def locals(self, arg: Sequence[ShaderLocalInfo], /) -> None: ...

    def get_local(self, name_or_hash: str | int) -> ShaderLocalInfo | None: ...

    def __repr__(self) -> str: ...

class ShaderRegistry:
    def __init__(self, load_defaults: bool = True) -> None: ...

    @overload
    def load_fxc(self, name: str, path: str | os.PathLike) -> None: ...

    @overload
    def load_fxc(self, name: str, stream: io.IOBase) -> None: ...

    def load_defaults(self) -> None: ...

    @property
    def shaders(self) -> dict[int, ShaderInfo]: ...

    def get_shader(self, name_or_hash: str | int) -> ShaderInfo | None: ...

    instance: pymateria.gta5.gen8.ShaderRegistry = ...
    """The global shared ShaderRegistry instance."""

class ShaderParameter:
    def __init__(self) -> None: ...

    @property
    def name(self) -> pymateria.gta5.HashString | None: ...

    @name.setter
    def name(self, arg: pymateria.gta5.HashString | None) -> None: ...

    @property
    def param_register(self) -> int: ...

    @param_register.setter
    def param_register(self, arg: int, /) -> None: ...

    @property
    def sampler_state_set(self) -> int: ...

    @sampler_state_set.setter
    def sampler_state_set(self, arg: int, /) -> None: ...

    @property
    def data(self) -> TextureBase | list[pymateria.Vector4f]: ...

    @data.setter
    def data(self, arg: TextureBase | Sequence[pymateria.Vector4f] | None) -> None: ...

class ShaderParameterList:
    @overload
    def __init__(self) -> None:
        """Default constructor"""

    @overload
    def __init__(self, arg: ShaderParameterList) -> None:
        """Copy constructor"""

    @overload
    def __init__(self, arg: Iterable[ShaderParameter], /) -> None:
        """Construct from an iterable object"""

    def __len__(self) -> int: ...

    def __bool__(self) -> bool:
        """Check whether the vector is nonempty"""

    def __repr__(self) -> str: ...

    def __iter__(self) -> Iterator[ShaderParameter]: ...

    @overload
    def __getitem__(self, arg: int, /) -> ShaderParameter: ...

    @overload
    def __getitem__(self, arg: slice, /) -> ShaderParameterList: ...

    def clear(self) -> None:
        """Remove all items from list."""

    def append(self, arg: ShaderParameter, /) -> None:
        """Append `arg` to the end of the list."""

    def insert(self, arg0: int, arg1: ShaderParameter, /) -> None:
        """Insert object `arg1` before index `arg0`."""

    def pop(self, index: int = -1) -> ShaderParameter:
        """Remove and return item at `index` (default last)."""

    def extend(self, arg: ShaderParameterList, /) -> None:
        """Extend `self` by appending elements from `arg`."""

    @overload
    def __setitem__(self, arg0: int, arg1: ShaderParameter, /) -> None: ...

    @overload
    def __setitem__(self, arg0: slice, arg1: ShaderParameterList, /) -> None: ...

    @overload
    def __delitem__(self, arg: int, /) -> None: ...

    @overload
    def __delitem__(self, arg: slice, /) -> None: ...

    def __eq__(self, arg: object, /) -> bool: ...

    def __ne__(self, arg: object, /) -> bool: ...

    @overload
    def __contains__(self, arg: ShaderParameter, /) -> bool: ...

    @overload
    def __contains__(self, arg: object, /) -> bool: ...

    def count(self, arg: ShaderParameter, /) -> int:
        """Return number of occurrences of `arg`."""

    def remove(self, arg: ShaderParameter, /) -> None:
        """Remove first occurrence of `arg`."""

class Shader:
    def __init__(self) -> None: ...

    @property
    def parameters(self) -> ShaderParameterList: ...

    @parameters.setter
    def parameters(self, arg: ShaderParameterList, /) -> None: ...

    @property
    def basis_shader(self) -> pymateria.gta5.HashString | None: ...

    @basis_shader.setter
    def basis_shader(self, arg: pymateria.gta5.HashString | None) -> None: ...

    @property
    def basis_material(self) -> pymateria.gta5.HashString | None: ...

    @basis_material.setter
    def basis_material(self, arg: pymateria.gta5.HashString | None) -> None: ...

    @property
    def draw_bucket(self) -> pymateria.gta5.ShaderDrawBucket: ...

    @draw_bucket.setter
    def draw_bucket(self, arg: pymateria.gta5.ShaderDrawBucket, /) -> None: ...

    @property
    def draw_bucket_mask(self) -> int: ...

    @draw_bucket_mask.setter
    def draw_bucket_mask(self, arg: int, /) -> None: ...

    @property
    def is_instanced(self) -> bool: ...

    @is_instanced.setter
    def is_instanced(self, arg: bool, /) -> None: ...

class ShaderList:
    @overload
    def __init__(self) -> None:
        """Default constructor"""

    @overload
    def __init__(self, arg: ShaderList) -> None:
        """Copy constructor"""

    @overload
    def __init__(self, arg: Iterable[Shader], /) -> None:
        """Construct from an iterable object"""

    def __len__(self) -> int: ...

    def __bool__(self) -> bool:
        """Check whether the vector is nonempty"""

    def __repr__(self) -> str: ...

    def __iter__(self) -> Iterator[Shader]: ...

    @overload
    def __getitem__(self, arg: int, /) -> Shader: ...

    @overload
    def __getitem__(self, arg: slice, /) -> ShaderList: ...

    def clear(self) -> None:
        """Remove all items from list."""

    def append(self, arg: Shader, /) -> None:
        """Append `arg` to the end of the list."""

    def insert(self, arg0: int, arg1: Shader, /) -> None:
        """Insert object `arg1` before index `arg0`."""

    def pop(self, index: int = -1) -> Shader:
        """Remove and return item at `index` (default last)."""

    def extend(self, arg: ShaderList, /) -> None:
        """Extend `self` by appending elements from `arg`."""

    @overload
    def __setitem__(self, arg0: int, arg1: Shader, /) -> None: ...

    @overload
    def __setitem__(self, arg0: slice, arg1: ShaderList, /) -> None: ...

    @overload
    def __delitem__(self, arg: int, /) -> None: ...

    @overload
    def __delitem__(self, arg: slice, /) -> None: ...

    def __eq__(self, arg: object, /) -> bool: ...

    def __ne__(self, arg: object, /) -> bool: ...

    @overload
    def __contains__(self, arg: Shader, /) -> bool: ...

    @overload
    def __contains__(self, arg: object, /) -> bool: ...

    def count(self, arg: Shader, /) -> int:
        """Return number of occurrences of `arg`."""

    def remove(self, arg: Shader, /) -> None:
        """Remove first occurrence of `arg`."""

class ShaderGroup:
    def __init__(self) -> None: ...

    @property
    def texture_dictionary(self) -> TextureDictionary: ...

    @texture_dictionary.setter
    def texture_dictionary(self, arg: TextureDictionary | None) -> None: ...

    @property
    def shaders(self) -> ShaderList: ...

    @shaders.setter
    def shaders(self, arg: ShaderList, /) -> None: ...

class FvfChannel(enum.Enum):
    POSITION = 0

    WEIGHT = 1

    BINDING = 2

    NORMAL = 3

    DIFFUSE = 4

    SPECULAR = 5

    TEXTURE0 = 6

    TEXTURE1 = 7

    TEXTURE2 = 8

    TEXTURE3 = 9

    TEXTURE4 = 10

    TEXTURE5 = 11

    TEXTURE6 = 12

    TEXTURE7 = 13

    TANGENT0 = 14

    TANGENT1 = 15

    BINORMAL0 = 16

    BINORMAL1 = 17

class FvfDataType(enum.Enum):
    HALF = 0

    HALF2 = 1

    HALF3 = 2

    HALF4 = 3

    FLOAT = 4

    FLOAT2 = 5

    FLOAT3 = 6

    FLOAT4 = 7

    UBYTE4 = 8

    COLOR = 9

    PACKED_NORMAL = 10

    SHORT_UNORM = 11

    SHORT2_UNORM = 12

    BYTE2_UNORM = 13

    SHORT2 = 14

    SHORT4 = 15

class Fvf:
    @overload
    def __init__(self) -> None: ...

    @overload
    def __init__(self, channels: Set[FvfChannel], size_signature: int = 8598872888530528662, pre_transform: bool = False, dynamic_order: bool = False) -> None: ...

    @overload
    def __init__(self, data: int, sizes: int) -> None: ...

    DEFAULT_SIZES: int = ...
    """Default size signature"""

    @property
    def channels(self) -> set[FvfChannel]: ...

    @property
    def size_signature(self) -> int: ...

    @property
    def pre_transform(self) -> bool: ...

    @property
    def dynamic_order(self) -> bool: ...

    @property
    def vertex_data_size(self) -> int: ...

    def is_channel_active(self, arg: FvfChannel, /) -> bool: ...

    def get_channel_size(self, arg: FvfChannel, /) -> int: ...

    def get_channel_offset(self, arg: FvfChannel, /) -> int: ...

    def get_channel_size_type(self, arg: FvfChannel, /) -> FvfDataType: ...

    def is_equal(self, arg: Fvf, /) -> bool: ...

    @property
    def dtype(self) -> dict:
        """
        A NumPy-compatible data-type description of this FVF.

        Returns a dictionary with the following shape: `{'names': [...] 'formats': [...], 'offsets': [...], 'itemsize': ...}`.
        The keys 'names', 'formats', and 'offsets' contain lists with an entry for each active channel. Names match the
        FvfChannel enum names.
        """

class IndexBuffer:
    def __init__(self) -> None: ...

    @property
    def indices(self) -> Annotated[NDArray[numpy.uint16], dict(order='C')]:
        """
        The contents of this index buffer, as a NumPy array of uint16.

        Note that the array references an internal buffer. If this buffer is freed — for
        example, due to overwriting the index buffer — accessing it may result in undefined
        behavior or a potential crash. To avoid such issues, handle the array with care or create
        a copy if necessary.
        """

    @indices.setter
    def indices(self, arg: Annotated[NDArray[numpy.uint16], dict(order='C', writable=False)], /) -> None: ...

class VertexBuffer:
    def __init__(self) -> None: ...

    @property
    def fvf(self) -> Fvf:
        """Flexible vertex format. Defines the layout of a vertex in this buffer."""

    @fvf.setter
    def fvf(self, arg: Fvf, /) -> None: ...

    @property
    def buffer_raw(self) -> Annotated[NDArray[numpy.uint8], dict(order='C')]:
        """
        The raw contents of this vertex buffer, as a NumPy array of bytes.

        Note that the array references an internal buffer. If this buffer is freed — for
        example, due to resizing the vertex buffer — accessing it may result in undefined
        behavior or a potential crash. To avoid such issues, handle the array with care or create
        a copy if necessary.
        """

    @property
    def buffer(self) -> numpy.typing.ArrayLike:
        """
        The contents of this vertex buffer, as a structured NumPy array.

        The array structure is determined by the FVF of this vertex buffer. See Fvf.dtype.

        Note that the array references an internal buffer. If this buffer is freed — for
        example, due to resizing the vertex buffer — accessing it may result in undefined
        behavior or a potential crash. To avoid such issues, handle the array with care or create
        a copy if necessary.
        """

    @property
    def num_vertices(self) -> int: ...

    def resize(self, arg: int, /) -> None: ...

class GeometryList:
    @overload
    def __init__(self) -> None:
        """Default constructor"""

    @overload
    def __init__(self, arg: GeometryList) -> None:
        """Copy constructor"""

    @overload
    def __init__(self, arg: Iterable[Geometry], /) -> None:
        """Construct from an iterable object"""

    def __len__(self) -> int: ...

    def __bool__(self) -> bool:
        """Check whether the vector is nonempty"""

    def __repr__(self) -> str: ...

    def __iter__(self) -> Iterator[Geometry]: ...

    @overload
    def __getitem__(self, arg: int, /) -> Geometry: ...

    @overload
    def __getitem__(self, arg: slice, /) -> GeometryList: ...

    def clear(self) -> None:
        """Remove all items from list."""

    def append(self, arg: Geometry, /) -> None:
        """Append `arg` to the end of the list."""

    def insert(self, arg0: int, arg1: Geometry, /) -> None:
        """Insert object `arg1` before index `arg0`."""

    def pop(self, index: int = -1) -> Geometry:
        """Remove and return item at `index` (default last)."""

    def extend(self, arg: GeometryList, /) -> None:
        """Extend `self` by appending elements from `arg`."""

    @overload
    def __setitem__(self, arg0: int, arg1: Geometry, /) -> None: ...

    @overload
    def __setitem__(self, arg0: slice, arg1: GeometryList, /) -> None: ...

    @overload
    def __delitem__(self, arg: int, /) -> None: ...

    @overload
    def __delitem__(self, arg: slice, /) -> None: ...

    def __eq__(self, arg: object, /) -> bool: ...

    def __ne__(self, arg: object, /) -> bool: ...

    @overload
    def __contains__(self, arg: Geometry, /) -> bool: ...

    @overload
    def __contains__(self, arg: object, /) -> bool: ...

    def count(self, arg: Geometry, /) -> int:
        """Return number of occurrences of `arg`."""

    def remove(self, arg: Geometry, /) -> None:
        """Remove first occurrence of `arg`."""

class Geometry:
    def __init__(self) -> None: ...

    @property
    def shader(self) -> Shader: ...

    @shader.setter
    def shader(self, arg: Shader, /) -> None: ...

    @property
    def primitive_type(self) -> pymateria.gta5.PrimitiveType: ...

    @primitive_type.setter
    def primitive_type(self, arg: pymateria.gta5.PrimitiveType, /) -> None: ...

    @property
    def matrix_palette(self) -> list[int]: ...

    @matrix_palette.setter
    def matrix_palette(self, arg: Sequence[int], /) -> None: ...

    @property
    def ib(self) -> IndexBuffer: ...

    @ib.setter
    def ib(self, arg: IndexBuffer, /) -> None: ...

    @property
    def vb(self) -> VertexBuffer: ...

    @vb.setter
    def vb(self, arg: VertexBuffer, /) -> None: ...

    def calculate_aabbs(self) -> pymateria.AABB3f: ...

class ModelList:
    @overload
    def __init__(self) -> None:
        """Default constructor"""

    @overload
    def __init__(self, arg: ModelList) -> None:
        """Copy constructor"""

    @overload
    def __init__(self, arg: Iterable[Model], /) -> None:
        """Construct from an iterable object"""

    def __len__(self) -> int: ...

    def __bool__(self) -> bool:
        """Check whether the vector is nonempty"""

    def __repr__(self) -> str: ...

    def __iter__(self) -> Iterator[Model]: ...

    @overload
    def __getitem__(self, arg: int, /) -> Model: ...

    @overload
    def __getitem__(self, arg: slice, /) -> ModelList: ...

    def clear(self) -> None:
        """Remove all items from list."""

    def append(self, arg: Model, /) -> None:
        """Append `arg` to the end of the list."""

    def insert(self, arg0: int, arg1: Model, /) -> None:
        """Insert object `arg1` before index `arg0`."""

    def pop(self, index: int = -1) -> Model:
        """Remove and return item at `index` (default last)."""

    def extend(self, arg: ModelList, /) -> None:
        """Extend `self` by appending elements from `arg`."""

    @overload
    def __setitem__(self, arg0: int, arg1: Model, /) -> None: ...

    @overload
    def __setitem__(self, arg0: slice, arg1: ModelList, /) -> None: ...

    @overload
    def __delitem__(self, arg: int, /) -> None: ...

    @overload
    def __delitem__(self, arg: slice, /) -> None: ...

    def __eq__(self, arg: object, /) -> bool: ...

    def __ne__(self, arg: object, /) -> bool: ...

    @overload
    def __contains__(self, arg: Model, /) -> bool: ...

    @overload
    def __contains__(self, arg: object, /) -> bool: ...

    def count(self, arg: Model, /) -> int:
        """Return number of occurrences of `arg`."""

    def remove(self, arg: Model, /) -> None:
        """Remove first occurrence of `arg`."""

class Model:
    def __init__(self) -> None: ...

    @property
    def geometries(self) -> GeometryList: ...

    @geometries.setter
    def geometries(self, arg: GeometryList, /) -> None: ...

    @property
    def render_bucket_mask(self) -> int: ...

    @render_bucket_mask.setter
    def render_bucket_mask(self, arg: int, /) -> None: ...

    @property
    def flags(self) -> pymateria.gta5.ModelFlags: ...

    @flags.setter
    def flags(self, arg: pymateria.gta5.ModelFlags, /) -> None: ...

    @property
    def has_skin(self) -> bool: ...

    @has_skin.setter
    def has_skin(self, arg: bool, /) -> None: ...

    @property
    def matrix_count(self) -> int: ...

    @matrix_count.setter
    def matrix_count(self, arg: int, /) -> None: ...

    @property
    def matrix_index(self) -> int: ...

    @matrix_index.setter
    def matrix_index(self, arg: int, /) -> None: ...

    def calculate_aabbs(self) -> pymateria.AABB3f: ...

class LodMap:
    @overload
    def __init__(self) -> None:
        """Default constructor"""

    @overload
    def __init__(self, arg: LodMap) -> None:
        """Copy constructor"""

    @overload
    def __init__(self, arg: dict[pymateria.gta5.LodType, Lod], /) -> None:
        """Construct from a dictionary"""

    def __len__(self) -> int: ...

    def __bool__(self) -> bool:
        """Check whether the map is nonempty"""

    def __repr__(self) -> str: ...

    @overload
    def __contains__(self, arg: pymateria.gta5.LodType, /) -> bool: ...

    @overload
    def __contains__(self, arg: object, /) -> bool: ...

    def __iter__(self) -> Iterator[pymateria.gta5.LodType]: ...

    def __getitem__(self, arg: pymateria.gta5.LodType, /) -> Lod: ...

    def __delitem__(self, arg: pymateria.gta5.LodType, /) -> None: ...

    def clear(self) -> None:
        """Remove all items"""

    def __setitem__(self, arg0: pymateria.gta5.LodType, arg1: Lod, /) -> None: ...

    def update(self, arg: LodMap, /) -> None:
        """Update the map with element from `arg`"""

    def __eq__(self, arg: object, /) -> bool: ...

    def __ne__(self, arg: object, /) -> bool: ...

    class ItemView:
        def __len__(self) -> int: ...

        def __iter__(self) -> Iterator[tuple[pymateria.gta5.LodType, Lod]]: ...

    class KeyView:
        @overload
        def __contains__(self, arg: pymateria.gta5.LodType, /) -> bool: ...

        @overload
        def __contains__(self, arg: object, /) -> bool: ...

        def __len__(self) -> int: ...

        def __iter__(self) -> Iterator[pymateria.gta5.LodType]: ...

    class ValueView:
        def __len__(self) -> int: ...

        def __iter__(self) -> Iterator[Lod]: ...

    def keys(self) -> LodMap.KeyView:
        """Returns an iterable view of the map's keys."""

    def values(self) -> LodMap.ValueView:
        """Returns an iterable view of the map's values."""

    def items(self) -> LodMap.ItemView:
        """Returns an iterable view of the map's items."""

class Lod:
    def __init__(self) -> None: ...

    @property
    def models(self) -> ModelList: ...

    @models.setter
    def models(self, arg: ModelList, /) -> None: ...

    @property
    def lod_threshold(self) -> float: ...

    @lod_threshold.setter
    def lod_threshold(self, arg: float, /) -> None: ...

    def calculate_bucket_mask(self) -> int: ...

    def calculate_aabbs(self) -> pymateria.AABB3f: ...

class BaseDrawable:
    @property
    def name(self) -> str: ...

    @name.setter
    def name(self, arg: str, /) -> None: ...

    @property
    def aabb_offset(self) -> pymateria.AABB3f: ...

    @aabb_offset.setter
    def aabb_offset(self, arg: pymateria.AABB3f, /) -> None: ...

    @property
    def lods(self) -> LodMap: ...

    @lods.setter
    def lods(self, arg: LodMap, /) -> None: ...

    @property
    def shader_group(self) -> ShaderGroup: ...

    @shader_group.setter
    def shader_group(self, arg: ShaderGroup | None) -> None: ...

    @property
    def skeleton(self) -> pymateria.gta5.Skeleton: ...

    @skeleton.setter
    def skeleton(self, arg: pymateria.gta5.Skeleton | None) -> None: ...

    @property
    def include_joint_data(self) -> bool: ...

    @include_joint_data.setter
    def include_joint_data(self, arg: bool, /) -> None: ...

    def calculate_aabbs(self) -> pymateria.AABB3f: ...

class Drawable(BaseDrawable):
    def __init__(self) -> None: ...

    @property
    def bound(self) -> pymateria.gta5.Bound: ...

    @bound.setter
    def bound(self, arg: pymateria.gta5.Bound | None) -> None: ...

    @property
    def lights(self) -> pymateria.gta5.LightList: ...

    @lights.setter
    def lights(self, arg: pymateria.gta5.LightList, /) -> None: ...

    class DeserializationResult(pymateria.SharedResult):
        def __init__(self) -> None: ...

        @property
        def result(self) -> Drawable: ...

        @result.setter
        def result(self, arg: Drawable, /) -> None: ...

        @property
        def deserializer(self) -> pymateria.rsc7.Deserializer: ...

    RSC_VERSION: int = ...
    """Resource version of this asset format."""

    @overload
    @staticmethod
    def import_rsc(file_path: str | os.PathLike, settings: pymateria.ImportSettings | None = None) -> Drawable.DeserializationResult: ...

    @overload
    @staticmethod
    def import_rsc(stream: io.IOBase, settings: pymateria.ImportSettings | None = None) -> Drawable.DeserializationResult: ...

    @overload
    @staticmethod
    def export_rsc(instance: Drawable, file_path: str | os.PathLike, settings: pymateria.ExportSettings | None = None) -> pymateria.SerializationResultRsc7: ...

    @overload
    @staticmethod
    def export_rsc(instance: Drawable, stream: io.IOBase, settings: pymateria.ExportSettings | None = None) -> pymateria.SerializationResultRsc7: ...

    def __repr__(self) -> str: ...

class DrawableDictionary:
    def __init__(self) -> None: ...

    class Map:
        @overload
        def __init__(self) -> None:
            """Default constructor"""

        @overload
        def __init__(self, arg: DrawableDictionary.Map) -> None:
            """Copy constructor"""

        @overload
        def __init__(self, arg: dict[pymateria.gta5.HashString, Drawable], /) -> None:
            """Construct from a dictionary"""

        def __len__(self) -> int: ...

        def __bool__(self) -> bool:
            """Check whether the map is nonempty"""

        def __repr__(self) -> str: ...

        @overload
        def __contains__(self, arg: pymateria.gta5.HashString, /) -> bool: ...

        @overload
        def __contains__(self, arg: object, /) -> bool: ...

        def __iter__(self) -> Iterator[pymateria.gta5.HashString]: ...

        def __getitem__(self, arg: pymateria.gta5.HashString, /) -> Drawable: ...

        def __delitem__(self, arg: pymateria.gta5.HashString, /) -> None: ...

        def clear(self) -> None:
            """Remove all items"""

        def __setitem__(self, arg0: pymateria.gta5.HashString, arg1: Drawable, /) -> None: ...

        def update(self, arg: DrawableDictionary.Map, /) -> None:
            """Update the map with element from `arg`"""

        def __eq__(self, arg: object, /) -> bool: ...

        def __ne__(self, arg: object, /) -> bool: ...

        class ItemView:
            def __len__(self) -> int: ...

            def __iter__(self) -> Iterator[tuple[pymateria.gta5.HashString, Drawable]]: ...

        class KeyView:
            @overload
            def __contains__(self, arg: pymateria.gta5.HashString, /) -> bool: ...

            @overload
            def __contains__(self, arg: object, /) -> bool: ...

            def __len__(self) -> int: ...

            def __iter__(self) -> Iterator[pymateria.gta5.HashString]: ...

        class ValueView:
            def __len__(self) -> int: ...

            def __iter__(self) -> Iterator[Drawable]: ...

        def keys(self) -> DrawableDictionary.Map.KeyView:
            """Returns an iterable view of the map's keys."""

        def values(self) -> DrawableDictionary.Map.ValueView:
            """Returns an iterable view of the map's values."""

        def items(self) -> DrawableDictionary.Map.ItemView:
            """Returns an iterable view of the map's items."""

    @property
    def drawables(self) -> DrawableDictionary.Map: ...

    @drawables.setter
    def drawables(self, arg: DrawableDictionary.Map, /) -> None: ...

    class DeserializationResult(pymateria.SharedResult):
        def __init__(self) -> None: ...

        @property
        def result(self) -> DrawableDictionary: ...

        @result.setter
        def result(self, arg: DrawableDictionary, /) -> None: ...

        @property
        def deserializer(self) -> pymateria.rsc7.Deserializer: ...

    RSC_VERSION: int = ...
    """Resource version of this asset format."""

    @overload
    @staticmethod
    def import_rsc(file_path: str | os.PathLike, settings: pymateria.ImportSettings | None = None) -> DrawableDictionary.DeserializationResult: ...

    @overload
    @staticmethod
    def import_rsc(stream: io.IOBase, settings: pymateria.ImportSettings | None = None) -> DrawableDictionary.DeserializationResult: ...

    @overload
    @staticmethod
    def export_rsc(instance: DrawableDictionary, file_path: str | os.PathLike, settings: pymateria.ExportSettings | None = None) -> pymateria.SerializationResultRsc7: ...

    @overload
    @staticmethod
    def export_rsc(instance: DrawableDictionary, stream: io.IOBase, settings: pymateria.ExportSettings | None = None) -> pymateria.SerializationResultRsc7: ...

class FragmentDrawable(BaseDrawable):
    def __init__(self) -> None: ...

    @property
    def bound(self) -> pymateria.gta5.Bound: ...

    @bound.setter
    def bound(self, arg: pymateria.gta5.Bound | None) -> None: ...

    @property
    def bound_matrix(self) -> pymateria.Matrix34: ...

    @bound_matrix.setter
    def bound_matrix(self, arg: pymateria.Matrix34, /) -> None: ...

    @property
    def extra_bounds(self) -> list[pymateria.gta5.ExtraBound]: ...

    @extra_bounds.setter
    def extra_bounds(self, arg: Sequence[pymateria.gta5.ExtraBound], /) -> None: ...

    @property
    def skeleton_type(self) -> pymateria.gta5.SkeletonType: ...

    @skeleton_type.setter
    def skeleton_type(self, arg: pymateria.gta5.SkeletonType, /) -> None: ...

    def __repr__(self) -> str: ...

class FragmentDrawableList:
    @overload
    def __init__(self) -> None:
        """Default constructor"""

    @overload
    def __init__(self, arg: FragmentDrawableList) -> None:
        """Copy constructor"""

    @overload
    def __init__(self, arg: Iterable[FragmentDrawable], /) -> None:
        """Construct from an iterable object"""

    def __len__(self) -> int: ...

    def __bool__(self) -> bool:
        """Check whether the vector is nonempty"""

    def __repr__(self) -> str: ...

    def __iter__(self) -> Iterator[FragmentDrawable]: ...

    @overload
    def __getitem__(self, arg: int, /) -> FragmentDrawable: ...

    @overload
    def __getitem__(self, arg: slice, /) -> FragmentDrawableList: ...

    def clear(self) -> None:
        """Remove all items from list."""

    def append(self, arg: FragmentDrawable, /) -> None:
        """Append `arg` to the end of the list."""

    def insert(self, arg0: int, arg1: FragmentDrawable, /) -> None:
        """Insert object `arg1` before index `arg0`."""

    def pop(self, index: int = -1) -> FragmentDrawable:
        """Remove and return item at `index` (default last)."""

    def extend(self, arg: FragmentDrawableList, /) -> None:
        """Extend `self` by appending elements from `arg`."""

    @overload
    def __setitem__(self, arg0: int, arg1: FragmentDrawable, /) -> None: ...

    @overload
    def __setitem__(self, arg0: slice, arg1: FragmentDrawableList, /) -> None: ...

    @overload
    def __delitem__(self, arg: int, /) -> None: ...

    @overload
    def __delitem__(self, arg: slice, /) -> None: ...

    def __eq__(self, arg: object, /) -> bool: ...

    def __ne__(self, arg: object, /) -> bool: ...

    @overload
    def __contains__(self, arg: FragmentDrawable, /) -> bool: ...

    @overload
    def __contains__(self, arg: object, /) -> bool: ...

    def count(self, arg: FragmentDrawable, /) -> int:
        """Return number of occurrences of `arg`."""

    def remove(self, arg: FragmentDrawable, /) -> None:
        """Remove first occurrence of `arg`."""

class FragmentTypeChild:
    def __init__(self) -> None: ...

    @property
    def undamaged_mass(self) -> float: ...

    @undamaged_mass.setter
    def undamaged_mass(self, arg: float, /) -> None: ...

    @property
    def damaged_mass(self) -> float: ...

    @damaged_mass.setter
    def damaged_mass(self, arg: float, /) -> None: ...

    @property
    def owner_group_pointer_index(self) -> int: ...

    @owner_group_pointer_index.setter
    def owner_group_pointer_index(self, arg: int, /) -> None: ...

    @property
    def flags(self) -> int: ...

    @flags.setter
    def flags(self, arg: int, /) -> None: ...

    @property
    def bone_id(self) -> int: ...

    @bone_id.setter
    def bone_id(self, arg: int, /) -> None: ...

    @property
    def enable_continuous_event_set(self) -> bool: ...

    @enable_continuous_event_set.setter
    def enable_continuous_event_set(self, arg: bool, /) -> None: ...

    @property
    def enable_collision_event_set(self) -> bool: ...

    @enable_collision_event_set.setter
    def enable_collision_event_set(self, arg: bool, /) -> None: ...

    @property
    def enable_break_event_set(self) -> bool: ...

    @enable_break_event_set.setter
    def enable_break_event_set(self, arg: bool, /) -> None: ...

    @property
    def enable_break_from_root_event_set(self) -> bool: ...

    @enable_break_from_root_event_set.setter
    def enable_break_from_root_event_set(self, arg: bool, /) -> None: ...

    @property
    def undamaged_entity(self) -> FragmentDrawable: ...

    @undamaged_entity.setter
    def undamaged_entity(self, arg: FragmentDrawable | None) -> None: ...

    @property
    def damaged_entity(self) -> FragmentDrawable: ...

    @damaged_entity.setter
    def damaged_entity(self, arg: FragmentDrawable | None) -> None: ...

class FragmentTypeChildList:
    @overload
    def __init__(self) -> None:
        """Default constructor"""

    @overload
    def __init__(self, arg: FragmentTypeChildList) -> None:
        """Copy constructor"""

    @overload
    def __init__(self, arg: Iterable[FragmentTypeChild], /) -> None:
        """Construct from an iterable object"""

    def __len__(self) -> int: ...

    def __bool__(self) -> bool:
        """Check whether the vector is nonempty"""

    def __repr__(self) -> str: ...

    def __iter__(self) -> Iterator[FragmentTypeChild]: ...

    @overload
    def __getitem__(self, arg: int, /) -> FragmentTypeChild: ...

    @overload
    def __getitem__(self, arg: slice, /) -> FragmentTypeChildList: ...

    def clear(self) -> None:
        """Remove all items from list."""

    def append(self, arg: FragmentTypeChild, /) -> None:
        """Append `arg` to the end of the list."""

    def insert(self, arg0: int, arg1: FragmentTypeChild, /) -> None:
        """Insert object `arg1` before index `arg0`."""

    def pop(self, index: int = -1) -> FragmentTypeChild:
        """Remove and return item at `index` (default last)."""

    def extend(self, arg: FragmentTypeChildList, /) -> None:
        """Extend `self` by appending elements from `arg`."""

    @overload
    def __setitem__(self, arg0: int, arg1: FragmentTypeChild, /) -> None: ...

    @overload
    def __setitem__(self, arg0: slice, arg1: FragmentTypeChildList, /) -> None: ...

    @overload
    def __delitem__(self, arg: int, /) -> None: ...

    @overload
    def __delitem__(self, arg: slice, /) -> None: ...

    def __eq__(self, arg: object, /) -> bool: ...

    def __ne__(self, arg: object, /) -> bool: ...

    @overload
    def __contains__(self, arg: FragmentTypeChild, /) -> bool: ...

    @overload
    def __contains__(self, arg: object, /) -> bool: ...

    def count(self, arg: FragmentTypeChild, /) -> int:
        """Return number of occurrences of `arg`."""

    def remove(self, arg: FragmentTypeChild, /) -> None:
        """Remove first occurrence of `arg`."""

class FragmentPhysicsLod:
    def __init__(self) -> None: ...

    @property
    def smallest_ang_inertia(self) -> float: ...

    @smallest_ang_inertia.setter
    def smallest_ang_inertia(self, arg: float, /) -> None: ...

    @property
    def largest_ang_inertia(self) -> float: ...

    @largest_ang_inertia.setter
    def largest_ang_inertia(self, arg: float, /) -> None: ...

    @property
    def min_move_force(self) -> float: ...

    @min_move_force.setter
    def min_move_force(self, arg: float, /) -> None: ...

    @property
    def body_type(self) -> pymateria.gta5.FragmentPhArticulatedBodyType: ...

    @body_type.setter
    def body_type(self, arg: pymateria.gta5.FragmentPhArticulatedBodyType | None) -> None: ...

    @property
    def min_breaking_impulses(self) -> list[float]: ...

    @min_breaking_impulses.setter
    def min_breaking_impulses(self, arg: Sequence[float], /) -> None: ...

    @property
    def root_cg_offset(self) -> pymateria.Vector3f: ...

    @root_cg_offset.setter
    def root_cg_offset(self, arg: pymateria.Vector3f, /) -> None: ...

    @property
    def original_root_cg_offset(self) -> pymateria.Vector3f: ...

    @original_root_cg_offset.setter
    def original_root_cg_offset(self, arg: pymateria.Vector3f, /) -> None: ...

    @property
    def unbroken_cg_offset(self) -> pymateria.Vector3f: ...

    @unbroken_cg_offset.setter
    def unbroken_cg_offset(self, arg: pymateria.Vector3f, /) -> None: ...

    @property
    def damping_constant(self) -> tuple[pymateria.Vector3f, pymateria.Vector3f, pymateria.Vector3f, pymateria.Vector3f, pymateria.Vector3f, pymateria.Vector3f]: ...

    @damping_constant.setter
    def damping_constant(self, arg: tuple[pymateria.Vector3f, pymateria.Vector3f, pymateria.Vector3f, pymateria.Vector3f, pymateria.Vector3f, pymateria.Vector3f], /) -> None: ...

    @property
    def group_names(self) -> list[str]: ...

    @group_names.setter
    def group_names(self, arg: Sequence[str], /) -> None: ...

    @property
    def groups(self) -> pymateria.gta5.FragmentTypeGroupList: ...

    @groups.setter
    def groups(self, arg: pymateria.gta5.FragmentTypeGroupList, /) -> None: ...

    @property
    def children(self) -> FragmentTypeChildList: ...

    @children.setter
    def children(self, arg: FragmentTypeChildList, /) -> None: ...

    @property
    def phys_damp_undamaged(self) -> pymateria.gta5.FragmentPhArchetypeDamp: ...

    @phys_damp_undamaged.setter
    def phys_damp_undamaged(self, arg: pymateria.gta5.FragmentPhArchetypeDamp | None) -> None: ...

    @property
    def phys_damp_damaged(self) -> pymateria.gta5.FragmentPhArchetypeDamp: ...

    @phys_damp_damaged.setter
    def phys_damp_damaged(self, arg: pymateria.gta5.FragmentPhArchetypeDamp | None) -> None: ...

    @property
    def composite_bounds(self) -> pymateria.gta5.BoundComposite: ...

    @composite_bounds.setter
    def composite_bounds(self, arg: pymateria.gta5.BoundComposite | None) -> None: ...

    @property
    def undamaged_ang_inertia(self) -> list[pymateria.Vector3f]: ...

    @undamaged_ang_inertia.setter
    def undamaged_ang_inertia(self, arg: Sequence[pymateria.Vector3f], /) -> None: ...

    @property
    def damaged_ang_inertia(self) -> list[pymateria.Vector3f]: ...

    @damaged_ang_inertia.setter
    def damaged_ang_inertia(self, arg: Sequence[pymateria.Vector3f], /) -> None: ...

    @property
    def link_attachments(self) -> list[pymateria.Matrix34]: ...

    @link_attachments.setter
    def link_attachments(self, arg: Sequence[pymateria.Matrix34], /) -> None: ...

    @property
    def self_collisions(self) -> list[tuple[int, int]]: ...

    @self_collisions.setter
    def self_collisions(self, arg: Sequence[tuple[int, int]], /) -> None: ...

    @property
    def root_group_count(self) -> int: ...

    @root_group_count.setter
    def root_group_count(self, arg: int, /) -> None: ...

    @property
    def num_root_damage_regions(self) -> int: ...

    @num_root_damage_regions.setter
    def num_root_damage_regions(self, arg: int, /) -> None: ...

    @property
    def num_bony_children(self) -> int: ...

    @num_bony_children.setter
    def num_bony_children(self, arg: int, /) -> None: ...

class FragmentPhysicsLodGroup:
    def __init__(self) -> None: ...

    @property
    def high_lod(self) -> FragmentPhysicsLod: ...

    @high_lod.setter
    def high_lod(self, arg: FragmentPhysicsLod | None) -> None: ...

    @property
    def medium_lod(self) -> FragmentPhysicsLod: ...

    @medium_lod.setter
    def medium_lod(self, arg: FragmentPhysicsLod | None) -> None: ...

    @property
    def low_lod(self) -> FragmentPhysicsLod: ...

    @low_lod.setter
    def low_lod(self, arg: FragmentPhysicsLod | None) -> None: ...

class BGPaneModelInfoBase:
    def __init__(self) -> None: ...

    @property
    def pos_base(self) -> pymateria.Vector3f: ...

    @pos_base.setter
    def pos_base(self, arg: pymateria.Vector3f, /) -> None: ...

    @property
    def pos_width(self) -> pymateria.Vector3f: ...

    @pos_width.setter
    def pos_width(self, arg: pymateria.Vector3f, /) -> None: ...

    @property
    def pos_height(self) -> pymateria.Vector3f: ...

    @pos_height.setter
    def pos_height(self, arg: pymateria.Vector3f, /) -> None: ...

    @property
    def uv_min(self) -> pymateria.UV: ...

    @uv_min.setter
    def uv_min(self, arg: pymateria.UV, /) -> None: ...

    @property
    def uv_max(self) -> pymateria.UV: ...

    @uv_max.setter
    def uv_max(self, arg: pymateria.UV, /) -> None: ...

    @property
    def thickness(self) -> float: ...

    @thickness.setter
    def thickness(self, arg: float, /) -> None: ...

    @property
    def flags(self) -> int: ...

    @flags.setter
    def flags(self, arg: int, /) -> None: ...

    @property
    def glass_type(self) -> int: ...

    @glass_type.setter
    def glass_type(self, arg: int, /) -> None: ...

    @property
    def shader_index(self) -> int: ...

    @shader_index.setter
    def shader_index(self, arg: int, /) -> None: ...

    @property
    def bounds_offset_front(self) -> float: ...

    @bounds_offset_front.setter
    def bounds_offset_front(self, arg: float, /) -> None: ...

    @property
    def bounds_offset_back(self) -> float: ...

    @bounds_offset_back.setter
    def bounds_offset_back(self, arg: float, /) -> None: ...

    @property
    def tangent(self) -> pymateria.Vector3f: ...

    @tangent.setter
    def tangent(self, arg: pymateria.Vector3f, /) -> None: ...

    @property
    def fvf(self) -> Fvf: ...

    @fvf.setter
    def fvf(self, arg: Fvf, /) -> None: ...

class BGPaneModelInfoBaseList:
    @overload
    def __init__(self) -> None:
        """Default constructor"""

    @overload
    def __init__(self, arg: BGPaneModelInfoBaseList) -> None:
        """Copy constructor"""

    @overload
    def __init__(self, arg: Iterable[BGPaneModelInfoBase], /) -> None:
        """Construct from an iterable object"""

    def __len__(self) -> int: ...

    def __bool__(self) -> bool:
        """Check whether the vector is nonempty"""

    def __repr__(self) -> str: ...

    def __iter__(self) -> Iterator[BGPaneModelInfoBase]: ...

    @overload
    def __getitem__(self, arg: int, /) -> BGPaneModelInfoBase: ...

    @overload
    def __getitem__(self, arg: slice, /) -> BGPaneModelInfoBaseList: ...

    def clear(self) -> None:
        """Remove all items from list."""

    def append(self, arg: BGPaneModelInfoBase, /) -> None:
        """Append `arg` to the end of the list."""

    def insert(self, arg0: int, arg1: BGPaneModelInfoBase, /) -> None:
        """Insert object `arg1` before index `arg0`."""

    def pop(self, index: int = -1) -> BGPaneModelInfoBase:
        """Remove and return item at `index` (default last)."""

    def extend(self, arg: BGPaneModelInfoBaseList, /) -> None:
        """Extend `self` by appending elements from `arg`."""

    @overload
    def __setitem__(self, arg0: int, arg1: BGPaneModelInfoBase, /) -> None: ...

    @overload
    def __setitem__(self, arg0: slice, arg1: BGPaneModelInfoBaseList, /) -> None: ...

    @overload
    def __delitem__(self, arg: int, /) -> None: ...

    @overload
    def __delitem__(self, arg: slice, /) -> None: ...

    def __eq__(self, arg: object, /) -> bool: ...

    def __ne__(self, arg: object, /) -> bool: ...

    @overload
    def __contains__(self, arg: BGPaneModelInfoBase, /) -> bool: ...

    @overload
    def __contains__(self, arg: object, /) -> bool: ...

    def count(self, arg: BGPaneModelInfoBase, /) -> int:
        """Return number of occurrences of `arg`."""

    def remove(self, arg: BGPaneModelInfoBase, /) -> None:
        """Remove first occurrence of `arg`."""

class VehicleWindow:
    def __init__(self) -> None: ...

    @property
    def window_proxies(self) -> pymateria.gta5.WindowProxyList: ...

    @window_proxies.setter
    def window_proxies(self, arg: pymateria.gta5.WindowProxyList, /) -> None: ...

    def generate_vehicle_windows(self, drawable: FragmentDrawable, bound_composite: pymateria.gta5.BoundComposite, fragment_type_children: FragmentTypeChildList) -> None: ...

class FragmentEnvCloth:
    def __init__(self) -> None: ...

    @property
    def tuning(self) -> pymateria.gta5.FragmentEnvClothTuning: ...

    @tuning.setter
    def tuning(self, arg: pymateria.gta5.FragmentEnvClothTuning | None) -> None: ...

    @property
    def referenced_drawable(self) -> FragmentDrawable: ...

    @referenced_drawable.setter
    def referenced_drawable(self, arg: FragmentDrawable | None) -> None: ...

    @property
    def controller(self) -> pymateria.gta5.ClothController: ...

    @controller.setter
    def controller(self, arg: pymateria.gta5.ClothController | None) -> None: ...

    @property
    def flags(self) -> int: ...

    @flags.setter
    def flags(self, arg: int, /) -> None: ...

    @property
    def user_data(self) -> list[int]: ...

    @user_data.setter
    def user_data(self, arg: Sequence[int], /) -> None: ...

class FragmentEnvClothList:
    @overload
    def __init__(self) -> None:
        """Default constructor"""

    @overload
    def __init__(self, arg: FragmentEnvClothList) -> None:
        """Copy constructor"""

    @overload
    def __init__(self, arg: Iterable[FragmentEnvCloth], /) -> None:
        """Construct from an iterable object"""

    def __len__(self) -> int: ...

    def __bool__(self) -> bool:
        """Check whether the vector is nonempty"""

    def __repr__(self) -> str: ...

    def __iter__(self) -> Iterator[FragmentEnvCloth]: ...

    @overload
    def __getitem__(self, arg: int, /) -> FragmentEnvCloth: ...

    @overload
    def __getitem__(self, arg: slice, /) -> FragmentEnvClothList: ...

    def clear(self) -> None:
        """Remove all items from list."""

    def append(self, arg: FragmentEnvCloth, /) -> None:
        """Append `arg` to the end of the list."""

    def insert(self, arg0: int, arg1: FragmentEnvCloth, /) -> None:
        """Insert object `arg1` before index `arg0`."""

    def pop(self, index: int = -1) -> FragmentEnvCloth:
        """Remove and return item at `index` (default last)."""

    def extend(self, arg: FragmentEnvClothList, /) -> None:
        """Extend `self` by appending elements from `arg`."""

    @overload
    def __setitem__(self, arg0: int, arg1: FragmentEnvCloth, /) -> None: ...

    @overload
    def __setitem__(self, arg0: slice, arg1: FragmentEnvClothList, /) -> None: ...

    @overload
    def __delitem__(self, arg: int, /) -> None: ...

    @overload
    def __delitem__(self, arg: slice, /) -> None: ...

    def __eq__(self, arg: object, /) -> bool: ...

    def __ne__(self, arg: object, /) -> bool: ...

    @overload
    def __contains__(self, arg: FragmentEnvCloth, /) -> bool: ...

    @overload
    def __contains__(self, arg: object, /) -> bool: ...

    def count(self, arg: FragmentEnvCloth, /) -> int:
        """Return number of occurrences of `arg`."""

    def remove(self, arg: FragmentEnvCloth, /) -> None:
        """Remove first occurrence of `arg`."""

class Fragment:
    def __init__(self) -> None: ...

    @property
    def bounding_sphere(self) -> pymateria.Sphere: ...

    @bounding_sphere.setter
    def bounding_sphere(self, arg: pymateria.Sphere, /) -> None: ...

    @property
    def tune_name(self) -> str: ...

    @tune_name.setter
    def tune_name(self, arg: str, /) -> None: ...

    @property
    def drawable(self) -> FragmentDrawable: ...

    @drawable.setter
    def drawable(self, arg: FragmentDrawable | None) -> None: ...

    @property
    def extra_drawables(self) -> FragmentDrawableList: ...

    @extra_drawables.setter
    def extra_drawables(self, arg: FragmentDrawableList, /) -> None: ...

    @property
    def extra_drawable_names(self) -> list[str]: ...

    @extra_drawable_names.setter
    def extra_drawable_names(self, arg: Sequence[str], /) -> None: ...

    @property
    def root_child(self) -> FragmentTypeChild: ...

    @root_child.setter
    def root_child(self, arg: FragmentTypeChild | None) -> None: ...

    @property
    def physics_lod_group(self) -> FragmentPhysicsLodGroup: ...

    @physics_lod_group.setter
    def physics_lod_group(self, arg: FragmentPhysicsLodGroup | None) -> None: ...

    @property
    def common_cloth_drawable(self) -> FragmentDrawable: ...

    @common_cloth_drawable.setter
    def common_cloth_drawable(self, arg: FragmentDrawable | None) -> None: ...

    @property
    def environment_cloths(self) -> FragmentEnvClothList: ...

    @environment_cloths.setter
    def environment_cloths(self, arg: FragmentEnvClothList, /) -> None: ...

    @property
    def glass_pane_model_infos(self) -> BGPaneModelInfoBaseList: ...

    @glass_pane_model_infos.setter
    def glass_pane_model_infos(self, arg: BGPaneModelInfoBaseList, /) -> None: ...

    @property
    def enable_collision_event_set(self) -> bool: ...

    @enable_collision_event_set.setter
    def enable_collision_event_set(self, arg: bool, /) -> None: ...

    @property
    def enable_collision_event_player(self) -> bool: ...

    @enable_collision_event_player.setter
    def enable_collision_event_player(self, arg: bool, /) -> None: ...

    @property
    def shared_matrix_set(self) -> pymateria.gta5.MatrixSet: ...

    @shared_matrix_set.setter
    def shared_matrix_set(self, arg: pymateria.gta5.MatrixSet | None) -> None: ...

    @property
    def entity_class(self) -> int: ...

    @entity_class.setter
    def entity_class(self, arg: int, /) -> None: ...

    @property
    def art_asset_id(self) -> int: ...

    @art_asset_id.setter
    def art_asset_id(self, arg: int, /) -> None: ...

    @property
    def attach_bottom_end(self) -> bool: ...

    @attach_bottom_end.setter
    def attach_bottom_end(self, arg: bool, /) -> None: ...

    @property
    def flags(self) -> int: ...

    @flags.setter
    def flags(self, arg: int, /) -> None: ...

    @property
    def client_class_id(self) -> int: ...

    @client_class_id.setter
    def client_class_id(self, arg: int, /) -> None: ...

    @property
    def unbroken_elasticity(self) -> float: ...

    @unbroken_elasticity.setter
    def unbroken_elasticity(self, arg: float, /) -> None: ...

    @property
    def gravity_factor(self) -> float: ...

    @gravity_factor.setter
    def gravity_factor(self, arg: float, /) -> None: ...

    @property
    def buoyancy_factor(self) -> float: ...

    @buoyancy_factor.setter
    def buoyancy_factor(self, arg: float, /) -> None: ...

    @property
    def glass_attachment_bone(self) -> int: ...

    @glass_attachment_bone.setter
    def glass_attachment_bone(self, arg: int, /) -> None: ...

    @property
    def damaged_object_index(self) -> int: ...

    @damaged_object_index.setter
    def damaged_object_index(self, arg: int, /) -> None: ...

    @property
    def generate_vehicle_windows(self) -> bool: ...

    @generate_vehicle_windows.setter
    def generate_vehicle_windows(self, arg: bool, /) -> None: ...

    @property
    def vehicle_window(self) -> VehicleWindow: ...

    @vehicle_window.setter
    def vehicle_window(self, arg: VehicleWindow | None) -> None: ...

    @property
    def lights(self) -> pymateria.gta5.LightList: ...

    @lights.setter
    def lights(self, arg: pymateria.gta5.LightList, /) -> None: ...

    class DeserializationResult(pymateria.SharedResult):
        def __init__(self) -> None: ...

        @property
        def result(self) -> Fragment: ...

        @result.setter
        def result(self, arg: Fragment, /) -> None: ...

        @property
        def deserializer(self) -> pymateria.rsc7.Deserializer: ...

    RSC_VERSION: int = ...
    """Resource version of this asset format."""

    @overload
    @staticmethod
    def import_rsc(file_path: str | os.PathLike, settings: pymateria.ImportSettings | None = None) -> Fragment.DeserializationResult: ...

    @overload
    @staticmethod
    def import_rsc(stream: io.IOBase, settings: pymateria.ImportSettings | None = None) -> Fragment.DeserializationResult: ...

    @overload
    @staticmethod
    def export_rsc(instance: Fragment, file_path: str | os.PathLike, settings: pymateria.ExportSettings | None = None) -> pymateria.SerializationResultRsc7: ...

    @overload
    @staticmethod
    def export_rsc(instance: Fragment, stream: io.IOBase, settings: pymateria.ExportSettings | None = None) -> pymateria.SerializationResultRsc7: ...

    def __repr__(self) -> str: ...

class MapTypes:
    def __init__(self) -> None: ...

    @property
    def name(self) -> pymateria.gta5.CombinedHashString: ...

    @name.setter
    def name(self, arg: pymateria.gta5.CombinedHashString, /) -> None: ...

    @property
    def dependencies(self) -> list[pymateria.gta5.CombinedHashString]: ...

    @dependencies.setter
    def dependencies(self, arg: Sequence[pymateria.gta5.CombinedHashString], /) -> None: ...

    @property
    def composite_entity_types(self) -> pymateria.gta5.CompositeEntityTypeList: ...

    @composite_entity_types.setter
    def composite_entity_types(self, arg: pymateria.gta5.CompositeEntityTypeList, /) -> None: ...

    @property
    def archetypes(self) -> pymateria.gta5.ArchetypeDefinitionList: ...

    @archetypes.setter
    def archetypes(self, arg: pymateria.gta5.ArchetypeDefinitionList, /) -> None: ...

    def __repr__(self) -> str: ...

    class DeserializationResult(pymateria.SharedResult):
        def __init__(self) -> None: ...

        @property
        def result(self) -> MapTypes: ...

        @result.setter
        def result(self, arg: MapTypes, /) -> None: ...

        @property
        def deserializer(self) -> pymateria.pso.Deserializer: ...

    RSC_VERSION: int = ...
    """Resource version of this asset format."""

    @overload
    @staticmethod
    def import_rsc(file_path: str | os.PathLike, settings: pymateria.ImportSettings | None = None) -> MapTypes.DeserializationResult: ...

    @overload
    @staticmethod
    def import_rsc(stream: io.IOBase, settings: pymateria.ImportSettings | None = None) -> MapTypes.DeserializationResult: ...

    @overload
    @staticmethod
    def export_rsc(instance: MapTypes, file_path: str | os.PathLike, settings: pymateria.ExportSettings | None = None) -> pymateria.SerializationResultPso: ...

    @overload
    @staticmethod
    def export_rsc(instance: MapTypes, stream: io.IOBase, settings: pymateria.ExportSettings | None = None) -> pymateria.SerializationResultPso: ...
