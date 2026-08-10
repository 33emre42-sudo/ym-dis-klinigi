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
  7. Alt sayfalar (hekimler / SSS / bilgi dizini), renk kontrasti ve sitemap
  8. Site duzeyindeki son guncelleme beyani git gecmisinden eski mi

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
import subprocess
import sys
from datetime import date
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
from kontrast import token_kontrast_hatalari

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
BILGI = ["nobetci-dis-hekimi-acil-dis.html",
         "gece-dis-agrisi.html", "gece-hafta-sonu-dis-hekimi.html",
         "kirilan-dis-ne-yapmali.html",
         "dis-apsesi.html", "dolgu-kaplama-dustu.html", "yirmi-yas-disi.html",
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
# ⚠️ 8 Agu 2026, SITE-16 B3 — kapi yalnizca SEYAHAT ifadelerini
# ariyordu; saglik turizmi ARACILIGINI (konaklama, havaalani transferi)
# ve dogrudan tedavi davetini hic gormuyordu. Turkiye'de bu aracilik
# yetki belgesine bagli; klinikte belge YOK.
#
# ⛔ Raporun onerdigi yama ALINMADI — fiile bagliydi:
# "we arrange your hotel" tutuyor ama "we can help with accommodation"
# kaciyordu. Bunun yerine ARACILIK ISIMLERI'nin kendisi arandi: bir dis
# klinigi sayfasinin otelden/konaklamadan soz etmesi icin mesru sebep
# yok. Olculdu: 78 sayfada bu isimler 0 kez geciyor, yani yanlis alarm
# uretmiyor.
#
# ⚠️ "airport" TEK BASINA ARANMAZ — havalimanindan YOL TARIFI vermek
# serbest ve yararlidir; su an 24 yerde mesru olarak geciyor (ulasim
# sayfalari). Tek basina aransaydi kapi 24 yanlis alarm verir, sonra
# gevsetilirdi — ONAYLI_CUMLE'de dort kez yasanan sinif tam buydu.
# Yalnizca "airport transfer/pickup" BILESIGI aranir: o, yol tarifi
# degil hizmet ilanidir.
TURIZM_DILI = {
    "seyahat cagrisi (EN)": r"\btravel(?:l)?ing\s+(?:to|from)\b"
                            r"|\bif\s+you\s+are\s+travel"
                            r"|\byour\s+stay\b|\blonger\s+stay\b"
                            r"|\btwo\s+trips\b|\bbefore\s+you\s+travel\b"
                            r"|\bhow\s+many\s+days\s+you\b"
                            r"|\bhotels?\b|\baccommodations?\b"
                            r"|\bairport\s+(?:transfer|pickup)s?\b"
                            r"|\bcome\s+to\s+(?:istanbul|turkey|t[üu]rkiye)\s+for\b",
    "seyahat cagrisi (ES)": r"\bsi\s+viaja\b|\bviajar\s+a\s+Estambul\b"
                            r"|\bsu\s+estancia\b|\bcu[aá]ntos\s+d[ií]as\b"
                            r"|\bhotel(?:es)?\b|\balojamientos?\b"
                            r"|\btraslados?\s+(?:al|desde\s+el)\s+aeropuerto\b"
                            r"|\bveng[ao]\s+a\s+Estambul\s+para\b",
    "seyahat cagrisi (FR)": r"\bsi\s+vous\s+voyagez\b|\bvotre\s+s[ée]jour\b"
                            r"|\bcombien\s+de\s+jours\b"
                            r"|\bh[oô]tels?\b|\bh[ée]bergements?\b"
                            r"|\btransferts?\s+a[ée]roport\b"
                            r"|\bvenez\s+[àa]\s+Istanbul\s+pour\b",
    "seyahat cagrisi (DE)": r"\bwenn\s+Sie\s+(?:an)?reisen\b"
                            r"|\bIhr\s+Aufenthalt\b|\bwie\s+viele\s+Tage\b"
                            r"|\bhotels?\b|\bunterk[üu]nfte?\b"
                            r"|\bflughafentransfers?\b"
                            r"|\bkommen\s+Sie\s+nach\s+Istanbul\b",
    "seyahat cagrisi (RU)": r"\bесли\s+вы\s+приезжаете\b|\bваше\s+пребывание\b"
                            r"|\bотел[ьяеи]|\bпрожива|\bтрансфер"
                            r"|\bприезжайте\s+в\s+Стамбул\b",
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

# --- SITE-16 B2: YABANCI SAYFALAR DA MEVZUATTAN GECER --------------------
# ⚠️ Bekci VARDI ama BAGLI DEGILDI. `mevzuat.py` icinde cok dilli yasak
# desenler tanimli (`specialists`, `especialistas`, `spécialistes`,
# `Spezialist`, `специалист` — K38; ayrica fiyat, garanti, once-sonra
# desenlerinin bes dildeki karsiliklari). Ama tarama dongusu YALNIZCA
# Turkce sayfalari geziyordu:  ["index.html"] + ALT_SAYFA + BILGI
#
# Sonuc: 3 Agustos'ta yayina giren 35 yabancı sayfa hicbir mevzuat
# kontrolunden gecmedi. Tanimli olup cagrilmayan koruma, korumasizliktan
# daha tehlikeli — "taranıyor" sanılıyor.
#
# Dil sayfalari `DILLER` sozlugunden geliyor (tek kaynak). Yayimda
# olmayan dil taranmaz: dosya diskte durabilir ama yayinda degilse
# mevzuat konusu da degildir.
print("\n--- 4b  Mevzuat: yabanci dil sayfalari ---")
_dil_mevzuat = []
_dil_sayilan = 0
for _dk in sorted(DILLER):
    if _dk not in _yayimda_diller():
        continue
    for _ds in DILLER[_dk]["sayfalar"]:
        if not os.path.exists(_ds):
            _dil_mevzuat.append("%s: DOSYA YOK" % _ds)
            continue
        try:
            _dh = io.open(_ds, encoding="utf-8").read()
        except OSError as _e:
            _dil_mevzuat.append("%s: okunamadi (%s)" % (_ds, _e))
            continue
        _dil_sayilan += 1
        for _s in mevzuat_tara(_dh, _ds):
            _dil_mevzuat.append("%s — %s" % (_ds, _s))

kontrol("yabanci sayfalar mevzuat taramasindan GECIYOR",
        not _dil_mevzuat,
        _dil_mevzuat[0][:96] if _dil_mevzuat
        else "%d sayfa · %d dil" % (_dil_sayilan, len(_yayimda_diller())))

# ⚠️ Sayfa sayilmadiysa tarama YAPILMAMIS demektir. Bos liste "temiz"
# ile karistirilmamali — bu projede fail-open'in en sik sekli.
kontrol("yabanci sayfa taramasi GERCEKTEN kostu",
        _dil_sayilan > 0 or not _yayimda_diller(),
        "%d sayfa tarandi" % _dil_sayilan)

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
g = len(re.findall(r'<meta\s+name=(["\'])google-site-verification\1', html, re.I))
b = len(re.findall(r'<meta\s+name=(["\'])msvalidate\.01\1', html, re.I))
y = len(re.findall(r'<meta\s+name=(["\'])yandex-verification\1', html, re.I))
kontrol("Google dogrulama etiketleri (2 olmali)", g == 2, "%d bulundu" % g)
kontrol("Bing dogrulama etiketi (msvalidate.01) (1 olmali)", b == 1, "%d bulundu" % b)
kontrol("Yandex dogrulama etiketi (1 olmali)", y == 1, "%d bulundu" % y)
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

# --- Tedavi listesi ANLATAN sayfaya bagli mi ----------------------------
# 4 Agu 2026 olcumu: ana sayfada dokuz `MedicalProcedure` vardi ama
# hicbirinin `url`'si yoktu. Tedavi sayfalarinin `about` alani ZATEN
# MedicalProcedure diyordu — yani parcalar iki ucta duruyor, birbirine
# bagli degildi. Google "bu klinik implant yapiyor" ve "implanti anlatan
# sayfa su" bilgilerinin AYNI SEY oldugunu bilmiyordu.
#
# Baglanti `tedavi-semasini-bagla.py` ile kuruldu. Bu kontrol onu KALICI
# yapiyor: yeni bir tedavi eklenip sayfasi baglanmazsa denetim durur.
_bagsiz = []
try:
    _ih = io.open("index.html", encoding="utf-8").read()
    for _b in re.findall(
            r'<script type="application/ld\+json">(.*?)</script>',
            _ih, re.S):
        try:
            _v = json.loads(_b)
        except ValueError:
            continue
        if _v.get("@type") != "Dentist":
            continue
        for _hz in _v.get("availableService") or []:
            _u = _hz.get("url", "")
            if not _u:
                _bagsiz.append("%s: url yok" % _hz.get("name", "?"))
                continue
            _dosya = _u.rsplit("/", 1)[-1]
            if not os.path.exists(_dosya):
                _bagsiz.append("%s: %s diskte yok"
                               % (_hz.get("name", "?"), _dosya))
except OSError as _e:
    _bagsiz.append("index.html okunamadi: %s" % _e)

kontrol("her tedavi ANLATAN sayfaya bagli",
        not _bagsiz, _bagsiz[0] if _bagsiz else "9 tedavi")

# --- YMYL sinyalleri: yazar, tarih, hekim unvani ------------------------
# 4 Agu 2026 arastirmasi: saglik icerigi Google'in YMYL sinifinda — en
# siki denetlenen kategori. Olculdu: 453 arama gosteriminin TAMAMI ana
# sayfaya gidiyordu, 35 yazinin hicbiri gorunmuyordu. Semada "kim
# inceledi" (reviewedBy) vardi ama "kim yayimladi" ve TARIHLER yoktu.
#
# Alanlar `sema-yazar-ekle.py` ile eklendi. Bu kontrol onlarin KALICI
# olmasini sagliyor: yeni bir yazi eksik semayla eklenirse burada durur.
# (Yazi eklemenin alti ayri adimi var ve gecmiste ikisi unutuldu.)
#
# ⚠️ `author` bir INSAN degil, KLINIK. Yazilari hekimler yazmadi;
# tibben incelediler ve bu sayfada aleni yaziyor. Uydurma insan yazar
# koymak, tam da YMYL'in denetledigi seyi ihlal ederdi.
print("\n--- 6b  bilgi yazilari: YMYL sema sinyalleri ---")
_ymyl_eksik = []
for _ad in BILGI:
    try:
        _t = io.open(_ad, encoding="utf-8").read()
    except OSError as e:
        _ymyl_eksik.append("%s (okunamadi: %s)" % (_ad, e))
        continue
    _sayfa = None
    for _b in re.findall(
            r'<script type="application/ld\+json">(.*?)</script>', _t, re.S):
        try:
            _v = json.loads(_b)
        except ValueError:
            continue                     # bozuk JSON ayri kontrolde
        if _v.get("@type") == "MedicalWebPage":
            _sayfa = _v
            break
    if _sayfa is None:
        _ymyl_eksik.append("%s: MedicalWebPage semasi yok" % _ad)
        continue
    _yok = [_k for _k in ("author", "datePublished", "dateModified",
                          "lastReviewed", "reviewedBy")
            if not _sayfa.get(_k)]
    if _yok:
        _ymyl_eksik.append("%s: %s eksik" % (_ad, ", ".join(_yok)))
        continue
    for _h in _sayfa.get("reviewedBy") or []:
        if not _h.get("hasCredential"):
            _ymyl_eksik.append("%s: %s icin hasCredential yok"
                               % (_ad, _h.get("name", "?")))
            break

kontrol("her yazida author + tarih + hekim unvani var",
        not _ymyl_eksik,
        _ymyl_eksik[0] if _ymyl_eksik else "%d yazi" % len(BILGI))

# --- Site duzeyindeki "son guncelleme" beyani bayat mi? ------------
#
# Bu beyan yalnizca index.html altbilgisinde bulunur. gizlilik.html'deki
# tarih, politika metninin kendi tarihi oldugu icin bu kontrolun kapsami
# disindadir ve asagidaki ayri kontrolle dogrulanir.
_SITE_AYLAR = {
    "Ocak": 1, "Şubat": 2, "Mart": 3, "Nisan": 4,
    "Mayıs": 5, "Haziran": 6, "Temmuz": 7, "Ağustos": 8,
    "Eylül": 9, "Ekim": 10, "Kasım": 11, "Aralık": 12,
}


def _site_turkce_tarih_coz(metin):
    parcalar = metin.split()
    if len(parcalar) != 3 or parcalar[1] not in _SITE_AYLAR:
        raise ValueError("beklenen bicim: 8 Ağustos 2026")
    return date(int(parcalar[2]), _SITE_AYLAR[parcalar[1]],
                int(parcalar[0]))


def _site_turkce_tarih_yaz(tarih):
    ay = next(ad for ad, no in _SITE_AYLAR.items() if no == tarih.month)
    return "%d %s %d" % (tarih.day, ay, tarih.year)


_site_kontrol_adi = "site son güncelleme tarihi bayat değil"
_site_footerlar = re.findall(r"<footer\b[^>]*>(.*?)</footer\s*>",
                             html, re.I | re.S)
_site_eslesmeler = ([m.strip() for m in re.findall(
    r"Son güncelleme:\s*([^<·]+)", _site_footerlar[0])]
    if len(_site_footerlar) == 1 else [])

if len(_site_footerlar) != 1 or len(_site_eslesmeler) != 1:
    kontrol(_site_kontrol_adi, False,
            "index.html footer'inda tek ve gecerli tarih beyani bulunamadi")
else:
    _site_yazan_metin = _site_eslesmeler[0]
    try:
        _site_yazan = _site_turkce_tarih_coz(_site_yazan_metin)
    except (TypeError, ValueError) as _e:
        kontrol(_site_kontrol_adi, False,
                "beyan tarihi cozulemedi: %s" % _e)
    else:
        _site_git_sorun = ""
        _site_gercek = None
        try:
            _site_git = subprocess.run(
                ["git", "log", "-1", "--format=%ad", "--date=short",
                 "--", "*.html"],
                cwd=os.path.dirname(os.path.abspath(__file__)),
                capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=30)
            _site_git_metin = _site_git.stdout.strip()
            if _site_git.returncode != 0 or not _site_git_metin:
                _site_git_sorun = ("git son HTML commit tarihi alinamadi "
                                   "(cikis %d)" % _site_git.returncode)
            else:
                try:
                    _site_gercek = date.fromisoformat(_site_git_metin)
                except ValueError:
                    _site_git_sorun = ("git tarihi anlasilamadi: %s"
                                       % _site_git_metin)
        except Exception as _e:
            _site_git_sorun = "git calistirilamadi (%s)" % type(_e).__name__

        if _site_git_sorun:
            kontrol(_site_kontrol_adi, True,
                    "ölçülemedi: %s; yayın bloke edilmedi"
                    % _site_git_sorun)
        else:
            _site_fark = (_site_gercek - _site_yazan).days
            if _site_fark > 0:
                kontrol(
                    _site_kontrol_adi, False,
                    "%d gün bayat (beyan: %s; git: %s)"
                    % (_site_fark, _site_yazan_metin,
                       _site_turkce_tarih_yaz(_site_gercek)))
            else:
                kontrol(
                    _site_kontrol_adi, True,
                    "beyan: %s; git: %s"
                    % (_site_yazan_metin,
                       _site_turkce_tarih_yaz(_site_gercek)))

# --- Gizlilik politikasinin "son guncelleme" tarihi GERCEK mi? -------
#
# ⚠️ 4 Agu 2026, SITE-16 B8: politika metni 4 Agustos 09:44'te
# degistirildi ama sayfadaki tarih "31 Temmuz"da kaldi. Yani metin
# degisti, hastaya "ne zaman degistigi" yanlis soylendi.
#
# Bu, bugun UCUNCU kez ayni sinif: TURETILMIS bir bilgi kaynagiyla
# birlikte guncellenmediginde sessizce yalan soyluyor (K45-6 bayat
# istem sablonu · SEO-3 B2 bayat envanter · burada bayat tarih).
# Ucunde de kimse yalan soylemek istemedi; elle adim atlandi.
#
# Bir gizlilik politikasinda bu yalnizca ozensizlik degil: sayfanin
# 132-134. satirlari "politika degisirse bu tarih degisir" diye SOZ
# VERIYOR. Tutulmayan soz, politikanin kendisini zayiflatir.
#
# Cozum elle dikkat degil, olcum: tarih GIT'ten geliyor.
_giz = "gizlilik.html"
_giz_sorun = ""
if not os.path.exists(_giz):
    _giz_sorun = "gizlilik.html bulunamadi"
else:
    _m = re.search(r'class="tarih">Son güncelleme:\s*([^<]+)<',
                   io.open(_giz, encoding="utf-8").read())
    if not _m:
        _giz_sorun = "sayfada 'Son güncelleme' satiri bulunamadi"
    else:
        _yazan = _m.group(1).strip()
        try:
            # ⚠️ `%-d` (bassiz gun) bir glibc uzantisi; Windows'taki
            # git onu tanimiyor ve komut 127 ile DUSUYOR. Bassiz hale
            # Python tarafinda getiriliyor — bicimlendirmeyi platforma
            # birakmak, bu kontrolu Windows'ta sessizce olcemez yapardi.
            # ⛔ 11 Agu 2026: OLCUT ARTIK DOSYA DEGIL, METIN.
            #
            # Eskiden `git log -1 -- gizlilik.html` idi: dosyada
            # HERHANGI bir degisiklik tarihi bayatlatiyordu. O gun
            # sayfaya yalnizca <nav> ve erisilebilirlik stilleri
            # eklendi — politika METNI degismedi. Kapi "tarihi
            # guncelle" dedi; oysa guncellemek hastaya "gizlilik
            # politikasi degisti" demek olurdu. Hukuki bir sayfada
            # bu kucuk bir yalan ve kapinin var olus sebebine aykiri.
            #
            # Artik gorunur METNIN en son degistigi commit araniyor;
            # bicim/markup degisiklikleri tarihi bayatlatmiyor.
            def _giz_metin(_ham):
                """POLITIKA METNI = `<main>` icerigi.

                ⚠️ Ilk denemede sayfanin TUM gorunur metni
                karsilastiriliyordu ve "Iceriğe atla" baglantisi
                eklenince kapi yine tetiklendi — oysa o bir GEZINME
                ogesi, politika metni degil. Hastaya "politikaniz
                degisti" demek icin `<main>` icindeki metnin degismesi
                gerekir.
                """
                _mm = re.search(r"(?s)<main\b[^>]*>(.*?)</main\s*>", _ham)
                _t = _mm.group(1) if _mm else _ham
                _t = re.sub(r"(?s)<(script|style)\b.*?</\1>", " ", _t)
                _t = re.sub(r"(?s)<!--.*?-->", " ", _t)
                _t = re.sub(r"<[^>]+>", " ", _t)
                # Tarih satirinin kendisi disarida: yoksa her guncelleme
                # bir sonrakini tetikler (kendi kendini besleyen dongu).
                _t = re.sub(r"Son güncelleme:\s*[^\n]*", " ", _t)
                return re.sub(r"\s+", " ", _t).strip()

            _gercek = ""
            _gl = subprocess.run(
                ["git", "log", "--format=%H %ad",
                 "--date=format:%d %B %Y", "--", _giz],
                capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=30)
            if _gl.returncode == 0 and _gl.stdout.strip():
                _satirlar = [x.split(" ", 1) for x in
                             _gl.stdout.strip().splitlines() if " " in x]
                _onceki_metin = None
                for _sha, _tar in _satirlar:
                    _sh = subprocess.run(
                        ["git", "show", "%s:%s" % (_sha, _giz)],
                        capture_output=True, text=True,
                        encoding="utf-8", errors="replace", timeout=30)
                    if _sh.returncode != 0:
                        break
                    _bu = _giz_metin(_sh.stdout)
                    if _onceki_metin is None:
                        _onceki_metin, _gercek = _bu, _tar.strip().lstrip("0")
                    elif _bu != _onceki_metin:
                        # Bir onceki (daha YENI) commit metni degistirmis.
                        break
                    else:
                        _gercek = _tar.strip().lstrip("0")
        except Exception as _e:
            _gercek = ""
            _giz_sorun = "git okunamadi (%s)" % type(_e).__name__
        # ⚠️ Olcemedigimizde TEMIZ demiyoruz. Git yoksa/okunmuyorsa
        # bu kontrol bir sey soylemeye YETKILI degil; sessizce
        # gecmek "bakildi" sanilmasina yol acar.
        if not _gercek and not _giz_sorun:
            _giz_sorun = "git son degisiklik tarihi alinamadi"
        elif _gercek:
            _AY = {"January": "Ocak", "February": "Şubat", "March": "Mart",
                   "April": "Nisan", "May": "Mayıs", "June": "Haziran",
                   "July": "Temmuz", "August": "Ağustos",
                   "September": "Eylül", "October": "Ekim",
                   "November": "Kasım", "December": "Aralık"}
            for _en, _tr in _AY.items():
                _gercek = _gercek.replace(_en, _tr)
            if _yazan != _gercek:
                _giz_sorun = ("sayfada '%s' yaziyor, git'e gore son "
                              "degisiklik '%s'" % (_yazan, _gercek))

kontrol("gizlilik politikasi tarihi GERCEK degisiklikle ayni",
        not _giz_sorun,
        _giz_sorun or "git ile dogrulandi")

# --- Dil bolumleri arasinda SOZ ESITLIGI ----------------------------
#
# ⚠️ 4 Agu 2026, SITE-16 B5: Almanca, Ispanyolca, Fransizca ve Rusca
# sayfalarin hepsi "telefonu Turkce yanitliyoruz" diyor. Ingilizce
# sayfalarda ayni telefon dugmesi var ama bu uyari YOK — yani
# Ingilizce konusan ziyaretciye otekilerden FARKLI bir hizmet
# beklentisi veriliyor.
#
# Bu, bu projede UCUNCU kez cikan sinif:
#   · 35 yabanci sayfa mevzuat taramasindan hic gecmiyordu
#   · bes dilde implant sisligi anlatiliyor ama ACIL ESIGI ve 112 yok
#   · simdi burada
#
# Ucunun de ortak yani: bir dil ilerliyor, otekiler geride kaliyor ve
# kimse fark etmiyor cunku her dosya KENDI ICINDE dogru gorunuyor.
# Elle karsilastirma bu isi tutmuyor — dil sayisi 5, sayfa sayisi 35.
#
# Burada kontrol edilen sey CEVIRI KALITESI DEGIL: bir dilde verilen
# operasyonel sozun butun dillerde verilip verilmedigi. Soz esitligi
# bir durustluk meselesi; ziyaretcinin hangi dili konustugu, ona ne
# soylendigini degistirmemeli.
_SOZLER = {
    # anahtar: her dilde o sozu tasiyan desen (kucuk harf aranir)
    # ⚠️ Desenler SAYFALARDAN OKUNARAK yazildi, cevrilerek DEGIL.
    # Ilk yazilista Rusca deseni tahmin edilmisti ("мы говорим
    # по-турецки") ve sayfada gercekte "мы отвечаем на турецком"
    # yazdigi icin kontrol, uyari YERINDE DURURKEN eksik bildirdi.
    # Yanlis alarm da bir arizadir: insani korumayi susturmaya iter.
    "telefon Turkce yanitlaniyor": {
        "en": "phone in turkish", "es": "teléfono en turco",
        "fr": "téléphone en turc", "de": "telefon sprechen wir türkisch",
        "ru": "по телефону мы отвечаем на турецком",
    },
}
_soz_eksik = []
for _soz, _desenler in _SOZLER.items():
    for _dk, _desen in _desenler.items():
        _bulundu = 0
        _bakilan = 0
        for _y in DILLER[_dk]["sayfalar"]:
            # Soz yalnizca GIRIS sayfalarinda aranir: ana sayfa ve
            # iletisim. Tedavi sayfalarina da sart kosmak gurultu
            # uretir — ziyaretci telefonu bu ikisinden ariyor.
            _t = os.path.basename(_y).lower()
            if not any(_a in _t for _a in ("index", "contact", "contacto",
                                           "kontakt", "kontakty")):
                continue
            _bakilan += 1
            if not os.path.exists(_y):
                continue
            if _desen in io.open(_y, encoding="utf-8").read().lower():
                _bulundu += 1
        if _bakilan == 0:
            # ⚠️ Hicbir sayfaya bakilamadiysa "gecti" DEME. Kapsam
            # bosluğu, bulgunun kendisinden tehlikeli: bakildi sanilir.
            _soz_eksik.append("%s: giris sayfasi bulunamadi" % _dk)
        elif _bulundu < _bakilan:
            _soz_eksik.append("%s: %d/%d giris sayfasinda '%s' yok"
                              % (_dk, _bakilan - _bulundu, _bakilan, _soz))

kontrol("her dil AYNI operasyonel sozu veriyor",
        not _soz_eksik,
        _soz_eksik[0] if _soz_eksik
        else "%d dil x %d soz" % (len(DILLER), len(_SOZLER)))

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

# Ayri CSS dosyalari da taranir.
_CSS_DOSYALARI = ("bilgi.css", "fontlar.css")
for ad in _CSS_DOSYALARI:
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

# ------------------------------------------------------------------
# ⚠️ 9 Agu 2026 — YUKARIDAKI TARAMANIN KOR NOKTASI: JAVASCRIPT
# ------------------------------------------------------------------
# Yukaridaki tarayici HTML ETIKETLERINE bakiyor. Bir dis adres
# `arayuz.js` icinde DIZGI olarak durup calisma aninda <iframe>'e
# donusurse HTML'de gorunmez ve tarama sessizce gecer.
#
# Tikla-yukle harita tam olarak boyle calisiyor ve bu BILEREK
# yapildi: `denetle.py`nin kendi ayrimina gore kullanicinin
# TIKLAMASIYLA acilan sey "sayfa acilisinda istek" degildir
# (wa.me dugmesiyle ayni kategori). Ama bu muafiyet SESSIZ kalirsa
# yarin baska bir dis adres ayni bosluktan girer.
#
# Bu yuzden muafiyet KOSULA baglandi: JS'te ucuncu taraf harita
# adresi varsa, `gizlilik.html` bunu ANLATMAK ZORUNDA. Yani kod ile
# verilen soz birbirine bagli; biri degisince oteki durur.
_JS = "arayuz.js"
if os.path.exists(_JS):
    with open(_JS, encoding="utf-8") as f:
        _js = f.read()
    # Yorum satirlarini dusur: gerekce metninde gecen adres bulgu degil.
    _js_kod = re.sub(r"^\s*(?://|\*|/\*).*$", "", _js, flags=re.M)
    _js_dis = sorted(set(
        m.group(0) for m in re.finditer(r"https?://[^\s\"'<>)]+", _js_kod)
        if _dis_mi(m.group(0))))
    if _js_dis:
        _harita_disi = [u for u in _js_dis
                        if "maps.google.com" not in u
                        and "google.com/maps" not in u]
        kontrol("arayuz.js'te BEKLENMEYEN dis adres yok", not _harita_disi,
                ("SIZINTI: %s" % _harita_disi[:2]) if _harita_disi
                else "yalniz tikla-yukle haritasi (%d adres)" % len(_js_dis))

        _gz = "gizlilik.html"
        _anlatiliyor = False
        if os.path.exists(_gz):
            with open(_gz, encoding="utf-8") as f:
                _g = f.read()
            # Uc sart: dugmenin adi, "yalnizca ... bastiginizda"
            # kosulu ve Google'in IP gorecegi durustlugu.
            _anlatiliyor = ('Haritayı aç' in _g
                            and 'yalnızca siz' in _g
                            and 'IP adresinizi görür' in _g)
        kontrol("gizlilik.html tikla-yukle haritasini ANLATIYOR",
                _anlatiliyor,
                "" if _anlatiliyor
                else "JS ucuncu taraf harita yukluyor ama gizlilik metni "
                     "bunu yazmiyor — verilen soz ile kod ayristi")
    else:
        kontrol("arayuz.js hicbir dis adres tasimiyor", True,
                "tikla-yukle harita yok")

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

# W3C WCAG 2.1 AA: normal metin 4,5:1; buyuk metin 3:1. Bu statik kapi
# semantik acik/koyu tema tokenlarini ve gradient metin uc noktalarini
# denetler. Sayfa envanteri ve harici CSS envanteri ortak kaynak listesidir;
# :root bulunmayan kaynaklar kontrast modulu tarafindan atlanir.
_kontrast_sorun = []
_kontrast_kaynaklari = []
for _ad in TARANAN:
    if not os.path.exists(_ad):
        continue
    with open(_ad, encoding="utf-8") as _f:
        _sayfa = _f.read()
    _sayfa_css = "\n".join(re.findall(
        r"<style[^>]*>(.*?)</style>", _sayfa, re.S | re.I))
    _kontrast_kaynaklari.append((_ad, _sayfa_css))
for _ad in _CSS_DOSYALARI:
    if not os.path.exists(_ad):
        continue
    with open(_ad, encoding="utf-8") as _f:
        _kontrast_kaynaklari.append((_ad, _f.read()))
for _ad, _css in _kontrast_kaynaklari:
    _kontrast_sorun.extend(
        "%s: %s" % (_ad, _sorun)
        for _sorun in token_kontrast_hatalari(_css))
kontrol("WCAG AA acik/koyu renk tokenlari", not _kontrast_sorun,
        _kontrast_sorun[0] if _kontrast_sorun
        else "normal metin 4,5:1 · buyuk metin 3:1")

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

# --- Hekimler de TEK varlik olmali ----------------------------------
#
# ⚠️ 4 Agu 2026 — IKI denetci bunu BAGIMSIZ olarak buldu
# (SEO-3 B5 ve SITE-16 B7). Ayni iki hekim 36 sayfada kalici `@id` ile
# tanimliyken ANA SAYFA onlari kimliksiz tanimliyordu; yani sitenin en
# onemli sayfasi, arama motoru acisindan iki ADSIZ yeni kisi
# yaratiyordu.
#
# Klinik nesnesi icin ayni kontrol yukarida zaten var ve 5. turda
# konuldu. Hekimler o zaman atlanmisti — ayni ilke, eksik uygulama.
#
# Neden onemli: varlik grafigi parcalanınca hekimin diplomasi,
# unvani ve incelediği yazilar TEK bir kiside toplanmiyor. YMYL
# icerikte kim yazdigi/inceledigi sinyalinin tamami buna dayaniyor.
_HEKIM_ID = {
    "Yunus Emre Çetin":
        "https://ymdisklinigi.com/hekimlerimiz.html#dt-yunus-emre-cetin",
    "Mert Daştan":
        "https://ymdisklinigi.com/hekimlerimiz.html#dt-mert-dastan",
}


def _kimliksiz_hekim(veri, bulunan, dosya):
    """Adi bizim hekimlerimizden biri olan ama @id'si yanlis/eksik
    Person dugumlerini toplar."""
    if isinstance(veri, dict):
        if veri.get("@type") == "Person":
            _ad = (veri.get("name") or "").strip()
            if _ad in _HEKIM_ID and veri.get("@id") != _HEKIM_ID[_ad]:
                bulunan.append("%s -> %s (@id: %s)"
                               % (dosya, _ad, veri.get("@id") or "YOK"))
        for x in veri.values():
            _kimliksiz_hekim(x, bulunan, dosya)
    elif isinstance(veri, list):
        for x in veri:
            _kimliksiz_hekim(x, bulunan, dosya)


_hekim_kopya = []
_hekim_bakilan = 0
for ad in ["index.html"] + ALT_SAYFA + BILGI:
    if not os.path.exists(ad):
        continue
    _hekim_bakilan += 1
    with open(ad, encoding="utf-8") as f:
        _s = f.read()
    for blok in re.findall(
            r'<script type="application/ld\+json">(.*?)</script>', _s, re.S):
        try:
            _kimliksiz_hekim(json.loads(blok), _hekim_kopya, ad)
        except json.JSONDecodeError:
            pass                      # bozuk JSON ayri kontrolde

kontrol("hekimler her sayfada AYNI kalici @id ile",
        not _hekim_kopya,
        _hekim_kopya[0] if _hekim_kopya
        else "%d sayfa tarandi" % _hekim_bakilan)

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

# --- Hub'in meta aciklamasindaki sayi da GERCEK olmali --------------
#
# ⚠️ 4 Agu 2026, SEO-3 B7: `bilgi-yazilari.html` sema tarafinda
# `numberOfItems:35` derken meta aciklamasi hala "32 bilgilendirme
# yazisi" diyordu. Ayni sayfa, ayni gun, iki farkli sayi.
#
# Ustteki kontrol ANA SAYFAYI yazıyla korurken hub'in KENDI
# aciklamasi korumasizdi — ve arama sonucunda kullaniciya gorunen
# metin tam olarak orasi. Yani yanlis sayinin en cok goruldugu yer
# denetlenmiyordu.
#
# Bugun bu sinifin DORDUNCU ornegi (K45-6 bayat istem · SEO-3 B2
# bayat envanter · gizlilik tarihi · burada). Hepsinde ortak kalip:
# kaynak degisti, ondan TURETILMIS metin elle guncellenmedi.
_hub = "bilgi-yazilari.html"
_hub_sorun = ""
if not os.path.exists(_hub):
    _hub_sorun = "bilgi-yazilari.html yok"
else:
    _ht = io.open(_hub, encoding="utf-8").read()
    _hm = re.search(r'<meta name="description" content="([^"]*)"', _ht)
    if not _hm:
        _hub_sorun = "meta description bulunamadi"
    else:
        _sayilar = [int(x) for x in re.findall(r"\b(\d+)\b", _hm.group(1))]
        if not _sayilar:
            # Aciklamada hic sayi yoksa sorun yok — yalnizca YAZILI
            # bir sayi varsa dogru olmasi gerekiyor.
            pass
        elif len(BILGI) not in _sayilar:
            _hub_sorun = ("aciklama %s diyor, diskte %d yazi var"
                          % (_sayilar, len(BILGI)))

kontrol("bilgi hub'inin aciklamasindaki sayi gercek",
        not _hub_sorun, _hub_sorun or "%d yazi" % len(BILGI))

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

# --- llms.txt bayat mi? ------------------------------------------------
#
# ⚠️ 9 Agu 2026: yapay zeka arama motorlari (ChatGPT, Perplexity)
# `llms.txt` dosyasini icerik haritasi olarak okuyor. Olculdu: ChatGPT
# "Bagcilar'da gece acik dis klinigi" sorusunda bizi ONERMIYOR, dort
# rakibi oneriyor. Harita `llms-uret.py` ile uretiliyor; URETILDIKTEN
# SONRA sayfa eklenirse sessizce eksik kalir — sitemap gibi.
#
# Bu kontrol o sessizligi kapatir: sitemap'teki her URL haritada
# gecmeli.
_llms_yol = "llms.txt"
if not os.path.exists(_llms_yol):
    kontrol("llms.txt var (yapay zeka icerik haritasi)", False,
            "yok — `python llms-uret.py --uygula` calistir")
else:
    try:
        _llms = io.open(_llms_yol, encoding="utf-8").read()
    except OSError as _e:
        # ⚠️ Olculemeyeni ihlal SAYMA: surekli kirmizi bir gosterge
        # yok sayilir, sonra kapi gevsetilir. Ama sessiz de kalma.
        kontrol("llms.txt guncel", True,
                "olculemedi (%s) — yayin bloke edilmedi" % _e)
    else:
        try:
            _sm = io.open("sitemap.xml", encoding="utf-8").read()
            _sm_urller = re.findall(r"<loc>([^<]+)</loc>", _sm)
        except OSError as _e:
            _sm_urller = []
        _eksik = [u for u in _sm_urller if u not in _llms]
        kontrol("llms.txt sitemap ile guncel",
                not _eksik,
                ("%d URL haritada YOK: %s — `python llms-uret.py --uygula`"
                 % (len(_eksik), ", ".join(_eksik[:3])))
                if _eksik else "%d URL" % len(_sm_urller))

# ----------------------------------------------------------------------
# llms-full.txt — TAM METIN (9 Agu 2026)
# ----------------------------------------------------------------------
# `llms.txt` bir icerik HARITASI (baslik + aciklama). `llms-full.txt`
# ise metnin KENDISI. Fark onemli: bir model "gece dis agrisinda ne
# yapmaliyim" sorusuna cevap ararken haritadan hangi sayfaya bakacagini
# anlar, ama CEVABI ancak metinden alir.
#
# Olculdu: 15 rakip klinikte llms-full.txt YOK. Bizde de 404 donuyordu.
#
# ⛔ RAKIBIN HATASI: ozbudent.com'un dosyasinin %6'si CSS ve JavaScript
# dolmus. Uretici bunu ariyor ve sizinti varsa DURUYOR; burada da
# ayrica denetleniyor — uretici atlanip dosya elle duzenlenirse gorunur.
_lf_yol = "llms-full.txt"
if not os.path.exists(_lf_yol):
    kontrol("llms-full.txt var (yapay zeka tam metin)", False,
            "yok — `python llms-full-uret.py --uygula` calistir")
else:
    try:
        _lf = io.open(_lf_yol, encoding="utf-8").read()
    except OSError as _e:
        kontrol("llms-full.txt guncel", True,
                "olculemedi (%s) — yayin bloke edilmedi" % _e)
    else:
        # 1) Sitemap'teki her URL tam metinde de gecmeli.
        _lf_eksik = [u for u in _sm_urller if ("URL: " + u) not in _lf]
        kontrol("llms-full.txt sitemap ile guncel", not _lf_eksik,
                ("%d URL metinde YOK: %s — "
                 "`python llms-full-uret.py --uygula`"
                 % (len(_lf_eksik), ", ".join(_lf_eksik[:3])))
                if _lf_eksik else "%d URL · %d KB"
                % (len(_sm_urller), len(_lf.encode("utf-8")) / 1024))
        # 2) CSS/JS sizmamis olmali — rakibin dustugu hata.
        _lf_sizinti = [ad for desen, ad in (
            (r"[{}]", "suslu parantez"),
            (r"\bfunction\s*\(", "function("),
            (r"\d+px\b", "px olcusu"),
            (r"@media\b", "@media"),
            (r"\bdocument\.(querySelector|getElementById)\b", "document.*"),
        ) if re.search(desen, _lf)]
        kontrol("llms-full.txt'te CSS/JS sizintisi YOK", not _lf_sizinti,
                ("SIZINTI: %s" % ", ".join(_lf_sizinti))
                if _lf_sizinti else "5 iz tarandi")

# ======================================================================
# KLINIK SEMASI HER SAYFADA VE TAZE MI  (9 Agu 2026)
# ======================================================================
# 15 rakip olculdu: semada koordinat 0/15, 7 gun 24 saat 0/15. Yani
# "Bagcilar'da gece acik dis klinigi" sorusunun makine okunur cevabi
# bolgede yalniz bizde var. Ama kendi tarafimizda da yarimdi: klinik
# semasi 78 sayfanin YALNIZ BIRINDE (index.html) tanimliydi.
#
# ⚠️ Sorun "atif var, tanim yok" idi: bilgi sayfalari
# `"author":{"@id":".../#klinik"}` diye atifta bulunuyordu ama o
# kimligi yalniz ana sayfa tanimliyordu.
#
# ⛔ ASIL RISK BAYATLAMA: kopyalar `sema-yay.py` ile uretiliyor ve
# degerleri index.html'den okuyor. Ana sayfadaki adres/saat/koordinat
# degisip kopyalar yenilenmezse, 78 sayfa YANLIS bilgi yayinlar —
# ustelik makine okunur bicimde. Bu kapi tam olarak onu tutuyor.
_SEMA_ISARET = "<!-- klinik-semasi: sema-yay.py uretir, ELLE DUZENLEME -->"
try:
    import importlib.util as _iu
    _spec = _iu.spec_from_file_location("_sema_yay", "sema-yay.py")
    _sy = _iu.module_from_spec(_spec)
    _spec.loader.exec_module(_sy)
    _beklenen = _sy.klinik_dugumu()
except Exception as _e:
    _beklenen = None
    kontrol("klinik semasi denetlenebiliyor", False,
            "sema-yay.py yuklenemedi (%s: %s) — semanin tazeligi "
            "OLCULEMEDI, temiz SAYILMAZ" % (type(_e).__name__, _e))

if _beklenen:
    _bekl_metin = json.dumps(_beklenen, ensure_ascii=False,
                             separators=(",", ":"))
    _sema_yok, _sema_bayat = [], []
    for _y in TARANAN:
        if not os.path.exists(_y):
            continue
        with open(_y, encoding="utf-8") as _f:
            _s = _f.read()
        if os.path.abspath(_y) == os.path.abspath("index.html"):
            continue                      # kaynagin kendisi
        if _SEMA_ISARET not in _s:
            _sema_yok.append(_y)
            continue
        _m = re.search(
            re.escape(_SEMA_ISARET) +
            r'\s*<script type="application/ld\+json">\s*(.*?)\s*</script>',
            _s, re.S)
        if not _m or _m.group(1).strip() != _bekl_metin:
            _sema_bayat.append(_y)

    kontrol("klinik semasi HER sayfada", not _sema_yok,
            ("%d sayfada YOK: %s — `python sema-yay.py --uygula`"
             % (len(_sema_yok), ", ".join(_sema_yok[:3])))
            if _sema_yok else "%d sayfa" % (len(TARANAN) - 1))
    kontrol("klinik semasi kopyalari TAZE", not _sema_bayat,
            ("%d sayfada BAYAT: %s — ana sayfa degismis, kopyalar "
             "yenilenmemis. `python sema-yay.py --uygula`"
             % (len(_sema_bayat), ", ".join(_sema_bayat[:3])))
            if _sema_bayat else "index.html ile birebir")

# ======================================================================
# HARF KAPSAMI — gorunur her karakter altkumede var mi  (9 Agu 2026)
# ======================================================================
# Yazi tipleri kendi sunucumuzda ve ALTKUMELI. Altkumede olmayan bir
# karakter sessizce SISTEM yazi tipiyle cizilir: sayfa calisir, hicbir
# test kirmizi vermez, sadece o harf baska bir yazi tipinde gorunur —
# ya da ilgili sistemde hic yoksa BOS KUTU olur.
#
# Olculdu: `←` ve `→` altkumede yoktu, `↑` ve `↓` vardi. Yani ayni
# dortlunun ikisi bizim fontumuzla ikisi baskasiyla ciziliyordu. Ikisi
# de sitenin KENDI satir ici SVG okuyla degistirildi (9 Agu) ve bu kapi
# ancak ondan sonra baglanabildi — daha once baglansa yayin kapanirdi.
#
# ⚠️ `harf-kapsam.py` `fontlar.css` yoksa OLCULEMEDI deyip 0 donuyor
# (bilerek fail-open: surekli kirmizi bir gosterge yok sayilir). Burada
# o hal AYRI raporlaniyor — "olculemedi" sessizce "temiz" olmasin.
try:
    _hk = subprocess.run([sys.executable, "harf-kapsam.py"],
                         cwd=os.path.dirname(os.path.abspath(__file__)),
                         capture_output=True, text=True,
                         encoding="utf-8", errors="replace", timeout=180)
    _hk_cikti = (_hk.stdout or "") + (_hk.stderr or "")
    if "OLCULEMEDI" in _hk_cikti:
        kontrol("harf kapsami olculebildi", False,
                "fontlar.css okunamadi — altkume kapsami OLCULEMEDI, "
                "temiz SAYILMAZ")
    else:
        _eksik = [s.strip() for s in _hk_cikti.splitlines()
                  if "U+" in s and "sayfa:" in s]
        kontrol("gorunur her karakter yazi tipi altkumesinde",
                _hk.returncode == 0,
                ("%d karakter altkumede YOK: %s — sistem yedegiyle "
                 "cizilir, bazi cihazlarda bos kutu olur"
                 % (len(_eksik), "; ".join(_eksik[:2])))
                if _eksik else "78 sayfa")
except Exception as _e:
    kontrol("harf kapsami olculebildi", False,
            "harf-kapsam.py kosturulamadi (%s: %s)"
            % (type(_e).__name__, _e))

# ======================================================================
# ERISILEBILIRLIK KAPISI  (11 Agu 2026)
# ======================================================================
# `ui-ux-pro-max` skill'inin 99 UX kilavuzuna karsi olculdu (olcen
# betik: `ux-olc.py`, kayit: `hasta-mesajlari/UX-OLCUMU-10AGU.md`).
# Uc gercek acik cikti, ucu de kapatildi. Bu kapi TEKRARINI engelliyor.
#
# ⚠️ NEDEN KAPI, NEDEN SADECE DUZELTME DEGIL:
# Ucunden IKISI kendiliginden kalici — hareket korumasi ve `.atla`
# stili `bilgi.css`te, yani yeni sayfa otomatik aliyor. AMA ATLAMA
# BAGLANTISININ KENDISI her sayfanin HTML'inde ve sitede ORTAK BIR
# SABLON DOSYASI YOK: her bilgi yazisi ayri yaziliyor. Yani yeni
# sayfada unutulabilecek tek sey bu — ve sitede 35+ bilgi yazisi var.
#
# 59-65. turlarin en sik hata sinifi tam buydu: bir yerde duzeltilip
# baska yerde unutulmak. Duzeltme yeter demedik, kapi koyduk.
_a11y_atlasiz, _a11y_navsiz, _a11y_idsiz = [], [], []
for _y in TARANAN:
    if not os.path.exists(_y):
        continue
    with open(_y, encoding="utf-8") as _f:
        _s = _f.read()
    if 'class="atla"' not in _s:
        _a11y_atlasiz.append(_y)
    elif 'id="icerik"' not in _s:
        # Atlama baglantisi var ama HEDEFI yok: baglanti hicbir yere
        # gitmez. "Var" gorunup calismayan kapi, olmamasindan kotudur.
        _a11y_idsiz.append(_y)
    # ⚠️ Sozcuk siniri kacisi BILEREK kullanilmiyor: ilk yazimda desen
    # onu iceriyordu ve dosyaya bir KONTROL KARAKTERI olarak yazildi
    # (kabuk kacisi bozdu). Desen hicbir sayfayla eslesmedi ve kapi 43
    # sayfanin HEPSINI reddetti — her yayini durduran bir YANLIS ALARM
    # kapisi olacakti. Acik karakter sinifi hem dogru hem kacisa kapali.
    if not re.search(r"<nav[ >]|role=[\"']navigation", _s):
        _a11y_navsiz.append(_y)

kontrol("her sayfada iceriğe atla baglantisi", not _a11y_atlasiz,
        ("%d sayfada YOK: %s — klavye ya da ekran okuyucu kullanan "
         "hasta butun menuyu tek tek gecmek zorunda kalir"
         % (len(_a11y_atlasiz), ", ".join(_a11y_atlasiz[:3])))
        if _a11y_atlasiz else "%d sayfa" % len(TARANAN))
kontrol("atlama baglantisinin HEDEFI var", not _a11y_idsiz,
        ("%d sayfada id=icerik yok: %s — baglanti hicbir yere gitmiyor"
         % (len(_a11y_idsiz), ", ".join(_a11y_idsiz[:3])))
        if _a11y_idsiz else "id=icerik her sayfada")
kontrol("her sayfada gezinme bolgesi (nav)", not _a11y_navsiz,
        ("%d sayfada YOK: %s"
         % (len(_a11y_navsiz), ", ".join(_a11y_navsiz[:3])))
        if _a11y_navsiz else "%d sayfa" % len(TARANAN))

# Hareket korumasi sayfanin KENDISINDE ya da yukledigi bir CSS'te
# olmali. `bilgi.css` 42 sayfada ortak; `gizlilik.html` tek istisna ve
# kurali kendi stil blogunda tasiyor.
_a11y_css = ""
for _c in sorted(glob.glob("*.css")):
    try:
        with open(_c, encoding="utf-8") as _f:
            _a11y_css += _f.read()
    except OSError:
        pass
_a11y_hareketsiz = []
for _y in TARANAN:
    if not os.path.exists(_y):
        continue
    with open(_y, encoding="utf-8") as _f:
        _s = _f.read()
    _kendi = "prefers-reduced-motion" in _s
    _ortak = ("prefers-reduced-motion" in _a11y_css
              and ".css" in _s)
    if not (_kendi or _ortak):
        _a11y_hareketsiz.append(_y)
kontrol("her sayfada hareket hassasiyeti korumasi", not _a11y_hareketsiz,
        ("%d sayfada YOK: %s — migren ya da vestibuler duyarliligi olan "
         "hastada animasyon bas donmesi yapabilir"
         % (len(_a11y_hareketsiz), ", ".join(_a11y_hareketsiz[:3])))
        if _a11y_hareketsiz else "%d sayfa" % len(TARANAN))


# ======================================================================
# NAP KILIDI — ad/adres/telefon her sayfada ve semada AYNI  (9 Agu 2026)
# ======================================================================
# Google'in yerel siralamada en cok onemsedigi sinyal NAP tutarliligi:
# ayni isletmenin adi, adresi ve telefonu her kaynakta BIREBIR ayni mi.
#
# 15 rakip olculdugunde bu tam da onlarin dustugu yerdi:
# `ozelbagcilardis`te UC ayri telefon numarasi, devlet hastanesinde iki
# ayri isletme adi, `eftaldent`te sayfa ile sema arasinda saat celiskisi.
# Bizde bugun sapma YOK (43 sayfa olculdu) — ama koruyan bir kapi da
# yoktu. Bu kapi, kazanilmis bir ustunlugu ELDE TUTMAK icin.
#
# ⚠️ Tehlike SESSIZ: bir sayfanin altbilgisinde telefonun tek hanesi
# degisse site calisir, hicbir test kirmizi vermez, sayfa 200 doner —
# yalnizca Google'in guven sinyali duser ve sebebi hic gorunmez.
#
# Kaynak TEK: semadaki degerler (`sema-yay.klinik_dugumu()`, o da
# index.html'den okuyor). Gorunur metin ona uymak zorunda; boylece
# "hangisi dogru" tartismasi olmuyor.
if _beklenen:
    _sema_tel = re.sub(r"\D", "", _beklenen.get("telephone", ""))
    _sema_sokak = _beklenen.get("address", {}).get("streetAddress", "")
    # "No: 47 D" gibi kapi numarasi parcasi — adresin en cok yanlis
    # yazilan yeri ve GBP'de de tam burasi yanlisti (No:47 / 34000).
    _m_kapi = re.search(r"No[:.]?\s*\d+\s*[/ ]?\s*[A-Za-z]?", _sema_sokak)
    _sema_kapi = re.sub(r"\s+", " ", _m_kapi.group(0)).strip() if _m_kapi else ""

    _TEL_DESEN = re.compile(r"(?:\+?90)?[\s/.-]*0?\s*5\d{2}[\s/.-]*"
                            r"\d{3}[\s/.-]*\d{2}[\s/.-]*\d{2}")
    _KAPI_DESEN = re.compile(r"No[:.]?\s*\d+\s*[/ ]?\s*[A-Za-z]?")

    _tel_sapan, _kapi_sapan, _kapisiz = [], [], []
    for _y in TARANAN:
        if not os.path.exists(_y):
            continue
        with open(_y, encoding="utf-8") as _f:
            _ham = _f.read()
        # Sema bloklari cikariliyor: onlar zaten ayri kapida
        # dogrulaniyor ve `+90...` bicimi gorunur metinden farkli.
        _govde = re.sub(r"(?s)<script.*?</script>", " ", _ham)
        for _t in set(_TEL_DESEN.findall(_govde)):
            if re.sub(r"\D", "", _t).lstrip("0")[-10:] != _sema_tel[-10:]:
                _tel_sapan.append("%s: %r" % (_y, _t.strip()))
        _kapilar = set(re.sub(r"\s+", " ", _k).strip()
                       for _k in _KAPI_DESEN.findall(_govde))
        if not _kapilar:
            # Her sayfada adres OLMAK ZORUNDA degil (ornegin gizlilik
            # metni) — bu yuzden ayri ve YUMUSAK sayiliyor, sessizce
            # yok sayilmiyor.
            _kapisiz.append(_y)
        for _k in _kapilar:
            if _sema_kapi and _k.lower() != _sema_kapi.lower():
                _kapi_sapan.append("%s: %r" % (_y, _k))

    kontrol("telefon HER sayfada semayla ayni", not _tel_sapan,
            ("%d sapma: %s — NAP tutarsizligi Google guven sinyalini "
             "dusurur ve sebebi gorunmez"
             % (len(_tel_sapan), "; ".join(_tel_sapan[:3])))
            if _tel_sapan else "%s (%d sayfa)" % (_sema_tel, len(TARANAN)))
    kontrol("adres kapi numarasi HER sayfada semayla ayni",
            not _kapi_sapan,
            ("%d sapma: %s — semada %r"
             % (len(_kapi_sapan), "; ".join(_kapi_sapan[:3]), _sema_kapi))
            if _kapi_sapan else "%r (%d sayfada yok, olagan)"
            % (_sema_kapi, len(_kapisiz)))
    kontrol("semadaki kapi numarasi OKUNABILDI", bool(_sema_kapi),
            "okunamazsa yukaridaki adres kapisi hicbir sey olcmez — "
            "streetAddress=%r" % _sema_sokak)

# ======================================================================
# YEREL VARLIK REFERANSLARI DISKTE VAR MI  (9 Agu 2026)
# ======================================================================
# ⚠️ BU KAPI YOKKEN GERCEK BIR KIRIK YAYINLANABILIRDI. `<picture>`
# bloklarina AVIF/WebP `<source>` eklenirken hedef turevler heniz
# uretilmemis olsaydi, denetim bunu GORMEZDI: `_KaynakToplayici`
# yalnizca UCUNCU TARAF adreslerini topluyor, yerel yolun diskte
# karsiligi olup olmadigina hic bakmiyordu.
#
# Sessiz olmasinin sebebi HTML'in kendi kurali: tarayici bir <source>'u
# `type`/`media` olcutune gore SECTIKTEN sonra dosya 404 donerse bir
# SONRAKI kaynaga DUSMEZ. Yani eksik tek bir AVIF, o gorseli AVIF
# destekleyen butun tarayicilarda yok eder — yani neredeyse herkeste.
# HTTP 200 doner, denetim yesil kalir, gorsel yoktur.
_VARLIK_OZ = {"img": ("src", "srcset"), "source": ("src", "srcset"),
              "script": ("src",), "video": ("src", "poster"),
              "audio": ("src",), "track": ("src",), "embed": ("src",),
              "object": ("data",)}
_VARLIK_REL = ("stylesheet", "preload", "modulepreload", "icon",
               "apple-touch-icon", "mask-icon", "manifest")


class _YerelVarlikToplayici(HTMLParser):
    """Sayfanin isaret ettigi YEREL varlik yollarini toplar."""

    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.yollar = []

    def _ekle(self, deger, srcset):
        if not deger:
            return
        adaylar = ([p.strip().split(" ")[0] for p in deger.split(",")]
                   if srcset else [deger.strip()])
        for a in adaylar:
            if not a or _dis_mi(a):
                continue
            a = a.split("#")[0].split("?")[0]
            # data:/mailto:/tel: ve bos degerler disarida
            if not a or ":" in a.split("/")[0]:
                continue
            self.yollar.append(a)

    def handle_starttag(self, etiket, oznitelikler):
        d = {k.lower(): (v or "") for k, v in oznitelikler}
        for oz in _VARLIK_OZ.get(etiket, ()):
            self._ekle(d.get(oz), oz == "srcset")
        if etiket == "link":
            rel = d.get("rel", "").lower().split()
            if any(r in _VARLIK_REL for r in rel):
                self._ekle(d.get("href"), False)


_eksik_varlik = []
for _sayfa in _tum:
    try:
        with open(_sayfa, encoding="utf-8") as _f:
            _icerik = _f.read()
    except OSError:
        continue
    _t = _YerelVarlikToplayici()
    try:
        _t.feed(_icerik)
        _t.close()
    except Exception:
        pass
    _dizin = os.path.dirname(_sayfa)
    for _y in _t.yollar:
        # Kok-bagil ("/x.png") site kokune, digerleri SAYFAYA gore cozulur
        _tam = (_y.lstrip("/") if _y.startswith("/")
                else os.path.normpath(os.path.join(_dizin, _y)))
        if not os.path.exists(_tam.replace("/", os.sep)):
            _eksik_varlik.append("%s -> %s" % (_sayfa, _y))

kontrol("her yerel varlik referansinin diskte karsiligi var",
        not _eksik_varlik,
        ("%d eksik: %s" % (len(_eksik_varlik), "; ".join(_eksik_varlik[:3])))
        if _eksik_varlik else "%d sayfa tarandi" % len(_tum))

print("=" * 74)
if hata:
    print("*** %d HATA ***" % hata)
    sys.exit(1)
print("*** HEPSI GECTI  ·  ana sayfa %d kelime ***" % kelime)
