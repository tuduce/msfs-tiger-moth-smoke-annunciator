"""Procedural vintage / chipped-paint texture set for the smoke annunciator.

Pure numpy (runs inside Blender's bundled python).  Writes MSFS style PBR PNGs:
    <name>_ALBD.PNG  base colour (sRGB)
    <name>_COMP.PNG  R=occlusion  G=roughness  B=metallic
    <name>_NORM.PNG  tangent space normal, DirectX (Y-) convention

All textures are one 1024x1024 atlas.  Region layout (u,v rects, v up) is shared with
build_annunciator.py through ATLAS below.
"""
import os
import struct
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402

SIZE = 1024

# name -> (u0, v0, u1, v1, physical_width_mm, physical_height_mm)
ATLAS = {
    "FRONT":  (0.00, 0.50, 1.00, 1.00, 60.0, 30.0),
    "TOP":    (0.00, 0.25, 0.50, 0.50, 60.0, 15.0),
    "BOTTOM": (0.50, 0.25, 1.00, 0.50, 60.0, 15.0),
    "LEFT":   (0.00, 0.00, 0.25, 0.25, 15.0, 30.0),
    "RIGHT":  (0.25, 0.00, 0.50, 0.25, 15.0, 30.0),
    "BACK":   (0.50, 0.125, 1.00, 0.25, 60.0, 30.0),
    # plain material swatches for the hardware (screws, bezels, nut, lever)
    "CHROME": (0.500, 0.0, 0.625, 0.125, 10.0, 10.0),
    "BRASS":  (0.625, 0.0, 0.750, 0.125, 10.0, 10.0),
    "STEEL":  (0.750, 0.0, 0.875, 0.125, 10.0, 10.0),
    "RUBBER": (0.875, 0.0, 1.000, 0.125, 10.0, 10.0),
}

# ---------------------------------------------------------------- tiny 5x7 stencil font
FONT = {
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "W": ["10001", "10001", "10001", "10101", "10101", "11011", "10001"],
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "N": ["10001", "11001", "10101", "10101", "10011", "10001", "10001"],
    "G": ["01110", "10001", "10000", "10111", "10001", "10001", "01111"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    " ": ["00000"] * 7,
}


def write_png(path, arr):
    """arr: uint8 HxWx3 or HxWx4, row 0 = top."""
    h, w, c = arr.shape
    colour_type = {3: 2, 4: 6}[c]
    raw = b"".join(b"\x00" + arr[y].tobytes() for y in range(h))

    def chunk(tag, data):
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, colour_type, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 6))
           + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)


# ---------------------------------------------------------------- noise helpers
def _smooth(t):
    return t * t * (3.0 - 2.0 * t)


def vnoise(h, w, cell, rng):
    gh = int(np.ceil(h / cell)) + 2
    gw = int(np.ceil(w / cell)) + 2
    g = rng.random((gh, gw)).astype(np.float32)
    ys = np.arange(h, dtype=np.float32) / cell
    xs = np.arange(w, dtype=np.float32) / cell
    y0 = ys.astype(int)
    x0 = xs.astype(int)
    fy = _smooth(ys - y0)[:, None]
    fx = _smooth(xs - x0)[None, :]
    a = g[y0][:, x0]
    b = g[y0][:, x0 + 1]
    c = g[y0 + 1][:, x0]
    d = g[y0 + 1][:, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def fbm(h, w, cell, octaves, rng):
    out = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    for _ in range(octaves):
        out += amp * vnoise(h, w, max(cell, 1.5), rng)
        tot += amp
        amp *= 0.5
        cell /= 2.0
    out /= tot
    lo, hi = out.min(), out.max()
    return (out - lo) / (hi - lo + 1e-9)


def boxblur(a, r):
    if r < 1:
        return a
    for axis in (0, 1):
        pad = [(0, 0), (0, 0)]
        pad[axis] = (r + 1, r)
        c = np.cumsum(np.pad(a, pad, mode="edge"), axis=axis, dtype=np.float64)
        n = a.shape[axis]
        sl_hi = [slice(None)] * 2
        sl_lo = [slice(None)] * 2
        sl_hi[axis] = slice(2 * r + 1, 2 * r + 1 + n)
        sl_lo[axis] = slice(0, n)
        a = ((c[tuple(sl_hi)] - c[tuple(sl_lo)]) / (2 * r + 1)).astype(np.float32)
    return a


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0 + 1e-9), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def mix(a, b, t):
    return a * (1 - t[..., None]) + b * t[..., None]


# ---------------------------------------------------------------- region helpers
def rect_px(name):
    u0, v0, u1, v1, pw, ph = ATLAS[name]
    x0, x1 = int(round(u0 * SIZE)), int(round(u1 * SIZE))
    y0, y1 = int(round((1 - v1) * SIZE)), int(round((1 - v0) * SIZE))  # image rows, top-down
    return x0, y0, x1, y1


def edge_distance_mm():
    """Distance (mm) to the nearest border of the atlas region each pixel belongs to."""
    d = np.full((SIZE, SIZE), 99.0, np.float32)
    yy, xx = np.mgrid[0:SIZE, 0:SIZE]
    for name in ATLAS:
        x0, y0, x1, y1 = rect_px(name)
        _, _, _, _, pw, ph = ATLAS[name]
        sx = pw / (x1 - x0)
        sy = ph / (y1 - y0)
        sub_x = xx[y0:y1, x0:x1] - x0
        sub_y = yy[y0:y1, x0:x1] - y0
        dist = np.minimum.reduce([sub_x * sx, (x1 - 1 - x0 - sub_x) * sx,
                                  sub_y * sy, (y1 - 1 - y0 - sub_y) * sy])
        d[y0:y1, x0:x1] = dist
    return d


def stencil_mask(text, cx_mm, cy_mm, cap_mm):
    """Letter mask on the FRONT region.  cx/cy measured from the pilot's left/bottom of the face."""
    x0, y0, x1, y1 = rect_px("FRONT")
    mask = np.zeros((SIZE, SIZE), np.float32)
    px_per_mm = (x1 - x0) / 60.0
    pix = cap_mm / 7.0 * px_per_mm              # size of one font pixel
    adv = 6 * pix                               # advance incl. 1 px gap
    total_w = len(text) * adv - pix
    start_x = x0 + (cx_mm * px_per_mm) - total_w / 2.0
    top_y = y0 + ((30.0 - cy_mm) * px_per_mm) - 3.5 * pix
    for i, ch in enumerate(text):
        glyph = FONT[ch]
        for r, row in enumerate(glyph):
            for c, bit in enumerate(row):
                if bit == "1":
                    xa = int(round(start_x + i * adv + c * pix))
                    xb = int(round(start_x + i * adv + (c + 1) * pix))
                    ya = int(round(top_y + r * pix))
                    yb = int(round(top_y + (r + 1) * pix))
                    mask[ya:yb, xa:xb] = 1.0
    return mask


def front_marks():
    """Painted lettering mask + engraved ring/line marks for the front face."""
    m = np.zeros((SIZE, SIZE), np.float32)
    for letter, x in (("R", 11.0), ("W", 24.0), ("B", 37.0)):
        m = np.maximum(m, stencil_mask(letter, x, 5.8, 2.4))
    m = np.maximum(m, stencil_mask("SMOKE", 24.0, 26.6, 2.0))
    m = np.maximum(m, stencil_mask("LONG", 50.0, 26.4, 2.0))
    m = np.maximum(m, stencil_mask("SHORT", 50.0, 6.4, 2.0))
    # thin divider line between lamp bank and switch
    x0, y0, x1, y1 = rect_px("FRONT")
    ppm = (x1 - x0) / 60.0
    xl = int(x0 + 43.2 * ppm)
    ya = int(y0 + (30 - 24.0) * ppm)
    yb = int(y0 + (30 - 6.0) * ppm)
    m[ya:yb, xl:xl + max(2, int(0.25 * ppm))] = 1.0
    return m


# ---------------------------------------------------------------- main generator
def generate(out_dir, name="ANNUNCIATOR", seed=7, dds_dir=None):
    rng = np.random.default_rng(seed)
    H = W = SIZE
    f = np.float32

    edge = edge_distance_mm()
    n_lo = fbm(H, W, 220, 3, rng)
    n_mid = fbm(H, W, 40, 4, rng)
    n_hi = fbm(H, W, 7, 3, rng)
    n_fine = rng.random((H, W)).astype(f)

    # ---- paint / wear masks -------------------------------------------------
    edge_w = np.exp(-edge / 1.4)                          # strongest at region borders (= bevelled edges)
    corner_w = np.exp(-edge / 2.6) * 0.45
    wear = edge_w * 1.25 + corner_w * (n_mid - 0.35) + 0.55 * (n_lo - 0.5) + 0.45 * (n_hi - 0.5)
    # sparse impact chips in the middle of faces
    blobs = smoothstep(0.66, 0.76, n_mid * 0.7 + n_hi * 0.4)
    wear = wear + blobs * 0.8
    bare = smoothstep(0.62, 0.70, wear)                   # bare steel
    primer = smoothstep(0.42, 0.50, wear) * (1 - bare)    # red-oxide primer under the paint
    rust_halo = boxblur(bare, 9) * smoothstep(0.35, 0.65, n_mid)
    rust = np.clip(rust_halo * 1.6, 0, 1) * (1 - bare * 0.4)
    grime = np.clip(0.38 + 0.7 * (n_lo - 0.4) + 0.5 * edge_w * (n_hi), 0, 1) * 0.62
    # scratches: thin random lines blurred a touch
    scratch = np.zeros((H, W), f)
    for _ in range(55):
        x = rng.integers(0, W)
        y = rng.integers(0, H)
        ang = rng.uniform(0, np.pi)
        ln = rng.integers(10, 55)
        for t in range(ln):
            xi = int(x + np.cos(ang) * t)
            yi = int(y + np.sin(ang) * t)
            if 0 <= xi < W and 0 <= yi < H:
                scratch[yi, xi] = rng.uniform(0.35, 0.8)
    scratch = np.clip(boxblur(scratch, 1) * 4.0, 0, 1)

    # ---- colour -------------------------------------------------------------
    paint_a = np.array([54, 62, 42], f) / 255.0           # faded olive drab
    paint_b = np.array([70, 76, 50], f) / 255.0           # sun bleached
    steel = np.array([128, 128, 122], f) / 255.0
    primer_c = np.array([112, 58, 44], f) / 255.0
    rust_c = np.array([128, 66, 28], f) / 255.0
    grime_c = np.array([26, 22, 17], f) / 255.0

    paint = mix(np.broadcast_to(paint_a, (H, W, 3)), np.broadcast_to(paint_b, (H, W, 3)), smoothstep(0.3, 0.8, n_lo))
    paint = paint * (0.92 + 0.16 * n_fine[..., None])
    albedo = mix(paint, np.broadcast_to(primer_c, (H, W, 3)), primer)
    albedo = mix(albedo, np.broadcast_to(steel, (H, W, 3)) * (0.7 + 0.5 * n_mid[..., None]), bare)
    albedo = mix(albedo, np.broadcast_to(rust_c, (H, W, 3)) * (0.6 + 0.6 * n_hi[..., None]), rust * 0.85)
    albedo = mix(albedo, np.broadcast_to(grime_c, (H, W, 3)), grime * (1 - bare * 0.5))

    # stencil lettering (faded off-white), chipped with the same wear
    marks = front_marks()
    letter_c = np.array([196, 186, 150], f) / 255.0
    letter_vis = marks * (1 - smoothstep(0.50, 0.62, wear + 0.25 * (n_hi - 0.5))) * 0.9
    albedo = mix(albedo, np.broadcast_to(letter_c, (H, W, 3)) * (0.75 + 0.3 * n_mid[..., None]), letter_vis)
    # scratches expose steel
    albedo = mix(albedo, np.broadcast_to(steel, (H, W, 3)), scratch * 0.65 * (1 - bare))

    metallic = np.clip(bare * 0.92 + scratch * 0.5 + rust * 0.15, 0, 1)
    rough = (0.74 + 0.12 * (n_mid - 0.5)) * (1 - bare) + (0.42 + 0.2 * n_hi) * bare
    rough = np.clip(rough + rust * 0.3 + grime * 0.15 - scratch * 0.15, 0.08, 1.0)
    occl = np.clip(1.0 - grime * 0.45 - rust * 0.15 - 0.25 * edge_w * (1 - bare), 0.2, 1.0)

    height = np.zeros((H, W), f)
    height -= bare * 0.9 + primer * 0.45               # chips are recessed (paint missing)
    height += letter_vis * 0.35
    height -= scratch * 0.4
    height += (n_hi - 0.5) * 0.12 + (n_fine - 0.5) * 0.05
    height += rust * (n_hi - 0.3) * 0.25

    # ---- hardware swatches overwrite their regions ---------------------------
    def swatch(region, col, met, rgh, tarnish):
        x0, y0, x1, y1 = rect_px(region)
        sl = (slice(y0, y1), slice(x0, x1))
        t = fbm(y1 - y0, x1 - x0, 14, 3, rng)
        c = np.array(col, f) / 255.0
        a = c[None, None, :] * (1 - tarnish * 0.5 * t[..., None]) * (0.85 + 0.25 * t[..., None])
        a = mix(a, np.broadcast_to(grime_c, a.shape), tarnish * 0.35 * smoothstep(0.55, 0.9, t))
        albedo[sl] = np.clip(a, 0, 1)
        metallic[sl] = met
        rough[sl] = np.clip(rgh + tarnish * 0.35 * t, 0, 1)
        occl[sl] = 1.0 - 0.2 * tarnish * t
        height[sl] = (t - 0.5) * 0.1 * tarnish

    swatch("CHROME", (176, 176, 172), 1.0, 0.30, 0.55)
    swatch("BRASS", (160, 120, 52), 1.0, 0.38, 0.70)
    swatch("STEEL", (58, 58, 60), 0.9, 0.50, 0.50)
    swatch("RUBBER", (28, 28, 28), 0.0, 0.85, 0.30)

    # ---- normal map (DirectX: green points down the image) -------------------
    hs = boxblur(height, 1)
    gy, gx = np.gradient(hs)
    strength = 14.0
    nx = -gx * strength
    ny = -gy * strength                                    # image-down = +green in DirectX
    nz = np.ones_like(nx)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    normal = np.stack([nx / ln, ny / ln, nz / ln], axis=-1) * 0.5 + 0.5

    def u8(a):
        return (np.clip(a, 0, 1) * 255.0 + 0.5).astype(np.uint8)

    comp = np.stack([occl, rough, metallic], axis=-1)
    write_png(f"{out_dir}/{name}_ALBD.PNG", u8(albedo))
    write_png(f"{out_dir}/{name}_COMP.PNG", u8(comp))
    write_png(f"{out_dir}/{name}_NORM.PNG", u8(normal))
    import dds
    dds_dir = dds_dir or out_dir
    sizes = [dds.write_dds(f"{dds_dir}/{name}_ALBD.PNG.DDS", np.clip(albedo, 0, 1) * 255.0, "albd"),
             dds.write_dds(f"{dds_dir}/{name}_COMP.PNG.DDS", np.clip(comp, 0, 1) * 255.0, "comp"),
             dds.write_dds(f"{dds_dir}/{name}_NORM.PNG.DDS", np.clip(normal, 0, 1), "norm")]
    return {"wear_bare_pct": float(bare.mean() * 100.0), "dds_bytes": sizes}


if __name__ == "__main__":
    import sys
    print(generate(sys.argv[1] if len(sys.argv) > 1 else "."))
