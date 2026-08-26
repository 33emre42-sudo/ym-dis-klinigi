#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ust seridin MOBIL iki kusurunu duzeltir (7 Agu 2026, hekim bildirdi).

⚠️ NEDEN BETIK: iki kusur da 77 sayfada ve kurallar IKI YERDE duruyor —
`index.html` kendi gomulu stilini kullaniyor, alt sayfalar `bilgi.css`'i.
Bu ayrim daha once de tuzak oldu (dil secici bilgi.css'e yazilmis, ana
sayfada ciplak liste gorunmustu). Elle duzeltmek ayni tuzagi ureteceginden
tek kaynak burasi.

--------------------------------------------------------------------
1) MARKA METNI SERIDIN DISINA TASIYOR
   375x812 olcumu: serit 0-64px, marka blogu -9px'ten 73px'e. Yani
   ustten 5px, alttan 9px TASIYOR. Sebep: 375px'te logo(34) + marka +
   telefon(156) + dil(33) yan yana sigmiyor, marka metnine yalnizca
   62px kaliyor; "YM Dis Klinigi" iki satira, "BAGCILAR · KIRAZLI" ise
   10,5px fontla UC satira boluniyor (38px).
   Cozum: dar ekranda alt satiri gizle, adi tek satira sabitle, telefon
   dugmesini 44px ikon hedefi yap. Konum bilgisi zaten baslikta, adreste ve
   alt bilgide var — seritte tekrar sart degil.

2) DIL BUTONU YALNIZCA "▼" GOSTERIYOR
   Olculdu: buton metni birebir "▼". Dar ekranda `.dil-ad` gizleniyor
   ve geriye SADECE ok kaliyor; kullanici hangi dilde oldugunu
   goremiyor. Cozum: ad gizlenince yerine dil KODU (TR/EN/…) cikar.
   Kod rozeti (`.dil-kod`) zaten tanimli — bayrak emojisi Windows'ta
   cizilmedigi icin bilerek boyle yapilmisti.

--------------------------------------------------------------------
Kullanim:
    python serit-mobil-duzelt.py            # KURU — hicbir sey yazmaz
    python serit-mobil-duzelt.py --uygula   # yazar

Betik TEKRAR KOSULABILIR: yapilmis degisikligi ikinci kez uygulamaz.
"""
import io
import os
import re
import sys

# ⚠️ Windows konsolu cp1254 — projenin oteki betikleri de bunu acikca
# ayarliyor (bkz. denetle.py). Yoksa Turkce/isaret karakteri basarken
# UnicodeEncodeError ile cokuyor ve RAPOR KAYBOLUYOR.
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

UYGULA = "--uygula" in sys.argv

# Dizin -> dil kodu. Kok dizin Turkce.
DIL_KODU = {"": "TR", "en": "EN", "es": "ES",
            "fr": "FR", "de": "DE", "ru": "RU"}

# Iki AYRI bicim var — bu bir tutarsizlik ve burada kapatiliyor:
#
#   a) kok sayfalar : <summary …><span class="dil-ad">Türkçe</span><span class="ok">…
#   b) dil sayfalari: <summary …><span>🇬🇧</span><span class="dil-ad">English</span>…
#
# ⚠️ (b) BAYRAK EMOJISIYLE KALMIS. Bayraktan vazgecme karari alinmis ve
# `index.html` yorumunda gerekcesi yaziyor: "Windows bolgesel-gosterge
# ciftlerini bayrak olarak cizmiyor, 'TR'/'GB' harfleri gorunuyordu."
# Karar kok sayfalara uygulanmis, 35 dil sayfasi GUNCELLENMEMIS —
# bu projede tekrar eden sinif: bir dil ilerliyor, otekiler geride
# kaliyor ve kimse fark etmiyor. Denetim de gormuyor; emoji taramasi
# yalniz index.html'e bakiyor ve bolgesel-gosterge karakterleri zaten
# taranan araligin (U+1F300–U+1FAFF) DISINDA.
# Ayrica klinik icerikte emoji kurali var (sohbet widget'i haric).
#
# Ikisi de ayni rozetle bitiyor: <span class="dil-kod dil-simdi">XX</span>
_SUMMARY = re.compile(r'(<summary[^>]*>)(\s*<span class="dil-ad">)')
_SUMMARY_BAYRAK = re.compile(
    r'(<summary[^>]*>)\s*<span>[^<]{0,8}</span>(\s*<span class="dil-ad">)')

# --- CSS parcalari ---------------------------------------------------
# Taban: rozet normalde gizli (genis ekranda dil ADI yaziyor zaten).
_CSS_TABAN = '  .dil-sec>summary .dil-simdi{display:none}\n'

# Dar ekran: ad gizlenince rozet ortaya cikar + marka/telefon daraltma.
_CSS_DAR = (
    '    .dil-sec>summary .dil-simdi{display:inline-flex}\n'
    '    /* ⚠️ Marka metni seridin disina tasiyordu (olculdu: 78px icerik,\n'
    '       64px serit). Alt satir gizleniyor, ad tek satira sabitleniyor,\n'
    '       telefon 44px ikon hedefi oluyor ki marka adi da gorunsun. */\n'
    '    .marka-metin>span{display:none}\n'
    '    .marka b{white-space:nowrap;font-size:15px}\n'
    '    .serit-tel{font-size:0;gap:0;padding:8px 12px}\n'
)


def _oku(y):
    return io.open(y, encoding="utf-8").read()


def _yaz(y, s):
    # ⚠️ UTF-8 ACIKCA belirtiliyor. PowerShell'in cp1254 tuzagi bu
    # projede siteyi 20 dakika okunamaz hale getirmisti.
    with io.open(y, "w", encoding="utf-8", newline="") as f:
        f.write(s)


def dil_kodu(yol):
    """Dosyanin bulundugu klasorden dil kodunu cikarir."""
    d = os.path.dirname(yol).replace(os.sep, "/").strip("./")
    return DIL_KODU.get(d.split("/")[0] if d else "")


def html_duzelt(yol):
    """summary icine dil kodu rozeti ekler. (degisti_mi, sebep)"""
    s = _oku(yol)
    if 'class="dil-sec"' not in s:
        return False, "dil secici yok"
    # ⚠️ Kontrol TAM SINIF ADIYLA yapiliyor, cunku ayni dosyada CSS de
    # olabiliyor: `index.html` gomulu stilinde `.dil-simdi` gecer ve
    # genis kontrol ("dil-simdi" in s) ANA SAYFAYI atlatmisti — rozet
    # 76 sayfaya girdi, ana sayfaya girmedi. HTML rozeti yalniz
    # `class="dil-kod dil-simdi"` biciminde yaziliyor; CSS'te bu gecmez.
    if 'class="dil-kod dil-simdi"' in s:
        return False, "zaten var"
    kod = dil_kodu(yol)
    if kod is None:
        return False, "dil kodu cozulemedi"
    rozet = '<span class="dil-kod dil-simdi">%s</span>' % kod
    # Once bayrakli bicim: bayragi rozetle DEGISTIR (eklemek yerine).
    yeni, n = _SUMMARY_BAYRAK.subn(
        lambda m: m.group(1) + rozet + m.group(2), s, count=1)
    nasil = "bayrak -> %s" % kod
    if n == 0:
        yeni, n = _SUMMARY.subn(
            lambda m: m.group(1) + rozet + m.group(2), s, count=1)
        nasil = kod
    if n == 0:
        # ⚠️ Sessizce gecme: desen tutmadiysa o sayfa duzelmemis demektir.
        return False, "⚠️ SUMMARY DESENI TUTMADI — elle bakilmali"
    if UYGULA:
        _yaz(yol, yeni)
    return True, nasil


def css_duzelt(yol, girinti):
    """Taban ve dar-ekran kurallarini ekler. (degisti_mi, sebep)"""
    s = _oku(yol)
    if "dil-simdi" in s:
        return False, "zaten var"
    taban = _CSS_TABAN if girinti else _CSS_TABAN.lstrip()
    dar = _CSS_DAR if girinti else "\n".join(
        l[2:] if l.startswith("    ") else l for l in _CSS_DAR.split("\n"))

    # 1) Taban kurali: `.ok` kuralinin hemen ardina.
    m = re.search(r'^([ \t]*)\.dil-sec>summary \.ok\{[^\n]*\n', s, re.M)
    if not m:
        return False, "⚠️ .ok kurali bulunamadi"
    s = s[:m.end()] + taban + s[m.end():]

    # 2) Dar ekran kurallari: `.dil-ad{display:none}` satirinin ardina.
    m = re.search(r'^([ \t]*)\.dil-sec>summary \.dil-ad\{display:none\}\n', s, re.M)
    if not m:
        return False, "⚠️ .dil-ad gizleme kurali bulunamadi"
    s = s[:m.end()] + dar + s[m.end():]

    if UYGULA:
        _yaz(yol, s)
    return True, "eklendi"


def main():
    print("=" * 66)
    print("SERIT MOBIL DUZELTMESI" + ("" if UYGULA else "  —  KURU CALISMA"))
    print("=" * 66)

    # --- CSS ---
    print("\n--- stil dosyalari ---")
    for yol, girinti in (("index.html", True), ("bilgi.css", False)):
        if not os.path.exists(yol):
            print("  ATLANDI  %-16s dosya yok" % yol)
            continue
        ok, sebep = css_duzelt(yol, girinti)
        print("  %-8s %-16s %s" % ("YAZILDI" if ok else "atlandi", yol, sebep))

    # --- HTML ---
    print("\n--- sayfalar ---")
    sayfalar = [a for a in os.listdir(".") if a.endswith(".html")]
    for d in DIL_KODU:
        if not d or not os.path.isdir(d):
            continue
        sayfalar += ["%s/%s" % (d, a) for a in os.listdir(d)
                     if a.endswith(".html")]
    sayfalar.sort()
    degisen, atlanan, sorunlu = 0, 0, []
    for y in sayfalar:
        ok, sebep = html_duzelt(y)
        if ok:
            degisen += 1
        elif str(sebep).startswith("⚠️"):
            sorunlu.append((y, sebep))
        else:
            atlanan += 1
    print("  duzeltilen : %d sayfa" % degisen)
    print("  atlanan    : %d (dil secici yok ya da zaten yapilmis)" % atlanan)
    if sorunlu:
        print("\n  *** ELLE BAKILACAK ***")
        for y, s in sorunlu:
            print("    %-44s %s" % (y, s))

    print("\n" + "=" * 66)
    if UYGULA:
        print("YAZILDI. Simdi: python denetle.py")
    else:
        print("HICBIR DOSYA DEGISMEDI. Uygulamak icin: --uygula")
    return 1 if sorunlu else 0


if __name__ == "__main__":
    sys.exit(main())
