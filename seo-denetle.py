# -*- coding: utf-8 -*-
"""CANLI sitenin SEO sagligi.

`denetle.py`'den FARKI onemli: o DISKTEKI dosyalara bakiyor ve cogunlukla
"var mi" diye soruyor. Bu betik CANLI siteye bakiyor ve "dogru mu" diye
soruyor.

Neden ayri: yayin atomik bir sembolik baglanti degisimi. Baglanti eski
bir surume donmus olabilir, sunucuda elle bir dosya degistirilmis
olabilir, ya da bir yayin yarim kalmis olabilir. Bunlarin hicbiri
diskteki dosyalara bakarak gorunmez.

Burada aranan seyler SESSIZ olanlar — site calisiyor gorunur, hicbir
test kirmizi vermez, ama Google'da kaybolursun:

  * bir sayfaya `noindex` girmesi
  * robots.txt'in kapanmasi
  * canonical'in YANLIS adresi gostermesi (sayfa kendini baskasi ilan
    eder ve dizinden dusner)
  * dogrulama etiketlerinin kaybolmasi (Search Console/Bing erisimi gider)
  * canli sitemap ile diskin ayrilmasi
  * iki sayfanin AYNI basligi/aciklamasi tasimasi

Calistirma:  python seo-denetle.py
Cikis kodu:  0 temiz · 1 KIRMIZI bulgu var
"""
import collections
import os
import re
import ssl
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

KOK = os.path.dirname(os.path.abspath(__file__))
SITE = "https://ymdisklinigi.com"
ZAMAN = 20
EN_BUYUK = 4 * 1024 * 1024        # tek sayfa icin fazlasiyla yeterli

# Google aciklamayi ~158 karakterde kesiyor; baslikta ~60 pikselden
# sonra "..." koyuyor. Kesilen metin tiklama oranini dusuruyor.
ACIKLAMA_UST = 158
BASLIK_UST = 65
ACIKLAMA_ALT = 70        # cok kisa aciklama da firsat kaybi

bulgular = []


def kirmizi(baslik, ayrinti=""):
    bulgular.append(("KIRMIZI", baslik, ayrinti))


def sari(baslik, ayrinti=""):
    bulgular.append(("SARI", baslik, ayrinti))


def getir(yol):
    """Canli sayfayi indirir. (metin, http_kodu) ya da (None, hata)."""
    adres = yol if yol.startswith("http") else SITE + yol
    istek = urllib.request.Request(
        adres, headers={"User-Agent": "YM-SEO-Denetim/1.0"})
    try:
        with urllib.request.urlopen(
                istek, timeout=ZAMAN,
                context=ssl.create_default_context()) as c:
            # Boyut sinirli okuma: kendi sunucumuz da olsa disaridan
            # gelen icerik once XML ayristiricisina giriyor. Ucuz
            # koruma, bagimlilik gerektirmiyor.
            return c.read(EN_BUYUK).decode("utf-8", "replace"), c.status
    except urllib.error.HTTPError as e:
        return None, e.code
    except Exception as e:
        return None, str(e)


def etiket(html, desen):
    e = re.search(desen, html, re.I | re.S)
    return e.group(1).strip() if e else None


# ------------------------------------------------------------------
print("=" * 70)
print("CANLI SEO DENETIMI  ·  %s" % SITE)
print("=" * 70)

# --- 1. robots.txt ------------------------------------------------
robots, kod = getir("/robots.txt")
if robots is None:
    kirmizi("robots.txt okunamadi", str(kod))
else:
    # ⚠️ "Disallow: /" tum siteyi kapatir. Tek satirlik bir hata
    # butun trafigi sifirlar ve hicbir test bunu gormez.
    if re.search(r"^\s*Disallow:\s*/\s*$", robots, re.I | re.M):
        kirmizi("robots.txt TUM SITEYI kapatiyor", "Disallow: /")
    if "sitemap:" not in robots.lower():
        sari("robots.txt sitemap bildirmiyor", "")
    print("  robots.txt        : okundu (%d bayt)" % len(robots))

# --- 2. sitemap: canli mi, diskle ayni mi -------------------------
ham, kod = getir("/sitemap.xml")
canli_url = set()
if ham is None:
    kirmizi("sitemap.xml okunamadi", str(kod))
else:
    try:
        kok = ET.fromstring(ham)
        canli_url = {e.text.strip() for e in kok.iter()
                     if e.tag.endswith("loc") and e.text}
    except ET.ParseError as e:
        kirmizi("sitemap.xml bozuk XML", str(e))

disk_yolu = os.path.join(KOK, "sitemap.xml")
if canli_url and os.path.exists(disk_yolu):
    try:
        dkok = ET.parse(disk_yolu).getroot()
        disk_url = {e.text.strip() for e in dkok.iter()
                    if e.tag.endswith("loc") and e.text}
    except ET.ParseError:
        disk_url = set()
    if disk_url and disk_url != canli_url:
        kirmizi("CANLI sitemap diskle AYNI DEGIL",
                "yalniz canlida: %s | yalniz diskte: %s"
                % (sorted(canli_url - disk_url)[:3],
                   sorted(disk_url - canli_url)[:3]))
print("  sitemap           : %d URL" % len(canli_url))

# --- 3. her sayfa tek tek ----------------------------------------
basliklar = collections.defaultdict(list)
aciklamalar = collections.defaultdict(list)
okunan = 0

for adres in sorted(canli_url):
    html, kod = getir(adres)
    kisa = adres.replace(SITE, "") or "/"
    if html is None:
        kirmizi("Sayfa acilmiyor", "%s -> %s" % (kisa, kod))
        continue
    okunan += 1

    # ⚠️ EN TEHLIKELI: noindex. Sayfa calisir, guzel gorunur, testler
    # gecer — ama Google'dan tamamen silinir.
    robots_meta = etiket(html, r'<meta\s+name="robots"\s+content="([^"]*)"')
    if robots_meta and "noindex" in robots_meta.lower():
        kirmizi("SAYFADA NOINDEX VAR", "%s -> %s" % (kisa, robots_meta))

    # canonical yalnizca VAR MI degil, DOGRU MU?
    kan = etiket(html, r'<link\s+rel="canonical"\s+href="([^"]*)"')
    if not kan:
        kirmizi("canonical yok", kisa)
    elif kan.rstrip("/") != adres.rstrip("/"):
        # Sayfa kendini baska bir adres ilan ediyor — dizinden duser.
        kirmizi("canonical YANLIS adresi gosteriyor",
                "%s -> %s" % (kisa, kan))

    bas = etiket(html, r"<title>(.*?)</title>")
    if not bas:
        kirmizi("title yok", kisa)
    else:
        basliklar[bas].append(kisa)
        if len(bas) > BASLIK_UST:
            sari("title uzun (kesilir)", "%s · %d karakter" % (kisa, len(bas)))

    ack = etiket(html, r'<meta\s+name="description"\s+content="([^"]*)"')
    if not ack:
        kirmizi("meta description yok", kisa)
    else:
        aciklamalar[ack].append(kisa)
        if len(ack) > ACIKLAMA_UST:
            sari("description uzun (kesilir)",
                 "%s · %d karakter" % (kisa, len(ack)))
        elif len(ack) < ACIKLAMA_ALT:
            sari("description cok kisa", "%s · %d karakter" % (kisa, len(ack)))

print("  acilan sayfa      : %d/%d" % (okunan, len(canli_url)))

# --- 4. yinelenen baslik/aciklama --------------------------------
# ⚠️ Iki sayfa ayni basligi tasiyorsa Google birini "yinelenen" sayip
# dizine hic almayabilir. Sessiz kayip.
for metin, yerler in basliklar.items():
    if len(yerler) > 1:
        kirmizi("AYNI title birden fazla sayfada",
                "%s -> %s" % (yerler, metin[:50]))
for metin, yerler in aciklamalar.items():
    if len(yerler) > 1:
        sari("Ayni description birden fazla sayfada",
             "%s -> %s" % (yerler, metin[:50]))

# --- 5. dogrulama etiketleri -------------------------------------
# ⚠️ Uc etiket var: iki Google (kisisel + klinik hesabi) ve bir Bing.
# Biri silinirse o hesabin Search Console/Webmaster erisimi KOPAR ve
# bunu ancak aylar sonra fark edersin.
ana, _ = getir("/")
if ana is None:
    kirmizi("Ana sayfa okunamadi", "")
else:
    g = len(re.findall(r'name="google-site-verification"', ana, re.I))
    b = len(re.findall(r'name="msvalidate\.01"', ana, re.I))
    if g < 2:
        kirmizi("Google dogrulama etiketi eksik",
                "%d bulundu, 2 olmali (kisisel + klinik hesabi)" % g)
    if b < 1:
        kirmizi("Bing dogrulama etiketi (msvalidate.01) YOK", "")
    print("  dogrulama etiketi : %d Google · %d Bing" % (g, b))

# --- rapor --------------------------------------------------------
print()
print("=" * 70)
k = [x for x in bulgular if x[0] == "KIRMIZI"]
s = [x for x in bulgular if x[0] == "SARI"]
if not bulgular:
    print("*** SEO TEMIZ — %d sayfa denetlendi ***" % okunan)
else:
    for renk, baslik, ayrinti in k + s:
        print("  %-8s %-42s %s" % (renk, baslik, ayrinti))
    print()
    print("KIRMIZI: %d · SARI: %d" % (len(k), len(s)))
print("=" * 70)

sys.exit(1 if k else 0)
