import json, os, subprocess, sys

def _run(company, extra_env=None):
    env = dict(os.environ, SHIFT_DATE="2026-08-23")
    env.pop("MOCK_LLM", None)          # the probe must be able to reach the network path
    for k in ("GROQ_API_KEY", "GEMINI_API_KEY", "OPENROUTER_API_KEY"):
        env.pop(k, None)
    if extra_env: env.update(extra_env)
    return subprocess.run([sys.executable, str(company / "kernel/healthcheck.py")],
                          cwd=company, env=env, capture_output=True, text=True)

def test_missing_keys_reported_per_link(company):
    """No keys at all: every link is named, nothing is silently skipped."""
    p = _run(company)
    assert p.returncode == 1, "a dead chain must report failure"
    chain = json.loads((company / "company/models.json").read_text())["zincir"]
    for step in chain:
        assert step["saglayici"] in p.stdout
        assert step["model"] in p.stdout, "the report must name the model, not just the provider"
    logs = list((company / "company/log").glob("*.log"))
    assert any("provider chain health" in f.read_text(encoding="utf-8") for f in logs)

def test_mock_mode_does_not_probe(company):
    """CI runs with MOCK_LLM=1 and must never touch the network."""
    p = _run(company, extra_env={"MOCK_LLM": "1"})
    assert p.returncode == 0
    assert "not probed" in p.stdout

def test_json_contracts_say_the_word_json(company):
    """Groq refuses response_format=json_object unless 'json' appears in the messages.

    Every prompt that asks for JSON must therefore say so out loud. Dropping the word
    is an easy edit to make and produces a 400 that looks nothing like its cause.
    """
    sources = ["kernel/runner.py", "kernel/healthcheck.py"] + \
              [f"company/agents/logic/{n}.py" for n in ("analyst", "evaluator", "predictor", "editor")]
    checked = 0
    for rel in sources:
        text = (company / rel).read_text(encoding="utf-8")
        for n, after in enumerate(text.split("ANSWER ONLY")[1:], 1):
            assert "json" in after[:400].lower(), f"{rel}: contract #{n} never says 'json'"
            checked += 1
    assert checked >= 5, "the contracts moved; this guard is no longer looking at them"
    probe = (company / "kernel/healthcheck.py").read_text(encoding="utf-8")
    assert "json" in probe.split("PING_USER =")[1][:200].lower(), \
        "the health probe itself must say 'json' or Groq rejects it"
