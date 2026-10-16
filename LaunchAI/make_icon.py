#!/usr/bin/env python3
"""Render the LaunchAI app icon and package it as LaunchAI.icns.

A chrome-blue power ring on a dark macOS-style plate. The ring is open at the
upper right and the "I" of "AI" is the power stem: it stands in the gap.

    python3 make_icon.py            # writes LaunchAI.png + LaunchAI.icns next to this file

Needs Pillow only. The repo already contains the rendered files, so the Mac
installer does not run this; it is here for regenerating or tweaking the icon.
"""

import io
import math
import struct
import sys
from pathlib import Path

try:
    from PIL import Image, ImageChops, ImageDraw, ImageFilter
except ImportError:
    sys.exit("Pillow is required:  python3 -m pip install Pillow")

SS = 3                      # supersampling factor
SIZE = 1024
N = SIZE * SS


def px(v):
    """Design units (a 1024 grid) to canvas pixels."""
    return v * SS


# ── colour ramps ──────────────────────────────────────────────────────────────
# Chrome look: dark edge, saturated blue, bright specular band, a darker trough,
# then a bounce light near the bottom edge.
CHROME = [
    (0.00, (6, 36, 110)),
    (0.14, (28, 106, 250)),
    (0.33, (196, 228, 255)),
    (0.45, (92, 170, 255)),
    (0.58, (20, 84, 212)),
    (0.76, (8, 42, 128)),
    (0.90, (56, 132, 244)),
    (1.00, (8, 30, 94)),
]
PLATE = [(0.0, (22, 38, 74)), (0.55, (10, 18, 40)), (1.0, (4, 8, 20))]


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


def chrome(canvas, mask, bevel=5):
    """Fill a shape with the chrome gradient and add a bevelled edge."""
    box = mask.getbbox()
    fill = vertical_gradient(CHROME, box[1], box[3])
    canvas = put(canvas, fill, mask)
    d = px(bevel)
    light = ImageChops.subtract(mask, ImageChops.offset(mask, d, d)).filter(ImageFilter.GaussianBlur(px(1.2)))
    dark = ImageChops.subtract(mask, ImageChops.offset(mask, -d, -d)).filter(ImageFilter.GaussianBlur(px(1.2)))
    canvas = put(canvas, solid((225, 242, 255)), light, 0.85)
    canvas = put(canvas, solid((4, 22, 70)), dark, 0.70)
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


def ring_mask(cx, cy, r_out, r_in, gap_from, gap_to):
    m = blank()
    d = ImageDraw.Draw(m)
    d.ellipse([cx - r_out, cy - r_out, cx + r_out, cy + r_out], fill=255)
    d.ellipse([cx - r_in, cy - r_in, cx + r_in, cy + r_in], fill=0)
    wedge = [(cx, cy)] + [polar(cx, cy, r_out * 2, gap_from + (gap_to - gap_from) * i / 48) for i in range(49)]
    d.polygon(wedge, fill=0)
    mid, cap = (r_out + r_in) / 2, (r_out - r_in) / 2          # round the two ends
    for deg in (gap_from, gap_to):
        x, y = polar(cx, cy, mid, deg)
        d.ellipse([x - cap, y - cap, x + cap, y + cap], fill=255)
    return m


def letter_a(x0, y_top, w, h, apex, stroke, bar_top, bar_h):
    """A bold, flat-topped capital A. All values in canvas pixels."""
    yb = y_top + h
    k = (w / 2 - apex / 2) / h                  # horizontal run per unit of height

    def left(y):                                # outer left edge
        return x0 + k * (yb - y)

    def right(y):
        return x0 + w - k * (yb - y)

    m = blank()
    d = ImageDraw.Draw(m)
    d.polygon([(x0, yb), (x0 + w / 2 - apex / 2, y_top), (x0 + w / 2 + apex / 2, y_top), (x0 + w, yb)], fill=255)
    y_in = yb - (w - 2 * stroke) / (2 * k)      # where the inner edges meet
    b1, b2 = bar_top, bar_top + bar_h
    d.polygon([(x0 + w / 2, y_in), (right(b1) - stroke, b1), (left(b1) + stroke, b1)], fill=0)   # counter
    d.polygon([(left(b2) + stroke, b2), (right(b2) - stroke, b2), (x0 + w - stroke, yb), (x0 + stroke, yb)], fill=0)
    return m


def build():
    cx, cy = px(512), px(548)
    canvas = Image.new("RGBA", (N, N), (0, 0, 0, 0))

    # plate ───────────────────────────────────────────────────────────────────
    plate = blank()
    ImageDraw.Draw(plate).polygon(squircle(px(512), px(512), px(412)), fill=255)
    canvas = drop_shadow(canvas, plate, dy=16, blur=22, opacity=0.55)
    canvas = put(canvas, vertical_gradient(PLATE, px(100), px(924)), plate)

    halo = blank()                                              # soft blue pool behind the ring
    ImageDraw.Draw(halo).ellipse([cx - px(330), cy - px(330), cx + px(330), cy + px(330)], fill=255)
    halo = ImageChops.multiply(halo.filter(ImageFilter.GaussianBlur(px(70))), plate)
    canvas = put(canvas, solid((26, 76, 190)), halo, 0.55)

    rim = ImageChops.subtract(plate, ImageChops.offset(plate, 0, px(3))).filter(ImageFilter.GaussianBlur(px(1)))
    canvas = put(canvas, solid((150, 190, 255)), rim, 0.45)     # thin light edge along the top

    gloss = blank()                                             # faint glass sheen on the upper half
    ImageDraw.Draw(gloss).ellipse([px(140), px(40), px(884), px(520)], fill=255)
    gloss = ImageChops.multiply(gloss.filter(ImageFilter.GaussianBlur(px(36))), plate)
    canvas = put(canvas, solid((255, 255, 255)), gloss, 0.09)

    # layout: A, then an I that is also the power stem ────────────────────────
    r_out, r_in = px(292), px(228)
    mid, cap = (r_out + r_in) / 2, (r_out - r_in) / 2
    base = cy + px(128)
    a_w, a_h, i_w, gap = px(236), px(262), px(70), px(36)
    left = cx - (a_w + gap + i_w) / 2
    i_x = left + a_w + gap

    # open the ring so the stem sits centred between its two rounded ends
    clear = px(24)
    gap_from = math.degrees(math.asin((i_x - clear - cap - cx) / mid))
    gap_to = math.degrees(math.asin((i_x + i_w + clear + cap - cx) / mid))

    # power ring ──────────────────────────────────────────────────────────────
    ring = ring_mask(cx, cy, r_out, r_in, gap_from, gap_to)
    glow = ring.filter(ImageFilter.GaussianBlur(px(26)))
    canvas = put(canvas, solid((40, 120, 255)), glow, 0.75)
    canvas = drop_shadow(canvas, ring, dy=10, blur=10, opacity=0.55)
    canvas = chrome(canvas, ring, bevel=5)

    # letters ─────────────────────────────────────────────────────────────────
    a = soften(letter_a(left, base - a_h, a_w, a_h, apex=px(84), stroke=px(66),
                        bar_top=base - px(104), bar_h=px(50)), 2.5)
    stem = blank()
    ImageDraw.Draw(stem).rounded_rectangle([i_x, cy - r_out - px(34), i_x + i_w, base], radius=i_w / 2, fill=255)
    stem = soften(stem, 1.5)
    letters = ImageChops.lighter(a, stem)
    canvas = drop_shadow(canvas, letters, dy=10, blur=9, opacity=0.6)
    canvas = chrome(canvas, a, bevel=5)
    canvas = chrome(canvas, stem, bevel=5)

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
    here = Path(__file__).resolve().parent
    master = build()
    master.save(here / "LaunchAI.png", "PNG", optimize=True)
    write_icns(master, here / "LaunchAI.icns")
    print("Wrote", here / "LaunchAI.png", "and", here / "LaunchAI.icns")


if __name__ == "__main__":
    main()
