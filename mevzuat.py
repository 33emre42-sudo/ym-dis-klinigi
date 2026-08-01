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
from html.parser import HTMLParser


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
# ⚠️ 4. tur bulgu 4 — ILERI BAKIS YETMEDI, BEYAZ LISTEYE GECILDI.
#
# 3. turda "garanti" ve "kampanya" desenlerine dar bir negatif ileri
# bakis konulmustu ("garanti" + hemen ardindan "edilemez" -> yesil).
# Bu FAIL-OPEN cikti: olumsuzlugu TERSINE CEVIREN cumleler geciyordu:
#     "Garanti etmez değiliz."      -> "etmez" goruldu, muaf sayildi
#     "Kampanya yoktur sanmayın."   -> "yoktur" goruldu, muaf sayildi
#     "İndirim yoktur demiyoruz."   -> ayni tuzak
# Uc ornek de aslinda ticari iddia.
#
# Artik ileri bakis YOK. Yasak kelimeler kosulsuz. Bunun yerine
# yazmamiz GEREKEN risk aciklamalari TAM CUMLE olarak beyaz listede;
# tarama oncesi metinden cikariliyorlar (telefon numarasiyla ayni
# yontem). Beyaz listedeki kalibin disina cikan her kullanim yakalanir.
#
# Yeni bir guvenlik cumlesi yazilacaksa BURAYA eklenir — bilincli bir
# karar olur, kazara muafiyet olmaz.
IZINLI_CUMLE = [
    r"hiçbir tedavinin sonucu garanti edilemez",
    r"tedavi sonuçları garanti edilemez",
    r"kliniğimizde kampanya bulunmamaktadır",
    r"kampanya ve indirim duyurusu yapılmamaktadır",
]

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
# NOT: kampanya ve indirim burada da YASAKLI'daki ayni dar olumsuzlamayi
# tasiyor. Aksi halde "Kliniğimizde kampanya bulunmamaktadır" cumlesi
# YASAKLI'dan gecip TICARI'ye takiliyordu (3. tur bulgu 7'nin devami —
# duzeltme tek tarafa uygulanmisti).
TICARI = re.compile(
    r"[üu]cret|fiyat|[öo]deme|taksit|bedava|bedelsiz"
    r"|indirim|kampanya"
    r"|masraf|₺|\bTL\b|dahildir|hari[çc]tir|paket"
    r"|\bucuz\b|\bhesapl[ıi]\b|\buygun fiyat"
    # ⚠️ 3. tur bulgu 7: yalin "ekonomik" yanlis alarm veriyordu —
    # "Ekonomik koşullar ağız sağlığına erişimi etkiler" tıbbi/toplumsal
    # bir cumle, ticari teklif degil. Yalnizca HIZMET SUNUM baglaminda
    # yakalaniyor.
    r"|\bekonomik\s+(?:tedavi|çözüm|seçenek|paket|fiyat|alternatif)"
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



# Sitede zaten herkese acik olan degerler yanlis alarm uretmesin
IZINLI_PARCA = ["0541 732 43 76", "905417324376", "google-site-verification"]

PUAN_IZI = [r"aggregateRating", r"ratingValue", r"reviewCount",
            r"\bGoogle'?da\s+\d", r"\d\s*[,.]\s*\d\s*·\s*\d+\s*değerlendirme"]

EMOJI_ISTISNA = {"💬", "🦷"}


class _OznitelikToplayici(HTMLParser):
    """Kullaniciya SUNULAN oznitelik metinlerini toplar.

    ⚠️ 3. tur bulgu 6: bunlar once regex ile okunuyordu ve regex
    yalnizca CIFT TIRNAKLI bicimi taniyordu. Yani su ucu de kaciyordu:
        alt='En iyi diş kliniği'            (tek tirnak)
        alt="En &#105;yi diş kliniği"       (HTML varligi)
    Ayrica BUTUN value alanlari taraniyordu; <input type="hidden"
    value="kampanya_v2"> gibi teknik bir deger yanlis alarm veriyordu.

    HTML ayristiricisi her iki tirnak bicimini de tanir ve oznitelik
    degerlerindeki karakter referanslarini kendisi cozer."""

    ILGILI = ("alt", "title", "aria-label", "aria-description",
              "placeholder")
    # ⚠️ 4. tur bulgu 6: value YALNIZCA <input type="button|submit|reset">
    # icin kullaniciya gorunen etikettir. <button value="kampanya_v2">
    # ve <option value="ekonomik"> icinde value TEKNIK gonderim
    # degeridir; kullanici gorunen METNI okur ve o metin zaten
    # duzlestir() ile taraniyor. Bunlari taramak yanlis alarm uretip
    # guvenli yayini gereksiz yere durduruyordu.
    VALUE_INPUT = ("button", "submit", "reset")

    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.parcalar = []

    def handle_starttag(self, etiket, oznitelikler):
        d = {}
        for k, v in oznitelikler:
            if v:
                d[k.lower()] = v
        for k in self.ILGILI:
            if d.get(k):
                self.parcalar.append(d[k])
        if etiket == "meta" and d.get("content"):
            self.parcalar.append(d["content"])
        if etiket == "input":
            tur = (d.get("type") or "text").lower()
            if tur in self.VALUE_INPUT and d.get("value"):
                self.parcalar.append(d["value"])
        # button / option value BILEREK taranmiyor (yukaridaki not).

    def handle_startendtag(self, etiket, oznitelikler):
        self.handle_starttag(etiket, oznitelikler)

    def error(self, mesaj):       # Python 3.9 oncesi soyut metot
        pass


def _muaf_mi(metin, eslesme):
    """`eslesme` DOGRUDAN olumsuzlanmis mi?

    ⚠️ 3. tur bulgu 5: muafiyet 2. turda "ayni cumle" ile
    sinirlandirilmisti ama bulunan muafiyetin DENETLENEN eslesmeye ait
    oldugu dogrulanmiyordu. Sonuc:
        "Fiyat yayımlayamıyoruz; taksit seçeneğimiz var."
    cumlesinde fiyat aciklamasi yuzunden TAKSIT de muaf oluyordu.

    Artik muafiyet konuma bagli: MUAF kalibinin ticari kelimesi
    (1. grup) TAM OLARAK denetlenen eslesmenin konumunda basliyorsa
    muafiyet ona aittir. Baska bir kelimenin muafiyeti bunu affetmez.
    Boylece cumle siniri bulmaya da gerek kalmadi — nokta/unlem/soru
    isareti veya HTML blogu ayrimi sorunu ortadan kalkti."""
    for mm in MUAF.finditer(metin):
        if mm.start(1) == eslesme.start():
            return True
    return False


def mevzuat_tara(ham_html, etiket):
    """Bir HTML dosyasinin TAMAMINI tarar — head dahil.

    head'in disarida birakilmasi 1. tur bulgusuydu: meta description
    veya JSON-LD icine yazilan bir ihlal denetimden geciyordu.

    ⚠️ 3. tur bulgu 5: parcalar artik TEK BIR METINDE BIRLESTIRILMIYOR.
    Birlestirince, noktasiz bir meta iceriginin sonundaki muafiyet bir
    sonraki parcanin basindaki ihlali affedebiliyordu. Her parca ayri
    taraniyor."""
    sorunlar = []

    # 1) gorunur metin
    parcalar = [duzlestir(ham_html)]

    # 2) kullaniciya sunulan oznitelikler + meta content (ayristiriciyla)
    toplayici = _OznitelikToplayici()
    try:
        toplayici.feed(ham_html)
        toplayici.close()
    except Exception:
        pass                      # bozuk HTML denetimi durdurmasin
    parcalar.extend(toplayici.parcalar)

    # 3) <title>
    for m in re.finditer(r"<title[^>]*>(.*?)</title>", ham_html, re.S | re.I):
        parcalar.append(html_mod.unescape(m.group(1)))

    # 4) JSON-LD icindeki her metin degeri
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

    gorulen = set()
    for ham_parca in parcalar:
        metin = kucult(ham_parca)
        for izin in IZINLI_PARCA:
            metin = metin.replace(kucult(izin), " ")
        # Onaylanmis guvenlik cumleleri taramadan CIKARILIR (4. tur b4).
        # Ileri bakis yerine bu yontem: kalibin disina cikan her
        # kullanim yakalanmaya devam eder.
        for izin in IZINLI_CUMLE:
            metin = re.sub(izin, " ", metin)
        if not metin.strip():
            continue

        # YASAKLI — muafiyet YOK, yalnizca kalibin kendi icine yazilmis
        # dar olumsuzlamalar yesil (bkz. YASAKLI desenlerindeki
        # negatif ileri bakislar).
        for ad, desen in YASAKLI.items():
            m = re.search(desen, metin)
            if m and ad not in gorulen:
                gorulen.add(ad)
                sorunlar.append("%s: %s" % (ad, m.group(0)[:30]))

        # TICARI — muafiyet gecerli, ama YALNIZCA eslesmenin kendisine ait
        for m in TICARI.finditer(metin):
            if not _muaf_mi(metin, m):
                anahtar = "K15:" + m.group(0)
                if anahtar not in gorulen:
                    gorulen.add(anahtar)
                    sorunlar.append("K15: %s" % m.group(0))
                break

    for desen in PUAN_IZI:
        if re.search(desen, ham_html, re.I):
            sorunlar.append("puan/yorum beyani: %s" % desen)
            break
    return sorunlar
