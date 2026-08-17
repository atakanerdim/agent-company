"""LLM sağlayıcı zinciri — DOKUNULMAZ ÇEKİRDEK (anayasa md. 1).

chat(sistem, user, cevap_json=False, kok=Path(".")) -> str
Zincir company/models.json'dan okunur; 429/5xx/ağ hatasında sıradakine düşer.
MOCK_LLM=1 iken MOCK_CEVAPLAR dosyasından anahtar-eşleşmeli yanıt döner.
"""
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

ANAHTARLAR = {"groq": "GROQ_API_KEY", "gemini": "GEMINI_API_KEY", "openrouter": "OPENROUTER_API_KEY"}
TABANLAR = {
    "groq": "https://api.groq.com/openai/v1/chat/completions",
    "openrouter": "https://openrouter.ai/api/v1/chat/completions",
}


class TumSaglayicilarDustu(Exception):
    pass


def _mock(user):
    yol = os.environ.get("MOCK_CEVAPLAR", "tests/mock_cevaplar.json")
    try:
        harita = json.loads(Path(yol).read_text(encoding="utf-8"))
    except OSError:
        harita = {}
    for anahtar, deger in harita.items():
        if anahtar in user:
            return deger if isinstance(deger, str) else json.dumps(deger, ensure_ascii=False)
    return json.dumps({"cikti_markdown": "mock", "koridor": None, "hafiza_ekle": None})


def _istek(url, govde, basliklar):
    veri = json.dumps(govde).encode("utf-8")
    basliklar = {"Content-Type": "application/json", **basliklar}
    req = urllib.request.Request(url, data=veri, headers=basliklar, method="POST")
    with urllib.request.urlopen(req, timeout=90) as yanit:
        return json.loads(yanit.read().decode("utf-8"))


def _cagri(adim, anahtar, sistem, user, cevap_json):
    saglayici, model = adim["saglayici"], adim["model"]
    if saglayici == "gemini":
        url = ("https://generativelanguage.googleapis.com/v1beta/models/"
               f"{model}:generateContent?key={anahtar}")
        govde = {"contents": [{"parts": [{"text": sistem + "\n\n" + user}]}]}
        if cevap_json:
            govde["generationConfig"] = {"response_mime_type": "application/json"}
        cevap = _istek(url, govde, {})
        return cevap["candidates"][0]["content"]["parts"][0]["text"]
    govde = {
        "model": model,
        "messages": [{"role": "system", "content": sistem}, {"role": "user", "content": user}],
        "temperature": 0.8,
    }
    if cevap_json:
        govde["response_format"] = {"type": "json_object"}
    cevap = _istek(TABANLAR[saglayici], govde, {"Authorization": f"Bearer {anahtar}"})
    return cevap["choices"][0]["message"]["content"]


def chat(sistem, user, cevap_json=False, kok=Path(".")):
    if os.environ.get("MOCK_LLM") == "1":
        return _mock(user)
    zincir = json.loads((Path(kok) / "company/models.json").read_text(encoding="utf-8"))["zincir"]
    for adim in zincir:
        anahtar = os.environ.get(ANAHTARLAR.get(adim["saglayici"], ""), "")
        if not anahtar:
            continue
        try:
            return _cagri(adim, anahtar, sistem, user, cevap_json)
        except urllib.error.HTTPError as h:
            if h.code == 429 or h.code >= 500:
                time.sleep(2)
                continue
            raise
        except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError):
            time.sleep(2)
            continue
    raise TumSaglayicilarDustu("zincirdeki hiçbir sağlayıcı yanıt vermedi")
