"""Provider chain health check — IMMUTABLE KERNEL (constitution art. 1).

Usage:  python kernel/healthcheck.py        (exit 0 = every link answered, 1 = a link is down)

Providers retire models without notice. When that happens every shift fails and the
company goes quiet for the same reason every day, so the daily log says only that the
shift was skipped. This probes each link of company/models.json directly and names the
provider AND the model, which is the part that actually needs changing.

A failing link is written to company/log/<date>.log, the same place shift failures go.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import llm
import runner

PING_SYSTEM = "You are a health probe. Answer with the single word: ok"
PING_USER = "ping"


def check(root):
    """Returns (ok, report_lines) — one line per link in the chain."""
    chain = json.loads((root / "company/models.json").read_text(encoding="utf-8"))["zincir"]
    lines, healthy = [], 0
    for step in chain:
        provider, model = step["saglayici"], step["model"]
        key = os.environ.get(llm.KEYS.get(provider, ""), "")
        if not key:
            lines.append(f"{provider} [{model}]: no API key in the environment")
            continue
        try:
            llm._call(step, key, PING_SYSTEM, PING_USER, False)
            healthy += 1
            lines.append(f"{provider} [{model}]: ok")
        except Exception as e:
            lines.append(f"{llm._detail(provider, e)} [model: {model}]")
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
    runner.log(root, "provider chain health: " + " | ".join(lines))
    return 1


if __name__ == "__main__":
    sys.exit(main())
