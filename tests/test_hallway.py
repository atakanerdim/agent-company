"""What the office says to itself, printed as one voice per line.

The kernel writes a hallway file as "<colleague>: <what they said>", and the page
prints the colleague separately, from the roster. So the name only ever needed to
be in one of those two places, and for a fortnight it was in both:

    Kiran Menon: Kiran Menon: Guard against missing shifts in desk rendering.

On 2026-09-02 the second name stopped being a duplicate and started being a
fabrication. The Office Correspondent filed this:

    Nadia Vance: Liam Zhou: The coffee machine may be gone, but our nightly ...

There is no Liam Zhou. Twelve colleagues work here and a visitor can count them on
the same page. The line was published under Nadia's portrait and attributed to a
thirteenth person who does not exist.

The record in company/hallway keeps every word of that, because the record is the
evidence and evidence is not tidied. What these tests hold is the display: a line
on the page carries what was said, and the page says who said it.
"""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _build():
    sys.path.insert(0, str(ROOT / "assets"))
    spec = importlib.util.spec_from_file_location("site_build", ROOT / "site/build.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_name_the_kernel_already_wrote_is_not_printed_twice():
    said = _build().hallway_line(
        "Kiran Menon: Kiran Menon: Guard against missing shifts in desk rendering.")
    assert said == "Guard against missing shifts in desk rendering."


def test_a_colleague_who_does_not_exist_does_not_get_a_byline():
    """The real line, from company/hallway/2026-09-02-gossip.txt."""
    said = _build().hallway_line(
        "Nadia Vance: Liam Zhou: The coffee machine may be gone, but our nightly "
        "model sync is now bullet-proof.")
    assert "Liam Zhou" not in said
    assert said.startswith("The coffee machine may be gone")


def test_a_line_that_is_only_a_sentence_survives_whole():
    build = _build()
    for line, expected in [
        ("Amara Diallo: My domestic leagues picks for 2026-W35 are in.",
         "My domestic leagues picks for 2026-W35 are in."),
        ("Hana Sato: No european nights this week.",
         "No european nights this week."),
    ]:
        assert build.hallway_line(line) == expected


def test_a_colon_that_is_not_a_name_is_left_alone():
    """One capitalised word in front of a colon is punctuation, not a byline."""
    build = _build()
    assert build.hallway_line("Oscar Delgado: Note: the sprint board is full again.") \
        == "Note: the sprint board is full again."
    assert build.hallway_line("Hana Sato: Week 35: no european nights.") \
        == "Week 35: no european nights."


def test_every_line_the_office_has_ever_left_still_says_something():
    """Stripping may never empty a real line, whatever the office has filed.

    No count is asserted here on purpose. Twice already a test has counted what the
    company had accumulated by the day it was written, and gone red the week the
    company accumulated more. Whatever is in the hallway on any given day, none of
    it may be reduced to nothing; an empty hallway passes that trivially and
    correctly.
    """
    build = _build()
    for path in sorted((ROOT / "company/hallway").glob("*.txt")):
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            continue
        assert build.hallway_line(raw), f"{path.name} was stripped down to nothing"
