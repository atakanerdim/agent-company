import json, os, shutil, sys
from pathlib import Path
import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK / "kernel"))

@pytest.fixture
def sirket(tmp_path, monkeypatch):
    """Şirketin çalışan bir kopyasını tmp'ye kurar, mock ortamını ayarlar."""
    for d in ("kernel", "company", "site"):
        shutil.copytree(KOK / d, tmp_path / d)
    (tmp_path / "out").mkdir()
    monkeypatch.setenv("MOCK_LLM", "1")
    monkeypatch.setenv("MOCK_HTTP", "1")
    monkeypatch.setenv("MOCK_ANSWERS", str(KOK / "tests" / "mock_answers.json"))
    monkeypatch.setenv("MOCK_FIXTURES", str(KOK / "tests" / "mock_fixtures.json"))
    return tmp_path
