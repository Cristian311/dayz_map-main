# -*- coding: utf-8 -*-
"""
Encoder DDS (DXT1 / DXT5) cu mipmap-uri, scris in numpy pur.
Produce fisiere .dds pe care GTA V (si pymateria / CodeWalker) le accepta direct.
"""
import struct
import numpy as np

DDSD_CAPS = 0x1
DDSD_HEIGHT = 0x2
DDSD_WIDTH = 0x4
DDSD_PIXELFORMAT = 0x1000
DDSD_MIPMAPCOUNT = 0x20000
DDSD_LINEARSIZE = 0x80000
DDPF_FOURCC = 0x4
DDSCAPS_COMPLEX = 0x8
DDSCAPS_TEXTURE = 0x1000
DDSCAPS_MIPMAP = 0x400000


def _to_rgba_u8(img: np.ndarray) -> np.ndarray:
    """Accepta float [0,1] sau uint8, 3 sau 4 canale -> uint8 RGBA."""
    if img.dtype != np.uint8:
        img = np.clip(img * 255.0 + 0.5, 0, 255).astype(np.uint8)
    if img.shape[2] == 3:
        a = np.full(img.shape[:2] + (1,), 255, dtype=np.uint8)
        img = np.concatenate([img, a], axis=2)
    return img


def _downsample(img: np.ndarray) -> np.ndarray:
    """Box filter 2x2 pe imagine uint8 RGBA (dimensiuni pare)."""
    h, w, c = img.shape
    f = img.astype(np.float32)
    f = f.reshape(h // 2, 2, w // 2, 2, c).mean(axis=(1, 3))
    return np.clip(f + 0.5, 0, 255).astype(np.uint8)


def _pack_565(rgb: np.ndarray) -> np.ndarray:
    """rgb float (N,3) 0..255 -> uint16 565."""
    r = np.clip(np.round(rgb[:, 0] * 31.0 / 255.0), 0, 31).astype(np.uint32)
    g = np.clip(np.round(rgb[:, 1] * 63.0 / 255.0), 0, 63).astype(np.uint32)
    b = np.clip(np.round(rgb[:, 2] * 31.0 / 255.0), 0, 31).astype(np.uint32)
    return ((r << 11) | (g << 5) | b).astype(np.uint16)


def _unpack_565(c: np.ndarray) -> np.ndarray:
    c = c.astype(np.uint32)
    r = ((c >> 11) & 31).astype(np.float32) * (255.0 / 31.0)
    g = ((c >> 5) & 63).astype(np.float32) * (255.0 / 63.0)
    b = (c & 31).astype(np.float32) * (255.0 / 31.0)
    return np.stack([r, g, b], axis=1)


def _blocks(img: np.ndarray) -> np.ndarray:
    """(H,W,4) uint8 -> (nblocks, 16, 4) float32, in ordinea rand-major a blocurilor."""
    h, w, c = img.shape
    b = img.reshape(h // 4, 4, w // 4, 4, c).transpose(0, 2, 1, 3, 4).reshape(-1, 16, c)
    return b.astype(np.float32)


def _encode_color_blocks(blocks: np.ndarray) -> np.ndarray:
    """
    Codare bloc culoare DXT1 (8 bytes / bloc) folosind bounding-box + inset.
    blocks: (N,16,4) float32. Returneaza (N,8) uint8.
    """
    rgb = blocks[:, :, :3]
    mn = rgb.min(axis=1)
    mx = rgb.max(axis=1)
    # inset 1/16 din interval, ca in stb_dxt (reduce erorile de cuantizare)
    inset = (mx - mn) / 16.0
    mn = np.clip(mn + inset, 0, 255)
    mx = np.clip(mx - inset, 0, 255)

    c0 = _pack_565(mx)
    c1 = _pack_565(mn)
    # garantam c0 > c1 (mod 4 culori); daca sunt egale, toti indicii = 0
    swap = c0 < c1
    c0s = np.where(swap, c1, c0)
    c1s = np.where(swap, c0, c1)
    c0 = c0s
    c1 = c1s

    p0 = _unpack_565(c0)
    p1 = _unpack_565(c1)
    p2 = (2.0 * p0 + p1) / 3.0
    p3 = (p0 + 2.0 * p1) / 3.0
    palette = np.stack([p0, p1, p2, p3], axis=1)  # (N,4,3)

    # distanta patratica pixel-paleta
    d = ((rgb[:, :, None, :] - palette[:, None, :, :]) ** 2).sum(axis=3)  # (N,16,4)
    idx = d.argmin(axis=2).astype(np.uint32)  # (N,16)
    equal = (c0 == c1)
    idx[equal] = 0
    shifts = (np.arange(16, dtype=np.uint32) * 2)[None, :]
    packed = (idx << shifts).sum(axis=1, dtype=np.uint64).astype(np.uint32)

    out = np.empty((blocks.shape[0], 8), dtype=np.uint8)
    out[:, 0:2] = c0.astype("<u2").view(np.uint8).reshape(-1, 2)
    out[:, 2:4] = c1.astype("<u2").view(np.uint8).reshape(-1, 2)
    out[:, 4:8] = packed.astype("<u4").view(np.uint8).reshape(-1, 4)
    return out


def _encode_alpha_blocks(blocks: np.ndarray) -> np.ndarray:
    """Bloc alpha DXT5 (8 bytes / bloc), mod cu 8 valori interpolate."""
    a = blocks[:, :, 3]
    amax = a.max(axis=1)
    amin = a.min(axis=1)
    a0 = np.round(amax).astype(np.int32)
    a1 = np.round(amin).astype(np.int32)
    same = a0 == a1
    # mod a0 > a1 -> 8 nivele
    levels = np.empty((blocks.shape[0], 8), dtype=np.float32)
    levels[:, 0] = a0
    levels[:, 1] = a1
    for i in range(1, 7):
        levels[:, i + 1] = ((7 - i) * a0 + i * a1) / 7.0
    d = np.abs(a[:, :, None] - levels[:, None, :])  # (N,16,8)
    idx = d.argmin(axis=2).astype(np.uint64)
    idx[same] = 0
    shifts = (np.arange(16, dtype=np.uint64) * 3)[None, :]
    packed = (idx << shifts).sum(axis=1, dtype=np.uint64)  # 48 biti utili
    out = np.empty((blocks.shape[0], 8), dtype=np.uint8)
    out[:, 0] = a0.astype(np.uint8)
    out[:, 1] = a1.astype(np.uint8)
    pb = packed.astype("<u8").view(np.uint8).reshape(-1, 8)
    out[:, 2:8] = pb[:, 0:6]
    return out


def encode_level(img_rgba: np.ndarray, fourcc: str) -> bytes:
    h, w, _ = img_rgba.shape
    # padding la multiplu de 4 prin replicare margine
    ph = (4 - h % 4) % 4
    pw = (4 - w % 4) % 4
    if ph or pw:
        img_rgba = np.pad(img_rgba, ((0, ph), (0, pw), (0, 0)), mode="edge")
    blocks = _blocks(img_rgba)
    color = _encode_color_blocks(blocks)
    if fourcc == "DXT1":
        return color.tobytes()
    alpha = _encode_alpha_blocks(blocks)
    return np.concatenate([alpha, color], axis=1).tobytes()


def mip_chain(img_rgba: np.ndarray, min_size: int = 4) -> list[np.ndarray]:
    """Lant de mipmap-uri pana la min_size (4 pentru formate BC, cerut de pymateria)."""
    levels = [img_rgba]
    cur = img_rgba
    while cur.shape[0] > min_size and cur.shape[1] > min_size and cur.shape[0] % 2 == 0 and cur.shape[1] % 2 == 0:
        cur = _downsample(cur)
        levels.append(cur)
    return levels


def write_dds(path: str, img: np.ndarray, fourcc: str = "DXT1", mipmaps: bool = True) -> None:
    """
    Scrie un DDS comprimat.
    img: (H,W,3|4) uint8 sau float [0,1]. fourcc: "DXT1" (opac) sau "DXT5" (cu alpha).
    """
    assert fourcc in ("DXT1", "DXT5")
    rgba = _to_rgba_u8(np.ascontiguousarray(img))
    h, w, _ = rgba.shape
    levels = mip_chain(rgba) if mipmaps else [rgba]
    block_bytes = 8 if fourcc == "DXT1" else 16
    linear_size = max(1, (w + 3) // 4) * max(1, (h + 3) // 4) * block_bytes

    flags = DDSD_CAPS | DDSD_HEIGHT | DDSD_WIDTH | DDSD_PIXELFORMAT | DDSD_LINEARSIZE
    caps = DDSCAPS_TEXTURE
    if len(levels) > 1:
        flags |= DDSD_MIPMAPCOUNT
        caps |= DDSCAPS_COMPLEX | DDSCAPS_MIPMAP

    header = struct.pack(
        "<4sIIIIIII11I",
        b"DDS ", 124, flags, h, w, linear_size, 0, len(levels), *([0] * 11)
    )
    pixfmt = struct.pack("<II4sIIIII", 32, DDPF_FOURCC, fourcc.encode("ascii"), 0, 0, 0, 0, 0)
    tail = struct.pack("<IIIII", caps, 0, 0, 0, 0)
    with open(path, "wb") as f:
        f.write(header)
        f.write(pixfmt)
        f.write(tail)
        for lv in levels:
            f.write(encode_level(lv, fourcc))


def write_png(path: str, img: np.ndarray) -> None:
    """PNG simplu (zlib) pentru previzualizare; fara dependinte externe."""
    import zlib
    rgba = _to_rgba_u8(np.ascontiguousarray(img))
    h, w, _ = rgba.shape
    raw = b"".join(b"\x00" + rgba[y].tobytes() for y in range(h))

    def chunk(tag: bytes, data: bytes) -> bytes:
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)))
        f.write(chunk(b"IDAT", zlib.compress(raw, 6)))
        f.write(chunk(b"IEND", b""))
