#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sitemap.xml içindeki `lastmod` tarihlerini GERÇEKLE eşitler.

    python sitemap-tazele.py            # ne değişecek, yazar
    python sitemap-tazele.py --uygula   # uygular

NEDEN VAR — 3 Ağustos 2026'da ölçüldü:
    sitemap  : 36 sayfa "2026-08-01", 19 sayfa "2026-08-02"
    diskte   : 76 sayfanın 75'i **2026-08-03**

Yani sitemap, değişmiş sayfalar için "değişmedi" diyordu.

⚠️ NEDEN ÖNEMLİ: Google `lastmod`'u tarama önceliği sinyali olarak
kullanıyor. Bu sitenin **asıl sorunu** 39 sayfanın henüz dizine
girmemiş olması. Böyle bir dönemde Google'a "bu sayfalar değişmedi"
demek, tam da istemediğimiz şeyi söylemek.

Google yanlış `lastmod` gördüğünde sinyale güvenmeyi tamamen bırakıyor
— yani bir kez yanlış olması, sonraki doğru tarihleri de değersiz
kılıyor. Elle güncel tutmaya güvenmek bir kez zaten tutmadı.

⛔ Tarih UYDURMAZ: temiz, Git'te izlenen sayfa için son Git commit
   tarihini (`%cs`) kullanır. Staged/unstaged/untracked yerel sayfa ise
   henüz commit edilmemiş içeriği yansıtmak için kendi dosya mtime'ını kullanır.
"""
import io
import os
import re
import stat
import subprocess
import sys
import tempfile
import time
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
KOK = os.path.dirname(os.path.abspath(__file__))
SITE = "https://ymdisklinigi.com/"


class SitemapHatasi(RuntimeError):
    """A sitemap entry cannot safely yield a local lastmod date."""


def sitemap_goreli_yolu(loc):
    """Map one canonical site URL to its canonical repository-relative path."""
    if not loc.startswith(SITE):
        raise SitemapHatasi("sitemap URL'i bu siteye ait degil: %s" % loc)
    yol = loc[len(SITE):]
    if yol.startswith("/") or not re.fullmatch(r"[a-z0-9./-]*", yol):
        raise SitemapHatasi("sitemap URL yolu kanonik degil: %s" % loc)
    parcalar = yol.split("/")
    if (any(parca in ("", ".", "..") for parca in parcalar[:-1])
            or parcalar[-1] in (".", "..")):
        raise SitemapHatasi("sitemap URL yolu kanonik degil: %s" % loc)
    if yol == "":
        return "index.html"
    if yol.endswith("/"):
        return yol + "index.html"
    return yol


def yerel_dosya(loc):
    """Sitemap URL'inden diskteki dosyayı bulur.

    Her dilin ana sayfası TEMİZ ADRESLE yayımlanıyor (`/`, `/en/`);
    diskteki karşılığı `index.html` / `en/index.html`.
    """
    yol = sitemap_goreli_yolu(loc)
    aday = KOK
    for parca in yol.split("/"):
        aday = os.path.join(aday, parca)
        try:
            durum = os.lstat(aday)
            if stat.S_ISLNK(durum.st_mode):
                raise SitemapHatasi("yerel yol baglanti iceriyor: %s" % loc)
            reparse_bayragi = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", None)
            if reparse_bayragi is not None:
                nitelikler = getattr(durum, "st_file_attributes", None)
                if not isinstance(nitelikler, int):
                    raise SitemapHatasi("yerel yol nitelikleri olculemedi: %s" % loc)
                if nitelikler & reparse_bayragi:
                    raise SitemapHatasi("yerel yol baglanti iceriyor: %s" % loc)
        except FileNotFoundError:
            return None
        except OSError as hata:
            raise SitemapHatasi("yerel yol olculemedi: %s" % hata)
    p = os.path.realpath(aday)
    kok = os.path.normcase(os.path.realpath(KOK))
    try:
        kok_ici = os.path.commonpath((kok, os.path.normcase(p))) == kok
    except ValueError:
        kok_ici = False
    if not kok_ici:
        raise SitemapHatasi("yerel dosya depo disina tasiyor: %s" % loc)
    return p if os.path.exists(p) else None


def kanonik_tarih_mi(tarih):
    """Accept only a real Gregorian calendar date in canonical YYYY-MM-DD form."""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", tarih):
        return False
    try:
        return datetime.strptime(tarih, "%Y-%m-%d").strftime("%Y-%m-%d") == tarih
    except ValueError:
        return False


def git_calistir(komut):
    """Run one argument-array Git command or fail closed if Git cannot run."""
    try:
        return subprocess.run(
            komut, cwd=KOK, text=True, encoding="utf-8", errors="replace",
            capture_output=True)
    except OSError as hata:
        raise SitemapHatasi("Git calistirilamadi: %s" % hata)


def git_son_commit_tarihi(yol):
    """Return an existing page's latest commit date in Git's %cs form."""
    goreli = os.path.relpath(yol, KOK)
    sonuc = git_calistir(["git", "log", "-1", "--format=%cs", "--", goreli])
    tarih = sonuc.stdout.rstrip("\r\n")
    if sonuc.returncode != 0 or not kanonik_tarih_mi(tarih):
        raise SitemapHatasi("Git commit tarihi olculemedi: %s" % goreli)
    return tarih


def git_degisiklik_var_mi(yol):
    """Whether this exact page has staged, unstaged, or untracked content."""
    goreli = os.path.relpath(yol, KOK).replace(os.sep, "/")
    sonuc = git_calistir(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all", "--",
         goreli])
    if sonuc.returncode != 0:
        raise SitemapHatasi("Git durumunu olcemedim: %s" % goreli)
    if not isinstance(sonuc.stdout, str):
        raise SitemapHatasi("Git durumu metin olarak olculemedi: %s" % goreli)
    if sonuc.stdout == "":
        return False
    kayitlar = sonuc.stdout.split("\0")
    if (not sonuc.stdout.endswith("\0") or len(kayitlar) != 2
            or kayitlar[-1] != ""):
        raise SitemapHatasi("Git durumu tek bir NUL kaydi degil: %s" % goreli)
    kayit = kayitlar[0]
    if (len(kayit) < 4 or kayit[2] != " "
            or kayit[:2] not in ("M ", " M", "MM", "A ", "AM", "??")
            or kayit[3:] != goreli):
        raise SitemapHatasi("Git durumu sayfa ile uyusmuyor: %s" % goreli)
    return True


def yerel_mtime_tarihi(yol):
    """Return the local date for a page with uncommitted content."""
    try:
        tarih = time.strftime("%Y-%m-%d", time.localtime(os.path.getmtime(yol)))
    except (OSError, OverflowError, ValueError) as hata:
        raise SitemapHatasi("yerel dosya tarihi olculemedi: %s" % yol) from hata
    if not kanonik_tarih_mi(tarih):
        raise SitemapHatasi("yerel dosya tarihi olculemedi: %s" % yol)
    return tarih


def son_degisim_tarihi(yol):
    """Choose Git history for clean pages and local mtime for local edits."""
    if git_degisiklik_var_mi(yol):
        return yerel_mtime_tarihi(yol)
    return git_son_commit_tarihi(yol)


def atomik_yaz(yol, metin):
    """Flush a same-directory temporary sitemap, then replace it atomically."""
    tanimlayici, gecici = tempfile.mkstemp(
        prefix=".sitemap-tazele-", suffix=".tmp", dir=os.path.dirname(yol))
    try:
        with io.open(tanimlayici, "w", encoding="utf-8", newline="") as dosya:
            yazilan = dosya.write(metin)
            if type(yazilan) is not int or yazilan != len(metin):
                raise OSError("sitemap gecici dosyasina eksik yazildi")
            dosya.flush()
            os.fsync(dosya.fileno())
        os.replace(gecici, yol)
        gecici = None
    finally:
        if gecici:
            os.unlink(gecici)


def main():
    uygula = "--uygula" in sys.argv
    p = os.path.join(KOK, "sitemap.xml")
    with io.open(p, encoding="utf-8") as dosya:
        s = dosya.read()

    degisen, bulunamayan, gorulen_yollar = [], [], {}

    def yenile(m):
        loc, lastmod = m.group(2), m.group(4)
        y = yerel_dosya(loc)
        if not y:
            bulunamayan.append(loc)
            return m.group(0)
        anahtar = os.path.normcase(os.path.realpath(y))
        onceki = gorulen_yollar.get(anahtar)
        if onceki is not None:
            raise SitemapHatasi(
                "ayni yerel dosyaya iki sitemap URL'i isaret ediyor: %s / %s"
                % (onceki, loc))
        gorulen_yollar[anahtar] = loc
        gercek = son_degisim_tarihi(y)
        if gercek == lastmod:
            return m.group(0)
        degisen.append((loc, lastmod, gercek))
        return m.group(1) + loc + m.group(3) + gercek + m.group(5)

    try:
        yeni = re.sub(r"(<loc>)([^<]+)(</loc>\s*<lastmod>)([^<]+)(</lastmod>)",
                      yenile, s)
    except SitemapHatasi as hata:
        print("HATA: %s" % hata)
        return 1

    print("")
    print("SITEMAP LASTMOD TAZELEME")
    print("=" * 66)
    if bulunamayan:
        print("⚠️ Diskte karsiligi bulunamayan %d URL:" % len(bulunamayan))
        for l in bulunamayan[:5]:
            print("    %s" % l)
        print("")
    if not degisen:
        print("  Butun tarihler dogru — yapacak bir sey yok.")
        return 0
    for loc, eski, gercek in degisen[:12]:
        print("  %-52s %s -> %s" % (loc[len(SITE):][:52] or "/", eski, gercek))
    if len(degisen) > 12:
        print("  ... ve %d tane daha" % (len(degisen) - 12))
    print("")
    print("  %d tarih%s" % (len(degisen),
                            "" if uygula else " — uygulamak icin --uygula"))
    if uygula:
        try:
            atomik_yaz(p, yeni)
        except OSError as hata:
            print("  HATA: sitemap yazilamadi: %s" % hata)
            return 1
        print("  YAZILDI.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
