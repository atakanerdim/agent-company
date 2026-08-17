"""Analist: fikstür/sonuç çekimi (deterministik) + LLM brifing."""
import datetime as dt
import json
import os
import time
import urllib.request
from pathlib import Path

LIGLER = ["PL", "PD", "BL1", "SA", "FL1"]


def _hafta(cuma):
    y, h, _ = cuma.isocalendar()
    return f"{y}-W{h:02d}"


def _cek(baslangic, bitis):
    if os.environ.get("MOCK_HTTP") == "1":
        yol = os.environ.get("MOCK_FIKSTUR", "tests/mock_fikstur.json")
        return json.loads(Path(yol).read_text(encoding="utf-8"))["matches"]
    if os.environ.get("MOCK_HTTP"):
        raise RuntimeError("mock http hatası")
    anahtar = os.environ["FOOTBALL_DATA_KEY"]
    maclar = []
    for lig in LIGLER:
        url = (f"https://api.football-data.org/v4/competitions/{lig}/matches"
               f"?dateFrom={baslangic}&dateTo={bitis}")
        req = urllib.request.Request(url, headers={"X-Auth-Token": anahtar})
        with urllib.request.urlopen(req, timeout=60) as y:
            maclar += json.loads(y.read().decode("utf-8")).get("matches", [])
        time.sleep(7)  # bedava katman: ~10 istek/dk
    return maclar


def calis(ajan, ctx, chat, kok):
    bugun = dt.date.fromisoformat(ctx["tarih"])
    if ctx["gun"] == "thu":
        cuma = bugun + dt.timedelta(days=1)
    else:  # mon
        cuma = bugun - dt.timedelta(days=3)
    hafta = _hafta(cuma)
    maclar = _cek(cuma.isoformat(), (cuma + dt.timedelta(days=2)).isoformat())

    if ctx["gun"] == "thu":
        fikstur = [{"mac_id": m["id"], "lig": m["competition"]["code"],
                    "ev": m["homeTeam"]["shortName"], "dep": m["awayTeam"]["shortName"],
                    "tarih": m["utcDate"]} for m in maclar]
        ozet = "\n".join(f'- [{f["lig"]}] {f["ev"]} - {f["dep"]}' for f in fikstur[:60])
        brifing = chat(ctx["prompt"],
                       f"[AJAN:analist][GUN:thu]\nHafta {hafta} fikstürü:\n{ozet}\n\n"
                       "Kısa bir maç brifingi yaz (markdown). "
                       'YANITINI YALNIZCA {"cikti_markdown": "...", "koridor": "... ya da null", '
                       '"hafiza_ekle": null} JSON nesnesi olarak ver.',
                       cevap_json=True, kok=kok)
        try:
            b = json.loads(brifing)
        except json.JSONDecodeError:
            b = {"cikti_markdown": brifing, "koridor": None}
        return {"files": {
                    f"company/data/fixtures/{hafta}.json": json.dumps(fikstur, ensure_ascii=False, indent=1),
                    f"company/minutes/{ctx['tarih']}-analist-brifing.md":
                        f"# Maç brifingi — {hafta}\n\n{b.get('cikti_markdown','')}\n"},
                "pr": {"baslik": f"analist: {hafta} fikstürü", "govde": f"{len(fikstur)} maç çekildi.",
                       "draft": False},
                "koridor": b.get("koridor"), "hafiza_ekle": None}

    sonuclar = [{"mac_id": m["id"], "ev_gol": m["score"]["fullTime"]["home"],
                 "dep_gol": m["score"]["fullTime"]["away"]}
                for m in maclar if m.get("status") == "FINISHED"]
    return {"files": {f"company/data/results/{hafta}.json":
                      json.dumps(sonuclar, ensure_ascii=False, indent=1)},
            "pr": {"baslik": f"analist: {hafta} sonuçları", "govde": f"{len(sonuclar)} sonuç işlendi.",
                   "draft": False},
            "koridor": None, "hafiza_ekle": None}
