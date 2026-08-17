import json, os, subprocess, sys

def test_tahminler(sirket):
    env = dict(os.environ, VARDIYA_TARIH="2026-08-20")
    subprocess.run([sys.executable, str(sirket / "kernel/runner.py"), "--agent", "analist", "--gun", "thu"],
                   cwd=sirket, env=env, capture_output=True, text=True)
    env["VARDIYA_TARIH"] = "2026-08-21"
    p = subprocess.run([sys.executable, str(sirket / "kernel/runner.py"), "--agent", "istatistikci", "--gun", "fri"],
                       cwd=sirket, env=env, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    t = json.loads((sirket / "company/data/predictions/istatistikci/2026-W34.json").read_text())
    assert len(t) == 3
    assert all(x["skor"].count("-") == 1 for x in t)
    ids = {x["mac_id"] for x in t}
    assert ids == {1001, 1002, 1003}
    q = json.loads((sirket / "out/pr_queue.json").read_text())
    assert q[-1]["baslik"].startswith("tahmin: istatistikci")
