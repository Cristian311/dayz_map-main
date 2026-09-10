# -*- coding: utf-8 -*-
"""
Scrie un fisier .gfx (Scaleform = SWF cu antetul 'GFX') care contine doar imaginea hartii, pentru
AddMinimapOverlay / SetMinimapOverlayDisplay din FiveM: imaginea apare pe radar si pe harta mare (pauza),
pozitionata direct in coordonate de joc (1 px = 1 m la scara 100). Fara dependinte (struct + zlib).

Structura: DefineBitsLossless2 (imaginea ARGB) -> DefineShape (dreptunghi umplut cu imaginea, coltul
stanga-sus la 0,0) -> PlaceObject2 -> ShowFrame -> End.
"""
import struct
import zlib

import numpy as np

from .dds_writer import _to_rgba_u8

TWIPS = 20  # 1 px = 20 twips


class _Bits:
    """Scriitor de biti MSB-first, cum cere formatul SWF."""

    def __init__(self):
        self.buf = bytearray()
        self.cur = 0
        self.n = 0

    def write(self, value: int, nbits: int):
        for i in range(nbits - 1, -1, -1):
            self.cur = (self.cur << 1) | ((int(value) >> i) & 1)
            self.n += 1
            if self.n == 8:
                self.buf.append(self.cur)
                self.cur = 0
                self.n = 0

    def write_signed(self, value: int, nbits: int):
        self.write(int(value) & ((1 << nbits) - 1), nbits)

    def align(self):
        if self.n:
            self.buf.append(self.cur << (8 - self.n))
            self.cur = 0
            self.n = 0

    def bytes(self) -> bytes:
        self.align()
        return bytes(self.buf)


def _nbits_signed(*values) -> int:
    return max(abs(int(v)) for v in values).bit_length() + 1  # +1 pentru semn


def _rect(xmin: int, xmax: int, ymin: int, ymax: int) -> bytes:
    b = _Bits()
    n = _nbits_signed(xmin, xmax, ymin, ymax)
    b.write(n, 5)
    for v in (xmin, xmax, ymin, ymax):
        b.write_signed(v, n)
    return b.bytes()


def _matrix_scale(scale: float) -> bytes:
    """MATRIX doar cu scalare uniforma (fixed 16.16), fara rotatie/translatie."""
    b = _Bits()
    fx = int(round(scale * 65536))
    n = _nbits_signed(fx)
    b.write(1, 1)          # HasScale
    b.write(n, 5)
    b.write_signed(fx, n)  # ScaleX
    b.write_signed(fx, n)  # ScaleY
    b.write(0, 1)          # HasRotate
    b.write(0, 5)          # NTranslateBits = 0
    return b.bytes()


def _tag(code: int, data: bytes) -> bytes:
    # forma lunga a antetului de tag, mereu
    return struct.pack("<HI", (code << 6) | 0x3F, len(data)) + data


def _define_bitmap(char_id: int, rgba: np.ndarray) -> bytes:
    """DefineBitsLossless2 (tag 36), format 5 = ARGB 32 biti, alpha premultiplicat, zlib."""
    h, w, _ = rgba.shape
    argb = np.empty((h, w, 4), dtype=np.uint8)
    a = rgba[..., 3].astype(np.uint16)
    argb[..., 0] = rgba[..., 3]
    for c in range(3):
        argb[..., c + 1] = (rgba[..., c].astype(np.uint16) * a // 255).astype(np.uint8)
    data = struct.pack("<HBHH", char_id, 5, w, h) + zlib.compress(argb.tobytes(), 9)
    return _tag(36, data)


def _define_shape(shape_id: int, bitmap_id: int, w_tw: int, h_tw: int) -> bytes:
    """DefineShape (tag 2): dreptunghi 0..w x 0..h umplut cu bitmap-ul (clipped, 1 px = 20 twips)."""
    body = bytearray(struct.pack("<H", shape_id))
    body += _rect(0, w_tw, 0, h_tw)
    body += b"\x01"                              # FillStyleCount = 1
    body += b"\x41"                              # clipped bitmap fill
    body += struct.pack("<H", bitmap_id)
    body += _matrix_scale(float(TWIPS))          # pixeli -> twips
    body += b"\x00"                              # LineStyleCount = 0
    bits = _Bits()
    bits.write(1, 4)                             # NumFillBits
    bits.write(0, 4)                             # NumLineBits
    # StyleChangeRecord: MoveTo(0,0) + FillStyle0 = 1
    bits.write(0, 1)                             # non-edge
    bits.write(0, 1)                             # StateNewStyles
    bits.write(0, 1)                             # StateLineStyle
    bits.write(0, 1)                             # StateFillStyle1
    bits.write(1, 1)                             # StateFillStyle0
    bits.write(1, 1)                             # StateMoveTo
    bits.write(1, 5)                             # MoveBits = 1
    bits.write_signed(0, 1)                      # MoveDeltaX
    bits.write_signed(0, 1)                      # MoveDeltaY
    bits.write(1, 1)                             # FillStyle0 = 1 (NumFillBits = 1)
    n = _nbits_signed(w_tw, h_tw)
    n = max(n, 2)
    for dx, dy in ((w_tw, 0), (0, h_tw), (-w_tw, 0), (0, -h_tw)):
        bits.write(1, 1)                         # edge record
        bits.write(1, 1)                         # straight
        bits.write(n - 2, 4)                     # NumBits - 2
        bits.write(1, 1)                         # GeneralLineFlag
        bits.write_signed(dx, n)
        bits.write_signed(dy, n)
    bits.write(0, 6)                             # EndShapeRecord
    body += bits.bytes()
    return _tag(2, bytes(body))


def _place_object(depth: int, char_id: int) -> bytes:
    # PlaceObject2: HasMatrix | HasCharacter, matrice identitate (7 biti de 0 -> 1 octet)
    return _tag(26, struct.pack("<BHH", 0x06, depth, char_id) + b"\x00")


def write_minimap_gfx(img: np.ndarray, path: str, signature: bytes = b"GFX", fps: int = 24) -> str:
    """
    img: (H, W, 3|4) float 0..1 sau uint8 (rand 0 = nord). Scrie <path> si intoarce calea.
    In joc: SetMinimapOverlayDisplay(id, origin_x, -(origin_y + size), 100*size/W, 100*size/H, 100).
    """
    rgba = _to_rgba_u8(np.ascontiguousarray(img))
    h, w = rgba.shape[:2]
    if w > 4096 or h > 4096:
        raise ValueError("imaginea de minimap trebuie sa fie cel mult 4096 px")
    w_tw, h_tw = w * TWIPS, h * TWIPS
    header_rest = _rect(0, w_tw, 0, h_tw) + struct.pack("<HH", int(fps) << 8, 1)
    tags = (_define_bitmap(1, rgba)
            + _define_shape(2, 1, w_tw, h_tw)
            + _place_object(1, 2)
            + _tag(1, b"")      # ShowFrame
            + _tag(0, b""))     # End
    total = 8 + len(header_rest) + len(tags)
    with open(path, "wb") as f:
        f.write(bytes(signature) + bytes([8]) + struct.pack("<I", total) + header_rest + tags)
    return path


def overlay_display_args(origin_x: float, origin_y: float, size: float, w_px: int, h_px: int):
    """Argumentele pentru SetMinimapOverlayDisplay (x, y, xScale, yScale): y-ul din Flash e inversat."""
    return (float(origin_x), -float(origin_y + size), 100.0 * size / w_px, 100.0 * size / h_px)
