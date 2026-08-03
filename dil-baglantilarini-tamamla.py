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

# ⚠️ BAYRAK EMOJISI KULLANILMIYOR — 3 Agu 2026.
# Once `&#127481;&#127479;` (bayrak emojisi) kullaniliyordu. Windows
# bolgesel-gosterge ciftlerini bayrak olarak CIZMIYOR; kullaniciya
# kucuk harflerle "TR", "GB" diye gorunuyordu. Hekim ekran goruntusuyle
# bildirdi. Emoji yerine ACIK bir kod rozeti: her isletim sisteminde,
# her yazi tipinde ayni gorunur.
BAYRAK = {"tr": '<span class="dil-kod">TR</span>',
          "en": '<span class="dil-kod">EN</span>',
          "es": '<span class="dil-kod">ES</span>',
          "fr": '<span class="dil-kod">FR</span>',
          "de": '<span class="dil-kod">DE</span>',
          "ru": '<span class="dil-kod">RU</span>'}
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


def yayimda_diller():
    """siteyi-yukle.py'nin YAYIMDA_DILLER kumesi — tek kaynak.

    ⚠️ Neden onemli: YAYIMLANAN bir sayfa, YAYIMLANMAYAN bir dile
    `hreflang` ya da dil secici baglantisi verirse canlida 404'e
    isaret eder. Google bunu "hreflang/sitemap hatali" diye okur ve
    siteye guveni duser — tam da sayfalarin dizine girmeye calistigi
    donemde. Kural: **yayimlanan sayfa yalnizca yayimlanan dile
    atifta bulunur.** (Yayimlanmayan dil sayfalari birbirine serbestce
    atifta bulunabilir; onlar zaten canlida degil.)
    """
    y = os.path.join(os.path.dirname(KOK), "hasta-mesajlari",
                     "siteyi-yukle.py")
    try:
        k = io.open(y, encoding="utf-8").read()
        m = re.search(r"^YAYIMDA_DILLER = (set\(\)|\{[^}]*\})", k, re.M)
        if not m:
            return None                      # bilinmiyor -> dokunma
        ns = {}
        exec(compile("D = " + m.group(1), "yd", "exec"), ns)
        return set(ns["D"])
    except Exception:
        return None


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


def _izinli(kaynak_kod, hedef_kod, yayimda):
    """Kaynak sayfa hedef dile atifta bulunabilir mi?

    Kural: YAYIMLANAN sayfa yalnizca YAYIMLANAN dile atifta bulunur.
    Yayimlanmayan dilin kendi sayfalari serbesttir (canlida degiller).
    """
    if yayimda is None:
        return True
    kaynak_yayimda = (kaynak_kod == "tr") or (kaynak_kod in yayimda)
    if not kaynak_yayimda:
        return True
    return (hedef_kod == "tr") or (hedef_kod in yayimda)


def hreflang_tamamla(esi, uygula, yayimda=None):
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
            eksik = [k for k in grup if k not in var
                     and _izinli(kod, k, yayimda)]
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


def secici_tamamla(esi, diller, uygula, yayimda=None):
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
            kaynak_on = yol.split("/")[0] if "/" in yol else "tr"
            if 'class="dil-sec"' not in s:
                # ⚠️ Secici, yayimda EN AZ IKI dil varken GERI GELMELI.
                # Tek dil kalinca kaldiriliyor (bkz. temizle); dil
                # onaylanip yayima girdiginde blogu yeniden kurmak
                # gerekiyor, yoksa dil eklendigi halde ziyaretci
                # gecis yapamaz — sessiz bir eksik.
                _izin = [d for d in diller if _izinli(kaynak_on, d, yayimda)]
                if len(_izin) < 2:
                    continue
                # ⚠️ `[^<]*` KULLANMA: Turkce sayfalarda telefon
                # baglantisinin ICINDE bir <svg> ikon var, o desen
                # eslesmiyordu ve secici sessizce kurulmuyordu.
                # Sinanarak yakalandi (Ingilizce onayi simulasyonu).
                _yer = re.search(
                    r'([ \t]*)<a class="serit-tel".*?</a>\n', s, re.S)
                if not _yer:
                    islem.append(("SECICI KURULAMADI", yol, "yer yok"))
                    continue
                _g = _yer.group(1)
                _blok = (
                    '%s<details class="dil-sec">\n'
                    '%s  <summary aria-label="Dil sec / Choose language">'
                    '<span class="dil-ad">%s</span>'
                    '<span class="ok">&#9660;</span></summary>\n'
                    '%s  <div class="dil-liste">\n'
                    '%s  </div>\n'
                    '%s</details>\n'
                    % (_g, _g, AD.get(kaynak_on, kaynak_on), _g, _g, _g))
                s = s.replace(_yer.group(0), _yer.group(0) + _blok, 1)
                io.open(os.path.join(KOK, yol), "w", encoding="utf-8",
                        newline="").write(s) if uygula else None
                islem.append(("secici kuruldu", yol,
                              "%d dil yayimda" % len(_izin)))
                if not uygula:
                    continue
            grup = esli.get(yol)
            kaynak_kod = yol.split("/")[0] if "/" in yol else "tr"
            for d in diller:
                if "%s %s</a>" % (BAYRAK[d], AD[d]) in s:
                    continue
                if not _izinli(kaynak_kod, d, yayimda):
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
                    # ⚠️ YENI KURULMUS BOS SECICI. Eklenecek yeri
                    # "mevcut dil satiri" diye aramak burada
                    # calismiyordu ve blok BOS kaliyordu — dil
                    # onaylansa bile ziyaretci gecis yapamazdi.
                    # Bos blokta `<div class="dil-liste">` satirinin
                    # hemen altina eklenir.
                    _bos = re.search(r'([ \t]*)<div class="dil-liste">\n', s)
                    if not _bos:
                        islem.append(("SECICI BULUNAMADI", yol, d))
                        continue
                    son = _bos.group(0)
                    girinti = _bos.group(1) + "  "
                else:
                    son = satirlar[-1]
                    girinti = son[:len(son) - len(son.lstrip())]
                islem.append(("secici", yol, "%s -> %s" % (d, hedef)))
                if uygula:
                    s = s.replace(son, son + '%s<a href="%s">%s %s</a>\n'
                                  % (girinti, hedef, BAYRAK[d], AD[d]), 1)
                    io.open(os.path.join(KOK, yol), "w", encoding="utf-8",
                            newline="").write(s)
    return islem


def sitemap_tamamla(esi, uygula, yayimda=None):
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
            if not _izinli("tr", kod, yayimda):
                continue          # yayimlanmayan dil sitemap'e girmez
            u = url(kod, yol)
            if u in s:
                continue
            islem.append(("sitemap", yol, u))
            ekler.append(kalip.group(1).replace(">%s<" % SITE, ">%s<" % u))
    if uygula and ekler:
        io.open(p, "w", encoding="utf-8", newline="").write(
            s.replace(kalip.group(1), kalip.group(1) + "".join(ekler), 1))
    return islem


def temizle(esi, yayimda, uygula):
    """YAYIMLANAN sayfalardan, yayimlanmayan dile atiflari kaldirir.

    Kapsam: hreflang satirlari, dil secici baglantilari, sitemap
    girdileri. Yayimlanmayan dilin KENDI sayfalarina dokunulmaz.
    """
    islem = []
    kaldirilacak = {d for g in esi for d in g if d != "tr"} - yayimda
    if not kaldirilacak:
        return islem

    for kok, klasorler, dosyalar in os.walk(KOK):
        klasorler[:] = [k for k in klasorler
                        if k not in (".git", "arsiv", "belge-bekliyor")
                        and k not in kaldirilacak]      # yayimlanmayan
        for ad in sorted(dosyalar):                     # dilin kendi
            if not ad.endswith(".html"):                # sayfalari haric
                continue
            yol = os.path.relpath(os.path.join(kok, ad),
                                  KOK).replace(os.sep, "/")
            s = io.open(os.path.join(KOK, yol), encoding="utf-8").read()
            o = s
            for d in kaldirilacak:
                s = re.sub(r'[ \t]*<link rel="alternate" hreflang="%s"'
                           r'[^>]*>\n?' % d, "", s)
                s = re.sub(r'[ \t]*<a href="[^"]*"[^>]*>%s %s</a>\n?'
                           % (BAYRAK[d], re.escape(AD[d])), "", s)
            # ⚠️ TEK SECENEKLI DIL MENUSU OLMAZ. Temizlikten sonra
            # secicide tek dil kaliyorsa blogun tamami kaldirilir:
            # "Türkçe" yazan, tiklaninca yalniz Türkçe gosteren bir
            # acilir menu, hic olmamasindan kotudur. (Ilk yazimda bu
            # atlandi ve TR sayfalari tek secenekli menuyle kaldi.)
            _kalan = len(re.findall(r'<a href="[^"]*"[^>]*>&#\d+;&#\d+; ',
                                    s))
            if _kalan <= 1:
                s2 = re.sub(r'[ \t]*<details class="dil-sec">.*?</details>\n?',
                            "", s, flags=re.S)
                if s2 != s:
                    s = s2
                    islem.append(("secici kaldirildi", yol,
                                  "tek dil kaldi — menu gizlendi"))
            if s != o:
                islem.append(("temizlik", yol,
                              "yayimlanmayan: " + ", ".join(
                                  sorted(kaldirilacak))))
                if uygula:
                    io.open(os.path.join(KOK, yol), "w", encoding="utf-8",
                            newline="").write(s)

    p = os.path.join(KOK, "sitemap.xml")
    s = io.open(p, encoding="utf-8").read()
    o = s
    for d in kaldirilacak:
        s = re.sub(r"\s*<url>\s*<loc>%s%s/[^<]*</loc>.*?</url>"
                   % (re.escape(SITE), d), "", s, flags=re.S)
    if s != o:
        islem.append(("temizlik", "sitemap.xml",
                      "%d -> %d URL" % (o.count("<url>"), s.count("<url>"))))
        if uygula:
            io.open(p, "w", encoding="utf-8", newline="").write(s)
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
    yayimda = yayimda_diller()
    if yayimda is None:
        print("  ⚠️ YAYIMDA_DILLER okunamadi — temizlik atlandi.")
        hepsi = []
    else:
        print("  yayimda olan diller: %s"
              % (", ".join(sorted(yayimda)) if yayimda else "(hicbiri)"))
        print("")
        hepsi = temizle(esi, yayimda, uygula)

    hepsi += (hreflang_tamamla(esi, uygula, yayimda)
              + secici_tamamla(esi, diller, uygula, yayimda)
              + sitemap_tamamla(esi, uygula, yayimda))
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
