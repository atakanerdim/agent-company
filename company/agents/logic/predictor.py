"""Predictor personas: one LLM call per competition, schema-validated.

A persona predicts for whichever track has its prediction day today. Two things
that look alike are kept firmly apart: a week with no matches, which is the
calendar and costs nothing, and a missing fixture file, which means the analyst
did not deliver and must be reported.
"""
import datetime as dt
import importlib.util
import json
import re

SCORE = re.compile(r"^\d{1,2}-\d{1,2}$")

# Nothing to do. The shift succeeds, writes no file and opens no pull request.
QUIET = {"files": {}, "pr": None, "hallway": None, "memory_add": None}


def _tracks(root):
    spec = importlib.util.spec_from_file_location(
        "logic_tracks", root / "company/agents/logic/tracks.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(agent, ctx, chat, root):
    tracks_mod = _tracks(root)
    track = tracks_mod.predict_track(tracks_mod.load(root), ctx["day"])
    if track is None:
        return QUIET

    # Every track predicts on the opening day of its own match window, so the
    # shift date and the fixture week are the same ISO week.
    week = tracks_mod.week_key(dt.date.fromisoformat(ctx["date"]))
    fpath = root / f"company/data/fixtures/{track['id']}/{week}.json"
    if not fpath.exists():
        raise FileNotFoundError(f"no fixtures: {track['id']}/{fpath.name}")
    fixtures = json.loads(fpath.read_text(encoding="utf-8"))
    if not fixtures:
        return QUIET

    leagues = {}
    for m in fixtures:
        leagues.setdefault(m["league"], []).append(m)

    predictions = []
    for league, matches in leagues.items():
        valid_ids = {m["match_id"] for m in matches}
        listing = "\n".join(f'- match_id {m["match_id"]}: {m["home"]} - {m["away"]}' for m in matches)
        user = (f"[AGENT:{agent['id']}][LEAGUE:{league}][DAY:{ctx['day']}]\n"
                f"Week {week}, {league} matches:\n"
                f"{listing}\n\nYour memory:\n{ctx['memory']}\n\nHallway:\n{ctx['hallway']}\n\n"
                "Predict a score for every match, in character. ANSWER ONLY with this JSON array: "
                '[{"match_id": <int>, "home": "...", "away": "...", "score": "2-1", '
                '"reasoning": "one sentence"}]')
        for _ in range(3):
            try:
                raw = chat(ctx["prompt"], user, want_json=True, root=root).strip()
                if raw.startswith("```"):
                    raw = raw.strip("`").lstrip("json").strip()
                obj = json.loads(raw)
                if isinstance(obj, dict):  # some models wrap {"predictions":[...]}
                    obj = next((v for v in obj.values() if isinstance(v, list)), [])
                picked = [t for t in obj
                          if isinstance(t, dict) and t.get("match_id") in valid_ids
                          and isinstance(t.get("score"), str) and SCORE.match(t["score"])]
                if picked:
                    predictions += [{"match_id": t["match_id"], "home": str(t.get("home", "")),
                                     "away": str(t.get("away", "")), "score": t["score"],
                                     "reasoning": str(t.get("reasoning", ""))[:400]} for t in picked]
                    break
            except (json.JSONDecodeError, ValueError, TypeError):
                continue

    if not predictions:
        raise ValueError("no valid predictions produced")
    return {"files": {f"company/data/predictions/{agent['id']}/{track['id']}/{week}.json":
                      json.dumps(predictions, ensure_ascii=False, indent=1)},
            "pr": {"title": f"predictions: {agent['id']} {track['id']} {week}",
                   "body": f"{len(predictions)} match predictions for {track['label']}. "
                           "Entertainment only — not betting advice.",
                   "draft": False},
            "hallway": f"My {track['label'].lower()} picks for {week} are in.",
            "memory_add": None}
