"""Evaluator: deterministic scoring + LLM retro."""
import datetime as dt
import json


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


def run(agent, ctx, chat, root):
    friday = dt.date.fromisoformat(ctx["date"]) - dt.timedelta(days=3)
    y, w, _ = friday.isocalendar()
    week = f"{y}-W{w:02d}"
    rpath = root / f"company/data/results/{week}.json"
    if not rpath.exists():
        raise FileNotFoundError(f"no results file: {rpath.name}")
    results = {r["match_id"]: (r["home_goals"], r["away_goals"])
               for r in json.loads(rpath.read_text(encoding="utf-8"))}

    lpath = root / "company/data/league.json"
    league = json.loads(lpath.read_text(encoding="utf-8"))
    weekly = {}
    for persona in league["personas"]:
        ppath = root / f"company/data/predictions/{persona}/{week}.json"
        detail = []
        if ppath.exists():
            for t in json.loads(ppath.read_text(encoding="utf-8")):
                if t["match_id"] in results:
                    pts = score_prediction(t["score"], results[t["match_id"]])
                    detail.append({"match_id": t["match_id"], "home": t["home"], "away": t["away"],
                                   "predicted": t["score"],
                                   "actual": "%d-%d" % results[t["match_id"]], "points": pts})
        total = sum(d["points"] for d in detail)
        weekly[persona] = {"points": total, "detail": detail}
        k = league["personas"][persona]
        k["points"] += total
        k["exact"] += sum(1 for d in detail if d["points"] == 3)
        k["outcome"] += sum(1 for d in detail if d["points"] == 1)
        k["weeks"] += 1

    summary = "\n".join(f'- {p}: {v["points"]} points '
                        f'({sum(1 for d in v["detail"] if d["points"]==3)} exact)'
                        for p, v in weekly.items())
    raw = chat(ctx["prompt"],
               f"[AGENT:evaluator][DAY:mon]\nWeek {week} scores:\n{summary}\n\n"
               "Write a short, honest retro: who missed and why, what we learned. "
               'ANSWER ONLY with {"output_markdown": "...", "hallway": "... or null", '
               '"memory_add": "... or null"} as a JSON object.',
               want_json=True, root=root)
    try:
        r = json.loads(raw)
    except json.JSONDecodeError:
        r = {"output_markdown": raw, "hallway": None, "memory_add": None}

    return {"files": {
                f"company/data/scores/{week}.json": json.dumps(weekly, ensure_ascii=False, indent=1),
                "company/data/league.json": json.dumps(league, ensure_ascii=False, indent=1),
                f"company/minutes/{ctx['date']}-evaluator-retro.md":
                    f"# Retro — {week}\n\n{summary}\n\n{r.get('output_markdown','')}\n"},
            "pr": {"title": f"evaluator: {week} scoring + retro",
                   "body": "Weekly points recorded; accuracy league updated.", "draft": False},
            "hallway": r.get("hallway"), "memory_add": r.get("memory_add")}
