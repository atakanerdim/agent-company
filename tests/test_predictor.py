import json, os, subprocess, sys

def test_predictions(company):
    env = dict(os.environ, SHIFT_DATE="2026-08-20")
    subprocess.run([sys.executable, str(company / "kernel/runner.py"), "--agent", "analyst", "--day", "thu"],
                   cwd=company, env=env, capture_output=True, text=True)
    env["SHIFT_DATE"] = "2026-08-21"
    p = subprocess.run([sys.executable, str(company / "kernel/runner.py"), "--agent", "statistician", "--day", "fri"],
                       cwd=company, env=env, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    t = json.loads((company / "company/data/predictions/statistician/2026-W34.json").read_text())
    assert len(t) == 3
    assert all(x["score"].count("-") == 1 for x in t)
    assert {x["match_id"] for x in t} == {1001, 1002, 1003}
    q = json.loads((company / "out/pr_queue.json").read_text())
    assert q[-1]["title"].startswith("predictions: statistician")
