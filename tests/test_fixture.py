"""The fixture's promise: a test sees a company that has not run yet.

Without this the suite quietly measures how long the company has been alive. A test
written on week one passes, the same test fails on week two, and the failure names a
league table instead of the bug. Every guard here exists because that already happened.
"""
import json

from conftest import ACCUMULATED


def test_no_accumulated_output(company):
    for rel in ACCUMULATED:
        leftovers = [p.name for p in (company / rel).glob("*") if p.name != ".gitkeep"]
        assert not leftovers, f"{rel} still holds {leftovers} from the real company"


def test_every_track_starts_at_zero(company):
    league = json.loads((company / "company/data/league.json").read_text(encoding="utf-8"))
    assert league["tracks"], "the league lost its tracks"
    for track, record in league["tracks"].items():
        assert record["personas"], f"{track} lost its personas"
        assert record["first_week"] is None and record["last_week"] is None, \
            f"{track} arrives mid-season: {record['first_week']}..{record['last_week']}"
        for name, row in record["personas"].items():
            assert row == {"points": 0, "exact": 0, "outcome": 0, "weeks": 0}, \
                f"{track}/{name} arrives with a history: {row}"


def test_the_league_covers_every_track_the_company_defines(company):
    """A track with no table would score into nothing and lose the week in silence."""
    league = json.loads((company / "company/data/league.json").read_text(encoding="utf-8"))
    tracks = json.loads((company / "company/data/tracks.json").read_text(encoding="utf-8"))
    assert set(league["tracks"]) == {t["id"] for t in tracks["tracks"]}


def test_the_agents_are_still_there(company):
    """Wiping output must never reach the company's own definition."""
    roster = json.loads((company / "company/roster.json").read_text(encoding="utf-8"))
    assert len(roster) == 12
    for agent in roster:
        assert (company / f"company/agents/prompts/{agent['id']}.md").exists()
        assert (company / f"company/agents/memory/{agent['id']}.md").exists()
    assert (company / "company/constitution.md").exists()
