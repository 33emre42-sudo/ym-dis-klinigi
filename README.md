# 7/24 Nöbetçi YM Diş Kliniği — tanıtım sitesi

Yayında: <https://ymdisklinigi.com>

## Dosyalar elle düzenlenir

`index.html` **tek gerçek kaynaktır.** Doğrudan düzenleyin.

> Eskiden `hasta-mesajlari/klinik-sitesi-olustur.py` bu dosyayı
> üretiyordu. Site elle geliştirildikçe üretici geride kaldı ve
> ikisi ayrıştı; üretici 1 Ağustos 2026'da arşivlendi
> (`hasta-mesajlari/arsiv/OKU-ONCE.md`). Çalıştırmayın — mevzuata
> aykırı puan/yorum beyanını geri getirir.

## Her değişiklikten sonra

    python denetle.py

Denetleyici beş başlıkta kontrol eder:

1. **JSON-LD** — `Dentist` ve `FAQPage` blokları geçerli mi
2. **SSS eşleşmesi** — şemadaki her soru/cevap sayfada birebir var mı
   (Google, şemadaki cevabın kullanıcıya da görünmesini şart koşuyor)
3. **Etiket dengesi** — açılan her etiket kapanmış mı
4. **Mevzuat** — 12 Kasım 2025 tanıtım yönetmeliği taraması: fiyat,
   kampanya, "en iyi", garanti, hasta yorumu, önce/sonra, puan beyanı.
   Bir yasaklı kelime "yapamıyoruz" bağlamında geçiyorsa muaf tutulur.
5. **İçerik** — kelime sayısı, bölümlerin varlığı, canonical, açıklama

Denetim hata verirse **düzeltmeden yayına almayın.**

## Yayına alma

    cd ../hasta-mesajlari
    python sunucuya-yukle.py

## Mevzuat sınırları (kısa)

Sitede **olamaz**: fiyat, indirim, kampanya, taksit · hasta yorumu,
memnuniyet beyanı, puan · önce/sonra görseli · "en iyi", "garanti",
"ağrısız" gibi sonuç vaadi.

Sitede **olabilir**: koruyucu ve bilgilendirici içerik, sunulan
hizmetlerin tanıtımı olmadan anlatımı, adres/saat/ulaşım, iletişim.

## Bu depoda hasta verisi yoktur

Hasta kayıtları ve `.env` dosyaları **hiçbir zaman** buraya girmez.
Depo herkese açıktır.
