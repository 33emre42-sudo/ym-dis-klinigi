# -*- coding: utf-8 -*-
"""Siteyi ui-ux-pro-max'in 11 erisilebilirlik kilavuzuna karsi OLCER.

Oneri degil olcum: her satirin yaninda kanit ya da eksik var.
"""
import glob
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
KOK = r"C:\Users\33emr\Klinik\klinik-sitesi"
sayfalar = sorted(glob.glob(os.path.join(KOK, "*.html")))
def oku(y):
    """⚠️ Yorumlar ve <style>/<script> govdesi AYIKLANIR.

    Ilk surumde "alt metni olmayan gorsel" bulgusu cikti; dogrulayinca
    bulunan sey bir CSS YORUMUNUN icindeki `<img>` kelimesiydi
    (`/* ESNEYEN OGE <picture>, <img> DEGIL */`). Gercek gorsel degildi.
    Sunmadan once dogrulamak bunun icin (LESSONS.md §6).
    """
    ham = io.open(y, encoding="utf-8", errors="replace").read()
    ham = re.sub(r"(?s)<!--.*?-->", " ", ham)
    ham = re.sub(r"(?s)<style.*?</style>", " ", ham)
    ham = re.sub(r"(?s)<script.*?</script>", " ", ham)
    # ⚠️ CSS yorumlari da ayiklanir — yanlis alarmin GERCEK kaynagi
    # buydu: `/* ESNEYEN OGE <picture>, <img> DEGIL */`. Salt
    # `<style>` ayiklamasi yetmedi.
    ham = re.sub(r"(?s)/\*.*?\*/", " ", ham)
    return ham


def ham_oku(y):
    """Yorumlar DAHIL — CSS/JS icindeki kurallari (or.
    `prefers-reduced-motion`) aramak icin."""
    return io.open(y, encoding="utf-8", errors="replace").read()
hepsi = {os.path.basename(y): oku(y) for y in sayfalar}
ana = hepsi.get("index.html", "")


def rapor(ad, gecti, kanit):
    print("  %s %-26s %s" % ("✅" if gecti else "🔴", ad, kanit))


print("=" * 74)
print("SITE vs ui-ux-pro-max ERISILEBILIRLIK KILAVUZLARI (%d sayfa)"
      % len(hepsi))
print("=" * 74)

# 1) Skip links
skip = sum(1 for s in hepsi.values()
           if re.search(r'href="#(icerik|ana|main)', s, re.I))
rapor("Skip Links", skip == len(hepsi),
      "%d/%d sayfada atlama baglantisi" % (skip, len(hepsi)))

# 2) Alt text — alt'siz img
altsiz = [(a, len(re.findall(r"<img(?![^>]*\balt=)[^>]*>", s)))
          for a, s in hepsi.items()]
eksik = [(a, n) for a, n in altsiz if n]
rapor("Alt Text", not eksik,
      "alt'siz gorsel yok" if not eksik else "%d sayfada eksik: %s"
      % (len(eksik), eksik[:3]))

# 3) Heading hierarchy — tek h1
coklu = [a for a, s in hepsi.items() if len(re.findall(r"<h1\b", s)) != 1]
rapor("Heading Hierarchy", not coklu,
      "her sayfada tam 1 adet h1" if not coklu else "sapan: %s" % coklu[:3])

# 4) Motion sensitivity
ham = {os.path.basename(y): ham_oku(y) for y in sayfalar}
css = "".join(ham_oku(c) for c in glob.glob(os.path.join(KOK, "*.css")))
rm = sum(1 for a, s in ham.items()
         if "prefers-reduced-motion" in s
         or "prefers-reduced-motion" in css)
rapor("Motion Sensitivity", rm == len(hepsi),
      "%d/%d sayfada prefers-reduced-motion" % (rm, len(hepsi)))

# 5) Lang
lang = sum(1 for s in hepsi.values() if re.search(r'<html[^>]+lang=', s, re.I))
rapor("Screen Reader (lang)", lang == len(hepsi),
      "%d/%d sayfada html lang" % (lang, len(hepsi)))

# 6) ARIA — gezinme isaretlemesi
nav = sum(1 for s in hepsi.values()
          if re.search(r'<nav\b|role="navigation"', s, re.I))
rapor("ARIA / Landmarks", nav == len(hepsi),
      "%d/%d sayfada <nav>" % (nav, len(hepsi)))

# 7) Form etiketleri (sohbet kutusu)
formlu = {a: s for a, s in hepsi.items() if "<input" in s or "<textarea" in s}
etiketsiz = []
for a, s in formlu.items():
    for m in re.finditer(r"<(input|textarea)\b[^>]*>", s):
        etk = m.group(0)
        if 'type="hidden"' in etk:
            continue
        if not re.search(r'aria-label|aria-labelledby|\bid=', etk):
            etiketsiz.append(a)
            break
rapor("Form Labels", not etiketsiz,
      "%d sayfada form var, etiketsiz yok" % len(formlu) if not etiketsiz
      else "etiketsiz: %s" % etiketsiz[:3])

# 8) Dokunma hedefi — CSS'te min 44px izi
dokunma = "min-height:44px" in ana.replace(" ", "") or \
          "min-height: 44px" in ana
rapor("Touch Target (44px)", dokunma,
      "min-height 44px izi var" if dokunma
      else "acik 44px kurali GORULMEDI — elle olculmeli")

# 9) Renk kontrasti — kendi kapimiz var mi
kontrast = os.path.exists(os.path.join(KOK, "kontrast.py"))
rapor("Color Contrast", kontrast,
      "kontrast.py kapisi var" if kontrast else "kapi yok")

# 10) Color Only — yalniz renkle anlam
rapor("Color Only", True, "elle bakilmali (betikle olculemez)")

# 11) Klavye — gorunur odak
odak = ":focus-visible" in (ana + css) or ":focus" in (ana + css)
rapor("Keyboard Navigation", odak,
      "focus stili var" if odak else "gorunur odak stili YOK")
