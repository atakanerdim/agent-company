"""The competition tracks: which matches belong to which rhythm of the week.

The company used to know one rhythm — five domestic leagues, played Friday to
Sunday, predicted on Friday, scored on Monday. A European track plays on Tuesday
and Wednesday, which is the same ISO week but a different set of days, so the day
of a shift no longer tells an agent what to do. This module answers that: given a
day, which competitions to fetch, over what window, and under what week key.

The definition lives in company/data/tracks.json rather than in code, for the same
reason the provider chain moved to models.json: adding or retiring a track should
be a data edit, not a change to an agent's logic.
"""
import datetime as dt
import json

DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
_WINDOW_FIELDS = ("day", "from", "to")


def _check_day(where, value):
    if value not in DAYS:
        raise ValueError(f"{where}: '{value}' is not one of {', '.join(DAYS)}")


def load(root):
    """Read and validate the tracks. Raises ValueError rather than failing mid-shift.

    A shift that discovers a malformed track halfway through has already written
    files and called the model. Everything that can be checked is checked here.
    """
    raw = json.loads((root / "company/data/tracks.json").read_text(encoding="utf-8"))
    tracks = raw.get("tracks")
    if not isinstance(tracks, list) or not tracks:
        raise ValueError("tracks.json: 'tracks' must be a non-empty list")
    seen = set()
    for t in tracks:
        tid = t.get("id")
        if not isinstance(tid, str) or not tid:
            raise ValueError("tracks.json: every track needs a non-empty id")
        if tid in seen:
            raise ValueError(f"tracks.json: duplicate track id '{tid}'")
        seen.add(tid)
        if not isinstance(t.get("label"), str) or not t["label"]:
            raise ValueError(f"{tid}: label is required (the site reads it)")
        comps = t.get("competitions")
        if not isinstance(comps, list) or not comps or \
           not all(isinstance(c, str) and c for c in comps):
            raise ValueError(f"{tid}: competitions must be a non-empty list of codes")
        for kind in ("fixtures", "results"):
            spec = t.get(kind)
            if not isinstance(spec, dict) or any(f not in spec for f in _WINDOW_FIELDS):
                raise ValueError(f"{tid}.{kind}: needs day, from and to")
            _check_day(f"{tid}.{kind}", spec["day"])
            if not isinstance(spec["from"], int) or not isinstance(spec["to"], int):
                raise ValueError(f"{tid}.{kind}: from and to must be whole days")
            if spec["from"] > spec["to"]:
                raise ValueError(f"{tid}.{kind}: from ({spec['from']}) is after to ({spec['to']})")
        predict = t.get("predict")
        if not isinstance(predict, dict) or "day" not in predict:
            raise ValueError(f"{tid}.predict: needs a day")
        _check_day(f"{tid}.predict", predict["day"])
    return tracks


def jobs_for(tracks, day):
    """Every (kind, track) pair due on this day. One shift can carry more than one."""
    return [(kind, t) for t in tracks for kind in ("fixtures", "results")
            if t[kind]["day"] == day]


def predict_track(tracks, day):
    """The track whose predictions are written today, or None.

    Written in the data rather than inferred from the fixture day: a persona should
    be able to read, in one place, which night it is playing for.
    """
    return next((t for t in tracks if t["predict"]["day"] == day), None)


def window(date, spec):
    """The match window a job covers, both ends included."""
    return date + dt.timedelta(days=spec["from"]), date + dt.timedelta(days=spec["to"])


def week_key(start):
    """The week a set of matches belongs to: the ISO week its window opens in.

    Both tracks of one week land on the same key — European Tuesday and domestic
    Friday share an ISO week — so the two are separated by folder, never by name.
    """
    y, w, _ = start.isocalendar()
    return f"{y}-W{w:02d}"
