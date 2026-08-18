"""Contact sheet of the twelve colleagues, for the README.

The portraits themselves are drawn by ``avatars.py`` and published as SVG at deploy
time. This file only arranges them into one raster so that somebody reading the
repository on GitHub sees the office without having to open the site.

Like ``hero.py`` it is never run by CI — the committed WebP is the artefact and this
file is the record of how it was made. Regenerate after changing the wardrobe:

    python assets/cast.py

Requires Pillow and cairosvg, neither of which the company itself depends on.
"""
import io
import json
import sys
from pathlib import Path

import cairosvg
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "assets"))
import avatars  # noqa: E402

BG, TEXT, MUTED = "#0f1117", "#e8eaf0", "#9aa3b5"
TILE, COLS, GAP, PAD, CAPTION = 150, 6, 16, 22, 40


def _font(size, bold=False):
    for name in (("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"),):
        for base in ("/usr/share/fonts/truetype/dejavu/", "/usr/share/fonts/TTF/", ""):
            try:
                return ImageFont.truetype(base + name, size)
            except OSError:
                continue
    return ImageFont.load_default()


def _fit(draw, text, font):
    """Trim a caption to its tile. A job title that runs into the neighbour reads
    as one person having two jobs."""
    if draw.textlength(text, font=font) <= TILE:
        return text
    while text and draw.textlength(text + "…", font=font) > TILE:
        text = text[:-1]
    return text.rstrip(" ,") + "…"


def build():
    looks = avatars.load_appearance(ROOT)
    people = {p["id"]: p for p in json.loads(
        (ROOT / "company/agents/identity.json").read_text(encoding="utf-8"))}
    order = [r["id"] for r in json.loads(
        (ROOT / "company/roster.json").read_text(encoding="utf-8"))]

    rows = (len(order) + COLS - 1) // COLS
    width = PAD * 2 + COLS * TILE + (COLS - 1) * GAP
    height = PAD * 2 + rows * (TILE + CAPTION) + (rows - 1) * GAP
    sheet = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(sheet)
    name_font, role_font = _font(13, bold=True), _font(12)

    for index, agent_id in enumerate(order):
        png = cairosvg.svg2png(bytestring=avatars.render(looks[agent_id]).encode(),
                               output_width=TILE * 2, output_height=TILE * 2)
        tile = Image.open(io.BytesIO(png)).convert("RGB").resize(
            (TILE, TILE), Image.LANCZOS)
        column, row = index % COLS, index // COLS
        x = PAD + column * (TILE + GAP)
        y = PAD + row * (TILE + CAPTION + GAP)
        sheet.paste(tile, (x, y))
        person = people[agent_id]
        draw.text((x, y + TILE + 7), _fit(draw, person["person"], name_font),
                  font=name_font, fill=TEXT)
        draw.text((x, y + TILE + 23), _fit(draw, person["title"], role_font),
                  font=role_font, fill=MUTED)

    return sheet


if __name__ == "__main__":
    out = ROOT / "assets/cast.webp"
    build().save(out, "WEBP", quality=90, method=6)
    print(f"{out.name}: {out.stat().st_size // 1024} KB")
