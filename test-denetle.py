#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DENETCININ KENDI TESTI — `denetle.py` gercekten yakaliyor mu?

    python test-denetle.py

Neden var: `denetle.py` sitenin mevzuat bekcisi. Bekcinin sessizce
korlesmesi, hic bekci olmamasindan daha tehlikeli — cunku "TAMAM"
yaziyor ve kimse bakmiyor. 2. tur Codex denetiminde tam bu cikti:
muafiyet mantigi butun yasak siniflarina uygulaniyordu ve
`alt="En iyi diş kliniği"` gibi oznitelikler hic taranmiyordu.

Her duzeltilen bulgu icin buraya bir KIRMIZI ornek (yakalanmali) ve
bir YESIL ornek (yanlis alarm vermemeli) eklenir.
"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import mevzuat  # noqa: E402  — desenlerin tek kaynagi

sonuc = []


def bekle(ad, html, yakalanmali, ipucu=""):
    """yakalanmali=True  -> mevzuat_tara EN AZ bir sorun bulmali
       yakalanmali=False -> hic sorun bulmamali (yanlis alarm yok)"""
    sorunlar = mevzuat.mevzuat_tara(html, "test")
    gecti = bool(sorunlar) == yakalanmali
    if not gecti:
        ipucu = ("BEKLENEN: %s · BULUNAN: %s"
                 % ("yakala" if yakalanmali else "temiz",
                    sorunlar[:2] or "temiz"))
    sonuc.append((ad, gecti, ipucu))


def sar(govde):
    """Test parcasini gercekci bir HTML iskeletine oturtur."""
    return ("<!DOCTYPE html><html lang=\"tr\"><head>"
            "<meta charset=\"utf-8\"><title>Test</title></head>"
            "<body>%s</body></html>" % govde)


# --- 2. tur bulgu 5: MUAF fail-open ------------------------------------
# Fiyat aciklamasi TEK BASINA gecmeli.
bekle("muaf: fiyat aciklamasi tek basina gecer",
      sar("<p>Fiyat bilgisini mevzuat gereği yayımlayamıyoruz.</p>"),
      False)

# Ayni metne eklenen "en iyi" AFFEDILMEMELI. Eski kod bunu geciriyordu.
bekle("muaf: yakindaki fiyat aciklamasi 'en iyi'yi AFFETMEZ",
      sar("<p>Fiyat bilgisini yayımlayamıyoruz. En iyi kliniğiz.</p>"),
      True)

# Ayni sekilde bagimsiz bir "kampanya" da affedilmemeli.
bekle("muaf: yakindaki aciklama 'kampanya'yi AFFETMEZ",
      sar("<p>Fiyat bilgisini yayımlayamıyoruz. Kampanyamız başladı.</p>"),
      True)

# Muafiyet AYNI CUMLEDE calismaya devam etmeli.
bekle("muaf: ayni cumlede ucret aciklamasi gecer",
      sar("<p>Ücret bilgisini mevzuat gereği paylaşamıyoruz.</p>"),
      False)

# --- 2. tur bulgu 6: oznitelikler taranmiyordu -------------------------
bekle("oznitelik: img alt icindeki 'en iyi' yakalanir",
      sar('<img src="a.jpg" alt="En iyi diş kliniği">'),
      True)

bekle("oznitelik: aria-label icindeki 'ucretsiz' yakalanir",
      sar('<button aria-label="Ücretsiz muayene">Tıkla</button>'),
      True)

bekle("oznitelik: title icindeki fiyat rakami yakalanir",
      sar('<a href="#" title="Muayene 500 TL">Bilgi</a>'),
      True)

bekle("oznitelik: placeholder icindeki 'garanti' yakalanir",
      sar('<input placeholder="Garantili tedavi">'),
      True)

bekle("oznitelik: masum alt metni yanlis alarm vermez",
      sar('<img src="a.jpg" alt="Kliniğin haritadaki konumu">'),
      False)

# --- 2. tur bulgu 7: ortulu ticari dil ---------------------------------
for kelime, ornek in [
        ("ucuz", "Ucuz implant seçenekleri"),
        ("hesapli", "Hesaplı tedavi imkânı"),
        ("ekonomik", "Ekonomik çözümler sunuyoruz"),
        ("ek bedel", "Gece geldiğinizde ek bedel yok"),
        ("gece farki", "Gece farkı almıyoruz"),
        ("fiyat farki", "Hafta sonu fiyat farkı uygulanmaz")]:
    bekle("ortulu ticari: '%s' yakalanir" % kelime,
          sar("<p>%s</p>" % ornek), True)

# "pahali" BILEREK desende yok — mecazi kullanimi var.
bekle("ortulu ticari: mecazi 'pahali' yanlis alarm vermez",
      sar("<p>Bu, çocuk diş hekimliğindeki en pahalı yanılgıdır.</p>"),
      False)

# Sitedeki gercek cumle gecmeli: uygulama beyani, fiyat beyani degil.
bekle("gercek metin: 'farkli uygulamaya tabi tutulmazsiniz' gecer",
      sar("<p>Gece ya da hafta sonu gelmeniz uygulanan işlemlerde bir "
          "farklılık oluşturmaz; geç saatte geldiniz diye farklı bir "
          "uygulamaya tabi tutulmazsınız.</p>"),
      False)

# --- 1. turdan gelen korumalar hala calisiyor mu? ----------------------
bekle("gerileme: ortuk agrisizlik yakalanir",
      sar("<p>İşlem sırasında ağrı hissetmezsiniz.</p>"), True)

bekle("gerileme: satir sonu ihlali gizleyemez",
      sar("<p>İşlem sırasında ağrı\n   beklenmez.</p>"), True)

bekle("gerileme: head icindeki ihlal yakalanir",
      "<!DOCTYPE html><html><head><meta name=\"description\" "
      "content=\"Bağcılar'ın en iyi kliniği\"></head><body><p>x</p>"
      "</body></html>", True)

bekle("gerileme: JSON-LD icindeki ihlal yakalanir",
      sar('<script type="application/ld+json">'
          '{"@type":"Dentist","description":"Garantili tedavi"}</script>'),
      True)

bekle("gerileme: puan beyani yakalanir",
      sar('<script type="application/ld+json">'
          '{"aggregateRating":{"ratingValue":"5"}}</script>'), True)

bekle("gerileme: telefon numarasi yanlis alarm vermez",
      sar("<p>Bize 0541 732 43 76 numarasından ulaşabilirsiniz.</p>"),
      False)

bekle("gerileme: 'uzmanimiz' iddiasi yakalanir",
      sar("<p>Uzmanımız sizi bekliyor.</p>"), True)

bekle("gerileme: sade bilgilendirme metni temiz gecer",
      sar("<p>Kanal tedavisi lokal anestezi altında yapılır. İşlem "
          "sonrasında birkaç gün çiğneme hassasiyeti olabilir.</p>"),
      False)

print("=" * 70)
print("DENETCI TESTI — denetle.py gercekten yakaliyor mu?")
print("=" * 70)
g = 0
for ad, ok, n in sonuc:
    print("  %s %-52s %s" % ("GECTI " if ok else "KALDI!", ad, n))
    g += 1 if ok else 0
print("=" * 70)
print("%d/%d gecti" % (g, len(sonuc)))
sys.exit(0 if g == len(sonuc) else 1)
