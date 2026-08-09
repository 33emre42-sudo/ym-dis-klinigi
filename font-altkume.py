#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Yazi tipi dosyalarindan KULLANILMAYAN harfleri atar.

    python font-altkume.py            # olcer, DOSYAYA DOKUNMAZ
    python font-altkume.py --uygula   # altkumeler + fontlar.css'i gunceller

NEDEN VAR
---------
`fontlar/` altindaki woff2 dosyalari Google Fonts'un hazir "latin" ve
"latin-ext" altkumeleri. Ikisi birlikte bircok dilin harfini tasiyor;
biz onlarin kucuk bir bolumunu kullaniyoruz. Kullanilmayan harf, her
ziyaretcinin bosuna indirdigi bayttir.

⛔ EN ONEMLI KURAL — `unicode-range` DE GUNCELLENIR
---------------------------------------------------
`fontlar.css` her `@font-face` icin bir `unicode-range` bildiriyor.
Tarayici bir karakteri o aralikta gorurse dosyayi indirir ve **o
harfin dosyada bulundugunu varsayar**. Dosyayi kesip bildirimi
oldugu gibi birakmak, en sinsi hatayi uretir: tarayici dosyayi
indirir, harf yoktur, ekranda bosluk ya da sistem yedegi cikar —
hicbir hata mesaji olmadan.

Bu yuzden betik altkumeyi urettikten SONRA `unicode-range`i o
dosyanin GERCEK cmap'inden yeniden yaziyor. Bildirim ile dosya her
zaman birbirini tutuyor.

⚠️ Hangi harfler korunur: 78 sayfanin (yayimlanmayan dil klasorleri
DAHIL) gorunur metninde gecen her karakter + asagidaki GUVENLIK
KUMESI. Dil klasorleri bilerek dahil: yarin yayimlanirlarsa harf
eksigi cikmasin.

⚠️ Yeni bir yazi yeni bir harf getirirse `harf-kapsam.py` bunu
denetimde yakalar (o kapi `denetle.py`ye bagli). Yani yanlis daraltma
yayina giremez — bu betigin guvenle kosulabilmesinin sebebi odur.
"""
import glob
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

KOK = os.path.dirname(os.path.abspath(__file__))
FONT_DIZIN = os.path.join(KOK, "fontlar")
CSS = os.path.join(KOK, "fontlar.css")

# Sayfalarda bugun gecmese de KORUNACAK karakterler. Gerekcesi: bunlar
# metin yazarken refleksle kullanilan isaretler; biri eksik kalirsa
# sistem yedegine dusup cevresindeki yazidan farkli gorunur.
GUVENLIK = set(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz"
    "0123456789"
    " !\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"
    "ÇĞİÖŞÜçğıöşü"                      # Turkce
    "ÀÁÂÄÈÉÊËÌÍÎÏÑÒÓÔÖÙÚÛÜÝ"            # yayimlanmayan dil sayfalari
    "àáâäèéêëìíîïñòóôöùúûüýÿ"
    "ÆæŒœßÅåØøÑ"
    "‘’“”„–—…·•→←↑↓×÷°′″"                 # tirnak, tire, oklar
    "€₺$£¢%‰©®™†‡§¶"
)


def gorunur_metin(html):
    """`harf-kapsam.py` ile AYNI ayiklama — ikisi ayrisirsa altkume
    denetimin olctugunden farkli bir kumeye gore uretilir."""
    h = re.sub(r"<(script|style)\b.*?</\1>", " ", html, flags=re.S | re.I)
    h = re.sub(r"<!--.*?-->", " ", h, flags=re.S)
    return re.sub(r"<[^>]+>", " ", h)


def kullanilan_karakterler():
    kume = set(GUVENLIK)
    sayfalar = sorted(glob.glob(os.path.join(KOK, "*.html")) +
                      glob.glob(os.path.join(KOK, "*", "*.html")))
    for p in sayfalar:
        with io.open(p, encoding="utf-8", errors="replace") as f:
            kume.update(gorunur_metin(f.read()))
    # Kontrol karakterleri ve emoji bizim altkumemizde olmaz.
    return {c for c in kume if ord(c) >= 0x20 and ord(c) < 0x2500}, len(sayfalar)


def araliklar_metni(kodlar):
    """Kod noktalarindan CSS `unicode-range` dizesi uretir."""
    kodlar = sorted(kodlar)
    parcalar, i = [], 0
    while i < len(kodlar):
        j = i
        while j + 1 < len(kodlar) and kodlar[j + 1] == kodlar[j] + 1:
            j += 1
        parcalar.append("U+%X" % kodlar[i] if i == j
                        else "U+%X-%X" % (kodlar[i], kodlar[j]))
        i = j + 1
    return ", ".join(parcalar)


def main():
    uygula = "--uygula" in sys.argv
    try:
        from fontTools import subset as ft_subset
        from fontTools.ttLib import TTFont
    except ImportError:
        print("⛔ fontTools kurulu degil.")
        print("   python -m pip install \"fonttools[woff]\"")
        return 2

    istenen, n_sayfa = kullanilan_karakterler()
    print("=" * 70)
    print("FONT ALTKUMESI  —  %s" % ("UYGULANIYOR" if uygula else "KURU OLCUM"))
    print("=" * 70)
    print("  %d sayfa tarandi · korunacak karakter: %d"
          % (n_sayfa, len(istenen)))
    print("")

    dosyalar = sorted(glob.glob(os.path.join(FONT_DIZIN, "*.woff2")))
    if not dosyalar:
        print("⛔ fontlar/ altinda woff2 yok.")
        return 2

    css = io.open(CSS, encoding="utf-8").read() if os.path.exists(CSS) else ""
    toplam_once = toplam_sonra = 0
    yeni_araliklar = {}

    for yol in dosyalar:
        ad = os.path.basename(yol)
        once = os.path.getsize(yol)
        toplam_once += once

        font = TTFont(yol)
        mevcut = set()
        for tablo in font["cmap"].tables:
            mevcut.update(tablo.cmap.keys())
        font.close()

        tutulacak = sorted(mevcut & {ord(c) for c in istenen})
        if not tutulacak:
            print("  !! %-42s bos altkume — ATLANDI" % ad)
            toplam_sonra += once
            continue

        hedef = yol + ".yeni" if uygula else os.path.join(
            os.environ.get("TEMP", "."), "kuru-" + ad)
        secenek = ft_subset.Options()
        secenek.flavor = "woff2"
        secenek.desubroutinize = True
        secenek.layout_features = ["*"]      # kerning/ligature korunur
        secenek.notdef_outline = True
        f2 = ft_subset.load_font(yol, secenek)
        # ⛔ `populate` SART. Ilk yazimda unutulmustu ve `subset()`
        # HICBIR harfi tutmadi: cikan dosyalar 1 KB, cmap BOS, yalniz
        # `.notdef` glifi. Ekranda "%94 kazanc" yaziyordu — cunku
        # kazanc, butun harfleri silmekti. Uygulansa her sayfa sistem
        # yazi tipine duserdi. Asagidaki KENDI KENDINI SINAMA bu
        # sinifi bir daha sessiz birakmiyor.
        altkumeci = ft_subset.Subsetter(options=secenek)
        altkumeci.populate(unicodes=tutulacak)
        altkumeci.subset(f2)
        ft_subset.save_font(f2, hedef, secenek)
        f2.close()

        # KENDI KENDINI SINAMA: uretilen dosya gercekten istenen
        # harfleri tasiyor mu? "Kucuk dosya" basarinin degil, bos
        # altkumenin de isaretidir.
        kontrol = TTFont(hedef)
        uretilen = set()
        for tablo in kontrol["cmap"].tables:
            uretilen.update(tablo.cmap.keys())
        kontrol.close()
        eksik = set(tutulacak) - uretilen
        if eksik:
            print("  🔴 %s — altkume EKSIK cikti: %d harf yok (or. %s)"
                  % (ad, len(eksik),
                     " ".join(chr(k) for k in sorted(eksik)[:8])))
            print("     Dosya YAZILMADI. Bos/eksik altkume, butun")
            print("     sayfalari sistem yazi tipine dusurur.")
            try:
                os.remove(hedef)
            except OSError:
                pass
            return 1

        sonra = os.path.getsize(hedef)
        toplam_sonra += sonra
        yeni_araliklar[ad] = araliklar_metni(tutulacak)
        print("  %-44s %6.1f KB -> %6.1f KB  (%d harf, -%.0f%%)"
              % (ad, once / 1024.0, sonra / 1024.0, len(tutulacak),
                 100.0 * (once - sonra) / once if once else 0))

        if uygula:
            os.replace(hedef, yol)
        else:
            try:
                os.remove(hedef)
            except OSError:
                pass

    print("")
    print("  TOPLAM  %.1f KB -> %.1f KB   (kazanc %.1f KB, %%%.0f)"
          % (toplam_once / 1024.0, toplam_sonra / 1024.0,
             (toplam_once - toplam_sonra) / 1024.0,
             100.0 * (toplam_once - toplam_sonra) / toplam_once
             if toplam_once else 0))

    if not uygula:
        print("\n  (kuru olcum — hicbir dosya degismedi. --uygula ile yaz.)")
        return 0

    # ---- unicode-range'leri GERCEK cmap'ten yeniden yaz ------------
    # Bildirim ile dosya ayrisirsa tarayici olmayan harfi bizde sanar.
    degisen = 0
    for ad, aralik in yeni_araliklar.items():
        desen = re.compile(
            r"(src:\s*url\(['\"]?fontlar/" + re.escape(ad)
            + r"['\"]?\)[^;]*;\s*unicode-range:\s*)([^;]+)(;)")
        css, n = desen.subn(lambda m: m.group(1) + aralik + m.group(3), css)
        degisen += n
    io.open(CSS, "w", encoding="utf-8", newline="\n").write(css)
    print("\n  fontlar.css: %d unicode-range yeniden yazildi (%d dosya)"
          % (degisen, len(yeni_araliklar)))
    if degisen != len(yeni_araliklar):
        print("  🔴 SAYILAR TUTMUYOR — CSS'te eslesmeyen kayit var.")
        print("     Bildirim ile dosya ayrisirsa tarayici OLMAYAN harfi")
        print("     bizde sanar ve harf sessizce kaybolur.")
        print("     `git checkout fontlar fontlar.css` ile geri al.")
        return 1
    print("\n  ⚠️ Simdi ZORUNLU: python harf-kapsam.py  ve  python denetle.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
