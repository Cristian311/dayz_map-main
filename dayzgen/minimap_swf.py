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


def _rect_records(w_tw: int, h_tw: int, fill_side: str = "1") -> bytes:
    """Inregistrarile de forma pentru dreptunghiul 0..w x 0..h, parcurs (0,0)->(w,0)->(w,h)->(0,h), adica in
    sensul acelor de ceas pe ecran (y in jos). fill_side: pe ce parte a muchiei sta umplutura 1: "1" = dreapta
    (interiorul unui drum in sensul acelor; asa scriu si programele Adobe), "0" = stanga, "both" = ambele."""
    bits = _Bits()
    bits.write(1, 4)                             # NumFillBits
    bits.write(0, 4)                             # NumLineBits
    use0, use1 = fill_side in ("0", "both"), fill_side in ("1", "both")
    bits.write(0, 1)                             # non-edge (StyleChangeRecord)
    bits.write(0, 1)                             # StateNewStyles
    bits.write(0, 1)                             # StateLineStyle
    bits.write(1 if use1 else 0, 1)              # StateFillStyle1
    bits.write(1 if use0 else 0, 1)              # StateFillStyle0
    bits.write(1, 1)                             # StateMoveTo
    bits.write(1, 5)                             # MoveBits = 1
    bits.write_signed(0, 1)                      # MoveDeltaX
    bits.write_signed(0, 1)                      # MoveDeltaY
    if use0:
        bits.write(1, 1)                         # FillStyle0 = 1 (NumFillBits = 1)
    if use1:
        bits.write(1, 1)                         # FillStyle1 = 1
    n = max(_nbits_signed(w_tw, h_tw), 2)
    for dx, dy in ((w_tw, 0), (0, h_tw), (-w_tw, 0), (0, -h_tw)):
        bits.write(1, 1)                         # edge record
        bits.write(1, 1)                         # straight
        bits.write(n - 2, 4)                     # NumBits - 2
        bits.write(1, 1)                         # GeneralLineFlag
        bits.write_signed(dx, n)
        bits.write_signed(dy, n)
    bits.write(0, 6)                             # EndShapeRecord
    return bits.bytes()


def _define_shape(shape_id: int, bitmap_id: int, w_tw: int, h_tw: int, fill_side: str = "1") -> bytes:
    """DefineShape (tag 2): dreptunghi 0..w x 0..h umplut cu bitmap-ul (clipped, 1 px = 20 twips)."""
    body = bytearray(struct.pack("<H", shape_id))
    body += _rect(0, w_tw, 0, h_tw)
    body += b"\x01"                              # FillStyleCount = 1
    body += b"\x41"                              # clipped bitmap fill
    body += struct.pack("<H", bitmap_id)
    body += _matrix_scale(float(TWIPS))          # pixeli -> twips
    body += b"\x00"                              # LineStyleCount = 0
    body += _rect_records(w_tw, h_tw, fill_side)
    return _tag(2, bytes(body))


def _place_object(depth: int, char_id: int) -> bytes:
    # PlaceObject2: HasMatrix | HasCharacter, matrice identitate (7 biti de 0 -> 1 octet)
    return _tag(26, struct.pack("<BHH", 0x06, depth, char_id) + b"\x00")


def _exporter_info(name: str) -> bytes:
    """ExporterInfo (tag 1000), primul tag din fisierele scrise de gfxexport: versiunea GFx 3.3 (0x036f), flags,
    formatul imaginilor, prefix gol, numele filmului, fara code offsets. Fisierele GTA/FiveM care merg il au."""
    short = name.encode("ascii", "replace")[:250]
    return _tag(1000, struct.pack("<HIH", 0x036F, 0x10, 0) + b"\x00" + bytes([len(short)]) + short + struct.pack("<H", 0))


def _file_attributes() -> bytes:
    return _tag(69, struct.pack("<I", 0x10))


def _write_movie(path: str, signature: bytes, w_tw: int, h_tw: int, body: bytes, fps: int, gfx_tags: bool, name: str):
    header_rest = _rect(0, w_tw, 0, h_tw) + struct.pack("<HH", int(fps) << 8, 1)
    head = (_exporter_info(name) + _file_attributes()) if gfx_tags else b""
    tags = head + body + _tag(1, b"") + _tag(0, b"")        # ShowFrame, End
    total = 8 + len(header_rest) + len(tags)
    with open(path, "wb") as f:
        f.write(bytes(signature) + bytes([8]) + struct.pack("<I", total) + header_rest + tags)
    return path


def write_minimap_gfx(img: np.ndarray, path: str, signature: bytes = b"GFX", fps: int = 24, gfx_tags: bool = True) -> str:
    """
    img: (H, W, 3|4) float 0..1 sau uint8 (rand 0 = nord). Scrie <path> si intoarce calea.
    In joc: SetMinimapOverlayDisplay(id, origin_x, -(origin_y + size), 100*size/W, 100*size/H, 100).
    """
    rgba = _to_rgba_u8(np.ascontiguousarray(img))
    h, w = rgba.shape[:2]
    if w > 4096 or h > 4096:
        raise ValueError("imaginea de minimap trebuie sa fie cel mult 4096 px")
    w_tw, h_tw = w * TWIPS, h * TWIPS
    body = _define_bitmap(1, rgba) + _define_shape(2, 1, w_tw, h_tw) + _place_object(1, 2)
    import os
    return _write_movie(path, signature, w_tw, h_tw, body, fps, gfx_tags, os.path.splitext(os.path.basename(path))[0])


def _define_solid_shape(shape_id: int, w_tw: int, h_tw: int, rgba: tuple, fill_side: str = "1") -> bytes:
    """DefineShape3 (tag 32): dreptunghi umplut cu o culoare (RGBA), fara nicio imagine. Folosit ca test: daca
    dreptunghiul apare pe radar si imaginea nu, jocul refuza imaginea incorporata, nu fisierul."""
    body = bytearray(struct.pack("<H", shape_id))
    body += _rect(0, w_tw, 0, h_tw)
    body += b"\x01"                              # FillStyleCount = 1
    body += b"\x00" + bytes(rgba)                # solid, RGBA
    body += b"\x00"                              # LineStyleCount = 0
    body += _rect_records(w_tw, h_tw, fill_side)
    return _tag(32, bytes(body))


def write_solid_gfx(path: str, w_px: int, h_px: int, rgba=(255, 0, 0, 160), signature: bytes = b"GFX", fps: int = 24,
                    gfx_tags: bool = True, fill_side: str = "1"):
    """Un .gfx cu un simplu dreptunghi colorat de w_px x h_px, pentru testarea afisarii pe radar."""
    import os
    w_tw, h_tw = w_px * TWIPS, h_px * TWIPS
    body = _define_solid_shape(1, w_tw, h_tw, tuple(rgba), fill_side) + _place_object(1, 1)
    return _write_movie(path, signature, w_tw, h_tw, body, fps, gfx_tags, os.path.splitext(os.path.basename(path))[0])


def overlay_display_args(origin_x: float, origin_y: float, size: float, w_px: int, h_px: int):
    """Argumentele pentru SetMinimapOverlayDisplay (x, y, xScale, yScale): y-ul din Flash e inversat."""
    return (float(origin_x), -float(origin_y + size), 100.0 * size / w_px, 100.0 * size / h_px)
