import json, os, subprocess, sys
from pathlib import Path

def _run(sirket, *arg, extra_env=None):
    env = dict(os.environ, SHIFT_DATE="2026-08-19")
    if extra_env: env.update(extra_env)
    return subprocess.run([sys.executable, str(sirket / "kernel/runner.py"), *arg],
                          cwd=sirket, env=env, capture_output=True, text=True)

def test_list_friday(sirket):
    p = _run(sirket, "--list", "--day", "fri")
    assert p.returncode == 0, p.stderr
    assert p.stdout.split() == ["statistician", "romantic", "coolhead", "pessimist"]

def test_generic_shift(sirket):
    p = _run(sirket, "--agent", "gossip", "--day", "wed")
    assert p.returncode == 0, p.stderr
    mins = list((sirket / "company/minutes").glob("*gossip*"))
    assert mins and "Mock shift" in mins[0].read_text()
    hall = list((sirket / "company/hallway").glob("2026-08-19-gossip.txt"))
    assert hall and "calm" in hall[0].read_text()
    q = json.loads((sirket / "out/pr_queue.json").read_text())
    assert q[-1]["agent"] == "gossip" and q[-1]["draft"] is False

def test_house_rules_prepended(sirket):
    sys.path.insert(0, str(sirket / "kernel"))
    import importlib, runner as r
    importlib.reload(r)
    roster = json.loads((sirket / "company/roster.json").read_text())
    ceo = next(a for a in roster if a["id"] == "ceo")
    ctx = r.build_ctx(sirket, ceo, "sun", "normal", None)
    assert ctx["prompt"].startswith("HOUSE RULES")
    assert "No profanity" in ctx["prompt"]

def test_broken_json_skipped(sirket):
    roster = json.loads((sirket / "company/roster.json").read_text())
    roster.append({"id":"broken","ad":"Broken","rol":"test","logic":None,"alan":None,"gunler":["wed"],"draft_pr":False})
    (sirket / "company/roster.json").write_text(json.dumps(roster))
    (sirket / "company/agents/prompts/broken.md").write_text("test")
    (sirket / "company/agents/memory/broken.md").write_text("empty")
    p = _run(sirket, "--agent", "broken", "--day", "wed")
    assert p.returncode == 0
    logs = list((sirket / "company/log").glob("*.log"))
    assert logs and "broken" in logs[0].read_text()

def test_editor_agent(sirket):
    p = _run(sirket, "--agent", "designer", "--day", "tue")
    assert p.returncode == 0, p.stderr
    assert (sirket / "site/theme-mock.css").exists()
    q = json.loads((sirket / "out/pr_queue.json").read_text())
    assert q[-1]["draft"] is True and "purple" in q[-1]["body"]

def test_editor_area_guard(sirket):
    bad = {"[AGENT:webdev]": {"files":{"kernel/runner.py":"x"},"rationale":"malicious intent here","hallway":None}}
    (sirket / "bad.json").write_text(json.dumps(bad))
    p = _run(sirket, "--agent", "webdev", "--day", "wed",
             extra_env={"MOCK_ANSWERS": str(sirket / "bad.json")})
    assert p.returncode == 0
    assert (sirket / "kernel/runner.py").read_text() != "x"
    assert list((sirket / "company/log").glob("*.log"))
