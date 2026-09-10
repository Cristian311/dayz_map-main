from collections.abc import Iterable, Iterator, Mapping, Sequence
import ctypes
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

    DIRT = 29

class ImageDimension(enum.Enum):
    DIM_1D = 0

    DIM_2D = 1

    CUBE = 2

    VOLUME = 3

    BUFFER = 4

    UNKNOWN = 5

class BufferFormat(enum.Enum):
    UNKNOWN = 0

    R32G32B32A32_TYPELESS = 1

    R32G32B32A32_FLOAT = 2

    R32G32B32A32_UINT = 3

    R32G32B32A32_SINT = 4

    R32G32B32_TYPELESS = 5

    R32G32B32_FLOAT = 6

    R32G32B32_UINT = 7

    R32G32B32_SINT = 8

    R16G16B16A16_TYPELESS = 9

    R16G16B16A16_FLOAT = 10

    R16G16B16A16_UNORM = 11

    R16G16B16A16_UINT = 12

    R16G16B16A16_SNORM = 13

    R16G16B16A16_SINT = 14

    R32G32_TYPELESS = 15

    R32G32_FLOAT = 16

    R32G32_UINT = 17

    R32G32_SINT = 18

    D32_FLOAT_S8X24_UINT = 20

    B10G10R10A2_UNORM = 21

    R10G10B10A2_SNORM = 22

    R10G10B10A2_TYPELESS = 23

    R10G10B10A2_UNORM = 24

    R10G10B10A2_UINT = 25

    R11G11B10_FLOAT = 26

    R8G8B8A8_TYPELESS = 27

    R8G8B8A8_UNORM = 28

    R8G8B8A8_UNORM_SRGB = 29

    R8G8B8A8_UINT = 30

    R8G8B8A8_SNORM = 31

    R8G8B8A8_SINT = 32

    R16G16_TYPELESS = 33

    R16G16_FLOAT = 34

    R16G16_UNORM = 35

    R16G16_UINT = 36

    R16G16_SNORM = 37

    R16G16_SINT = 38

    R32_TYPELESS = 39

    D32_FLOAT = 40

    R32_FLOAT = 41

    R32_UINT = 42

    R32_SINT = 43

    R8G8_TYPELESS = 48

    R8G8_UNORM = 49

    R8G8_UINT = 50

    R8G8_SNORM = 51

    R8G8_SINT = 52

    R16_TYPELESS = 53

    R16_FLOAT = 54

    D16_UNORM = 55

    R16_UNORM = 56

    R16_UINT = 57

    R16_SNORM = 58

    R16_SINT = 59

    R8_TYPELESS = 60

    R8_UNORM = 61

    R8_UINT = 62

    R8_SNORM = 63

    R8_SINT = 64

    A8_UNORM = 65

    R9G9B9E5_SHAREDEXP = 67

    BC1_TYPELESS = 70

    BC1_UNORM = 71

    BC1_UNORM_SRGB = 72

    BC2_TYPELESS = 73

    BC2_UNORM = 74

    BC2_UNORM_SRGB = 75

    BC3_TYPELESS = 76

    BC3_UNORM = 77

    BC3_UNORM_SRGB = 78

    BC4_TYPELESS = 79

    BC4_UNORM = 80

    BC4_SNORM = 81

    BC5_TYPELESS = 82

    BC5_UNORM = 83

    BC5_SNORM = 84

    B5G6R5_UNORM = 85

    B5G5R5A1_UNORM = 86

    B8G8R8A8_UNORM = 87

    B8G8R8A8_TYPELESS = 90

    B8G8R8A8_UNORM_SRGB = 91

    BC6H_TYPELESS = 94

    BC6H_UF16 = 95

    BC6H_SF16 = 96

    BC7_TYPELESS = 97

    BC7_UNORM = 98

    BC7_UNORM_SRGB = 99

    AYUV = 100

    Y410 = 101

    Y416 = 102

    NV12 = 103

    B4G4R4A4_UNORM = 115

    D16_UNORM_S8_UINT = 118

    R16_UNORM_X8_TYPELESS = 119

    X16_TYPELESS_G8_UINT = 120

    ETC1 = 121

    ETC1_SRGB = 122

    ETC1A = 123

    ETC1A_SRGB = 124

    R4G4_UNORM = 127

    @property
    def bits_per_pixel(self) -> int: ...

class TileMode(enum.Enum):
    LINEAR = 0

    DISPLAY = 27

    AUTO = 255

class AntiAliasType(enum.Enum):
    AA_1X = 0

    AA_2X = 1

    AA_4X = 2

    AA_8X = 3

    AA_16X = 4

    AA_4S1F = 5

    AA_8S1F = 6

    AA_4S2F = 7

    AA_8S2F = 8

    AA_8S4F = 9

    AA_16S1F = 10

    AA_16S2F = 11

    AA_16S4F = 12

    AA_16S8F = 13

    AA_2X_RAW = 14

    AA_4X_RAW = 15

    AA_8X_RAW = 16

    AA_16X_RAW = 17

class TextureReference:
    @overload
    def __init__(self) -> None: ...

    @overload
    def __init__(self, name: str, depth: int = 1, dimension: ImageDimension = ImageDimension.DIM_2D) -> None: ...

    @property
    def name(self) -> str: ...

    @name.setter
    def name(self, arg: str, /) -> None: ...

    @property
    def depth(self) -> int: ...

    @depth.setter
    def depth(self, arg: int, /) -> None: ...

    @property
    def dimension(self) -> ImageDimension: ...

    @dimension.setter
    def dimension(self, arg: ImageDimension, /) -> None: ...

    @property
    def is_reference(self) -> bool: ...

    def __repr__(self) -> str: ...

class Texture(TextureReference):
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
    def format(self) -> BufferFormat: ...

    @format.setter
    def format(self, arg: BufferFormat, /) -> None: ...

    @property
    def tile_mode(self) -> TileMode: ...

    @tile_mode.setter
    def tile_mode(self, arg: TileMode, /) -> None: ...

    @property
    def anti_alias(self) -> AntiAliasType: ...

    @anti_alias.setter
    def anti_alias(self, arg: AntiAliasType, /) -> None: ...

    @property
    def mips(self) -> pymateria.gta5.TextureMipList: ...

    @mips.setter
    def mips(self, arg: pymateria.gta5.TextureMipList, /) -> None: ...

    @property
    def compression_rdo_lambda(self) -> int: ...

    @compression_rdo_lambda.setter
    def compression_rdo_lambda(self, arg: int, /) -> None: ...

    @property
    def template_type(self) -> TextureTemplateType: ...

    @template_type.setter
    def template_type(self, arg: TextureTemplateType, /) -> None: ...

    @property
    def template_flags(self) -> int: ...

    @template_flags.setter
    def template_flags(self, arg: int, /) -> None: ...

    @property
    def is_render_target(self) -> bool: ...

    @is_render_target.setter
    def is_render_target(self, arg: bool, /) -> None: ...

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

class ShaderSamplerInfo:
    @overload
    def __init__(self) -> None: ...

    @overload
    def __init__(self, name: str, semantic: str, index: int) -> None: ...

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
    def index(self) -> int: ...

    @index.setter
    def index(self, arg: int, /) -> None: ...

    def __repr__(self) -> str: ...

class ShaderResourceType(enum.Enum):
    TEXTURE = 0

    STRUCTURED = 1

    TYPED = 2

    BYTE_ADDRESS = 3

    RTX_ACCELERATION_STRUCTURE = 4

class ShaderResourceInfo:
    @overload
    def __init__(self) -> None: ...

    @overload
    def __init__(self, name: str, semantic: str, index: int, type: ShaderResourceType) -> None: ...

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
    def index(self) -> int: ...

    @index.setter
    def index(self, arg: int, /) -> None: ...

    @property
    def type(self) -> ShaderResourceType: ...

    @type.setter
    def type(self, arg: ShaderResourceType, /) -> None: ...

    def __repr__(self) -> str: ...

class ShaderBufferFieldType(enum.Enum):
    BOOL = 0

    INT = 1

    INT2 = 2

    INT3 = 3

    INT4 = 4

    UINT = 5

    UINT2 = 6

    UINT3 = 7

    UINT4 = 8

    FLOAT = 9

    FLOAT2 = 10

    FLOAT3 = 11

    FLOAT4 = 12

    MATRIX34 = 13

    MATRIX44 = 14

    INVALID = 15

    @property
    def size(self) -> int: ...

class ShaderBufferFieldInfo:
    @overload
    def __init__(self) -> None: ...

    @overload
    def __init__(self, name: str, semantic: str, type: ShaderBufferFieldType, offset: int) -> None: ...

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
    def type(self) -> ShaderBufferFieldType: ...

    @type.setter
    def type(self, arg: ShaderBufferFieldType, /) -> None: ...

    @property
    def offset(self) -> int: ...

    @offset.setter
    def offset(self, arg: int, /) -> None: ...

    @property
    def array_count(self) -> int: ...

    @array_count.setter
    def array_count(self, arg: int, /) -> None: ...

    def __repr__(self) -> str: ...

class ShaderBufferInfo:
    @overload
    def __init__(self) -> None: ...

    @overload
    def __init__(self, name: str, semantic: str, index: int) -> None: ...

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
    def index(self) -> int: ...

    @index.setter
    def index(self, arg: int, /) -> None: ...

    @property
    def size(self) -> int: ...

    @size.setter
    def size(self, arg: int, /) -> None: ...

    @property
    def fields(self) -> dict[int, ShaderBufferFieldInfo]: ...

    @fields.setter
    def fields(self, arg: Mapping[int, ShaderBufferFieldInfo], /) -> None: ...

    @property
    def ctype(self) -> type[ctypes.Structure]:
        """
        Gets a `ctypes.Structure` subclass that matches the memory layout of this shader buffer.

        Each field is translated into the corresponding C type. For example:
          - `INT` becomes `ctypes.c_int32`
          - `FLOAT` becomes `ctypes.c_float`
          - Vector types (e.g., `FLOAT3`) are converted to arrays, such as `ctypes.c_float * 3`

        Any padding between fields is preserved using `ctypes.c_uint8` arrays named `_padN`, where `N` is a unique identifier.
        """

    def get_sorted_fields(self) -> list[ShaderBufferFieldInfo]: ...

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
    def samplers(self) -> list[ShaderSamplerInfo]: ...

    @samplers.setter
    def samplers(self, arg: Sequence[ShaderSamplerInfo], /) -> None: ...

    @property
    def buffers(self) -> list[ShaderBufferInfo]: ...

    @buffers.setter
    def buffers(self, arg: Sequence[ShaderBufferInfo], /) -> None: ...

    @property
    def resources(self) -> list[ShaderResourceInfo]: ...

    @resources.setter
    def resources(self, arg: Sequence[ShaderResourceInfo], /) -> None: ...

    def __repr__(self) -> str: ...

class ShaderRegistry:
    def __init__(self, load_defaults: bool = True) -> None: ...

    @overload
    def load_fxc(self, name: str, path: str | os.PathLike) -> None: ...

    @overload
    def load_fxc(self, name: str, stream: io.IOBase) -> None: ...

    @overload
    def load_awc(self, path: str | os.PathLike) -> None: ...

    @overload
    def load_awc(self, stream: io.IOBase) -> None: ...

    def load_defaults(self) -> None: ...

    @property
    def shaders(self) -> dict[int, ShaderInfo]: ...

    def get_shader(self, name_or_hash: str | int) -> ShaderInfo | None: ...

    instance: pymateria.gta5.gen9.ShaderRegistry = ...
    """The global shared ShaderRegistry instance."""

class ShaderBufferInfoHandle:
    def __init__(self, shader: ShaderInfo, buffer_index: int) -> None: ...

    @property
    def shader(self) -> ShaderInfo: ...

    @shader.setter
    def shader(self, arg: ShaderInfo, /) -> None: ...

    @property
    def buffer_index(self) -> int: ...

    @buffer_index.setter
    def buffer_index(self, arg: int, /) -> None: ...

    @property
    def is_null(self) -> bool: ...

    def __bool__(self) -> bool: ...

    @property
    def info(self) -> ShaderBufferInfo: ...

class ShaderBuffer:
    def __init__(self) -> None: ...

    @property
    def info(self) -> ShaderBufferInfo: ...

    @property
    def raw_data(self) -> pymateria.Buffer: ...

    @property
    def data(self) ->  ctypes._Pointer[ctypes.Structure]:
        """
        Gets a `ctypes.POINTER(ctypes.Structure)` pointing to the data of this shader buffer.

        This allows direct access to read or modify the buffer's fields. The pointer type is a
        `ctypes.Structure` subclass that matches the memory layout of the shader buffer.

        See `ShaderBufferInfo.ctype` for details about the structure type.
        """

    def set_default_values(self) -> None: ...

    def reset(self, arg: ShaderBufferInfoHandle, /) -> None: ...

class ShaderParameters:
    @overload
    def __init__(self) -> None: ...

    @overload
    def __init__(self, arg: ShaderInfo, /) -> None: ...

    def reset(self, arg: ShaderInfo, /) -> None: ...

    @property
    def sampler_count(self) -> int: ...

    @property
    def buffer_count(self) -> int: ...

    @property
    def buffers(self) -> list[ShaderBuffer]: ...

    def get_buffer_by_index(self, arg: int, /) -> ShaderBuffer: ...

    def get_buffer_by_name(self, arg: pymateria.gta5.HashString, /) -> ShaderBuffer: ...

    def get_buffer_by_semantic(self, arg: pymateria.gta5.HashString, /) -> ShaderBuffer: ...

    @property
    def resource_count(self) -> int: ...

    @property
    def resources(self) -> list[TextureReference | None]: ...

    def get_resource_by_index(self, arg: int, /) -> TextureReference | None: ...

    def get_resource_by_name(self, arg: pymateria.gta5.HashString, /) -> TextureReference | None: ...

    def get_resource_by_semantic(self, arg: pymateria.gta5.HashString, /) -> TextureReference | None: ...

    def set_resource_by_index(self, index: int, resource: TextureReference | None) -> None: ...

    def set_resource_by_name(self, name: pymateria.gta5.HashString, resource: TextureReference | None) -> None: ...

    def set_resource_by_semantic(self, semantic: pymateria.gta5.HashString, resource: TextureReference | None) -> None: ...

    def get_resource_index_by_name(self, arg: pymateria.gta5.HashString, /) -> int: ...

    def get_resource_index_by_semantic(self, arg: pymateria.gta5.HashString, /) -> int: ...

class Shader:
    def __init__(self) -> None: ...

    @property
    def parameters(self) -> ShaderParameters: ...

    @parameters.setter
    def parameters(self, arg: ShaderParameters, /) -> None: ...

    @property
    def basis_hash(self) -> pymateria.gta5.CombinedHashString: ...

    @basis_hash.setter
    def basis_hash(self, arg: pymateria.gta5.CombinedHashString, /) -> None: ...

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

    @property
    def max_render_threads(self) -> int: ...

    @max_render_threads.setter
    def max_render_threads(self, arg: int, /) -> None: ...

    @property
    def user_flags(self) -> int: ...

    @user_flags.setter
    def user_flags(self, arg: int, /) -> None: ...

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
    POSITION0 = 0

    POSITION1 = 1

    POSITION2 = 2

    POSITION3 = 3

    NORMAL0 = 4

    NORMAL1 = 5

    NORMAL2 = 6

    NORMAL3 = 7

    TANGENT0 = 8

    TANGENT1 = 9

    TANGENT2 = 10

    TANGENT3 = 11

    BINORMAL0 = 12

    BINORMAL1 = 13

    BINORMAL2 = 14

    BINORMAL3 = 15

    BLEND_WEIGHT0 = 16

    BLEND_WEIGHT1 = 17

    BLEND_WEIGHT2 = 18

    BLEND_WEIGHT3 = 19

    BLEND_INDICES0 = 20

    BLEND_INDICES1 = 21

    BLEND_INDICES2 = 22

    BLEND_INDICES3 = 23

    COLOR0 = 24

    COLOR1 = 25

    COLOR2 = 26

    COLOR3 = 27

    TEXCOORD0 = 28

    TEXCOORD1 = 29

    TEXCOORD2 = 30

    TEXCOORD3 = 31

    TEXCOORD4 = 32

    TEXCOORD5 = 33

    TEXCOORD6 = 34

    TEXCOORD7 = 35

    TEXCOORD8 = 36

    TEXCOORD9 = 37

    TEXCOORD10 = 38

    TEXCOORD11 = 39

    TEXCOORD12 = 40

    TEXCOORD13 = 41

    TEXCOORD14 = 42

    TEXCOORD15 = 43

    TEXCOORD16 = 44

    TEXCOORD17 = 45

    TEXCOORD18 = 46

    TEXCOORD19 = 47

    TEXCOORD20 = 48

    TEXCOORD21 = 49

    TEXCOORD22 = 50

    TEXCOORD23 = 51

    SV_POSITION = 52

    SV_INSTANCE_ID = 53

    SV_PRIMITIVE_ID = 54

    SV_VERTEX_ID = 55

    SV_DEPTH = 56

    SV_VIEWPORT_ARRAY_INDEX = 57

    SV_SAMPLE_INDEX = 58

    SV_RENDER_TARGET_ARRAY_INDEX = 59

    SV_TESS_FACTOR = 60

    SV_INSIDE_TESS_FACTOR = 61

    SV_DOMAIN_LOCATION = 62

    SV_IS_FRONT_FACE = 63

    SV_GS_INSTANCE_ID = 64

    SV_OUTPUT_CONTROL_POINT_ID = 65

    SV_COVERAGE = 66

    SV_DISPATCH_THREAD_ID = 67

    SV_GROUP_ID = 68

    SV_GROUP_INDEX = 69

    SV_GROUP_THREAD_ID = 70

    SV_DEPTH_GREATER_EQUAL = 71

    SV_DEPTH_LESS_EQUAL = 72

    SV_RESERVED0 = 73

    SV_RESERVED1 = 74

    SV_RESERVED2 = 75

    SV_CLIP_DISTANCE0 = 76

    SV_CLIP_DISTANCE1 = 77

    SV_CLIP_DISTANCE2 = 78

    SV_CLIP_DISTANCE3 = 79

    SV_CULL_DISTANCE0 = 80

    SV_CULL_DISTANCE1 = 81

    SV_CULL_DISTANCE2 = 82

    SV_CULL_DISTANCE3 = 83

    SV_TARGET0 = 84

    SV_TARGET1 = 85

    SV_TARGET2 = 86

    SV_TARGET3 = 87

    SV_TARGET4 = 88

    SV_TARGET5 = 89

    SV_TARGET6 = 90

    SV_TARGET7 = 91

    INVALID = 92

class FvfChannelInfo:
    def __init__(self) -> None: ...

    @property
    def offset(self) -> int: ...

    @offset.setter
    def offset(self, arg: int, /) -> None: ...

    @property
    def stride(self) -> int: ...

    @stride.setter
    def stride(self, arg: int, /) -> None: ...

    @property
    def format(self) -> BufferFormat: ...

    @format.setter
    def format(self, arg: BufferFormat, /) -> None: ...

    def __repr__(self) -> str: ...

class Fvf:
    def __init__(self) -> None: ...

    @property
    def channels(self) -> dict[FvfChannel, FvfChannelInfo]: ...

    @property
    def vertex_data_size(self) -> int: ...

    @vertex_data_size.setter
    def vertex_data_size(self, arg: int, /) -> None: ...

    @property
    def is_structure_of_arrays(self) -> bool: ...

    @is_structure_of_arrays.setter
    def is_structure_of_arrays(self, arg: bool, /) -> None: ...

    def is_channel_active(self, arg: FvfChannel, /) -> bool: ...

    def get_channel_size(self, arg: FvfChannel, /) -> int: ...

    def get_channel_offset(self, arg: FvfChannel, /) -> int: ...

    def get_channel_size_type(self, arg: FvfChannel, /) -> BufferFormat: ...

    def enable_channel(self, channel: FvfChannel, offset: int, stride: int, format: BufferFormat) -> None: ...

    def disable_channel(self, channel: FvfChannel) -> None: ...

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
