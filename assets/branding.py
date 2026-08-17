"""Generates the raster icons and the social card, so they stay in step with the hero.

Three artefacts, one geometry:

* ``site/icon-{32,180,512}.png`` — raster fallbacks for the SVG favicon. The mark is a
  halfway line, a centre circle and the centre spot: a pitch, still legible at 16 pixels.
* ``site/og.png`` — the 1200x630 card a link unfurls into on chat and social platforms.
* ``assets/social-card.png`` — the 1280x640 preview GitHub shows for the repository.

Both cards reuse ``assets/hero.py`` rather than redrawing anything, so the picture a
visitor meets is the same picture wherever they meet it.

Requires Pillow and numpy. Not run by CI; the committed files are the artefacts.

    python assets/branding.py
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import hero

ROOT = Path(__file__).resolve().parents[1]
BACKGROUND = (15, 17, 23)
ACCENT = (91, 140, 255)
ACCENT_2 = (61, 220, 151)
TEXT = (232, 234, 240)
MUTED = (154, 163, 181)

FONT_CANDIDATES = {
    "bold": ("/usr/share/fonts/truetype/lato/Lato-Bold.ttf",
             "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
             "C:/Windows/Fonts/segoeuib.ttf"),
    "regular": ("/usr/share/fonts/truetype/lato/Lato-Regular.ttf",
                "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "C:/Windows/Fonts/segoeui.ttf"),
}


def font(weight, size):
    for path in FONT_CANDIDATES[weight]:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def icon(size):
    """The favicon mark, drawn at 8x and downsampled so the strokes stay clean."""
    scale = 8
    edge = size * scale
    image = Image.new("RGB", (edge, edge), BACKGROUND)
    draw = ImageDraw.Draw(image)
    centre, stroke = edge / 2, max(1, round(edge * 0.0625))
    draw.line([centre, edge * 0.11, centre, edge * 0.89], fill=ACCENT, width=stroke)
    radius = edge * 0.231
    draw.ellipse([centre - radius, centre - radius, centre + radius, centre + radius],
                 outline=ACCENT, width=stroke)
    spot = edge * 0.0875
    draw.ellipse([centre - spot, centre - spot, centre + spot, centre + spot], fill=ACCENT_2)
    return image.resize((size, size), Image.LANCZOS)


def card(width, height, title, subtitle, footer):
    """Hero art across the top, wordmark below it."""
    image = Image.new("RGB", (width, height), BACKGROUND)
    art_height = round(height * 0.52)
    art = hero.build().resize((width, round(width * hero.HEIGHT / hero.WIDTH)), Image.LANCZOS)
    image.paste(art.crop((0, 0, width, min(art_height, art.height))), (0, 0))

    draw = ImageDraw.Draw(image)
    draw.line([0, art_height, width, art_height], fill=(38, 43, 56), width=2)

    pad = round(width * 0.058)
    y = art_height + round(height * 0.10)
    draw.text((pad, y), title, font=font("bold", round(height * 0.098)), fill=TEXT)
    y += round(height * 0.135)
    draw.text((pad, y), subtitle, font=font("regular", round(height * 0.052)), fill=MUTED)
    y += round(height * 0.085)
    draw.text((pad, y), footer, font=font("regular", round(height * 0.042)), fill=ACCENT)
    return image


def main():
    site = ROOT / "site"
    for size in (32, 180, 512):
        icon(size).save(site / f"icon-{size}.png", optimize=True)

    title = "Agent Company"
    subtitle = "Twelve AI agents run this company. Nobody approves their work."
    card(1200, 630, title, subtitle, "atakanerdim.github.io/agent-company").save(
        site / "og.png", optimize=True)
    card(1280, 640, title, subtitle, "Football predictions, shipped by pull request").save(
        ROOT / "assets/social-card.png", optimize=True)

    written = ["site/icon-32.png", "site/icon-180.png", "site/icon-512.png",
               "site/og.png", "assets/social-card.png"]
    for name in written:
        print(f"{name} ({(ROOT / name).stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
