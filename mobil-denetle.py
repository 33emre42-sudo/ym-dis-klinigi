#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MOBIL DEGISMEZ DENETIMI — `denetle.py`nin bakmadigi sinif.

    python mobil-denetle.py        # cikis 0 = temiz, 1 = bulgu

--------------------------------------------------------------------
⚠️ NE YAPAR, NE YAPMAZ — ONCE BUNU OKU

Bu betik TARAYICI CALISTIRMAZ. Yerlesim hesaplamaz; "su oge su
pikselde" diyemez. Yaptigi sey, gecmiste GERCEKTEN yasanmis mobil
hatalarin ARDINDA YATAN DEGISMEZLERI dogrulamak.

Neden boyle: bu projede mobil hatalarin hepsi ayni iki kokten cikti —
(a) 77 sayfa arasinda PARITE bozulmasi, (b) index.html'in gomulu stili
ile bilgi.css'in AYRISMASI. Ikisi de statik olarak olculebilir.

Gercek yerlesim olcumu (kutu, cakisma, tasma) hala tarayicida
yapilmali; bu betik onun yerine gecmez, onu GEREKSIZ KILMAZ.

--------------------------------------------------------------------
Kapsanan gercek olaylar:

  · Sohbet dugmesi "Mesaj gonder"in UZERINDE oturuyordu (56px tam
    ortusme) — `#sohbet-ac` alt bosluguyla `.sabit` yuksekligi
    arasindaki iliski.
  · Dil butonu yalnizca "▼" gosteriyordu — rozet 76 sayfaya girdi,
    ANA SAYFAYA girmedi (tekrar-kosulabilirlik kontrolu fazla genisti).
  · Dil butonu seridin 38px disina tasti — marka adi nowrap yapilinca
    telefon dugmesi buyudu; mobilde ikon-only olmasi gerekiyor.
  · Eylem cubugu 1/78 sayfadaydi.
  · `.dugme.ikincil` bilgi.css'te tanimsizdi.
  · `gece-hafta-sonu-dis-hekimi.html` </body></html> olmadan bitiyordu.
  · 35 dil sayfasinda bayrak emojisi kalmisti (karar kok sayfalara
    uygulanip dil sayfalari guncellenmemisti).
  · "Ara" etiketi yabanci sayfalarda Turkce kalabilir.
"""
import io
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
os.chdir(os.path.dirname(os.path.abspath(__file__)))

DILLER = ("de", "en", "es", "fr", "ru")
ARA_ETIKET = {"": "Ara", "en": "Call", "es": "Llamar",
              "fr": "Appeler", "de": "Anrufen", "ru": "&#1055;"}

hata = 0


def kontrol(ad, kosul, ayrinti=""):
    global hata
    print("  %s  %-52s %s" % ("TAMAM" if kosul else "HATA ", ad, ayrinti))
    if not kosul:
        hata += 1


def oku(y):
    return io.open(y, encoding="utf-8").read()


def yorumsuz(s):
    """CSS ve HTML yorumlarini cikarir.

    ⚠️ Yorumlar kodu TARIF eder ve icinde ornek kural/etiket gecebilir.
    Denetim yorumdaki ornegi GERCEK sanarsa yanlis alarm verir — ya da
    daha kotusu, gercek bir sorunu maskeler.

    Bu projede iki kez yasandi:
      · `denetle.py` bir yorumda gecen acik etiketi sayip
        "<details> 3 ac / 2 kapa" dedi (HTML dengeliydi).
      · Burada, KALDIRILMIS bir kurali tarif eden yorum yuzunden
        "daha dar medya sorgusu eziyor" alarmi verildi (kural silinmisti).

    Ornek bazinda duzeltmek yerine sinif kapatiliyor.
    """
    s = re.sub(r"/\*.*?\*/", " ", s, flags=re.S)
    s = re.sub(r"<!--.*?-->", " ", s, flags=re.S)
    return s


def sayfalar():
    s = [a for a in os.listdir(".") if a.endswith(".html")]
    for d in DILLER:
        if os.path.isdir(d):
            s += ["%s/%s" % (d, a) for a in os.listdir(d) if a.endswith(".html")]
    return sorted(s)


def dil_kodu(y):
    d = os.path.dirname(y).replace(os.sep, "/").strip("./")
    k = d.split("/")[0] if d else ""
    return k if k in ARA_ETIKET else ""


print("=" * 74)
print("MOBIL DEGISMEZ DENETIMI")
print("=" * 74)

sf = sayfalar()
# Kapsam: ust seridi ve menusu olan sayfalar. gizlilik.html disarida.
kapsam = [y for y in sf if '<nav class="menu"' in oku(y)]

# ---------------------------------------------------------------- 1
print("\n--- 1/4  sayfa paritesi (%d sayfa) ---" % len(kapsam))

beklenen = (
    ("hamburger menu", 'class="menu-ac"'),
    ("dil kodu rozeti", 'class="dil-kod dil-simdi"'),
    ('eylem cubugu (.sabit)', 'class="sabit"'),
    ("arayuz.js baglantisi", "arayuz.js"),
)
for ad, desen in beklenen:
    eksik = [y for y in kapsam if desen not in oku(y)]
    kontrol("her sayfada %s var" % ad, not eksik,
            ("EKSIK: %s" % eksik[:3]) if eksik else "%d sayfa" % len(kapsam))

# ⚠️ Bayrak emojisi: karar "kod rozeti kullan" idi, dil sayfalari
# guncellenmeden kalmisti. Bolgesel-gosterge cifti = bayrak.
bayrakli = [y for y in sf
            if re.search(r"[\U0001F1E6-\U0001F1FF]", oku(y))]
kontrol("hicbir sayfada bayrak emojisi yok", not bayrakli,
        ("BULUNDU: %s" % bayrakli[:3]) if bayrakli else "%d sayfa" % len(sf))

kapanmayan = [y for y in sf if "</body>" not in oku(y) or "</html>" not in oku(y)]
kontrol("her sayfa </body></html> ile kapaniyor", not kapanmayan,
        ("KAPANMAYAN: %s" % kapanmayan) if kapanmayan else "%d sayfa" % len(sf))

# arayuz.js yolu alt klasorde ../ olmali
yanlis_yol = []
for y in kapsam:
    s = oku(y)
    m = re.search(r'src="([^"]*arayuz\.js)"', s)
    if not m:
        continue
    gerekli = "../arayuz.js" if "/" in y else "arayuz.js"
    if m.group(1) != gerekli:
        yanlis_yol.append("%s -> %s (olmasi gereken %s)" % (y, m.group(1), gerekli))
kontrol("arayuz.js yolu dogru", not yanlis_yol,
        yanlis_yol[0] if yanlis_yol else "kok ve dil klasorleri")

# ---------------------------------------------------------------- 2
print("\n--- 2/4  dil etiketi paritesi ---")
# ⚠️ "Ara" Turkce. Yabanci sayfada Turkce dugme, denetimdeki
# "her dil AYNI operasyonel sozu veriyor" ilkesini bozar.
yanlis_etiket = []
for y in kapsam:
    s = oku(y)
    m = re.search(r'<div class="sabit">(.*?)</div>', s, re.S)
    if not m:
        continue
    k = dil_kodu(y)
    if ARA_ETIKET[k] not in m.group(1):
        yanlis_etiket.append("%s (%s bekleniyordu)" % (y, ARA_ETIKET[k] or "Ara"))
kontrol("cubuk 'Ara' etiketi sayfanin dilinde", not yanlis_etiket,
        yanlis_etiket[0] if yanlis_etiket else "%d dil" % (len(DILLER) + 1))

# ---------------------------------------------------------------- 3
print("\n--- 3/4  iki stil kaynagi AYRISMIS mi ---")
# ⚠️ index.html kendi gomulu stilini, alt sayfalar bilgi.css'i
# kullaniyor. Bu ayrim daha once tuzak oldu: dil secici bilgi.css'e
# yazilmis, ana sayfada ciplak liste gorunmustu. Kurallarin IKISINDE
# DE bulunmasi sart.
ih, bc = yorumsuz(oku("index.html")), yorumsuz(oku("bilgi.css"))
ORTAK = (
    (".menu-ac", ".menu-ac"),
    ("hamburger :has() kapisi", "@supports selector(:has(*))"),
    ("hamburger acilma kurali", ".serit:has(.menu-ac[open]) + .menu"),
    (".sabit kurali", ".sabit{"),
    (".dugme.ikincil", ".dugme.ikincil"),
    ("dil kodu rozeti kurali", ".dil-simdi"),
    ("mobilde telefon ikon-only", ".serit-tel span{display:none}"),
)
for ad, desen in ORTAK:
    v_ih, v_bc = desen in ih, desen in bc
    kontrol("%s her iki kaynakta" % ad, v_ih and v_bc,
            "" if (v_ih and v_bc) else
            "index.html=%s  bilgi.css=%s" % ("var" if v_ih else "YOK",
                                             "var" if v_bc else "YOK"))

# ---------------------------------------------------------------- 4
print("\n--- 4/4  sayisal degismezler ---")


def _px(kaynak, desen):
    m = re.search(desen, kaynak)
    return int(m.group(1)) if m else None


# Cubuk varsa govdenin alt boslugu cubugu KARSILAMALI, yoksa son
# icerik cubugun altinda kalir.
for ad, kaynak in (("index.html", ih), ("bilgi.css", bc)):
    pb = _px(kaynak, r"body\{padding-bottom:(\d+)px\}")
    kontrol("%s: cubuk icin govde alt boslugu" % ad, pb is not None and pb >= 80,
            ("%spx" % pb) if pb else "TANIMSIZ — icerik cubugun altinda kalir")

# ⚠️ 56px TAM ORTUSME yasandi: sohbet dugmesi cubugun uzerindeydi.
# Dugmenin alt boslugu, cubugun kapladigi alani ASMALI.
m = re.search(r"#sohbet-ac\{bottom:calc\((\d+)px \+ (\d+)px\)\}", ih)
sohbet_alt = (int(m.group(1)) + int(m.group(2))) if m else None
pb_ih = _px(ih, r"body\{padding-bottom:(\d+)px\}")
kontrol("sohbet dugmesi cubugun USTUNDE",
        sohbet_alt is not None and pb_ih is not None and sohbet_alt > pb_ih,
        ("dugme %spx > cubuk alani %spx" % (sohbet_alt, pb_ih))
        if sohbet_alt and pb_ih else "olculemedi — elle bakilmali")

# Esikler ayni olmali: `.sabit` 720px'te goruunuyor, sohbet dugmesinin
# duzeltmesi de 720px'te devreye girmeli. Ayrisirsa cakisma geri doner.
esik_sabit = re.search(r"@media \(max-width:720px\)\{\s*\.sabit\{display:flex\}", ih)
esik_sohbet = re.search(r"@media \(max-width:720px\)\{\s*#sohbet-ac\{bottom:calc", ih)
kontrol("cubuk ve sohbet duzeltmesi AYNI esikte (720px)",
        bool(esik_sabit) and bool(esik_sohbet),
        "" if (esik_sabit and esik_sohbet) else "esikler ayrismis — cakisma geri doner")

# ⚠️ MENU PANELI BASLIGIN ALTINA SABITLENIYOR ve `top` degeri baslik
# yuksekligine BAGLI. Ikisi ayrisirsa panel ya basligi orter ya da
# altinda bosluk birakir. `.serit .sar{height:64px}` + 1px alt cizgi = 65px.
for ad, kaynak in (("index.html", ih), ("bilgi.css", bc)):
    yuk = _px(kaynak, r"\.serit \.sar\{[^}]*height:(\d+)px")
    ust = _px(kaynak, r"\.serit:has\(\.menu-ac\[open\]\) \+ \.menu\{[^}]*top:(\d+)px")
    kontrol("%s: menu paneli basligin ALTINDA baslar" % ad,
            yuk is not None and ust is not None and ust == yuk + 1,
            "serit %spx + 1 = %s, panel top:%s" % (yuk, (yuk + 1) if yuk else "?", ust))

# ⚠️ Panel SABIT konumda olmali. `static` kalirsa sayfa kaydirilinca
# ekranin disina cikar — menu "acilmiyor" gorunur (8 Agu, hekim bildirdi).
for ad, kaynak in (("index.html", ih), ("bilgi.css", bc)):
    m = re.search(r"\.serit:has\(\.menu-ac\[open\]\) \+ \.menu\{([^}]*)\}", kaynak)
    sabit = bool(m) and "position:fixed" in m.group(1)
    kontrol("%s: menu paneli position:fixed" % ad,
            sabit,
            "" if sabit else
            "static kalirsa kaydirinca ekran disinda acilir")

# ⚠️ Klavye acilinca duzen alani kuculmeli; yoksa sohbetin yazi alani
# ve son mesajlar klavyenin altinda kalir.
_interactive_widget = "interactive-widget=resizes-content" in ih
kontrol("viewport meta'sinda interactive-widget",
        _interactive_widget,
        "" if _interactive_widget else
        "klavye acikken sohbet okunamiyordu")

# `vh` klavye/tarayici cubugu ile degismez; `dvh` degisir.
# ⚠️ Dosyada BIRDEN COK `@media (max-width:720px)` blogu var (biri eylem
# cubugu, biri sohbet). Ilk yazilista desen ILK bloga takilmisti ve
# kontrol yanlis yerde "dvh yok" diyordu — kendi kontrolumun yanlis
# pozitifi. Artik dogrudan `#ym-sohbet` kuralina bakiliyor: mobil surum
# `left:10px` ile ayirt ediliyor.
_sohbet_kurallari = re.findall(r"#ym-sohbet\{([^}]*)\}", ih)
_mobil_sohbet = [k for k in _sohbet_kurallari if "left:10px" in k]
kontrol("mobil sohbet yuksekligi dvh kullaniyor",
        bool(_mobil_sohbet) and "dvh" in _mobil_sohbet[0]
        and "100vh" not in _mobil_sohbet[0],
        "vh klavye acilinca kuculmez"
        if not _mobil_sohbet else _mobil_sohbet[0][:60])

# ⚠️ DAHA DAR bir medya sorgusu tabaka kuralini EZMEMELI.
# Gercek olay: dosyanin sonunda kalmis
#   `@media (max-width:520px){#ym-sohbet{right:12px;bottom:80px}}`
# 720px'lik tabaka kuralindan SONRA geldigi icin dar ekranda kazaniyordu.
# Olculdu: 375px'te panelin alt boslugu 10px degil 80px cikiyordu — yani
# duzeltme yaziliydi ama YURURLUKTE DEGILDI. Bu sinif sessiz: kural
# dosyada duruyor, kimse ezildigini gormuyor.
_ezen = []
for _m in re.finditer(r"@media \(max-width:(\d+)px\)\{[^{]*#ym-sohbet\{([^}]*)\}", ih):
    if int(_m.group(1)) < 720 and re.search(r"\b(bottom|right|left|width)\s*:", _m.group(2)):
        _ezen.append("max-width:%spx -> %s" % (_m.group(1), _m.group(2)[:40]))
kontrol("daha dar medya sorgusu sohbet konumunu EZMIYOR", not _ezen,
        _ezen[0] if _ezen else "720px tabaka kurali yururlukte")

print("\n" + "=" * 74)
print("*** %s ***" % ("HEPSI GECTI" if hata == 0 else "%d HATA" % hata))
sys.exit(1 if hata else 0)
