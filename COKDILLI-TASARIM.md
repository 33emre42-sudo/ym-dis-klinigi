# Çok dilli site — tasarım kararları

**Karar tarihi:** 3 Ağustos 2026
**Hekim kararı:** önce **yalnız İngilizce**, tam set kurulacak, ölçülecek,
işe yararsa diğer 4 dile çoğaltılacak (ES/FR/DE/RU).
**Öne çıkan işlemler:** implant · kaplama/estetik · kanal tedavisi ve
genel tedaviler.

---

## Bu bir "siteyi çevirme" işi DEĞİL

33 bilgi yazısı **yerel arama niyetine** göre yazıldı: *"gece diş ağrısı
Bağcılar"*, *"nöbetçi dişçi"*. Almanya'dan implant için gelmeyi düşünen
biri bunları aramıyor. Onun soruları başka:

- Hangi işlemler yapılıyor, kim yapıyor
- **Kaç gün kalmam gerekir**, kaç ziyaret
- Ülkeme döndükten sonra kontrol nasıl olacak
- Bir sorun çıkarsa ne oluyor
- Klinik nerede, havalimanından nasıl gelinir

Yani çeviri değil, **amaca özel yeni içerik**. 41 sayfayı olduğu gibi
çevirmek 160.000 kelimelik, yabancı hastaya hitap etmeyen bir yığın
üretirdi.

## ⚠️ Fiyat gerçeği — baştan kabul edilmiş sınır

Hasta turizminin en çok konuşulan konusu fiyat ve biz **hiçbir dilde**
fiyattan söz edemeyiz (K15). Rakipler bunu yapıyor olabilir; girmiyoruz.

Bu yüzden konumlanma fiyat değil **güven** üzerine kurulacak: süreç
şeffaflığı, hekim adı ve doğru unvanı, 7/24 erişilebilirlik, dönüş
sonrası iletişim. Bunlar mevzuata uygun ve gerçekten ayırt edici.

⚠️ Kaplama/estetik bölümü **sonuç vaadi sınırına en yakın** alan.
"Gülüşünüzü yenileyin" tarzı dil kolayca vaade kayıyor. Bu bölüm
yazılırken çok dilli tarayıcı (`YASAKLI_COKDILLI`) tek başına yetmez —
anlam kontrolü şart.

## Sıralama — neden hemen değil

Şu an **41 sayfanın 1'i** Google'da. 7 günlük alan adına yeni URL
yığmak tarama sırasını iyileştirmez, dağıtır. İngilizce bölüm Türkçe
taraf dizine girmeye başladıkça açılacak. Hekim de "acelesi yok" dedi.

---

## Mimari kararlar

| Konu | Karar | Gerekçe |
|---|---|---|
| URL yapısı | `ymdisklinigi.com/en/...` alt klasör | Alt alan adı ya da ayrı alan adı otoriteyi böler. Küçük site için alt klasör en iyisi. |
| `hreflang` | Her sayfada TR ↔ EN çifti + `x-default=TR` | Olmadan Google iki sürümü yinelenen sayar ve birini düşürür. |
| canonical | Her sayfa **kendine** | EN sayfa TR'yi canonical gösterirse dizine hiç girmez. |
| Dil geçişi | Görünür bağlantı, otomatik yönlendirme **YOK** | IP'ye göre otomatik yönlendirme Googlebot'u da yönlendirir ve tarama bozulur. |
| Sitemap | Aynı `sitemap.xml`, `xhtml:link` ile | Ayrı sitemap gerekmez; 41+8 URL tek dosyada rahat. |
| Çeviri kaynağı | Elle yazılacak | Makine çevirisi tıbbi metinde hem yanlış hem mevzuat riski. |

## Sayfa seti (İngilizce, 8 sayfa)

1. `/en/` — ana sayfa: kim, nerede, ne yapıyoruz, 7/24
2. `/en/dental-implants.html`
3. `/en/crowns-and-veneers.html` ⚠️ vaat dili riski yüksek
4. `/en/root-canal-and-general-dentistry.html`
5. `/en/treatment-planning-and-your-stay.html` — kaç gün, kaç ziyaret,
   dönüş sonrası kontrol
6. `/en/our-dentists.html` — Dt. Yunus Emre Çetin, Dt. Mert Daştan,
   **genel diş hekimi** (K38 — "specialist" kelimesi geçmeyecek)
7. `/en/getting-here.html` — havalimanı, metro, adres
8. `/en/contact.html`

## ⚠️ Denetim yolu — içerikten ÖNCE kurulacak

`denetle.py` içinde **bilerek** bir kapı var: alt klasördeki her HTML
denetimi **durduruyor** (`denetlenmeyen HTML yok`). Bu kapı bir dış
denetim bulgusuydu ve doğrulanmıştı: içinde "garanti", "5000 TL",
"%20 indirim" geçen bir alt klasör sayfası denetimden geçmişti.

Yani `en/` klasörü açılır açılmaz denetim kırmızıya döner — **bu doğru
davranış.** Kapıyı gevşetmek yasak. Yapılacak:

- `EN_SAYFA` listesi eklenecek ve `_beklenen` kümesine girecek
- İngilizce sayfalar için **ayrı sorumluluk notu deseni** gerekiyor;
  mevcut kontrol Türkçe `TIBBİ İÇERİK KONTROLÜ...` metnini arıyor
- Acil eşiği kontrolü (`acil_esik_hatalari`) Türkçe desenlere dayalı —
  İngilizce karşılığı yazılmadan İngilizce acil içerik yayınlanmamalı.
  **Bu yüzden ilk sette acil/gece içeriği YOK**; turizm sayfaları
  planlı tedaviyi anlatıyor, acil yönlendirmeyi değil.
- `hreflang` çiftlerinin karşılıklı olduğu denetlenecek (tek yönlü
  `hreflang` Google tarafından yok sayılıyor)

## Yapıldı (3 Ağustos)

✅ **Mevzuat kapısı 6 dile açıldı** — sayfalardan önce. `YASAKLI_COKDILLI`:
sonuç vaadi, fiyat/ticari dil, hasta yorumu, önce-sonra, uzmanlık
iddiası; EN/ES/FR/DE/RU. 18 test (`test-denetle.py` 159 → 177).

Bu sıra bilinçliydi: tersi olsaydı ilk İngilizce sayfa **denetimsiz**
yayına girerdi. Bugüne kadarki bütün koruma Türkçe desenlerdi;
*"painless treatment"* yazan bir sayfa denetimden geçerdi.

⚠️ Kurarken gerçek bir yanlış alarm yakalandı: Fransızca `tarif` deseni
Türkçe **"tarif"** kelimesini yakalayıp yayındaki `sut-disi-curugu.html`
sayfasını kırmızıya döndürdü. Desen daraltıldı, iki yönlü teste bağlandı.

## Sırada

1. `denetle.py`'ye İngilizce denetim yolu (yukarıdaki dört madde)
2. İngilizce sayfaların metinleri — **hekim onayına sunulacak**
   (dışarı çıkan içerik = DURAK)
3. `hreflang` + sitemap güncellemesi
4. Yayın, sonra Search Console'da İngilizce sayfalar için dizine ekleme
5. Ölçüm: hangi sayfa arama alıyor. İşe yararsa ES/FR/DE/RU.
