import json, os, subprocess, sys
from pathlib import Path

def _kos(sirket, gun, tarih):
    env = dict(os.environ, VARDIYA_TARIH=tarih)
    return subprocess.run([sys.executable, str(sirket / "kernel/runner.py"), "--agent", "analist", "--gun", gun],
                          cwd=sirket, env=env, capture_output=True, text=True)

def test_persembe_fikstur(sirket):
    p = _kos(sirket, "thu", "2026-08-20")
    assert p.returncode == 0, p.stderr
    f = json.loads((sirket / "company/data/fixtures/2026-W34.json").read_text())
    assert len(f) == 4 and f[0]["ev"] == "Arsenal" and f[0]["lig"] == "PL"
    mins = list((sirket / "company/minutes").glob("*analist*"))
    assert mins and "Mock brifing" in mins[0].read_text()

def test_pazartesi_sonuclar(sirket):
    p = _kos(sirket, "mon", "2026-08-24")
    assert p.returncode == 0, p.stderr
    r = json.loads((sirket / "company/data/results/2026-W34.json").read_text())
    assert {x["mac_id"]: (x["ev_gol"], x["dep_gol"]) for x in r} == {1001: (2, 1), 1002: (3, 1)}

def test_http_hatasi_dosya_bozmaz(sirket, monkeypatch):
    eski = '[{"mac_id": 9, "lig": "PL", "ev": "A", "dep": "B", "tarih": "x"}]'
    (sirket / "company/data/fixtures/2026-W34.json").write_text(eski)
    env = dict(os.environ, VARDIYA_TARIH="2026-08-20", MOCK_HTTP="patla")
    p = subprocess.run([sys.executable, str(sirket / "kernel/runner.py"), "--agent", "analist", "--gun", "thu"],
                       cwd=sirket, env=env, capture_output=True, text=True)
    assert p.returncode == 0
    assert (sirket / "company/data/fixtures/2026-W34.json").read_text() == eski
    assert list((sirket / "company/log").glob("*.log"))
