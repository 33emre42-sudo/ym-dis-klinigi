# -*- coding: utf-8 -*-
"""CSS ve yazi tipi baglantilarina ICERIK DAMGASI basar.

    python surum-damgala.py            # ne degisecegini yazar
    python surum-damgala.py --uygula   # yazar

NEDEN VAR — 11 Agustos 2026, OLCUMLE bulundu:

Sunucu duragan dosyalari 30 GUN onbellege veriyor
(`Cache-Control: max-age=2592000`) ve dosya adlarinda surum isareti
YOKTU (`href="bilgi.css"`). Tarayicida olculdu:

    fontlar.css   transferSize 0  -> ONBELLEK, aga HIC gidilmedi
    archivo-*.woff2               -> ayni
    logo-isaret-*.avif            -> ayni

Yani bir CSS duzeltmesi yayinlandiginda SITEYE DAHA ONCE GIRMIS bir
ziyaretci onu 30 gune kadar GORMUYOR. O gece dokunma hedefleri
duzeltilmisti; icerik sayfalarinda geri donen hastanin dugmeleri
44px'e cikmayacakti ve bunu kimse fark etmeyecekti.

⚠️ HTML'in kendisi `no-cache` — yani METIN duzeltmeleri (tibbi icerik
dahil) hemen ulasiyor. Sorun yalnizca CSS/font/gorsel katmaninda.

Cozum: dosya ICERIGINDEN turetilen bir damga (`?v=<sha8>`). Icerik
degisince damga degisir, tarayici yeni URL'yi bilmedigi icin agdan
alir. Icerik degismezse damga da degismez, onbellek calismaya devam
eder — yani hiz kaybi yok.

⛔ SIRA ONEMLI: once `fontlar.css` icindeki font URL'leri damgalanir
(bu, fontlar.css'in icerigini DEGISTIRIR), sonra HTML'deki CSS
baglantilari damgalanir. Ters sirada fontlar.css'in damgasi bir tur
bayat kalir.

Kapisi `denetle.py` icinde: damga dosyanin GERCEK ozetiyle
eslesmiyorsa yayin durur.
"""
import glob
import hashlib
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
KOK = os.path.dirname(os.path.abspath(__file__))
UYGULA = "--uygula" in sys.argv

DAMGALI_CSS = ("bilgi.css", "fontlar.css")


def ozet(yol):
    """Dosya iceriginin ilk 8 hanesi. Yoksa None — 'temiz' degil."""
    if not os.path.exists(yol):
        return None
    with io.open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:8]


def yaz(yol, metin):
    if UYGULA:
        io.open(yol, "w", encoding="utf-8", newline="").write(metin)


degisen = []

# ---------------------------------------------------------------- 1
# fontlar.css icindeki font URL'leri. Once bu, cunku dosyayi degistirir.
fyol = os.path.join(KOK, "fontlar.css")
if os.path.exists(fyol):
    fmetin = io.open(fyol, encoding="utf-8").read()
    yeni = fmetin

    def _font(m):
        ad = m.group(1)
        o = ozet(os.path.join(KOK, ad))
        if o is None:
            return m.group(0)          # dosya yok: dokunma, kapi yakalar
        return "url(%s?v=%s)" % (ad, o)

    yeni = re.sub(r"url\((fontlar/[^)?]+\.woff2)(?:\?v=[0-9a-f]+)?\)",
                  _font, yeni)
    if yeni != fmetin:
        degisen.append(("fontlar.css", "font URL damgalari"))
        yaz(fyol, yeni)
        fmetin = yeni

# ---------------------------------------------------------------- 2
# HTML'deki CSS baglantilari. fontlar.css YENI haliyle ozetlenir.
# ⚠️ `fontlar.css`in ozeti DISKTEN degil, BELLEKTEKI YENI halinden
# alinir. Kuru calismada dosya henuz yazilmamis olur; diskten okusaydik
# onizleme gercekten FARKLI bir damga gosterirdi — yani "ne olacagini
# yazan" mod yalan soylerdi.
damga = {}
for ad in DAMGALI_CSS:
    if ad == "fontlar.css" and os.path.exists(fyol):
        o = hashlib.sha256(fmetin.encode("utf-8")).hexdigest()[:8]
    else:
        o = ozet(os.path.join(KOK, ad))
    if o is None:
        print("  ⚠️  %s yok — damgalanmadi" % ad)
    else:
        damga[ad] = o

def _onyukleme(m):
    """`<link rel=preload>` icindeki font adresi.

    ⚠️ ILK SURUMDE ATLANDI ve ZARAR VERDI. CSS damgali adresi
    istiyordu, onyukleme damgasiz adresi cekiyordu: iki AYRI adres,
    yani ayni font iki kez iniyor ve onyukleme bosa gidiyor.
    Tarayici bunu kendisi soyledi:

        "The resource .../ibm-plex-sans-400-latin.woff2 was preloaded
         using link preload but not used within a few seconds..."

    Onyukleme, ilk boyamayi hizlandirmak icin var; eslesmeyince tam
    tersini yapiyor. Kendi ekledigim damganin actigi delikti.
    """
    ad = m.group(1)
    o = ozet(os.path.join(KOK, ad))
    return m.group(0) if o is None else 'href="%s?v=%s"' % (ad, o)


for sayfa in sorted(glob.glob(os.path.join(KOK, "*.html"))):
    metin = io.open(sayfa, encoding="utf-8").read()
    yeni = metin
    for ad, o in damga.items():
        yeni = re.sub(
            r'href="%s(?:\?v=[0-9a-f]+)?"' % re.escape(ad),
            'href="%s?v=%s"' % (ad, o), yeni)
    yeni = re.sub(r'href="(fontlar/[^"?]+\.woff2)(?:\?v=[0-9a-f]+)?"',
                  _onyukleme, yeni)
    if yeni != metin:
        degisen.append((os.path.basename(sayfa), ", ".join(
            "%s=%s" % (a, o) for a, o in sorted(damga.items()))))
        yaz(sayfa, yeni)

print("=" * 70)
for ad, ne in degisen:
    print("  %-34s %s" % (ad, ne))
print("=" * 70)
if not degisen:
    print("  damgalar zaten guncel — degisiklik yok")
elif UYGULA:
    print("  %d dosya guncellendi" % len(degisen))
else:
    print("  %d dosya DEGISECEK — yazmak icin: --uygula" % len(degisen))
