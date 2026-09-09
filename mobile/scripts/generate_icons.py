#!/usr/bin/env python3
"""
Generates the app icon set from one design defined in code.

Rerun after any brand change:

    python3 mobile/scripts/generate_icons.py

Outputs into mobile/assets/:
  icon.png                        1024x1024, opaque, no alpha (App Store requirement)
  adaptive-icon.png               1024x1024 Android foreground, transparent, safe-zone aware
  android-icon-foreground.png     same as above, name Expo's Android config expects
  splash-icon.png                 1024x1024 transparent mark for the launch screen
  favicon.png                     48x48 for the web build

The mark is a stylised hanger inside a viewfinder frame: the camera is how you
search, the hanger is what you are searching for.
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

ASSETS = Path(__file__).resolve().parent.parent / "assets"

# Black ground, white mark. A single-colour glyph on near-black reads at every
# size a home screen renders, which a two-tone mark on olive did not: at 60pt
# the amber-on-olive version lost its brackets entirely.
BG = (14, 15, 11, 255)        # near-black, warmed very slightly toward the olive
BONE = (237, 234, 226, 255)   # colors.bg, the mark
INK = (20, 21, 15, 255)       # for the mark on the light splash
SIZE = 1024

# Supersampling factor. Drawing large and downscaling gives clean curves without
# pulling in a vector renderer.
SS = 4


def _canvas(transparent: bool) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    mode_bg = (0, 0, 0, 0) if transparent else BG
    img = Image.new("RGBA", (SIZE * SS, SIZE * SS), mode_bg)
    return img, ImageDraw.Draw(img)


def _draw_mark(draw: ImageDraw.ImageDraw, scale: float, color=BONE) -> None:
    """Draws the viewfinder-plus-hanger mark, centred, at the given scale.

    `scale` is a fraction of the full canvas the mark should occupy.
    """
    full = SIZE * SS
    centre = full / 2
    span = full * scale
    left, top = centre - span / 2, centre - span / 2
    right, bottom = centre + span / 2, centre + span / 2

    stroke = span * 0.055
    corner = span * 0.26

    # Viewfinder brackets: four corners, each two strokes.
    for x_dir, y_dir, x0, y0 in (
        (1, 1, left, top),
        (-1, 1, right, top),
        (1, -1, left, bottom),
        (-1, -1, right, bottom),
    ):
        draw.line(
            [(x0, y0), (x0 + corner * x_dir, y0)], fill=color, width=int(stroke)
        )
        draw.line(
            [(x0, y0), (x0, y0 + corner * y_dir)], fill=color, width=int(stroke)
        )
        # Round the elbow so the two strokes meet cleanly.
        r = stroke / 2
        draw.ellipse([x0 - r, y0 - r, x0 + r, y0 + r], fill=color)

    # ── Hanger ──────────────────────────────────────────────────────────────
    #
    # Proportions are stated as fractions of the frame so the mark holds
    # together at every export size. The group is measured, then shifted so its
    # own bounding box is centred in the frame rather than the apex being
    # centred, which is what made the old mark sit low and read lopsided.
    hanger_width = span * 0.52
    hook_r = span * 0.105

    bar_y = span * 0.17          # the bottom bar
    apex_y = -span * 0.02        # where the two shoulders meet the stem
    stem_top_y = -span * 0.095  # where the stem hands over to the hook

    top = stem_top_y - hook_r
    offset = centre - (top + bar_y) / 2   # centres the hanger's own extent

    bar_y += offset
    apex_y += offset
    stem_top_y += offset

    w = int(stroke * 0.95)
    cap = stroke * 0.95 / 2

    def dot(x: float, y: float) -> None:
        """Round cap, since PIL's line ends are square."""
        draw.ellipse([x - cap, y - cap, x + cap, y + cap], fill=color)

    # Shoulders, from the apex down to each end of the bar.
    for direction in (-1, 1):
        draw.line(
            [(centre, apex_y), (centre + direction * hanger_width / 2, bar_y)],
            fill=color,
            width=w,
        )

    # Bottom bar, with rounded ends.
    draw.line(
        [(centre - hanger_width / 2, bar_y), (centre + hanger_width / 2, bar_y)],
        fill=color,
        width=w,
    )
    dot(centre - hanger_width / 2, bar_y)
    dot(centre + hanger_width / 2, bar_y)
    dot(centre, apex_y)

    # Stem: straight up from the apex to where the hook begins.
    draw.line([(centre, apex_y), (centre, stem_top_y)], fill=color, width=w)

    # Hook. A half circle stopped dead at three o'clock, which the old version
    # drew, reads as a stub rather than a hook. Carrying the arc past the right
    # side and down to about four o'clock gives the tip the inward curl that
    # makes the shape legible as a coat hanger at 40pt.
    hook_cx = centre + hook_r
    box = [
        hook_cx - hook_r,
        stem_top_y - hook_r,
        hook_cx + hook_r,
        stem_top_y + hook_r,
    ]
    draw.arc(box, start=178, end=382, fill=color, width=w)
    dot(centre, stem_top_y)

    # Round the free tip, at the arc's end angle.
    end_rad = math.radians(382)
    dot(hook_cx + hook_r * math.cos(end_rad), stem_top_y + hook_r * math.sin(end_rad))


def _save(img: Image.Image, name: str, size: int = SIZE, drop_alpha: bool = False) -> None:
    out = img.resize((size, size), Image.LANCZOS)
    if drop_alpha:
        # The App Store rejects icons with an alpha channel.
        flat = Image.new("RGB", out.size, BG[:3])
        flat.paste(out, mask=out.split()[3])
        out = flat
    path = ASSETS / name
    out.save(path, "PNG")
    print(f"  {name}  {size}x{size}{'  (opaque)' if drop_alpha else ''}")


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    print(f"Writing icons to {ASSETS}")

    # App Store icon: opaque background, mark at a comfortable margin.
    img, draw = _canvas(transparent=False)
    _draw_mark(draw, scale=0.62)
    _save(img, "icon.png", drop_alpha=True)
    _save(img, "favicon.png", size=48, drop_alpha=True)

    # Android adaptive foreground: transparent, and smaller because the system
    # masks the outer third of the layer.
    img, draw = _canvas(transparent=True)
    _draw_mark(draw, scale=0.42)
    _save(img, "adaptive-icon.png")
    _save(img, "android-icon-foreground.png")

    # Splash marks. Two of them, because the launch screen follows the phone's
    # appearance: an ink mark on the bone background, and a bone mark on the
    # black one. A single asset would be invisible in one of the two.
    img, draw = _canvas(transparent=True)
    _draw_mark(draw, scale=0.50, color=INK)
    _save(img, "splash-icon.png")

    img, draw = _canvas(transparent=True)
    _draw_mark(draw, scale=0.50, color=BONE)
    _save(img, "splash-icon-dark.png")

    print("Done.")


if __name__ == "__main__":
    main()
