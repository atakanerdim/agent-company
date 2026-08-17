# Kurulum (tek seferlik, ~20 dakika)

Önkoşul: 4 API anahtarın hazır (Groq, Google AI Studio, OpenRouter, football-data.org).

## 1. Repoyu aç ve kodu gönder

GitHub'da **public** bir repo aç: `otonom-studyo` (README'siz, boş).
Sonra bu klasörde:

```bash
git remote add origin https://github.com/KULLANICI_ADIN/otonom-studyo.git
git push -u origin main
```

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
