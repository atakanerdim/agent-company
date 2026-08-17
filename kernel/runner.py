"""Shift runner — IMMUTABLE KERNEL (constitution art. 1).

Usage:
  python kernel/runner.py --list --day fri
  python kernel/runner.py --agent gossip --day wed
  python kernel/runner.py --agent designer --day sat --mode revision --input out/comments.txt
  python kernel/runner.py --day fri            (every agent on duty, in roster order)

Result contract (logic modules and the generic flow):
  {"files": {path: content}, "pr": {"title","body","draft"}|None,
   "hallway": str|None, "memory_add": str|None}
"""
import argparse
import datetime as dt
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import llm

HOUSE_RULES = """HOUSE RULES — enforced by the immutable kernel, they outrank your persona:
- Write in English only.
- No profanity, slurs, sexual content, threats, or harassment. The tone is witty office banter, never abuse.
- Real people (players, coaches, referees) may be discussed only in the context of match performance. Never invent scandals, injuries, quotes, or personal claims about real people.
- No personal data about anyone. No politics, no religion.
- Predictions are entertainment only, never betting or financial advice. Betting language is forbidden.
- Never write API keys, tokens, or secrets into any file.
"""

GENERIC_CONTRACT = ('ANSWER ONLY with this JSON object: '
                    '{"output_markdown": "your shift output (markdown)", '
                    '"hallway": "the ONE line you leave in the hallway, or null", '
                    '"memory_add": "a short note to append to your memory, or null"}')
COMMENT_CONTRACT = 'ANSWER ONLY with this JSON object: {"comment": "your review of the change"}'


def shift_date():
    return os.environ.get("SHIFT_DATE") or dt.date.today().isoformat()


def log(root, message):
    path = root / "company/log" / f"{shift_date()}.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"[{dt.datetime.utcnow().isoformat(timespec='seconds')}] {message}\n")


def build_ctx(root, agent, day, mode, input_path):
    read = lambda p: (root / p).read_text(encoding="utf-8") if (root / p).exists() else ""
    lines = sorted((root / "company/hallway").glob("*.txt"))[-10:]
    hallway = "\n".join(l.read_text(encoding="utf-8").strip() for l in lines)
    extra = read(input_path) if input_path else ""
    return {"prompt": HOUSE_RULES + "\n" + read(f"company/agents/prompts/{agent['id']}.md"),
            "memory": read(f"company/agents/memory/{agent['id']}.md"),
            "hallway": hallway, "day": day, "mode": mode, "input": extra[:6000],
            "date": shift_date()}


def _ask_json(system, user, root, validate):
    """Asks the LLM for JSON; 3 attempts; validate(obj) -> obj or raises ValueError."""
    last = None
    for _ in range(3):
        raw = llm.chat(system, user, want_json=True, root=root)
        try:
            clean = raw.strip()
            if clean.startswith("```"):
                clean = clean.strip("`").lstrip("json").strip()
            return validate(json.loads(clean))
        except (json.JSONDecodeError, ValueError, KeyError, TypeError) as e:
            last = e
    raise ValueError(f"no valid JSON in 3 attempts: {last}")


def generic(root, agent, ctx):
    tag = f"[AGENT:{agent['id']}][MODE:{ctx['mode']}][DAY:{ctx['day']}]"
    user = (f"{tag}\nDate: {ctx['date']}\n\nYour memory:\n{ctx['memory']}\n\n"
            f"Last hallway lines:\n{ctx['hallway']}\n\n")
    if ctx["mode"] == "comment":
        user += f"Change under review:\n{ctx['input']}\n\n{COMMENT_CONTRACT}"
        obj = _ask_json(ctx["prompt"], user, root,
                        lambda o: o if isinstance(o.get("comment"), str) else _bad())
        return {"files": {f"out/comment-{agent['id']}.txt": obj["comment"]},
                "pr": None, "hallway": None, "memory_add": None}
    user += f"Do today's shift.\n\n{GENERIC_CONTRACT}"

    def validate(o):
        if not isinstance(o.get("output_markdown"), str):
            raise ValueError("output_markdown missing")
        return o

    obj = _ask_json(ctx["prompt"], user, root, validate)
    path = f"company/minutes/{ctx['date']}-{agent['id']}.md"
    content = f"# {agent['ad']} — {ctx['date']}\n\n{obj['output_markdown']}\n"
    return {"files": {path: content},
            "pr": {"title": f"{agent['id']}: shift {ctx['date']}",
                   "body": f"Daily shift output from {agent['ad']}.", "draft": agent["draft_pr"]},
            "hallway": obj.get("hallway"), "memory_add": obj.get("memory_add")}


def _bad():
    raise ValueError("schema mismatch")


def load_logic(root, name):
    path = root / "company/agents/logic" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"logic_{name}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def apply(root, agent, result):
    written = []
    for path, content in (result.get("files") or {}).items():
        if ".." in path or path.startswith("/"):
            raise ValueError(f"invalid path: {path}")
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        written.append(path)
    if result.get("hallway"):
        line = str(result["hallway"]).strip().splitlines()[0][:200]
        (root / "company/hallway" / f"{shift_date()}-{agent['id']}.txt").write_text(
            f"{agent['ad']}: {line}\n", encoding="utf-8")
    if result.get("memory_add"):
        with open(root / f"company/agents/memory/{agent['id']}.md", "a", encoding="utf-8") as f:
            f.write(f"\n- [{shift_date()}] {result['memory_add']}\n")
    pr = result.get("pr")
    if pr and written:
        qpath = root / "out/pr_queue.json"
        qpath.parent.mkdir(exist_ok=True)
        queue = json.loads(qpath.read_text(encoding="utf-8")) if qpath.exists() else []
        queue.append({"agent": agent["id"], "branch": f"shift/{agent['id']}/{shift_date()}",
                      "title": pr["title"], "body": pr["body"], "draft": bool(pr.get("draft"))})
        qpath.write_text(json.dumps(queue, ensure_ascii=False, indent=1), encoding="utf-8")


def run_agent(root, agent, day, mode, input_path):
    """Runs one shift. Returns True if it produced output, False if it was skipped."""
    ctx = build_ctx(root, agent, day, mode, input_path)
    try:
        if agent.get("logic") and mode != "comment":
            result = load_logic(root, agent["logic"]).calis(agent, ctx, llm.chat, root)
        else:
            result = generic(root, agent, ctx)
        apply(root, agent, result)
        print(f"done: {agent['id']}")
        return True
    except Exception as e:  # a shift must never take the company down
        log(root, f"{agent['id']} shift skipped: {type(e).__name__}: {e}")
        print(f"skipped: {agent['id']} ({e})", file=sys.stderr)
        return False


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--day", default=None)
    p.add_argument("--agent", default=None)
    p.add_argument("--mode", default="normal")
    p.add_argument("--input", default=None)
    p.add_argument("--list", action="store_true")
    a = p.parse_args()
    root = Path.cwd()
    day = a.day or dt.date.fromisoformat(shift_date()).strftime("%a").lower()
    roster = json.loads((root / "company/roster.json").read_text(encoding="utf-8"))
    if a.list:
        for ag in roster:
            if day in ag["gunler"]:
                print(ag["id"])
        return
    picked = [ag for ag in roster if ag["id"] == a.agent] if a.agent \
        else [ag for ag in roster if day in ag["gunler"]]
    ok = True
    for ag in picked:
        ok = run_agent(root, ag, day, a.mode, a.input) and ok
        time.sleep(int(os.environ.get("SHIFT_GAP_SEC", "0")))
    if not ok:
        # The caller must be able to tell a real shift from an error log,
        # otherwise the skipped shift gets committed as if it were output.
        sys.exit(1)


if __name__ == "__main__":
    main()
