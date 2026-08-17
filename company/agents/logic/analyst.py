"""Analyst: deterministic fixture/result fetching + LLM briefing."""
import datetime as dt
import json
import os
import time
import urllib.request
from pathlib import Path

LEAGUES = ["PL", "PD", "BL1", "SA", "FL1"]


def _week(friday):
    y, w, _ = friday.isocalendar()
    return f"{y}-W{w:02d}"


def _fetch(date_from, date_to):
    if os.environ.get("MOCK_HTTP") == "1":
        path = os.environ.get("MOCK_FIXTURES", "tests/mock_fixtures.json")
        return json.loads(Path(path).read_text(encoding="utf-8"))["matches"]
    if os.environ.get("MOCK_HTTP"):
        raise RuntimeError("mock http failure")
    key = os.environ["FOOTBALL_DATA_KEY"]
    matches = []
    for league in LEAGUES:
        url = (f"https://api.football-data.org/v4/competitions/{league}/matches"
               f"?dateFrom={date_from}&dateTo={date_to}")
        req = urllib.request.Request(url, headers={"X-Auth-Token": key})
        with urllib.request.urlopen(req, timeout=60) as resp:
            matches += json.loads(resp.read().decode("utf-8")).get("matches", [])
        time.sleep(7)  # free tier: ~10 requests/min
    return matches


def calis(agent, ctx, chat, root):
    today = dt.date.fromisoformat(ctx["date"])
    friday = today + dt.timedelta(days=1) if ctx["day"] == "thu" else today - dt.timedelta(days=3)
    week = _week(friday)
    matches = _fetch(friday.isoformat(), (friday + dt.timedelta(days=2)).isoformat())

    if ctx["day"] == "thu":
        fixtures = [{"match_id": m["id"], "league": m["competition"]["code"],
                     "home": m["homeTeam"]["shortName"], "away": m["awayTeam"]["shortName"],
                     "date": m["utcDate"]} for m in matches]
        summary = "\n".join(f'- [{f["league"]}] {f["home"]} - {f["away"]}' for f in fixtures[:60])
        raw = chat(ctx["prompt"],
                   f"[AGENT:analyst][DAY:thu]\nWeek {week} fixtures:\n{summary}\n\n"
                   "Write a short match briefing (markdown). "
                   'ANSWER ONLY with {"output_markdown": "...", "hallway": "... or null", '
                   '"memory_add": null} as a JSON object.',
                   want_json=True, root=root)
        try:
            b = json.loads(raw)
        except json.JSONDecodeError:
            b = {"output_markdown": raw, "hallway": None}
        return {"files": {
                    f"company/data/fixtures/{week}.json": json.dumps(fixtures, ensure_ascii=False, indent=1),
                    f"company/minutes/{ctx['date']}-analyst-briefing.md":
                        f"# Match briefing — {week}\n\n{b.get('output_markdown','')}\n"},
                "pr": {"title": f"analyst: fixtures {week}",
                       "body": f"Fetched {len(fixtures)} matches.", "draft": False},
                "hallway": b.get("hallway"), "memory_add": None}

    results = [{"match_id": m["id"], "home_goals": m["score"]["fullTime"]["home"],
                "away_goals": m["score"]["fullTime"]["away"]}
               for m in matches if m.get("status") == "FINISHED"]
    return {"files": {f"company/data/results/{week}.json":
                      json.dumps(results, ensure_ascii=False, indent=1)},
            "pr": {"title": f"analyst: results {week}",
                   "body": f"Recorded {len(results)} results.", "draft": False},
            "hallway": None, "memory_add": None}
