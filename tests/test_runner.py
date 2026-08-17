import json, subprocess, sys, os
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]

def _kos(sirket, *arg):
    env = dict(os.environ, VARDIYA_TARIH="2026-08-19")
    return subprocess.run([sys.executable, str(sirket / "kernel/runner.py"), *arg],
                          cwd=sirket, env=env, capture_output=True, text=True)

def test_liste_cuma(sirket):
    p = _kos(sirket, "--liste", "--gun", "fri")
    assert p.returncode == 0, p.stderr
    assert p.stdout.split() == ["istatistikci", "romantik", "sogukkanli", "pesimist"]

def test_generic_vardiya(sirket):
    p = _kos(sirket, "--agent", "dedikoducu", "--gun", "wed")
    assert p.returncode == 0, p.stderr
    mins = list((sirket / "company/minutes").glob("*dedikoducu*"))
    assert mins and "Mock vardiya" in mins[0].read_text()
    kor = list((sirket / "company/koridor").glob("2026-08-19-dedikoducu.txt"))
    assert kor and "sakin" in kor[0].read_text()
    q = json.loads((sirket / "out/pr_queue.json").read_text())
    assert q[-1]["ajan"] == "dedikoducu" and q[-1]["draft"] is False

def test_bozuk_json_atlanir(sirket):
    roster = json.loads((sirket / "company/roster.json").read_text())
    roster.append({"id":"bozuk","ad":"Bozuk","rol":"test","logic":None,"alan":None,"gunler":["wed"],"draft_pr":False})
    (sirket / "company/roster.json").write_text(json.dumps(roster))
    (sirket / "company/agents/prompts/bozuk.md").write_text("test")
    (sirket / "company/agents/memory/bozuk.md").write_text("bos")
    p = _kos(sirket, "--agent", "bozuk", "--gun", "wed")
    assert p.returncode == 0
    logs = list((sirket / "company/log").glob("*.log"))
    assert logs and "bozuk" in logs[0].read_text()

def test_editor_ajan(sirket):
    p = _kos(sirket, "--agent", "tasarimci", "--gun", "tue")
    assert p.returncode == 0, p.stderr
    assert (sirket / "site/tema-mock.css").exists()
    q = json.loads((sirket / "out/pr_queue.json").read_text())
    assert q[-1]["draft"] is True and "mor" in q[-1]["govde"]

def test_editor_alan_disi_reddedilir(sirket, monkeypatch):
    kotu = {"[AJAN:websorumlusu]": {"dosyalar":{"kernel/runner.py":"x"},"gerekce":"kötü niyet","koridor":None}}
    (sirket / "kotu.json").write_text(json.dumps(kotu))
    env = dict(os.environ, VARDIYA_TARIH="2026-08-19", MOCK_CEVAPLAR=str(sirket / "kotu.json"))
    import subprocess, sys
    p = subprocess.run([sys.executable, str(sirket / "kernel/runner.py"), "--agent", "websorumlusu", "--gun", "wed"],
                       cwd=sirket, env=env, capture_output=True, text=True)
    assert p.returncode == 0
    icerik = (sirket / "kernel/runner.py").read_text()
    assert icerik != "x"
    logs = list((sirket / "company/log").glob("*.log"))
    assert logs
