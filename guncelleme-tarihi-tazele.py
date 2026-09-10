#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""index.html site guncelleme tarihini son HTML commit'iyle esitler.

    python guncelleme-tarihi-tazele.py            # ne degisecek, yazar
    python guncelleme-tarihi-tazele.py --uygula   # uygular

Tarih uydurmaz: izlenen ``*.html`` dosyalarinin Git gecmisini ve yalnizca
Git durumunda gorunen guvenli kirli HTML adaylarinin yerel tarihini olcer.
Temiz izlenen dosyalarin checkout mtime'i kullanilmaz. Olcum veya Git
belirsizse dosyayi degistirmez.
"""
from datetime import date, datetime
import io
import os
import re
import stat
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
KOK = os.path.dirname(os.path.abspath(__file__))
AYLAR = {
    1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan",
    5: "Mayıs", 6: "Haziran", 7: "Temmuz", 8: "Ağustos",
    9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık",
}
TARIH_DESENI = re.compile(
    r"(Son güncelleme:\s*)(?P<tarih>[0-9]{1,2}\s+[^\s<·]+\s+[0-9]{4})"
)
FOOTER_DESENI = re.compile(r"<footer\b[^>]*>.*?</footer\s*>", re.I | re.S)
GIT_TARIH_DESENI = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\n?")


def turkce_tarih(tarih):
    return "%d %s %d" % (tarih.day, AYLAR[tarih.month], tarih.year)


def _git_tarihi(izlenen_yollar):
    if not izlenen_yollar:
        return None, "git son HTML commit tarihi alinamadi (izlenen HTML yok)"
    try:
        sonuc = subprocess.run(
            ["git", "log", "-1", "--format=%ad", "--date=short",
             "--"] + sorted(izlenen_yollar),
            cwd=KOK, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=30)
    except Exception as e:
        return None, "git calistirilamadi (%s)" % type(e).__name__

    metin = sonuc.stdout
    if sonuc.returncode != 0 or not isinstance(metin, str) or not metin:
        return None, ("git son HTML commit tarihi alinamadi (cikis %d)"
                      % sonuc.returncode)
    if not GIT_TARIH_DESENI.fullmatch(metin):
        return None, "git tarihi anlasilamadi: %s" % metin.strip()
    try:
        return date.fromisoformat(metin.rstrip("\n")), ""
    except ValueError:
        return None, "git tarihi anlasilamadi: %s" % metin.strip()


def _kanonik_html_yolu(ham_yol):
    if not ham_yol or any(b < 0x20 or b > 0x7e for b in ham_yol):
        return None, "git HTML yolu kanonik degil"
    try:
        yol = ham_yol.decode("ascii")
    except UnicodeError:
        return None, "git HTML yolu anlasilamadi"
    if (yol != yol.strip() or not yol.endswith(".html") or "\\" in yol
            or ":" in yol or yol.startswith("/") or os.path.isabs(yol)):
        return None, "git HTML yolu kanonik degil"
    parcalar = yol.split("/")
    if any(not parca or parca in (".", "..") for parca in parcalar):
        return None, "git HTML yolu kanonik degil"
    return yol, ""


def _durum_yolu(kayit):
    if len(kayit) < 4 or kayit[2:3] != b" ":
        return None, "git durum kaydi bozuk"
    durum = kayit[:2]
    if durum not in (b"??", b" M", b"M ", b"MM", b"A ", b"AM"):
        return None, "git HTML durumu guvensiz: %s" % durum.decode(
            "ascii", "replace")
    return _kanonik_html_yolu(kayit[3:])


def _kirli_html_yollari():
    try:
        durum = subprocess.run(
            ["git", "status", "--porcelain=v1", "-z",
             "--untracked-files=all", "--", "*.html"],
            cwd=KOK, capture_output=True, timeout=30)
    except Exception as e:
        return None, "git durum bilgisi alinamadi (%s)" % type(e).__name__
    if durum.returncode != 0 or not isinstance(durum.stdout, bytes):
        return None, "git durum bilgisi alinamadi (cikis %d)" % durum.returncode

    ham = durum.stdout
    if ham and not ham.endswith(b"\0"):
        return None, "git durum kaydi NUL ile bitmiyor"
    yollari = []
    gorulenler = set()
    for kayit in ham.split(b"\0")[:-1]:
        yol, sorun = _durum_yolu(kayit)
        if sorun:
            return None, sorun
        anahtar = yol.casefold()
        if anahtar in gorulenler:
            return None, "git HTML yolu belirsiz"
        gorulenler.add(anahtar)
        yollari.append(yol)
    return yollari, ""


def _izlenen_html_yollari():
    try:
        sonuc = subprocess.run(
            ["git", "ls-files", "-z", "--", "*.html"],
            cwd=KOK, capture_output=True, timeout=30)
    except Exception as e:
        return None, "git izlenen HTML bilgisi alinamadi (%s)" % type(e).__name__
    if sonuc.returncode != 0 or not isinstance(sonuc.stdout, bytes):
        return None, "git izlenen HTML bilgisi alinamadi (cikis %d)" % sonuc.returncode
    if sonuc.stdout and not sonuc.stdout.endswith(b"\0"):
        return None, "git izlenen HTML kaydi NUL ile bitmiyor"

    yollari = {}
    for ham_yol in sonuc.stdout.split(b"\0")[:-1]:
        yol, sorun = _kanonik_html_yolu(ham_yol)
        if sorun:
            return None, sorun
        anahtar = yol.casefold()
        onceki = yollari.get(anahtar)
        if onceki is not None and onceki != yol:
            return None, "git izlenen HTML yolu belirsiz"
        yollari[anahtar] = yol
    return yollari, ""


def _reparse_mi(bilgi):
    bayrak = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return (stat.S_ISLNK(bilgi.st_mode)
            or bool(getattr(bilgi, "st_file_attributes", 0) & bayrak))


def _yerel_html_tarihi(yol):
    kok = os.path.abspath(KOK)
    yerel_yol = os.path.abspath(os.path.join(kok, *yol.split("/")))
    try:
        ortak = os.path.commonpath([kok, yerel_yol])
    except ValueError:
        return None, "git HTML yolu kok disinda"
    if os.path.normcase(ortak) != os.path.normcase(kok):
        return None, "git HTML yolu kok disinda"
    try:
        ara = kok
        bilgi = None
        for parca in yol.split("/"):
            ara = os.path.join(ara, parca)
            bilgi = os.lstat(ara)
            if _reparse_mi(bilgi):
                return None, "yerel HTML yolu reparse veya bag"
        if not stat.S_ISREG(bilgi.st_mode):
            return None, "yerel HTML yolu duzenli dosya degil"
        gercek_kok = os.path.realpath(kok)
        gercek_yol = os.path.realpath(yerel_yol)
        if os.path.normcase(os.path.commonpath(
                [gercek_kok, gercek_yol])) != os.path.normcase(gercek_kok):
            return None, "yerel HTML yolu kok disinda"
        return date.fromtimestamp(bilgi.st_mtime), ""
    except (OSError, ValueError, OverflowError) as e:
        return None, "yerel HTML tarihi alinamadi (%s)" % type(e).__name__


def git_tarihi():
    izlenenler, sorun = _izlenen_html_yollari()
    if sorun:
        return None, sorun
    git_tarihi, sorun = _git_tarihi(list(izlenenler.values()))
    if sorun:
        return None, sorun
    yollari, sorun = _kirli_html_yollari()
    if sorun:
        return None, sorun
    if yollari:
        for yol in yollari:
            izlenen = izlenenler.get(yol.casefold())
            if izlenen is not None and izlenen != yol:
                return None, "git HTML yolu belirsiz"

    en_yeni = git_tarihi
    for yol in yollari:
        yerel, sorun = _yerel_html_tarihi(yol)
        if sorun:
            return None, sorun
        if yerel > en_yeni:
            en_yeni = yerel
    return en_yeni, ""


def _tam_yaz(dosya, veri):
    return dosya.write(veri)


def atomik_yaz(yol, veri, tarih):
    """Yeni baytlari ayni dizindeki fsync'li gecici dosyadan degistirir."""
    gecici = None
    fd = None
    yazildi = False
    sorun = ""
    try:
        kaynak_bilgi = os.stat(yol)
        fd, gecici = tempfile.mkstemp(
            prefix=".guncelleme-tarihi-", suffix=".tmp",
            dir=os.path.dirname(os.path.abspath(yol)))
        with os.fdopen(fd, "wb") as dosya:
            fd = None
            if _tam_yaz(dosya, veri) != len(veri):
                raise OSError("kisa yazma")
            dosya.flush()
            mtime_ns = int(datetime(
                tarih.year, tarih.month, tarih.day, 12, 0, 0).timestamp()
                * 1000000000)
            os.utime(gecici, ns=(kaynak_bilgi.st_atime_ns, mtime_ns))
            os.fsync(dosya.fileno())
        os.replace(gecici, yol)
        gecici = None
        yazildi = True
    except Exception as e:
        sorun = type(e).__name__
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError as e:
                yazildi = False
                sorun = "dosya kapatma basarisiz (%s)" % type(e).__name__
        if gecici is not None:
            try:
                os.unlink(gecici)
            except OSError as e:
                yazildi = False
                sorun = "temizleme basarisiz (%s)" % type(e).__name__
    return yazildi, sorun


def main():
    uygula = "--uygula" in sys.argv
    p = os.path.join(KOK, "index.html")

    print("")
    print("SITE SON GUNCELLEME TARIHI TAZELEME")
    print("=" * 66)

    try:
        with io.open(p, "r", encoding="utf-8", newline="") as f:
            icerik = f.read()
    except OSError as e:
        print("  index.html okunamadi (%s)." % type(e).__name__)
        return 1

    footerlar = list(FOOTER_DESENI.finditer(icerik))
    eslesmeler = (list(TARIH_DESENI.finditer(footerlar[0].group(0)))
                   if len(footerlar) == 1 else [])
    if len(footerlar) != 1 or len(eslesmeler) != 1:
        print("  index.html footer'inda tek bir 'Son güncelleme' tarihi bulunamadi.")
        print("  Dosya degistirilmedi; tarih uydurulmadi.")
        return 1

    gercek, sorun = git_tarihi()
    if sorun:
        print("  Tarih ölçülemedi: %s." % sorun)
        print("  Dosya degistirilmedi; tarih uydurulmadi.")
        return 1

    eslesme = eslesmeler[0]
    eski = eslesme.group("tarih")
    yeni = turkce_tarih(gercek)
    if eski == yeni:
        print("  index.html zaten dogru: %s" % yeni)
        print("  Yapacak bir sey yok.")
        return 0

    print("  %-20s %s -> %s" % ("index.html", eski, yeni))
    print("")
    print("  1 tarih%s" % ("" if uygula
                            else " — uygulamak icin --uygula"))
    if uygula:
        bas, son = eslesme.span("tarih")
        bas += footerlar[0].start()
        son += footerlar[0].start()
        yenilenmis = icerik[:bas] + yeni + icerik[son:]
        yazildi, yazma_sorunu = atomik_yaz(
            p, yenilenmis.encode("utf-8"), gercek)
        if not yazildi:
            print("  index.html atomik yazilamadi (%s)." % yazma_sorunu)
            print("  Dosya degistirilmedi; tarih uydurulmadi.")
            return 1
        print("  YAZILDI.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
