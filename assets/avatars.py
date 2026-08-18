"""Portraits for the twelve colleagues, drawn from a fixed parts library.

The point of this file is the boundary it draws.

The *skeleton* is fixed and lives here: everyone has one head, two eyes, one nose,
a neck and a pair of shoulders, at coordinates nobody may move. The *wardrobe* is
open and lives in ``company/agents/appearance.json``: hair, colour, expression,
glasses, clothing, accessory, prop. The Designer may edit that file through the
normal pull-request ritual, so a colleague can change their shirt colour, put on
glasses, grow a beard or dye their hair — but cannot grow a second nose, because
there is no slot for one and ``tests/test_appearance.py`` rejects any value that
is not in ``SCHEMA`` below.

So ``SCHEMA`` is the contract. It is the single source of truth for what an agent
is allowed to look like: the renderer reads it, the test enforces it, and the
Designer's brief points at it.

Output is plain SVG using only universal primitives — no filter, no clipPath, no
external reference. Deterministic, offline, and cheap enough to regenerate on every
deploy from ``site/build.py``.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# --------------------------------------------------------------------------
# Palettes. Wardrobe values are names, never raw colours, so a stray hex string
# in the appearance file cannot smuggle in something off-brand.
# --------------------------------------------------------------------------

SKIN = {
    "porcelain": ("#f0d0b8", "#d8b096"),
    "sand":      ("#e6bb97", "#cb9b76"),
    "honey":     ("#d3a06f", "#b5814f"),
    "amber":     ("#b97f4e", "#9a6337"),
    "chestnut":  ("#8f5a33", "#734425"),
    "espresso":  ("#5f3b22", "#4a2c17"),
}

HAIR_COLOUR = {
    "ink":      "#15171f",
    "espresso": "#3a2418",
    "chestnut": "#5d3a22",
    "auburn":   "#8a3c22",
    "sand":     "#b98d4e",
    "silver":   "#b9bec9",
    "cobalt":   "#2f5bd0",
    "plum":     "#6d2f6a",
}

CLOTH = {
    "slate":  "#3a4356",
    "ink":    "#1c202b",
    "indigo": "#3b3f8f",
    "cobalt": "#2f5bd0",
    "teal":   "#166e6a",
    "mint":   "#3ddc97",
    "moss":   "#3f6b3a",
    "amber":  "#c8862b",
    "rust":   "#a2452c",
    "plum":   "#6d2f6a",
    "rose":   "#c05a72",
    "bone":   "#d8d2c6",
}

BACKDROP = {
    "slate":  "#232a38",
    "ink":    "#1a1d26",
    "indigo": "#252a4a",
    "teal":   "#16323a",
    "moss":   "#22321f",
    "plum":   "#2e1f36",
    "rust":   "#33221c",
    "amber":  "#33291a",
}

# --------------------------------------------------------------------------
# The contract. Every slot, every value an agent may choose.
# --------------------------------------------------------------------------

SCHEMA = {
    "skin":        tuple(SKIN),
    "hair":        ("bald", "crop", "bob", "long", "curls", "afro",
                    "braids", "bun", "topknot", "wave", "side_part", "ponytail"),
    "hair_colour": tuple(HAIR_COLOUR),
    "brows":       ("flat", "raised", "worried", "arched", "angry"),
    "eyes":        ("open", "narrow", "wide", "sharp", "tired", "side"),
    "mouth":       ("neutral", "smile", "smirk", "frown", "flat", "open", "whisper"),
    "facial_hair": ("none", "stubble", "moustache", "beard", "goatee"),
    "glasses":     ("none", "round", "square", "halfmoon"),
    "top":         ("tee", "shirt", "blazer", "hoodie", "turtleneck", "cardigan", "polo"),
    "top_colour":  tuple(CLOTH),
    "accent":      ("none", "tie", "scarf", "lanyard", "headphones",
                    "earrings", "pin", "necklace"),
    "accent_colour": tuple(CLOTH),
    "prop":        ("none", "mug", "notepad", "phone", "pencil", "whistle", "clipboard"),
    # There is no gesture slot. A cupped "whispering" hand read as a second ear,
    # then as a paper fan; a hand resting under the chin read as a second chin.
    # At this size a body part that is not on the skeleton does not survive, so
    # character is carried by gaze, mouth, hair, clothing and the prop instead.
    "backdrop":    tuple(BACKDROP),
}

# Head geometry. Fixed. Not a wardrobe slot, and deliberately not configurable.
CX, CY, RX, RY = 60, 50, 24, 27
EYE_Y, EYE_L, EYE_R = 52, 51, 69
BROW_Y = 41
MOUTH_Y = 67


def _e(tag, **kw):
    attrs = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in kw.items())
    return f"<{tag} {attrs}/>"


def _lighten(hex_colour, amount=0.34):
    r, g, b = (int(hex_colour[i:i + 2], 16) for i in (1, 3, 5))
    mix = lambda v: round(v + (255 - v) * amount)
    return f"#{mix(r):02x}{mix(g):02x}{mix(b):02x}"


# --------------------------------------------------------------------------
# Hair. Two layers: mass behind the head, fringe and side pieces in front.
# --------------------------------------------------------------------------

def _hair_back(style, c):
    if style == "bald":
        return ""
    if style == "afro":
        return _e("circle", cx=CX, cy=42, r=32, fill=c)
    if style == "curls":
        blobs = "".join(_e("circle", cx=x, cy=y, r=r, fill=c) for x, y, r in
                        [(38, 40, 11), (50, 27, 12), (64, 24, 13), (78, 33, 12), (85, 46, 10)])
        return _e("ellipse", cx=CX, cy=44, rx=27, ry=27, fill=c) + blobs
    if style == "bob":
        return (_e("ellipse", cx=CX, cy=45, rx=30, ry=29, fill=c) +
                _e("rect", x=30, y=45, width=60, height=28, rx=12, fill=c))
    if style == "long":
        return (_e("ellipse", cx=CX, cy=45, rx=30, ry=29, fill=c) +
                _e("rect", x=28, y=45, width=64, height=54, rx=16, fill=c))
    if style == "braids":
        braid = "".join(_e("circle", cx=x, cy=y, r=6.5, fill=c)
                        for x in (30, 90) for y in (60, 72, 84))
        return _e("ellipse", cx=CX, cy=44, rx=28, ry=27, fill=c) + braid
    if style == "bun":
        return (_e("ellipse", cx=CX, cy=45, rx=27, ry=27, fill=c) +
                _e("circle", cx=CX, cy=17, r=11, fill=c))
    if style == "topknot":
        # Swept back and tied. The knot on top is what keeps it from reading as a hat.
        return (_e("ellipse", cx=CX, cy=45, rx=26, ry=26, fill=c) +
                _e("rect", x=56, y=18, width=8, height=12, rx=4, fill=c) +
                _e("ellipse", cx=CX, cy=16, rx=9, ry=8, fill=c))
    if style == "ponytail":
        return (_e("ellipse", cx=CX, cy=45, rx=27, ry=27, fill=c) +
                _e("ellipse", cx=90, cy=64, rx=9, ry=18, fill=c) +
                _e("rect", x=82, y=44, width=10, height=7, rx=3, fill=c))
    # crop, wave, side_part
    return _e("ellipse", cx=CX, cy=44, rx=26, ry=26, fill=c)


def _shine(style, c):
    """Two strands catching the light.

    Without them a solid mass of colour on top of a head reads as a hat rather than
    as hair — which is only obvious once somebody dyes their hair a colour hair is
    not normally, and the portrait suddenly acquires a beanie.
    """
    if style == "bald":
        return ""
    return _e("path", d="M45 33 Q53 26 63 26 M52 39 Q61 31 73 33",
              fill="none", stroke=_lighten(c), stroke_width=2,
              stroke_linecap="round", stroke_opacity="0.55")


def _hair_front(style, c):
    if style == "bald":
        return _e("path", d="M44 34 Q60 25 76 34", fill="none",
                  stroke="#ffffff", stroke_opacity="0.10", stroke_width=3)
    # topknot deliberately shares the default fringe below: a low, thick band across
    # the forehead reads as the brim of a hat, and the knot alone should carry the style.
    if style == "side_part":
        return _e("path", d="M36 42 Q44 24 62 24 Q84 24 84 44 Q76 32 58 33 Q44 34 36 42 Z", fill=c)
    if style == "wave":
        return _e("path", d="M36 43 Q42 30 52 34 Q60 24 70 33 Q80 29 84 44 "
                            "Q78 34 60 35 Q44 36 36 43 Z", fill=c)
    if style in ("bob", "long"):
        return (_e("path", d="M34 44 Q40 22 60 22 Q80 22 86 44 Q78 33 60 33 Q42 33 34 44 Z", fill=c) +
                _e("rect", x=30, y=40, width=11, height=32, rx=5, fill=c) +
                _e("rect", x=79, y=40, width=11, height=32, rx=5, fill=c))
    if style in ("curls", "afro"):
        return _e("path", d="M36 44 Q46 30 60 30 Q74 30 84 44 Q74 36 60 36 Q46 36 36 44 Z", fill=c)
    # crop, braids, bun, ponytail
    return _e("path", d="M36 43 Q42 26 60 26 Q78 26 84 43 Q76 32 60 32 Q44 32 36 43 Z", fill=c)


# --------------------------------------------------------------------------
# Face
# --------------------------------------------------------------------------

def _brows(style, c):
    pairs = {
        "flat":    ("M43 41 L57 41", "M63 41 L77 41"),
        "raised":  ("M43 40 Q50 35 57 39", "M63 39 Q70 35 77 40"),
        "worried": ("M43 38 Q50 43 57 42", "M63 42 Q70 43 77 38"),
        "arched":  ("M43 42 Q50 34 57 41", "M63 41 Q70 34 77 42"),
        "angry":   ("M43 37 L57 42", "M63 42 L77 37"),
    }[style]
    return "".join(_e("path", d=d, fill="none", stroke=c,
                      stroke_width=3, stroke_linecap="round") for d in pairs)


def _one_eye(style, x):
    white, iris = "#f6f7fb", "#2b3242"
    if style == "narrow":
        # A squint, not a closed eye: the pupil has to stay visible under the lid.
        return (_e("ellipse", cx=x, cy=EYE_Y + 1, rx=6.2, ry=2.8, fill=white) +
                _e("circle", cx=x, cy=EYE_Y + 1, r=2.4, fill=iris) +
                _e("path", d=f"M{x-6.6} {EYE_Y-1} Q{x} {EYE_Y-4.5} {x+6.6} {EYE_Y-1}",
                   fill="none", stroke=iris, stroke_width=2.6, stroke_linecap="round"))
    if style == "tired":
        return (_e("ellipse", cx=x, cy=EYE_Y + 1, rx=6, ry=3.4, fill=white) +
                _e("circle", cx=x, cy=EYE_Y + 1, r=2.6, fill=iris) +
                _e("path", d=f"M{x-6.4} {EYE_Y} Q{x} {EYE_Y-3} {x+6.4} {EYE_Y}",
                   fill="none", stroke=iris, stroke_width=2.4, stroke_linecap="round"))
    if style == "sharp":
        return (_e("path", d=f"M{x-6.5} {EYE_Y+1} Q{x} {EYE_Y-6} {x+6.5} {EYE_Y+1} "
                             f"Q{x} {EYE_Y+4} {x-6.5} {EYE_Y+1} Z", fill=white) +
                _e("circle", cx=x, cy=EYE_Y, r=2.7, fill=iris))
    if style == "wide":
        return (_e("ellipse", cx=x, cy=EYE_Y, rx=6.6, ry=6, fill=white) +
                _e("circle", cx=x, cy=EYE_Y, r=3.1, fill=iris) +
                _e("circle", cx=x + 1.4, cy=EYE_Y - 1.8, r=1.1, fill="#ffffff"))
    if style == "side":
        # Looking off to one side, which is most of what the office correspondent does.
        return (_e("ellipse", cx=x, cy=EYE_Y, rx=6.4, ry=4.6, fill=white) +
                _e("circle", cx=x + 3.1, cy=EYE_Y, r=2.7, fill=iris))
    return (_e("ellipse", cx=x, cy=EYE_Y, rx=6.2, ry=4.6, fill=white) +
            _e("circle", cx=x, cy=EYE_Y, r=2.8, fill=iris))


def _mouth(style, c, lip):
    if style == "smile":
        return _e("path", d=f"M52 {MOUTH_Y-1} Q60 {MOUTH_Y+7} 68 {MOUTH_Y-1}",
                  fill="none", stroke=lip, stroke_width=3, stroke_linecap="round")
    if style == "smirk":
        return _e("path", d=f"M52 {MOUTH_Y+2} Q60 {MOUTH_Y+5} 69 {MOUTH_Y-3}",
                  fill="none", stroke=lip, stroke_width=3, stroke_linecap="round")
    if style == "frown":
        return _e("path", d=f"M52 {MOUTH_Y+4} Q60 {MOUTH_Y-3} 68 {MOUTH_Y+4}",
                  fill="none", stroke=lip, stroke_width=3, stroke_linecap="round")
    if style == "flat":
        return _e("path", d=f"M53 {MOUTH_Y+1} L67 {MOUTH_Y+1}",
                  fill="none", stroke=lip, stroke_width=2.6, stroke_linecap="round")
    if style == "open":
        return (_e("ellipse", cx=60, cy=MOUTH_Y + 1, rx=5.5, ry=4.4, fill="#5a2530") +
                _e("path", d=f"M55 {MOUTH_Y-1} Q60 {MOUTH_Y+1} 65 {MOUTH_Y-1}",
                   fill="none", stroke="#ffffff", stroke_width=1.6))
    if style == "whisper":
        # Lips pursed round, mid-sentence, about somebody.
        return (_e("ellipse", cx=61, cy=MOUTH_Y + 1, rx=3.6, ry=4.2, fill="#5a2530") +
                _e("ellipse", cx=61, cy=MOUTH_Y + 1, rx=3.6, ry=4.2, fill="none",
                   stroke=lip, stroke_width=1.8))
    return _e("path", d=f"M53 {MOUTH_Y+1} Q60 {MOUTH_Y+3} 67 {MOUTH_Y+1}",
              fill="none", stroke=lip, stroke_width=2.8, stroke_linecap="round")


def _facial_hair(style, c):
    if style == "none":
        return ""
    if style == "stubble":
        return _e("path", d="M39 58 Q40 79 60 81 Q80 79 81 58 Q78 72 60 73 Q42 72 39 58 Z",
                  fill=c, fill_opacity="0.30")
    if style == "moustache":
        return _e("path", d=f"M51 {MOUTH_Y-5} Q60 {MOUTH_Y-9} 69 {MOUTH_Y-5} "
                            f"Q60 {MOUTH_Y-1} 51 {MOUTH_Y-5} Z", fill=c)
    if style == "goatee":
        # Moustache and chin tuft, with clear daylight between them and the mouth.
        return (_e("path", d=f"M50 {MOUTH_Y-6} Q60 {MOUTH_Y-11} 70 {MOUTH_Y-6} "
                             f"Q60 {MOUTH_Y-2} 50 {MOUTH_Y-6} Z", fill=c) +
                _e("path", d=f"M54 {MOUTH_Y+7} Q60 {MOUTH_Y+4} 66 {MOUTH_Y+7} "
                             f"Q65 {MOUTH_Y+16} 60 {MOUTH_Y+17} "
                             f"Q55 {MOUTH_Y+16} 54 {MOUTH_Y+7} Z", fill=c))
    return (_e("path", d="M38 54 Q38 79 60 85 Q82 79 82 54 Q79 69 71 71 "
                         "Q66 76 60 76 Q54 76 49 71 Q41 69 38 54 Z", fill=c) +
            _e("path", d=f"M50 {MOUTH_Y-6} Q60 {MOUTH_Y-11} 70 {MOUTH_Y-6} "
                        f"Q60 {MOUTH_Y-1} 50 {MOUTH_Y-6} Z", fill=c))


def _glasses(style):
    line, glass = "#e8eaf0", "#9fc6ff"
    if style == "none":
        return ""
    if style == "square":
        return (_e("rect", x=42, y=45, width=16, height=13, rx=2.5, fill=glass,
                   fill_opacity="0.16", stroke=line, stroke_width=2) +
                _e("rect", x=62, y=45, width=16, height=13, rx=2.5, fill=glass,
                   fill_opacity="0.16", stroke=line, stroke_width=2) +
                _e("path", d="M58 51 L62 51 M42 50 L35 52 M78 50 L85 52",
                   stroke=line, stroke_width=2, fill="none"))
    if style == "halfmoon":
        return (_e("path", d="M42 53 Q50 60 58 53", fill="none", stroke=line, stroke_width=2) +
                _e("path", d="M62 53 Q70 60 78 53", fill="none", stroke=line, stroke_width=2) +
                _e("path", d="M42 53 L58 53 M62 53 L78 53 M58 53 L62 53 M42 53 L35 51 M78 53 L85 51",
                   stroke=line, stroke_width=2, fill="none"))
    return (_e("circle", cx=50, cy=52, r=8.5, fill=glass, fill_opacity="0.16",
               stroke=line, stroke_width=2) +
            _e("circle", cx=70, cy=52, r=8.5, fill=glass, fill_opacity="0.16",
               stroke=line, stroke_width=2) +
            _e("path", d="M58.5 52 L61.5 52 M41.5 51 L35 52 M78.5 51 L85 52",
               stroke=line, stroke_width=2, fill="none"))


# --------------------------------------------------------------------------
# Body
# --------------------------------------------------------------------------

SHOULDERS = "M16 120 C16 100 33 90 60 90 C87 90 104 100 104 120 Z"


def _top(style, c, dark):
    body = _e("path", d=SHOULDERS, fill=c)
    if style == "turtleneck":
        return body + _e("rect", x=50, y=80, width=20, height=13, rx=6, fill=c)
    if style == "hoodie":
        return (body + _e("path", d="M44 92 Q60 104 76 92 L76 120 L44 120 Z", fill=dark) +
                _e("path", d="M46 91 Q60 102 74 91", fill="none", stroke=dark, stroke_width=5) +
                _e("path", d="M58 100 L58 116 M62 100 L62 116", stroke="#ffffff",
                   stroke_opacity="0.5", stroke_width=2, fill="none"))
    if style == "blazer":
        return (body + _e("path", d="M60 92 L46 120 L34 120 L44 93 Z", fill=dark) +
                _e("path", d="M60 92 L74 120 L86 120 L76 93 Z", fill=dark) +
                _e("path", d="M52 92 L60 104 L68 92 L68 120 L52 120 Z", fill="#e8eaf0"))
    if style == "shirt":
        return (body + _e("path", d="M52 91 L60 101 L68 91 L68 120 L52 120 Z", fill="#e8eaf0") +
                _e("path", d="M53 91 L60 100 L67 91", fill="none", stroke=dark, stroke_width=2))
    if style == "cardigan":
        return (body + _e("path", d="M54 92 L54 120 L66 120 L66 92 Z", fill="#e8eaf0") +
                _e("path", d="M54 92 L54 120 M66 92 L66 120", stroke=dark,
                   stroke_width=2, fill="none") +
                _e("circle", cx=60, cy=104, r=1.8, fill=dark) +
                _e("circle", cx=60, cy=114, r=1.8, fill=dark))
    if style == "polo":
        return (body + _e("path", d="M53 91 L60 99 L67 91 L67 106 L53 106 Z", fill=dark) +
                _e("circle", cx=60, cy=104, r=1.6, fill="#e8eaf0"))
    return body + _e("path", d="M50 92 Q60 99 70 92", fill="none", stroke=dark, stroke_width=3)


def _accent(style, c):
    if style == "none":
        return ""
    if style == "tie":
        return (_e("path", d="M60 96 L56 100 L60 104 L64 100 Z", fill=c) +
                _e("path", d="M60 104 L56 118 L60 120 L64 118 Z", fill=c))
    if style == "scarf":
        return (_e("path", d="M44 92 Q60 102 76 92 L78 100 Q60 111 42 100 Z", fill=c) +
                _e("path", d="M70 100 L74 120 L66 120 Z", fill=c))
    if style == "lanyard":
        return (_e("path", d="M52 92 L60 108 L68 92", fill="none", stroke=c, stroke_width=2.6) +
                _e("rect", x=55, y=107, width=10, height=8, rx=2, fill=c))
    if style == "headphones":
        return (_e("path", d="M33 52 Q33 20 60 20 Q87 20 87 52", fill="none",
                   stroke=c, stroke_width=4) +
                _e("rect", x=28, y=48, width=10, height=17, rx=5, fill=c) +
                _e("rect", x=82, y=48, width=10, height=17, rx=5, fill=c))
    if style == "earrings":
        return "".join(_e("circle", cx=x, cy=63, r=3.2, fill=c) for x in (36, 84))
    if style == "pin":
        return _e("circle", cx=45, cy=101, r=3.4, fill=c)
    return (_e("path", d="M48 93 Q60 106 72 93", fill="none", stroke=c, stroke_width=2) +
            _e("circle", cx=60, cy=104, r=3, fill=c))


def _prop(style):
    if style == "none":
        return ""
    if style == "mug":
        return (_e("rect", x=88, y=98, width=18, height=16, rx=3, fill="#e8eaf0") +
                _e("path", d="M106 102 q6 4 0 8", fill="none", stroke="#e8eaf0", stroke_width=2.6) +
                _e("rect", x=88, y=98, width=18, height=4, rx=2, fill="#9aa3b5"))
    if style == "notepad":
        return (_e("rect", x=86, y=96, width=20, height=22, rx=2, fill="#e8eaf0") +
                _e("path", d="M90 103 L102 103 M90 108 L102 108 M90 113 L98 113",
                   stroke="#9aa3b5", stroke_width=1.8, fill="none"))
    if style == "clipboard":
        return (_e("rect", x=86, y=94, width=21, height=24, rx=2, fill="#d8d2c6") +
                _e("rect", x=92, y=91, width=9, height=6, rx=2, fill="#9aa3b5") +
                _e("path", d="M90 105 L103 105 M90 110 L103 110 M90 115 L99 115",
                   stroke="#7c8496", stroke_width=1.8, fill="none"))
    if style == "phone":
        return (_e("rect", x=90, y=94, width=15, height=24, rx=3, fill="#1c202b",
                   stroke="#e8eaf0", stroke_width=1.6) +
                _e("rect", x=93, y=98, width=9, height=14, rx=1, fill="#5b8cff",
                   fill_opacity="0.65"))
    if style == "pencil":
        return (_e("path", d="M88 118 L104 96 L108 99 L92 120 Z", fill="#c8862b") +
                _e("path", d="M104 96 L108 99 L107 93 Z", fill="#e8eaf0"))
    return (_e("path", d="M96 92 Q104 96 100 102", fill="none",
               stroke="#d8d2c6", stroke_width=2) +
            _e("rect", x=88, y=101, width=20, height=13, rx=6.5, fill="#c8862b") +
            _e("rect", x=83, y=104, width=7, height=7, rx=2, fill="#c8862b") +
            _e("circle", cx=101, cy=107, r=3, fill="#1c202b"))


# --------------------------------------------------------------------------

def render(look):
    """Return one portrait as an SVG string. ``look`` must satisfy SCHEMA."""
    skin, shade = SKIN[look["skin"]]
    hair = HAIR_COLOUR[look["hair_colour"]]
    cloth = CLOTH[look["top_colour"]]
    back = BACKDROP[look["backdrop"]]
    accent_colour = CLOTH[look["accent_colour"]]
    dark = "#0f1117"

    parts = [
        _e("rect", x=0, y=0, width=120, height=120, rx=18, fill=back),
        _hair_back(look["hair"], hair),
        _top(look["top"], cloth, dark),
        _accent(look["accent"], accent_colour),
        _e("rect", x=53, y=70, width=14, height=22, rx=6, fill=shade),
        _e("ellipse", cx=36, cy=54, rx=4.4, ry=6, fill=skin),
        _e("ellipse", cx=84, cy=54, rx=4.4, ry=6, fill=skin),
        _e("ellipse", cx=CX, cy=CY, rx=RX, ry=RY, fill=skin),
        _hair_front(look["hair"], hair),
        _shine(look["hair"], hair),
        _brows(look["brows"], hair),
        _one_eye(look["eyes"], EYE_L),
        _one_eye(look["eyes"], EYE_R),
        _e("path", d="M59 55 L56.4 62 Q60 64.5 63.4 62", fill="none", stroke=shade,
           stroke_width=2.6, stroke_linecap="round", stroke_linejoin="round"),
        _facial_hair(look["facial_hair"], hair),
        _mouth(look["mouth"], skin, "#8d4a4f"),
        _glasses(look["glasses"]),
        _prop(look["prop"]),
    ]
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" '
            'width="120" height="120" role="img">' + "".join(parts) + "</svg>")


def load_appearance(root=ROOT):
    """The wardrobe, keyed by agent id. Keys starting with '_' are notes, not people."""
    raw = json.loads((root / "company/agents/appearance.json").read_text(encoding="utf-8"))
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def write_all(out_dir, root=ROOT):
    """Render every colleague into ``out_dir``. Returns the number written."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    looks = load_appearance(root)
    for agent_id, look in looks.items():
        (out_dir / f"{agent_id}.svg").write_text(render(look), encoding="utf-8")
    return len(looks)


if __name__ == "__main__":
    print(f"{write_all(ROOT / 'site/data/avatars')} portraits written")
