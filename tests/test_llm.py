import io, json, os, urllib.error
import pytest
import llm


def test_mock_deterministic(monkeypatch):
    monkeypatch.setenv("MOCK_LLM", "1")
    monkeypatch.setenv("MOCK_ANSWERS", os.path.join(os.path.dirname(__file__), "mock_answers.json"))
    c = llm.chat("system", "[AGENT:analyst] task")
    assert "Mock briefing" in c
    c2 = llm.chat("system", "[LEAGUE:PL] matches")
    assert json.loads(c2)[0]["match_id"] == 1001


class FakeResp:
    def __init__(self, body): self.body = body.encode()
    def read(self): return self.body
    def __enter__(self): return self
    def __exit__(self, *a): return False


def _err(code):
    return urllib.error.HTTPError("u", code, "err", {}, io.BytesIO(b""))


def test_chain_fallback(monkeypatch):
    monkeypatch.delenv("MOCK_LLM", raising=False)
    for k in ("GROQ_API_KEY", "GEMINI_API_KEY", "OPENROUTER_API_KEY"):
        monkeypatch.setenv(k, "x")
    calls = []
    def fake(req, timeout=0):
        calls.append(req.full_url)
        if len(calls) == 1: raise _err(429)
        return FakeResp(json.dumps({"candidates":[{"content":{"parts":[{"text":"gemini answer"}]}}]}))
    monkeypatch.setattr(llm.urllib.request, "urlopen", fake)
    out = llm.chat("s", "u", root=llm.Path(__file__).resolve().parents[1])
    assert out == "gemini answer" and len(calls) == 2


@pytest.fixture
def instant(monkeypatch):
    """Same logic, no waiting — the pauses are what the retry costs in production."""
    monkeypatch.setattr(llm, "BACKOFF_SEC", (0, 0, 0))
    monkeypatch.setattr(llm, "GAP_SEC", 0)


def _keys(monkeypatch):
    monkeypatch.delenv("MOCK_LLM", raising=False)
    for k in ("GROQ_API_KEY", "GEMINI_API_KEY", "OPENROUTER_API_KEY"):
        monkeypatch.setenv(k, "x")


def test_all_down(monkeypatch, instant):
    _keys(monkeypatch)
    monkeypatch.setattr(llm.urllib.request, "urlopen", lambda r, timeout=0: (_ for _ in ()).throw(_err(500)))
    with pytest.raises(llm.AllProvidersDown):
        llm.chat("s", "u", root=llm.Path(__file__).resolve().parents[1])


def test_every_request_identifies_itself(monkeypatch):
    """A bare Python-urllib User-Agent is what bot protection answers with 403."""
    monkeypatch.delenv("MOCK_LLM", raising=False)
    seen = {}
    def fake(req, timeout=0):
        seen.update(req.headers)
        return FakeResp(json.dumps({"choices": [{"message": {"content": "ok"}}]}))
    monkeypatch.setattr(llm.urllib.request, "urlopen", fake)
    llm._call({"saglayici": "groq", "model": "m"}, "k", "s", "u", False)
    agent = seen.get("User-agent", "")
    assert agent.startswith("agent-company/") and "urllib" not in agent


def test_a_busy_chain_is_walked_again(monkeypatch, instant):
    """Both providers said 'temporary, retry shortly' — so retry, and take the answer."""
    _keys(monkeypatch)
    calls = []
    def fake(req, timeout=0):
        calls.append(req.full_url)
        if len(calls) <= 3:                      # first pass: everyone is busy
            raise _err(429 if len(calls) == 1 else 503)
        return FakeResp(json.dumps({"choices": [{"message": {"content": "second pass"}}]}))
    monkeypatch.setattr(llm.urllib.request, "urlopen", fake)
    out = llm.chat("s", "u", root=llm.Path(__file__).resolve().parents[1])
    assert out == "second pass" and len(calls) == 4


def test_a_dead_chain_is_not_walked_again(monkeypatch, instant):
    """404 means the model was retired. Waiting will not bring it back, and the
    shift has a time budget to spend on things that might work."""
    _keys(monkeypatch)
    calls = []
    def fake(req, timeout=0):
        calls.append(req.full_url)
        raise _err(404)
    monkeypatch.setattr(llm.urllib.request, "urlopen", fake)
    with pytest.raises(llm.AllProvidersDown) as caught:
        llm.chat("s", "u", root=llm.Path(__file__).resolve().parents[1])
    assert len(calls) == 3, "a permanent failure must not be retried"
    assert "groq" in str(caught.value) and "gemini" in str(caught.value)
