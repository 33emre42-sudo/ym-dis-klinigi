# 7/24 Nöbetçi YM Diş Kliniği — tanıtım sitesi

Yayında: <https://ymdisklinigi.com>

## ⚠️ Buradaki dosyaları elle düzenlemeyin

`index.html`, `CNAME`, `robots.txt` ve `sitemap.xml` **otomatik üretiliyor**.
Elle yaptığınız değişiklik, üretici bir daha çalıştığında silinir.

Değişiklik yapmak için üreticiyi düzenleyin:

    Klinik/hasta-mesajlari/klinik-sitesi-olustur.py

sonra çalıştırın:

    python klinik-sitesi-olustur.py

Üretici, yazmadan önce iki denetim yapıyor:

* **K15** — sayfada fiyat / ödeme / kampanya dili geçemez. Geçerse site
  **yazılmaz**, hata verir.
* **Emoji** — sayfada emoji olmayacak (tasarım kararı).

Sık değiştirilen yerler üreticinin başında duruyor:

| Ne | Nerede |
|---|---|
| Telefon, adres, alan adı | `K` sözlüğü |
| Hastaya gösterilen sorular | `SORULAR` listesi |
| Tedavi kategorileri ve açıklamaları | `KATEGORI` sözlüğü |

Tasarım kararlarının gerekçeleri (hangi başlık neden elendi, renk neden
değişti) dosyanın en üstündeki açıklama bloğunda yazılı.

## Bu depoda hasta verisi yoktur

Hasta kayıtları ve `.env` dosyaları **hiçbir zaman** buraya girmez.
Depo herkese açıktır.
