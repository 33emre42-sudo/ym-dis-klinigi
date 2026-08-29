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
import unicodedata
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
#
# ⚠️ 7. tur bulgu 5 — ILK IZ TARAMASI TEK KARAKTERE BAKIYORDU (`[ÃÄÅ]`).
# Iki yonlu hataydi; ikisi de calistirilarak dogrulandi:
#
#   YANLIS ALARM: saglam metindeki "Ångström" gibi gecerli bir yabanci
#                 ozel ad, tek basina "Å" icerdigi icin hasarli sayildi.
#
#   KACIRIYORDU : Sitede cok kullanilan noktalama isaretlerinin cift
#                 kodlanmis hali Ã/Ä/Å ICERMIYOR —
#                     "—" -> "â€”"      "·" -> "Â·"      "’" -> "â€™"
#                 Yani yalnizca noktalamasi bozulmus KISMI hasar
#                 tespitten kaciyordu. Sayfa altlarindaki
#                 "0541 732 43 76 · Gizlilik" satiri tam bu kalipta.
#
# Artik tek karakter degil GERCEK BOZULMA CIFTLERI araniyor.
_CIFT_IZLER = (
    # Turkce harflerin cift kodlanmis hali
    "Ã§", "Ã‡", "Ã¶", "Ã–", "Ã¼", "Ãœ",
    "Ä±", "Ä°", "ÄŸ", "Äž", "ÅŸ", "Åž",
    # Noktalama/bosluk — "â€" U+2013..U+201D ailesinin ortak oneki
    "Â·", "Â ", "â€",
    # ⚠️ 8. tur bulgu 6: sitede gecen DIGER karakterlerin kismi bozulma
    # izleri de listede yoktu ve kaciyordu (yedisi de dogrulandi):
    #   ©->Â©   ×->Ã—   â->Ã¢   î->Ã®   →->â†’   ✦->âœ¦   🦷->ğŸ¦·
    # "â" ve "î" Turkce metinde gecer (kâr, resmî) ama bozulmus hali
    # "Ã¢"/"Ã®" saglam metinde bulunmaz.
    "Â©", "Ã—", "Ã¢", "Ã®", "â†", "âœ", "ğŸ",
)
_C1_IZ = re.compile(r"[\u0080-\u009f]")


def cift_kodlanmis(metin):
    """Metinde UTF-8'in cp1254 olarak okunmasina ait iz var mi?

    Uc katman: bozulma ciftleri KISMI hasari yakalar, C1 kontrol
    karakterleri gercek olayda gorulen U+009E gibi baytlari yakalar,
    tam metin cozumu de dosyanin tamaminin bozuldugu hali dogrular."""
    if any(iz in metin for iz in _CIFT_IZLER):
        return True
    if _C1_IZ.search(metin):
        return True
    if all(ord(c) < 128 for c in metin):
        return False                     # ASCII metinde soru yok
    try:
        _ansi_baytlari(metin).decode("utf-8")
        return True
    except (UnicodeEncodeError, UnicodeDecodeError):
        return False


# ⚠️ 9. tur bulgu 4 — YENI BIR BOZUKLUK SINIFI: BIRLESTIRICI KARAKTER.
# iletisim.html'de baslik "Çalişma saatleri̇." diye yayina cikti.
# Sebep: sayfayi kuran betikte `"ÇALIŞMA SAATLERİ".capitalize()`
# kullanilmisti. Python'un capitalize()'i Turkce bilmez:
#     "I" -> "i"  (olmasi gereken "ı")
#     "İ" -> "i" + U+0307 COMBINING DOT ABOVE
# Ekranda neredeyse dogru gorunur ama metin bozuktur: kopyalama, arama
# ve karsilastirma beklenmedik sonuc verir; ayni metin iki farkli
# bayt dizisiyle temsil edilir.
#
# `cift_kodlanmis()` bunu GORMEZ — farkli bir hasar sinifi. Turkce
# metinde birlestirici isarete gerek yoktur (butun harfler precomposed),
# bu yuzden tolerans SIFIR.
def birlestirici_var(metin):
    """Metinde birlestirici (combining) karakter var mi?

    Varsa dondurulen liste (konum, karakter) ciftleridir."""
    return [(i, k) for i, k in enumerate(metin)
            if unicodedata.combining(k)]


# ⚠️ 10. tur bulgu 1 — ACIL YONLENDIRME ESIGI.
#
# Ayni hata SINIFI ucuncu kez cikti:
#   6. tur — sohbet kutusu ag hatasinda 112 yerine klinige yonlendiriyordu
#   8. tur — macun yutulmasinda klinik degil 114 Zehir Danisma gerekiyordu
#  10. tur — 112 gerektiren belirtiler "VE" ile birbirine baglanmisti:
#
#     "...nefes veya yutma güçlüğü VE yüksek ateş acil durumdur: 112"
#
# Duz okunusu: 112 icin IKISININ DE olmasi gerekiyor. Oysa hava yolu
# belirtisi TEK BASINA acildir; ates ise tek basina "ayni gun
# degerlendirme" esigidir. Hasta bunu okuyup "atesim yok, sabahi
# beklerim" diyebilir. Ayni kalip uc sayfada birden vardi ve biri
# (dis-apsesi.html) DOKUZ turdur denetimden geciyordu — goz yakalamiyor.
#
# Kural: 112 talimatiyla AYNI CUMLEDE "ates" gecmez; ates yonlendirmesi
# ayri cumleye yazilir. Mekanik ama ogretilebilir — yazari "ikisini ayir"
# diye zorluyor ve yanlis okumaya yer birakmiyor.
#
# Bloklar AYRI AYRI bakilir: <li> ve <p> kendi cumlesidir. Aksi halde
# duzlestir() bir <ul>'un tamamini tek dizgeye ceviriyor ve listedeki
# "Yüksek ateş" maddesi asagidaki 112 paragrafiyla ayni cumleymis gibi
# gorunuyor — ilk yazimda tam da bu yanlis alarmi verdi.
_ACIL_BLOK = re.compile(r"<(p|li)\b[^>]*>(.*?)</\1>", re.S | re.I)
_ACIL_CUMLE = re.compile(r"(?<=[.!?])\s+")

# 11. tur bulgu 2 — kural GENISLETILDI.
#
# Ilk hal yalnizca "ates" ariyordu, cunku 10. turda cikan ornek oydu. Ama
# tehlike atese ozgu degil: TEK BASINA acil olan bir belirtiyi "ve" ile
# ikinci bir bulguya baglamak her durumda ayni yanlis okumayi uretiyor.
#
#     "Nefes güçlüğü VE şiddetli ağrı varsa 112'yi arayın"
#
# Nefes guclugu tek basina acildir; agri sart degildir.
#
# ⚠️ Denetci burada "cumlede veya/ya da geciyorsa muaf tut" onerdi. Oyle
# YAPILMADI: o kacis kapisi, ayni cumlede baska bir yerde gecen mesru bir
# "veya" yuzunden gercek hatayi susturur —
#     "Nefes veya yutma güçlüğü ve şiddetli ağrı varsa 112"
# kacip giderdi. Bunun yerine daha dar ve daha kesin bir kalip kuruldu:
# belirtinin HEMEN ARDINDAN "ve" geliyor mu? Boylece kacis kapisina gerek
# kalmiyor ve mesru cumleler ("yüzde ve boyunda hızla yayılan şişlik" —
# "yüzde" bir belirti degil) yanlis alarm vermiyor.
#
# ⚠️ 13. tur: nitelemeler ZORUNLU yapildi. Once hepsi istege bagliydi,
# yani duz "nefes" / "bilinç" / "yutma" tek basina hayati belirti
# sayiliyordu. Komsuluk arayan eski taramada bu zararsizdi; blok
# duzeyinde tarayan yeni surumde agiz-kurulugu.html'deki "burundan
# nefes almayı destekleyin" cumlesini kirmizi yakti. Yanlis alarm veren
# bekci kapatilir — bu yuzden niteleme sart, ama niteleme ekleri
# `\w*` ile serbest ("zorlanıyorsanız", "güçlüğünde").
_ACIL_ZORLUK = (r"(?:g[üu][çc]l[üu][ğg]\w*|darl[ıi][ğg]\w*|zorlan\w*"
                r"|s[ıi]k[ıi]nt[ıi]s[ıi])")
_ACIL_BELIRTI = (
    r"nefes(?:\s+al\w*)?\s+" + _ACIL_ZORLUK +
    r"|yut(?:ma|kunma|makta|kunmakta)\s+" + _ACIL_ZORLUK +
    r"|bilin[çc]\s+(?:bulan[ıi]kl\w*|de[ğg]i[şs]ikli\w*|kayb\w*|kapan\w*)"
    r"|bay[ıi]lma|n[öo]bet\b"
    r"|a[ğg][ıi]z taban[ıi]nda [şs]i[şs]lik"
    r"|h[ıi]zla yay[ıi]lan [şs]i[şs]lik"
    # 14. tur bulgu 3 — ikisi de sitede GERCEKTEN kullanilan bicimler
    # (dis-cekimi-sonrasi-sislik.html:85-88), ama desende yoktu:
    #   "dilinizin altı şişmişse"  = agiz tabaninda sislik'in es anlamlisi
    #   "şişlik … hızla yayılıyorsa" = mevcut kalibin TERS sozcuk sirasi
    r"|dil(?:\w+)?\s+alt[ıi](?:nda)?\s+[şs]i[şs]\w*"
    r"|[şs]i[şs]lik(?:\s+\S+){0,6}\s+h[ıi]zla\s+yay[ıi]l\w*")
# 12. tur bulgu 4 — desen genisletildi ve MIMARI ACIK kapatildi.
#
# (a) Belirti listesi eksikti: durdurulamayan kanama listede yoktu, oysa
#     tek basina 112 sebebi.
# (b) Bag sozcugu yalnizca duz "ve" idi; "ile", "hem…hem", ters sira
#     ("siddetli agri ve nefes guclugu") ve hal ekli bicimler
#     ("nefes guclugunde ve") kaciyordu.
# (c) ASCII yazim ("ates") kacıyordu — duz eslesme kullaniliyordu.
# (d) EN ONEMLISI: eski kod "112 gecmiyorsa bu bloga hic bakma" diyordu.
#     Yani hayati bir belirtiyi SADECE klinige yonlendiren bir kutu
#     mimari olarak GORUNMEZDI. yirmi-yas-disi.html bunun canli orneğiydi:
#     "Yüksek ateş, yutkunma ya da nefes güçlüğü" maddesi "hemen arayın"
#     listesindeydi ve sayfada 112 hic gecmiyordu.
_ACIL_BELIRTI += (
    r"|durdurulamayan(?: yo[ğg]un)? kanama"
    r"|kontrol alt[ıi]na al[ıi]namayan kanama"
    r"|(?:tekrarla(?:nan|yan) )?bask[ıi]ya ra[ğg]men "
    r"(?:durmayan|s[üu]ren)(?: yo[ğg]un)? kanama"
    r"|kanama(?:\s+\S+){0,6}\s+durmuyorsa"
    r"|a[ğg]z[ıi](?:n[ıi]z[ıi])?\s+h[ıi]zla dolduruyorsa")
_ACIL_BELIRTI_RE = re.compile(_ACIL_BELIRTI, re.I)

# "ates" ASCII yazilsa da yakalanmali.
_ACIL_ATES = re.compile(r"\bate[şs]\w*", re.I)

# BAG KALIBI — belirtinin HEMEN yanindaki "ve"/"hem". Iki yon de bakilir:
#   "nefes güçlüğü VE şiddetli ağrı"   (belirti -> bag)
#   "şiddetli ağrı VE nefes güçlüğü"   (bag -> belirti, ters sira)
# `\w*` Turkce hal ekini tolere ediyor: "nefes güçlüğüNDE ve …".
#
# ⚠️ Denetci burada gevsek bir tarama onerdi (kosul sozcugunden onceki
# parcada HERHANGI bir yerde "ve" ara). Denendi ve KENDI DOGRU
# metinlerimizde yanlis alarm verdi: "…, yüzde VE boyunda hızla yayılan
# şişlik, … ya da bayılma varsa 112" cumlesinde "ve" iki vucut bolgesini
# birlestiriyor, iki AYRI SART kurmuyor. Yanlis alarm veren bir bekci
# insanlar tarafindan kapatilir; bu yuzden kalip DAR tutuldu.
#
# ⚠️ TEK BASINA "ile" BILEREK DISARIDA: "Nefes güçlüğü ile karşılaşırsanız
# 112'yi arayın" mesru bir cumle ve "ile" orada baglac degil. Nadir bir
# yazimi kacirmak, her acil kutusunu kirmizi yakmaktan iyidir. Testle
# sabit. ("ile birlikte" AYRI mesele — asagiya bak.)
_ACIL_VE_BAGI = re.compile(
    r"(?:%s)\w*\s+(?:ve|hem|yan[ıi]nda)\s|\b(?:ve|hem)\s+(?:%s)"
    % (_ACIL_BELIRTI, _ACIL_BELIRTI), re.I)

# KESIN BAGLAC — 13. tur bulgu 4. "ile birlikte", "eşlik ediyorsa" gibi
# ifadeler "ve"den farkli: iki vucut bolgesini birlestirmezler, iki AYRI
# SARTI birlestirirler. Yine de KOMSULUK sarti korundu; cumle duzeyinde
# "belirti + kesin baglac" aramak denendi ve kendi DOGRU metnimizi
# kirmizi yakti:
#
#   "…kanama durmuyorsa, ağzınızı hızla dolduruyorsa YA DA kanamaya
#    baş dönmesi, bayılacak gibi olma, nefes darlığı veya çarpıntı
#    EŞLIK EDIYORSA."            (kan-sulandirici-dis-tedavisi.html)
#
# Burada "eşlik ediyorsa" bir 112 sebebini KISITLAMIYOR, listeye YENI
# bir sebep EKLIYOR — "ya da" ile baglanmis ayri bir dal. Tehlikeli olan
# tersidir: tek basina 112 gerektiren belirtinin kendisinin bir baska
# bulguya bagimli kilinmasi. Iki bicimi de o yuzden dar:
#   1. belirti HEMEN once  → "nefes güçlüğü ile birlikte ateş varsa"
#   2. belirti YONELME hali → "nefes güçlüğüne ateş eşlik ediyorsa"
#      (belirti burada eklenen degil, eklenilen taban)
_ACIL_KESIN_BAG = re.compile(
    r"(?:%s)\w*\s+(?:ile birlikte|ile beraber|yan[ıi] s[ıi]ra"
    r"|e[şs]lik ed\w+|beraberinde|birlikte)"
    r"|(?:%s)(?:y?[ae]|n[ae])\s+(?:\S+\s+){0,4}e[şs]lik ed\w+"
    % (_ACIL_BELIRTI, _ACIL_BELIRTI), re.I)

# 14. tur bulgu 2 — ayni bagimlilik TERS SIRAYLA da kurulabiliyor ve
# yukaridaki iki bicim de belirtinin ONCE gelmesini bekliyordu:
#   "Şiddetli ağrıyla birlikte nefes güçlüğü varsa 112'yi arayın."
#   "Şiddetli ağrının eşlik ettiği nefes güçlüğünde 112'yi arayın."
# Ikisinde de nefes guclugu — tek basina 112 sebebi — siddetli agrinin
# varliğina baglanmis. Agrisi olmayan hasta bekler.
#
# ⚠️ Burada da komsuluk sart: baglac ile belirti ARDISIK olmali. Yoksa
# kan-sulandirici-dis-tedavisi.html'deki dogru cumle yine kirmizi yanar
# (orada "eşlik ediyorsa" cumlenin SONUNDA ve sebep EKLIYOR). Sinama
# testi o cumleyi ayrica civiliyor.
_ACIL_KESIN_BAG_TERS = re.compile(
    r"(?:\b\S+(?:yl[ae]|l[ae])|\b\S+\s+ile)\s+(?:birlikte|beraber)\s+(?:%s)"
    r"|(?:e[şs]li[ğg]inde|beraberinde|e[şs]lik etti[ğg]i)\s+(?:%s)"
    % (_ACIL_BELIRTI, _ACIL_BELIRTI), re.I)

# Klinige yonlendiren kalip — "112 yok ama klinik var" durumunu bulmak icin.
# ⚠️ 13. tur bulgu 3: liste dort kalibi kaciriyordu ve hepsi sitede
# GERCEKTEN kullaniliyordu — "kliniği arayabilirsiniz" (index),
# "değerlendirmesi alın" (dis-apsesi), "kliniğe gelin" (kirilan-dis),
# "kliniğe başvurun" (tedaviler). Emir kipi kadar rica kipi de sayilir;
# hasta icin ikisi de "acile degil, buraya gel" demektir.
_ACIL_KLINIK = re.compile(
    r"klini[ğg]i(?:nizi)?\s+"
    r"(?:hemen\s+|aci(?:len|l)\s+|ayn[ıi] g[üu]n\s+)?"
    r"aray(?:[ıi]n|abilirsiniz|[ıi]n[ıi]z)"
    r"|klini[ğg]e\s+(?:hemen\s+)?(?:gelin|ba[şs]vurun|ula[şs][ıi]n"
    r"|gelmeniz|ba[şs]vurman[ıi]z)"
    r"|klini[ğg]imize\s+(?:ula[şs]|gelin|ba[şs]vurun)"
    r"|hemen\s+aray[ıi]n|bizi\s+aray[ıi]n|bizimle\s+ileti[şs]im"
    r"|hekim(?:iniz)?e\s+(?:ba[şs]vurun|g[öo]r[üu]n[üu]n|dan[ıi][şs][ıi]n)"
    r"|de[ğg]erlendirmesi(?:ni)?\s+al[ıi]n", re.I)


def acil_esik_hatalari(sayfa_html):
    """112 esigini atese ya da ikinci bir belirtiye baglayan cumleler.

    Uc kural:
      1. 112 talimatiyla ayni cumlede "ates" gecmez.
      2. Tek basina acil olan bir belirtinin hemen ardindan "ve" gelmez.
      3. Hayati belirtinin hemen ardindan kesin baglac ("ile birlikte")
         ya da belirtinin yonelme hali + "eşlik ediyorsa" gelmez.
    """
    bulunan = []
    for m in _ACIL_BLOK.finditer(sayfa_html):
        blok = duzlestir(m.group(2))
        if "112" not in blok:
            continue
        for cumle in _ACIL_CUMLE.split(blok):
            if "112" not in cumle:
                continue
            kucuk = kucult(cumle)
            if (_ACIL_ATES.search(kucuk) or _ACIL_VE_BAGI.search(kucuk)
                    or _ACIL_KESIN_BAG.search(kucuk)
                    or _ACIL_KESIN_BAG_TERS.search(kucuk)):
                bulunan.append(cumle.strip()[:110])
    return bulunan


# Uyari kutulari — yonlendirme baslikta, belirti listede olabilir.
_UYARI_KUTU = re.compile(
    r'<div class="uyari">(.*?)</div>', re.S | re.I)
_ILK_UL = re.compile(r"<[uo]l\b", re.I)
_LI = re.compile(r"<li\b[^>]*>(.*?)</li>", re.S | re.I)


def _yonlendirmeli_liler(ham):
    """Kutu basligindaki yonlendirmeyi her liste maddesine MIRAS verir.

    ⚠️ 14. tur bulgu 1. 13. turdaki "birimde 112 varsa cumle cumle bak"
    duzeltmesinin kalan deligi: liste isaretlemesinde noktalama yoksa
    kutunun tamami TEK cumle sayiliyor, icinde 112 gectigi icin eleniyor.
    Tek basina `<li>` ise hayati belirtiyi tasiyor ama yonlendirmeyi
    tasimiyor — cunku yonlendirme BASLIKTA. Ikisi hicbir birimde
    bulusmuyordu:

        <div class="uyari">
          <b>Şunlarda kliniği arayın</b>
          <ul><li>Nefes alma güçlüğü</li></ul>
          <p>Kontrol edilemeyen kanamada 112'yi arayın.</p>
        </div>

    Cozum: baslik klinige yonlendiriyorsa her `<li>` icin
    "baslik + madde" seklinde AYRI bir birim uretilir. Yalnizca `<li>`
    sinirina gecmek yetmezdi (test 556 tam bu iliskiyi koruyor).
    """
    ul = _ILK_UL.search(ham)
    if not ul:
        return []
    oncul = duzlestir(ham[:ul.start()])
    if not _ACIL_KLINIK.search(kucult(oncul)):
        return []                    # baslik klinige yonlendirmiyor
    return [("%s %s" % (oncul, duzlestir(m.group(1)))).strip()
            for m in _LI.finditer(ham)]


def acil_klinige_yonlendirme_hatalari(sayfa_html):
    """Hayati belirtiyi SADECE klinige yonlendiren metinler.

    ⚠️ 12. tur bulgu 4(d): `acil_esik_hatalari` yalnizca 112 GECEN
    cumlelere bakiyor. Bir kutu hayati belirtiyi sayip "hemen arayın"
    diyorsa ve sayfada 112 hic gecmiyorsa o kutu GORUNMEZ kaliyordu.
    yirmi-yas-disi.html tam olarak boyleydi ve dokuz turdur denetimden
    geciyordu.

    ⚠️ 13. tur bulgu 3 — o duzeltmenin ikinci deligi: tarama yalnizca
    `div.uyari` kutularina bakiyordu ve kutuda 112 GECIYORSA kutunun
    TAMAMI muaf sayiliyordu. Yani "…112'yi arayın. Nefes güçlüğünde
    kliniği arayın." diyen bir kutu temiz cikiyordu — muafiyet, tam da
    korunmasi gereken cumleyi ortuyordu. Ayni desen kutu disindaki
    paragraflarda da kullaniliyor.

    Simdi iki duzeyli:
      A. Birimde 112 hic yoksa → birimin tamami degerlendirilir.
      B. Birimde 112 varsa → cumle cumle bakilir; 112 ICERMEYEN bir
         cumle hem klinige yonlendirip hem hayati belirti sayamaz.

    Birim = `div.uyari` kutusu VEYA tek basina bir `p`/`li`. Ikisi de
    gerekli: kutuda yonlendirme cogu zaman BASLIKTA ("Şu durumlarda
    hemen arayın") ve belirtiler alttaki `<li>`lerde durur — yalnizca
    `p`/`li` taransa ikisi hic ayni birimde bulusmaz. Kutu disindaki
    duz paragraflarda ise ayni desen kutusuz kullaniliyor.
    """
    bulunan = []
    birimler = []
    for m in _UYARI_KUTU.finditer(sayfa_html):
        birimler.append(m.group(1))
        birimler += _yonlendirmeli_liler(m.group(1))
    birimler += [m.group(2) for m in _ACIL_BLOK.finditer(sayfa_html)]
    for ham in birimler:
        birim = duzlestir(ham)
        if "112" in birim:
            parcalar = [c for c in _ACIL_CUMLE.split(birim)
                        if "112" not in c]
            etiket = "(cumlede 112 yok)"
        else:
            parcalar = [birim]
            etiket = "(birimde 112 yok)"
        for parca in parcalar:
            kucuk = kucult(parca)
            if not _ACIL_KLINIK.search(kucuk):
                continue                 # klinige yonlendirmiyor
            if not _ACIL_BELIRTI_RE.search(kucuk):
                continue                 # hayati belirti saymiyor
            kayit = "%s … %s" % (parca.strip()[:90], etiket)
            if kayit not in bulunan:     # kutu + icindeki p ayni bulgu
                bulunan.append(kayit)
    return bulunan


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
    gosteriyordu. Onayli cumle listede aynen dursa bile eslesmiyordu.

    ⚠️ 8. tur bulgu 4 — KONU SINIRI EKLENDI.
    `_sonraki_cumleler()` tersleme ararken "uc cumle" sayiyordu, ama HER
    blok etiketi (acilis VE kapanis) bir cumle siniri uretiyor. Yani
    asagidaki metinde gorunur tek bir notr paragraf olmasina ragmen
    ucluk butce tukeniyor ve tersleme KACIYORDU:

        <p>Hiçbir tedavinin sonucu garanti edilemez.</p>
        <p>Bu yalnızca genel bir açıklamadır.</p>
        <p>Tam tersi.</p>

    Sabit sayi yerine artik KONU siniri var: baslik, title, summary, dt
    ve legend yeni bir konu baslatir (U+E000 isareti). Tersleme ayni
    konu icinde araniyor; sonraki BAGIMSIZ basliktaki "Tam tersi" ise
    yanlis alarm uretmiyor."""
    metin = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", ham,
                   flags=re.S | re.I)
    metin = re.sub(r"</?(?:title|h[1-6]|summary|dt|legend)\b[^>]*>",
                   " \ue000 ", metin, flags=re.I)
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
    # gizlilik.html — 4 Agu 2026: yapay zeka kanali KAPATILINCA cumle
    # yeniden yazildi ("bu kanalda" -> "otomatik yanıtlarda") ve muafiyet
    # DUSTU, denetim durdu. Kasitli davranis: muafiyet TAM CUMLE
    # esitligine bagli, boylece cumlenin sonuna kimse ek yazamiyor.
    # Yeni hali de ayni seyi soyluyor — ucret VERILMEDIGINI beyan ediyor,
    # ucret REKLAMI yapmiyor. Listeye o yuzden giriyor.
    "Otomatik yanıtlarda tıbbi değerlendirme, ilaç önerisi ve ücret "
    "bilgisi verilmez",
]

# Cumle siniri. Nokta fazla bolerse zarari yok: parca kisalir, birebir
# esitlik daha ZOR saglanir — yani hata yonu her zaman fail-CLOSED.
# `;` ve `:` BILEREK sinir: "garanti edilemez; iyileşme kişiden kişiye
# değişir" mesru bir devamdir ve engellenmemeli. Tersine cevirmeyi
# noktalama degil `_TERSLEME` yakalar (6. tur b3).
_CUMLE_SINIRI = re.compile("[.!?;:\ue000]+")
# Konu isareti (U+E000) de cumle siniridir — 8. tur b4.

# Onayli cumlenin ARDINDAN gelip onu tersine ceviren ifadeler.
#
# ⚠️ 7. tur bulgu 1 — ILK HALI HEM FAIL-OPEN HEM FAIL-CLOSED'DI.
# Denetci dort ornekle gosterdi, dordu de calistirilarak dogrulandi:
#   KACIRIYORDU : "...garanti edilemez. Öyle değil."      (listede yok)
#                 "...garanti edilemez. Bu bir açıklamadır. Tam tersi."
#                 (araya notr cumle girince _sonraki_cumle goremiyordu)
#   YANLIS ALARM: "...garanti edilemez. Gerçekte iyileşme kişiden
#                 kişiye değişir."   <- MESRU ve yazmamiz gereken cumle
#                 "...garanti edilemez. Aslında bu durum sık görülür."
# Yalin "aslinda/gercekte/aksine" tersleme sayilamaz; bunlar aciklama
# baglaclari. Artik yalnizca TERSLEME YAPAN kaliplar araniyor ve
# arkadan gelen birkac cumle birden taraniyor.
#
# DURUSTCE SINIR: bu bir anlam cozumleyici DEGILDIR. Kasitli ve keyfi
# yeniden yazimlarin tamamini desenle kapatmak mumkun degil; denetci de
# bunu yaziyor. Katmanin amaci DIKKATSIZLIGI yakalamak.
_TERSLEME = re.compile(
    r"\b(?:demiyoruz|demedik|sanmay[ıi]n|tam tersi"
    r"|[şs]aka(?:yd[ıi])?"
    r"|(?:bu|o|[öo]yle)\s+(?:(?:do[ğg]ru|ger[çc]ek)\s+)?de[ğg]il"
    r"|bunu\s+kastetmiyoruz|aksini\s+kastediyoruz"
    r"|(?:asl[ıi]nda|ger[çc]ekte)\s+"
    r"(?:payla[şs]abiliriz|verebiliriz|var(?:d[ıi]r)?|uygulan[ıi]r"
    r"|veriyoruz|yap[ıi]yoruz))\b", re.I)

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
    # 15. tur site bulgusu 2 — UCUNCU kez icerik duzeyinde vaat dili
    # kacti. "Bunların hepsi gece başlatılabilir — ağrı varsa GIDERILIR"
    # cumlesi yayina girdi; bekci "ağrısız/garanti" ariyordu, KESIN
    # KIPTE cozum vaadini gormuyordu. Her agri tek ziyarette tamamen
    # giderilemeyebilir; hasta kesin rahatlama bekleyip yola cikar.
    #
    # ⚠️ Kalip OZNEYE bagli, fiile degil. Sitede mesru kullanimlar var:
    #   "önceliğimiz ağrının giderilmesi"        -> isim hali, vaat degil
    #   "bir kısmı temizlikle giderilebilir"     -> -ebilir, imkan
    #   "çürük ve dişeti sorunları … giderilir"  -> klinik sira, hastanin
    #                                               sikayeti degil
    # Yalnizca HASTANIN sikayetine kesin kiple soz verilmesi yakalanir.
    "sonuc vaadi (kesin kip)":
        r"ağrı(?:n[ıi]z)?\s+(?:varsa\s+)?giderilir"
        r"|(?:ağrınız|şikâyetiniz|şikayetiniz|sorununuz)\s+"
        r"(?:geçer|biter|diner|çözülür)\b",
    "kampanya": r"\bkampanya",
    "indirim": r"\bindirim",
    "ucretsiz": r"\bücretsiz\b",
    "fiyat rakami": r"\d[\d.]*\s*(?:tl|₺)\b",
    "hasta yorumu": r"\bmemnun kald|\byorumları\b",
    "once-sonra": r"önce\s*[-/]\s*sonra",
    "uzman iddiasi": r"\buzman(?:ımız|larımız)\b",
}

# ==========================================================================
# COK DILLI KAPI — hasta turizmi icin dil eklenmesi PLANLANIYOR
# ==========================================================================
# ⚠️ NEDEN SAYFALARDAN ONCE: bugune kadarki butun mevzuat korumasi
# TURKCE desenlerden ibaretti. Ingilizce bir sayfada "painless
# treatment" ya da "guaranteed results" yazsa denetimden GECERDI —
# hicbir desen eslesmezdi. Oysa 12 Kasim 2025 yonetmeligi klinigi
# baglar, sayfanin dili farketmez. Yani ceviri sayfa yazmadan ONCE
# kapinin kurulmasi gerekiyordu; tersi sirada ilk ceviri sayfa
# denetimsiz yayina girerdi.
#
# Diller Medicasimple'in online randevu ekranindakiyle ayni secildi
# (EN/ES/FR/DE/RU) — hasta turizminde en cok kullanilan diller.
#
# Kapsanan kavramlar Turkce tarafla BIREBIR ayni: sonuc vaadi,
# fiyat/ticari dil, hasta yorumu, once-sonra, uzmanlik iddiasi (K38).
#
# ⚠️ Desenler DAR tutuldu. Genis tutmak mevcut 41 Turkce sayfada
# yanlis alarm verir ve denetimi kullanilamaz hale getirir; bu yuzden
# eklendikten sonra tum site uzerinde yanlis-pozitif taramasi yapildi.
YASAKLI_COKDILLI = {
    # --- sonuc vaadi / ustunluk iddiasi -----------------------------
    "en iyi iddiasi (EN)": r"\b(?:the\s+)?best\b|\bnumber\s+one\b",
    "en iyi iddiasi (ES)": r"\bel\s+mejor\b|\bla\s+mejor\b",
    "en iyi iddiasi (FR)": r"\ble\s+meilleur\b|\bla\s+meilleure\b",
    "en iyi iddiasi (DE)": r"\bder\s+beste\b|\bdie\s+beste\b|\bbestes?\b",
    "en iyi iddiasi (RU)": r"\bлучш",

    "garanti (EN)": r"\bguarantee",
    "garanti (ES)": r"\bgarantiz|\bgarantía",
    "garanti (FR)": r"\bgaranti",
    "garanti (DE)": r"\bgarantie|\bgarantiert",
    "garanti (RU)": r"\bгарант",

    "agrisiz iddiasi (EN)": r"\bpainless\b|\bpain[-\s]free\b"
                            r"|\bno\s+pain\b|\bwithout\s+(?:any\s+)?pain\b",
    "agrisiz iddiasi (ES)": r"\bindoloro|\bsin\s+dolor\b",
    "agrisiz iddiasi (FR)": r"\bindolore|\bsans\s+douleur\b",
    "agrisiz iddiasi (DE)": r"\bschmerzfrei|\bschmerzlos"
                            r"|\bohne\s+schmerzen\b",
    "agrisiz iddiasi (RU)": r"\bбезболезнен",

    # --- fiyat / ticari dil (K15) -----------------------------------
    "fiyat (EN)": r"\bprices?\b|\bpricing\b|\bcosts?\b|\bfees?\b"
                  r"|\bdiscount|\bfree\s+(?:consultation|check[-\s]?up"
                  r"|examination|treatment)\b|\binstallment"
                  r"|\bcheap\b|\baffordable\b",
    "fiyat (ES)": r"\bprecios?\b|\bcostos?\b|\bcostes?\b|\bdescuento"
                  r"|\bgratis\b|\bgratuito\b|\bcuotas\b|\bbarato\b"
                  r"|\basequible\b",
    # ⚠️ `\btarifs?\b` YAZILAMAZ: "tarif" yaygin bir TURKCE kelimedir
    # ("çocuk ağrıyı tarif etmekte zorlanır" — sut-disi-curugu.html).
    # Calistirilarak yakalandi. Fransizca fiyat anlami cogulda ya da
    # tanimlikla geliyor; desen ona daraltildi.
    "fiyat (FR)": r"\bprix\b|\btarifs\b|\b(?:le|les|nos|du)\s+tarif\b"
                  r"|\bcoûts?\b|\bréduction"
                  r"|\bgratuit|\bpromotion\b|\bpas\s+cher\b",
    "fiyat (DE)": r"\bpreis|\bkosten\b|\brabatt|\bkostenlos"
                  r"|\bgratis\b|\bratenzahlung|\bgünstig",
    "fiyat (RU)": r"\bцен[аыу]\b|\bстоимост|\bскидк|\bбесплатн"
                  r"|\bрассрочк",
    # ⚠️ 4 Agu 2026, SITE-16 B6 — KAMPANYA yasagi yalniz TURKCE tarafta
    # vardi (bkz. "kampanya" deseni yukarida). Cok dilli kapida
    # karsiligi yoktu: Ispanyolca bir sayfa "campaña", Almanca bir
    # sayfa "Aktion" yazabilir ve tarama TEMIZ derdi.
    #
    # Ayni yonetmelik yabanci dildeki metin icin de gecerli — hatta
    # saglik turizmi hedefleyen sayfalarda denetim daha gorunur.
    # Turkce tarafi koruyup yabanci tarafi acik birakmak, korumanin
    # kendisini anlamsiz kilar.
    #
    # `promotion` (FR) ve `promotions` (EN/ES) zaten fiyat desenlerinde
    # geciyor; burada TEKRAR edilmiyor ki ayni ihlal iki kod altinda
    # bildirilmesin.
    "kampanya (EN)": r"\bcampaigns?\b",
    "kampanya (ES)": r"\bcampañas?\b|\bpromociones?\b",
    "kampanya (FR)": r"\bcampagnes?\b",
    "kampanya (DE)": r"\bkampagne(?:n)?\b|\baktion(?:en)?\b",
    "kampanya (RU)": r"\bкампани(?:я|и|й|ю|ей|ями|ях)\b"
                     r"|\bакци(?:я|и|й|ю|ей|ями|ях)\b",
    "para birimi": r"[€$£]\s?\d|\d\s?(?:eur|usd|gbp)\b",

    # --- hasta yorumu / puan ----------------------------------------
    "hasta yorumu (EN)": r"\btestimonial|\bpatient\s+reviews?\b"
                         r"|\b\d[.,]?\d?\s*[-\s]?stars?\b",
    "hasta yorumu (ES)": r"\btestimonio|\bopiniones\s+de\s+pacientes\b",
    "hasta yorumu (FR)": r"\btémoignage|\bavis\s+(?:de\s+)?patients\b",
    "hasta yorumu (DE)": r"\berfahrungsbericht|\bpatientenbewertung",
    "hasta yorumu (RU)": r"\bотзыв",

    # --- once/sonra --------------------------------------------------
    "once-sonra (EN)": r"\bbefore\s*(?:and|/|-|&)\s*after\b",
    "once-sonra (ES)": r"\bantes\s+y\s+después\b",
    "once-sonra (FR)": r"\bavant\s*(?:et|/|-)\s*après\b",
    "once-sonra (DE)": r"\bvorher\s*(?:und|/|-)\s*nachher\b",
    "once-sonra (RU)": r"\bдо\s+и\s+после\b",

    # --- K38: iki hekim de GENEL DIS HEKIMI, uzman degil -------------
    # ⚠️ 8 Agu 2026, SITE-16 B2 — UC AYRI KACAK VARDI:
    #
    # 1. `\bfachar[zt]` bir KARAKTER SINIFI: "fachar" + (z ya da t).
    #    Yani "facharz"/"fachart" ile eslesiyor, `Facharzt`i ancak
    #    tesadufen yakaliyor, `Fachzahnarzt` / `Fachzahnärzte` hic
    #    gormuyordu — Almanca'da dis hekimi unvani tam da odur.
    # 2. Unvan araniyordu ama UZMANLASMA FIILI aranmiyordu:
    #    "specializes in", "especializado en", "spécialisé dans",
    #    "специализируется на" hepsi geciyordu. K38 acisindan ikisi
    #    ayni iddia: iki hekim de GENEL dis hekimi.
    # 3. DISIL bicimler kaciyordu: `expertos?` "expertas"i,
    #    `experts?` "expertes"i gormuyordu.
    #
    # ⛔ Raporun onerdigi DE yamasi (`spezialis\w*\s+(?:auf|in)`)
    # ALINMADI: kendi test cumlesini bile gecmiyor. Almanca'da yapi
    # fiil-sonludur — "ist AUF Implantate SPEZIALISIERT" — yani edat
    # fiilden ONCE gelir. Gövde aramak hem dogru hem daha basit;
    # "spezialis" ile baslayan her Almanca kelime zaten uzmanlik
    # iddiasidir (Spezialist, spezialisiert, Spezialisierung).
    "uzman iddiasi (EN)": r"\bspecialists?\b|\bexperts?\b"
                          r"|\bspeciali[sz]\w*\s+in\b",
    "uzman iddiasi (ES)": r"\bespecialistas?\b|\bexpert[oa]s?\b"
                          r"|\bespecializ\w*\s+en\b",
    "uzman iddiasi (FR)": r"\bspécialistes?\b|\bexpert(?:e|es|s)?\b"
                          r"|\bspécialis\w*\s+(?:en|dans)\b",
    "uzman iddiasi (DE)": r"\bspezialis|\bfach(?:zahn)?(?:arzt|ärzt)"
                          r"|\bexperten?\b",
    "uzman iddiasi (RU)": r"\bспециалист|\bэксперт"
                          r"|\bспециализ\w*\s+на\b",
}

YASAKLI.update(YASAKLI_COKDILLI)

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
# ⚠️ 2 Agu 2026 — `indirim` ve `kampanya` burada KELIME SINIRSIZ yaziliydi.
# Yukaridaki yorum "YASAKLI'daki ayni dar olumsuzlamayi tasiyor" diyor ama
# `\b` oneki tasinmamisti. Sonuc: "sindirim" kelimesi "indirim" diye
# yakalaniyordu. Agiz kokusu yazisindaki "reflü ve bazı sindirim sistemi
# sorunları" cumlesi bu yuzden K15 hatasi verdi — tibbi bir metin, ticari
# iddia degil. Yanlis alarm denetimi degersizlestirir (3. tur b7'de
# "ekonomik" icin ayni ders alinmisti).
# ⚠️ 7. tur bulgu 6 — TIBBI KELIMELERIN ICINDEN TICARI TERIM CIKIYORDU.
# `indirim` icin kelime siniri eklenmisti ama ayni sorun diger koklerde
# suruyordu. Denetci uc ornek verdi, ucu de calistirilarak dogrulandi:
#     "Çekim sonrası yumuşak doku ödemesi olabilir."  -> K15: ödeme
#         (ÖDEM tibbi bir terim; dis hekimliginde surekli gecer)
#     "Aletler steril paketleme sonrasında saklanır." -> K15: paket
#     "Bu bulgu değerlendirmeye dahildir."            -> K15: dahildir
# Yanlis alarm bekciyi degersizlestirir ve onu devre disi birakmaya
# yonelik baski yaratir — 3. tur b7 ("ekonomik") ve 2 Agu ("sindirim")
# ile ayni sinif.
#
# `dahildir|hariçtir` BAGLAMSIZ oldugu icin tamamen cikarildi: gercek
# ticari kullanimda `fiyat`, `ücret`, `paket`, `TL`, `₺` ya da `KDV`
# zaten ayrica eslesir.
#
# ⚠️ 8. tur bulgu 5 — CEKIM LISTESI YETMIYORDU.
# `\b[öo]deme(?:ler|niz|nizi|nin)?\b` yalnizca sayilan ekleri taniyordu;
# "ödemeyi", "ödemeye", "paketimizden" gibi DOGAL ticari ifadeler
# kaciyordu (ucu de calistirilarak dogrulandi). Turkce sondan eklemeli
# oldugu icin ek listesi yazmak bitmez — artik kok + serbest ek, iki
# ISTISNA disinda:
#
#   `ödemesi` VE CEKIMLERI — hem tibbi (doku ödemi) hem ticari olabilir;
#                belirsiz oldugu icin BILEREK disarida (7. tur b6).
#                ⚠️ 9. tur b3: istisna yalnizca yalin "ödemesi" icindi;
#                "ödemesinin", "ödemesine", "ödemesinde" gibi DOGAL
#                TIBBI cekimler yakalaniyor ve yanlis alarm veriyordu
#                ("Yumuşak doku ödemesinin azalması beklenir").
#   `paketle*` — "paketleme/paketlenmis/paketleyin" teknik terimdir;
#                ama "paketler" (cogul) ticari, o yuzden lem/len/ley
#                ayrimi yapiliyor.
#   `steril paket*` — sterilizasyon baglami. 9. tur b3: "steril paketli
#                alet" ticari sanilıyordu. Istisna YALNIZ onunde
#                dogrudan "steril" varsa gecerli; "tedavi paketlidir"
#                yakalanmaya devam ediyor.
TICARI = re.compile(
    r"[üu]cret|fiyat"
    r"|\b[öo]deme(?!si(?:\b|n(?:i|e|de|den|in)\b))\w*"
    r"|taksit|bedava|bedelsiz"
    r"|\bindirim|\bkampanya"
    r"|masraf|₺|\bTL\b|\bKDV\b"
    r"|(?<!steril )\bpaket(?!lem|len|ley)\w*"
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


def _sonraki_cumleler(metin, konum):
    """`konum`daki cumleden sonra gelen AYNI KONU metnini dondurur.

    ⚠️ 7. tur b1: eskiden yalnizca BIR sonraki cumleye bakiliyordu;
    araya notr bir cumle koymak terslemeyi gizlemeye yetiyordu.
    ⚠️ 8. tur b4: "uc cumle" butcesi de yetmedi — her HTML blok etiketi
    cumle siniri urettigi icin ayri paragraflara yazilan tersleme
    butceyi tuketip kaciyordu. Artik sayi degil KONU siniri esas:
    bir sonraki baslik/summary'e kadar olan metin taraniyor."""
    son = _CUMLE_SINIRI.search(metin, konum)
    if not son:
        return ""
    ilk = son.end()
    konu_sonu = metin.find("\ue000", ilk)
    return metin[ilk:konu_sonu if konu_sonu >= 0 else len(metin)]


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
    return not _TERSLEME.search(_sonraki_cumleler(metin, eslesme.start()))


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
