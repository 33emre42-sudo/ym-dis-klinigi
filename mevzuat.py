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
# METIN KODLAMASI — cift kodlama tespiti
# ===========================================================================
# 1 Agu 2026: index.html'deki BUTUN Turkce karakterler cift kodlandi ve
# 20 dakika oyle yayinda kaldi. Sebep PowerShell 5.1'in klasik tuzagi:
# `Get-Content -Raw` -Encoding verilmeyince dosyayi sistem ANSI kod
# sayfasiyla (cp1254) okur, `Set-Content -Encoding utf8` de o bozuk
# metni UTF-8 olarak yazar. "Diş" -> "DiÅŸ", basa BOM.
#
# Hicbir denetim yakalamadi: dosya gecerli UTF-8 kalir, kelime sayisi
# tutar, yasak kelime taramasi bozuk metinde zaten eslesmez. Yalnizca
# TARAYICIDA belli olur — yani hastada.
#
# Tespit su asimetriye dayanir: cift kodlanmis metin ANSI'ye geri
# cevrilip UTF-8 olarak COZULEBILIR; saglam Turkce metin cozulemez
# ("ş" -> 0xFE, gecersiz UTF-8 baslangic bayti).
def _ansi_baytlari(metin):
    """Metni cp1254 baytlarina cevirir.

    cp1254'te TANIMSIZ olan baytlari (0x8E, 0x9E…) .NET U+0080-U+009F
    araligina esler; Python'un kodlayicisi ise hata verir. Gercek
    hasarda 41 adet U+009E vardi ve bu fark yuzunden ilk yazdigim
    tespit fonksiyonu hasari KACIRIYORDU. C1 karakterleri kendi
    baytlarina yaziliyor."""
    b = bytearray()
    for c in metin:
        try:
            b += c.encode("cp1254")
        except UnicodeEncodeError:
            o = ord(c)
            if o >= 0x100:
                raise
            b.append(o)
    return bytes(b)


# ⚠️ 6. tur bulgu 5 — TESPIT IKI AYRI YERDEN KACIRIYORDU:
#
#   1. `metin[:40000]` ile kesiliyordu. index.html 89.452 karakter:
#      dosyanin YARISINDAN COGUNA hic bakilmiyordu. 1 Agustos'taki hasar
#      ikinci yarida olsaydi hicbir denetim gormezdi.
#
#   2. Butun ornegin cp1254'e cevrilip UTF-8 cozulmesi bekleniyordu.
#      Saglam Turkce bir bolum cozumu patlatir ("ş" -> 0xFE, gecersiz
#      UTF-8 baslangici), bu yuzden icinde tek bir bozuk parca olan
#      KARISIK dosya "temiz" donerdi. Oysa gercek hasar tam boyle
#      gorunur: dosyanin bir bolumu bozulur, gerisi saglam kalir.
#
# Artik once IZ taramasi yapiliyor: tum metin, konum siniri yok.
# Dayanak — saglam Turkce metinde "Ã", "Ä", "Å" karakterleri BULUNMAZ
# (alfabede yoklar), oysa cift kodlanmis her Turkce karakter bunlardan
# biriyle baslayan bir cifte donusur ("Diş" -> "DiÅŸ"). C1 kontrol
# karakterleri (U+0080-U+009F) de gecerli metinde olmaz; gercek hasarda
# 41 adet U+009E vardi.
_CIFT_IZ = re.compile(r"[ÃÄÅ]|[\u0080-\u009f]")


def cift_kodlanmis(metin):
    """Metin bir kez fazla kodlanmis mi?

    Iki yontem birlikte: iz taramasi KISMI hasari yakalar, tam metin
    cozumu ise dosyanin tamaminin bozuldugu hali dogrular."""
    if _CIFT_IZ.search(metin):
        return True
    if all(ord(c) < 128 for c in metin):
        return False                     # ASCII metinde soru yok
    try:
        _ansi_baytlari(metin).decode("utf-8")
        return True
    except (UnicodeEncodeError, UnicodeDecodeError):
        return False


def ansi_okumasi(baytlar):
    """PowerShell'in hatali okumasinin taklidi — YALNIZCA test icin.

    Bekcinin kendisi de bir varsayim; hasari yeniden uretmeden
    yakaladigini iddia edemeyiz."""
    cikti = []
    for b in bytearray(baytlar):
        try:
            cikti.append(bytes([b]).decode("cp1254"))
        except UnicodeDecodeError:
            cikti.append(chr(b))         # tanimsiz bayt -> C1
    return "".join(cikti)


# Blok duzeyindeki etiketler. Inline olanlar (b, strong, em, a, span…)
# BILEREK disarida: "<b>garanti edilemez</b>" cumleyi bolmemeli.
_BLOK = (r"p|div|li|ul|ol|h[1-6]|t[dhr]|table|thead|tbody|section|article"
         r"|header|footer|nav|main|aside|blockquote|figure|figcaption"
         r"|dl|dt|dd|form|fieldset|legend|label|option|select|textarea"
         r"|title|summary|details|br|hr|template")


def mevzuat_metni(ham):
    """Gorunur metin — BLOK sinirlari CUMLE siniri sayilir.

    ⚠️ 5. tur bulgu 2'nin duzeltmesini yazarken cikti: `duzlestir()`
    butun etiketleri bosluga cevirir. Muafiyet artik tam cumle
    esitligine dayandigi icin bu, iki ayri blogu tek cumle gibi
    gosteriyordu:

        <title>Test</title> … <p>Mevzuat gereği fiyat bilgisi
        paylaşamıyoruz.</p>
        -> "test mevzuat gereği fiyat bilgisi paylaşamıyoruz"

    Onayli cumle listede aynen dursa bile eslesmiyordu. Yonu
    fail-CLOSED oldugu icin tehlikeli degildi ama mesru metni
    engelliyordu: bir baslik ya da komsu paragraf, altindaki guvenlik
    cumlesini kullanilamaz kiliyordu."""
    metin = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", ham,
                   flags=re.S | re.I)
    metin = re.sub(r"</?(?:%s)\b[^>]*>" % _BLOK, " . ", metin, flags=re.I)
    metin = re.sub(r"<[^>]+>", " ", metin)
    metin = html_mod.unescape(metin)
    return re.sub(r"\s+", " ", metin).strip()


# ===========================================================================
# MUAFIYET — TAM CUMLE ESITLIGI   (5. tur bulgu 2)
# ===========================================================================
# Bu, AYNI KOKUN dorduncu duzeltmesi. Gecmisi bilerek burada tutuyorum;
# bes turda dort kez ayni tuzaga dusuldu:
#
#   2. tur b5  Muafiyet, eslesmenin +-70 karakterinde ARANIYORDU.
#              "Fiyat yayımlayamıyoruz. En iyi kliniğiz."  -> geciyordu
#   3. tur b5  Muafiyet ayni cumleye baglandi ama HANGI kelimeye ait
#              oldugu dogrulanmiyordu.
#              "Fiyat yayımlayamıyoruz; taksit seçeneğimiz var."
#   4. tur b4  Negatif ileri bakis fail-open cikti.
#              "Garanti etmez değiliz."  -> geciyordu
#   5. tur b2  Beyaz listedeki cumle, daha uzun bir metnin ICINDEN
#              KOSULSUZ siliniyordu:
#              "Hiçbir tedavinin sonucu garanti edilemez demiyoruz."
#              -> onayli parca silindi, geriye "demiyoruz" kaldi, GECTI.
#              Ayni sekilde MUAF kalibi cumlenin bittigini aramadigi icin
#              "Fiyat veremiyoruz demiyoruz; implant 5000 lira." geciyordu.
#
# ORTAK KOK: muafiyet her seferinde PARCA duzeyinde veriliyordu. Parcayi
# neyin cevreledigine bakilmadigi surece cevreye her zaman bir ek
# yazilabilir. Desen ekleyerek kapatilacak bir acik degildi.
#
# ARTIK TEK KURAL:
#   Bir yasak eslesme, ancak ICINDE BULUNDUGU CUMLENIN TAMAMI
#   ONAYLI_CUMLE listesindeki bir cumleyle birebir esitse muaf olur.
#   Metinden hicbir sey SILINMEZ; silme islemi ne yapildigini gizliyordu.
#
# ⚠️ 6. tur bulgu 3 — O "BILINEN SINIR" GERCEK BIR ACIKTI.
# Cumle siniri `.!?;:` idi. Yani "...garanti edilemez; demiyoruz."
# metninde `garanti` eslesmesinin cumlesi yalnizca onayli ilk parcaydi
# ve muafiyet veriliyordu. Denetci uc yolu da gosterdi ve UCU DE
# denetimden gecti: "; demiyoruz", ": aslinda paylasabiliriz",
# ". Demiyoruz." Sozlesme "cevresine ek yazilamaz" diyordu; dogru degildi.
#
# Iki katmanli kapatma:
# ILK DENEME YANLISTI, KAYDA GECIYOR: cumle sinirindan `;:` cikarilmisti.
# Bu, terslemeyi yakaliyordu ama MESRU metni de engelliyordu — bekcinin
# kendi testinde iki dogru cumle kirmiziya dondu:
#     "Hiçbir tedavinin sonucu garanti edilemez; iyileşme kişiden
#      kişiye değişir."
# Yazmamiz GEREKEN durustce aciklamalar tam bu bicimde. Her mesru devami
# ONAYLI_CUMLE'ye eklemek de olcusuz buyur (kombinasyon patlamasi).
#
# Dogru ayrim noktalama degil, DEVAMIN NE YAPTIGI: "; iyileşme kişiden
# kişiye değişir" cumleyi destekler, "; demiyoruz" tersine cevirir.
# Bu yuzden sinir eski haline dondu ve koruma su katmana yuklendi:
#   onayli cumlenin ARDINDAN gelen cumlede tersleme belirteci varsa
#   muafiyet DUSER (`_TERSLEME`).
# Ayni mekanizma uc yolu birden kapatir: "; demiyoruz", ": aslinda
# paylasabiliriz" ve ". Demiyoruz." — ucu de "sonraki cumle"dir.
#
# Yeni bir guvenlik cumlesi yazilacaksa BURAYA eklenir. Denetim hatasi
# eklenecek cumleyi sadelestirilmis haliyle ekrana yazar; kopyalayin.
ONAYLI_CUMLE = [
    # Yazmamiz GEREKEN risk aciklamalari
    "Hiçbir tedavinin sonucu garanti edilemez",
    "Tedavi sonuçları garanti edilemez",
    "Kliniğimizde kampanya bulunmamaktadır",
    "Kampanya ve indirim duyurusu yapılmamaktadır",
    # K15 fiyat aciklamalari — eskiden ayri bir MUAF regex'iydi.
    # Regex "cumle bitti mi" diye bakmadigi icin sonuna ek yazilabiliyordu.
    "Mevzuat gereği fiyat bilgisi paylaşamıyoruz",
    "Mevzuat gereği ücret bilgisi yayımlayamıyoruz",
    "Fiyat bilgisini bu kanalda veremiyoruz",
    # gizlilik.html — yapay zeka kanalinin sinirlari
    "tıbbi değerlendirme, ilaç önerisi ve ücret bilgisi bu kanalda "
    "verilmez, bu konular hekiminize aktarılır",
]

# Cumle siniri. Nokta fazla bolerse zarari yok: parca kisalir, birebir
# esitlik daha ZOR saglanir — yani hata yonu her zaman fail-CLOSED.
# `;` ve `:` BILEREK sinir: "garanti edilemez; iyileşme kişiden kişiye
# değişir" mesru bir devamdir ve engellenmemeli. Tersine cevirmeyi
# noktalama degil `_TERSLEME` yakalar (6. tur b3).
_CUMLE_SINIRI = re.compile(r"[.!?;:]+")

# Onayli cumlenin ARDINDAN gelip onu tersine ceviren ifadeler.
# Dar tutuldu: bir guvenlik cumlesinin hemen arkasindan gelmedikce
# bunlarin cogu masum kelimelerdir, bu yuzden yalnizca o konumda
# aranirlar. Yanlis alarm verirse metin degistirilir — hata yonu
# yine fail-CLOSED.
_TERSLEME = re.compile(
    r"\b(demiyoruz|demedik|sanmay[ıi]n|asl[ıi]nda|ger[çc]ekte"
    r"|tam tersi|aksine|[şs]aka)\b", re.I)

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


def sadelestir(cumle):
    """Karsilastirma bicimi: kucult, noktalamayi at, boslugu tekle.

    Onayli cumleler ve taranan metin AYNI islemden geciyor; yoksa
    "Kliniğimizde kampanya bulunmamaktadır." ile listedeki noktasiz
    hali eslesmezdi."""
    c = kucult(cumle)
    c = re.sub(r"[^\w\s]", " ", c)
    return re.sub(r"\s+", " ", c).strip()


_ONAYLI = frozenset(sadelestir(c) for c in ONAYLI_CUMLE)


def _cumle(metin, konum):
    """`konum`daki karakterin icinde bulundugu cumleyi dondurur."""
    bas = 0
    for m in _CUMLE_SINIRI.finditer(metin, 0, konum):
        bas = m.end()
    son = _CUMLE_SINIRI.search(metin, konum)
    return metin[bas:son.start() if son else len(metin)]


def _sonraki_cumle(metin, konum):
    """`konum`daki karakterin cumlesinden SONRAKI cumleyi dondurur."""
    son = _CUMLE_SINIRI.search(metin, konum)
    if not son:
        return ""
    bas = son.end()
    sonraki = _CUMLE_SINIRI.search(metin, bas)
    return metin[bas:sonraki.start() if sonraki else len(metin)]


def _muaf_mi(metin, eslesme):
    """Eslesmeyi iceren cumlenin TAMAMI onayli mi — ve ardindan
    tersine cevrilmiyor mu?

    Muafiyetin tek yolu budur. Yasak kelimenin cevresine yazilan her
    ek — "... demiyoruz", "... sanmayın", "; implant 5000 lira" —
    cumleyi listedekinden farkli kilar ve muafiyet DUSER.

    ⚠️ 6. tur b3: `;` ve `:` cumle siniri sayildigi surece "ek
    yazilamaz" sozu DOGRU DEGILDI; yan cumle olarak eklenen tersleme
    muafiyeti bozmuyordu. Sinir daraltildi. Nokta ile ayrilan tersleme
    ise cumle butunlugunu hic bozmadigi icin ayrica aranir: onayli
    cumlenin hemen ardindan "demiyoruz / aslinda / tam tersi" gelirse
    muafiyet duser.

    Muaf olamayan bir eslesmenin cumlesi hata metnine konur; boylece
    gercekten yazmamiz gereken yeni bir guvenlik cumlesi varsa
    kopyalanacak hali gozukur."""
    if sadelestir(_cumle(metin, eslesme.start())) not in _ONAYLI:
        return False
    return not _TERSLEME.search(_sonraki_cumle(metin, eslesme.start()))


def mevzuat_tara(ham_html, etiket):
    """Bir HTML dosyasinin TAMAMINI tarar — head dahil.

    head'in disarida birakilmasi 1. tur bulgusuydu: meta description
    veya JSON-LD icine yazilan bir ihlal denetimden geciyordu.

    ⚠️ 3. tur bulgu 5: parcalar artik TEK BIR METINDE BIRLESTIRILMIYOR.
    Birlestirince, noktasiz bir meta iceriginin sonundaki muafiyet bir
    sonraki parcanin basindaki ihlali affedebiliyordu. Her parca ayri
    taraniyor."""
    sorunlar = []

    # 1) gorunur metin — blok sinirlari cumle siniri sayilarak
    parcalar = [mevzuat_metni(ham_html)]

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
        if not metin.strip():
            continue

        # ⚠️ 5. tur bulgu 2: onayli cumleler ARTIK METINDEN SILINMIYOR.
        # Silme, yasak kelimeyi ortadan kaldirip cevresindeki tersine
        # cevirme ekini yalniz birakiyordu. Muafiyet artik her eslesme
        # icin AYRI AYRI ve cumlenin tamamina bakilarak veriliyor —
        # YASAKLI ve TICARI icin ayni mekanizma.
        for ad, desen in YASAKLI.items():
            if ad in gorulen:
                continue
            for m in re.finditer(desen, metin):
                if _muaf_mi(metin, m):
                    continue
                gorulen.add(ad)
                sorunlar.append("%s: %s" % (ad, m.group(0)[:30]))
                break

        for m in TICARI.finditer(metin):
            if _muaf_mi(metin, m):
                continue
            anahtar = "K15:" + m.group(0)
            if anahtar not in gorulen:
                gorulen.add(anahtar)
                sorunlar.append("K15: %s  <- cumle: \"%s\""
                                % (m.group(0),
                                   sadelestir(_cumle(metin, m.start()))[:90]))
            break

    for desen in PUAN_IZI:
        if re.search(desen, ham_html, re.I):
            sorunlar.append("puan/yorum beyani: %s" % desen)
            break
    return sorunlar
