"""Tahminci personaları: lig başına tek LLM çağrısı, şema doğrulamalı."""
import datetime as dt
import json
import re
from pathlib import Path

SKOR = re.compile(r"^\d{1,2}-\d{1,2}$")


def _hafta(ctx):
    cuma = dt.date.fromisoformat(ctx["tarih"])  # cuma günü koşar
    y, h, _ = cuma.isocalendar()
    return f"{y}-W{h:02d}"


def calis(ajan, ctx, chat, kok):
    hafta = _hafta(ctx)
    fyol = kok / f"company/data/fixtures/{hafta}.json"
    if not fyol.exists():
        raise FileNotFoundError(f"fikstür yok: {fyol.name}")
    fikstur = json.loads(fyol.read_text(encoding="utf-8"))
    ligler = {}
    for m in fikstur:
        ligler.setdefault(m["lig"], []).append(m)

    tahminler = []
    for lig, maclar in ligler.items():
        gecerli_id = {m["mac_id"] for m in maclar}
        liste = "\n".join(f'- mac_id {m["mac_id"]}: {m["ev"]} - {m["dep"]}' for m in maclar)
        user = (f"[AJAN:{ajan['id']}][LIG:{lig}][GUN:fri]\nHafta {hafta}, {lig} maçları:\n{liste}\n\n"
                f"Hafızan:\n{ctx['hafiza']}\n\nKoridor:\n{ctx['koridor']}\n\n"
                "Her maç için kişiliğine uygun skor tahmini yap. YANITINI YALNIZCA şu JSON dizisi "
                'olarak ver: [{"mac_id": <int>, "ev": "...", "dep": "...", "skor": "2-1", '
                '"gerekce": "tek cümle"}]')
        for _ in range(3):
            try:
                ham = chat(ctx["prompt"], user, cevap_json=True, kok=kok).strip()
                if ham.startswith("```"):
                    ham = ham.strip("`").lstrip("json").strip()
                obj = json.loads(ham)
                if isinstance(obj, dict):  # bazı modeller {"tahminler":[...]} sarar
                    obj = next((v for v in obj.values() if isinstance(v, list)), [])
                secilen = [t for t in obj
                           if isinstance(t, dict) and t.get("mac_id") in gecerli_id
                           and isinstance(t.get("skor"), str) and SKOR.match(t["skor"])]
                if secilen:
                    tahminler += [{"mac_id": t["mac_id"], "ev": str(t.get("ev", "")),
                                   "dep": str(t.get("dep", "")), "skor": t["skor"],
                                   "gerekce": str(t.get("gerekce", ""))[:400]} for t in secilen]
                    break
            except (json.JSONDecodeError, ValueError, TypeError):
                continue

    if not tahminler:
        raise ValueError("hiç geçerli tahmin üretilemedi")
    return {"files": {f"company/data/predictions/{ajan['id']}/{hafta}.json":
                      json.dumps(tahminler, ensure_ascii=False, indent=1)},
            "pr": {"baslik": f"tahmin: {ajan['id']} {hafta}",
                   "govde": f"{len(tahminler)} maç için tahmin. Eğlence amaçlıdır, bahis tavsiyesi değildir.",
                   "draft": False},
            "koridor": f"{hafta} tahminlerimi yazdım, isabet ligi beni bekler.", "hafiza_ekle": None}
