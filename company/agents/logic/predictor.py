"""Predictor personas: one LLM call per league, schema-validated."""
import datetime as dt
import json
import re

SCORE = re.compile(r"^\d{1,2}-\d{1,2}$")


def _week(ctx):
    friday = dt.date.fromisoformat(ctx["date"])  # runs on friday
    y, w, _ = friday.isocalendar()
    return f"{y}-W{w:02d}"


def run(agent, ctx, chat, root):
    week = _week(ctx)
    fpath = root / f"company/data/fixtures/{week}.json"
    if not fpath.exists():
        raise FileNotFoundError(f"no fixtures: {fpath.name}")
    fixtures = json.loads(fpath.read_text(encoding="utf-8"))
    leagues = {}
    for m in fixtures:
        leagues.setdefault(m["league"], []).append(m)

    predictions = []
    for league, matches in leagues.items():
        valid_ids = {m["match_id"] for m in matches}
        listing = "\n".join(f'- match_id {m["match_id"]}: {m["home"]} - {m["away"]}' for m in matches)
        user = (f"[AGENT:{agent['id']}][LEAGUE:{league}][DAY:fri]\nWeek {week}, {league} matches:\n"
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
    return {"files": {f"company/data/predictions/{agent['id']}/{week}.json":
                      json.dumps(predictions, ensure_ascii=False, indent=1)},
            "pr": {"title": f"predictions: {agent['id']} {week}",
                   "body": f"{len(predictions)} match predictions. Entertainment only — not betting advice.",
                   "draft": False},
            "hallway": f"My {week} predictions are in; the accuracy league awaits.",
            "memory_add": None}
