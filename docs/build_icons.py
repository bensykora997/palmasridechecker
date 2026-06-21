"""Generate PWA icons for Palmas Ride Engine.

Dev-only — run locally to (re)generate the committed PNGs in static/icons/.
Pillow is NOT a runtime dependency (not in requirements.txt).

    python3 docs/build_icons.py

Produces: icon-192.png, icon-512.png, icon-512-maskable.png,
apple-touch-icon.png (180px).  favicon.svg is maintained separately.

Design: accent-orange rounded field with a white road-bike silhouette.
All geometry is derived proportionally from the wheel-hub positions so the
same drawing looks correct at every size.
"""

import os
from PIL import Image, ImageDraw

ORANGE = (240, 160, 48, 255)
WHITE  = (255, 255, 255, 255)

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "static", "icons")


def _pt(lh, wb, r, fx, fy):
    """Pixel coord offset from rear hub by (fx*wb, fy*r)."""
    return (round(lh[0] + fx * wb), round(lh[1] + fy * r))


def _draw_bike(d, cx, cy, scale, color, lw_base):
    """Draw a proper road-bicycle silhouette centred on (cx, cy).

    All geometry is expressed as multiples of the wheel radius (r) and the
    wheelbase (wb), derived from `scale`.  Proportions match a real road bike
    (73-deg seat tube, 72-deg head tube, diamond frame).
    """
    lw = max(2, round(lw_base * scale))
    hw = max(1, round(lw_base * scale * 0.75))

    r   = round(28 * scale)
    sep = round(45 * scale)
    wb  = 2 * sep

    lh = (cx - sep, cy)   # rear hub
    rh = (cx + sep, cy)   # front hub

    # Frame joints — offsets from rear hub as fractions of wheelbase / radius
    bb   = _pt(lh, wb, r,  0.45,  0.00)   # bottom bracket
    st_t = _pt(lh, wb, r,  0.32, -2.00)   # seat tube top
    hd_t = _pt(lh, wb, r,  0.89, -2.00)   # head tube top
    hd_b = _pt(lh, wb, r,  0.92, -1.20)   # head tube bottom

    sp_t  = _pt(lh, wb, r,  0.25, -2.90)  # seatpost top
    sdl_l = _pt(lh, wb, r,  0.11, -3.00)  # saddle left
    sdl_r = _pt(lh, wb, r,  0.42, -3.00)  # saddle right

    stm_t = _pt(lh, wb, r,  0.83, -3.00)  # stem top
    bar_l = _pt(lh, wb, r,  0.72, -3.00)  # handlebar left
    bar_r = _pt(lh, wb, r,  0.97, -3.00)  # handlebar right
    drop  = _pt(lh, wb, r,  0.97, -2.30)  # right drop end

    # Wheels
    d.ellipse([lh[0]-r, lh[1]-r, lh[0]+r, lh[1]+r], outline=color, width=lw)
    d.ellipse([rh[0]-r, rh[1]-r, rh[0]+r, rh[1]+r], outline=color, width=lw)

    # Diamond frame
    d.line([lh, bb],     fill=color, width=lw)   # chain stay
    d.line([lh, st_t],   fill=color, width=lw)   # seat stay
    d.line([st_t, bb],   fill=color, width=lw)   # seat tube
    d.line([st_t, hd_t], fill=color, width=lw)   # top tube
    d.line([bb, hd_b],   fill=color, width=lw)   # down tube
    d.line([hd_t, hd_b], fill=color, width=lw)   # head tube
    d.line([hd_b, rh],   fill=color, width=lw)   # fork

    # Seatpost + saddle
    d.line([st_t, sp_t],   fill=color, width=hw)
    d.line([sdl_l, sdl_r], fill=color, width=hw)

    # Stem + drop handlebars
    d.line([hd_t, stm_t],  fill=color, width=hw)
    d.line([bar_l, bar_r], fill=color, width=hw)
    d.line([bar_r, drop],  fill=color, width=hw)


def _make_icon(size, radius_frac, bg, scale_frac=1.0, pad_frac=0.0):
    """Render one icon PNG.

    cy is offset below centre so the bike is vertically balanced:
      bike top    ~ cy - 3.0*r  (saddle/handlebar)
      bike bottom ~ cy + 1.0*r  (wheel bottom)
      => centre of visual mass at cy - r, so cy = size/2 + r centres it.
    """
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d   = ImageDraw.Draw(img)

    pad    = int(size * pad_frac)
    radius = int(size * radius_frac)
    d.rounded_rectangle([pad, pad, size - 1 - pad, size - 1 - pad],
                        radius=radius, fill=bg)

    scale = (size / 160.0) * scale_frac
    r_px  = round(28 * scale)
    cx    = size // 2
    cy    = size // 2 + r_px

    _draw_bike(d, cx, cy, scale, WHITE, 6)
    return img


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    _make_icon(192, 0.22, ORANGE).save(os.path.join(OUT_DIR, "icon-192.png"))
    _make_icon(512, 0.22, ORANGE).save(os.path.join(OUT_DIR, "icon-512.png"))

    # Maskable: full-bleed square, bike scaled to stay in the safe zone
    _make_icon(512, 0.0, ORANGE, scale_frac=0.68).save(
        os.path.join(OUT_DIR, "icon-512-maskable.png")
    )

    # Apple adds its own rounding, so use a full square
    _make_icon(180, 0.0, ORANGE).save(os.path.join(OUT_DIR, "apple-touch-icon.png"))

    print("Wrote icons to", OUT_DIR)
    for n in sorted(os.listdir(OUT_DIR)):
        path = os.path.join(OUT_DIR, n)
        print(f"  {n:30s}  {os.path.getsize(path):,} bytes")


if __name__ == "__main__":
    main()
