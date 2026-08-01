#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SITE DENETIMI — index.html veya bilgi yazilari degistiginde calistirilir.

    python denetle.py

Neyi kontrol eder:
  1. JSON-LD bloklari gecerli mi, Dentist + FAQPage duruyor mu
  2. FAQPage semasindaki soru/cevaplar sayfadaki metinle AYNI mi
     (Google, semadaki cevabin sayfada gorunur olmasini sart kosuyor)
  3. HTML etiket dengesi
  4. Mevzuat taramasi — 12 Kas 2025 tanitim yonetmeligi
  5. Icerik hacmi ve bolumlerin varligi
  6. Bilgi yazilari — ayni kurallar onlar icin de

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
import html as html_mod
import io
import json
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

hata = 0


def kontrol(ad, kosul, ayrinti=""):
    global hata
    if kosul:
        print("  TAMAM  %-46s %s" % (ad, ayrinti))
    else:
        print("  HATA   %-46s %s" % (ad, ayrinti))
        hata += 1


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
TICARI = re.compile(
    r"[üu]cret|fiyat|[öo]deme|taksit|indirim|kampanya|bedava|bedelsiz"
    r"|masraf|₺|\bTL\b|dahildir|hari[çc]tir|paket", re.I)

# Muafiyet SADECE yasak kelimeyi dogrudan olumsuzlayan kalipta gecerli.
# Genis pencere fail-open yaratiyordu (1. tur bulgu 6).
MUAF = re.compile(
    r"(fiyat|ücret|kampanya|indirim|ödeme)[^.]{0,60}"
    r"(paylaşamıyoruz|yayımlayamıyoruz|veremiyoruz|izin vermiyor"
    r"|yayımlamasına izin)")

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
    parcalar = [duzlestir(ham_html)]
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

    for ad, desen in YASAKLI.items():
        for m in re.finditer(desen, metin):
            pencere = metin[max(0, m.start() - 70):m.end() + 70]
            if not MUAF.search(pencere):
                sorunlar.append("%s: %s" % (ad, m.group(0)[:30]))
                break
    for m in TICARI.finditer(metin):
        pencere = metin[max(0, m.start() - 70):m.end() + 70]
        if not MUAF.search(pencere):
            sorunlar.append("K15: %s" % m.group(0))
            break
    for desen in PUAN_IZI:
        if re.search(desen, ham_html, re.I):
            sorunlar.append("puan/yorum beyani: %s" % desen)
            break
    return sorunlar


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

# --- 1. JSON-LD ---
print("\n--- 1/6  JSON-LD yapisal veri ---")
bloklar = re.findall(
    r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
kontrol("iki JSON-LD blogu var", len(bloklar) == 2, "%d blok" % len(bloklar))

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
kontrol("FAQPage semasi var", "FAQPage" in tipler)

# --- 2. SSS: sema <-> sayfa (TAM METIN, soru bazli eslesme) ---
print("\n--- 2/6  SSS: sema ile sayfa metni AYNI mi ---")
faq = next((v for v in cozulen if v.get("@type") == "FAQPage"), None)
if faq:
    sorular = faq["mainEntity"]
    sayfa = {}
    for m in re.finditer(
            r'<details class="sss-ogesi">\s*<summary>(.*?)</summary>\s*'
            r'<div class="sss-cevap">(.*?)</div>\s*</details>', html, re.S):
        sayfa[duzlestir(m.group(1))] = duzlestir(m.group(2))

    print("     sema %d soru  ·  sayfa %d soru" % (len(sorular), len(sayfa)))
    kontrol("soru sayilari esit", len(sorular) == len(sayfa))

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
            ("uyusmaz: %s" % uyusmaz[:2]) if uyusmaz else "")

# --- 3. Etiket dengesi ---
print("\n--- 3/6  HTML etiket dengesi ---")
for etiket in ("details", "summary", "section", "div", "main"):
    ac = len(re.findall(r"<%s[\s>]" % etiket, html))
    kapa = len(re.findall(r"</%s>" % etiket, html))
    kontrol("<%s> dengeli" % etiket, ac == kapa,
            "%d ac / %d kapa" % (ac, kapa))

# --- 4. Mevzuat (TUM DOSYA, head dahil) ---
print("\n--- 4/6  Mevzuat taramasi (12 Kas 2025 yonetmeligi) ---")
sorunlar = mevzuat_tara(html, "index.html")
kontrol("index.html mevzuat taramasi", not sorunlar,
        ("; ".join(sorunlar[:3])) if sorunlar else "head + JSON-LD dahil")

govde = html[html.find("<body"):]
emoji = [e for e in re.findall(r"[\U0001F300-\U0001FAFF]", govde)
         if e not in EMOJI_ISTISNA]
kontrol("govdede emoji yok (widget haric)", not emoji,
        ("BULUNDU: %s" % " ".join(sorted(set(emoji)))) if emoji else "")

# --- 5. Icerik ---
print("\n--- 5/6  Icerik hacmi ve bolumler ---")
metin = duzlestir(govde)
kelime = len([k for k in metin.split(" ") if len(k) > 1])
kontrol("gorunur metin 1200+ kelime", kelime > 1200, "%d kelime" % kelime)
kontrol("7 tedavi alaninda acilir ayrinti",
        len(re.findall(r'<details class="ayrinti">', html)) == 7)
for ad, im in (("SSS", 'id="sss"'), ("hekimler", 'id="hekimler"'),
               ("bilgi yazilari", 'id="bilgi"'), ("ulasim", 'id="ulasim"')):
    kontrol("%s bolumu var" % ad, im in html)
kontrol("canonical etiketi var", 'rel="canonical"' in html)
kontrol("meta description var", 'name="description"' in html)
kontrol("Search Console dogrulamasi duruyor",
        "google-site-verification" in html)

# --- 6. Bilgi yazilari ---
BILGI = ["gece-dis-agrisi.html", "kirilan-dis-ne-yapmali.html",
         "dis-apsesi.html", "yirmi-yas-disi.html"]
print("\n--- 6/6  bilgi yazilari (%d sayfa) ---" % len(BILGI))

diskteki = sorted(os.path.basename(y) for y in glob.glob("*.html")
                  if os.path.basename(y) not in ("index.html", "gizlilik.html"))
kontrol("listedeki sayfalar diskle ayni", diskteki == sorted(BILGI),
        "diskte: %s" % ", ".join(diskteki))

for ad in BILGI:
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

if os.path.exists("sitemap.xml"):
    with open("sitemap.xml", encoding="utf-8") as f:
        sm = f.read()
    eksik = [a for a in BILGI + ["gizlilik.html"] if a not in sm]
    kontrol("sitemap tum sayfalari iceriyor", not eksik,
            ("eksik: %s" % eksik) if eksik else "")

print("=" * 74)
if hata:
    print("*** %d HATA ***" % hata)
    sys.exit(1)
print("*** HEPSI GECTI  ·  ana sayfa %d kelime ***" % kelime)
