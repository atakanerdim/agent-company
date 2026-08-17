"""Vardiya çalıştırıcısı — DOKUNULMAZ ÇEKİRDEK (anayasa md. 1).

Kullanım:
  python kernel/runner.py --liste --gun fri
  python kernel/runner.py --agent dedikoducu --gun wed
  python kernel/runner.py --agent tasarimci --gun sat --mode revizyon --girdi out/yorumlar.json
  python kernel/runner.py --gun fri            (o günün tüm ajanları, sırayla)

Sonuç sözleşmesi (logic modülleri ve generic akış):
  {"files": {yol: icerik}, "pr": {"baslik","govde","draft"}|None,
   "koridor": str|None, "hafiza_ekle": str|None}
"""
import argparse
import datetime as dt
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import llm

GENERIC_SOZLESME = ("YANITINI YALNIZCA şu JSON nesnesi olarak ver: "
                    '{"cikti_markdown": "vardiya çıktın (markdown)", '
                    '"koridor": "koridora bırakacağın TEK satır ya da null", '
                    '"hafiza_ekle": "hafızana eklenecek kısa not ya da null"}')
YORUM_SOZLESME = 'YANITINI YALNIZCA şu JSON nesnesi olarak ver: {"yorum": "PR üzerine değerlendirmen"}'


def tarih():
    return os.environ.get("VARDIYA_TARIH") or dt.date.today().isoformat()


def log(kok, mesaj):
    yol = kok / "company/log" / f"{tarih()}.log"
    yol.parent.mkdir(parents=True, exist_ok=True)
    with open(yol, "a", encoding="utf-8") as f:
        f.write(f"[{dt.datetime.utcnow().isoformat(timespec='seconds')}] {mesaj}\n")


def ctx_kur(kok, ajan, gun, mode, girdi_yolu):
    oku = lambda p: (kok / p).read_text(encoding="utf-8") if (kok / p).exists() else ""
    satirlar = sorted((kok / "company/koridor").glob("*.txt"))[-10:]
    koridor = "\n".join(s.read_text(encoding="utf-8").strip() for s in satirlar)
    girdi = oku(girdi_yolu) if girdi_yolu else ""
    return {"prompt": oku(f"company/agents/prompts/{ajan['id']}.md"),
            "hafiza": oku(f"company/agents/memory/{ajan['id']}.md"),
            "koridor": koridor, "gun": gun, "mode": mode, "girdi": girdi[:6000],
            "tarih": tarih()}


def _json_iste(sistem, user, kok, dogrula):
    """LLM'den JSON ister; 3 deneme; dogrula(obj) -> obj ya da ValueError."""
    son_hata = None
    for _ in range(3):
        ham = llm.chat(sistem, user, cevap_json=True, kok=kok)
        try:
            ham_temiz = ham.strip()
            if ham_temiz.startswith("```"):
                ham_temiz = ham_temiz.strip("`").lstrip("json").strip()
            return dogrula(json.loads(ham_temiz))
        except (json.JSONDecodeError, ValueError, KeyError, TypeError) as h:
            son_hata = h
    raise ValueError(f"3 denemede geçerli JSON alınamadı: {son_hata}")


def generic(kok, ajan, ctx):
    etiket = f"[AJAN:{ajan['id']}][MOD:{ctx['mode']}][GUN:{ctx['gun']}]"
    user = (f"{etiket}\nTarih: {ctx['tarih']}\n\nHafızan:\n{ctx['hafiza']}\n\n"
            f"Koridorun son satırları:\n{ctx['koridor']}\n\n")
    if ctx["mode"] == "yorum":
        user += f"İncelenecek değişiklik:\n{ctx['girdi']}\n\n{YORUM_SOZLESME}"
        obj = _json_iste(ctx["prompt"], user, kok, lambda o: o if isinstance(o.get("yorum"), str) else _hata())
        return {"files": {f"out/yorum-{ajan['id']}.txt": obj["yorum"]},
                "pr": None, "koridor": None, "hafiza_ekle": None}
    user += f"Bugünkü vardiyanı yap.\n\n{GENERIC_SOZLESME}"

    def dogrula(o):
        if not isinstance(o.get("cikti_markdown"), str):
            raise ValueError("cikti_markdown yok")
        return o

    obj = _json_iste(ctx["prompt"], user, kok, dogrula)
    dosya = f"company/minutes/{ctx['tarih']}-{ajan['id']}.md"
    icerik = f"# {ajan['ad']} — {ctx['tarih']}\n\n{obj['cikti_markdown']}\n"
    return {"files": {dosya: icerik},
            "pr": {"baslik": f"{ajan['id']}: {ctx['tarih']} vardiyası",
                   "govde": f"{ajan['ad']} günlük vardiya çıktısı.", "draft": ajan["draft_pr"]},
            "koridor": obj.get("koridor"), "hafiza_ekle": obj.get("hafiza_ekle")}


def _hata():
    raise ValueError("şema uymadı")


def logic_yukle(kok, ad):
    yol = kok / "company/agents/logic" / f"{ad}.py"
    spec = importlib.util.spec_from_file_location(f"logic_{ad}", yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def uygula(kok, ajan, sonuc):
    yazilan = []
    for yol, icerik in (sonuc.get("files") or {}).items():
        if ".." in yol or yol.startswith("/"):
            raise ValueError(f"geçersiz yol: {yol}")
        hedef = kok / yol
        hedef.parent.mkdir(parents=True, exist_ok=True)
        hedef.write_text(icerik, encoding="utf-8")
        yazilan.append(yol)
    if sonuc.get("koridor"):
        satir = str(sonuc["koridor"]).strip().splitlines()[0][:200]
        (kok / "company/koridor" / f"{tarih()}-{ajan['id']}.txt").write_text(
            f"{ajan['ad']}: {satir}\n", encoding="utf-8")
    if sonuc.get("hafiza_ekle"):
        with open(kok / f"company/agents/memory/{ajan['id']}.md", "a", encoding="utf-8") as f:
            f.write(f"\n- [{tarih()}] {sonuc['hafiza_ekle']}\n")
    pr = sonuc.get("pr")
    if pr and yazilan:
        kuyruk_yolu = kok / "out/pr_queue.json"
        kuyruk_yolu.parent.mkdir(exist_ok=True)
        kuyruk = json.loads(kuyruk_yolu.read_text(encoding="utf-8")) if kuyruk_yolu.exists() else []
        kuyruk.append({"ajan": ajan["id"], "dal": f"vardiya/{ajan['id']}/{tarih()}",
                       "baslik": pr["baslik"], "govde": pr["govde"], "draft": bool(pr.get("draft"))})
        kuyruk_yolu.write_text(json.dumps(kuyruk, ensure_ascii=False, indent=1), encoding="utf-8")


def ajan_kos(kok, ajan, gun, mode, girdi):
    ctx = ctx_kur(kok, ajan, gun, mode, girdi)
    try:
        if ajan.get("logic") and mode != "yorum":
            sonuc = logic_yukle(kok, ajan["logic"]).calis(ajan, ctx, llm.chat, kok)
        else:
            sonuc = generic(kok, ajan, ctx)
        uygula(kok, ajan, sonuc)
        print(f"tamam: {ajan['id']}")
    except Exception as h:  # vardiya asla şirketi durdurmaz
        log(kok, f"{ajan['id']} vardiyası atlandı: {type(h).__name__}: {h}")
        print(f"atlandı: {ajan['id']} ({h})", file=sys.stderr)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--gun", default=None)
    p.add_argument("--agent", default=None)
    p.add_argument("--mode", default="normal")
    p.add_argument("--girdi", default=None)
    p.add_argument("--liste", action="store_true")
    a = p.parse_args()
    kok = Path.cwd()
    gun = a.gun or dt.date.fromisoformat(tarih()).strftime("%a").lower()
    roster = json.loads((kok / "company/roster.json").read_text(encoding="utf-8"))
    if a.liste:
        for aj in roster:
            if gun in aj["gunler"]:
                print(aj["id"])
        return
    secili = [aj for aj in roster if aj["id"] == a.agent] if a.agent \
        else [aj for aj in roster if gun in aj["gunler"]]
    for aj in secili:
        ajan_kos(kok, aj, gun, a.mode, a.girdi)
        time.sleep(int(os.environ.get("VARDIYA_ARA_SN", "0")))


if __name__ == "__main__":
    main()
