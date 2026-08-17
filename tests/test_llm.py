import io, json, os, urllib.error
import pytest
import llm


def test_mock_deterministik(monkeypatch):
    monkeypatch.setenv("MOCK_LLM", "1")
    monkeypatch.setenv("MOCK_CEVAPLAR", os.path.join(os.path.dirname(__file__), "mock_cevaplar.json"))
    c = llm.chat("sistem", "[AJAN:analist] görev")
    assert "Mock brifing" in c
    c2 = llm.chat("sistem", "[LIG:PL] maçlar")
    assert json.loads(c2)[0]["mac_id"] == 1001


class SahteYanit:
    def __init__(self, govde): self.govde = govde.encode()
    def read(self): return self.govde
    def __enter__(self): return self
    def __exit__(self, *a): return False


def _hata(kod):
    return urllib.error.HTTPError("u", kod, "hata", {}, io.BytesIO(b""))


def test_zincir_dusme(monkeypatch, tmp_path):
    monkeypatch.delenv("MOCK_LLM", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "x")
    monkeypatch.setenv("GEMINI_API_KEY", "y")
    monkeypatch.setenv("OPENROUTER_API_KEY", "z")
    sira = []
    def sahte(req, timeout=0):
        sira.append(req.full_url)
        if len(sira) == 1: raise _hata(429)
        return SahteYanit(json.dumps({"candidates":[{"content":{"parts":[{"text":"gemini cevap"}]}}]}))
    monkeypatch.setattr(llm.urllib.request, "urlopen", sahte)
    out = llm.chat("s", "u", kok=llm.Path(__file__).resolve().parents[1])
    assert out == "gemini cevap" and len(sira) == 2


def test_hepsi_duserse(monkeypatch):
    monkeypatch.delenv("MOCK_LLM", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "x")
    monkeypatch.setenv("GEMINI_API_KEY", "y")
    monkeypatch.setenv("OPENROUTER_API_KEY", "z")
    monkeypatch.setattr(llm.urllib.request, "urlopen", lambda r, timeout=0: (_ for _ in ()).throw(_hata(500)))
    with pytest.raises(llm.TumSaglayicilarDustu):
        llm.chat("s", "u", kok=llm.Path(__file__).resolve().parents[1])
