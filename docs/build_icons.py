"""Generate PWA icons for Palmas Ride Engine.

Dev-only — run locally to (re)generate the committed PNGs in static/icons/.
Pillow is NOT a runtime dependency (not in requirements.txt); it's only used
here at build time.

    python3 docs/build_icons.py

Produces: icon-192.png, icon-512.png, icon-512-maskable.png,
apple-touch-icon.png (180), plus favicon.svg.

Design: accent-orange rounded field with a simple white bicycle mark — matches
the app's --accent-orange (#f0a030) on --bg (#0f0f1a).
"""

import os
from PIL import Image, ImageDraw

ORANGE = (240, 160, 48, 255)   # --accent-orange
DARK = (15, 15, 26, 255)       # --bg
WHITE = (255, 255, 255, 255)

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "icons")


def _draw_bike(d, cx, cy, scale, color, width):
    """Draw a minimal bicycle: two wheels + frame, centered on (cx, cy)."""
    r = int(28 * scale)               # wheel radius
    sep = int(46 * scale)             # half distance between hubs
    lw = max(2, int(width * scale))
    lh = cx - sep, cy                 # left hub
    rh = cx + sep, cy                 # right hub
    # Wheels
    for (hx, hy) in (lh, rh):
        d.ellipse([hx - r, hy - r, hx + r, hy + r], outline=color, width=lw)
    # Frame: simple triangle + seat/handlebar stems
    top = (cx - int(6 * scale), cy - int(34 * scale))   # saddle top
    bar = (cx + int(30 * scale), cy - int(34 * scale))  # handlebar top
    mid = (cx, cy)                                       # bottom bracket
    d.line([lh, top[0:2]], fill=color, width=lw)        # seat tube
    d.line([top, mid], fill=color, width=lw)
    d.line([mid, rh], fill=color, width=lw)
    d.line([lh, mid], fill=color, width=lw)             # down/chain stay
    d.line([mid, bar], fill=color, width=lw)            # down tube to bars
    d.line([top, bar], fill=color, width=lw)            # top tube
    d.line([bar[0], bar[1], rh[0], rh[1]], fill=color, width=lw)  # fork


def _rounded(size, radius_frac, bg, draw_mark=True, pad_frac=0.0):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = int(size * pad_frac)
    radius = int(size * radius_frac)
    d.rounded_rectangle([pad, pad, size - 1 - pad, size - 1 - pad],
                        radius=radius, fill=bg)
    if draw_mark:
        scale = size / 160.0
        _draw_bike(d, size // 2, int(size * 0.52), scale, WHITE, 6)
    return img


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    # Standard icons — rounded orange field, full bleed.
    _rounded(192, 0.22, ORANGE).save(os.path.join(OUT_DIR, "icon-192.png"))
    _rounded(512, 0.22, ORANGE).save(os.path.join(OUT_DIR, "icon-512.png"))

    # Maskable — safe zone: keep the mark well inside, full-bleed orange square
    # (no rounding; the launcher applies the mask).
    maskable = _rounded(512, 0.0, ORANGE, draw_mark=False)
    md = ImageDraw.Draw(maskable)
    _draw_bike(md, 256, int(512 * 0.52), (512 / 160.0) * 0.7, WHITE, 6)
    maskable.save(os.path.join(OUT_DIR, "icon-512-maskable.png"))

    # Apple touch icon (180) — Apple adds its own rounding, so use a full square.
    apple = _rounded(180, 0.0, ORANGE)
    apple.save(os.path.join(OUT_DIR, "apple-touch-icon.png"))

    # SVG favicon
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
        '<rect width="64" height="64" rx="14" fill="#f0a030"/>'
        '<g fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round">'
        '<circle cx="20" cy="40" r="11"/><circle cx="44" cy="40" r="11"/>'
        '<path d="M20 40 L30 22 L42 22 M30 22 L44 40 M20 40 L36 40"/>'
        '</g></svg>'
    )
    with open(os.path.join(OUT_DIR, "favicon.svg"), "w") as f:
        f.write(svg)

    print("Wrote icons to", OUT_DIR)
    for n in os.listdir(OUT_DIR):
        print("  ", n)


if __name__ == "__main__":
    main()
