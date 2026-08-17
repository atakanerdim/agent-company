"""Site veri paketleyicisi: company/ içeriğini site/veri altına kopyalar.
Deterministiktir; Pages deploy'unda ve CI'da koşar. LLM çağırmaz."""
import datetime as dt
import json
import shutil
import subprocess
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
VERI = KOK / "site/veri"


def main():
    if VERI.exists():
        shutil.rmtree(VERI)
    VERI.mkdir(parents=True)
    (VERI / "data").mkdir()
    for alt in ("fixtures", "predictions", "results", "skorlar"):
        kaynak = KOK / "company/data" / alt
        if kaynak.exists():
            shutil.copytree(kaynak, VERI / "data" / alt)
    for tekil in ("company/data/league.json",):
        if (KOK / tekil).exists():
            shutil.copy(KOK / tekil, VERI / "data" / Path(tekil).name)
    for klasor in ("minutes", "koridor"):
        if (KOK / "company" / klasor).exists():
            shutil.copytree(KOK / "company" / klasor, VERI / klasor)
    shutil.copytree(KOK / "company/agents/prompts", VERI / "prompts")
    shutil.copy(KOK / "company/roster.json", VERI / "roster.json")
    shutil.copy(KOK / "company/anayasa.md", VERI / "anayasa.md")

    # Şirket adı: anayasadaki "Şirket adı:" satırından
    ad = ""
    for satir in (KOK / "company/anayasa.md").read_text(encoding="utf-8").splitlines():
        if satir.startswith("Şirket adı:") and "henüz yok" not in satir:
            ad = satir.split(":", 1)[1].strip()
    (VERI / "ad.txt").write_text(ad, encoding="utf-8")

    # Değişiklik günlüğü (git varsa)
    gunluk = []
    try:
        cikti = subprocess.run(
            ["git", "log", "-n", "60", "--pretty=format:%as%x09%s"],
            cwd=KOK, capture_output=True, text=True, check=True).stdout
        for satir in cikti.splitlines():
            tarih, _, mesaj = satir.partition("\t")
            gunluk.append({"tarih": tarih, "mesaj": mesaj})
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    (VERI / "gunluk.json").write_text(json.dumps(gunluk, ensure_ascii=False), encoding="utf-8")

    dosyalar = sorted(p.relative_to(VERI).as_posix() for p in VERI.rglob("*") if p.is_file())
    (VERI / "manifest.json").write_text(json.dumps(
        {"uretim": dt.datetime.utcnow().isoformat(timespec="seconds"),
         "dosyalar": dosyalar}, ensure_ascii=False), encoding="utf-8")
    print(f"site/veri hazır: {len(dosyalar)} dosya")


if __name__ == "__main__":
    main()
