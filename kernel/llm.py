"""LLM provider chain — IMMUTABLE KERNEL (constitution art. 1).

chat(system, user, want_json=False, root=Path(".")) -> str
Chain is read from company/models.json. A provider that fails for ANY reason is
skipped and the next one is tried; only when every provider has failed does the
call raise AllProvidersDown, carrying one line per provider so the shift log says
which one refused and why. Secrets are redacted from those lines.

If a whole pass fails and at least one of those failures was *transient* — a 429,
a 5xx, a dropped connection — the chain is walked again after a pause. Every link
of this chain is a free tier, and free tiers say "temporarily rate-limited, retry
shortly" at exactly the moment every cron job in the world fires at once. Walking
the chain once and giving up turns a busy minute into a lost shift.

With MOCK_LLM=1, answers come from the MOCK_ANSWERS file by substring key match.
"""
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

KEYS = {"groq": "GROQ_API_KEY", "gemini": "GEMINI_API_KEY", "openrouter": "OPENROUTER_API_KEY"}
BASES = {
    "groq": "https://api.groq.com/openai/v1/chat/completions",
    "openrouter": "https://openrouter.ai/api/v1/chat/completions",
}


# A request with no User-Agent is sent as "Python-urllib/3.x", which the bot
# protection in front of some provider APIs answers with a flat 403 — and only from
# datacentre addresses, so it never reproduces on a laptop. Identify the caller.
USER_AGENT = "agent-company/1.0 (+https://github.com/atakanerdim/agent-company)"

# Time budget when everything is down: three passes, and inside a pass a short gap
# between providers. Tests set these to zero.
BACKOFF_SEC = (0, 15, 45)
GAP_SEC = 2


class AllProvidersDown(Exception):
    pass


SECRET = re.compile(r"(gsk_|sk-or-|AIza|github_pat_|ghp_)[A-Za-z0-9_\-]{6,}|key=[^&\s\"']+")


def _scrub(text):
    """Provider error bodies end up in company/log — never let a key ride along."""
    return SECRET.sub("***", str(text))


def _detail(provider, error):
    body = ""
    if isinstance(error, urllib.error.HTTPError):
        head = f"HTTP {error.code} {error.reason}"
        try:
            body = " " + error.read().decode("utf-8", "replace")[:200]
        except OSError:
            body = ""
    else:
        head = f"{type(error).__name__}: {error}"
    return _scrub(f"{provider}: {head}{body}".strip()).replace("\n", " ")


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


def _transient(error):
    """Worth trying again, as opposed to worth reporting.

    A 404 means the model is gone and a 401 means the key is wrong; waiting does not
    help either. A 429 or a 5xx or a dropped connection means the provider is busy.
    """
    if isinstance(error, urllib.error.HTTPError):
        return error.code == 429 or error.code >= 500
    return isinstance(error, (urllib.error.URLError, TimeoutError))


def _request(url, body, headers):
    data = json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json", "User-Agent": USER_AGENT, **headers}
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
    failures = []
    for pause in BACKOFF_SEC:
        if pause:
            time.sleep(pause)
        failures, worth_retrying = [], False
        for step in chain:
            provider = step["saglayici"]
            key = os.environ.get(KEYS.get(provider, ""), "")
            if not key:
                failures.append(f"{provider}: no API key in the environment")
                continue
            try:
                return _call(step, key, system, user, want_json)
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError,
                    KeyError, json.JSONDecodeError) as e:
                # Every failure falls through — a chain that stops at the first bad
                # provider is not a fallback chain at all.
                failures.append(_detail(provider, e))
                worth_retrying = worth_retrying or _transient(e)
            time.sleep(GAP_SEC)
        if not worth_retrying:
            break
    raise AllProvidersDown("; ".join(failures) or "the provider chain is empty")
