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
    err, _ = hc._probe({"saglayici": "groq", "model": "m", "style": "openai",
                "url": "https://example.invalid/v1/chat/completions",
                "key_env": "GROQ_API_KEY"}, "k")
    assert err is None
    assert len(calls) == 2, "a transient failure must be retried exactly once"

def test_dead_model_is_not_retried(company, monkeypatch):
    """404 means the model is retired. Retrying wastes the shift's time budget."""
    hc = _hc(company)
    calls = []
    def gone(step, key, system, user, want_json):
        calls.append(1); raise _http(404)
    monkeypatch.setattr(hc.llm, "_call", gone)
    monkeypatch.setattr(hc.time, "sleep", lambda s: None)
    err, _body = hc._probe({"saglayici": "groq", "model": "m", "style": "openai",
                "url": "https://example.invalid/v1/chat/completions",
                "key_env": "GROQ_API_KEY"}, "k")
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


# ---------------------------------------------------------------------------
# Repointing a retired model. Nobody is watching this company, so a chain that can
# only report its own death is a chain that dies the first time a free tier prunes
# its catalogue. The line between "the model is gone" and "we are over quota" is the
# whole safety of this feature: the second must never rewrite the chain.
# ---------------------------------------------------------------------------

def _step(**over):
    step = {"saglayici": "groq", "model": "old-model", "style": "openai",
            "url": "https://example.invalid/v1/chat/completions",
            "key_env": "GROQ_API_KEY",
            "models_url": "https://example.invalid/v1/models",
            "model_prefer": ["gpt-oss", "llama"]}
    step.update(over)
    return step


def _body_http(code, body):
    return urllib.error.HTTPError("https://x", code, "boom", {}, io.BytesIO(body.encode()))


def _model_of(company, provider="groq"):
    chain = json.loads((company / "company/models.json").read_text(encoding="utf-8"))["zincir"]
    return next(l["model"] for l in chain if l["saglayici"] == provider)


def test_a_retired_model_is_replaced_from_the_provider_list(company, monkeypatch):
    hc = _hc(company)
    monkeypatch.setattr(hc, "_available",
                        lambda step, key: ["llama-3.3-70b", "openai/gpt-oss-120b", "whisper-1"])
    new = hc.repair(company, _step(), "k", _body_http(404, "not found"), "not found")
    assert new == "openai/gpt-oss-120b", "the preference list decides, in order"
    assert _model_of(company) == "openai/gpt-oss-120b", "the chain on disk must be updated"


def test_being_over_quota_or_busy_never_rewrites_the_chain(company, monkeypatch):
    """402, 429 and 5xx are about the account and the hour, not about the model."""
    hc = _hc(company)
    monkeypatch.setattr(hc, "_available", lambda step, key: ["some-other-model"])
    before = _model_of(company)
    for code, body in ((402, "Payment required to access this resource"),
                       (429, "rate limited"),
                       (503, "high demand"),
                       (401, "invalid api key")):
        assert hc.repair(company, _step(), "k", _body_http(code, body), body) is None
        assert _model_of(company) == before, f"HTTP {code} must leave the chain alone"


def test_a_400_is_repaired_only_when_it_names_the_model(company, monkeypatch):
    hc = _hc(company)
    monkeypatch.setattr(hc, "_available", lambda step, key: ["openai/gpt-oss-120b"])
    before = _model_of(company)
    assert hc.repair(company, _step(), "k",
                     _body_http(400, "messages must contain the word json"),
                     "messages must contain the word json") is None
    assert _model_of(company) == before
    assert hc.repair(company, _step(), "k",
                     _body_http(400, '{"error":{"code":"model_not_found"}}'),
                     '{"error":{"code":"model_not_found"}}') == "openai/gpt-oss-120b"


def test_an_unreadable_model_list_changes_nothing(company, monkeypatch):
    """A provider that will not list its models is not an invitation to guess."""
    hc = _hc(company)
    monkeypatch.setattr(hc, "_available", lambda step, key: [])
    before = _model_of(company)
    assert hc.repair(company, _step(), "k", _body_http(404, "gone"), "gone") is None
    assert _model_of(company) == before


def test_the_replacement_is_never_the_model_that_just_died(company, monkeypatch):
    hc = _hc(company)
    monkeypatch.setattr(hc, "_available", lambda step, key: ["old-model"])
    before = _model_of(company)
    assert hc.repair(company, _step(model="old-model"), "k",
                     _body_http(404, "gone"), "gone") is None
    assert _model_of(company) == before


def test_a_link_with_no_model_list_is_left_alone(company):
    """models_url is optional; a link without one simply reports and waits."""
    hc = _hc(company)
    step = _step()
    del step["models_url"]
    assert hc.repair(company, step, "k", _body_http(404, "gone"), "gone") is None


def test_a_catalogue_with_nothing_acceptable_changes_nothing(company, monkeypatch):
    """model_prefer is a fence, not a ranking.

    OpenRouter lists paid and free models side by side, told apart only by a ':free'
    suffix. A chain that falls back to "whatever came first alphabetically" would
    put this company on a paid model without anyone noticing, and the one promise it
    makes about itself is that it costs nothing to run.
    """
    hc = _hc(company)
    monkeypatch.setattr(hc, "_available",
                        lambda step, key: ["anthropic/claude-x", "openai/gpt-5-pro"])
    before = _model_of(company)
    assert hc.repair(company, _step(model_prefer=[":free"]), "k",
                     _body_http(404, "gone"), "gone") is None
    assert _model_of(company) == before


def test_without_a_preference_any_model_will_do(company, monkeypatch):
    hc = _hc(company)
    monkeypatch.setattr(hc, "_available", lambda step, key: ["a-model", "b-model"])
    assert hc.repair(company, _step(model_prefer=[]), "k",
                     _body_http(404, "gone"), "gone") == "a-model"
