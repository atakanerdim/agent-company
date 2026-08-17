"""Editor: agents that edit files within their allowed area (designer, webdev, process)."""
import json
from pathlib import Path

SAMPLE_FILE_LIMIT = 8
CONTENT_LIMIT = 5000


def _current(root, areas):
    parts = []
    for area in areas:
        target = root / area
        paths = [target] if target.is_file() else sorted(target.rglob("*"))
        for p in paths:
            if p.is_file() and p.suffix in (".css", ".html", ".js", ".md") \
               and len(parts) < SAMPLE_FILE_LIMIT:
                rel = p.relative_to(root).as_posix()
                if rel.startswith("site/data/"):
                    continue  # build output, not a source file
                parts.append(f"--- {rel} ---\n{p.read_text(encoding='utf-8')[:CONTENT_LIMIT]}")
    return "\n".join(parts)


def run(agent, ctx, chat, root):
    areas = agent["alan"]
    task = ("Revise your draft taking the feedback into account." if ctx["mode"] == "revision"
            else "Make ONE concrete improvement to the files in your area.")
    user = (f"[AGENT:{agent['id']}][MODE:{ctx['mode']}][DAY:{ctx['day']}]\n"
            f"Your memory:\n{ctx['memory']}\n\nHallway:\n{ctx['hallway']}\n\n"
            f"Areas you may edit: {', '.join(areas)}\n\n"
            f"Current files:\n{_current(root, areas)}\n\n"
            + (f"Feedback received:\n{ctx['input']}\n\n" if ctx["input"] else "")
            + f"{task} At most 3 files, each with its FULL new content. "
            'ANSWER ONLY with this JSON object: {"files": {"path": "full content"}, '
            '"rationale": "why you changed it", "hallway": "one line or null"}')

    last = None
    for _ in range(3):
        try:
            raw = chat(ctx["prompt"], user, want_json=True, root=root).strip()
            if raw.startswith("```"):
                raw = raw.strip("`").lstrip("json").strip()
            obj = json.loads(raw)
            files = obj["files"]
            rationale = obj["rationale"]
            if not isinstance(files, dict) or not files or len(files) > 3:
                raise ValueError("must edit 1-3 files")
            if not isinstance(rationale, str) or len(rationale.strip()) < 10:
                raise ValueError("rationale required (constitution art. 3)")
            for path in files:
                if ".." in path or path.startswith("/") or \
                   not any(path.startswith(a.rstrip("/")) if (root / a).is_file()
                           else path.startswith(a) for a in areas):
                    raise ValueError(f"path outside area: {path}")
            return {"files": files,
                    "pr": {"title": f"{agent['id']}: edit {ctx['date']}",
                           "body": f"Rationale: {rationale}", "draft": agent["draft_pr"]},
                    "hallway": obj.get("hallway"), "memory_add": None}
        except (json.JSONDecodeError, ValueError, KeyError, TypeError) as e:
            last = e
    raise ValueError(f"editor produced no valid edit in 3 attempts: {last}")
