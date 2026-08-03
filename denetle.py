#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SITE DENETIMI — index.html veya bilgi yazilari degistiginde calistirilir.

    python denetle.py

Neyi kontrol eder:
  1. index.html JSON-LD — Dentist duruyor mu, FAQPage YANLISLIKLA geri
     gelmis mi (sema artik SSS sayfasinda yasiyor)
  2. FAQPage semasindaki soru/cevaplar SSS sayfasindaki metinle AYNI mi
     (Google, semadaki cevabin sayfada gorunur olmasini sart kosuyor)
  3. HTML etiket dengesi
  4. Mevzuat taramasi — 12 Kas 2025 tanitim yonetmeligi (TUM sayfalar)
  5. Icerik hacmi, bolumler ve sekmeli menu
  6. Bilgi yazilari — ayni kurallar onlar icin de
  7. Alt sayfalar (hekimler / SSS / bilgi dizini) ve sitemap

--------------------------------------------------------------------------
1 Agu 2026 — site ayri sekmelere bolundu:
  index.html · hekimlerimiz.html · sik-sorulan-sorular.html ·
  bilgi-yazilari.html + 10 bilgi yazisi

FAQPage semasi index'ten SSS sayfasina TASINDI. Ayni SSS'yi iki URL'de
yayimlamak ikisini de zayiflatiyor; sema, cevabin gorunur oldugu tek
sayfada durur. Bu yuzden index'te FAQPage gorulurse HATA verilir.
Sema elle yazilmaz — `python sss-sema-uret.py` uretir.

--------------------------------------------------------------------------
1. tur Codex denetiminden sonra (1 Agu 2026) yapilan duzeltmeler:

  * METIN DUZLESTIRILEREK aranıyor. Onceki hal satir sonlarini
    dikkate almiyordu; "ağrı\n beklenmez" ifadesi tam da bu yuzden
    kacmisti. Artik tum bosluklar tek boslugua indirgeniyor.
  * HEAD DE TARANIYOR. Onceki hal sadece <body> sonrasina bakiyordu;
    meta description, og:description ve JSON-LD icine yazilan bir
    fiyat/kampanya/ustunluk ifadesi denetimden gecebiliyordu.
  * MUAF_BAGLAM DARALTILDI. Once yasak kelimenin +-90 karakterinde
    herhangi bir olumsuzlama muafiyet sayiliyordu; "Kampanyamiz basladi.
    Saglik reklamlarinda bazi ifadeler yasak." gibi bir metin
    gecebilirdi. Artik yalnizca yasak kelimeyi DOGRUDAN olumsuzlayan
    kalip muaf.
  * FAQ KARSILASTIRMASI TAM METIN. Once ilk 60 karakter karsilastirilip
    sira bazli zip() ile eslesiliyordu; semanin devamina gorunmeyen
    metin eklenebilirdi. Artik soru metnine gore eslesip cevabin
    tamami karsilastiriliyor.
  * ORTUK AGRISIZLIK kaliplari eklendi ("ağrı beklenmez" vb.).
  * PUAN/YORUM taramasi bilgi yazilarinda da calisiyor.
--------------------------------------------------------------------------
"""
import glob
import io
import json
import os
import re
import sys
# sitemap.xml BIZIM urettigimiz, depo icindeki bir dosya — disaridan
# gelen belge ayristirilmiyor. (xml.etree zaten dis varlik cozmez.)
import xml.etree.ElementTree as ET

# Mevzuat desenleri ve metin duzlestirme ORTAK modulde (2. tur bulgusu:
# duzlestir iki yerde kopyalanmisti; biri degisirse digeri sessizce
# ayrisirdi). Desenler icin: mevzuat.py · testi: test-denetle.py
from html.parser import HTMLParser

from mevzuat import (acil_esik_hatalari, acil_klinige_yonlendirme_hatalari,
                     birlestirici_var, cift_kodlanmis, duzlestir, kucult,
                     mevzuat_tara, EMOJI_ISTISNA, YASAKLI, TICARI)

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

hata = 0


def kontrol(ad, kosul, ayrinti=""):
    global hata
    if kosul:
        print("  TAMAM  %-46s %s" % (ad, ayrinti))
    else:
        print("  HATA   %-46s %s" % (ad, ayrinti))
        hata += 1




# ===========================================================================
print("=" * 74)
print("SITE DENETIMI")
print("=" * 74)

YOL = "index.html"
try:
    with open(YOL, encoding="utf-8") as f:
        html = f.read()
except FileNotFoundError:
    print("index.html bulunamadi — betigi site klasorunde calistirin.")
    sys.exit(1)

# Sayfa listeleri — tek kaynak
BILGI = ["gece-dis-agrisi.html", "gece-hafta-sonu-dis-hekimi.html",
         "kirilan-dis-ne-yapmali.html",
         "dis-apsesi.html", "yirmi-yas-disi.html",
         "kanal-tedavisi.html", "implant-sureci.html",
         "diseti-kanamasi.html", "dis-sikma-gece-plagi.html",
         "hamilelikte-dis-sagligi.html", "cocukta-ilk-dis.html",
         "dis-dolgusu.html", "dis-cekimi.html", "protez-kaplama.html",
         "dis-tasi-temizligi.html", "dis-cekimi-sonrasi-sislik.html",
         "dis-hekimi-korkusu.html", "agiz-kokusu.html",
         "dis-hassasiyeti.html", "curuk-nasil-olusur.html",
         "florur-nedir.html", "agiz-yarasi-aft.html",
         "sigara-ve-agiz-sagligi.html", "dis-ipi-kullanimi.html",
         "dis-beyazlatma-gercekleri.html",
         "dis-teli-ortodonti.html", "seffaf-plak.html",
         "dis-rontgeni.html", "diseti-cekilmesi.html",
         "agiz-kurulugu.html", "diyabet-ve-agiz-sagligi.html",
         "kan-sulandirici-dis-tedavisi.html",
         "sut-disi-curugu.html"]
ALT_SAYFA = ["hekimlerimiz.html", "sik-sorulan-sorular.html",
             "bilgi-yazilari.html", "ulasim-ve-hizmet-bolgesi.html",
             "tedaviler.html", "iletisim.html"]
SSS_SAYFA = "sik-sorulan-sorular.html"

# ==========================================================================
# INGILIZCE BOLUM — hasta turizmi (COKDILLI-TASARIM.md)
# ==========================================================================
# ⚠️ Sayfa YAZILMADAN once denetim yolu kuruldu. Tersi sirada ilk
# Ingilizce sayfa DENETIMSIZ yayina girerdi: `denetlenmeyen HTML yok`
# kapisi alt klasordeki her HTML'de denetimi DURDURUYOR (bu kapi bir
# dis denetim bulgusuydu; icinde "garanti", "5000 TL", "%20 indirim"
# gecen bir alt klasor sayfasi denetimden gecmisti). O kapi
# GEVSETILMIYOR — Ingilizce sayfalar listeye AÇIKÇA ekleniyor.
#
# Metinler 3 Agu'da hekim onayindan gecti. Sekiz sayfa:
EN_SAYFA = ["en/index.html",
            "en/dental-implants.html",
            "en/crowns-and-veneers.html",
            "en/root-canal-and-general-dentistry.html",
            "en/our-dentists.html",
            "en/getting-here.html",
            "en/contact.html"]

# ============================================================================
# SAGLIK TURIZMI KAPISI — 3 Agu 2026
# ============================================================================
# ⚠️ Yabanci dilde "tedavi icin Istanbul'a gelin / kac gun kalirsiniz"
# icerigi yayimlamak, faaliyeti ULUSLARARASI SAGLIK TURIZMI kapsamina
# sokuyor. Bunun icin Uluslararasi Saglik Turizmi Yetki Belgesi
# ZORUNLU — secmeli degil. Muayenehane ve poliklinikler AYNI sartlara
# tabi; "biz kucuguz" muafiyeti yok. Sartlar arasinda saglik turizmi
# birimi, hizmet dilini B2 seviyesinde BELGELI bilen personel ve
# yabanci hastalar icin onam/epikriz duzenlemesi var.
#
# Klinikte belge HENUZ YOK (3 Agu 2026; basvuru yapilacak).
#
# ⚠️ BU KONU 25 TUR KOD DENETIMININ HIC SORMADIGI BIR SORUYDU. Kodda
# hata yoktu, tasarimda da yoktu — eksik olan bir BELGEYDI. On-olum
# turu ("bu is 6 ay sonra coktu, nasil coktu?") yakaladi. Sayfalar
# yayimlanmak uzereydi.
#
# Turizm sayfalari SILINMEDI, `belge-bekliyor/` klasorunde duruyor ve
# siteyi-yukle.py o klasoru atliyor. Belge gelince BELGE_VAR = True
# yapilip sayfalar geri alinir.
BELGE_VAR = False

# Bu kaliplar YAYIMLANAN yabanci dil sayfalarinda ARANMAZ olmali.
# Bilgi vermek serbest; "tedavi icin buraya SEYAHAT ET" demek degil.
TURIZM_DILI = {
    "seyahat cagrisi (EN)": r"\btravel(?:l)?ing\s+(?:to|from)\b"
                            r"|\bif\s+you\s+are\s+travel"
                            r"|\byour\s+stay\b|\blonger\s+stay\b"
                            r"|\btwo\s+trips\b|\bbefore\s+you\s+travel\b"
                            r"|\bhow\s+many\s+days\s+you\b",
    "seyahat cagrisi (ES)": r"\bsi\s+viaja\b|\bviajar\s+a\s+Estambul\b"
                            r"|\bsu\s+estancia\b|\bcu[aá]ntos\s+d[ií]as\b",
    "seyahat cagrisi (FR)": r"\bsi\s+vous\s+voyagez\b|\bvotre\s+s[ée]jour\b"
                            r"|\bcombien\s+de\s+jours\b",
    "seyahat cagrisi (DE)": r"\bwenn\s+Sie\s+(?:an)?reisen\b"
                            r"|\bIhr\s+Aufenthalt\b|\bwie\s+viele\s+Tage\b",
    "seyahat cagrisi (RU)": r"\bесли\s+вы\s+приезжаете\b|\bваше\s+пребывание\b",
}

# Ingilizce sorumluluk notu — Turkce karsiligiyla AYNI islevde.
# Turkce sayfalarda "hekim muayenesinin yerine gecmez" araniyor;
# Ingilizce sayfada o cumle bulunmayacagi icin ayri desen sart.
EN_SORUMLULUK = "does not replace an examination"

# --- Ispanyolca (3 Agu 2026) ---------------------------------------
ES_SAYFA = ["es/index.html",
            "es/implantes-dentales.html",
            "es/coronas-y-carillas.html",
            "es/endodoncia-y-odontologia-general.html",
            "es/nuestros-odontologos.html",
            "es/como-llegar.html",
            "es/contacto.html"]
ES_SORUMLULUK = "no sustituye la exploración"

# --- Fransizca (3 Agu 2026) ----------------------------------------
FR_SAYFA = ["fr/index.html",
            "fr/implants-dentaires.html",
            "fr/couronnes-et-facettes.html",
            "fr/traitement-de-racine-et-dentisterie-generale.html",
            "fr/nos-dentistes.html",
            "fr/comment-venir.html",
            "fr/contact.html"]
# ⚠️ DUZ kesme isareti (') — sayfalarda oyle yaziyor. Kivrik (’)
# yazilmisti ve desen HICBIR sayfada tutmadi; denetim "sorumluluk
# notu yok" dedi. Ceviri sayfalarinda en kolay atlanan ayrinti.
FR_SORUMLULUK = "ne remplace pas l'examen"

# --- Almanca (3 Agu 2026) ------------------------------------------
DE_SAYFA = ["de/index.html",
            "de/zahnimplantate.html",
            "de/kronen-und-veneers.html",
            "de/wurzelbehandlung-und-allgemeine-zahnmedizin.html",
            "de/unsere-zahnaerzte.html",
            "de/anfahrt.html",
            "de/kontakt.html"]
# ⚠️ Desen TEK SATIR olmali. HTML'de cumle satir sonu ve girintiyle
# bolunmus duruyor; "ersetzt keine" ile "zahnärztliche Untersuchung"
# arasinda satir sonu + bosluklar var. Ikisini birlikte aramak
# HICBIR sayfada tutmazdi (Fransizcada ayni tuzaga kesme isaretiyle
# duselmisti). Ayirt edici TEK parca yeter.
DE_SORUMLULUK = "zahnärztliche Untersuchung"

# --- Rusca (3 Agu 2026) --------------------------------------------
RU_SAYFA = ["ru/index.html",
            "ru/zubnye-implanty.html",
            "ru/koronki-i-viniry.html",
            "ru/lechenie-kanalov-i-obshchaya-stomatologiya.html",
            "ru/nashi-stomatologi.html",
            "ru/kak-dobratsya.html",
            "ru/kontakty.html"]
# Tek parca, satira bolunmeyen kalip (bkz. DE notu).
RU_SORUMLULUK = "осмотр стоматолога"

# ⚠️ AYNI SAYFANIN dillerdeki karsiliklari. Dosya adlari CEVIRILI
# oldugu icin (dental-implants / implantes-dentales) ad esleme
# CALISMAZ; ilk surum oyle yazilmisti ve `hreflang` eksigini
# yakalamiyordu: es/ sayfalari eklendiginde en/ sayfalarinin
# `hreflang="es"` vermesi gerektigini GORMUYORDU. Tek yonlu hreflang'i
# Google yok sayar, yani cok dilli kurulum sessizce yarim kalirdi.
SAYFA_ESI = [
    {"tr": "index.html",
     "en": "en/index.html",
     "es": "es/index.html",
     "fr": "fr/index.html",
     "de": "de/index.html",
     "ru": "ru/index.html"},
    {"tr": "implant-sureci.html",
     "en": "en/dental-implants.html",
     "es": "es/implantes-dentales.html",
     "fr": "fr/implants-dentaires.html",
     "de": "de/zahnimplantate.html",
     "ru": "ru/zubnye-implanty.html"},
    {"tr": "protez-kaplama.html",
     "en": "en/crowns-and-veneers.html",
     "es": "es/coronas-y-carillas.html",
     "fr": "fr/couronnes-et-facettes.html",
     "de": "de/kronen-und-veneers.html",
     "ru": "ru/koronki-i-viniry.html"},
    {"tr": "kanal-tedavisi.html",
     "en": "en/root-canal-and-general-dentistry.html",
     "es": "es/endodoncia-y-odontologia-general.html",
     "fr": "fr/traitement-de-racine-et-dentisterie-generale.html",
     "de": "de/wurzelbehandlung-und-allgemeine-zahnmedizin.html",
     "ru": "ru/lechenie-kanalov-i-obshchaya-stomatologiya.html"},
    {"tr": "hekimlerimiz.html",
     "en": "en/our-dentists.html",
     "es": "es/nuestros-odontologos.html",
     "fr": "fr/nos-dentistes.html",
     "de": "de/unsere-zahnaerzte.html",
     "ru": "ru/nashi-stomatologi.html"},
    {"tr": "ulasim-ve-hizmet-bolgesi.html",
     "en": "en/getting-here.html",
     "es": "es/como-llegar.html",
     "fr": "fr/comment-venir.html",
     "de": "de/anfahrt.html",
     "ru": "ru/kak-dobratsya.html"},
    {"tr": "iletisim.html",
     "en": "en/contact.html",
     "es": "es/contacto.html",
     "fr": "fr/contact.html",
     "de": "de/kontakt.html",
     "ru": "ru/kontakty.html"},
]

# ⚠️ Diller TEK TEK degil TABLODAN denetleniyor. Eskiden yalnizca
# Ingilizce icin yazilmis bir blok vardi; her yeni dil o blogun
# kopyalanmasini gerektirirdi ve dordunculde biri mutlaka atlanirdi.
# Yeni dil eklemek artik BURAYA IKI SATIR yazmak demek.
DILLER = {
    "en": {"ad": "Ingilizce", "sayfalar": EN_SAYFA,
           "sorumluluk": EN_SORUMLULUK},
    "es": {"ad": "Ispanyolca", "sayfalar": ES_SAYFA,
           "sorumluluk": ES_SORUMLULUK},
    "fr": {"ad": "Fransizca", "sayfalar": FR_SAYFA,
           "sorumluluk": FR_SORUMLULUK},
    "de": {"ad": "Almanca", "sayfalar": DE_SAYFA,
           "sorumluluk": DE_SORUMLULUK},
    "ru": {"ad": "Rusca", "sayfalar": RU_SAYFA,
           "sorumluluk": RU_SORUMLULUK},
}
COKDILLI_SAYFA = [y for d in DILLER.values() for y in d["sayfalar"]]


def _yayimda_diller():
    """siteyi-yukle.py'nin YAYIMDA_DILLER kumesi — TEK KAYNAK.

    ⚠️ Burada ayri bir liste TUTULMAZ. Iki yerde tutulan her sey
    ayrisiyor; bu projede uc kez oldu (dil adlari sozlugu, ana sayfa
    listesi, sorumluluk desenleri). Okunamazsa BOS kume donulur —
    yani "hicbiri yayimda" — cunku yanlis yayimlamak, fazladan
    denetim hatasi vermekten pahalidir.
    """
    y = os.path.join(os.path.dirname(os.path.abspath(".")),
                     "hasta-mesajlari", "siteyi-yukle.py")
    if not os.path.exists(y):
        y = os.path.join("..", "hasta-mesajlari", "siteyi-yukle.py")
    try:
        k = io.open(y, encoding="utf-8").read()
        m = re.search(r"^YAYIMDA_DILLER = (set\(\)|\{[^}]*\})", k, re.M)
        if not m:
            return set()
        ns = {}
        exec(compile("D = " + m.group(1), "yd", "exec"), ns)
        return set(ns["D"])
    except Exception:
        return set()

# Sekmeli menude bulunmasi gereken baglantilar.
# ⚠️ 2 Agu 2026: "Tedaviler" ve "İletişim" eskiden `/#tedaviler` ve
# `/#iletisim` CAPALARIYDI. Bir bilgi yazisindayken tiklaninca once ana
# sayfaya gidiyor, sonra asagi kaydiriyordu — digger sekmeler (hekimler,
# SSS, ulasim) ayri sayfa oldugu icin tutarsizdi ve hekim bunu kullanim
# zorlugu olarak bildirdi. Ikisi de ayri sayfaya tasindi.
MENU_BAGLARI = ["hekimlerimiz.html", "bilgi-yazilari.html",
                SSS_SAYFA, "ulasim-ve-hizmet-bolgesi.html",
                "tedaviler.html", "iletisim.html"]

# --- 1. JSON-LD ---
print("\n--- 1/7  index.html JSON-LD yapisal veri ---")
bloklar = re.findall(
    r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
kontrol("bir JSON-LD blogu var", len(bloklar) == 1, "%d blok" % len(bloklar))

tipler, cozulen = [], []
for i, b in enumerate(bloklar):
    try:
        veri = json.loads(b)
        cozulen.append(veri)
        tipler.append(veri.get("@type"))
        kontrol("blok %d gecerli JSON" % (i + 1), True, veri.get("@type"))
    except json.JSONDecodeError as e:
        kontrol("blok %d gecerli JSON" % (i + 1), False, str(e))

kontrol("Dentist semasi var", "Dentist" in tipler)
# FAQPage index'te OLMAMALI — ayni SSS iki URL'de yayimlanirsa ikisi de
# zayiflar. Sema yalnizca sik-sorulan-sorular.html'de durur.
kontrol("index'te FAQPage YOK (SSS sayfasinda olmali)",
        "FAQPage" not in tipler,
        "geri gelmis!" if "FAQPage" in tipler else "sema SSS sayfasinda")

# --- 2. SSS: sema <-> sayfa (TAM METIN, soru bazli eslesme) ---
print("\n--- 2/7  SSS sayfasi: sema ile metin AYNI mi ---")
if not os.path.exists(SSS_SAYFA):
    kontrol(SSS_SAYFA, False, "dosya yok")
else:
    with open(SSS_SAYFA, encoding="utf-8") as f:
        sss_html = f.read()
    sss_bloklar = re.findall(
        r'<script type="application/ld\+json">(.*?)</script>', sss_html, re.S)
    faq = None
    for b in sss_bloklar:
        try:
            v = json.loads(b)
        except json.JSONDecodeError as e:
            kontrol("SSS sayfasi JSON-LD gecerli", False, str(e))
            continue
        if v.get("@type") == "FAQPage":
            faq = v
    kontrol("SSS sayfasinda FAQPage semasi var", faq is not None)

    if faq:
        sorular = faq["mainEntity"]
        sayfa = {}
        for m in re.finditer(
                r'<details class="sss-ogesi">\s*<summary>(.*?)</summary>\s*'
                r'<div class="sss-cevap">(.*?)</div>\s*</details>',
                sss_html, re.S):
            sayfa[duzlestir(m.group(1))] = duzlestir(m.group(2))

        print("     sema %d soru  ·  sayfa %d soru"
              % (len(sorular), len(sayfa)))
        kontrol("soru sayilari esit", len(sorular) == len(sayfa))
        kontrol("en az 15 soru var", len(sayfa) >= 15, "%d soru" % len(sayfa))

        eksik, uyusmaz = [], []
        for q in sorular:
            ad = duzlestir(q["name"])
            if ad not in sayfa:
                eksik.append(ad[:40])
                continue
            # TAM metin karsilastirmasi — ilk 60 karakter yetmiyordu
            if sayfa[ad] != duzlestir(q["acceptedAnswer"]["text"]):
                uyusmaz.append(ad[:40])
        kontrol("her sema sorusu sayfada var", not eksik,
                ("eksik: %s" % eksik[:2]) if eksik else "")
        kontrol("cevaplar TAM METIN ayni", not uyusmaz,
                ("uyusmaz: %s — 'python sss-sema-uret.py' calistirin"
                 % uyusmaz[:2]) if uyusmaz else "")

# --- 3. Etiket dengesi ---
print("\n--- 3/7  HTML etiket dengesi ---")
for etiket in ("details", "summary", "section", "div", "main"):
    ac = len(re.findall(r"<%s[\s>]" % etiket, html))
    kapa = len(re.findall(r"</%s>" % etiket, html))
    kontrol("<%s> dengeli" % etiket, ac == kapa,
            "%d ac / %d kapa" % (ac, kapa))

# --- 4. Mevzuat (TUM DOSYA, head dahil) ---
print("\n--- 4/7  Mevzuat taramasi (12 Kas 2025 yonetmeligi) ---")
sorunlar = mevzuat_tara(html, "index.html")
kontrol("index.html mevzuat taramasi", not sorunlar,
        ("; ".join(sorunlar[:3])) if sorunlar else "head + JSON-LD dahil")

govde = html[html.find("<body"):]
emoji = [e for e in re.findall(r"[\U0001F300-\U0001FAFF]", govde)
         if e not in EMOJI_ISTISNA]
kontrol("govdede emoji yok (widget haric)", not emoji,
        ("BULUNDU: %s" % " ".join(sorted(set(emoji)))) if emoji else "")

# --- 5. Icerik ---
print("\n--- 5/7  Icerik hacmi, bolumler ve menu ---")
metin = duzlestir(govde)
kelime = len([k for k in metin.split(" ") if len(k) > 1])
# ⚠️ 2 Agu 2026 — TEDAVILER VE ILETISIM AYRI SAYFAYA TASINDI.
# Menude capa (`/#tedaviler`) olduklari icin bir bilgi yazisindan
# tiklaninca once ana sayfaya gidip sonra kaydiriyorlardi; diger
# sekmeler ayri sayfa oldugu icin tutarsizdi. Icerik KAYBOLMADI,
# tasindi — bu yuzden kontroller de tasindi:
#   * tedavi ayrintilarinin (7 details) sayimi -> tedaviler.html
#   * ana sayfa kelime esigi 1200 -> 800 (tedavi metni artik orada degil)
# Ana sayfa hala her bolume KOPRU kurmak zorunda; capa yerine sayfa
# baglantisi araniyor.
kontrol("gorunur metin 800+ kelime", kelime > 800, "%d kelime" % kelime)
for ad, im in (("SSS", 'id="sss"'), ("hekimler", 'id="hekimler"'),
               ("bilgi yazilari", 'id="bilgi"'), ("ulasim", 'id="ulasim"')):
    kontrol("%s bolumu var" % ad, im in html)
for ad, bag in (("tedaviler", "tedaviler.html"),
                ("iletisim", "iletisim.html")):
    kontrol("ana sayfa %s sayfasina baglaniyor" % ad, bag in html)

# Tedavi ayrintilari artik kendi sayfasinda.
# ⚠️ Ilk tasima denemesi BOZUK CIKTI: blok `tedavi-bolum`, `tedavi-fon`,
# `dizin`, `ayrinti`, `kunye` siniflarini kullaniyordu ve bunlarin
# tamami index.html'in GOMULU <style> blogunda tanimliydi — bilgi.css'te
# yok. Sayfa stilsiz kaldi, dev fon gorseli ekrani kapladi ve yatay
# tasma olustu. Canliya cikmisti; geri alindi.
# Cozum CSS kopyalamak degil, icerigi alt sayfalarda ZATEN calisan
# yapiya tasimak oldu: `details.sss-ogesi` akordeonu (SSS sayfasiyla
# ayni). Bu yuzden desen `ayrinti` degil `sss-ogesi`.
if os.path.exists("tedaviler.html"):
    with open("tedaviler.html", encoding="utf-8") as f:
        _ted = f.read()
    _adet = len(re.findall(r'<details class="sss-ogesi">', _ted))
    kontrol("7 tedavi alaninda acilir ayrinti (tedaviler.html)",
            _adet == 7, "%d adet" % _adet)
else:
    kontrol("tedaviler.html var", False, "dosya yok")
kontrol("canonical etiketi var", 'rel="canonical"' in html)
kontrol("meta description var", 'name="description"' in html)
kontrol("Search Console dogrulamasi duruyor",
        "google-site-verification" in html)

# Menu: HER sayfada olmali ve ayni baglantilari icermeli. Bir sayfada
# menu unutulursa ziyaretci o sayfada kapana kisilir.
print()
for ad in ["index.html"] + ALT_SAYFA + BILGI:
    if not os.path.exists(ad):
        continue
    with open(ad, encoding="utf-8") as f:
        s_ = f.read()
    eksik_bag = [b for b in MENU_BAGLARI if b not in s_]
    kontrol("menu · %s" % ad,
            'class="menu"' in s_ and not eksik_bag,
            ("eksik: %s" % eksik_bag[:3]) if eksik_bag
            else ("menu yok" if 'class="menu"' not in s_ else ""))

# --- Metin kodlamasi saglam mi? ---
# 1 Agu 2026: index.html'deki BUTUN Turkce karakterler cift kodlandi ve
# 20 dakika oyle yayinda kaldi. Sebep PowerShell 5.1'in klasik tuzagi:
# `Get-Content` -Encoding verilmeyince dosyayi sistem ANSI kod
# sayfasiyla (cp1254) okur, `Set-Content -Encoding utf8` de o bozuk
# metni UTF-8 yazar. "Diş" -> "DiÅŸ", basa da BOM eklenir.
#
# Hicbir denetim bunu yakalamadi: dosya gecerli UTF-8 kaliyor, kelime
# sayisi tutuyor, yasak kelime taramasi zaten bozuk metinde eslesmiyor.
# Tarayicida ise sayfanin tamami okunamaz hale geliyor.
#
# Tespit: cift kodlanmis metin cp1254'e geri cevrilip UTF-8 olarak
# COZULEBILIR. Saglam Turkce metin cozulemez ("ş" -> 0xFE, gecersiz
# UTF-8 baslangici). Test bu asimetriye dayaniyor.
#
# ⚠️ 9. tur bulgu 4 — IKINCI BIR BOZUKLUK SINIFI EKLENDI.
# iletisim.html'de baslik "Çalişma saatleri̇." diye yayina cikti:
# sayfayi kuran betikte `"ÇALIŞMA SAATLERİ".capitalize()` kullanilmisti
# ve Python'un capitalize()'i Turkce bilmiyor —
#     "I" -> "i" (olmasi gereken "ı"),  "İ" -> "i" + U+0307
# Ekranda neredeyse dogru gorunuyordu; cift kodlama kontrolu de bunu
# GORMEDI, cunku farkli bir hasar. Turkce metinde birlestirici isarete
# gerek yok (harfler precomposed), o yuzden tolerans sifir.
print()
bozuk_kodlama, bomlu, birlestirici = [], [], []
for ad in ["index.html"] + ALT_SAYFA + BILGI + ["gizlilik.html"]:
    if not os.path.exists(ad):
        continue
    with open(ad, "rb") as f:
        ham = f.read()
    if ham.startswith(b"\xef\xbb\xbf"):
        bomlu.append(ad)
    try:
        coz = ham.decode("utf-8")
        if cift_kodlanmis(coz):
            bozuk_kodlama.append(ad)
        bul = birlestirici_var(coz)
        if bul:
            birlestirici.append("%s (%d adet, ilki U+%04X)"
                                % (ad, len(bul), ord(bul[0][1])))
    except UnicodeDecodeError:
        bozuk_kodlama.append(ad + " (UTF-8 degil)")

kontrol("hicbir sayfa cift kodlanmamis", not bozuk_kodlama,
        ("BOZUK: %s" % bozuk_kodlama[:3]) if bozuk_kodlama
        else "%d sayfa" % (len(BILGI) + len(ALT_SAYFA) + 2))
kontrol("hicbir sayfada BOM yok", not bomlu,
        ("BOM'lu: %s" % bomlu[:3]) if bomlu else "")
kontrol("hicbir sayfada birlestirici karakter yok", not birlestirici,
        ("BOZUK: %s" % birlestirici[:2]) if birlestirici
        else "%d sayfa" % (len(BILGI) + len(ALT_SAYFA) + 2))

# 112 esigi TUM sayfalarda aranir — bilgi yazilarinda ayrica sayfa
# bazinda raporlaniyor ama ana sayfa, iletisim ve SSS de 112 yaziyor.
# Kuralin gerekcesi `acil_esik_hatalari` yaninda.
_acil_karisik, _acil_klinik = [], []
for ad in ["index.html"] + ALT_SAYFA + BILGI + ["gizlilik.html"]:
    if not os.path.exists(ad):
        continue
    with open(ad, encoding="utf-8") as f:
        _s = f.read()
    for c in acil_esik_hatalari(_s):
        _acil_karisik.append("%s: %s" % (ad, c))
    for c in acil_klinige_yonlendirme_hatalari(_s):
        _acil_klinik.append("%s: %s" % (ad, c))
kontrol("112 esigi atese/ikinci belirtiye baglanmamis", not _acil_karisik,
        _acil_karisik[0] if _acil_karisik
        else "%d sayfa" % (len(BILGI) + len(ALT_SAYFA) + 2))
kontrol("hayati belirti yalniz klinige yonlendirilmiyor", not _acil_klinik,
        _acil_klinik[0] if _acil_klinik
        else "%d sayfa · uyari kutulari" % (len(BILGI) + len(ALT_SAYFA) + 2))

# --- Sohbet metinleri HTML'de mi? (5. tur bulgu 4) ---
# mevzuat.py <script> bloklarini bilerek atlar — kod taranmaz. Ama sohbet
# kutusunun hastaya GOSTERDIGI metinler kod degil icerik. JavaScript
# dizgisinde durduklari surece ekranda gorunur, denetimden gecerlerdi.
print()
# HTML yorumlari kod DEGILDIR: bir aciklama satirinda gecen ornek
# cagri, tanimsiz metin sanilip yanlis alarm veriyordu.
kod_html = re.sub(r"<!--.*?-->", " ", html, flags=re.S)
sablon = re.search(r'<template id="sohbet-metin">(.*?)</template>',
                   kod_html, re.S)
kontrol("sohbet metin sablonu var", sablon is not None)
if sablon:
    tanimli = set(re.findall(r'data-ad="([^"]+)"', sablon.group(1)))
    cagrilan = set(re.findall(r'\bmet\("([^"]+)"\)', kod_html))
    kontrol("her met() cagrisinin karsiligi var", cagrilan <= tanimli,
            ("TANIMSIZ: %s" % sorted(cagrilan - tanimli))
            if cagrilan - tanimli else "%d metin" % len(cagrilan))
    kontrol("sablonda olu metin yok", tanimli <= cagrilan,
            ("kullanilmiyor: %s" % sorted(tanimli - cagrilan))
            if tanimli - cagrilan else "")

# balon()/dugme() ilk argumani DIZGE SABITI olmamali. Olursa metin
# yeniden <script> icine kacar ve bekci onu goremez.
kodda = re.findall(r'\b(balon|dugme)\s*\(\s*["\']', kod_html)
kontrol("hastaya gosterilen metin kodda DIZGE degil", not kodda,
        ("kodda dizge: %s" % sorted(set(kodda))) if kodda
        else "hepsi <template>'ten okunuyor")

# --- 6. Bilgi yazilari ---
print("\n--- 6/7  bilgi yazilari (%d sayfa) ---" % len(BILGI))

diskteki = sorted(os.path.basename(y) for y in glob.glob("*.html")
                  if os.path.basename(y) not in ("index.html", "gizlilik.html"))
kontrol("listedeki sayfalar diskle ayni",
        diskteki == sorted(BILGI + ALT_SAYFA),
        ("fark: %s" % sorted(set(diskteki) ^ set(BILGI + ALT_SAYFA)))
        if diskteki != sorted(BILGI + ALT_SAYFA) else
        "%d yazi + %d alt sayfa" % (len(BILGI), len(ALT_SAYFA)))


# ⚠️ 6. tur bulgu 4 — ALT KLASORDEKI HTML BUTUN DENETIMI ATLIYORDU.
# Yukaridaki kontrol yalnizca KOK dizine bakiyor (`glob("*.html")`),
# oysa `siteyi-yukle.py` dosyalari `os.walk` ile topluyor ve her .html
# dosyasini yayimlanabilir sayiyor. Yani `gecici/yeni.html` mevzuat
# taramasindan, sorumluluk notu kontrolunden ve sitemap beklentisinden
# HIC GECMEDEN yayina gidebiliyordu.
#
# Denetci bunu isaret etti, sinandi ve DOGRULANDI: icinde "en iyi",
# "garanti", "5000 TL" ve "%20 indirim" gecen bir alt klasor sayfasi
# olusturuldu, denetim "HEPSI GECTI" dedi ve sifir donduruldu.
#
# Klasor istisnalari yukleyicideki liste ile AYNI olmali; ayrisirsa
# ayni acik geri gelir.
# belge-bekliyor/ — saglik turizmi belgesi gelene kadar bekleyen
# sayfalar. siteyi-yukle.py da ayni klasoru atliyor; ikisi
# ayrisirsa sayfa yayina cikar ve denetim gormez.
YUKLEYICI_DISI = (".git", "arsiv", "belge-bekliyor")


def _tum_html():
    """Alt klasorler DAHIL butun HTML dosyalari (yukleyiciyle ayni kapsam)."""
    bulunan = []
    for kok, klasorler, dosyalar in os.walk("."):
        klasorler[:] = [k for k in klasorler if k not in YUKLEYICI_DISI]
        for ad in dosyalar:
            if ad.lower().endswith(".html"):
                yol = os.path.relpath(os.path.join(kok, ad), ".")
                bulunan.append(yol.replace(os.sep, "/"))
    return sorted(bulunan)


_tum = _tum_html()
_beklenen = sorted(["index.html", "gizlilik.html"] + BILGI + ALT_SAYFA
                   + COKDILLI_SAYFA)
_fazla = [y for y in _tum if y not in _beklenen]
kontrol("denetlenmeyen HTML yok (alt klasorler dahil)",
        _tum == _beklenen,
        ("BEKLENMEYEN: %s" % _fazla) if _fazla
        else ("eksik: %s" % sorted(set(_beklenen) - set(_tum)))
        if _tum != _beklenen else "%d sayfa" % len(_tum))

for ad in BILGI:
    if not os.path.exists(ad):
        kontrol(ad, False, "dosya yok")
        continue
    with open(ad, encoding="utf-8") as f:
        s = f.read()
    sorun = []

    for c in acil_esik_hatalari(s):
        sorun.append("112 ile ates ayni cumlede: %s" % c)

    for blok in re.findall(
            r'<script type="application/ld\+json">(.*?)</script>', s, re.S):
        try:
            json.loads(blok)
        except json.JSONDecodeError as e:
            sorun.append("JSON-LD bozuk (%s)" % e)

    for etiket in ("div", "section", "article", "ul", "ol", "li", "p"):
        ac = len(re.findall(r"<%s[\s>]" % etiket, s))
        kapa = len(re.findall(r"</%s>" % etiket, s))
        if ac != kapa:
            sorun.append("<%s> dengesiz (%d/%d)" % (etiket, ac, kapa))

    sorun += mevzuat_tara(s, ad)

    if "canonical" not in s:
        sorun.append("canonical yok")
    if 'name="description"' not in s:
        sorun.append("description yok")
    if 'href="bilgi.css"' not in s:
        sorun.append("bilgi.css bagli degil")
    duz = duzlestir(s[s.find("<body"):])
    if "hekim muayenesinin yerine geçmez" not in duz.lower():
        sorun.append("sorumluluk notu yok")

    kelimeler = len([k for k in duz.split(" ") if len(k) > 1])
    if kelimeler < 500:
        sorun.append("cok kisa (%d kelime)" % kelimeler)

    kontrol(ad, not sorun,
            ("; ".join(sorun[:2])) if sorun else "%d kelime" % kelimeler)

kontrol("bilgi.css var", os.path.exists("bilgi.css"))

# --- Yazi tipleri YEREL mi? (Codex 1. tur bulgu 7'nin kalici cozumu) ---
# Site hicbir ucuncu taraf sunucusuna istek atmamali: hastanin IP'si
# ve hangi sayfayi actigi disari gitmesin. Bir sayfaya yanlislikla
# Google Fonts baglantisi geri eklenirse burada yakalanir.
# ⚠️ 3. tur bulgu 12: bu kontrol yalnizca .css ve font uzantilarina
# bakiyordu. Oysa gizlilik metnimiz "sayfa acildiginda hicbir ucuncu
# taraf sunucusuna istek gonderilmez" diye SOZ VERIYOR. Geri eklenecek
# bir <script src>, <img src>, <iframe>, preload ya da CSS @import bu
# sozu bozar ve denetimden gecerdi. Artik SAYFA YUKLENIRKEN istek
# olusturan butun kaynak turleri taraniyor.
#
# Onemli ayrim: kullanicinin TIKLAMASIYLA acilan baglantilar
# (wa.me, tel:, maps.app.goo.gl) kaynak yuklemesi DEGILDIR — onlar
# taranmaz, aksi halde her WhatsApp dugmesi hata verirdi.
print()

_YERLI = re.compile(r"^(?:https?:)?//(?:www\.)?ymdisklinigi\.com", re.I)


def _dis_mi(deger):
    """Sayfa yuklenirken istek olusturacak bir DIS adres mi?"""
    d = (deger or "").strip()
    if not d or d.startswith(("data:", "#", "mailto:", "tel:")):
        return False
    if d.startswith(("//", "http://", "https://")):
        return not _YERLI.match(d)
    return False            # bagil yol = kendi sunucumuz


class _KaynakToplayici(HTMLParser):
    """Sayfa acilirken ag istegi doguran ogeleri toplar."""
    # etiket -> bakilacak oznitelikler
    HEDEF = {"script": ("src",), "img": ("src", "srcset"),
             "source": ("src", "srcset"), "iframe": ("src",),
             "video": ("src", "poster"), "audio": ("src",),
             "embed": ("src",), "object": ("data",),
             "track": ("src",), "input": ("src",),
             # ⚠️ 4. tur b5: SVG icindeki dis kaynaklar da istek dogurur
             "image": ("href", "xlink:href"),
             "use": ("href", "xlink:href")}

    # ⚠️ 4. tur b5: icon / apple-touch-icon / mask-icon / manifest
    # ILISKILERI EKSIKTI. Bunlar da sayfa acilisinda yukleniyor;
    # birinin ucuncu tarafa cevrilmesi gizlilik sayfasindaki
    # "acilista ucuncu tarafa istek yok" sozunu bozardi ama denetim
    # gecerdi.
    YUKLEYEN_REL = ("stylesheet", "preload", "prefetch", "preconnect",
                    "modulepreload", "dns-prefetch", "icon",
                    "apple-touch-icon", "mask-icon", "manifest")

    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.dis = []

    def handle_starttag(self, etiket, oznitelikler):
        d = {k.lower(): (v or "") for k, v in oznitelikler}
        for oz in self.HEDEF.get(etiket, ()):
            for parca in re.split(r"\s*,\s*", d.get(oz, "")):
                aday = parca.split()[0] if parca.split() else ""
                if _dis_mi(aday):
                    self.dis.append("%s[%s]=%s" % (etiket, oz, aday[:52]))
        # <link>: yalnizca YUKLEME yapan iliskiler
        if etiket == "link":
            rel = (d.get("rel") or "").lower()
            if any(r in rel.split() for r in self.YUKLEYEN_REL):
                if _dis_mi(d.get("href")):
                    self.dis.append("link[%s]=%s" % (rel, d.get("href")[:52]))
        # ⚠️ 4. tur b5: style="background:url(https://...)" taranmiyordu
        for m in re.finditer(r"url\(\s*['\"]?([^'\")]+)", d.get("style", "")):
            if _dis_mi(m.group(1)):
                self.dis.append("style url()=%s" % m.group(1)[:52])

    def handle_startendtag(self, etiket, oznitelikler):
        self.handle_starttag(etiket, oznitelikler)

    def error(self, mesaj):
        pass


def _dis_kaynaklar(s_):
    t = _KaynakToplayici()
    try:
        t.feed(s_)
        t.close()
    except Exception:
        pass
    bulgular = list(t.dis)
    # Satir ici <style> ve harici CSS icindeki @import / url()
    for css in re.findall(r"<style[^>]*>(.*?)</style>", s_, re.S | re.I):
        for m in re.finditer(r"@import\s+(?:url\()?['\"]?([^'\")\s]+)", css):
            if _dis_mi(m.group(1)):
                bulgular.append("@import=%s" % m.group(1)[:52])
        for m in re.finditer(r"url\(\s*['\"]?([^'\")]+)", css):
            if _dis_mi(m.group(1)):
                bulgular.append("css url()=%s" % m.group(1)[:52])
    return bulgular


dis_font = []
TARANAN = ["index.html", "gizlilik.html"] + ALT_SAYFA + BILGI
for ad in TARANAN:
    if not os.path.exists(ad):
        continue
    with open(ad, encoding="utf-8") as f:
        s_ = f.read()
    if "fonts.googleapis.com" in s_ or "fonts.gstatic.com" in s_:
        dis_font.append(ad + " (Google Fonts)")
        continue
    d_ = _dis_kaynaklar(s_)
    if d_:
        dis_font.append("%s -> %s" % (ad, d_[:2]))

# Ayri CSS dosyalari da taranir (bilgi.css, fontlar.css)
for ad in ("bilgi.css", "fontlar.css"):
    if not os.path.exists(ad):
        continue
    with open(ad, encoding="utf-8") as f:
        css = f.read()
    for m in re.finditer(r"(?:@import\s+(?:url\()?|url\(\s*)['\"]?([^'\")\s]+)",
                         css):
        if _dis_mi(m.group(1)):
            dis_font.append("%s -> %s" % (ad, m.group(1)[:52]))
            break

kontrol("hicbir sayfa disaridan KAYNAK cekmiyor", not dis_font,
        ("SIZINTI: %s" % dis_font[:3]) if dis_font
        else "%d sayfa + 2 css · script/img/iframe/link/@import taranir"
             % len(TARANAN))

kontrol("fontlar.css var", os.path.exists("fontlar.css"))
if os.path.exists("fontlar.css"):
    with open("fontlar.css", encoding="utf-8") as f:
        fcss = f.read()
    istenen = re.findall(r"url\(([^)]+\.woff2)\)", fcss)
    eksik_font = [y for y in istenen if not os.path.exists(y)]
    kontrol("fontlar.css'teki dosyalar diskte var", not eksik_font,
            ("eksik: %s" % eksik_font[:2]) if eksik_font
            else "%d woff2" % len(istenen))
    # Turkce icin latin-ext SART: ğ ş İ Ğ Ş orada.
    kontrol("latin-ext altkumesi var (Turkce icin sart)",
            "latin-ext" in fcss)
    kontrol("font-display: swap tanimli",
            fcss.count("font-display: swap") == len(istenen),
            "%d/%d" % (fcss.count("font-display: swap"), len(istenen)))

# --- 7. Alt sayfalar + sitemap ---
print("\n--- 7/7  alt sayfalar (%d) ve sitemap ---" % len(ALT_SAYFA))

for ad in ALT_SAYFA:
    if not os.path.exists(ad):
        kontrol(ad, False, "dosya yok")
        continue
    with open(ad, encoding="utf-8") as f:
        s = f.read()
    sorun = []

    for blok in re.findall(
            r'<script type="application/ld\+json">(.*?)</script>', s, re.S):
        try:
            json.loads(blok)
        except json.JSONDecodeError as e:
            sorun.append("JSON-LD bozuk (%s)" % e)

    for etiket in ("div", "section", "article", "ul", "ol", "li", "p",
                   "details", "summary", "nav"):
        ac = len(re.findall(r"<%s[\s>]" % etiket, s))
        kapa = len(re.findall(r"</%s>" % etiket, s))
        if ac != kapa:
            sorun.append("<%s> dengesiz (%d/%d)" % (etiket, ac, kapa))

    sorun += mevzuat_tara(s, ad)

    if "canonical" not in s:
        sorun.append("canonical yok")
    if 'name="description"' not in s:
        sorun.append("description yok")
    if 'href="bilgi.css"' not in s:
        sorun.append("bilgi.css bagli degil")
    duz = duzlestir(s[s.find("<body"):])
    if "hekim muayenesinin yerine geçmez" not in duz.lower():
        sorun.append("sorumluluk notu yok")

    # `iletisim.html` bir ICERIK sayfasi degil KUNYE sayfasidir:
    # telefon, adres, saatler. Onu 400 kelimeye ulastirmak icin metin
    # eklemek yapay sisirme olurdu ve baska sayfalardaki bilgiyi
    # tekrarlardi. Esik bu sayfa icin dusuruldu — kural gevsetilmedi,
    # kapsami duzeltildi.
    alt_sinir = 120 if ad == "iletisim.html" else 400
    kelimeler = len([k for k in duz.split(" ") if len(k) > 1])
    if kelimeler < alt_sinir:
        sorun.append("cok kisa (%d kelime)" % kelimeler)

    kontrol(ad, not sorun,
            ("; ".join(sorun[:2])) if sorun else "%d kelime" % kelimeler)

# --- Klinik varligi TEK mi? (5. tur bulgu 6) ---
# SEO b4'te 11 sayfadaki tam publisher nesnesi @id referansina
# indirilmisti ama hekimlerimiz.html'deki `about` ve iki `worksFor`
# atlanmisti: sayfa ESKI adla UC ayri Dentist nesnesi uretmeye devam
# ediyordu. Arama motoru bunlari ayri isletmeler sayabilir; varlik
# birlestirmenin butun anlami kaybolur. Elle taranarak bulunmasi zor,
# bekci baksin.
KLINIK_ID = "https://ymdisklinigi.com/#klinik"


def _klinik_kopyalari(veri, bulunan):
    if isinstance(veri, dict):
        if (veri.get("@type") in ("Dentist", "MedicalClinic", "LocalBusiness")
                and veri.get("@id") != KLINIK_ID):
            bulunan.append(veri.get("name") or "adsiz nesne")
        for x in veri.values():
            _klinik_kopyalari(x, bulunan)
    elif isinstance(veri, list):
        for x in veri:
            _klinik_kopyalari(x, bulunan)


kopyalar = []
for ad in ALT_SAYFA + BILGI + ["gizlilik.html"]:
    if not os.path.exists(ad):
        continue
    with open(ad, encoding="utf-8") as f:
        s_ = f.read()
    bulunan = []
    for blok in re.findall(
            r'<script type="application/ld\+json">(.*?)</script>', s_, re.S):
        try:
            _klinik_kopyalari(json.loads(blok), bulunan)
        except json.JSONDecodeError:
            pass
    if bulunan:
        kopyalar.append("%s -> %s" % (ad, bulunan[0]))
kontrol("klinik varligi tek @id (kopya Dentist nesnesi yok)",
        not kopyalar, ("; ".join(kopyalar[:2])) if kopyalar
        else "%d sayfa yalniz @id ile atifta bulunuyor"
             % (len(ALT_SAYFA) + len(BILGI) + 1))

# gizlilik.html ALT_SAYFA listesinde degil — menusu ve bicemi farkli.
# Ama CANLI, herkese acik bir sayfa ve mevzuat taramasinin tamamen
# disinda kalmasi gozden kacmisti.
if os.path.exists("gizlilik.html"):
    with open("gizlilik.html", encoding="utf-8") as f:
        gz = f.read()
    gsorun = mevzuat_tara(gz, "gizlilik.html")
    kontrol("gizlilik.html mevzuat taramasi", not gsorun,
            ("; ".join(gsorun[:2])) if gsorun else "taraniyor")

# Bilgi dizini gercekten TUM yazilari listeliyor mu? Yeni bir yazi
# eklenip dizine konmazsa sayfa yetim kalir — hicbir yerden linklenmez.
if os.path.exists("bilgi-yazilari.html"):
    with open("bilgi-yazilari.html", encoding="utf-8") as f:
        dizin = f.read()
    yetim = [a for a in BILGI if a not in dizin]
    kontrol("bilgi dizini tum yazilari listeliyor", not yetim,
            ("dizinde yok: %s" % yetim) if yetim
            else "%d yazi" % len(BILGI))

    # ⚠️ 3 Agu 2026: ItemList semasindaki `numberOfItems` hic
    # denetlenmiyordu. Yazi eklerken kart konup sayinin unutulmasi
    # (ya da tersi) skill'in kendi "sik dusulen hatalar" listesinde
    # yaziyor ama hicbir sey dogrulamiyordu. Artik dogruluyor.
    _say = re.search(r'"numberOfItems"\s*:\s*(\d+)', dizin)
    kontrol("ItemList numberOfItems dogru",
            bool(_say) and int(_say.group(1)) == len(BILGI),
            ("semada %s, diskte %d yazi"
             % (_say.group(1) if _say else "yok", len(BILGI))))

# ==========================================================================
# INGILIZCE BOLUM KONTROLLERI (COKDILLI-TASARIM.md)
# ==========================================================================
# ⚠️ Sayfalar yazilmadan once kuruldu. EN_SAYFA bosken bu blok sessizce
# geciyor; ilk Ingilizce sayfa eklendigi an devreye giriyor.
if COKDILLI_SAYFA:
    _en_sorun = []
    _tr_hedefi = {}          # yabanci sayfa -> gosterdigi TR sayfa
    for _kod, _dil in sorted(DILLER.items()):
      for _ad in _dil["sayfalar"]:
          if not os.path.exists(_ad):
              _en_sorun.append("%s: dosya yok" % _ad)
              continue
          _s = io.open(_ad, encoding="utf-8").read()

          # 1) Sorumluluk notu — Turkce desen yabanci sayfada tutmaz.
          if _dil["sorumluluk"].lower() not in _s.lower():
              _en_sorun.append("%s: %s sorumluluk notu yok"
                               % (_ad, _dil["ad"]))

          # 1b) SAGLIK TURIZMI KAPISI. Belge yokken "tedavi icin seyahat
          #     et" dili yayimlanamaz. Bu kontrol icerik denetimi degil
          #     MEVZUAT kapisidir: ihlali idari yaptirim doguruyor.
          if not BELGE_VAR:
              for _kad, _kdesen in TURIZM_DILI.items():
                  _bul = re.search(_kdesen, _s, re.I)
                  if _bul:
                      _en_sorun.append(
                          "%s: SAGLIK TURIZMI DILI — %s: \"%s\" "
                          "(yetki belgesi yok; belge-bekliyor/ klasorune al "
                          "ya da cumleyi cikar)"
                          % (_ad, _kad, _bul.group(0)[:40]))

          # 2) canonical KENDINE. TR sayfayi gosterirse Google yabanci
          #    sayfayi hic dizine almaz — cok dilli calismanin tamami
          #    bosa gider.
          _kan = re.search(r'<link rel="canonical" href="([^"]+)"', _s)
          # ⚠️ Her dilin ana sayfasi TEMIZ ADRESLE (`/en/`, `/es/`)
          # yayimlaniyor; canonical dosya adini gosterirse ziyaretcinin
          # gordugu adres ile bildirilen adres ayrisir.
          _yol = _ad.replace(os.sep, "/")
          _bekl = ("https://ymdisklinigi.com/%s/" % _kod
                   if _yol == "%s/index.html" % _kod
                   else "https://ymdisklinigi.com/" + _yol)
          if not _kan or _kan.group(1).rstrip("/") != _bekl.rstrip("/"):
              _en_sorun.append("%s: canonical kendine degil (%s)"
                               % (_ad, _kan.group(1) if _kan else "yok"))

          # 3) hreflang: kendisi + TR + x-default + AYNI SAYFANIN VAR
          #    OLDUGU her dil.
          # ⚠️ Son sart onemli: Ispanyolca eklendiginde Ingilizce sayfa
          #    da `hreflang="es"` vermeli. Vermezse Google iki bolumu
          #    ayri ayri degerlendirir ve cok dilli kurulum yarim kalir.
          #    Dil eklerken en kolay atlanan yer burasi.
          _hl = dict(re.findall(
              r'<link[^>]+hreflang="([^"]+)"[^>]+href="([^"]+)"', _s))
          if not _hl:
              _hl = {b: a for a, b in re.findall(
                  r'<link[^>]+href="([^"]+)"[^>]+hreflang="([^"]+)"', _s)}
          _gerekli = {_kod, "tr", "x-default"}
          # ⚠️ Ad esleme DEGIL, ACIK ESLEME tablosu. Ceviri dosya
          # adlari farkli oldugu icin ad karsilastirmasi bu sayfalari
          # hic eslestiremiyordu ve `hreflang` eksigi kaciyordu.
          for _grup in SAYFA_ESI:
              if _yol in _grup.values():
                  _gerekli.update(_grup.keys())
                  break
          # ⚠️ Dongu degiskeni `_bk` — `_dil` KULLANILAMAZ, dis dongunun
          # dil sozlugunu ezer ve sonraki dilde cokerdi (yazarken
          # yapildi, buraya not dusuldu).
          for _bk in sorted(_gerekli):
              if _bk not in _hl:
                  _en_sorun.append("%s: hreflang '%s' yok" % (_ad, _bk))
          if "tr" in _hl:
              _tr_hedefi[_ad] = _hl["tr"].split("/")[-1] or "index.html"

    # 4) ⚠️ hreflang KARSILIKLI olmali. Tek yonlu hreflang'i Google
    #    YOK SAYIYOR — yani TR sayfa da EN'i gostermeli. Bu, cok dilli
    #    kurulumda en sik yapilan ve en sessiz hatadir.
    for _en, _tr in _tr_hedefi.items():
        # ⚠️ Karsiliklilik yalnizca YAYIMLANAN diller arasinda aranir.
        # Yayimlanmayan bir dil sayfasi TR'ye isaret edebilir (zararsiz,
        # canlida degil) ama TR'nin ona GERI isaret etmesi CANLIDA
        # 404 demek olurdu. Yani burada karsiliklilik istemek, tam da
        # kacinmak istedigimiz seyi zorunlu kilardi.
        _ekod = _en.replace(os.sep, "/").split("/")[0]
        if _ekod not in _yayimda_diller():
            continue
        # ⚠️ Bu kontrol bir duzenleme sirasinda ULASILAMAZ hale
        # gelmisti (ustune `continue` dusmustu) — yani sessizce
        # kapanmisti. Denetim "gecti" diyordu ama bir kontrol olmustu.
        if not os.path.exists(_tr):
            _en_sorun.append("%s -> %s: TR karsiligi diskte yok" % (_en, _tr))
            continue
        _trs = io.open(_tr, encoding="utf-8").read()
        # ⚠️ TR sayfa, EN karsiligini TEMIZ ADRESLE gosterebilir
        # (`/en/` — ana sayfa icin dogru olan bu). Iki bicimden biri
        # varsa karsiliklilik saglanmis sayilir.
        _en_yol = _en.replace(os.sep, "/")
        _bicimler = [_en_yol]
        _kk = _en_yol.split("/", 1)[0]
        if _en_yol == "%s/index.html" % _kk:
            _bicimler.append("/%s/" % _kk)
        if not any(b in _trs for b in _bicimler):
            _en_sorun.append("%s: TR sayfasi (%s) GERI hreflang vermiyor"
                             % (_en, _tr))

    kontrol("cok dilli bolum tutarli (canonical + karsilikli hreflang)",
            not _en_sorun,
            ("; ".join(_en_sorun[:3])) if _en_sorun
            else "%d dil, %d sayfa" % (len(DILLER), len(COKDILLI_SAYFA)))

# ⚠️ 3 Agu 2026: ana sayfa "toplam on alti baslik" diyordu — o cumle
# 16 yazi varken doğruydu, sonra 17 yazi daha eklendi ve kimse cumleye
# dokunmadi. Ziyaretciye yanlis bilgi veriyor ve siteyi olduğundan
# zayif gosteriyordu. Yazi eklemek bu sayiyi bozdugu icin ARTIK
# DENETLENIYOR; elle guncel tutmaya guvenmek bir kez zaten tutmadi.
_ONLUK = {2: "yirmi", 3: "otuz", 4: "kirk", 5: "elli",
          6: "altmis", 7: "yetmis", 8: "seksen", 9: "doksan"}
_BIRLIK = {1: "bir", 2: "iki", 3: "uc", 4: "dort", 5: "bes",
           6: "alti", 7: "yedi", 8: "sekiz", 9: "dokuz"}


def _yaziyla(n):
    """33 -> 'otuz uc'. Turkce karakterler sadelestirilmis halde
    donuyor; karsilastirma da sadelestirilmis metin uzerinde."""
    if n < 10:
        return _BIRLIK.get(n, str(n))
    onlar, birler = divmod(n, 10)
    bas = "on" if onlar == 1 else _ONLUK.get(onlar, str(onlar))
    return bas if birler == 0 else bas + " " + _BIRLIK[birler]


def _sadelestir(s_):
    for a, b in (("ı", "i"), ("ü", "u"), ("ö", "o"), ("ç", "c"),
                 ("ş", "s"), ("ğ", "g"), ("â", "a")):
        s_ = s_.replace(a, b)
    return s_


_iy = re.search(r"toplam\s+([a-zA-ZçğıöşüÇĞİÖŞÜâ ]+?)\s+başlık", html)
_bekleniyor = _yaziyla(len(BILGI))
_yazan = _iy.group(1).strip() if _iy else None
_dogru = _yazan is not None and _sadelestir(_yazan) == _bekleniyor
kontrol("ana sayfadaki yazi sayisi dogru", _dogru,
        ("'%s' — %d yazi" % (_yazan, len(BILGI))) if _dogru else
        ("ana sayfa '%s' diyor ama diskte %d yazi var — \"%s\" olmali"
         % (_yazan or "hic sayi yok", len(BILGI), _bekleniyor)))

# ⚠️ 5. tur bulgu 8: burasi "dosya adi sitemap METNINDE geciyor mu" diye
# bakiyordu. Alt dizge oldugu icin `dis-cekimi.html` beklenirken sitemap'te
# yalnizca `eski-dis-cekimi.html` bulunsa da GECIYORDU. Fazladan ya da
# yinelenen URL hic denetlenmiyordu. Artik XML ayristirilip TAM URL
# KUMELERI karsilastiriliyor.
if os.path.exists("sitemap.xml"):
    try:
        kok = ET.parse("sitemap.xml").getroot()
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        loclar = [x.text.strip() for x in kok.findall("s:url/s:loc", ns)]
        beklenen = {"https://ymdisklinigi.com/"}
        beklenen.update("https://ymdisklinigi.com/" + a
                        for a in BILGI + ALT_SAYFA + ["gizlilik.html"])
        # ⚠️ Her dil bolumunun ana sayfasi TEMIZ ADRESLE (`/en/`,
        # `/es/`) yayimlanir; diskteki dosya adi `en/index.html`.
        # Sitemap'te dosya adini yazmak ziyaretcinin gordugu adresten
        # farkli bir URL bildirmek olurdu — Google ikisini ayri sayfa
        # sanabilir. Kural DILDEN BAGIMSIZ yazildi; yeni dil eklenince
        # burayi guncellemek unutulurdu.
        # ⚠️ Yalnizca YAYIMLANAN diller sitemap'te olmali. Yayimlanmayan
        # bir dili bildirmek Google'i 404'e yollar ve sitemap'e guveni
        # duser — tam da sayfalarin dizine girmeye calistigi donemde.
        # Kaynak: siteyi-yukle.py -> YAYIMDA_DILLER (tek kaynak).
        for _dk in DILLER:
            if _dk not in _yayimda_diller():
                continue
            beklenen.update(
                "https://ymdisklinigi.com/"
                + ("%s/" % _dk if a == "%s/index.html" % _dk else a)
                for a in DILLER[_dk]["sayfalar"])
        var = set(loclar)
        yinelenen = len(loclar) != len(var)
        kontrol("sitemap diskle BIREBIR ayni",
                var == beklenen and not yinelenen,
                ("eksik=%s fazla=%s%s"
                 % (sorted(beklenen - var), sorted(var - beklenen),
                    " YINELENEN VAR" if yinelenen else ""))
                if (var != beklenen or yinelenen)
                else "%d URL" % len(loclar))
    except ET.ParseError as e:
        kontrol("sitemap.xml gecerli XML", False, str(e))

print("=" * 74)
if hata:
    print("*** %d HATA ***" % hata)
    sys.exit(1)
print("*** HEPSI GECTI  ·  ana sayfa %d kelime ***" % kelime)
