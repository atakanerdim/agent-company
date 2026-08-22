"""A persona predicts for the track whose night it is — and stays quiet otherwise.

Three outcomes must never be confused: predictions written, nothing to predict,
and the analyst failed to deliver. The middle one is the calendar (a summer break,
an international window, a week with no European football) and it has to cost
nothing: no file, no pull request, no error log. Without that, three months of
close season would fill the public changelog with false alarms every week.
"""
import json, os, subprocess, sys


def _run(company, agent, day, date):
    env = dict(os.environ, SHIFT_DATE=date)
    return subprocess.run([sys.executable, str(company / "kernel/runner.py"),
                           "--agent", agent, "--day", day],
                          cwd=company, env=env, capture_output=True, text=True)


def test_friday_predicts_the_domestic_track(company):
    _run(company, "analyst", "thu", "2026-08-20")
    p = _run(company, "statistician", "fri", "2026-08-21")
    assert p.returncode == 0, p.stderr
    t = json.loads((company /
                    "company/data/predictions/statistician/domestic/2026-W34.json").read_text())
    assert len(t) == 3
    assert all(x["score"].count("-") == 1 for x in t)
    assert {x["match_id"] for x in t} == {1001, 1002, 1003}
    q = json.loads((company / "out/pr_queue.json").read_text())
    assert q[-1]["title"].startswith("predictions: statistician domestic")


def test_tuesday_predicts_the_european_track(company):
    _run(company, "analyst", "mon", "2026-08-24")
    p = _run(company, "statistician", "tue", "2026-08-25")
    assert p.returncode == 0, p.stderr
    assert (company /
            "company/data/predictions/statistician/europe/2026-W35.json").exists()


def test_a_week_with_no_matches_is_not_a_failed_shift(company):
    """No football is the calendar, not a fault: no file, no pull request, no log."""
    europe = company / "company/data/fixtures/europe"
    europe.mkdir(parents=True, exist_ok=True)
    (europe / "2026-W35.json").write_text("[]", encoding="utf-8")
    p = _run(company, "statistician", "tue", "2026-08-25")
    assert p.returncode == 0, p.stderr
    assert not list((company / "company/data/predictions").rglob("*.json"))
    assert not (company / "out/pr_queue.json").exists()
    assert not list((company / "company/log").glob("*.log"))


def test_a_missing_fixture_file_is_still_a_failed_shift(company):
    """The quiet path must not swallow a real breakage."""
    p = _run(company, "statistician", "tue", "2026-08-25")
    assert p.returncode == 1
    assert any("statistician" in f.read_text(encoding="utf-8")
               for f in (company / "company/log").glob("*.log"))


def test_a_day_that_predicts_nothing_passes_quietly(company):
    """Wednesday belongs to no track. Nothing to do is not something to report."""
    p = _run(company, "statistician", "wed", "2026-08-26")
    assert p.returncode == 0, p.stderr
    assert not (company / "out/pr_queue.json").exists()
    assert not list((company / "company/log").glob("*.log"))
