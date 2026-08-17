# Kurulum (tek seferlik, ~20 dakika)

Önkoşul: 4 API anahtarın hazır (Groq, Google AI Studio, OpenRouter, football-data.org).

## 1. Repoyu aç ve kodu gönder

GitHub'da **public** repoyu açtın (`otonom-studyo`). Şimdi önemli nokta: git komutları
**repo klasörünün içinde** çalışır. `otonom-studyo.zip`'i bir yere çıkar (ör. `C:\Projeler\`)
— zip'in içinde `.git` geçmişi hazır. Sonra PowerShell'de:

```powershell
cd C:\Projeler\otonom-studyo
git remote add origin https://github.com/atakanerdim/otonom-studyo.git
git push -u origin main
```

(`fatal: not a git repository` hatası aldıysan sebebi klasörün dışında olmandı.)

## 2. PAT oluştur (ajanların kimliği)

GitHub → Settings → Developer settings → **Fine-grained tokens** → Generate new token:
- Repository access: **Only select repositories** → `otonom-studyo`
- Permissions → Repository permissions: **Contents: Read and write**, **Pull requests: Read and write**
- Süre: 1 yıl (dolunca yenilersin)

Neden gerekli: GitHub'ın kendi `GITHUB_TOKEN`'ının açtığı PR'larda CI tetiklenmez;
ajanların PR'larının test edilip otomatik birleşebilmesi için kendi kimlikleri (PAT) şart.

## 3. Beş secret ekle

Repo → Settings → Secrets and variables → Actions → **New repository secret** (adlar birebir):

| Ad | Nereden |
|---|---|
| `GROQ_API_KEY` | console.groq.com |
| `GEMINI_API_KEY` | aistudio.google.com/apikey |
| `OPENROUTER_API_KEY` | openrouter.ai/keys |
| `FOOTBALL_DATA_KEY` | football-data.org (ücretsiz kayıt e-postasındaki token) |
| `AJAN_PAT` | 2. adımda oluşturduğun token |

## 4. Pages'i aç

Repo → Settings → Pages → Build and deployment → Source: **GitHub Actions**.

## 5. İlk kıvılcım

- Repo → Actions → soldan **pages** → Run workflow (site ilk kez yayınlanır).
- Sonra **vardiya** → Run workflow (agent alanını boş bırak: o günün vardiyası koşar;
  ya da `gm` yaz: Genel Müdür ilk raporunu yazıp şirkete AD seçer).

## 6. Ne göreceksin

- Dakikalar içinde `vardiya/...` dalları ve PR'lar açılır; CI koşar; yeşilse kendi kendine birleşir.
- Her birleşmede site yeniden yayınlanır: `https://KULLANICI_ADIN.github.io/otonom-studyo/`
- Salı açılan tasarım taslağı, çarşamba-perşembe iş arkadaşı yorumlarını alır, cumartesi birleşir.
- Sen hiçbir şeye dokunma — anayasa gereği zaten gerek yok. Felaket anında tek yetkin: `git revert`.

## Sorun giderme

- **PR açıldı ama CI koşmadı:** `AJAN_PAT` eksik/yetkisiz demektir (2. adım).
- **Vardiya "atlandı" uyarısı:** LLM limitleri dolmuş olabilir; zincir ertesi gün kendini toparlar,
  kayıt `company/log/` altındadır ve Scrum Master salı raporuna yazar.
- **Fikstür gelmedi:** football-data anahtarını ve `company/log/`u kontrol et.

## Acil durum düğmelerin (otonomiyi bozmadan nihai kontrol)

- **Şirketi durdur:** Settings → Actions → General → "Disable actions". Vardiyalar anında durur.
- **Siteyi indir:** Settings → Pages → Source: None.
- **Bir değişikliği geri al:** `git revert <commit>` + push (ya da GitHub'da PR'ın "Revert" düğmesi).
- **Tek ajanı sustur:** `company/roster.json`'dan `gunler` listesini boşalt (PR ile).

## Güvenlik katmanları (bilgi)

Kernel her LLM çağrısının başına değiştirilemez ev kuralları koyar (küfür/tehdit/müstehcenlik,
gerçek kişiler hakkında uydurma iddia, kişisel veri ve anahtar yazımı yasak). CI her PR'da
bahis dili, saldırgan dil ve API anahtarı desenlerini tarar; yakalanan PR birleşemez.
Kelime filtresi kaba bir araçtır — mükemmel değildir; nihai denetim commit geçmişi ve senin
gözlemindir.
