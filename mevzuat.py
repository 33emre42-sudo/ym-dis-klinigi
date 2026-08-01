# -*- coding: utf-8 -*-
"""
MEVZUAT TARAYICI — 12 Kasim 2025 saglikta tanitim yonetmeligi.

Bu dosya KUTUPHANEDIR: ice aktarilir, kendi basina bir sey yazdirmaz.
`denetle.py` (site denetimi), `sss-sema-uret.py` (sema uretimi) ve
`test-denetle.py` (bekcinin kendi testi) buradan besleniyor.

Neden ayri dosya: 2. tur Codex denetiminde `duzlestir()` fonksiyonunun
iki yerde kopyalandigi ve birinin degismesi halinde digerinin sessizce
ayrisacagi isaret edildi. Ayrica `denetle.py` ice aktarilinca butun
denetimi calistirdigi icin test edilemiyordu. Ikisi de bu ayrimla
cozuldu — desenlerin TEK bir kaynagi var.

Desenlerin dogru calistigini `test-denetle.py` kaniti tutar; desen
degistiren herkes o testi de gunceller.
"""
import html as html_mod
import json
import re


def duzlestir(metin):
    """Etiketleri at, HTML varliklarini coz, butun bosluklari tek bosluga
    indir. Satir sonu yuzunden desen kacmasin diye ZORUNLU."""
    metin = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", metin,
                   flags=re.S | re.I)
    metin = re.sub(r"<[^>]+>", " ", metin)
    metin = html_mod.unescape(metin)
    return re.sub(r"\s+", " ", metin).strip()


def kucult(metin):
    return metin.lower().replace("i̇", "i")


# ===========================================================================
# MEVZUAT DESENLERI — 12 Kasim 2025 tanitim yonetmeligi
# ===========================================================================
YASAKLI = {
    "en iyi": r"\ben iyi\b",
    "garanti": r"\bgaranti",
    "agrisiz iddiasi": r"\bağrısız\b",
    # Ortuk agrisizlik vaadi — 1. tur denetim bulgusu.
    # "Agri beklenmez" demek de bir sonuc vaadidir; kisisel anestezi
    # yanitini ve akut iltihapta ek anestezi ihtiyacini disliyor.
    "ortuk agrisizlik": r"ağrı (?:beklenmez|olmaz|hissetmezsiniz|duymazsınız)"
                        r"|acı (?:duymazsınız|hissetmezsiniz)"
                        r"|hiç (?:acımaz|ağrımaz)",
    "kampanya": r"\bkampanya",
    "indirim": r"\bindirim",
    "ucretsiz": r"\bücretsiz\b",
    "fiyat rakami": r"\d[\d.]*\s*(?:tl|₺)\b",
    "hasta yorumu": r"\bmemnun kald|\byorumları\b",
    "once-sonra": r"önce\s*[-/]\s*sonra",
    "uzman iddiasi": r"\buzman(?:ımız|larımız)\b",
}

# K15 — ticari dil freni. Eskiden klinik-sitesi-olustur.py icindeydi;
# uretici 1 Agu 2026'da arsivlendigi icin buraya tasindi.
#
# 2. tur bulgu 7: acik isimler (ucret/fiyat) yakalaniyordu ama AYNI
# ticari mesaji veren ortulu kaliplar kaciyordu — "ucuz implant",
# "hesapli tedavi", "gece farki almiyoruz", "ek bedel yok" gibi.
# Bunlar eklendi. Yalin "pahali" BILEREK eklenmedi: cocukta-ilk-dis
# yazisindaki "en pahali yanilgi" benzetmesi gibi fiyat iddiasi
# olmayan kullanimlari var; yanlis alarm denetimi degersizlestirir.
TICARI = re.compile(
    r"[üu]cret|fiyat|[öo]deme|taksit|indirim|kampanya|bedava|bedelsiz"
    r"|masraf|₺|\bTL\b|dahildir|hari[çc]tir|paket"
    r"|\bucuz\b|\bhesapl[ıi]\b|\bekonomik\b|\buygun fiyat"
    r"|ek bedel|fiyat fark[ıi]|gece fark[ıi]|hafta sonu fark[ıi]",
    re.I)

# ⚠️ 2. tur bulgu 5 — BU MUAFIYET FAIL-OPEN IDI.
# Aciklama "yalnizca yasak kelimeyi DOGRUDAN olumsuzlayan kalip muaf"
# diyordu; uygulama ise eslesmenin +-70 karakterinde HERHANGI bir MUAF
# ariyordu. Sonuc: "Fiyat yayımlayamıyoruz. En iyi kliniğiz." metninde
# "en iyi" ihlali, yakindaki fiyat aciklamasi yuzunden AFFEDILIYORDU.
# Ustelik muafiyet butun YASAKLI siniflarina uygulaniyordu.
#
# Artik:
#   * MUAF yalnizca TICARI eslesmelerinde gecerli (YASAKLI'da DEGIL).
#   * Pencere degil, eslesmenin bulundugu CUMLE inceleniyor.
MUAF = re.compile(
    r"(fiyat|ücret|kampanya|indirim|ödeme)[^.]{0,60}"
    r"(paylaşamıyoruz|yayımlayamıyoruz|veremiyoruz|izin vermiyor"
    r"|yayımlamasına izin)")


def _cumle(metin, konum):
    """Verilen konumun icinde bulundugu cumleyi dondurur.

    Pencere yerine cumle kullaniliyor: bir onceki cumledeki muafiyet
    aciklamasi, sonraki cumledeki ihlali affetmesin."""
    bas = metin.rfind(".", 0, konum) + 1
    son = metin.find(".", konum)
    return metin[bas:son if son != -1 else len(metin)]

# Sitede zaten herkese acik olan degerler yanlis alarm uretmesin
IZINLI_PARCA = ["0541 732 43 76", "905417324376", "google-site-verification"]

PUAN_IZI = [r"aggregateRating", r"ratingValue", r"reviewCount",
            r"\bGoogle'?da\s+\d", r"\d\s*[,.]\s*\d\s*·\s*\d+\s*değerlendirme"]

EMOJI_ISTISNA = {"💬", "🦷"}


def mevzuat_tara(ham_html, etiket):
    """Bir HTML dosyasinin TAMAMINI tarar — head dahil.

    head'in disarida birakilmasi 1. tur bulgusuydu: meta description
    veya JSON-LD icine yazilan bir ihlal denetimden geciyordu."""
    sorunlar = []

    # 1) gorunur metin + 2) head'deki meta iceriKleri + 3) JSON-LD degerleri
    #    + 4) KULLANICIYA SUNULAN OZNITELIKLER
    parcalar = [duzlestir(ham_html)]

    # ⚠️ 2. tur bulgu 6: duzlestir() etiketleri OZNITELIKLERIYLE birlikte
    # siliyor. Yani <img alt="En iyi diş kliniği"> ya da
    # aria-label="Ücretsiz muayene" denetimden GECIYORDU. Bu metinler
    # ekran okuyucuya okunur ve gorsel yuklenmediginde ekranda gorunur —
    # mevzuat acisindan "gorunmuyor" sayilamaz.
    for oz in ("alt", "title", "aria-label", "aria-description",
               "placeholder", "value"):
        for m in re.finditer(r'\b%s="([^"]*)"' % oz, ham_html, re.I):
            parcalar.append(m.group(1))

    for m in re.finditer(r'<meta[^>]+content="([^"]*)"', ham_html, re.I):
        parcalar.append(m.group(1))
    for m in re.finditer(r"<title[^>]*>(.*?)</title>", ham_html, re.S | re.I):
        parcalar.append(m.group(1))
    for blok in re.findall(
            r'<script type="application/ld\+json">(.*?)</script>',
            ham_html, re.S):
        try:
            def gez(d):
                if isinstance(d, dict):
                    for v in d.values():
                        gez(v)
                elif isinstance(d, list):
                    for v in d:
                        gez(v)
                elif isinstance(d, str):
                    parcalar.append(d)
            gez(json.loads(blok))
        except json.JSONDecodeError:
            pass

    metin = kucult(" ".join(parcalar))
    for izin in IZINLI_PARCA:
        metin = metin.replace(kucult(izin), " ")

    # YASAKLI siniflarinda MUAFIYET YOK. "En iyi", "garanti", "ağrısız"
    # gibi ifadelerin mesru bir istisnasi bulunmuyor; yakinda bir fiyat
    # aciklamasi olmasi bunlari affetmez (2. tur bulgu 5).
    for ad, desen in YASAKLI.items():
        m = re.search(desen, metin)
        if m:
            sorunlar.append("%s: %s" % (ad, m.group(0)[:30]))

    # TICARI'de muafiyet gecerli — ama yalnizca AYNI CUMLEDE.
    for m in TICARI.finditer(metin):
        if not MUAF.search(_cumle(metin, m.start())):
            sorunlar.append("K15: %s" % m.group(0))
            break
    for desen in PUAN_IZI:
        if re.search(desen, ham_html, re.I):
            sorunlar.append("puan/yorum beyani: %s" % desen)
            break
    return sorunlar
