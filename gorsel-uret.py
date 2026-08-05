#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GORSEL VARYANTLARI URETIR — AVIF + WebP, iki genislikte.

    python gorsel-uret.py

Neden: SEO denetimi (b7) — butun gorseller tek JPG olarak sunuluyordu.
Telefondan giren hasta da masaustu boyutundaki dosyayi indiriyordu.
`konum-harita.jpg` tek basina 257 KB.

Uretilen dosyalar `gorsel/` klasorune yaziliyor; kaynak JPG'ler yerinde
kaliyor ve <img src> icinde YEDEK olarak duruyor (AVIF/WebP desteklemeyen
eski tarayici yine gorsel gorur).

Yeniden calistirmak guvenli: cikti kaynaktan yeniyse atlanir.
"""
import io
import os
import sys

from PIL import Image

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

KOK = os.path.dirname(os.path.abspath(__file__))
HEDEF = os.path.join(KOK, "gorsel")

# (dosya, genislikler) — genislik sayfadaki GERCEK kullanima gore secildi
GORSELLER = [
    ("gorsel-hero.jpg",        (900, 1600)),   # giris, tam genislik
    ("konum-harita.jpg",       (550, 700, 1100)),  # mobil retina ara adayi
    ("gorsel-fon-klinik.jpg",  (600, 1200)),
    ("gorsel-fon-bakim.jpg",   (600, 1200)),
    ("gorsel-fon-rontgen.jpg", (600, 1200)),
    ("gorsel-lamine.jpg",      (600, 1200)),
    ("gorsel-implant.jpg",     (600, 1200)),
    ("gorsel-cocuk.jpg",       (600, 1200)),
    # ⚠️ 5. tur bulgu 7: 1. ve 7. kart masaustunde IKI SUTUN kapliyor
    # (.dizin-satir:nth-child(1|7){grid-column:span 2}) — yuva 662px,
    # digerleri 324px. Ikisi de 400/800 uretiyordu ve `sizes` 33vw
    # dedigi icin tarayici GENIS karta 400px'lik gorseli seciyordu.
    # Kaynak dosyalar 900px; buyutme yapilmadigi icin ulasilabilecek en
    # buyuk varyant 900. Retina masaustunde (662x2=1324) yine de
    # kaynak sinirina takiliyoruz — daha iyisi icin gercek klinik
    # fotograflari gerekiyor.
    ("gorsel-k-genel.jpg",     (400, 800, 900)),   # genis kart (1.)
    ("gorsel-k-kanal.jpg",     (400, 800)),        # tedavi karti
    ("gorsel-k-cerrahi.jpg",   (400, 800)),
    ("gorsel-k-protez.jpg",    (400, 800)),
    ("gorsel-k-diseti.jpg",    (400, 800)),
    ("gorsel-k-orto.jpg",      (400, 800)),
    ("gorsel-k-cocuk.jpg",     (400, 800, 900)),   # genis kart (7.)
]

KALITE = {"avif": 55, "webp": 78}


def guncel_mi(kaynak, cikti):
    return (os.path.exists(cikti)
            and os.path.getmtime(cikti) >= os.path.getmtime(kaynak))


def main():
    os.makedirs(HEDEF, exist_ok=True)
    toplam_once = toplam_sonra = 0
    uretildi = atlandi = 0

    for ad, genislikler in GORSELLER:
        kaynak = os.path.join(KOK, ad)
        if not os.path.exists(kaynak):
            print("  YOK: %s" % ad)
            continue
        kok_ad = os.path.splitext(ad)[0]
        toplam_once += os.path.getsize(kaynak)

        with Image.open(kaynak) as im:
            im = im.convert("RGB")
            asil_g = im.width
            for g in genislikler:
                # Kaynaktan buyutme YAPMA — bulanik gorsel uretmenin anlami yok
                hedef_g = min(g, asil_g)
                oran = hedef_g / float(im.width)
                boyut = (hedef_g, max(1, int(round(im.height * oran))))
                kucuk = im.resize(boyut, Image.LANCZOS)
                for bicim in ("avif", "webp"):
                    cikti = os.path.join(HEDEF, "%s-%d.%s"
                                         % (kok_ad, g, bicim))
                    if guncel_mi(kaynak, cikti):
                        atlandi += 1
                        toplam_sonra += os.path.getsize(cikti)
                        continue
                    kucuk.save(cikti, quality=KALITE[bicim])
                    toplam_sonra += os.path.getsize(cikti)
                    uretildi += 1
        print("  %-26s %4d px kaynak -> %s" % (ad, asil_g,
                                               ", ".join(str(x) for x in genislikler)))

    print("")
    print("uretildi : %d dosya (atlanan %d)" % (uretildi, atlandi))
    print("kaynak   : %.0f KB" % (toplam_once / 1024.0))
    print("varyant  : %.0f KB (hepsi birlikte; tarayici BIRINI indirir)"
          % (toplam_sonra / 1024.0))


if __name__ == "__main__":
    main()
