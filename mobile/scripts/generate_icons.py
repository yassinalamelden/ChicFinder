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

from pathlib import Path

from PIL import Image, ImageDraw

ASSETS = Path(__file__).resolve().parent.parent / "assets"

BG = (13, 13, 13, 255)        # colors.bg
ACCENT = (232, 255, 71, 255)  # colors.accent
SIZE = 1024

# Supersampling factor. Drawing large and downscaling gives clean curves without
# pulling in a vector renderer.
SS = 4


def _canvas(transparent: bool) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    mode_bg = (0, 0, 0, 0) if transparent else BG
    img = Image.new("RGBA", (SIZE * SS, SIZE * SS), mode_bg)
    return img, ImageDraw.Draw(img)


def _draw_mark(draw: ImageDraw.ImageDraw, scale: float, color=ACCENT) -> None:
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

    # Hanger. Laid out so the whole group is vertically centred in the frame:
    # the hook's top and the bar sit at roughly equal distances from `centre`.
    hanger_width = span * 0.50
    bar_y = centre + span * 0.18       # bottom bar
    apex_y = centre + span * 0.02      # where the two shoulders meet
    stem_top_y = centre - span * 0.10  # where the vertical stem meets the hook
    hook_r = span * 0.075

    bar_stroke = stroke * 0.95
    w = int(bar_stroke)
    cap = bar_stroke / 2

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

    # Hook: a half circle whose left end meets the top of the stem exactly, so
    # the two read as one continuous line.
    hook_cx = centre + hook_r
    draw.arc(
        [hook_cx - hook_r, stem_top_y - hook_r, hook_cx + hook_r, stem_top_y + hook_r],
        start=180,
        end=360,
        fill=color,
        width=w,
    )
    dot(centre, stem_top_y)
    dot(centre + 2 * hook_r, stem_top_y)


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
    _draw_mark(draw, scale=0.58)
    _save(img, "icon.png", drop_alpha=True)
    _save(img, "favicon.png", size=48, drop_alpha=True)

    # Android adaptive foreground: transparent, and smaller because the system
    # masks the outer third of the layer.
    img, draw = _canvas(transparent=True)
    _draw_mark(draw, scale=0.42)
    _save(img, "adaptive-icon.png")
    _save(img, "android-icon-foreground.png")

    # Splash mark: transparent, drawn against the config's background colour.
    img, draw = _canvas(transparent=True)
    _draw_mark(draw, scale=0.50)
    _save(img, "splash-icon.png")

    print("Done.")


if __name__ == "__main__":
    main()
