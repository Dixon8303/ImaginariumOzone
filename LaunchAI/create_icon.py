#!/usr/bin/env python3
"""
Generates the LaunchAI icon: metallic blue 'AI' letters fused with a
power-button ring, then packages everything into LaunchAI.icns.

Requirements: pip install Pillow
Usage:        python3 create_icon.py
Output:       LaunchAI.icns  (place inside LaunchAI.app/Contents/Resources/)
"""

import math
import os
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
except ImportError:
    sys.exit("Pillow not installed. Run:  pip install Pillow")


# ── Metallic-blue palette ──────────────────────────────────────────────────────
BG          = (10,  14,  26, 255)   # near-black navy
RING_DARK   = (20,  80, 160, 255)   # deep blue
RING_MID    = (50, 140, 240, 255)   # bright blue
RING_LIGHT  = (160, 210, 255, 255)  # specular highlight
GLOW        = (30, 100, 220,  90)   # outer glow (semi-transparent)
TEXT_DARK   = (30,  90, 180, 255)
TEXT_MID    = (70, 160, 255, 255)
TEXT_LIGHT  = (200, 230, 255, 255)
NOTCH       = (10,  14,  26, 255)   # power-button gap matches bg


def lerp_color(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(4))


def metallic_stop(t):
    """4-stop metallic blue gradient: dark → bright → mid → dark."""
    if t < 0.25:
        return lerp_color(RING_DARK, RING_MID, t / 0.25)
    elif t < 0.45:
        return lerp_color(RING_MID, RING_LIGHT, (t - 0.25) / 0.20)
    elif t < 0.65:
        return lerp_color(RING_LIGHT, RING_MID, (t - 0.45) / 0.20)
    else:
        return lerp_color(RING_MID, RING_DARK, (t - 0.65) / 0.35)


def text_metallic_stop(t):
    if t < 0.3:
        return lerp_color(TEXT_DARK, TEXT_LIGHT, t / 0.3)
    elif t < 0.55:
        return lerp_color(TEXT_LIGHT, TEXT_MID, (t - 0.3) / 0.25)
    else:
        return lerp_color(TEXT_MID, TEXT_DARK, (t - 0.55) / 0.45)


def draw_metallic_ring(draw, cx, cy, r_outer, r_inner, gap_deg=60, gap_width=8):
    """
    Draw a power-button ring: full circle with a notch cut at the top,
    coloured with a metallic-blue vertical gradient.
    """
    size = r_outer * 2 + 4
    # rasterise ring pixel-by-pixel for the gradient
    img_ring = Image.new("RGBA", (int(size), int(size)), (0, 0, 0, 0))
    px = img_ring.load()
    half = size / 2
    for y in range(int(size)):
        for x in range(int(size)):
            dx = x - half
            dy = y - half
            dist = math.hypot(dx, dy)
            if r_inner <= dist <= r_outer:
                angle = math.degrees(math.atan2(dx, -dy)) % 360
                # cut the notch at top (centred on 0°)
                if angle <= gap_deg / 2 or angle >= 360 - gap_deg / 2:
                    continue
                t = (y / size)          # vertical gradient position
                col = metallic_stop(t)
                px[x, y] = col
    # paste ring onto draw's image at offset
    offset = (int(cx - half), int(cy - half))
    draw._image.paste(img_ring, offset, img_ring)


def draw_power_stem(draw, cx, cy, top_y, stem_h, stem_w):
    """Draw the vertical line of the power button with metallic gradient."""
    x0 = int(cx - stem_w / 2)
    x1 = int(cx + stem_w / 2)
    y0 = int(top_y)
    y1 = int(top_y + stem_h)
    total_h = y1 - y0
    for y in range(y0, y1):
        t = (y - y0) / max(total_h - 1, 1)
        col = metallic_stop(t)
        draw.rectangle([x0, y, x1, y], fill=col)


def draw_ai_text(img, cx, cy, font_size):
    """
    Render 'AI' with a vertical metallic-blue gradient, centred at (cx,cy).
    Falls back to default PIL font if no system font is found.
    """
    # Try to find a bold system font
    font = None
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/liberation/LiberationSans-Bold.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                font = ImageFont.truetype(path, font_size)
                break
            except Exception:
                pass

    # Measure text on a scratch image
    scratch = Image.new("RGBA", (img.width * 2, img.height * 2), (0, 0, 0, 0))
    sd = ImageDraw.Draw(scratch)
    text = "AI"
    if font:
        bbox = sd.textbbox((0, 0), text, font=font)
    else:
        font = ImageFont.load_default()
        bbox = sd.textbbox((0, 0), text, font=font)

    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = int(cx - tw / 2 - bbox[0])
    ty = int(cy - th / 2 - bbox[1])

    # Render solid white text
    text_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    td = ImageDraw.Draw(text_layer)
    td.text((tx, ty), text, fill=(255, 255, 255, 255), font=font)

    # Build gradient mask same height as image
    gradient = Image.new("RGBA", img.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(gradient)
    for y in range(img.height):
        t = y / img.height
        col = text_metallic_stop(t) if y >= ty and y <= ty + th else (0, 0, 0, 0)
        gd.line([(0, y), (img.width, y)], fill=col)

    # Apply gradient only where text is opaque
    text_alpha = text_layer.split()[3]
    gradient.putalpha(text_alpha)

    img.paste(gradient, (0, 0), gradient)


def render_icon(size):
    img = Image.new("RGBA", (size, size), BG)
    draw = ImageDraw.Draw(img)

    cx = size / 2
    cy = size / 2

    # Outer glow
    glow_r = size * 0.44
    for r in range(int(glow_r), int(glow_r * 0.7), -1):
        alpha = int(GLOW[3] * (1 - (r - glow_r * 0.7) / (glow_r * 0.3)))
        draw.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            outline=(*GLOW[:3], max(0, alpha)),
            width=2,
        )

    # Ring geometry
    r_outer = size * 0.36
    ring_thickness = size * 0.065
    r_inner = r_outer - ring_thickness
    gap_deg = 58          # degrees open at top for power notch

    draw_metallic_ring(draw, cx, cy, r_outer, r_inner, gap_deg=gap_deg)

    # Power stem
    stem_w = ring_thickness * 0.9
    stem_top = cy - r_outer * 0.92
    stem_h = r_outer * 0.52
    draw_power_stem(draw, cx, cy, stem_top, stem_h, stem_w)

    # 'AI' text — sits in lower half of ring
    font_size = int(size * 0.28)
    text_cy = cy + size * 0.07
    draw_ai_text(img, cx, text_cy, font_size)

    # Subtle rounded-rect frame for the whole icon
    corner = size * 0.18
    frame_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    fd = ImageDraw.Draw(frame_layer)
    fd.rounded_rectangle([0, 0, size - 1, size - 1], radius=corner,
                         fill=(0, 0, 0, 0), outline=(*RING_MID[:3], 60), width=max(1, size // 90))
    img = Image.alpha_composite(img, frame_layer)

    # Soft specular gloss overlay at top-left
    gloss = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    for y in range(int(size * 0.45)):
        alpha = int(30 * (1 - y / (size * 0.45)))
        ImageDraw.Draw(gloss).line([(0, y), (int(size * 0.6), y)],
                                   fill=(255, 255, 255, alpha))
    img = Image.alpha_composite(img, gloss)

    return img


def build_icns(pngs: dict, out_path: str):
    """
    Assemble an ICNS file from a dict of {size: PIL.Image}.
    Handles the 8 standard sizes used by macOS.
    """
    ICNS_TYPES = {
        16:   b"icp4",
        32:   b"icp5",
        64:   b"icp6",
        128:  b"ic07",
        256:  b"ic08",
        512:  b"ic09",
        1024: b"ic10",
    }

    chunks = []
    for sz, tag in ICNS_TYPES.items():
        if sz not in pngs:
            continue
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            pngs[sz].save(f, format="PNG")
            tmp = f.name
        with open(tmp, "rb") as f:
            data = f.read()
        os.unlink(tmp)
        length = 8 + len(data)
        chunks.append(struct.pack(">4sI", tag, length) + data)

    total = 8 + sum(len(c) for c in chunks)
    with open(out_path, "wb") as f:
        f.write(struct.pack(">4sI", b"icns", total))
        for c in chunks:
            f.write(c)

    print(f"Written: {out_path}  ({total} bytes, {len(chunks)} sizes)")


def main():
    sizes = [16, 32, 64, 128, 256, 512, 1024]
    print("Rendering icon sizes:", sizes)
    pngs = {}
    for sz in sizes:
        print(f"  {sz}×{sz} …", end=" ", flush=True)
        pngs[sz] = render_icon(sz)
        print("ok")

    # Also save a 1024px preview PNG
    preview = Path("LaunchAI_preview.png")
    pngs[1024].save(preview, format="PNG")
    print(f"Preview saved: {preview}")

    build_icns(pngs, "LaunchAI.icns")
    print("\nDone! Copy LaunchAI.icns into LaunchAI.app/Contents/Resources/")


if __name__ == "__main__":
    main()
