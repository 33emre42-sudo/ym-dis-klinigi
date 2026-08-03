#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Yeni bir dil eklendikten sonra BAGLANTILARI tamamlar (3 Agu 2026).

    python dil-baglantilarini-tamamla.py            # ne yapacagini yazar
    python dil-baglantilarini-tamamla.py --uygula   # uygular

Uc isi yapar, hepsi `denetle.py` icindeki SAYFA_ESI + DILLER
tablolarindan turetilir (tek kaynak):

  1. hreflang — her sayfa, esi olan HER dile baglanti vermeli.
     Tek yonlu hreflang'i Google YOK SAYIYOR; eksik kalirsa cok dilli
     kurulum sessizce yarim kalir.
  2. Dil secici — esi olan sayfaya gitmeli, karsi dilin ANA SAYFASINA
     degil. Esi olmayan sayfalarda (bilgi yazilari) ana sayfaya gider.
  3. sitemap.xml — yeni sayfalar eklenir.

NEDEN VAR: bu is Ispanyolca, Fransizca ve Almanca icin UC KEZ elle
yapildi ve her seferinde bir sey atlandi:
  · ES turunda en/ sayfalarina `hreflang="es"` konmasi unutuldu
    (ad esleme calismiyordu, ceviri dosya adlari farkli)
  · FR turunda ana sayfa baglantilari `../index.html` yapildi —
    ayni sayfa ama FARKLI URL, canonical ile ayrisiyor
  · DE turunda ayni adimlar bastan yazildi
Elle tekrarlanan is, dorduncusunde mutlaka yanlis yapilir.

⛔ Metin CEVIRMEZ, sayfa URETMEZ. Yalnizca baglanti tamamlar.
"""
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
KOK = os.path.dirname(os.path.abspath(__file__))
SITE = "https://ymdisklinigi.com/"

BAYRAK = {"tr": "&#127481;&#127479;", "en": "&#127468;&#127463;",
          "es": "&#127466;&#127480;", "fr": "&#127467;&#127479;",
          "de": "&#127465;&#127466;", "ru": "&#127479;&#127482;"}
AD = {"tr": "T&uuml;rk&ccedil;e", "en": "English", "es": "Espa&ntilde;ol",
      "fr": "Fran&ccedil;ais", "de": "Deutsch", "ru": "&#1056;&#1091;&#1089;&#1089;&#1082;&#1080;&#1081;"}


def tablolari_oku():
    """denetle.py'den SAYFA_ESI ve DILLER — kopyalamadan."""
    k = io.open(os.path.join(KOK, "denetle.py"), encoding="utf-8").read()
    ns = {}
    b = k.index("SAYFA_ESI = [")
    exec(compile(k[b:k.index("\n]", b) + 2], "esleme", "exec"), ns)
    diller = re.findall(r'^\s{4}"(\w\w)": \{"ad":', k, re.M)
    return ns["SAYFA_ESI"], ["tr"] + diller


def url(kod, yol):
    """Yayin adresi. Her dilin ANA SAYFASI temiz adresle yayimlanir."""
    if yol == "index.html":
        return SITE
    if yol == "%s/index.html" % kod:
        return SITE + kod + "/"
    return SITE + yol


def bagil(kaynak, hedef):
    """Kaynak sayfadan hedefe goreceli adres.

    ⚠️ Ana sayfalar TEMIZ ADRESLE ("/", "en/", "../es/") baglanir.
    `../index.html` ayni sayfaya gider ama FARKLI bir URL'dir ve
    canonical ile ayrisir — Google ikisini ayri sayfa sanabilir.
    """
    kk = kaynak.split("/")[0] if "/" in kaynak else ""
    if hedef == "index.html":
        return "/"
    hk = hedef.split("/")[0]
    if hedef == "%s/index.html" % hk:
        return ("%s/" % hk) if not kk else ("../%s/" % hk)
    if kk == hk:
        return hedef.split("/", 1)[1]
    return hedef if not kk else "../" + hedef


def hreflang_tamamla(esi, uygula):
    islem = []
    for grup in esi:
        for kod, yol in grup.items():
            p = os.path.join(KOK, yol)
            if not os.path.exists(p):
                islem.append(("EKSIK DOSYA", yol, ""))
                continue
            s = io.open(p, encoding="utf-8").read()
            var = dict(re.findall(
                r'<link rel="alternate" hreflang="([^"]+)" href="([^"]+)">',
                s))
            eksik = [k for k in grup if k not in var]
            if not eksik:
                continue
            islem.append(("hreflang", yol, ", ".join(eksik)))
            if not uygula:
                continue
            ilk = [l for l in s.splitlines(True)
                   if '<link rel="alternate"' in l][0]
            ek = "".join('<link rel="alternate" hreflang="%s" href="%s">\n'
                         % (k, url(k, grup[k])) for k in eksik)
            io.open(p, "w", encoding="utf-8",
                    newline="").write(s.replace(ilk, ek + ilk, 1))
    return islem


def secici_tamamla(esi, diller, uygula):
    esli = {y: g for g in esi for y in g.values()}
    islem = []
    for kok, _, dosyalar in os.walk(KOK):
        if any(a in kok for a in (".git", "arsiv", "belge-bekliyor")):
            continue
        for ad in sorted(dosyalar):
            if not ad.endswith(".html"):
                continue
            yol = os.path.relpath(os.path.join(kok, ad),
                                  KOK).replace(os.sep, "/")
            s = io.open(os.path.join(KOK, yol), encoding="utf-8").read()
            if 'class="dil-sec"' not in s:
                continue
            grup = esli.get(yol)
            for d in diller:
                if "%s %s</a>" % (BAYRAK[d], AD[d]) in s:
                    continue
                hedef = (bagil(yol, grup[d]) if grup and d in grup
                         else bagil(yol, "%s/index.html" % d)
                         if d != "tr" else "/")
                # son dil satirinin ALTINA ekle
                satirlar = [l for l in s.splitlines(True)
                            if "</a>" in l and any(
                                "%s %s</a>" % (BAYRAK[x], AD[x]) in l
                                for x in diller)]
                if not satirlar:
                    islem.append(("SECICI BULUNAMADI", yol, d))
                    continue
                son = satirlar[-1]
                girinti = son[:len(son) - len(son.lstrip())]
                islem.append(("secici", yol, "%s -> %s" % (d, hedef)))
                if uygula:
                    s = s.replace(son, son + '%s<a href="%s">%s %s</a>\n'
                                  % (girinti, hedef, BAYRAK[d], AD[d]), 1)
                    io.open(os.path.join(KOK, yol), "w", encoding="utf-8",
                            newline="").write(s)
    return islem


def sitemap_tamamla(esi, uygula):
    p = os.path.join(KOK, "sitemap.xml")
    s = io.open(p, encoding="utf-8").read()
    kalip = re.search(r"(\s*<url>\s*<loc>%s</loc>.*?</url>)"
                      % re.escape(SITE), s, re.S)
    if not kalip:
        return [("SITEMAP KALIBI YOK", "", "")]
    islem = []
    ekler = []
    for grup in esi:
        for kod, yol in grup.items():
            u = url(kod, yol)
            if u in s:
                continue
            islem.append(("sitemap", yol, u))
            ekler.append(kalip.group(1).replace(">%s<" % SITE, ">%s<" % u))
    if uygula and ekler:
        io.open(p, "w", encoding="utf-8", newline="").write(
            s.replace(kalip.group(1), kalip.group(1) + "".join(ekler), 1))
    return islem


def main():
    uygula = "--uygula" in sys.argv
    esi, diller = tablolari_oku()
    print("")
    print("DIL BAGLANTILARI — %s" % ("UYGULANIYOR" if uygula
                                     else "yalnizca rapor"))
    print("=" * 66)
    print("diller: %s · %d sayfa grubu" % (", ".join(diller), len(esi)))
    print("")
    hepsi = (hreflang_tamamla(esi, uygula)
             + secici_tamamla(esi, diller, uygula)
             + sitemap_tamamla(esi, uygula))
    if not hepsi:
        print("  Yapacak bir sey yok — baglantilar tam.")
        return 0
    for tur, yol, not_ in hepsi:
        print("  %-18s %-46s %s" % (tur, yol[:46], not_))
    print("")
    print("  %d islem%s" % (len(hepsi),
                            "" if uygula else " — uygulamak icin --uygula"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
