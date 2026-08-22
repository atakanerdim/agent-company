"""Analyst: deterministic fixture/result fetching + LLM briefing.

The analyst works competition tracks, not a fixed list of leagues. A single shift
can carry more than one job — Monday closes the domestic weekend and opens the
European midweek — because the shift contract allows a result to write several
files under one pull request.
"""
import datetime as dt
import importlib.util
import json
import os
import time
import urllib.request
from pathlib import Path

REQUEST_GAP_SEC = 7  # free tier: ~10 requests/min


def _tracks(root):
    spec = importlib.util.spec_from_file_location(
        "logic_tracks", root / "company/agents/logic/tracks.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fetch(competitions, date_from, date_to):
    if os.environ.get("MOCK_HTTP") == "1":
        path = os.environ.get("MOCK_FIXTURES", "tests/mock_fixtures.json")
        return json.loads(Path(path).read_text(encoding="utf-8"))["matches"]
    if os.environ.get("MOCK_HTTP"):
        raise RuntimeError("mock http failure")
    key = os.environ["FOOTBALL_DATA_KEY"]
    matches = []
    for code in competitions:
        url = (f"https://api.football-data.org/v4/competitions/{code}/matches"
               f"?dateFrom={date_from}&dateTo={date_to}")
        req = urllib.request.Request(url, headers={"X-Auth-Token": key})
        with urllib.request.urlopen(req, timeout=60) as resp:
            matches += json.loads(resp.read().decode("utf-8")).get("matches", [])
        time.sleep(REQUEST_GAP_SEC)
    return matches


def _briefing(chat, ctx, root, track, week, fixtures):
    summary = "\n".join(f'- [{f["league"]}] {f["home"]} - {f["away"]}' for f in fixtures[:60])
    raw = chat(ctx["prompt"],
               f"[AGENT:analyst][DAY:{ctx['day']}][TRACK:{track['id']}]\n"
               f"Week {week} fixtures, {track['label']}:\n{summary}\n\n"
               "Write a short match briefing (markdown). "
               'ANSWER ONLY with {"output_markdown": "...", "hallway": "... or null", '
               '"memory_add": null} as a JSON object.',
               want_json=True, root=root)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"output_markdown": raw, "hallway": None}


def run(agent, ctx, chat, root):
    today = dt.date.fromisoformat(ctx["date"])
    tracks_mod = _tracks(root)
    tracks = tracks_mod.load(root)
    jobs = tracks_mod.jobs_for(tracks, ctx["day"])
    if not jobs:
        raise ValueError(f"no competition track has work on {ctx['day']}")

    files, titles, said, quiet_note = {}, [], None, None
    for kind, track in sorted(jobs, key=lambda j: (j[0], j[1]["id"])):
        start, end = tracks_mod.window(today, track[kind])
        week = tracks_mod.week_key(start)
        matches = _fetch(track["competitions"], start.isoformat(), end.isoformat())
        titles.append(f"{track['id']} {kind} {week}")

        if kind == "fixtures":
            fixtures = [{"match_id": m["id"], "league": m["competition"]["code"],
                         "home": m["homeTeam"]["shortName"], "away": m["awayTeam"]["shortName"],
                         "date": m["utcDate"]} for m in matches]
            files[f"company/data/fixtures/{track['id']}/{week}.json"] = \
                json.dumps(fixtures, ensure_ascii=False, indent=1)
            if fixtures:
                # A briefing is only worth a model call when there is something to brief.
                b = _briefing(chat, ctx, root, track, week, fixtures)
                files[f"company/minutes/{ctx['date']}-analyst-{track['id']}-briefing.md"] = \
                    f"# Match briefing — {track['label']}, {week}\n\n{b.get('output_markdown','')}\n"
                said = said or b.get("hallway")
            else:
                # An empty week is the calendar, not a fault. It is written down so the
                # personas can see there is nothing to predict, and said out loud so a
                # visitor knows why the night is quiet.
                quiet_note = quiet_note or f"No {track['label'].lower()} this week."
        else:
            results = [{"match_id": m["id"], "home_goals": m["score"]["fullTime"]["home"],
                        "away_goals": m["score"]["fullTime"]["away"]}
                       for m in matches if m.get("status") == "FINISHED"]
            files[f"company/data/results/{track['id']}/{week}.json"] = \
                json.dumps(results, ensure_ascii=False, indent=1)

    return {"files": files,
            "pr": {"title": f"analyst: {', '.join(titles)}",
                   "body": f"Fetched {len(files)} file(s) across {len(jobs)} job(s).",
                   "draft": False},
            "hallway": said or quiet_note, "memory_add": None}
