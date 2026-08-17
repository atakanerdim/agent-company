"""Değerlendirici: deterministik puanlama + LLM retro."""
import datetime as dt
import json


def puanla(tahmin, gercek):
    try:
        te, td = (int(x) for x in tahmin.split("-"))
    except (ValueError, AttributeError):
        return 0
    ge, gd = gercek
    if (te, td) == (ge, gd):
        return 3
    isaret = lambda a, b: 0 if a == b else (1 if a > b else 2)
    return 1 if isaret(te, td) == isaret(ge, gd) else 0


def calis(ajan, ctx, chat, kok):
    cuma = dt.date.fromisoformat(ctx["tarih"]) - dt.timedelta(days=3)
    y, h, _ = cuma.isocalendar()
    hafta = f"{y}-W{h:02d}"
    ryol = kok / f"company/data/results/{hafta}.json"
    if not ryol.exists():
        raise FileNotFoundError(f"sonuç dosyası yok: {ryol.name}")
    sonuclar = {r["mac_id"]: (r["ev_gol"], r["dep_gol"])
                for r in json.loads(ryol.read_text(encoding="utf-8"))}

    lig_yolu = kok / "company/data/league.json"
    lig = json.loads(lig_yolu.read_text(encoding="utf-8"))
    haftalik = {}
    for persona in lig["personalar"]:
        pyol = kok / f"company/data/predictions/{persona}/{hafta}.json"
        detay = []
        if pyol.exists():
            for t in json.loads(pyol.read_text(encoding="utf-8")):
                if t["mac_id"] in sonuclar:
                    p = puanla(t["skor"], sonuclar[t["mac_id"]])
                    detay.append({"mac_id": t["mac_id"], "ev": t["ev"], "dep": t["dep"],
                                  "tahmin": t["skor"],
                                  "gercek": "%d-%d" % sonuclar[t["mac_id"]], "puan": p})
        toplam = sum(d["puan"] for d in detay)
        haftalik[persona] = {"puan": toplam, "detay": detay}
        k = lig["personalar"][persona]
        k["puan"] += toplam
        k["kesin"] += sum(1 for d in detay if d["puan"] == 3)
        k["sonuc"] += sum(1 for d in detay if d["puan"] == 1)
        k["hafta"] += 1

    ozet = "\n".join(f'- {p}: {v["puan"]} puan '
                     f'({sum(1 for d in v["detay"] if d["puan"]==3)} kesin skor)'
                     for p, v in haftalik.items())
    retro = chat(ctx["prompt"],
                 f"[AJAN:degerlendirici][GUN:mon]\nHafta {hafta} skorları:\n{ozet}\n\n"
                 "Kısa ve dürüst bir retro yaz: kim neden yanıldı, ne öğrendik. "
                 'YANITINI YALNIZCA {"cikti_markdown": "...", "koridor": "... ya da null", '
                 '"hafiza_ekle": "... ya da null"} JSON nesnesi olarak ver.',
                 cevap_json=True, kok=kok)
    try:
        r = json.loads(retro)
    except json.JSONDecodeError:
        r = {"cikti_markdown": retro, "koridor": None, "hafiza_ekle": None}

    return {"files": {
                f"company/data/skorlar/{hafta}.json": json.dumps(haftalik, ensure_ascii=False, indent=1),
                "company/data/league.json": json.dumps(lig, ensure_ascii=False, indent=1),
                f"company/minutes/{ctx['tarih']}-degerlendirici-retro.md":
                    f"# Retro — {hafta}\n\n{ozet}\n\n{r.get('cikti_markdown','')}\n"},
            "pr": {"baslik": f"degerlendirici: {hafta} puanlama + retro",
                   "govde": "Haftalık puanlar işlendi, isabet ligi güncellendi.", "draft": False},
            "koridor": r.get("koridor"), "hafiza_ekle": r.get("hafiza_ekle")}
