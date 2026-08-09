#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Klinik şemasını bütün sayfalara yayar.

    python sema-yay.py            # ne değişecek, yazar
    python sema-yay.py --uygula   # uygular

NEDEN VAR — 9 Ağustos 2026'da ölçüldü:

15 rakip klinik ölçüldü (`hasta-mesajlari/RAKIP-HARITASI.md`). Sonuç:

    şemada koordinat            0 / 15 rakip
    şemada 7 gün 24 saat        0 / 15 rakip
    llms.txt                    0 / 10 ölçülen

Yani "Bağcılar'da gece açık diş kliniği" sorusunun makine okunur
cevabı bölgede YALNIZ BIZDE var. Ama kendi tarafımızda da yarım:

    "@type":"Dentist"           1 / 78 sayfa   (yalnız index.html)
    openingHoursSpecification   1 / 78
    GeoCoordinates              1 / 78

Beş dildeki 35 sayfada tek şema tipi `WebPage`. Yani tek gerçek
üstünlüğümüz yabancı dilde makine tarafında HİÇ görünmüyor.

⚠️ SORUN "atıf var, tanım yok" idi. Bilgi sayfaları klinik kimliğine
zaten atıfta bulunuyordu:

    "author":{"@id":"https://ymdisklinigi.com/#klinik"}

ama o kimliği YALNIZ `index.html` tanımlıyordu. Bir tarayıcı ya da
yapay zekâ doğrudan `gece-dis-agrisi.html` sayfasına düştüğünde,
çözemediği bir kimliğe bakıyordu.

⛔ YENİ İDDİA ÜRETMEZ. Eklenen düğüm, ana sayfada ZATEN yazılı olan
olguların (ad, adres, telefon, koordinat, çalışma saati) aynı `@id`
altında tekrarıdır. Aynı `@id` = aynı varlık; arama motorları bunu
birleştirir, 78 ayrı klinik OLUŞMAZ.

⛔ DEĞERLER ELLE YAZILMAZ. Hepsi `index.html`in kendi şemasından
okunur — aksi halde ana sayfa güncellenince 77 sayfa sessizce
bayatlardı. `denetle.py` bu tazeliği ayrıca denetliyor.
"""
import glob
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

KOK = os.path.dirname(os.path.abspath(__file__))
KAYNAK = "index.html"
KLINIK_ID = "https://ymdisklinigi.com/#klinik"

# Derli toplu düğüme giren alanlar. "Kim, nerede, ne zaman açık"
# sorusunu karşılayan asgari küme — `availableService`, `employee`,
# `image` gibi ağır alanlar ana sayfada kalır.
ALANLAR = ("@type", "@id", "name", "alternateName", "url", "telephone",
           "address", "geo", "openingHoursSpecification")

ISARET = "<!-- klinik-semasi: sema-yay.py uretir, ELLE DUZENLEME -->"


def _oku(yol):
    with io.open(yol, encoding="utf-8") as f:
        return f.read()


def klinik_dugumu():
    """`index.html`teki klinik düğümünü bulur ve derli toplu hâlini döner."""
    s = _oku(os.path.join(KOK, KAYNAK))
    for blok in re.findall(
            r'<script type="application/ld\+json">(.*?)</script>', s, re.S):
        try:
            d = json.loads(blok)
        except ValueError:
            continue
        adaylar = d.get("@graph", [d]) if isinstance(d, dict) else d
        if not isinstance(adaylar, list):
            adaylar = [adaylar]
        for n in adaylar:
            if isinstance(n, dict) and n.get("@id") == KLINIK_ID:
                derli = {"@context": "https://schema.org"}
                for a in ALANLAR:
                    if a in n:
                        derli[a] = n[a]
                return derli
    return None


def _etiket(dugum):
    return ('%s\n<script type="application/ld+json">\n%s\n</script>'
            % (ISARET, json.dumps(dugum, ensure_ascii=False,
                                  separators=(",", ":"))))


def sayfalar():
    """index.html DIŞINDAKİ bütün HTML sayfaları."""
    return sorted(
        y for y in glob.glob(os.path.join(KOK, "**", "*.html"), recursive=True)
        if os.path.basename(y) != KAYNAK or os.path.dirname(y) != KOK)


def main():
    uygula = "--uygula" in sys.argv
    dugum = klinik_dugumu()
    print("=" * 68)
    print("KLINIK SEMASINI SAYFALARA YAY")
    print("=" * 68)
    if not dugum:
        print("  🔴 index.html icinde %s bulunamadi — DURDU." % KLINIK_ID)
        return 2
    print("  kaynak      : %s (@id %s)" % (KAYNAK, KLINIK_ID))
    print("  alanlar     : %s" % ", ".join(k for k in dugum if k != "@context"))
    print("  dugum boyu  : %d bayt"
          % len(json.dumps(dugum, ensure_ascii=False).encode("utf-8")))

    etiket = _etiket(dugum)
    eklenecek, guncellenecek, atlanan, kafasiz = [], [], [], []
    for yol in sayfalar():
        s = _oku(yol)
        ad = os.path.relpath(yol, KOK).replace(os.sep, "/")
        if "</head>" not in s:
            # ⚠️ Sessizce atlanmaz: <head>i olmayan sayfa varsa bilinmeli.
            kafasiz.append(ad)
            continue
        if ISARET in s:
            mevcut = re.search(
                re.escape(ISARET) +
                r'\s*<script type="application/ld\+json">\s*(.*?)\s*</script>',
                s, re.S)
            if mevcut and mevcut.group(1).strip() == json.dumps(
                    dugum, ensure_ascii=False, separators=(",", ":")):
                atlanan.append(ad)
            else:
                guncellenecek.append(ad)
        else:
            eklenecek.append(ad)

    print("")
    print("  eklenecek   : %3d sayfa" % len(eklenecek))
    print("  tazelenecek : %3d sayfa (bayat kopya)" % len(guncellenecek))
    print("  zaten guncel: %3d sayfa" % len(atlanan))
    if kafasiz:
        print("  ⚠️ <head> YOK  : %d sayfa — %s"
              % (len(kafasiz), ", ".join(kafasiz[:3])))

    if not (eklenecek or guncellenecek):
        print("\n  Yapacak bir sey yok.")
        return 0
    if not uygula:
        print("\n  KURU CALISMA — uygulamak icin --uygula")
        return 0

    n = 0
    for ad in eklenecek + guncellenecek:
        yol = os.path.join(KOK, ad.replace("/", os.sep))
        s = _oku(yol)
        if ISARET in s:
            s = re.sub(
                re.escape(ISARET) +
                r'\s*<script type="application/ld\+json">.*?</script>\s*',
                "", s, flags=re.S)
        s = s.replace("</head>", etiket + "\n</head>", 1)
        with io.open(yol, "w", encoding="utf-8", newline="") as f:
            f.write(s)
        n += 1
    print("\n  YAZILDI: %d sayfa" % n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
