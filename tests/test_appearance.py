"""The wardrobe is open; the skeleton is not.

The Designer may edit ``company/agents/appearance.json`` through the normal pull
request, so colleagues can change clothes, hair, glasses and expression over time.
These tests are the fence around that freedom: a value that is not in the schema,
a slot that does not exist, a missing colleague or a portrait that fails to draw
turns CI red, and a red pull request never merges.

They read the company's *definition* (roster, identity, wardrobe), which the test
fixture deliberately preserves, so they do not need a pristine copy.
"""
import json
import sys
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "assets"))
import avatars  # noqa: E402


def _roster_ids():
    rows = json.loads((ROOT / "company/roster.json").read_text(encoding="utf-8"))
    return [r["id"] for r in rows]


def _identity():
    return json.loads((ROOT / "company/agents/identity.json").read_text(encoding="utf-8"))


def test_every_colleague_has_a_look_and_nobody_extra():
    looks = avatars.load_appearance(ROOT)
    assert sorted(looks) == sorted(_roster_ids())


def test_every_look_uses_exactly_the_declared_slots():
    for agent_id, look in avatars.load_appearance(ROOT).items():
        assert sorted(look) == sorted(avatars.SCHEMA), f"{agent_id}: slot list changed"


def test_every_value_is_one_the_schema_allows():
    """No second nose. Values are names from a fixed list, never raw geometry or colour."""
    for agent_id, look in avatars.load_appearance(ROOT).items():
        for slot, value in look.items():
            assert value in avatars.SCHEMA[slot], \
                f"{agent_id}.{slot} = {value!r} is not an allowed value"


def test_every_portrait_draws_and_parses():
    for agent_id, look in avatars.load_appearance(ROOT).items():
        svg = avatars.render(look)
        ElementTree.fromstring(svg)  # raises if the SVG is malformed
        assert svg.startswith("<svg"), agent_id
        # No external or internal reference to resolve: sanitisers and offline
        # renderers drop those, and a dropped reference means nothing is drawn.
        assert "url(" not in svg and "xlink" not in svg, agent_id
        assert 1500 < len(svg) < 20000, f"{agent_id}: suspicious portrait size {len(svg)}"


def test_portraits_are_deterministic():
    looks = avatars.load_appearance(ROOT)
    once = {k: avatars.render(v) for k, v in looks.items()}
    twice = {k: avatars.render(v) for k, v in looks.items()}
    assert once == twice


def test_identity_covers_the_roster_and_reads_as_prose():
    people = _identity()
    assert sorted(p["id"] for p in people) == sorted(_roster_ids())
    for p in people:
        for field in ("person", "title", "room", "bio"):
            assert p[field].strip(), f"{p['id']}: {field} is empty"
        # The site shows a human description, never the working instructions.
        assert len(p["bio"]) > 40, f"{p['id']}: bio too thin to be worth reading"
        assert "You are" not in p["bio"], f"{p['id']}: bio is prompt text, not a description"


def test_every_prompt_still_carries_its_own_name():
    """The Process Owner may rewrite any prompt, but not rename a colleague.

    A persona only knows who it is from its prompt: the kernel builds the system
    message from the house rules and that file alone. Lose the name there and the
    colleague stops signing its reviews, which is the only thing that tells the
    office page who is speaking — and the roster and the portraits go on claiming
    a person the text no longer describes.
    """
    rows = json.loads((ROOT / "company/roster.json").read_text(encoding="utf-8"))
    for person in _identity():
        prompt = (ROOT / f"company/agents/prompts/{person['id']}.md").read_text(encoding="utf-8")
        assert person["person"] in prompt, \
            f"{person['id']}: the prompt no longer names {person['person']}"
        row = next(r for r in rows if r["id"] == person["id"])
        assert row["ad"] == person["person"], \
            f"{person['id']}: roster display name and identity disagree"


def test_the_designer_can_actually_reach_the_wardrobe():
    """The freedom has to be wired up, not just described in a brief.

    Three things must line up or the wardrobe quietly becomes read-only: the file is
    in the Designer's area, the editor samples it into their context, and the path
    check accepts it.
    """
    rows = json.loads((ROOT / "company/roster.json").read_text(encoding="utf-8"))
    designer = next(r for r in rows if r["id"] == "designer")
    wardrobe = "company/agents/appearance.json"
    assert wardrobe in designer["alan"]

    sys.path.insert(0, str(ROOT / "company/agents/logic"))
    import editor  # noqa: E402
    context, unrewritable = editor._current(ROOT, designer["alan"])
    assert wardrobe in context, \
        "the editor does not sample the wardrobe, so the Designer would rewrite it blind"
    assert '"skin"' in context, "the wardrobe is listed but its contents were not included"
    assert wardrobe not in unrewritable, \
        "the wardrobe outgrew the sample limit, so the Designer can no longer change it"


def test_wardrobe_rejects_an_invented_value():
    """The fence is real: prove it catches something it should catch."""
    look = dict(next(iter(avatars.load_appearance(ROOT).values())))
    look["hair"] = "second_nose"
    assert look["hair"] not in avatars.SCHEMA["hair"]
