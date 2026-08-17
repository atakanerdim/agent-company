"""Site HTML doğrulayıcı: parse + yerel bağlantı + zorunlu ibareler. CI'da koşar."""
import sys
from html.parser import HTMLParser
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
SITE = KOK / "site"


class Toplayici(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.baglar, self.hatali = [], []
        self.yigin = []
    TEKIL = {"meta", "link", "br", "img", "input", "hr", "canvas"}

    def handle_starttag(self, tag, attrs):
        if tag not in self.TEKIL:
            self.yigin.append(tag)
        for k, v in attrs:
            if k in ("href", "src") and v and not v.startswith(("http", "#", "data:")):
                self.baglar.append(v)

    def handle_endtag(self, tag):
        if tag in self.TEKIL:
            return
        if not self.yigin or self.yigin[-1] != tag:
            self.hatali.append(tag)
        else:
            self.yigin.pop()


def main():
    hatalar = []
    for sayfa in sorted(SITE.glob("*.html")):
        metin = sayfa.read_text(encoding="utf-8")
        p = Toplayici()
        p.feed(metin)
        if p.hatali or p.yigin:
            hatalar.append(f"{sayfa.name}: dengesiz etiketler {p.hatali or p.yigin}")
        for b in p.baglar:
            hedef = b.split("?")[0].split("#")[0]
            if hedef.startswith("veri/"):
                continue  # build çıktısı, çalışma anında oluşur
            if not (SITE / hedef).exists():
                hatalar.append(f"{sayfa.name}: kırık bağlantı {b}")
    tahmin = (SITE / "tahmin.html").read_text(encoding="utf-8")
    if "bahis tavsiyesi değildir" not in tahmin:
        hatalar.append("tahmin.html: sorumluluk reddi ibaresi eksik (anayasa md. 4)")
    if "gerçek üretim" not in (SITE / "index.html").read_text(encoding="utf-8"):
        hatalar.append("index.html: rozet eksik (anayasa md. 7)")
    for h in hatalar:
        print("HATA:", h)
    sys.exit(1 if hatalar else 0)


if __name__ == "__main__":
    main()
