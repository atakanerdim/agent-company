import json, os, shutil, sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "kernel"))

# Everything the agents pile up as the company runs. A test that reads any of this
# is really reading whatever week the company happens to be in, which is why the
# fixture wipes it: tests describe behaviour, never accumulated history.
ACCUMULATED = ("company/minutes", "company/hallway", "company/log",
               "company/data/scores", "company/data/predictions",
               "company/data/fixtures", "company/data/results")

EMPTY_PERSONA = {"points": 0, "exact": 0, "outcome": 0, "weeks": 0}


def _wipe(directory):
    for item in directory.glob("*"):
        if item.name == ".gitkeep":
            continue
        shutil.rmtree(item) if item.is_dir() else item.unlink()


@pytest.fixture
def company(tmp_path, monkeypatch):
    """A pristine working copy of the company, plus the mock environment.

    The company on disk grows every day: minutes, hallway lines, error logs, weekly
    fixtures and results, and an accuracy league that counts up. A test written
    against that state passes on the day it is written and fails a week later for
    reasons that have nothing to do with the code. So the copy starts empty.
    """
    for d in ("kernel", "company", "site"):
        shutil.copytree(ROOT / d, tmp_path / d)
    (tmp_path / "out").mkdir()

    for rel in ACCUMULATED:
        _wipe(tmp_path / rel)
    league_path = tmp_path / "company/data/league.json"
    league = json.loads(league_path.read_text(encoding="utf-8"))
    league["personas"] = {name: dict(EMPTY_PERSONA) for name in league["personas"]}
    league_path.write_text(json.dumps(league), encoding="utf-8")

    monkeypatch.setenv("MOCK_LLM", "1")
    monkeypatch.setenv("MOCK_HTTP", "1")
    monkeypatch.setenv("MOCK_ANSWERS", str(ROOT / "tests" / "mock_answers.json"))
    monkeypatch.setenv("MOCK_FIXTURES", str(ROOT / "tests" / "mock_fixtures.json"))
    return tmp_path
