import json, os, shutil, stat, sys
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
    """Remove a tree, clearing the read-only flag Windows refuses to delete through.

    On Windows os.rmdir refuses a directory carrying FILE_ATTRIBUTE_READONLY with
    "Access is denied", even when it is empty, and shutil.copytree carries that flag
    from the source into every copy the fixture makes. Waiting does not help: the
    attribute never clears on its own. Clearing it does.

    Measured on 2026-08-22: every directory of one working copy was 0x11
    READONLY|DIRECTORY, and the same rmdir succeeded immediately after a chmod.
    Guarded by os.name because S_IWRITE means something else entirely on POSIX —
    setting it there would strip the read and execute bits and break traversal.
    """
    if os.name == "nt":
        for item in (path, *path.rglob("*")):
            try:
                os.chmod(item, stat.S_IWRITE)
            except OSError:
                pass
    shutil.rmtree(path)


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
