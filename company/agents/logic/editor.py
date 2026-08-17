"""Editor: alanıyla sınırlı dosya düzenleyen ajanlar (tasarımcı, web, süreç)."""
import json
from pathlib import Path

ORNEK_DOSYA_SINIRI = 8
ICERIK_SINIRI = 5000


def _mevcut(kok, alanlar):
    parcalar = []
    for alan in alanlar:
        for yol in sorted((kok / alan).rglob("*")):
            if yol.is_file() and yol.suffix in (".css", ".html", ".js", ".md") \
               and "veri" not in yol.parts and len(parcalar) < ORNEK_DOSYA_SINIRI:
                rel = yol.relative_to(kok).as_posix()
                parcalar.append(f"--- {rel} ---\n{yol.read_text(encoding='utf-8')[:ICERIK_SINIRI]}")
    return "\n".join(parcalar)


def calis(ajan, ctx, chat, kok):
    alanlar = ajan["alan"]
    gorev = ("Yorumları dikkate alarak taslağını revize et." if ctx["mode"] == "revizyon"
             else "Alanındaki dosyalarda BİR somut iyileştirme yap.")
    user = (f"[AJAN:{ajan['id']}][MOD:{ctx['mode']}][GUN:{ctx['gun']}]\n"
            f"Hafızan:\n{ctx['hafiza']}\n\nKoridor:\n{ctx['koridor']}\n\n"
            f"Düzenleyebileceğin alanlar: {', '.join(alanlar)}\n\n"
            f"Mevcut dosyalar:\n{_mevcut(kok, alanlar)}\n\n"
            + (f"Gelen geri bildirim:\n{ctx['girdi']}\n\n" if ctx["girdi"] else "")
            + f"{gorev} En fazla 3 dosya, her dosyanın TAM yeni içeriğiyle. "
            'YANITINI YALNIZCA şu JSON nesnesi olarak ver: {"dosyalar": {"yol": "tam içerik"}, '
            '"gerekce": "değişiklik gerekçen", "koridor": "tek satır ya da null"}')

    son_hata = None
    for _ in range(3):
        try:
            ham = chat(ctx["prompt"], user, cevap_json=True, kok=kok).strip()
            if ham.startswith("```"):
                ham = ham.strip("`").lstrip("json").strip()
            obj = json.loads(ham)
            dosyalar = obj["dosyalar"]
            gerekce = obj["gerekce"]
            if not isinstance(dosyalar, dict) or not dosyalar or len(dosyalar) > 3:
                raise ValueError("dosya sayısı 1-3 olmalı")
            if not isinstance(gerekce, str) or len(gerekce.strip()) < 10:
                raise ValueError("gerekçe zorunlu (anayasa md. 3)")
            for yol in dosyalar:
                if ".." in yol or yol.startswith("/") or \
                   not any(yol.startswith(a) for a in alanlar):
                    raise ValueError(f"alan dışı yol: {yol}")
            return {"files": dosyalar,
                    "pr": {"baslik": f"{ajan['id']}: {ctx['tarih']} düzenlemesi",
                           "govde": f"Gerekçe: {gerekce}", "draft": ajan["draft_pr"]},
                    "koridor": obj.get("koridor"), "hafiza_ekle": None}
        except (json.JSONDecodeError, ValueError, KeyError, TypeError) as h:
            son_hata = h
    raise ValueError(f"editor 3 denemede geçerli düzenleme üretemedi: {son_hata}")
