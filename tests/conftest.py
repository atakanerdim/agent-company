import json, os, shutil, sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "kernel"))

@pytest.fixture
def company(tmp_path, monkeypatch):
    """Installs a working copy of the company in tmp and sets up the mock environment."""
    for d in ("kernel", "company", "site"):
        shutil.copytree(ROOT / d, tmp_path / d)
    (tmp_path / "out").mkdir()
    monkeypatch.setenv("MOCK_LLM", "1")
    monkeypatch.setenv("MOCK_HTTP", "1")
    monkeypatch.setenv("MOCK_ANSWERS", str(ROOT / "tests" / "mock_answers.json"))
    monkeypatch.setenv("MOCK_FIXTURES", str(ROOT / "tests" / "mock_fixtures.json"))
    return tmp_path
