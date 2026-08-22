"""Evaluator: deterministic scoring + LLM retro.

Each competition track keeps its own table. A persona can be the sharpest reader of
domestic weekends and hopeless on European nights, and the site should be able to
show that, so the two are never added together.

A season ends by going quiet. Rather than ask the company to know a calendar it has
no way to read, a gap of SEASON_GAP_WEEKS scored weeks is treated as the start of a
new season: the finished table is archived under the weeks it covered, and the track
starts again from zero.
"""
import datetime as dt
import importlib.util
import json

SEASON_GAP_WEEKS = 4
EMPTY = {"points": 0, "exact": 0, "outcome": 0, "weeks": 0}


def _tracks(root):
    spec = importlib.util.spec_from_file_location(
        "logic_tracks", root / "company/agents/logic/tracks.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def score_prediction(predicted, actual):
    try:
        ph, pa = (int(x) for x in predicted.split("-"))
    except (ValueError, AttributeError):
        return 0
    ah, aa = actual
    if (ph, pa) == (ah, aa):
        return 3
    sign = lambda a, b: 0 if a == b else (1 if a > b else 2)
    return 1 if sign(ph, pa) == sign(ah, aa) else 0


def _monday_of(week):
    """'2026-W34' -> the Monday that opens that ISO week."""
    year, number = week.split("-W")
    return dt.date.fromisocalendar(int(year), int(number), 1)


def _weeks_between(earlier, later):
    return (_monday_of(later) - _monday_of(earlier)).days // 7


def _season_rollover(record, week, track_id, files):
    """Archive a finished season and start the track again from zero.

    Returns the record to score into — the same one, or a fresh one.
    """
    last = record.get("last_week")
    if not last or _weeks_between(last, week) < SEASON_GAP_WEEKS:
        return record
    first = record.get("first_week") or last
    files[f"company/data/league-archive/{track_id}-{first}-{last}.json"] = \
        json.dumps(record, ensure_ascii=False, indent=1)
    return {"personas": {name: dict(EMPTY) for name in record["personas"]},
            "first_week": None, "last_week": None}


def _score_track(root, track_id, week, record, files):
    """Score one track. Returns (per-persona detail, True) or (None, False) if it did not play."""
    rpath = root / f"company/data/results/{track_id}/{week}.json"
    if not rpath.exists():
        return None, False
    results = {r["match_id"]: (r["home_goals"], r["away_goals"])
               for r in json.loads(rpath.read_text(encoding="utf-8"))}

    weekly, played = {}, False
    for persona in record["personas"]:
        ppath = root / f"company/data/predictions/{persona}/{track_id}/{week}.json"
        if not ppath.exists():
            # No predictions is not a score of zero. Counting it as a played week
            # would put a phantom round into the public accuracy league.
            weekly[persona] = {"points": 0, "detail": [], "submitted": False}
            continue
        detail = []
        for t in json.loads(ppath.read_text(encoding="utf-8")):
            if t["match_id"] in results:
                pts = score_prediction(t["score"], results[t["match_id"]])
                detail.append({"match_id": t["match_id"], "home": t["home"], "away": t["away"],
                               "predicted": t["score"],
                               "actual": "%d-%d" % results[t["match_id"]], "points": pts})
        total = sum(d["points"] for d in detail)
        weekly[persona] = {"points": total, "detail": detail, "submitted": True}
        played = True
        k = record["personas"][persona]
        k["points"] += total
        k["exact"] += sum(1 for d in detail if d["points"] == 3)
        k["outcome"] += sum(1 for d in detail if d["points"] == 1)
        k["weeks"] += 1

    if not played:
        return None, False
    files[f"company/data/scores/{track_id}/{week}.json"] = \
        json.dumps(weekly, ensure_ascii=False, indent=1)
    record["first_week"] = record.get("first_week") or week
    record["last_week"] = week
    return weekly, True


def run(agent, ctx, chat, root):
    tracks_mod = _tracks(root)
    tracks = tracks_mod.load(root)
    week = tracks_mod.week_key(dt.date.fromisoformat(ctx["date"]) - dt.timedelta(days=3))

    lpath = root / "company/data/league.json"
    league = json.loads(lpath.read_text(encoding="utf-8"))
    league.setdefault("tracks", {})

    files, lines, scored = {}, [], []
    for track in tracks:
        tid = track["id"]
        if tid not in league["tracks"]:
            template = next(iter(league["tracks"].values()), {"personas": {}})
            league["tracks"][tid] = {"personas": {n: dict(EMPTY) for n in template["personas"]},
                                     "first_week": None, "last_week": None}
        record = _season_rollover(league["tracks"][tid], week, tid, files)
        league["tracks"][tid] = record
        weekly, played = _score_track(root, tid, week, record, files)
        if not played:
            lines.append(f"- {track['label']}: no round to score this week")
            continue
        scored.append(tid)
        for persona, v in weekly.items():
            lines.append(
                f'- {track["label"]} / {persona}: did not submit predictions this week'
                if not v["submitted"] else
                f'- {track["label"]} / {persona}: {v["points"]} points '
                f'({sum(1 for d in v["detail"] if d["points"] == 3)} exact)')

    if not scored:
        raise ValueError(f"no track had a scored round for {week}; nothing to record")

    files["company/data/league.json"] = json.dumps(league, ensure_ascii=False, indent=1)
    summary = "\n".join(lines)
    raw = chat(ctx["prompt"],
               f"[AGENT:evaluator][DAY:{ctx['day']}]\nWeek {week} scores:\n{summary}\n\n"
               "Write a short, honest retro on what these numbers show. "
               "Stay strictly within them: a persona listed as not submitting predictions "
               "did not play this week, and a track listed as having no round did not play "
               "at all, so never invent a reason for how either scored, and never describe "
               "matches or reasoning you were not given. "
               'ANSWER ONLY with {"output_markdown": "...", "hallway": "... or null", '
               '"memory_add": "... or null"} as a JSON object.',
               want_json=True, root=root)
    try:
        r = json.loads(raw)
    except json.JSONDecodeError:
        r = {"output_markdown": raw, "hallway": None, "memory_add": None}

    files[f"company/minutes/{ctx['date']}-evaluator-retro.md"] = \
        f"# Retro — {week}\n\n{summary}\n\n{r.get('output_markdown','')}\n"
    return {"files": files,
            "pr": {"title": f"evaluator: {week} scoring + retro",
                   "body": f"Weekly points recorded for {', '.join(scored)}; "
                           "accuracy tables updated.", "draft": False},
            "hallway": r.get("hallway"), "memory_add": r.get("memory_add")}
