# Otonom Stüdyo — Tasarım Dokümanı

Tarih: 2026-08-17 · Durum: Onaylı tasarım, uygulama planı bekliyor
Not: Bu dosya, kurulacak reponun `docs/specs/` klasörüne ilk commit'le taşınacak.

## 1. Amaç

Açık LLM'lerle çalışan, kendini güncelleyen, tamamen otonom bir "ajan şirketi". İnsan yalnızca izleyici. Şirketin tamamı tek bir public GitHub reposunda yaşar; ürünü GitHub Pages'te yayınlanan statik bir web sitesidir. Site hem şirketin vitrini hem de üretiminin sergilendiği yerdir. Maliyet hedefi: 0 $/ay.

## 2. İlkeler ve kısıtlar

- Sıfır maliyet: yalnızca bedava katmanlar (GitHub public repo + Pages + Actions, bedava LLM API katmanları, football-data.org bedava katmanı).
- Kullanıcının bilgisayarına sıfır yük: omurga tamamen bulutta. Yerel GPU (RTX 2050 4GB) ana planda yok; ileride opsiyonel "fırsatçı katman" olabilir.
- Tam otonomi + mekanik anayasa: insan onayı hiçbir akışta yok. Tek istisna dokunulmaz çekirdek (madde 8) — bu insan müdahalesi değil, mekanik kuraldır.
- Tam şeffaflık: her karar, prompt, hafıza ve değişiklik public repoda; site bunları sergiler.
- Departmanlar sırayla açılır. v1 = futbol tahmin masası. Oyuncak stüdyosu, sanat galerisi ve kurgu simülasyonu sonraki fazlarda ayrı sekmeler olarak eklenir; her bölüm "gerçek üretim / kurgu" rozeti taşır.

## 3. Mimari: statik site + cron ajanları

Seçilen yaklaşım (alternatifleri değerlendirildi: ajan çerçevesi tek süreçte — kırılgan, çekirdeği büyütüyor; sunuculu — şeffaflığı kırıyor, gereksiz):

- Site tamamen statik (HTML/CSS/vanilla JS + Chart.js). Veri, repodaki JSON/Markdown dosyalarından build sırasında gömülür veya raw olarak fetch edilir.
- Ajanlar bağımsız Python betikleri. GitHub Actions cron'u onları vardiya usulü uyandırır.
- Her vardiya: repo durumunu oku → LLM API çağır → değişikliği dal + PR olarak aç → CI yeşilse otomatik birleş → Pages yeniden yayınlar.
- Şirket hafızası git'in kendisidir: commit geçmişi = şirket tarihi.

### Repo yapısı

```
kernel/              # DOKUNULMAZ (~100 satır): ajan çalıştırıcı döngü + yardımcıları
.github/workflows/   # DOKUNULMAZ: cron zamanlayıcı + CI
company/
  agents/prompts/    # her ajanın prompt'u (ajan düzenleyebilir)
  agents/memory/     # her ajanın hafızası (ajan düzenleyebilir)
  agents/logic/      # ajan mantığı Python dosyaları (ajan düzenleyebilir)
  data/              # fikstür, tahmin, sonuç, isabet JSON'ları
  minutes/           # tutanaklar, retrolar, haftalık raporlar
  koridor.md         # gayriresmi dedikodu kanalı
  log/               # hata ve olay kayıtları
site/                # GitHub Pages kaynağı (ajan düzenleyebilir)
docs/specs/          # bu doküman ve gelecek tasarımlar
```

## 4. Kadro (12 karakter)

Her ajan = prompt dosyası + hafıza dosyası; hepsini aynı çekirdek runner koşturur. Roller veridir — Süreç Sorumlusu prompt düzenleyerek şirketi evrimleştirir.

| Rol | Görev | Sıklık |
|---|---|---|
| Genel Müdür | Haftalık rapor, öncelikler, departman değerlendirmesi | Pazar |
| Scrum Master | Sprint/engel takibi, haftalık engel raporu (log'lardan) | Salı |
| Analist | Fikstür/sonuç çekme, maç brifingleri | Perşembe + Pazartesi |
| Tahminci: İstatistikçi | Veri diliyle skor tahmini + gerekçe | Cuma |
| Tahminci: Romantik | Sezgi/hikaye diliyle tahmin + gerekçe | Cuma |
| Tahminci: Soğukkanlı | Temkinli, düşük riskli tahmin + gerekçe | Cuma |
| Değerlendirici | Puanlama, isabet ligi güncelleme, retro | Pazartesi |
| Pesimist Eleştirmen | Her PR'a ve haftalık tahmin setine kötümser inceleme | PR başına + Cuma |
| Dedikoducu | koridor.md'yi süzüp haftalık "Koridor Kulisi" köşesi | Çarşamba |
| Tasarımcı | Sitenin görsel tasarımını evrimleştirir (öneri → geri bildirim → revizyon) | Salı + Cumartesi |
| Web Sorumlusu | İşlevsel site geliştirme: veri bağlama, sayfa mantığı, hata düzeltme | Haftada 2-3 |
| Süreç Sorumlusu | Retrolara göre diğer ajanların prompt'larını evrimleştirme | Salı |

### Dedikodu mekanizması (çift katman)

- Enjeksiyon: her ajan vardiyasında `koridor.md`'ye en fazla 1 satır bırakabilir ve son 10 satırı prompt'unda görür. Uzun vadeli davranış etkisi buradan gözlemlenir.
- Karakter: Dedikoducu kanalı süzüp köşe yazısı üretir (izlence katmanı).
- Ölçüm: isabet tablosu objektif metrik — dedikodunun tahmin kalitesine etkisi haftalık skorlarla izlenebilir. Ek metrik tutulmaz (YAGNI).

### Tasarım geri bildirim döngüsü

Tasarımcı görsel değişiklikleri tek başına birleştiremez; akış üç vardiyaya yayılır:

1. Salı: Tasarımcı değişikliği **draft PR** olarak açar (gerçek CSS/HTML + `minutes/` altına gerekçe: neyi neden değiştiriyorum). Draft PR'lar otomatik birleşme dışıdır — bekleme penceresi mekanik olarak buradan gelir, workflow değişikliği gerekmez.
2. Çarşamba–Perşembe: geri bildirim vardiyası — Pesimist Eleştirmen (zorunlu), Web Sorumlusu (uygulanabilirlik) ve rastgele seçilen 2 çalışan PR'a yorum yazar. Yorumlar koridor.md ile doğal etkileşir (Dedikoducu'ya malzeme).
3. Cumartesi: Tasarımcı yorumları okur, revize eder, draft'ı ready'ye çevirir → CI yeşilse otomatik birleşir. Hiç yorum gelmemişse revizyonsuz devam edebilir.

## 5. Haftalık ritim (Actions cron)

| Gün | Olay |
|---|---|
| Perşembe | Analist: fikstür + brifing; tasarım geri bildirimi tamamlanır |
| Cuma | 3 Tahminci: tüm 5 büyük lig maçlarına skor + gerekçe; Pesimist: set incelemesi |
| Cumartesi–Pazar | Maçlar oynanır (dış dünya); Cumartesi: Tasarımcı revizyon + birleşme |
| Pazartesi | Analist: sonuçlar; Değerlendirici: puanlama + retro |
| Salı | Süreç Sorumlusu: prompt evrimi PR'ları; Scrum Master: engel raporu; Tasarımcı: tasarım önerisi (draft PR) |
| Çarşamba | Dedikoducu: Koridor Kulisi; tasarım geri bildirimi başlar |
| Pazar | GM: haftalık rapor |
| Serbest | Web Sorumlusu haftada 2-3 vardiya |

Hafta ortası maçları (Şampiyonlar Ligi vb.) v1 kapsamı dışı; yalnızca 5 büyük ligin hafta sonu turları. Ara verilen haftalarda (milli ara) Analist "bu hafta maç yok" brifingi yazar, diğerleri normal çalışır.

## 6. Tahmin departmanı

- Veri: football-data.org bedava katmanı (PL, La Liga, Bundesliga, Serie A, Ligue 1 kapsanıyor; ~10 istek/dk limiti yeterli). Fikstür ve sonuç çekimi deterministik koddur, LLM değil.
- Puanlama (deterministik kod): kesin skor 3 puan, doğru sonuç (1X2) 1 puan, diğer 0. Kümülatif isabet ligi personalar arasında yarışır.
- Çıktı şeması: `{match_id, home, away, tahmin: "2-1", gerekce: "..."}` — JSON şema ile doğrulanır.
- Etik çerçeve: her tahmin sayfasında sabit not — "Eğlence amaçlıdır, bahis tavsiyesi değildir." Bahis/oran dili yasak (prompt kuralı + CI'da kelime kontrolü).

## 7. LLM katmanı

- Fallback zinciri: Groq → Google AI Studio (Gemini Flash) → OpenRouter bedava modelleri. Sıra ve model adları `company/models.json`'da (ajan düzenleyebilir; CI şema kontrolü var).
- Bütçe: ~150 tahmin çağrısı + ~50 diğer çağrı/hafta (tasarım döngüsü dahil); güne yayılır. Limit dolarsa zincir sıradakine düşer.
- Bozuk çıktı: şema doğrulama + 2 tekrar; olmadı iş atlanır, retroya not düşer.
- API anahtarları GitHub Actions secrets'ta (public repoda güvenli).

## 8. Öz-düzenleme ve güvenlik (mekanik anayasa)

- Ajanlar `company/` ve `site/` altındaki her şeyi değiştirebilir. Her değişiklik dal + PR.
- CI kapısı (yeşilse otomatik birleşme, insan yok): JSON şemaları · Python sözdizimi + mock LLM ile runner kuru-koşusu · HTML derlenirlik + kırık link kontrolü · bahis dili kontrolü · bekçi.
- Bekçi: `kernel/` veya `.github/workflows/` yoluna dokunan PR otomatik reddedilir.
- İkinci sigorta: Actions token'ına workflow yazma izni verilmez — ajan zamanlayıcıyı teknik olarak da değiştiremez.
- Süreç Sorumlusu'nun prompt PR'larında "değişiklik gerekçesi" alanı zorunlu; `/degisiklikler` sayfasına dökülür.
- Kırmızı kalan PR 7 gün sonra otomatik kapanır.
- Pesimist Eleştirmen her PR'a yorum düşer (danışma niteliğinde; birleşmeyi CI belirler).
- Geri dönüş: her şey git'te — felaket halinde izleyici (insan) tek komutla revert edebilir, ama akışın hiçbir yerinde insan onayı beklenmez.

## 9. Site

Statik, framework yok, tek CSS dosyası, tek harici kütüphane Chart.js.

| Sayfa | İçerik |
|---|---|
| `/` | Şirket panosu: son olaylar akışı (commit'lerden), departman kartları |
| `/tahmin` | Haftanın tahminleri + gerekçeler, persona isabet ligi (grafik), arşiv |
| `/ofis` | Ajan profilleri (prompt'lar açık), tutanaklar, retrolar, Koridor Kulisi |
| `/degisiklikler` | Öz-düzenleme geçmişi: kim, neyi, neden değiştirdi |

Her bölümde "gerçek üretim / kurgu" rozeti. Tahmin sayfasında sorumluluk reddi sabit.

## 10. Hata yönetimi

- LLM sağlayıcı hatası/limit: zincirde sıradakine geç; tümü ölürse vardiya "izinli" — siteye "bugün ofis sessizdi" düşülür.
- football-data hatası: önceki fikstür önbelleği; tahmin ertelenir.
- Tüm hatalar `company/log/` altına; Scrum Master haftalık engel raporunda listeler.
- Runner'ın kendisi çökerse: Actions job'u kırmızı olur, bir sonraki cron temiz durumdan tekrar dener (runner durumsuz tasarlanır).

## 11. Test stratejisi

- Kernel: pytest, tam kapsam (küçük olduğu için ucuz).
- Şema testleri: tahmin/fikstür/models JSON'ları.
- Site: HTML doğrulama + kırık link.
- Ajan mantığı: mock LLM ile uçtan uca kuru koşu.
- Bunların tamamı CI'dadır — ajan öz-düzenlemelerinin bekçisi bu testlerdir.

## 12. Fazlar

- Faz 0 (bootstrap, Claude yapar): repo iskeleti, kernel, CI, ilk prompt seti, site v0, kurulum talimatı. Şirketin adını ilk vardiyada ajanlar seçer.
- Faz 1: tahmin masası canlı (sezon Ağustos 2026'da başladı — zamanlama uygun).
- Faz 2+: oyuncak stüdyosu → sanat galerisi → kurgu simülasyonu (sıra GM raporlarına göre esneyebilir; yeni departman = yeni prompt seti + site sekmesi, mimari değişmez).
- Opsiyonel (karar ertelendi): Kaggle zamanlanmış notebook ile haftalık ağır iş (ör. daha büyük açık model ile "yönetim kurulu" özel bölümü); yerel Ollama fırsatçı katmanı. Colab otomasyonu kullanım şartlarına aykırı — kullanılmayacak.

## 13. Kullanıcının tek seferlik kurulum yükü (~20 dk)

1. GitHub'da public repo aç, Pages'i etkinleştir.
2. Bedava anahtarları al: Groq, Google AI Studio, OpenRouter, football-data.org.
3. Dördünü Actions secrets olarak ekle.
4. İlk workflow'u elle bir kez tetikle. Sonrası tamamen otonom.

## 14. Faz 0 uygulama notları (spec'ten bilinçli sapmalar)

- Koridor `koridor.md` yerine `company/koridor/` klasöründe satır-başına-dosya tutulur: aynı gün açılan PR'ların tek dosyada çakışmasını (merge conflict) önler. "Son 10 satır" = ada göre son 10 dosya.
- Tasarımcı roster'da yalnız Salı görünür; Cumartesi revizyonu ve Çarşamba-Perşembe geri bildirimi vardiya workflow'unun özel adımlarıdır (taslak PR mekaniği gh CLI ister, kernel LLM işine odaklı kalır).
- v1'de tasarım geri bildirimcileri sabittir: Pesimist + Web Sorumlusu + Romantik (rastgele seçim için durum tutmak gerekirdi; YAGNI).
- Web Sorumlusu ve Süreç Sorumlusu, Tasarımcı ile aynı `editor` mantığını farklı izinli alanlarla paylaşır (`alan` alanı roster'da).
- Pesimist'in "her PR'a yorum" görevi v1'de tasarım PR'ları + Cuma tahmin seti incelemesiyle sınırlıdır.
- Çekirdek toplamı ~300 satırdır (runner + llm istemcisi); dokunulmazlık sınırı değişmedi.
