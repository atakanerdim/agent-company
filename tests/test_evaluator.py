"""Each competition track keeps its own table, and a long silence ends a season."""
import datetime as dt
import json, os, subprocess, sys


def _run(company, date, day="mon"):
    env = dict(os.environ, SHIFT_DATE=date)
    return subprocess.run([sys.executable, str(company / "kernel/runner.py"),
                           "--agent", "evaluator", "--day", day],
                          cwd=company, env=env, capture_output=True, text=True)


def _put(company, rel, payload):
    path = company / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _round(company, track, week, score="2-1", actual=(2, 1)):
    _put(company, f"company/data/results/{track}/{week}.json",
         [{"match_id": 1, "home_goals": actual[0], "away_goals": actual[1]}])
    for persona in ("statistician", "romantic", "coolhead"):
        _put(company, f"company/data/predictions/{persona}/{track}/{week}.json",
             [{"match_id": 1, "home": "A", "away": "B", "score": score, "reasoning": "x"}])


def _league(company):
    return json.loads((company / "company/data/league.json").read_text(encoding="utf-8"))


def test_each_track_is_scored_onto_its_own_table(company):
    _round(company, "domestic", "2026-W34", score="2-1")          # exact, 3 points
    _round(company, "europe", "2026-W34", score="1-0")            # right winner, 1 point
    p = _run(company, "2026-08-24")
    assert p.returncode == 0, p.stderr
    league = _league(company)
    assert league["tracks"]["domestic"]["personas"]["statistician"]["points"] == 3
    assert league["tracks"]["europe"]["personas"]["statistician"]["points"] == 1
    assert (company / "company/data/scores/domestic/2026-W34.json").exists()
    assert (company / "company/data/scores/europe/2026-W34.json").exists()


def test_one_track_playing_is_enough(company):
    """A week with no European football must not stop the domestic scoring."""
    _round(company, "domestic", "2026-W34")
    p = _run(company, "2026-08-24")
    assert p.returncode == 0, p.stderr
    league = _league(company)
    assert league["tracks"]["domestic"]["personas"]["statistician"]["weeks"] == 1
    assert league["tracks"]["europe"]["personas"]["statistician"]["weeks"] == 0
    assert not (company / "company/data/scores/europe/2026-W34.json").exists()


def test_no_track_playing_is_a_failed_shift(company):
    p = _run(company, "2026-08-24")
    assert p.returncode == 1
    assert any("evaluator" in f.read_text(encoding="utf-8")
               for f in (company / "company/log").glob("*.log"))


def test_a_long_silence_archives_the_season_and_starts_a_new_one(company):
    """A close season is a gap in the scoring, and the table must not carry across it."""
    _round(company, "domestic", "2026-W34")
    assert _run(company, "2026-08-24").returncode == 0
    assert _league(company)["tracks"]["domestic"]["personas"]["statistician"]["points"] == 3

    # Nine weeks later — a summer of nothing — the same track plays again.
    later_monday = dt.date(2026, 8, 24) + dt.timedelta(weeks=9)
    later_week = "%d-W%02d" % (later_monday - dt.timedelta(days=3)).isocalendar()[:2]
    _round(company, "domestic", later_week)
    p = _run(company, later_monday.isoformat())
    assert p.returncode == 0, p.stderr

    record = _league(company)["tracks"]["domestic"]
    assert record["personas"]["statistician"]["points"] == 3, "the new season starts from zero"
    assert record["personas"]["statistician"]["weeks"] == 1
    assert record["first_week"] == later_week
    archived = list((company / "company/data/league-archive").glob("domestic-*.json"))
    assert len(archived) == 1 and "2026-W34" in archived[0].name


def test_a_short_gap_does_not_end_the_season(company):
    """An international break is two or three weeks. The table must survive it."""
    _round(company, "domestic", "2026-W34")
    assert _run(company, "2026-08-24").returncode == 0
    later_monday = dt.date(2026, 8, 24) + dt.timedelta(weeks=3)
    later_week = "%d-W%02d" % (later_monday - dt.timedelta(days=3)).isocalendar()[:2]
    _round(company, "domestic", later_week)
    assert _run(company, later_monday.isoformat()).returncode == 0
    record = _league(company)["tracks"]["domestic"]
    assert record["personas"]["statistician"]["points"] == 6, "points carry across a short gap"
    assert not (company / "company/data/league-archive").exists() or \
        not list((company / "company/data/league-archive").glob("*.json"))
