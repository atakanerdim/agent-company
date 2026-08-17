import json, os, subprocess, sys

def _shift(sirket, agent, day, date):
    env = dict(os.environ, SHIFT_DATE=date)
    return subprocess.run([sys.executable, str(sirket / "kernel/runner.py"), "--agent", agent, "--day", day],
                          cwd=sirket, env=env, capture_output=True, text=True)

def test_score_prediction():
    import importlib.util
    from pathlib import Path
    path = Path(__file__).resolve().parents[1] / "company/agents/logic/evaluator.py"
    spec = importlib.util.spec_from_file_location("ev", path)
    ev = importlib.util.module_from_spec(spec); spec.loader.exec_module(ev)
    assert ev.score_prediction("2-1", (2, 1)) == 3
    assert ev.score_prediction("2-1", (3, 1)) == 1
    assert ev.score_prediction("2-1", (1, 1)) == 0
    assert ev.score_prediction("1-1", (2, 2)) == 1

def test_weekly_cycle(sirket):
    _shift(sirket, "analyst", "thu", "2026-08-20")
    for a in ("statistician", "romantic", "coolhead"):
        _shift(sirket, a, "fri", "2026-08-21")
    _shift(sirket, "analyst", "mon", "2026-08-24")
    p = _shift(sirket, "evaluator", "mon", "2026-08-24")
    assert p.returncode == 0, p.stderr
    s = json.loads((sirket / "company/data/scores/2026-W34.json").read_text())
    assert s["statistician"]["points"] == 3
    lg = json.loads((sirket / "company/data/league.json").read_text())
    assert lg["personas"]["statistician"] == {"points": 3, "exact": 1, "outcome": 0, "weeks": 1}
    mins = [m for m in (sirket / "company/minutes").iterdir() if "evaluator" in m.name]
    assert mins and "Mock retro" in mins[0].read_text()
