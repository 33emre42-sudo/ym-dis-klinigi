#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""index.html site guncelleme tarihini son HTML commit'iyle esitler.

    python guncelleme-tarihi-tazele.py            # ne degisecek, yazar
    python guncelleme-tarihi-tazele.py --uygula   # uygular

Tarih uydurmaz: depodaki herhangi bir ``*.html`` dosyasina dokunan son
commit'in tarihini git'ten okur. Git tarihi olculemezse dosyayi degistirmez.
"""
from datetime import date
import io
import os
import re
import subprocess
import sys

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


def turkce_tarih(tarih):
    return "%d %s %d" % (tarih.day, AYLAR[tarih.month], tarih.year)


def git_tarihi():
    try:
        sonuc = subprocess.run(
            ["git", "log", "-1", "--format=%ad", "--date=short",
             "--", "*.html"],
            cwd=KOK, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=30)
    except Exception as e:
        return None, "git calistirilamadi (%s)" % type(e).__name__

    metin = sonuc.stdout.strip()
    if sonuc.returncode != 0 or not metin:
        return None, ("git son HTML commit tarihi alinamadi (cikis %d)"
                      % sonuc.returncode)
    try:
        return date.fromisoformat(metin), ""
    except ValueError:
        return None, "git tarihi anlasilamadi: %s" % metin


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
        with io.open(p, "w", encoding="utf-8", newline="") as f:
            f.write(yenilenmis)
        print("  YAZILDI.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
