"""Deterministic hero image for the README: the company, drawn on a pitch.

Nothing here is decoration for its own sake. Every mark is read from the company:

* the twelve nodes are the twelve agents in ``company/roster.json``, placed in the
  formation their role implies — the CEO where a keeper stands, the process agents
  in defence, the desk in midfield, the site and culture agents wide, the three
  predictor personas up front;
* the blue web is who talks to whom — the hallway, the design feedback round, the
  review the pessimist runs over the set;
* the three amber arcs are the three personas predicting the same fixture and
  disagreeing about it, which is the point of running three of them.

The output is a raster. An earlier version of this file emitted SVG, which markdown
renderers sanitise: a stripped ``filter`` or ``clipPath`` definition leaves an
unresolvable reference, and an unresolvable reference means the element is not drawn
at all. A raster is the one form every renderer agrees on.

Requires Pillow and numpy. It is never run by CI — the committed WebP is the artefact;
this file is the record of how it was made.

    python assets/hero.py
"""
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
WIDTH, HEIGHT, SUPERSAMPLE = 1600, 480, 2
BACKGROUND = np.array([10, 12, 18], np.float32)

BLUE = (91, 140, 255)
VIOLET = (138, 122, 255)
GREEN = (61, 220, 151)
AMBER = (240, 179, 92)

# A pitch is 105x68 metres. The banner is far wider than it is tall, so the frame
# holds the full length and crops the middle band of the width — the way a broadcast
# graphic does. Everything drawn stays inside the visible band.
PITCH_LENGTH, PITCH_WIDTH, MARGIN = 105.0, 68.0, 2.5
UNIT = WIDTH * SUPERSAMPLE / (PITCH_LENGTH + 2 * MARGIN)

ROLE_COLOUR = {
    "management": BLUE, "process": BLUE,
    "predictions": VIOLET, "quality": VIOLET,
    "culture": GREEN, "site": GREEN,
    "predictor": AMBER,
}

FORMATION = {
    "ceo": (5, 34),
    "scrum": (19, 24), "process": (19, 44),
    "analyst": (32, 28), "evaluator": (32, 40),
    "designer": (45, 24), "gossip": (45, 34), "webdev": (45, 44),
    "pessimist": (60, 34),
    "statistician": (78, 24), "coolhead": (78, 34), "romantic": (78, 44),
}

PASSES = [
    ("ceo", "scrum"), ("ceo", "process"),
    ("scrum", "analyst"), ("process", "evaluator"), ("analyst", "evaluator"),
    ("analyst", "gossip"), ("evaluator", "gossip"),
    ("designer", "gossip"), ("webdev", "gossip"), ("designer", "webdev"),
    ("gossip", "pessimist"), ("analyst", "pessimist"), ("evaluator", "pessimist"),
    ("pessimist", "statistician"), ("pessimist", "coolhead"), ("pessimist", "romantic"),
]

# Where each persona puts the ball: same fixture, three different answers.
SHOTS = [("statistician", 31.6, -3.6), ("coolhead", 34.0, -1.6), ("romantic", 36.4, 3.8)]


def px(metres):
    return (metres + MARGIN) * UNIT


def py(metres):
    return (metres - PITCH_WIDTH / 2) * UNIT + HEIGHT * SUPERSAMPLE / 2


def shade(colour, factor):
    return tuple(int(max(0, min(255, channel * factor))) for channel in colour)


class Light:
    """Emissive strokes on separate blur tiers, tone-mapped once at the end.

    Stacking blurred layers additively drives every bright pixel to white and the
    colour dies with it. Accumulating in float and mapping through 1-exp(-x) instead
    lets the highlights saturate softly while the hue survives.
    """

    def __init__(self):
        self.tiers = {}

    def tier(self, blur):
        if blur not in self.tiers:
            image = Image.new("RGB", (WIDTH * SUPERSAMPLE, HEIGHT * SUPERSAMPLE), (0, 0, 0))
            self.tiers[blur] = (image, ImageDraw.Draw(image))
        return self.tiers[blur][1]

    def render(self, base, exposure=1.45):
        total = np.zeros((HEIGHT * SUPERSAMPLE, WIDTH * SUPERSAMPLE, 3), np.float32)
        for blur, (image, _) in sorted(self.tiers.items()):
            if blur:
                image = image.filter(ImageFilter.GaussianBlur(blur * SUPERSAMPLE))
            total += np.asarray(image, np.float32)
        tone = 1.0 - np.exp(-(total / 255.0) * exposure)
        under = np.asarray(base, np.float32) / 255.0
        blended = np.clip(under + tone * (1.0 - under), 0, 1)
        return Image.fromarray((blended * 255).astype(np.uint8)).resize(
            (WIDTH, HEIGHT), Image.LANCZOS)


def vignette(image, strength=0.45):
    width, height = image.size
    rows, columns = np.mgrid[0:height, 0:width]
    dx = (columns - width / 2) / (width / 2)
    dy = (rows - height / 2) / (height / 2)
    radius = np.sqrt((dx * 0.8) ** 2 + dy ** 2)
    mask = np.clip(1 - strength * np.clip((radius - 0.45) / 0.85, 0, 1) ** 1.5, 0, 1)[..., None]
    faded = np.asarray(image, np.float32) * mask + BACKGROUND[None, None, :] * (1 - mask)
    return Image.fromarray(faded.astype(np.uint8))


def draw_pitch():
    image = Image.new("RGB", (WIDTH * SUPERSAMPLE, HEIGHT * SUPERSAMPLE),
                      tuple(BACKGROUND.astype(int)))
    draw = ImageDraw.Draw(image)
    tall = HEIGHT * SUPERSAMPLE

    for index in range(9):  # mown stripes
        if index % 2 == 0:
            draw.rectangle([px(index * PITCH_LENGTH / 9), 0,
                            px((index + 1) * PITCH_LENGTH / 9), tall], fill=(16, 20, 29))

    line, weight = (56, 70, 96), int(2.2 * SUPERSAMPLE)
    middle = PITCH_WIDTH / 2
    draw.line([px(52.5), 0, px(52.5), tall], fill=line, width=weight)
    circle = 9.15 * UNIT
    draw.ellipse([px(52.5) - circle, py(middle) - circle,
                  px(52.5) + circle, py(middle) + circle], outline=line, width=weight)
    draw.ellipse([px(52.5) - 3 * SUPERSAMPLE, py(middle) - 3 * SUPERSAMPLE,
                  px(52.5) + 3 * SUPERSAMPLE, py(middle) + 3 * SUPERSAMPLE], fill=line)

    for goal_line, direction in ((0.0, 1), (PITCH_LENGTH, -1)):
        draw.line([px(goal_line), 0, px(goal_line), tall], fill=line, width=weight)
        box = sorted([px(goal_line), px(goal_line + direction * 16.5)])
        draw.rectangle([box[0], py(13.85), box[1], py(54.15)], outline=line, width=weight)
        area = sorted([px(goal_line), px(goal_line + direction * 5.5)])
        draw.rectangle([area[0], py(24.85), area[1], py(43.15)], outline=line, width=weight)
        spot = px(goal_line + direction * 11)
        radius = 2.2 * SUPERSAMPLE
        draw.ellipse([spot - radius, py(middle) - radius,
                      spot + radius, py(middle) + radius], fill=line)
    return image


def build():
    roster = json.loads((ROOT / "company/roster.json").read_text(encoding="utf-8"))
    base = draw_pitch()
    light = Light()
    core, soft, halo = light.tier(0), light.tier(6), light.tier(26)

    for left, right in PASSES:
        start, end = FORMATION[left], FORMATION[right]
        points = [(px(start[0]), py(start[1])), (px(end[0]), py(end[1]))]
        for layer, factor, width in ((halo, .16, 5), (soft, .22, 2.2), (core, .42, 1.8)):
            layer.line(points, fill=shade(BLUE, factor), width=int(width * SUPERSAMPLE))

    for persona, target, bend in SHOTS:
        origin_x, origin_y = FORMATION[persona]
        points = []
        for step in range(41):
            t = step / 40
            x = origin_x + (PITCH_LENGTH - 0.4 - origin_x) * t
            y = origin_y + (target - origin_y) * t + math.sin(math.pi * t) * bend
            points.append((px(x), py(y)))
        for layer, factor, width in ((halo, .30, 6), (soft, .40, 2.4), (core, .85, 2.0)):
            layer.line(points, fill=shade(AMBER, factor),
                       width=int(width * SUPERSAMPLE), joint="curve")

    for layer, factor, width in ((halo, .5, 9), (soft, .6, 4), (core, 1.0, 3.4)):
        layer.line([px(PITCH_LENGTH), py(30.34), px(PITCH_LENGTH), py(37.66)],
                   fill=shade(AMBER, factor), width=int(width * SUPERSAMPLE))

    for agent in roster:
        x, y = FORMATION[agent["id"]]
        colour = ROLE_COLOUR[agent["rol"]]
        for layer, factor, radius in ((halo, .42, 17), (soft, .55, 9), (core, 1.0, 7.2)):
            layer.ellipse([px(x) - radius * SUPERSAMPLE, py(y) - radius * SUPERSAMPLE,
                           px(x) + radius * SUPERSAMPLE, py(y) + radius * SUPERSAMPLE],
                          fill=shade(colour, factor))

    return vignette(light.render(base))


if __name__ == "__main__":
    target = ROOT / "assets/hero.webp"
    build().save(target, "WEBP", quality=90, method=6)
    print(f"{target.relative_to(ROOT)} written ({target.stat().st_size // 1024} KB)")
