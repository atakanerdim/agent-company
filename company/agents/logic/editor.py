"""Editor: agents that edit files within their allowed area (designer, webdev, process)."""
import datetime as dt
import importlib.util
import json
import os
from pathlib import Path

SAMPLE_FILE_LIMIT = 8
# The editor protocol asks for a file's FULL new content, so a file must never be
# shown in part. On 2026-08-19 this limit was 5000 and site/app.js was 12900 chars:
# the agent was handed the first 5000, asked for the whole file, and honestly
# returned what it had been given. Two thirds of the file were deleted, mid-word.
# A file bigger than this is still shown, but marked unrewritable rather than
# quietly cropped.
CONTENT_LIMIT = 24000
# The same day, site/style.css came back as the four words "/* No changes needed */".
# An answer meant for the human went into the field that becomes the file. A rewrite
# that collapses a file to a fraction of itself is a failure however it is phrased.
SHRINK_FLOOR = 0.6
# On 2026-08-26 the page went dark a second time and SHRINK_FLOOR never fired,
# because the rewrite did not shrink the file — it grew it by 252 bytes while
# turning a quote into an escape. Size says nothing about whether a file runs.
# validate.check answers the only question that does: does it still parse.


def _validator(root):
    """Logic modules are loaded by path, not as a package, so import by path too."""
    spec = importlib.util.spec_from_file_location(
        "logic_validate", root / "company/agents/logic/validate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _current(root, areas, seed=0):
    """Return the sample text plus the paths that must not be rewritten.

    Unrewritable means one of two things, and the agent is told which: the file was
    shown in part because it is longer than CONTENT_LIMIT, or it was not shown at
    all because the area holds more than SAMPLE_FILE_LIMIT files. Both end the same
    way if left alone — an agent hands back a file it never read in full, and the
    difference is deleted.
    """
    candidates = []
    for area in areas:
        target = root / area
        paths = [target] if target.is_file() else sorted(target.rglob("*"))
        for p in paths:
            # .json belongs here because an agent's area can be a data file — the
            # wardrobe, for instance — and an editor that cannot see the current
            # value rewrites it from nothing.
            if p.is_file() and p.suffix in (".css", ".html", ".js", ".md", ".json"):
                rel = p.relative_to(root).as_posix()
                if rel.startswith("site/data/"):
                    continue  # build output, not a source file
                candidates.append((rel, p))

    # An area can hold far more files than fit in one prompt — the Process Owner
    # tends twelve prompts and twelve memories. Showing the same first eight every
    # week would make the rest unreachable for good, so the window turns: over a few
    # shifts every file comes round. What is shown may be rewritten; what is not,
    # may not. Which file an agent may touch changes, but the rule never does.
    if len(candidates) > SAMPLE_FILE_LIMIT:
        offset = (seed * SAMPLE_FILE_LIMIT) % len(candidates)
        candidates = candidates[offset:] + candidates[:offset]

    parts, unrewritable = [], {}
    for rel, p in candidates[:SAMPLE_FILE_LIMIT]:
        body = p.read_text(encoding="utf-8")
        if len(body) > CONTENT_LIMIT:
            unrewritable[rel] = (f"{rel} was shown to you in part only "
                                 f"({CONTENT_LIMIT} of {len(body)} characters), so it "
                                 "cannot be rewritten whole. Edit a different file.")
            parts.append(f"--- {rel} (first {CONTENT_LIMIT} characters of "
                         f"{len(body)}; TOO LONG TO REWRITE, read only) ---\n"
                         f"{body[:CONTENT_LIMIT]}")
        else:
            parts.append(f"--- {rel} ---\n{body}")

    hidden = [rel for rel, _ in candidates[SAMPLE_FILE_LIMIT:]]
    for rel in hidden:
        unrewritable[rel] = (f"{rel} was not shown to you this time, so it cannot be "
                             "rewritten today. Edit one of the files listed above; this "
                             "one comes round on another shift.")

    # Everything else that exists in the area. The sample only ever offers the
    # handful of text suffixes above, so a file of any other kind — site/build.py,
    # for one, which generates the whole site — was invisible to this guard and
    # could be handed back by an agent that had never seen a line of it. The rule
    # was always "what is shown may be rewritten"; this makes the other half of it
    # true. Creating a NEW file is untouched: only a file already on disk can be
    # overwritten blind.
    shown = {rel for rel, _ in candidates[:SAMPLE_FILE_LIMIT]}
    for area in areas:
        target = root / area
        for p in ([target] if target.is_file() else target.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(root).as_posix()
            if rel in shown or rel in unrewritable:
                continue
            if rel.startswith("site/data/"):
                unrewritable[rel] = (f"{rel} is build output, not a source file. It is "
                                     "written by site/build.py on every deploy and anything "
                                     "you put there is overwritten.")
            else:
                unrewritable[rel] = (f"{rel} is not one of the files you were shown, so it "
                                     "cannot be rewritten. Only edit a file whose current "
                                     "contents are in front of you.")
    if hidden:
        parts.append("--- not shown this shift (DO NOT REWRITE; they come round later) ---\n"
                     + "\n".join(hidden))
    return "\n".join(parts), unrewritable


def run(agent, ctx, chat, root):
    areas = agent["alan"]
    task = ("Revise your draft taking the feedback into account." if ctx["mode"] == "revision"
            else "Make ONE concrete improvement to the files in your area.")
    # The window turns with the date, so consecutive shifts see different files.
    # Dry runs pin it: a mocked shift has to be reproducible, and the turning itself
    # is covered directly by tests rather than through the mock.
    seed = 0 if os.environ.get("MOCK_LLM") == "1" else \
        dt.date.fromisoformat(ctx["date"]).toordinal()
    current, unrewritable = _current(root, areas, seed)
    user = (f"[AGENT:{agent['id']}][MODE:{ctx['mode']}][DAY:{ctx['day']}]\n"
            f"Your memory:\n{ctx['memory']}\n\nHallway:\n{ctx['hallway']}\n\n"
            f"Areas you may edit: {', '.join(areas)}\n\n"
            f"Current files:\n{current}\n\n"
            + (f"Feedback received:\n{ctx['input']}\n\n" if ctx["input"] else "")
            + f"{task} At most 3 files, each with its FULL new content — every line you "
            "were shown plus your change, never a summary, a fragment or a note about "
            "the file. "
            'ANSWER ONLY with this JSON object: {"files": {"path": "full content"}, '
            '"rationale": "why you changed it", "hallway": "one line or null"}')

    last = None
    for _ in range(3):
        # A rejected attempt is told why. Resampling the identical prompt three times
        # only rolls the same dice again; the model can correct a fault it can read.
        retry = f"\n\nYour previous answer was rejected: {last}\nTry again." if last else ""
        try:
            raw = chat(ctx["prompt"], user + retry, want_json=True, root=root).strip()
            if raw.startswith("```"):
                raw = raw.strip("`").lstrip("json").strip()
            obj = json.loads(raw)
            files = obj["files"]
            rationale = obj["rationale"]
            if not isinstance(files, dict) or not files or len(files) > 3:
                raise ValueError("must edit 1-3 files")
            if not isinstance(rationale, str) or len(rationale.strip()) < 10:
                raise ValueError("rationale required (constitution art. 3)")
            for path, content in files.items():
                if ".." in path or path.startswith("/") or \
                   not any(path.startswith(a.rstrip("/")) if (root / a).is_file()
                           else path.startswith(a) for a in areas):
                    raise ValueError(f"path outside area: {path}")
                if not isinstance(content, str):
                    raise ValueError(f"{path}: content must be the file's text")
                # site/data/ is written by site/build.py on every deploy and is not
                # in the repository at all, so it never appears on disk for the check
                # below to catch. Anything left there is overwritten within the minute.
                if path.startswith("site/data/"):
                    raise ValueError(
                        f"{path}: site/data/ is build output, not a source file. It is "
                        "regenerated on every deploy; edit what produces it instead.")
                if path in unrewritable:
                    raise ValueError(unrewritable[path])
                before = root / path
                was = len(before.read_text(encoding="utf-8")) if before.is_file() else 0
                if was and len(content) < was * SHRINK_FLOOR:
                    raise ValueError(
                        f"{path}: you returned {len(content)} characters to replace {was}. "
                        "A rewrite may not drop below "
                        f"{int(SHRINK_FLOOR * 100)}% of the file — return every line, "
                        "not just the part you touched.")
                broken = _validator(root).check(path, content)
                if broken:
                    raise ValueError(
                        f"{path}: what you wrote does not parse — {broken}. "
                        "Read your own output back before you send it: a file that "
                        "does not parse does not run, however complete it looks.")
            return {"files": files,
                    "pr": {"title": f"{agent['id']}: edit {ctx['date']}",
                           "body": f"Rationale: {rationale}", "draft": agent["draft_pr"]},
                    "hallway": obj.get("hallway"), "memory_add": None}
        except (json.JSONDecodeError, ValueError, KeyError, TypeError) as e:
            last = e
    raise ValueError(f"editor produced no valid edit in 3 attempts: {last}")
