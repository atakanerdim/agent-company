import json, os, subprocess, sys

def _vardiya(sirket, ajan, gun, tarih):
    env = dict(os.environ, VARDIYA_TARIH=tarih)
    return subprocess.run([sys.executable, str(sirket / "kernel/runner.py"), "--agent", ajan, "--gun", gun],
                          cwd=sirket, env=env, capture_output=True, text=True)

def test_puanla():
    import importlib.util
    from pathlib import Path
    yol = Path(__file__).resolve().parents[1] / "company/agents/logic/degerlendirici.py"
    spec = importlib.util.spec_from_file_location("dg", yol)
    dg = importlib.util.module_from_spec(spec); spec.loader.exec_module(dg)
    assert dg.puanla("2-1", (2, 1)) == 3
    assert dg.puanla("2-1", (3, 1)) == 1
    assert dg.puanla("2-1", (1, 1)) == 0
    assert dg.puanla("1-1", (2, 2)) == 1

def test_haftalik_dongu(sirket):
    _vardiya(sirket, "analist", "thu", "2026-08-20")
    for a in ("istatistikci", "romantik", "sogukkanli"):
        _vardiya(sirket, a, "fri", "2026-08-21")
    _vardiya(sirket, "analist", "mon", "2026-08-24")
    p = _vardiya(sirket, "degerlendirici", "mon", "2026-08-24")
    assert p.returncode == 0, p.stderr
    s = json.loads((sirket / "company/data/skorlar/2026-W34.json").read_text())
    assert s["istatistikci"]["puan"] == 3
    lig = json.loads((sirket / "company/data/league.json").read_text())
    assert lig["personalar"]["istatistikci"] == {"puan": 3, "kesin": 1, "sonuc": 0, "hafta": 1}
    mins = [m for m in (sirket / "company/minutes").iterdir() if "degerlendirici" in m.name]
    assert mins and "Mock retro" in mins[0].read_text()
