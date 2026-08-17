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


def test_all_down(monkeypatch):
    monkeypatch.delenv("MOCK_LLM", raising=False)
    for k in ("GROQ_API_KEY", "GEMINI_API_KEY", "OPENROUTER_API_KEY"):
        monkeypatch.setenv(k, "x")
    monkeypatch.setattr(llm.urllib.request, "urlopen", lambda r, timeout=0: (_ for _ in ()).throw(_err(500)))
    with pytest.raises(llm.AllProvidersDown):
        llm.chat("s", "u", root=llm.Path(__file__).resolve().parents[1])
