import json, os, shutil, sys, time
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
               "company/data/fixtures", "company/data/results",
               "company/data/league-archive")

EMPTY_PERSONA = {"points": 0, "exact": 0, "outcome": 0, "weeks": 0}


def _rmtree(path):
    """Remove a tree, allowing for Windows taking its time to let go.

    On Windows a file that has just been unlinked can keep its directory entry
    alive until the last handle on it closes — an indexer's, a virus scanner's —
    and the rmdir that follows fails with "Access is denied" on a directory that
    is, as far as the program is concerned, already empty. The company's data now
    lives one level deeper (per competition track), which made a fixture that had
    always been fine start failing on Windows while staying green on the Linux
    runner. Retrying briefly costs nothing where the problem does not exist.
    """
    for attempt in range(6):
        try:
            shutil.rmtree(path)
            return
        except PermissionError:
            if attempt == 5:
                raise
            time.sleep(0.25)


def _wipe(directory):
    for item in directory.glob("*"):
        if item.name == ".gitkeep":
            continue
        _rmtree(item) if item.is_dir() else item.unlink()


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
    for record in league["tracks"].values():
        record["personas"] = {n: dict(EMPTY_PERSONA) for n in record["personas"]}
        record["first_week"] = record["last_week"] = None
    league_path.write_text(json.dumps(league), encoding="utf-8")

    monkeypatch.setenv("MOCK_LLM", "1")
    monkeypatch.setenv("MOCK_HTTP", "1")
    monkeypatch.setenv("MOCK_ANSWERS", str(ROOT / "tests" / "mock_answers.json"))
    monkeypatch.setenv("MOCK_FIXTURES", str(ROOT / "tests" / "mock_fixtures.json"))
    return tmp_path
