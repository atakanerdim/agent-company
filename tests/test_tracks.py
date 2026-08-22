"""The tracks definition is read before any shift acts on it.

A malformed track that is only discovered halfway through a shift has already
written files and spent a model call. These tests hold the promise that a bad
definition fails at load, and that each day maps to exactly the work it should.
"""
import datetime as dt
import importlib.util
import json

import pytest


def _tracks(company):
    spec = importlib.util.spec_from_file_location(
        "logic_tracks_under_test", company / "company/agents/logic/tracks.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GOOD = {"id": "x", "label": "X", "competitions": ["PL"],
        "fixtures": {"day": "thu", "from": 1, "to": 3},
        "predict": {"day": "fri"},
        "results": {"day": "mon", "from": -3, "to": -1}}


def _with(**changes):
    t = json.loads(json.dumps(GOOD))
    for key, value in changes.items():
        t[key] = value
    return t


def test_both_tracks_load(company):
    t = _tracks(company)
    assert [x["id"] for x in t.load(company)] == ["domestic", "europe"]


@pytest.mark.parametrize("broken", [
    {"id": "x"},                                            # nothing but an id
    _with(competitions=[]),                                 # no competitions
    _with(label=""),                                        # the site needs a name
    _with(fixtures={"day": "someday", "from": 1, "to": 3}),  # not a day of the week
    _with(fixtures={"day": "thu", "from": 3, "to": 1}),      # window runs backwards
    _with(fixtures={"day": "thu", "from": 1}),               # missing 'to'
    _with(predict={}),                                       # no prediction day
])
def test_a_broken_track_is_refused_at_load(company, broken):
    t = _tracks(company)
    (company / "company/data/tracks.json").write_text(
        json.dumps({"tracks": [broken]}), encoding="utf-8")
    with pytest.raises(ValueError):
        t.load(company)


def test_two_tracks_may_not_share_an_id(company):
    t = _tracks(company)
    (company / "company/data/tracks.json").write_text(
        json.dumps({"tracks": [GOOD, GOOD]}), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        t.load(company)


def test_monday_and_thursday_each_carry_two_jobs(company):
    """One shift, two tracks: the analyst fetches for both in a single visit."""
    t = _tracks(company)
    tracks = t.load(company)
    assert sorted((kind, x["id"]) for kind, x in t.jobs_for(tracks, "mon")) == \
        [("fixtures", "europe"), ("results", "domestic")]
    assert sorted((kind, x["id"]) for kind, x in t.jobs_for(tracks, "thu")) == \
        [("fixtures", "domestic"), ("results", "europe")]
    assert t.jobs_for(tracks, "sat") == []


def test_the_week_key_opens_with_the_window(company):
    """European Tuesday and domestic Friday of one week share a key."""
    t = _tracks(company)
    tracks = t.load(company)
    europe = next(x for x in tracks if x["id"] == "europe")
    domestic = next(x for x in tracks if x["id"] == "domestic")

    monday = dt.date(2026, 8, 24)
    assert t.window(monday, europe["fixtures"]) == (dt.date(2026, 8, 25), dt.date(2026, 8, 26))
    assert t.week_key(t.window(monday, europe["fixtures"])[0]) == "2026-W35"

    thursday = dt.date(2026, 8, 27)
    assert t.week_key(t.window(thursday, domestic["fixtures"])[0]) == "2026-W35"
    assert t.week_key(t.window(thursday, europe["results"])[0]) == "2026-W35"

    assert t.week_key(t.window(monday, domestic["results"])[0]) == "2026-W34"


def test_each_day_predicts_at_most_one_track(company):
    t = _tracks(company)
    tracks = t.load(company)
    assert t.predict_track(tracks, "tue")["id"] == "europe"
    assert t.predict_track(tracks, "fri")["id"] == "domestic"
    assert t.predict_track(tracks, "wed") is None
