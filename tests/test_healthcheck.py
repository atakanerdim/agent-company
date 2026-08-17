import io, json, os, subprocess, sys, urllib.error

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

def _hc(company):
    sys.path.insert(0, str(company / "kernel"))
    import importlib, healthcheck
    importlib.reload(healthcheck)
    return healthcheck

def _http(code):
    return urllib.error.HTTPError("https://x", code, "boom", {}, io.BytesIO(b"busy"))

def test_transient_failure_is_retried(company, monkeypatch):
    """503 means the provider is busy, not that the model is gone. Retry before reporting."""
    hc = _hc(company)
    calls = []
    def flaky(step, key, system, user, want_json):
        calls.append(1)
        if len(calls) == 1: raise _http(503)
        return '{"ok": true}'
    monkeypatch.setattr(hc.llm, "_call", flaky)
    monkeypatch.setattr(hc.time, "sleep", lambda s: None)
    assert hc._probe({"saglayici": "groq", "model": "m"}, "k") is None
    assert len(calls) == 2, "a transient failure must be retried exactly once"

def test_dead_model_is_not_retried(company, monkeypatch):
    """404 means the model is retired. Retrying wastes the shift's time budget."""
    hc = _hc(company)
    calls = []
    def gone(step, key, system, user, want_json):
        calls.append(1); raise _http(404)
    monkeypatch.setattr(hc.llm, "_call", gone)
    monkeypatch.setattr(hc.time, "sleep", lambda s: None)
    err = hc._probe({"saglayici": "groq", "model": "m"}, "k")
    assert isinstance(err, urllib.error.HTTPError) and err.code == 404
    assert len(calls) == 1, "a permanent failure must not be retried"

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
