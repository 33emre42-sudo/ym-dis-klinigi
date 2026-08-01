#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SITE DENETIMI — index.html degistiginde calistirilir.

    python denetle.py

Neyi kontrol eder:
  1. JSON-LD bloklari gecerli mi, Dentist + FAQPage duruyor mu
  2. FAQPage semasindaki soru/cevaplar sayfadaki metinle ayni mi
     (Google, semadaki cevabin sayfada gorunur olmasini sart kosuyor)
  3. HTML etiket dengesi
  4. Mevzuat taramasi — 12 Kas 2025 tanitim yonetmeligi
  5. Icerik hacmi ve bolumlerin varligi
"""
import glob
import io
import json
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

YOL = "index.html"
try:
    with open(YOL, encoding="utf-8") as f:
        html = f.read()
except FileNotFoundError:
    print("index.html bulunamadi — betigi site klasorunde calistirin.")
    sys.exit(1)

hata = 0


def kontrol(ad, kosul, ayrinti=""):
    global hata
    if kosul:
        print("  TAMAM  %-46s %s" % (ad, ayrinti))
    else:
        print("  HATA   %-46s %s" % (ad, ayrinti))
        hata += 1


print("=" * 74)
print("SITE DENETIMI")
print("=" * 74)

# --- 1. JSON-LD ---
print("\n--- 1/5  JSON-LD yapisal veri ---")
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

# --- 2. SSS: sema <-> sayfa ---
print("\n--- 2/5  SSS: sema ile sayfa metni eslesiyor mu ---")
faq = next((v for v in cozulen if v.get("@type") == "FAQPage"), None)
if faq:
    sorular = faq["mainEntity"]
    sayfa_sorulari = [s.strip() for s in re.findall(
        r'<details class="sss-ogesi">\s*<summary>(.*?)</summary>', html, re.S)]
    govdeler = re.findall(r'<div class="sss-cevap">(.*?)</div>', html, re.S)
    print("     sema %d soru  ·  sayfa %d soru" %
          (len(sorular), len(sayfa_sorulari)))
    kontrol("soru sayilari esit", len(sorular) == len(sayfa_sorulari))

    eksik = [q["name"] for q in sorular if q["name"] not in sayfa_sorulari]
    kontrol("her sema sorusu sayfada var", not eksik,
            ("eksik: %s" % eksik[:2]) if eksik else "")

    uyusmaz = []
    for q, g in zip(sorular, govdeler):
        duz = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", g)).strip()
        sema = re.sub(r"\s+", " ", q["acceptedAnswer"]["text"]).strip()
        if duz[:60] != sema[:60]:
            uyusmaz.append(q["name"])
    kontrol("cevap metinleri sayfayla ayni", not uyusmaz,
            ("uyusmaz: %s" % uyusmaz[:2]) if uyusmaz else "")

# --- 3. Etiket dengesi ---
print("\n--- 3/5  HTML etiket dengesi ---")
for etiket in ("details", "summary", "section", "div", "main"):
    ac = len(re.findall(r"<%s[\s>]" % etiket, html))
    kapa = len(re.findall(r"</%s>" % etiket, html))
    kontrol("<%s> dengeli" % etiket, ac == kapa,
            "%d ac / %d kapa" % (ac, kapa))

# --- 4. Mevzuat ---
print("\n--- 4/5  Mevzuat taramasi (12 Kas 2025 yonetmeligi) ---")

# K15 — ticari dil freni. Bu kontrol eskiden klinik-sitesi-olustur.py
# icindeydi; uretici 1 Agu 2026'da arsivlendigi icin buraya tasindi.
# Uretici ayrica aggregateRating (5,0 puan / 8 degerlendirme) yaziyordu;
# bu bir memnuniyet beyanidir ve yonetmelikte yasaktir — geri gelmesin
# diye asagida ayrica kontrol ediliyor.
TICARI = re.compile(
    r"[üu]cret|fiyat|[öo]deme|taksit|indirim|kampanya|bedava|bedelsiz"
    r"|masraf|₺|\bTL\b|dahildir|hari[çc]tir|paket", re.I)

govde = html[html.find("<body"):]
metin = re.sub(r"<[^>]+>", " ", govde)
metin_k = re.sub(r"\s+", " ", metin.lower().replace("i̇", "i"))

# Bir yasakli kelime, "yapamiyoruz/yasak" baglaminda geciyorsa muaftir.
# Ornek: "mevzuat fiyat ve kampanya yayimlamasina izin vermiyor" —
# bu bir kampanya DEGIL, kampanya yapilamadiginin aciklamasi.
MUAF_BAGLAM = re.compile(
    r"(izin vermiyor|yasak|paylaşamıyoruz|yayımlayamıyoruz|"
    r"veremiyoruz|mümkün değil)")

YASAKLI = {
    "en iyi": r"\ben iyi\b",
    "garanti": r"\bgaranti",
    "agrisiz iddiasi": r"\bağrısız\b",
    "kampanya": r"\bkampanya",
    "indirim": r"\bindirim",
    "ucretsiz": r"\bücretsiz\b",
    "fiyat rakami": r"\d[\d.]*\s*(?:tl|₺)\b",
    "hasta yorumu": r"\bmemnun kald|\byorumları\b",
    "once-sonra": r"önce\s*[-/]\s*sonra",
    "uzman iddiasi": r"\buzman(?:ımız|larımız)\b",
}
for ad, desen in YASAKLI.items():
    gercek = []
    for m in re.finditer(desen, metin_k):
        pencere = metin_k[max(0, m.start() - 90):m.end() + 90]
        if not MUAF_BAGLAM.search(pencere):
            gercek.append(m.group(0))
    kontrol("yasakli ifade yok: %s" % ad, not gercek,
            ("BULUNDU: %s" % gercek[:3]) if gercek else "")

# K15: ticari dil (uretici bunu yaparsa site YAZILMIYORDU)
k15 = []
for m in TICARI.finditer(metin_k):
    pencere = metin_k[max(0, m.start() - 90):m.end() + 90]
    if not MUAF_BAGLAM.search(pencere):
        k15.append(m.group(0))
kontrol("K15 — ticari dil yok", not k15,
        ("BULUNDU: %s" % sorted(set(k15))[:4]) if k15 else "")

# Puan / yorum beyani — yonetmelikte yasak, uretici bunu yaziyordu
puan_izleri = []
for desen in (r"aggregateRating", r"ratingValue", r"reviewCount",
              r"\bGoogle'?da\s+\d", r"\d\s*[,.]\s*\d\s*·\s*\d+\s*değerlendirme"):
    if re.search(desen, html, re.I):
        puan_izleri.append(desen)
kontrol("puan/yorum beyani yok", not puan_izleri,
        ("BULUNDU: %s" % puan_izleri) if puan_izleri else "")

# Emoji — tasarim karari: sayfa govdesinde emoji olmayacak.
# Iki bilincli istisna, ikisi de sohbet widget'inda: 💬 acma dugmesi,
# 🦷 pencere basligi. Widget hastaya daha samimi bir dille hitap ediyor;
# sayfanin geri kalani emojisiz kalmali.
EMOJI_ISTISNA = {"💬", "🦷"}
emoji = [e for e in re.findall(r"[\U0001F300-\U0001FAFF]", govde)
         if e not in EMOJI_ISTISNA]
kontrol("govdede emoji yok (widget haric)", not emoji,
        ("BULUNDU: %s" % " ".join(sorted(set(emoji)))) if emoji else "")

# --- 5. Icerik ---
print("\n--- 5/5  Icerik hacmi ve bolumler ---")
kelime = len([k for k in re.split(r"\s+", metin) if len(k) > 1])
kontrol("gorunur metin 1200+ kelime", kelime > 1200, "%d kelime" % kelime)
kontrol("7 tedavi alaninda acilir ayrinti",
        len(re.findall(r'<details class="ayrinti">', html)) == 7)
kontrol("SSS bolumu var", 'id="sss"' in html)
kontrol("ulasim bolumu var", 'id="ulasim"' in html)
kontrol("canonical etiketi var", 'rel="canonical"' in html)
kontrol("meta description var", 'name="description"' in html)

# --- 6. Bilgi yazilari ---
# Ayri sayfalar da yayina gidiyor; ayni mevzuat ve gecerlilik kurallari
# onlar icin de gecerli.
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

    g = s[s.find("<body"):]
    m = re.sub(r"<[^>]+>", " ", g)
    mk = re.sub(r"\s+", " ", m.lower().replace("i̇", "i"))
    for etiketAd, desen in YASAKLI.items():
        for mm in re.finditer(desen, mk):
            pencere = mk[max(0, mm.start() - 90):mm.end() + 90]
            if not MUAF_BAGLAM.search(pencere):
                sorun.append("yasakli: %s" % etiketAd)
                break
    for mm in TICARI.finditer(mk):
        pencere = mk[max(0, mm.start() - 90):mm.end() + 90]
        if not MUAF_BAGLAM.search(pencere):
            sorun.append("K15: %s" % mm.group(0))
            break

    if "canonical" not in s:
        sorun.append("canonical yok")
    if 'name="description"' not in s:
        sorun.append("description yok")
    if 'href="bilgi.css"' not in s:
        sorun.append("bilgi.css bagli degil")
    # not: metin satirlara bolunmus olabilir, bosluklari sadelestirerek ara
    if "hekim muayenesinin yerine geçmez" not in re.sub(r"\s+", " ", m).lower():
        sorun.append("sorumluluk notu yok")

    kelimeler = len([k for k in re.split(r"\s+", m) if len(k) > 1])
    if kelimeler < 500:
        sorun.append("cok kisa (%d kelime)" % kelimeler)

    kontrol(ad, not sorun,
            ("; ".join(sorun[:2])) if sorun else "%d kelime" % kelimeler)

kontrol("bilgi.css var", os.path.exists("bilgi.css"))

# sitemap her yayin sayfasini icermeli
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
