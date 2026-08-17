import json, os, subprocess, sys
from pathlib import Path

def _run(company, *arg, extra_env=None):
    env = dict(os.environ, SHIFT_DATE="2026-08-19")
    if extra_env: env.update(extra_env)
    return subprocess.run([sys.executable, str(company / "kernel/runner.py"), *arg],
                          cwd=company, env=env, capture_output=True, text=True)

def test_list_friday(company):
    p = _run(company, "--list", "--day", "fri")
    assert p.returncode == 0, p.stderr
    assert p.stdout.split() == ["statistician", "romantic", "coolhead", "pessimist"]

def test_generic_shift(company):
    p = _run(company, "--agent", "gossip", "--day", "wed")
    assert p.returncode == 0, p.stderr
    mins = list((company / "company/minutes").glob("*gossip*"))
    assert mins and "Mock shift" in mins[0].read_text()
    hall = list((company / "company/hallway").glob("2026-08-19-gossip.txt"))
    assert hall and "calm" in hall[0].read_text()
    q = json.loads((company / "out/pr_queue.json").read_text())
    assert q[-1]["agent"] == "gossip" and q[-1]["draft"] is False

def test_house_rules_prepended(company):
    sys.path.insert(0, str(company / "kernel"))
    import importlib, runner as r
    importlib.reload(r)
    roster = json.loads((company / "company/roster.json").read_text())
    ceo = next(a for a in roster if a["id"] == "ceo")
    ctx = r.build_ctx(company, ceo, "sun", "normal", None)
    assert ctx["prompt"].startswith("HOUSE RULES")
    assert "No profanity" in ctx["prompt"]

def test_broken_json_skipped(company):
    roster = json.loads((company / "company/roster.json").read_text())
    roster.append({"id":"broken","ad":"Broken","rol":"test","logic":None,"alan":None,"gunler":["wed"],"draft_pr":False})
    (company / "company/roster.json").write_text(json.dumps(roster))
    (company / "company/agents/prompts/broken.md").write_text("test")
    (company / "company/agents/memory/broken.md").write_text("empty")
    p = _run(company, "--agent", "broken", "--day", "wed")
    assert p.returncode == 0
    logs = list((company / "company/log").glob("*.log"))
    assert logs and "broken" in logs[0].read_text()

def test_editor_agent(company):
    p = _run(company, "--agent", "designer", "--day", "tue")
    assert p.returncode == 0, p.stderr
    assert (company / "site/theme-mock.css").exists()
    q = json.loads((company / "out/pr_queue.json").read_text())
    assert q[-1]["draft"] is True and "purple" in q[-1]["body"]

def test_editor_area_guard(company):
    bad = {"[AGENT:webdev]": {"files":{"kernel/runner.py":"x"},"rationale":"malicious intent here","hallway":None}}
    (company / "bad.json").write_text(json.dumps(bad))
    p = _run(company, "--agent", "webdev", "--day", "wed",
             extra_env={"MOCK_ANSWERS": str(company / "bad.json")})
    assert p.returncode == 0
    assert (company / "kernel/runner.py").read_text() != "x"
    assert list((company / "company/log").glob("*.log"))
