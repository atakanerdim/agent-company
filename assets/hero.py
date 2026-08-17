"""Deterministic generative hero for the repository README.

Three wave sources, each emitting concentric rings. Nothing draws the pattern in the
middle — it is interference, the product of sources that never coordinate. One seed
produces the whole image; no stroke is placed by hand.

Run it with no arguments to rewrite hero.svg next to this file. The README shows
hero.webp, rendered from that SVG, because a raster is the one form every markdown
renderer agrees on. The SVG uses only circles, rects and gradients — no filter and no
clip-path, since sanitisers strip those and an unresolvable clip-path reference means
the element is not drawn at all.
"""
import math
import random

W, H = 1600, 480
SEED = 20260817

BG = "#0b0d13"
BLUE = (91, 140, 255)
GREEN = (61, 220, 151)
VIOLET = (138, 122, 255)


def mix(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def hexof(rgb):
    return "#%02x%02x%02x" % rgb


SOURCES = [
    # x, y, colour, ring spacing, count, phase
    (W * 0.22, H * 0.46, BLUE, 6.2, 150, 0.0),
    (W * 0.55, H * 0.70, VIOLET, 12.6, 80, 1.7),
    (W * 0.86, H * 0.34, GREEN, 8.7, 110, 3.1),
]


def build():
    rnd = random.Random(SEED)
    parts = []

    for sx, sy, colour, step, count, phase in SOURCES:
        rings = []
        for i in range(count):
            r = 10 + i * step
            # opacity breathes with radius so the field has bands rather than a flat wash
            wave = (math.sin(i * 0.17 + phase) + 1) / 2
            op = 0.09 + 0.58 * wave * (1 - i / count) ** 0.5
            if op < 0.02:
                continue
            rings.append(
                f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="{r:.1f}" '
                f'stroke-opacity="{op:.3f}"/>'
            )
        parts.append(
            f'<g fill="none" stroke="{hexof(colour)}" stroke-width="0.85">'
            + "".join(rings)
            + "</g>"
        )

    # a scatter of nodes, brighter where two fields cross
    nodes = []
    for _ in range(90):
        x = rnd.uniform(0, W)
        y = rnd.uniform(0, H)
        near = min(math.hypot(x - s[0], y - s[1]) for s in SOURCES)
        if near < 60:
            continue
        colour = hexof(mix(BLUE, GREEN, x / W))
        nodes.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rnd.uniform(0.8, 2.2):.2f}" '
            f'fill="{colour}" fill-opacity="{rnd.uniform(0.25, 0.85):.2f}"/>'
        )

    body = "".join(parts) + "".join(nodes)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Generative interference field">
<defs>
  <linearGradient id="wash" x1="0" y1="0" x2="1" y2="0.4">
    <stop offset="0%" stop-color="#5b8cff" stop-opacity="0.26"/>
    <stop offset="50%" stop-color="#8a7aff" stop-opacity="0.16"/>
    <stop offset="100%" stop-color="#3ddc97" stop-opacity="0.24"/>
  </linearGradient>
  <linearGradient id="fade" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="{BG}" stop-opacity="0.35"/>
    <stop offset="35%" stop-color="{BG}" stop-opacity="0"/>
    <stop offset="70%" stop-color="{BG}" stop-opacity="0"/>
    <stop offset="100%" stop-color="{BG}" stop-opacity="0.5"/>
  </linearGradient>
  <radialGradient id="glowA" cx="50%" cy="50%" r="50%">
    <stop offset="0%" stop-color="#5b8cff" stop-opacity="0.20"/>
    <stop offset="100%" stop-color="#5b8cff" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="glowB" cx="50%" cy="50%" r="50%">
    <stop offset="0%" stop-color="#3ddc97" stop-opacity="0.18"/>
    <stop offset="100%" stop-color="#3ddc97" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="vig" cx="50%" cy="50%" r="78%">
    <stop offset="55%" stop-color="{BG}" stop-opacity="0"/>
    <stop offset="100%" stop-color="{BG}" stop-opacity="0.7"/>
  </radialGradient>
</defs>
<rect width="{W}" height="{H}" fill="{BG}"/>
<rect width="{W}" height="{H}" fill="url(#wash)"/>
<ellipse cx="{W*0.22}" cy="{H*0.46}" rx="520" ry="360" fill="url(#glowA)"/>
<ellipse cx="{W*0.86}" cy="{H*0.34}" rx="520" ry="360" fill="url(#glowB)"/>
{body}
<rect width="{W}" height="{H}" fill="url(#fade)"/>
<rect width="{W}" height="{H}" fill="url(#vig)"/>
</svg>
'''


if __name__ == "__main__":
    import os
    target = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hero.svg")
    open(target, "w", encoding="utf-8").write(build())
    print("assets/hero.svg written")
