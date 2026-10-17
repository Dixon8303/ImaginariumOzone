#!/usr/bin/env python3
"""Render the LaunchAI app icon and package it as LaunchAI.icns.

A chrome-blue power button — a ring open at the top with the stem standing in the gap — and
the lettering sitting inside it, on a macOS-style plate. The blue is E.A.T. Media's #0292EB.

    python3 make_icon.py                  # "BGF" -> LaunchAI.png + LaunchAI.icns next to this file
    python3 make_icon.py --text AI        # any short capital-letter text, e.g. the earlier AI version
    python3 make_icon.py --out some/dir   # write the files somewhere else

Needs Pillow and a heavy sans font (Inter Black if installed, else Arial Black or DejaVu Bold).
The repo already holds the rendered files, so the Mac installer never runs this.
"""

import argparse
import io
import math
import os
import struct
import sys
from pathlib import Path

try:
    from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps
except ImportError:
    sys.exit("Pillow is required:  python3 -m pip install Pillow")

SS = 3                      # supersampling factor
SIZE = 1024
N = SIZE * SS

FONTS = [
    "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf",
    "/usr/share/fonts/opentype/inter/Inter-Black.otf",
    "/Library/Fonts/Inter-Black.otf",
    os.path.expanduser("~/Library/Fonts/Inter-Black.otf"),
    "/System/Library/Fonts/Supplemental/Arial Black.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def px(v):
    """Design units (a 1024 grid) to canvas pixels."""
    return v * SS


# ── colour ramps ──────────────────────────────────────────────────────────────
BRAND = (2, 146, 235)       # E.A.T. Media blue

# Chrome: dark edge, brand blue, a bright specular band, a darker trough, then a bounce light.
CHROME = [
    (0.00, (0, 38, 108)),
    (0.13, (2, 118, 220)),
    (0.31, (208, 240, 255)),
    (0.43, BRAND),
    (0.57, (0, 92, 184)),
    (0.75, (0, 46, 118)),
    (0.90, (40, 164, 248)),
    (1.00, (0, 36, 100)),
]
PLATE = [(0.0, (16, 32, 62)), (0.55, (7, 15, 34)), (1.0, (3, 7, 18))]


def ramp(stops, t):
    t = max(0.0, min(1.0, t))
    for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
        if t <= t1:
            k = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
            return tuple(int(round(c0[i] + (c1[i] - c0[i]) * k)) for i in range(3))
    return stops[-1][1]


def vertical_gradient(stops, top, bottom):
    """N x N RGB image whose colour depends only on y, spanning top..bottom."""
    img = Image.new("RGB", (N, N))
    d = ImageDraw.Draw(img)
    span = max(1, bottom - top)
    for y in range(N):
        d.line([(0, y), (N, y)], fill=ramp(stops, (y - top) / span))
    return img


def solid(color):
    return Image.new("RGB", (N, N), color)


# ── mask + compositing helpers ────────────────────────────────────────────────
def blank():
    return Image.new("L", (N, N), 0)


def put(canvas, rgb, mask, opacity=1.0):
    """Alpha-composite an RGB fill through a mask onto an RGBA canvas."""
    layer = rgb.convert("RGBA")
    if opacity < 1.0:
        mask = mask.point(lambda v: int(v * opacity))
    layer.putalpha(mask)
    return Image.alpha_composite(canvas, layer)


def soften(mask, radius):
    """Round off corners while keeping a soft (anti-aliased) edge."""
    blurred = mask.filter(ImageFilter.GaussianBlur(px(radius)))
    return blurred.point(lambda v: max(0, min(255, int((v - 128) * 6 + 128))))


def drop_shadow(canvas, mask, dy, blur, opacity):
    shadow = ImageChops.offset(mask.filter(ImageFilter.GaussianBlur(px(blur))), 0, px(dy))
    return put(canvas, solid((0, 0, 0)), shadow, opacity)


def glow(canvas, mask, blur, opacity, color=BRAND):
    return put(canvas, solid(color), mask.filter(ImageFilter.GaussianBlur(px(blur))), opacity)


def chrome(canvas, mask, bevel=5):
    """Fill a shape with the chrome gradient and add a bevelled edge."""
    box = mask.getbbox()
    canvas = put(canvas, vertical_gradient(CHROME, box[1], box[3]), mask)
    d = px(bevel)
    light = ImageChops.subtract(mask, ImageChops.offset(mask, d, d)).filter(ImageFilter.GaussianBlur(px(1.2)))
    dark = ImageChops.subtract(mask, ImageChops.offset(mask, -d, -d)).filter(ImageFilter.GaussianBlur(px(1.2)))
    canvas = put(canvas, solid((228, 246, 255)), light, 0.85)
    canvas = put(canvas, solid((0, 20, 66)), dark, 0.70)
    return canvas


# ── shapes ────────────────────────────────────────────────────────────────────
def squircle(cx, cy, half, n=5.0, steps=720):
    pts = []
    for i in range(steps):
        t = 2 * math.pi * i / steps
        c, s = math.cos(t), math.sin(t)
        pts.append((cx + half * math.copysign(abs(c) ** (2 / n), c),
                    cy + half * math.copysign(abs(s) ** (2 / n), s)))
    return pts


def polar(cx, cy, radius, deg):
    """Point at `deg` degrees clockwise from twelve o'clock."""
    a = math.radians(deg)
    return cx + radius * math.sin(a), cy - radius * math.cos(a)


def disc(cx, cy, r):
    m = blank()
    ImageDraw.Draw(m).ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    return m


def ring_mask(cx, cy, r_out, r_in, gap_from, gap_to):
    """A ring with rounded ends, open between two angles (degrees clockwise from the top)."""
    m = blank()
    d = ImageDraw.Draw(m)
    d.ellipse([cx - r_out, cy - r_out, cx + r_out, cy + r_out], fill=255)
    d.ellipse([cx - r_in, cy - r_in, cx + r_in, cy + r_in], fill=0)
    wedge = [(cx, cy)] + [polar(cx, cy, r_out * 2, gap_from + (gap_to - gap_from) * i / 48) for i in range(49)]
    d.polygon(wedge, fill=0)
    mid, cap = (r_out + r_in) / 2, (r_out - r_in) / 2
    for deg in (gap_from, gap_to):
        x, y = polar(cx, cy, mid, deg)
        d.ellipse([x - cap, y - cap, x + cap, y + cap], fill=255)
    return m


def load_font(size):
    for path in FONTS:
        if os.path.exists(path):
            return ImageFont.truetype(path, int(size))
    sys.exit("No heavy sans font found. Install Inter (fonts-inter) or edit FONTS in make_icon.py.")


def text_mask(text, cap_px, track=0.035):
    """The text as a mask, cropped to its ink, with a cap height of cap_px pixels."""
    probe = load_font(400)
    box = probe.getbbox("H")
    font = load_font(400 * cap_px / (box[3] - box[1]))
    pad = int(cap_px)
    advance = [font.getlength(c) for c in text]
    width = int(sum(advance) + cap_px * track * len(text)) + 2 * pad
    m = Image.new("L", (width, int(cap_px * 2.2)), 0)
    d = ImageDraw.Draw(m)
    x, base = pad, cap_px * 1.35
    for c, adv in zip(text, advance):
        d.text((x, base), c, font=font, fill=255, anchor="ls")
        x += adv + cap_px * track
    return m.crop(m.getbbox())


def fitted_text(text, r_in, y_off, h_max):
    """The biggest text block that sits inside the ring's inner circle, centred y_off below the middle."""
    unit = text_mask(text, 100)
    aspect = unit.width / unit.height              # block width / block height
    h = h_max
    while h > 40:
        half_w = h * aspect / 2
        if math.hypot(half_w, y_off + h / 2) <= r_in - px(30):
            break
        h -= px(1)
    return text_mask(text, h * 100 / unit.height)


def build(text="AI"):
    cx, cy = px(512), px(534)
    r_out, r_in = px(338), px(266)
    stem_w, clear = px(60), px(26)
    canvas = Image.new("RGBA", (N, N), (0, 0, 0, 0))

    # plate ───────────────────────────────────────────────────────────────────
    plate = blank()
    ImageDraw.Draw(plate).polygon(squircle(px(512), px(512), px(412)), fill=255)
    canvas = drop_shadow(canvas, plate, dy=16, blur=22, opacity=0.55)
    canvas = put(canvas, vertical_gradient(PLATE, px(100), px(924)), plate)
    pool = ImageChops.multiply(disc(cx, cy, px(360)).filter(ImageFilter.GaussianBlur(px(80))), plate)
    canvas = put(canvas, solid((10, 70, 160)), pool, 0.55)
    rim = ImageChops.subtract(plate, ImageChops.offset(plate, 0, px(3))).filter(ImageFilter.GaussianBlur(px(1)))
    canvas = put(canvas, solid((150, 200, 255)), rim, 0.45)
    sheen = blank()
    ImageDraw.Draw(sheen).ellipse([px(140), px(40), px(884), px(520)], fill=255)
    sheen = ImageChops.multiply(sheen.filter(ImageFilter.GaussianBlur(px(36))), plate)
    canvas = put(canvas, solid((255, 255, 255)), sheen, 0.08)

    # the power ring, open at the top for the stem ────────────────────────────
    mid, cap = (r_out + r_in) / 2, (r_out - r_in) / 2
    half_gap = math.degrees(math.asin((stem_w / 2 + clear + cap) / mid))
    ring = ring_mask(cx, cy, r_out, r_in, -half_gap, half_gap)
    canvas = glow(canvas, ring, 28, 0.75)

    # recessed glass inside the ring, so the lettering has something to sit on ─
    well = disc(cx, cy, r_in + px(4))
    lit = ImageOps.invert(Image.radial_gradient("L")).resize((int(2 * r_in), int(2 * r_in)), Image.BICUBIC)
    spot = blank()
    spot.paste(lit, (int(cx - r_in), int(cy - r_in)))
    canvas = put(canvas, vertical_gradient([(0, (3, 9, 24)), (1, (2, 6, 16))], int(cy - r_in), int(cy + r_in)), well)
    canvas = put(canvas, solid((8, 52, 128)), ImageChops.multiply(spot, well), 0.55)
    canvas = put(canvas, solid((0, 0, 0)), ImageChops.multiply(ring.filter(ImageFilter.GaussianBlur(px(16))), well), 0.85)

    canvas = drop_shadow(canvas, ring, dy=10, blur=10, opacity=0.55)
    canvas = chrome(canvas, ring, bevel=5)

    # lettering ───────────────────────────────────────────────────────────────
    y_off = px(38)
    block = fitted_text(text, r_in, y_off, px(280))
    bx, by = int(cx - block.width / 2), int(cy + y_off - block.height / 2)
    letters = blank()
    letters.paste(block, (bx, by))
    letters = soften(letters, 0.7)
    top = by

    # stem: from just above the ring down to a clear gap above the lettering
    stem_bottom = min(cy - px(95), top - px(62))
    stem = blank()
    ImageDraw.Draw(stem).rounded_rectangle([cx - stem_w / 2, cy - r_out - px(36), cx + stem_w / 2, stem_bottom],
                                           radius=stem_w / 2, fill=255)
    stem = soften(stem, 1.0)
    canvas = glow(canvas, stem, 18, 0.7)
    canvas = drop_shadow(canvas, stem, dy=8, blur=8, opacity=0.5)
    canvas = chrome(canvas, stem, bevel=4)

    canvas = glow(canvas, letters, 16, 0.55)
    canvas = drop_shadow(canvas, letters, dy=9, blur=8, opacity=0.65)
    canvas = chrome(canvas, letters, bevel=4)

    return canvas.resize((SIZE, SIZE), Image.LANCZOS)


# ── ICNS packaging ────────────────────────────────────────────────────────────
ICNS_TYPES = [          # (type, pixel size). PNG payloads, readable on macOS 10.7+
    (b"icp4", 16), (b"icp5", 32), (b"icp6", 64), (b"ic07", 128), (b"ic08", 256),
    (b"ic09", 512), (b"ic10", 1024), (b"ic11", 32), (b"ic12", 64), (b"ic13", 256), (b"ic14", 512),
]


def write_icns(master, path):
    cache, chunks = {}, []
    for tag, size in ICNS_TYPES:
        if size not in cache:
            buf = io.BytesIO()
            (master if size == master.width else master.resize((size, size), Image.LANCZOS)).save(buf, "PNG", optimize=True)
            cache[size] = buf.getvalue()
        chunks.append(struct.pack(">4sI", tag, 8 + len(cache[size])) + cache[size])
    body = b"".join(chunks)
    path.write_bytes(struct.pack(">4sI", b"icns", 8 + len(body)) + body)


def main():
    ap = argparse.ArgumentParser(description="Render the LaunchAI icon.")
    ap.add_argument("--text", default="BGF", help="the lettering, capitals (default: BGF)")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent), help="output folder")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    master = build(args.text.upper())
    master.save(out / "LaunchAI.png", "PNG", optimize=True)
    write_icns(master, out / "LaunchAI.icns")
    print("Wrote", out / "LaunchAI.png", "and", out / "LaunchAI.icns")


if __name__ == "__main__":
    main()
