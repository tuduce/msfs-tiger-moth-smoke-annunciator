"""Minimal DDS writer (numpy) producing the same formats the Ants Tiger Moth package ships:

    kind "albd" / "comp" -> BC1 (DXT1), opaque, full mip chain
    kind "norm"          -> BC5 signed (BC5S) two-channel tangent space normal (x,y), full mip chain

plus the <name>.DDS.json flags sidecar MSFS expects next to every texture.
Square power-of-two textures only.
"""
import json
import struct
import time

import numpy as np

FLAGS = {
    "albd": ["FL_BITMAP_COMPRESSION", "FL_BITMAP_MIPMAP"],
    "comp": ["FL_BITMAP_COMPRESSION", "FL_BITMAP_MIPMAP", "FL_BITMAP_NO_GAMMA_CORRECTION",
             "FL_BITMAP_METAL_ROUGH_AO_DATA"],
    "norm": ["FL_BITMAP_COMPRESSION", "FL_BITMAP_MIPMAP", "FL_BITMAP_TANGENT_DXT5N",
             "FL_BITMAP_NO_GAMMA_CORRECTION"],
}


def _pad4(a):
    h, w = a.shape[:2]
    ph, pw = (-h) % 4, (-w) % 4
    if ph or pw:
        a = np.pad(a, ((0, ph), (0, pw)) + ((0, 0),) * (a.ndim - 2), mode="edge")
    return a


def _blocks(a):
    """(H,W,C) -> (N,16,C) in raster block order, texels row-major inside a block."""
    a = _pad4(a)
    h, w, c = a.shape
    return a.reshape(h // 4, 4, w // 4, 4, c).transpose(0, 2, 1, 3, 4).reshape(-1, 16, c)


def _mips(a, renorm=False):
    out = [a]
    while a.shape[0] > 1 or a.shape[1] > 1:
        h, w = a.shape[:2]
        nh, nw = max(h // 2, 1), max(w // 2, 1)
        if h > 1 and w > 1:
            a = a.reshape(nh, 2, nw, 2, -1).mean(axis=(1, 3))
        elif h > 1:
            a = a.reshape(nh, 2, nw, -1).mean(axis=1)
        else:
            a = a.reshape(nh, nw, 2, -1).mean(axis=2)
        if renorm:                                   # keep (x,y,z) unit length: store xy only, z implied
            xy = a[..., :2]
            ln = np.sqrt((xy ** 2).sum(-1, keepdims=True))
            a = np.where(ln > 1.0, xy / np.maximum(ln, 1e-6), xy)
        out.append(a)
    return out


# ----------------------------------------------------------------------- BC1
def _enc565(rgb):
    r = np.clip(np.rint(rgb[..., 0] * 31 / 255.0), 0, 31).astype(np.uint16)
    g = np.clip(np.rint(rgb[..., 1] * 63 / 255.0), 0, 63).astype(np.uint16)
    b = np.clip(np.rint(rgb[..., 2] * 31 / 255.0), 0, 31).astype(np.uint16)
    return (r << 11) | (g << 5) | b


def _dec565(c):
    r = ((c >> 11) & 31).astype(np.float32) * 255.0 / 31
    g = ((c >> 5) & 63).astype(np.float32) * 255.0 / 63
    b = (c & 31).astype(np.float32) * 255.0 / 31
    return np.stack([r, g, b], -1)


def bc1(rgb):
    blk = _blocks(rgb.astype(np.float32))                       # (N,16,3)
    mn, mx = blk.min(1), blk.max(1)
    inset = (mx - mn) / 16.0
    mn, mx = mn + inset, mx - inset
    ca, cb = _enc565(mx), _enc565(mn)
    c0, c1 = np.maximum(ca, cb), np.minimum(ca, cb)             # c0 > c1 -> 4 colour mode
    p0, p1 = _dec565(c0), _dec565(c1)
    pal = np.stack([p0, p1, (2 * p0 + p1) / 3.0, (p0 + 2 * p1) / 3.0], 1)    # (N,4,3)
    d = ((blk[:, :, None, :] - pal[:, None, :, :]) ** 2).sum(-1)             # (N,16,4)
    idx = d.argmin(-1).astype(np.uint32)
    idx[c0 == c1] = 0
    bits = np.zeros(len(blk), np.uint32)
    for i in range(16):
        bits |= idx[:, i] << (2 * i)
    rec = np.empty(len(blk), dtype=[("c0", "<u2"), ("c1", "<u2"), ("bits", "<u4")])
    rec["c0"], rec["c1"], rec["bits"] = c0, c1, bits
    return rec.tobytes()


# ----------------------------------------------------------------------- BC5S (two signed BC4 channels)
def _bc4_signed(v):
    """v: (N,16) float in [-1,1] -> (N,8) uint8."""
    q = np.clip(np.rint(v * 127.0), -127, 127).astype(np.int16)
    e0, e1 = q.max(1), q.min(1)                                  # e0 >= e1 ; e0 > e1 -> 8 value mode
    k = np.arange(8)[None, :]
    pal = np.where(k == 0, e0[:, None],
          np.where(k == 1, e1[:, None],
                   ((8 - k) * e0[:, None] + (k - 1) * e1[:, None]) / 7.0))        # (N,8)
    d = np.abs(q[:, :, None].astype(np.float32) - pal[:, None, :])
    idx = d.argmin(-1).astype(np.uint64)
    idx[e0 == e1] = 0
    bits = np.zeros(len(q), np.uint64)
    for i in range(16):
        bits |= idx[:, i] << np.uint64(3 * i)
    out = np.zeros((len(q), 8), np.uint8)
    out[:, 0] = e0.astype(np.int8).view(np.uint8)
    out[:, 1] = e1.astype(np.int8).view(np.uint8)
    bb = bits.astype("<u8").view(np.uint8).reshape(-1, 8)
    out[:, 2:8] = bb[:, :6]
    return out


def bc5s(xy):
    blk = _blocks(xy.astype(np.float32))                          # (N,16,2)
    both = np.concatenate([_bc4_signed(blk[:, :, 0]), _bc4_signed(blk[:, :, 1])], axis=1)
    return both.tobytes()


# ----------------------------------------------------------------------- file
def write_dds(path, data, kind):
    """data: float array. albd/comp -> (H,W,3) 0..255 ; norm -> (H,W,3) 0..1 tangent normal (DirectX)."""
    assert data.shape[0] == data.shape[1] and (data.shape[0] & (data.shape[0] - 1)) == 0
    if kind == "norm":
        xy = data[..., :2] * 2.0 - 1.0
        levels, enc, fourcc, block = _mips(xy, renorm=True), bc5s, b"BC5S", 16
    else:
        levels, enc, fourcc, block = _mips(data[..., :3].astype(np.float32)), bc1, b"DXT1", 8
    body = b"".join(enc(m) for m in levels)
    h, w = data.shape[:2]
    linear = max(1, (w + 3) // 4) * max(1, (h + 3) // 4) * block
    flags = 0x1 | 0x2 | 0x4 | 0x1000 | 0x20000 | 0x80000
    header = struct.pack("<4s7I11I", b"DDS ", 124, flags, h, w, linear, 0, len(levels), *([0] * 11))
    header += struct.pack("<II4sIIIII", 32, 0x4, fourcc, 0, 0, 0, 0, 0)
    header += struct.pack("<5I", 0x401008, 0, 0, 0, 0)
    with open(path, "wb") as f:
        f.write(header + body)
    with open(path + ".json", "w") as f:
        json.dump({"Version": 2, "SourceFileDate": int(time.time() * 1e7) + 116444736000000000,
                   "Flags": FLAGS[kind]}, f, separators=(",", ":"))
    return len(header) + len(body)
