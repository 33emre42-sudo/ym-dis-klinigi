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
import urllib.parse
import urllib.request
from defusedxml import ElementTree as ET
from defusedxml.common import DefusedXmlException

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


def _guvenli_site_adresi(yol):
    """Yalnizca kliniğin sabit HTTPS origin'indeki sade URL'yi kabul eder."""
    if not isinstance(yol, str):
        return None
    adres = SITE + yol if yol.startswith("/") else yol
    try:
        parca = urllib.parse.urlsplit(adres)
        site = urllib.parse.urlsplit(SITE)
    except (TypeError, ValueError):
        return None
    if (parca.scheme, parca.netloc) != (site.scheme, site.netloc):
        return None
    if parca.username is not None or parca.password is not None:
        return None
    if parca.query or parca.fragment or not parca.path.startswith("/"):
        return None
    return urllib.parse.urlunsplit(
        (parca.scheme, parca.netloc, parca.path, "", ""))


class _YonlendirmeYok(urllib.request.HTTPRedirectHandler):
    """Izinli URL'den baska bir origin'e sessiz yonlendirmeyi engeller."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_HTTP_ACICI = urllib.request.build_opener(
    urllib.request.HTTPSHandler(context=ssl.create_default_context()),
    _YonlendirmeYok())


def getir(yol):
    """Canli sayfayi indirir. (metin, http_kodu) ya da (None, hata)."""
    adres = _guvenli_site_adresi(yol)
    if adres is None:
        return None, "guvensiz URL"
    istek = urllib.request.Request(
        adres, headers={"User-Agent": "YM-SEO-Denetim/1.0"})
    try:
        with _HTTP_ACICI.open(istek, timeout=ZAMAN) as c:
            # Boyut sinirli okuma: kendi sunucumuz da olsa disaridan
            # gelen icerik once XML ayristiricisina giriyor. Ucuz
            # koruma, bagimlilik gerektirmiyor.
            return c.read(EN_BUYUK).decode("utf-8", "replace"), c.status
    except urllib.error.HTTPError as e:
        return None, e.code
    except Exception as e:
        return None, str(e)


def dogrulama_durumu(html):
    desen_google = r'<meta\b[^>]*\bname\s*=\s*(["\'])google-site-verification\1'
    desen_bing = r'<meta\b[^>]*\bname\s*=\s*(["\'])msvalidate\.01\1'
    desen_yandex = r'<meta\b[^>]*\bname\s*=\s*(["\'])yandex-verification\1'
    g = len(re.findall(desen_google, html, re.I | re.S))
    b = len(re.findall(desen_bing, html, re.I | re.S))
    y = len(re.findall(desen_yandex, html, re.I | re.S))
    eksikler = []
    if g < 2:
        eksikler.append(("Google dogrulama etiketi eksik",
                         "%d bulundu, 2 olmali (kisisel + klinik hesabi)" % g))
    if b < 1:
        eksikler.append(("Bing dogrulama etiketi (msvalidate.01) YOK", ""))
    if y < 1:
        eksikler.append(("Yandex dogrulama etiketi (yandex-verification) YOK", ""))
    return g, b, y, eksikler


def etiket(html, desen):
    e = re.search(desen, html, re.I | re.S)
    return e.group(1).strip() if e else None


def yinelenen_meta_bulgulari(basliklar, aciklamalar):
    """Duplicate title / description bulgularını renkli tuple listesine çevirir."""
    bulgular = []

    for metin, sayfalar in sorted(basliklar.items(), key=lambda item: item[0]):
        if len(sayfalar) > 1:
            urller = ", ".join(sorted(set(sayfalar)))
            bulgular.append((
                "KIRMIZI",
                "AYNI title birden fazla sayfada",
                'metin="%s" · sayfalar=%s' % (metin, urller)))

    for metin, sayfalar in sorted(aciklamalar.items(), key=lambda item: item[0]):
        if len(sayfalar) > 1:
            urller = ", ".join(sorted(set(sayfalar)))
            bulgular.append((
                "SARI",
                "Ayni description birden fazla sayfada",
                'metin="%s" · sayfalar=%s' % (metin, urller)))

    return bulgular


def sitemap_hatalari(canli_url, disk_yolu):
    """Bos, eksik, bozuk veya canlidan farkli sitemap'i fail-closed bulur."""

    hatalar = []
    if not canli_url:
        hatalar.append(("sitemap.xml URL icermiyor", "0 URL"))
    if not os.path.exists(disk_yolu):
        hatalar.append(("Yerel sitemap.xml yok", disk_yolu))
        return hatalar
    try:
        dkok = ET.parse(disk_yolu).getroot()
        disk_url = {e.text.strip() for e in dkok.iter()
                    if e.tag.endswith("loc") and e.text}
    except (ET.ParseError, DefusedXmlException, OSError) as e:
        hatalar.append(("Yerel sitemap.xml okunamadi", str(e)))
        return hatalar
    if disk_url != canli_url:
        hatalar.append((
            "CANLI sitemap diskle AYNI DEGIL",
            "yalniz canlida: %s | yalniz diskte: %s"
            % (sorted(canli_url - disk_url)[:3],
               sorted(disk_url - canli_url)[:3])))
    return hatalar


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
    except (ET.ParseError, DefusedXmlException) as e:
        kirmizi("sitemap.xml bozuk XML", str(e))

disk_yolu = os.path.join(KOK, "sitemap.xml")
for baslik, ayrinti in sitemap_hatalari(canli_url, disk_yolu):
    kirmizi(baslik, ayrinti)
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
ana, _ = getir("/")
if ana is None:
    kirmizi("Ana sayfa okunamadi", "")
else:
    g, b, y, eksikler = dogrulama_durumu(ana)
    for baslik, ayrinti in eksikler:
        kirmizi(baslik, ayrinti)
    print("  dogrulama etiketi : %d Google · %d Bing · %d Yandex" % (g, b, y))
for renk, baslik, ayrinti in yinelenen_meta_bulgulari(basliklar, aciklamalar):
    if renk == "KIRMIZI":
        kirmizi(baslik, ayrinti)
    else:
        sari(baslik, ayrinti)




# --- rapor --------------------------------------------------------
print()
print("=" * 70)
print("  acilan sayfa      : %d" % okunan)
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
