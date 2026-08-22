"""Provider chain health check — IMMUTABLE KERNEL (constitution art. 1).

Usage:  python kernel/healthcheck.py        (exit 0 = every link answered, 1 = a link is down)

Providers retire models without notice. When that happens every shift fails and the
company goes quiet for the same reason every day, so the daily log says only that the
shift was skipped. This probes each link of company/models.json directly and names the
provider AND the model, which is the part that actually needs changing.

A failing link is written to company/log/<date>.log, the same place shift failures go.

When the failure says the MODEL is gone rather than that the provider is busy, the
check goes one step further and repoints the link at a model the provider still
offers, writing the new name into company/models.json. Nobody is watching this
company; a chain that can only report its own death outlives its usefulness the
first time a free tier retires a model name.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import llm
import runner

# The probe asks for JSON exactly like a real shift does, so that a provider which
# accepts plain chat but rejects JSON mode is still caught. The word "json" has to
# appear in the message itself: Groq refuses response_format=json_object without it.
PING_SYSTEM = "You are a health probe. Answer in JSON."
PING_USER = 'Reply with this JSON object and nothing else: {"ok": true}'


RETRY_SEC = 5


# What a provider says when a model name has been retired, as opposed to when the
# account is over quota or the service is busy. Only the first kind is repairable,
# and confusing the two would let a rate-limited Sunday rewrite the chain.
MODEL_GONE = ("model_not_found", "no longer available", "does not exist",
              "decommissioned", "deprecated", "unknown model", "not found")


def _probe(step, key):
    """Returns (error, body) — (None, "") if the link answered.

    Retries once on 429/5xx. A provider under load is not a retired model, and a
    report that cries wolf every Sunday is a report nobody reads.

    The body is read here, once, because an HTTPError can only be read once and
    both the report and the repair need it.
    """
    last, body = None, ""
    for attempt in (1, 2):
        try:
            llm._call(step, key, PING_SYSTEM, PING_USER, True)
            return None, ""
        except Exception as e:
            last, body = e, ""
            if isinstance(e, urllib.error.HTTPError):
                try:
                    body = e.read().decode("utf-8", "replace")
                except OSError:
                    body = ""
                if attempt == 1 and (e.code == 429 or e.code >= 500):
                    time.sleep(RETRY_SEC)
                    continue
            break
    return last, body


def _line(provider, error, body):
    """The report line, built from a body that has already been read."""
    if isinstance(error, urllib.error.HTTPError):
        head = f"HTTP {error.code} {error.reason} {body[:200]}"
    else:
        head = f"{type(error).__name__}: {error}"
    return llm._scrub(f"{provider}: {head}".strip()).replace("\n", " ")


def _model_is_gone(error, body):
    """True only when the provider is saying the model itself is no longer served."""
    if not isinstance(error, urllib.error.HTTPError):
        return False
    if error.code == 404:
        return True
    if error.code == 400:
        low = body.lower()
        return any(phrase in low for phrase in MODEL_GONE)
    # 401 wrong key, 402 out of quota, 429 busy, 5xx down — none of these mean the
    # model is gone, and none of them may be allowed to rewrite the chain.
    return False


def _available(step, key):
    """Model names the provider currently offers, sorted. Empty if the list is unreadable."""
    url = step.get("models_url")
    if not url:
        return []
    request = urllib.request.Request(
        url.replace("{key}", key),
        headers={"User-Agent": llm.USER_AGENT, "Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(request, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return []
    if step["style"] == "gemini":
        names = [m.get("name", "").split("/")[-1] for m in data.get("models", [])]
    else:
        names = [m.get("id", "") for m in data.get("data", [])]
    return sorted(n for n in names if n)


def _pick(names, prefer, avoid):
    """Deterministic choice, and a fence.

    When a link states model_prefer, those substrings are a REQUIREMENT and not
    merely an order: nothing outside them is eligible. The chain is made of free
    tiers, and a provider whose catalogue is mostly paid — OpenRouter lists both,
    separated only by a ':free' suffix — would otherwise be repointed at a model
    that quietly starts charging. No match means no change.
    """
    if prefer:
        for wanted in prefer:
            for name in names:
                if wanted in name and name != avoid:
                    return name
        return None
    return next((name for name in names if name != avoid), None)


def repair(root, step, key, error, body):
    """Repoint a link whose model the provider has retired. Returns the new name or None."""
    if not _model_is_gone(error, body):
        return None
    replacement = _pick(_available(step, key), step.get("model_prefer") or [], step["model"])
    if not replacement:
        return None
    path = Path(root) / "company/models.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    for link in document["zincir"]:
        if link["saglayici"] == step["saglayici"]:
            link["model"] = replacement
    path.write_text(json.dumps(document, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return replacement


def check(root):
    """Returns (ok, report_lines) — one line per link in the chain."""
    chain = llm.chain(root)
    lines, healthy = [], 0
    for step in chain:
        provider, model = step["saglayici"], step["model"]
        key = os.environ.get(step["key_env"], "")
        if not key:
            lines.append(f"{provider} [{model}]: no API key in the environment")
            continue
        err, body = _probe(step, key)
        if err is None:
            healthy += 1
            lines.append(f"{provider} [{model}]: ok")
            continue
        line = f"{_line(provider, err, body)} [model: {model}]"
        replacement = repair(root, step, key, err, body)
        if replacement:
            line += f" -> repointed to {replacement}"
        lines.append(line)
    return healthy == len(chain) and healthy > 0, lines


def main():
    root = Path.cwd()
    if os.environ.get("MOCK_LLM") == "1":
        print("mock mode: the chain is not probed")
        return 0
    ok, lines = check(root)
    for line in lines:
        print(line)
    if ok:
        return 0
    runner.log(root, "provider chain health: " + " | ".join(lines), "health")
    return 1


if __name__ == "__main__":
    sys.exit(main())
