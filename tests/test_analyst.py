import json, os, subprocess, sys

def _run(sirket, day, date):
    env = dict(os.environ, SHIFT_DATE=date)
    return subprocess.run([sys.executable, str(sirket / "kernel/runner.py"), "--agent", "analyst", "--day", day],
                          cwd=sirket, env=env, capture_output=True, text=True)

def test_thursday_fixtures(sirket):
    p = _run(sirket, "thu", "2026-08-20")
    assert p.returncode == 0, p.stderr
    f = json.loads((sirket / "company/data/fixtures/2026-W34.json").read_text())
    assert len(f) == 4 and f[0]["home"] == "Arsenal" and f[0]["league"] == "PL"
    mins = list((sirket / "company/minutes").glob("*analyst*"))
    assert mins and "Mock briefing" in mins[0].read_text()

def test_monday_results(sirket):
    p = _run(sirket, "mon", "2026-08-24")
    assert p.returncode == 0, p.stderr
    r = json.loads((sirket / "company/data/results/2026-W34.json").read_text())
    assert {x["match_id"]: (x["home_goals"], x["away_goals"]) for x in r} == {1001: (2, 1), 1002: (3, 1)}

def test_http_error_keeps_files(sirket):
    old = '[{"match_id": 9, "league": "PL", "home": "A", "away": "B", "date": "x"}]'
    (sirket / "company/data/fixtures/2026-W34.json").write_text(old)
    env = dict(os.environ, SHIFT_DATE="2026-08-20", MOCK_HTTP="fail")
    p = subprocess.run([sys.executable, str(sirket / "kernel/runner.py"), "--agent", "analyst", "--day", "thu"],
                       cwd=sirket, env=env, capture_output=True, text=True)
    assert p.returncode == 0
    assert (sirket / "company/data/fixtures/2026-W34.json").read_text() == old
    assert list((sirket / "company/log").glob("*.log"))
