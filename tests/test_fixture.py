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


def test_league_starts_at_zero(company):
    league = json.loads((company / "company/data/league.json").read_text(encoding="utf-8"))
    assert league["personas"], "the league lost its personas"
    for name, row in league["personas"].items():
        assert row == {"points": 0, "exact": 0, "outcome": 0, "weeks": 0}, \
            f"{name} arrives with a history: {row}"


def test_the_agents_are_still_there(company):
    """Wiping output must never reach the company's own definition."""
    roster = json.loads((company / "company/roster.json").read_text(encoding="utf-8"))
    assert len(roster) == 12
    for agent in roster:
        assert (company / f"company/agents/prompts/{agent['id']}.md").exists()
        assert (company / f"company/agents/memory/{agent['id']}.md").exists()
    assert (company / "company/constitution.md").exists()
