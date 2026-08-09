#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Logo `<picture>` bloklarina AVIF/WebP kaynaklari ekler.

    python logo-modern-bicim.py            # kuru calisma (varsayilan)
    python logo-modern-bicim.py --uygula   # degisiklikleri yazar

NEDEN VAR — 9 Agustos 2026'da olculdu:

Sitedeki sekiz fotografin hepsinin AVIF/WebP turevi vardi; **iki
logonun yoktu.** Gercek tarayici olcumu (mobil, canli site): inen
`logo-isaret.png` sayfanin en buyuk IKINCI yuku, 50,3 KB. Kaynak
480x480, baslikta gosterim 34x34.

    82,4 KB PNG  ->  2,9 KB AVIF (102 px)

Logo 78 sayfanin hepsinde var.

⚠️ `<img>` ETIKETINE DOKUNULMAZ. O, AVIF/WebP desteklemeyen eski
tarayicinin yedegidir; `class`, `alt`, `width`, `height`, `decoding`,
`src` yakalandigi bicimiyle geri yazilir.

⚠️ JSON-LD'DEKI LOGO SATIRI KORUNUR. `index.html` icinde
`"logo":"https://ymdisklinigi.com/logo-isaret.png"` diye bir sema alani
var; `<picture>` icinde OLMADIGI icin bu betik onu hic gormez.

Ikinci kez calistirmak guvenli: yenilenmis blogun govdesi artik tek bir
PNG `<source>`'undan ibaret olmadigi icin `ESKI_KAYNAK.fullmatch`
tutmaz ve blok atlanir.

Kod Codex tarafindan yazildi (K60), eksik-dosya kapisi eklenerek
uygulandi.
"""
import glob
import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

KOK = os.path.dirname(os.path.abspath(__file__))

PICTURE = re.compile(
    r"(?P<acilis><picture(?:\s[^>]*)?>)(?P<govde>.*?)(?P<kapanis></picture>)",
    re.DOTALL,
)
SON_IMG = re.compile(r"(?P<img><img\b[^>]*>)\s*\Z", re.DOTALL)
# ⚠️ ONEK YAKALANIR — 9 Agu. Ilk yazimda desen duz `logo-isaret.png`
# ariyordu; `en/ es/ fr/ de/ ru/` altindaki **35 sayfa** logoyu
# `../logo-isaret.png` diye cagirdigi icin hepsi SESSIZCE atlanmisti.
# 78 sayfanin 43'u yenilenip 35'i eski kalacakti ve cikti "43 blok
# degisecek" dedigi icin eksiklik fark edilmezdi.
ESKI_KAYNAK = re.compile(
    r'\s*<source\s+(?:'
    r'srcset="(?P<o1>(?:\.\./)*)logo-isaret\.png"'
    r'\s+media="\(prefers-color-scheme: dark\)"'
    r'|media="\(prefers-color-scheme: dark\)"'
    r'\s+srcset="(?P<o2>(?:\.\./)*)logo-isaret\.png"'
    r')\s*/?>\s*\Z',
    re.DOTALL,
)
SINIF = re.compile(r'\bclass="([^"]*)"')


def baslik_kaynaklari(o=""):
    """Baslik markasi: 34x34 gosterim, 3x retina karsiligi 102 px."""
    return (
        '<source type="image/avif" media="(prefers-color-scheme: dark)" '
        'srcset="{o}gorsel/logo-isaret-102.avif">'
        '<source type="image/webp" media="(prefers-color-scheme: dark)" '
        'srcset="{o}gorsel/logo-isaret-102.webp">'
        '<source media="(prefers-color-scheme: dark)" '
        'srcset="{o}logo-isaret.png">'
        '<source type="image/avif" '
        'srcset="{o}gorsel/logo-isaret-koyu-102.avif">'
        '<source type="image/webp" '
        'srcset="{o}gorsel/logo-isaret-koyu-102.webp">'
    ).format(o=o)


def filigran_kaynaklari(o=""):
    """Giris filigrani: `min(30vw,320px)`, retina icin 480 (kaynak siniri)."""
    return (
        '<source type="image/avif" media="(prefers-color-scheme: dark)" '
        'srcset="{o}gorsel/logo-isaret-320.avif 320w, '
        '{o}gorsel/logo-isaret-480.avif 480w" sizes="min(30vw,320px)">'
        '<source type="image/webp" media="(prefers-color-scheme: dark)" '
        'srcset="{o}gorsel/logo-isaret-320.webp 320w, '
        '{o}gorsel/logo-isaret-480.webp 480w" sizes="min(30vw,320px)">'
        '<source media="(prefers-color-scheme: dark)" '
        'srcset="{o}logo-isaret.png">'
        '<source type="image/avif" '
        'srcset="{o}gorsel/logo-isaret-koyu-320.avif 320w, '
        '{o}gorsel/logo-isaret-koyu-480.avif 480w" sizes="min(30vw,320px)">'
        '<source type="image/webp" '
        'srcset="{o}gorsel/logo-isaret-koyu-320.webp 320w, '
        '{o}gorsel/logo-isaret-koyu-480.webp 480w" sizes="min(30vw,320px)">'
    ).format(o=o)


def gecen_dosyalar():
    """Eklenecek kaynaklarin isaret ettigi YEREL dosya yollari.

    Onek KOK'e gore normallestirilir: `en/` icindeki
    `../gorsel/x.avif` ile kokteki `gorsel/x.avif` AYNI dosyadir.
    """
    metin = baslik_kaynaklari() + filigran_kaynaklari()
    yollar = set()
    for srcset in re.findall(r'srcset="([^"]+)"', metin):
        for aday in srcset.split(","):
            yollar.add(aday.strip().split(" ")[0])
    return sorted(yollar)


def eksikler():
    """⛔ FAIL-CLOSED KAPI — turevler yoksa yazma YAPILMAZ.

    Tarayici bir `<source>`'u tur/ortam olcutune gore SECTIKTEN sonra o
    dosya 404 donerse, bir SONRAKI kaynaga DUSMEZ; goruntu kirik cikar.
    Yani `gorsel-uret.py` kosulmadan bu betigi uygulamak, modern
    tarayicilarin hepsinde logoyu YOK EDER — ve `denetle.py` bunu
    goremezdi (o yalnizca ucuncu taraf kaynaklara bakiyordu).

    Bu yuzden yol listesi metinden TURETILIYOR, elle yazilmiyor:
    kaynak metni degisirse kapi kendiliginde yeni yolu kontrol eder.
    """
    return [y for y in gecen_dosyalar()
            if not os.path.exists(os.path.join(KOK, y.replace("/", os.sep)))]


# ⚠️ DENETIMIN GORMEDIGI YERI DEGISTIRME — 9 Agu. Ilk kosuda betik
# `belge-bekliyor/en/...` sayfasini da yeniledi. O klasor hem
# `siteyi-yukle.py`nin hem `denetle.py`nin KAPSAMI DISINDA
# (`denetle.py:701 YUKLEYICI_DISI`): sayfa yayina hic girmiyor ve
# hicbir kapi ona bakmiyor. Uustelik o sayfanin logo yolu zaten
# kirikti (iki klasor derinlikte ama tek `../` kullaniyor) — betik
# kirikligi sadikca kopyaladi ve tek kirik kaynak bese cikti.
#
# Denetimin goremedigi bir dosyayi degistirmek, dogrulanamayan
# degisiklik uretmektir. Kapsam ayni tutuluyor.
DISLANAN = (".git", "arsiv", "belge-bekliyor")


def _disarida(yol):
    bagil = os.path.relpath(yol, KOK).replace(os.sep, "/")
    return any(p in DISLANAN for p in bagil.split("/")[:-1])


def modernlestir(metin):
    """Eski logo bloklarini yeniler; (yeni_metin, degisim_sayisi) doner."""
    degisim = 0

    def yenile(eslesme):
        nonlocal degisim
        govde = eslesme.group("govde")
        img_eslesmesi = SON_IMG.search(govde)
        if not img_eslesmesi:
            return eslesme.group(0)

        img = img_eslesmesi.group("img")
        onceki = govde[:img_eslesmesi.start()]
        # Tam esitlik sart: govde SADECE eski PNG kaynagi olmali.
        # Idempotanligi saglayan satir budur.
        eski = ESKI_KAYNAK.fullmatch(onceki)
        if not eski:
            return eslesme.group(0)

        # Sayfanin kendi onegi ("" ya da "../") aynen tasinir.
        onek = eski.group("o1") or eski.group("o2") or ""

        sinif_eslesmesi = SINIF.search(img)
        siniflar = sinif_eslesmesi.group(1).split() if sinif_eslesmesi else []
        if "logo" in siniflar:
            kaynaklar = baslik_kaynaklari(onek)
        elif "filigran-giris" in siniflar:
            kaynaklar = filigran_kaynaklari(onek)
        else:
            return eslesme.group(0)

        degisim += 1
        return (eslesme.group("acilis") + kaynaklar + img
                + eslesme.group("kapanis"))

    return PICTURE.sub(yenile, metin), degisim


def main():
    uygula = "--uygula" in sys.argv

    print("")
    print("LOGO MODERN BICIM")
    print("=" * 66)

    yok = eksikler()
    if yok:
        print("  ⛔ TUREV DOSYALAR EKSIK — %d tane:" % len(yok))
        for y in yok:
            print("       %s" % y)
        print("")
        print("  Once uret:  python gorsel-uret.py")
        print("  Uygulanirsa modern tarayicilarda logo KIRIK cikar;")
        print("  secilen <source> 404 donunce tarayici yedege DUSMEZ.")
        return 1

    yollar = [y for y in sorted(glob.glob(os.path.join(KOK, "**", "*.html"),
                                          recursive=True))
              if not _disarida(y)]
    degisenler = []
    toplam = 0
    for yol in yollar:
        with io.open(yol, "r", encoding="utf-8", newline="") as f:
            eski = f.read()
        yeni, adet = modernlestir(eski)
        if not adet:
            continue
        degisenler.append((yol, adet))
        toplam += adet
        if uygula:
            # newline="" — satir sonlari oldugu gibi korunur.
            with io.open(yol, "w", encoding="utf-8", newline="") as f:
                f.write(yeni)

    if not toplam:
        print("  0 degisiklik — hepsi zaten guncel.")
        return 0

    for yol, adet in degisenler:
        print("  %-54s %d blok" % (os.path.relpath(yol, KOK), adet))
    print("")
    if uygula:
        print("  %d blok yenilendi, %d dosya yazildi."
              % (toplam, len(degisenler)))
    else:
        print("  %d blok degisecek — uygulamak icin --uygula" % toplam)
    return 0


if __name__ == "__main__":
    sys.exit(main())
