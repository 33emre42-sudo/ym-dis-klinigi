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
import time
import urllib.error
import urllib.parse
import urllib.request
from defusedxml import ElementTree as ET
from defusedxml.common import DefusedXmlException
from robots_kurallari import kok_erisimi_engelli

sys.stdout.reconfigure(encoding="utf-8", errors="replace",
                       line_buffering=True, write_through=True)

KOK = os.path.dirname(os.path.abspath(__file__))
SITE = "https://ymdisklinigi.com"
ZAMAN = 20
TOPLAM_ZAMAN = 300
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


def _istek_zaman_asimi(deadline=None, tek_istek_suresi=ZAMAN, saat=None):
    """Tek istegi hem kendi timeout'u hem toplam audit suresiyle sinirlar."""
    saat = time.monotonic if saat is None else saat
    if deadline is None:
        return float(tek_istek_suresi)
    kalan = float(deadline) - float(saat())
    if kalan <= 0:
        return None
    return min(float(tek_istek_suresi), kalan)


def getir(yol, acici=None, deadline=None, saat=None):
    """Canli sayfayi indirir. (metin, http_kodu) ya da (None, hata)."""
    adres = _guvenli_site_adresi(yol)
    if adres is None:
        return None, "guvensiz URL"
    zaman_asimi = _istek_zaman_asimi(deadline, ZAMAN, saat)
    if zaman_asimi is None:
        return None, "toplam sure doldu"
    acici = _HTTP_ACICI if acici is None else acici
    istek = urllib.request.Request(
        adres, headers={"User-Agent": "YM-SEO-Denetim/1.0"})
    try:
        with acici.open(istek, timeout=zaman_asimi) as c:
            # Boyut sinirli okuma: kendi sunucumuz da olsa disaridan
            # gelen icerik once XML ayristiricisina giriyor. Ucuz
            # koruma, bagimlilik gerektirmiyor.
            return c.read(EN_BUYUK).decode("utf-8", "replace"), c.status
    except urllib.error.HTTPError as e:
        return None, e.code
    except Exception as e:
        return None, str(e)


def canli_kapsam_hatasi(beklenen, okunan, toplam_sure_doldu):
    """Eksik URL kapsamini ya da sure dolumunu fail-closed ayrintilandirir."""
    if okunan == beklenen and not toplam_sure_doldu:
        return None
    return ("beklenen=%d · okunan=%d · toplam_sure_doldu=%s"
            % (beklenen, okunan,
               "evet" if toplam_sure_doldu else "hayir"))


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
_denetim_deadline = time.monotonic() + TOPLAM_ZAMAN
_toplam_sure_doldu = False
print("=" * 70)
print("CANLI SEO DENETIMI  ·  %s" % SITE)
print("=" * 70)

# --- 1. robots.txt ------------------------------------------------
robots, kod = getir("/robots.txt", deadline=_denetim_deadline)
if robots is None:
    kirmizi("robots.txt okunamadi", str(kod))
else:
    # ⚠️ Disallow satırı tek başına yorumlanamaz; ait olduğu User-agent
    # grubu önemlidir. SEO istihbarat botlarını kapatan meşru kurallar,
    # Google/AI botları için yanlışlıkla "tüm site kapalı" sayılmamalı.
    kritik_tarayicilar = (
        "Googlebot", "Googlebot-Image", "Bingbot", "YandexBot", "DuckDuckBot",
        "GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot",
        "Claude-SearchBot", "Claude-User", "PerplexityBot", "Perplexity-User",
        "Google-Extended", "Applebot", "CCBot",
    )
    engellenenler = [
        ajan for ajan in kritik_tarayicilar
        if kok_erisimi_engelli(robots, ajan)
    ]
    if engellenenler:
        kirmizi("robots.txt kritik tarayicilari kokten engelliyor",
                ", ".join(engellenenler))
    if "sitemap:" not in robots.lower():
        sari("robots.txt sitemap bildirmiyor", "")
    print("  robots.txt        : okundu (%d bayt)" % len(robots))

# --- 2. sitemap: canli mi, diskle ayni mi -------------------------
ham, kod = getir("/sitemap.xml", deadline=_denetim_deadline)
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
denenen = 0
toplam_sayfa = len(canli_url)

for sira, adres in enumerate(sorted(canli_url), 1):
    kisa = adres.replace(SITE, "") or "/"
    if _istek_zaman_asimi(_denetim_deadline) is None:
        _toplam_sure_doldu = True
        break
    denenen += 1
    print("  sayfa             : %d/%d %s"
          % (sira, toplam_sayfa, kisa), flush=True)
    html, kod = getir(adres, deadline=_denetim_deadline)
    if html is None:
        if kod == "toplam sure doldu":
            _toplam_sure_doldu = True
            break
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
_kapsam_hatasi = canli_kapsam_hatasi(
    toplam_sayfa, okunan, _toplam_sure_doldu)
if _kapsam_hatasi:
    kirmizi("CANLI tarama kapsami eksik", _kapsam_hatasi)
print("  sayfa kapsami     : %d/%d okundu · %d denendi"
      % (okunan, toplam_sayfa, denenen))

ana, _ana_kod = getir("/", deadline=_denetim_deadline)
if ana is None:
    if _ana_kod == "toplam sure doldu":
        _toplam_sure_doldu = True
    kirmizi("Ana sayfa okunamadi", str(_ana_kod))
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




# --- 4. GEO: yapay zeka tarayicilari erisebiliyor mu --------------
# ⚠️ 9 Agu 2026 — NEDEN GUNLUK OLCULUYOR.
# Bugun klinige ILK KEZ yapay zeka tavsiyesiyle hasta geldi. O akisin
# tamami iki dosyaya bagli: `llms.txt` (icerik haritasi) ve
# `llms-full.txt` (tam metin). Bunlar SESSIZCE kirilabilir — robots.txt
# degisir, sunucu 404 doner, bir yayin dosyayi goturur. Hicbiri siteyi
# bozmaz; sadece bizi yapay zeka aramasindan siler.
#
# Olculdu: 15 rakip klinigin hicbirinde bu dosyalar yok. Elimizdeki tek
# gercek GEO ustunlugu bu — gunluk bakilmali.
print()
print("--- yapay zeka tarayicilari (GEO) ---")
_AI_TARAYICILAR = ("GPTBot/1.2", "OAI-SearchBot/1.0", "PerplexityBot/1.0",
                   "ClaudeBot/1.0", "Google-Extended")
for _dosya in ("llms.txt", "llms-full.txt"):
    _engelli, _olculemedi = [], []
    for _ua in _AI_TARAYICILAR:
        try:
            # Dosyanin kendi guvenlik kalibi kullaniliyor: adres ak
            # listeden geciyor ve `_HTTP_ACICI` baska bir origin'e
            # sessiz yonlendirmeyi engelliyor.
            _adres = _guvenli_site_adresi("/" + _dosya)
            if _adres is None:
                _olculemedi.append("%s (guvensiz URL)" % _ua)
                continue
            _timeout = _istek_zaman_asimi(
                _denetim_deadline, tek_istek_suresi=20)
            if _timeout is None:
                _toplam_sure_doldu = True
                _olculemedi.append("%s (toplam sure doldu)" % _ua)
                break
            _i = urllib.request.Request(_adres, headers={"User-Agent": _ua})
            with _HTTP_ACICI.open(_i, timeout=_timeout) as _c:
                if _c.status != 200 or not _c.read(64):
                    _engelli.append(_ua)
        except Exception as _e:
            # ⚠️ Olculemeyen ENGELLI sayilmaz ama sessiz de kalmaz.
            _olculemedi.append("%s (%s)" % (_ua, type(_e).__name__))
    if _engelli:
        kirmizi("%s AI tarayicisina KAPALI" % _dosya, ", ".join(_engelli))
    elif _olculemedi:
        sari("%s erisimi olculemedi" % _dosya, ", ".join(_olculemedi[:3]))
    else:
        print("  TAMAM  %-22s %d tarayici da 200 aliyor"
              % (_dosya, len(_AI_TARAYICILAR)))

# --- 5. randevu ucu canli mi --------------------------------------
# ⚠️ Semadaki `ReserveAction` hedefi ve GBP'deki "Web sitesi" alani
# ayni adrese bakiyor. 9 Agu'da olculdu: 302 ile ucuncu tarafa
# yonleniyor. Yonlendirmenin KENDISI sorun degil — HEDEFIN OLMESI
# sorun. O zaman hem randevu ucu kaybolur hem GBP'den gelen hasta
# bos sayfaya duser, ve hicbiri siteyi bozmadigi icin FARK EDILMEZ.
print()
print("--- randevu ucu ---")
try:
    # ⚠️ Burada `_HTTP_ACICI` KULLANILMIYOR ve bu BILINCLI: randevu ucu
    # ucuncu tarafa yonleniyor, olcmek istedigimiz sey tam da hedefin
    # canli olup olmadigi. Ote yandan adres yine ak listeden geciyor.
    _radres = _guvenli_site_adresi("/randevu")
    _timeout = _istek_zaman_asimi(
        _denetim_deadline, tek_istek_suresi=25)
    if _timeout is None:
        _toplam_sure_doldu = True
        raise TimeoutError("toplam sure doldu")
    _rq = urllib.request.Request(_radres,
                                 headers={"User-Agent": "YM-SEO-denetim"})
    with urllib.request.urlopen(_rq, timeout=_timeout) as _rc:
        _son = _rc.geturl()
        if _rc.status != 200:
            kirmizi("randevu ucu HTTP %d" % _rc.status, _son)
        else:
            print("  TAMAM  randevu ucu 200  -> %s" % _son[:60])
except Exception as _e:
    kirmizi("randevu ucu ACILMIYOR", "%s: %s" % (type(_e).__name__, _e))

# --- olmayan yol GERCEKTEN 404 mu? (soft-404 kapisi) ---------------
# ⚠️ 18 Agu 2026 — 20 rakip taranirken IKI sitede olculdu: olmayan HER
# yol HTTP 200 donuyor (biri de 404'u baska bir adrese yonlendiriyor).
# Sonuc: arama motoru sonsuz sayida bos sayfayi "gecerli icerik" sanar,
# tarama butcesi harcanir ve kalitesiz URL dizine girer.
#
# Bizde ayni gun ELLE olculdu ve dort yolun dordu de dogru 404 donuyordu.
# Ama OLCULEN sey KORUNAN sey degildir: nginx yapilandirmasi degisirse
# ya da bir "her seyi ana sayfaya yonlendir" kurali eklenirse hicbir
# mevcut kontrol bunu gormez. Kapi bu yuzden burada.
print()
print("--- olmayan yol 404 donuyor mu ---")
_yok_yolu = "/ym-denetim-olmayan-yol-404-sinavi"
_yok_adres = _guvenli_site_adresi(_yok_yolu)
_yok_timeout = _istek_zaman_asimi(_denetim_deadline, tek_istek_suresi=15)
if _yok_adres is None:
    kirmizi("soft-404 sinavi kurulamadi", "adres reddedildi")
elif _yok_timeout is None:
    _toplam_sure_doldu = True
    sari("soft-404 OLCULEMEDI", "toplam sure doldu")
else:
    try:
        _yok_istek = urllib.request.Request(
            _yok_adres, headers={"User-Agent": "YM-SEO-denetim"})
        with _HTTP_ACICI.open(_yok_istek, timeout=_yok_timeout) as _yok_c:
            kirmizi("SOFT-404: olmayan yol HTTP %d donuyor" % _yok_c.status,
                    _yok_yolu)
    except urllib.error.HTTPError as _yok_h:
        if _yok_h.code in (404, 410):
            print("  TAMAM  olmayan yol HTTP %d" % _yok_h.code)
        elif 300 <= _yok_h.code < 400:
            kirmizi("SOFT-404: olmayan yol YONLENDIRILIYOR (HTTP %d)"
                    % _yok_h.code, _yok_yolu)
        else:
            sari("olmayan yol 404 degil (HTTP %d)" % _yok_h.code, _yok_yolu)
    except Exception as _yok_e:
        # ⛔ Olculemeyen sey TEMIZ degildir (LESSONS §2) — sari, yesil degil.
        sari("soft-404 OLCULEMEDI",
             "%s: %s" % (type(_yok_e).__name__, _yok_e))

if _istek_zaman_asimi(_denetim_deadline) is None:
    _toplam_sure_doldu = True
if _toplam_sure_doldu:
    kirmizi("CANLI denetim toplam sure sinirina ulasti",
            "%d saniye · eksik olcum temiz sayilmadi" % TOPLAM_ZAMAN)

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
