import json, os, subprocess, sys
from pathlib import Path

EMPTY_FIXTURES = Path(__file__).resolve().parent / "mock_fixtures_empty.json"


def _run(company, day, date, extra_env=None):
    env = dict(os.environ, SHIFT_DATE=date)
    if extra_env:
        env.update(extra_env)
    return subprocess.run([sys.executable, str(company / "kernel/runner.py"),
                           "--agent", "analyst", "--day", day],
                          cwd=company, env=env, capture_output=True, text=True)


def test_thursday_carries_both_tracks(company):
    """Domestic fixtures for the weekend ahead, European results for the midweek behind."""
    p = _run(company, "thu", "2026-08-20")
    assert p.returncode == 0, p.stderr
    f = json.loads((company / "company/data/fixtures/domestic/2026-W34.json").read_text())
    assert len(f) == 4 and f[0]["home"] == "Arsenal" and f[0]["league"] == "PL"
    assert (company / "company/data/results/europe/2026-W34.json").exists()
    mins = list((company / "company/minutes").glob("*analyst*"))
    assert any("Mock briefing" in m.read_text(encoding="utf-8") for m in mins)


def test_monday_carries_both_tracks(company):
    """The domestic weekend closes and the European midweek opens in one shift."""
    p = _run(company, "mon", "2026-08-24")
    assert p.returncode == 0, p.stderr
    r = json.loads((company / "company/data/results/domestic/2026-W34.json").read_text())
    assert {x["match_id"]: (x["home_goals"], x["away_goals"]) for x in r} == \
        {1001: (2, 1), 1002: (3, 1)}
    assert (company / "company/data/fixtures/europe/2026-W35.json").exists()


def test_one_shift_opens_one_pull_request_naming_every_job(company):
    p = _run(company, "mon", "2026-08-24")
    assert p.returncode == 0, p.stderr
    q = json.loads((company / "out/pr_queue.json").read_text())
    title = q[-1]["title"]
    assert title.startswith("analyst: "), "the changelog filter reads this prefix"
    assert "domestic results 2026-W34" in title and "europe fixtures 2026-W35" in title
    assert len([e for e in q if e["agent"] == "analyst"]) == 1


def test_a_week_with_no_matches_is_written_down_and_said_out_loud(company):
    """An empty week must cost nothing and must not look like a failure."""
    p = _run(company, "mon", "2026-08-24",
             {"MOCK_FIXTURES": str(EMPTY_FIXTURES)})
    assert p.returncode == 0, p.stderr
    fixtures = company / "company/data/fixtures/europe/2026-W35.json"
    assert json.loads(fixtures.read_text()) == []
    hall = (company / "company/hallway/2026-08-24-analyst.txt").read_text(encoding="utf-8")
    assert "european nights" in hall.lower()
    assert not list((company / "company/log").glob("*.log"))
    briefings = list((company / "company/minutes").glob("*europe-briefing*"))
    assert not briefings, "an empty week must not spend a model call on a briefing"


def test_http_error_keeps_files(company):
    old = '[{"match_id": 9, "league": "PL", "home": "A", "away": "B", "date": "x"}]'
    target = company / "company/data/fixtures/domestic/2026-W34.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(old)
    p = _run(company, "thu", "2026-08-20", {"MOCK_HTTP": "fail"})
    assert p.returncode == 1, "a skipped shift must report failure"
    assert target.read_text() == old
    assert any("analyst" in f.read_text(encoding="utf-8")
               for f in (company / "company/log").glob("*.log"))
