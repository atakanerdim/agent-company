"""LLM provider chain — IMMUTABLE KERNEL (constitution art. 1).

chat(system, user, want_json=False, root=Path(".")) -> str
Chain is read from company/models.json; falls through on 429/5xx/network errors.
With MOCK_LLM=1, answers come from the MOCK_ANSWERS file by substring key match.
"""
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

KEYS = {"groq": "GROQ_API_KEY", "gemini": "GEMINI_API_KEY", "openrouter": "OPENROUTER_API_KEY"}
BASES = {
    "groq": "https://api.groq.com/openai/v1/chat/completions",
    "openrouter": "https://openrouter.ai/api/v1/chat/completions",
}


class AllProvidersDown(Exception):
    pass


def _mock(user):
    path = os.environ.get("MOCK_ANSWERS", "tests/mock_answers.json")
    try:
        table = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError:
        table = {}
    for key, value in table.items():
        if key in user:
            return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return json.dumps({"output_markdown": "mock", "hallway": None, "memory_add": None})


def _request(url, body, headers):
    data = json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json", **headers}
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=90) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _call(step, key, system, user, want_json):
    provider, model = step["saglayici"], step["model"]
    if provider == "gemini":
        url = ("https://generativelanguage.googleapis.com/v1beta/models/"
               f"{model}:generateContent?key={key}")
        body = {"contents": [{"parts": [{"text": system + "\n\n" + user}]}]}
        if want_json:
            body["generationConfig"] = {"response_mime_type": "application/json"}
        resp = _request(url, body, {})
        return resp["candidates"][0]["content"]["parts"][0]["text"]
    body = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0.8,
    }
    if want_json:
        body["response_format"] = {"type": "json_object"}
    resp = _request(BASES[provider], body, {"Authorization": f"Bearer {key}"})
    return resp["choices"][0]["message"]["content"]


def chat(system, user, want_json=False, root=Path(".")):
    if os.environ.get("MOCK_LLM") == "1":
        return _mock(user)
    chain = json.loads((Path(root) / "company/models.json").read_text(encoding="utf-8"))["zincir"]
    for step in chain:
        key = os.environ.get(KEYS.get(step["saglayici"], ""), "")
        if not key:
            continue
        try:
            return _call(step, key, system, user, want_json)
        except urllib.error.HTTPError as h:
            if h.code == 429 or h.code >= 500:
                time.sleep(2)
                continue
            raise
        except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError):
            time.sleep(2)
            continue
    raise AllProvidersDown("no provider in the chain answered")
