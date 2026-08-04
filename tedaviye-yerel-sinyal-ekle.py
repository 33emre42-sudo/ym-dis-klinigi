#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tedavi sayfalarina YEREL SINYAL ekler: baslik + gorunur hizmet satiri.

SORUN (4 Agu 2026 olcumu):
Dokuz tedavi sayfasinin hepsi 740-1080 kelime, icerik derinligi
rakiplerle kiyaslanabilir. Ama HICBIRI gosterim almiyor.

Sebep basliklar. Hepsi yalnizca BILGI amacli:
    "İmplant Tedavisi Adım Adım: Süreç Nasıl İşler?"
    "Kanal Tedavisi: Dişi Çekmeden Kurtarmak"

Bunlar "implant nasil yapilir" sorusunu hedefliyor, "Bağcılar implant"
sorgusunu degil. 35 sayfa icinde basliginda ilce gecen TEK sayfa
`nobetci-dis-hekimi-acil-dis.html` — ve siralandigimiz sorgular tam
onun hedefindekiler. Tesaduf degil.

Rakipler bunu yapiyor:
    "Lost Dent Ağız ve Diş Sağlığı Polikliniği - Bahçelievler Diş"
    "MCT Ağız ve Diş Sağlığı Polikliniği – Bağcılar Nöbetçi..."

⚠️ MEVZUAT: eklenen satir HIZMET ANLATIMI ve ADRES — ikisi de serbest.
Fiyat, kampanya, ustunluk iddiasi, "uzman" YOK. Yeni tibbi iddia da
yok; sayfanin tibbi icerigine dokunulmuyor.

⚠️ Riski dusuk: bu sayfalar su an SIFIR gosterim aliyor. Kaybedecek
sira yok.
"""
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
KOK = os.path.dirname(os.path.abspath(__file__))

EK = " | Bağcılar Diş Kliniği"

# Gorunur gövde satiri — sayfanin SONUNDAKI cagri bolumunden ONCE.
# "Bu tedavi kliniğimizde uygulanır" + adres. Hizmet anlatimi + adres.
SATIR = ('<p class="yerel-not">Bu tedavi kliniğimizde uygulanmaktadır. '
         'Adres: Kirazlı Mah. Mevlana Cad. No: 47 D, Bağcılar / '
         'İstanbul — Kirazlı Metro yakınında, her gün 24 saat açık.</p>')

TEDAVI = [
    "dis-dolgusu.html", "kanal-tedavisi.html", "dis-cekimi.html",
    "implant-sureci.html", "protez-kaplama.html", "dis-teli-ortodonti.html",
    "cocukta-ilk-dis.html", "diseti-cekilmesi.html",
    "dis-tasi-temizligi.html",
]


def main():
    kontrol = "--kontrol" in sys.argv
    bas = govde = 0
    sorun = []

    for ad in TEDAVI:
        yol = os.path.join(KOK, ad)
        if not os.path.isfile(yol):
            sorun.append("%s: DOSYA YOK" % ad)
            continue
        t = io.open(yol, encoding="utf-8").read()
        yeni = t

        # --- 1) baslik --------------------------------------------------
        m = re.search(r"<title>([^<]*)</title>", yeni)
        if not m:
            sorun.append("%s: <title> yok" % ad)
        elif EK.strip() in m.group(1):
            pass                                  # zaten var
        else:
            eski_b = m.group(0)
            yeni_b = "<title>%s%s</title>" % (m.group(1).rstrip(), EK)
            yeni = yeni.replace(eski_b, yeni_b, 1)
            # og:title ve twitter:title de ayni olmali; ayrisirsa
            # paylasimda baska, aramada baska baslik gorunur.
            for oz in ('property="og:title"', 'name="twitter:title"'):
                yeni = re.sub(
                    r'(<meta %s content=")([^"]*)(")' % re.escape(oz),
                    lambda k: k.group(1) + k.group(2).rstrip() + EK
                    + k.group(3)
                    if EK.strip() not in k.group(2) else k.group(0),
                    yeni)
            bas += 1

        # --- 2) gorunur yerel satir -------------------------------------
        if 'class="yerel-not"' in yeni:
            pass
        else:
            # Cagri bolumunun ONUNE koy: metnin sonu, dogal yer.
            i = yeni.find('<div class="cagri"')
            if i < 0:
                sorun.append("%s: cagri bolumu bulunamadi" % ad)
            else:
                yeni = yeni[:i] + SATIR + "\n" + yeni[i:]
                govde += 1

        if yeni != t and not kontrol:
            io.open(yol, "w", encoding="utf-8").write(yeni)

    print("")
    print("baslik: %d · govde satiri: %d · SORUNLU: %d"
          % (bas, govde, len(sorun)))
    for s in sorun:
        print("  🔴 %s" % s)
    if kontrol:
        print("(--kontrol: dosya YAZILMADI)")
    return 1 if sorun else 0


if __name__ == "__main__":
    sys.exit(main())
