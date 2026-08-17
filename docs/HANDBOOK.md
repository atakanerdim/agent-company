# HANDBOOK — Otonom Stüdyo (tek doğruluk kaynağı)

> Bu dosya, projenin oturumlar arası hafızasıdır. Her çalışma oturumunun BAŞINDA okunur,
> SONUNDA güncellenir. Burada yazmayan hiçbir "hatırlanan" bilgiye güvenilmez.
> Canlı adres: https://github.com/atakanerdim/otonom-studyo

## Kimlik

Tamamen otonom, kendini güncelleyen 12 ajanlı yapay zeka şirketi. Çalışma dili İngilizce.
İnsan (Atakan) yalnızca gözlemci. Maliyet 0$/ay. v1 departmanı: futbol tahmin masası
(5 büyük lig, haftalık skor tahminleri, herkese açık isabet ligi).

## Mimari (değişmez özet)

- Tek public GitHub reposu = şirketin tamamı. GitHub Pages = site. Actions cron (06:00 UTC) = vardiyalar.
- Her değişiklik dal + PR → CI yeşil ve draft değilse otomatik squash merge. İnsan onayı yok.
- `kernel/` (runner.py + llm.py) ve `.github/workflows/` DOKUNULMAZ; CI bekçisi reddeder.
- Kernel her LLM çağrısına silinemez HOUSE RULES ekler; CI content-guard bahis/saldırgan dil/anahtar deseni tarar.
- LLM zinciri: Groq → Gemini → OpenRouter (models.json). Veri: football-data.org.
- Ajan = prompt + hafıza dosyası; logic'liler: analyst, predictor (3 persona), evaluator, editor (designer/webdev/process).
- Koridor: `company/hallway/` (satır-başına-dosya); dedikodu deneyi buradan akar.
- Tasarım döngüsü: Salı draft PR → Çar-Per yorumlar (pessimist, webdev, romantic) → Cmt revizyon + ready.

## Dosya haritası (kritik yollar)

| Ne | Nerede |
|---|---|
| Anayasa | company/constitution.md (şirket adı satırı dahil) |
| Kadro kaydı | company/roster.json |
| İsabet ligi | company/data/league.json |
| Haftalık veriler | company/data/{fixtures,predictions,results,scores}/ |
| Tutanak/retro | company/minutes/ |
| Hata kayıtları | company/log/ |
| Tasarım/plan | docs/specs/, docs/ |
| Kurulum + acil durum | KURULUM.md |

## Faz durumu

- [x] Faz 0: inşa + testler (15 pytest) + mock haftalık kuru koşu — 2026-08-17 tamam
- [ ] LANSMAN: repo push + secrets (5) + Pages + ilk `pages` ve `shift` tetiği ← ŞU ANKİ ADIM
- [ ] Faz 1: ilk gerçek hafta gözlemi (CEO ad seçer, ilk tahminler, ilk retro)
- [ ] Faz 2+: toy studio → art gallery → fiction sim (sırayla, tek tek)

## Karar günlüğü (özet)

2026-08-17: Mimari A (statik site + cron ajanları) seçildi; kadro 12; dedikodu çift katman
(enjeksiyon + köşe); dokunulmaz çekirdek kabul; ilk departman futbol tahmini; her şey İngilizce;
hukuki disclaimer her sayfada; CI content-guard eklendi. Ayrıntı: docs/specs/.

## v2 fikir park alanı (karar verilmedi)

- Anonim çapraz değerlendirme (llm-council esinli): tahminciler birbirinin setini kimliksiz sıralar, sıralama isabeti de puanlanır.
- Moderatör LLM geçişi (çift kontrol, API maliyeti 2x).
- Kaggle zamanlanmış notebook ile haftalık "yönetim kurulu" özel bölümü.
- Rastgele geri bildirimci seçimi (şimdilik sabit üçlü).

## Açık sorular

- (boş)
