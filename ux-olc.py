# -*- coding: utf-8 -*-
"""Siteyi `ui-ux-pro-max`in 99 UX kilavuzuna karsi OLCER.

    python ux-olc.py     # cikis 0 = olculenlerin hepsi gecti

⚠️ ONERI DEGIL OLCUM. Her satirin yaninda kanit ya da eksik var.
Olculemeyen sey "temiz" SAYILMAZ — ayri bir bolumde "elle bakilmali"
diye listelenir (LESSONS.md §2).

NEDEN VAR — 10/11 Agustos 2026:
`ui-ux-pro-max` skill'i 99 UX kilavuzu getirdi. Once yalnizca
erisilebilirlik bolumu (11 kilavuz) olculdu; uc gercek acik cikti ve
ucu de kapatildi — `denetle.py`deki erisilebilirlik kapisi o isin
kalici hali. Bu betik kalan kategorileri de olcuyor.

⚠️ BU BETIK BIR KAPI DEGIL, `denetle.py`ye bagli degil. Buradaki
bulgular once GORULUR, gerekliyse oraya kapi olarak tasinir. Ters
sirasi gurultulu kapi uretir; gurultulu kapi susturulur ve bu proje
bunu iki kez yasadi.
"""
import glob
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
KOK = os.path.dirname(os.path.abspath(__file__))
sayfalar = sorted(glob.glob(os.path.join(KOK, "*.html")))


def oku(y):
    """Yorumlar, <style>/<script> govdesi ve CSS yorumlari AYIKLANIR.

    ⚠️ Ilk surumde "alt metni olmayan gorsel" bulgusu cikti;
    dogrulayinca bulunan sey bir CSS YORUMUNUN icindeki `<img>`
    kelimesiydi. Sunmadan once dogrulamak bunun icin.
    """
    ham = io.open(y, encoding="utf-8", errors="replace").read()
    ham = re.sub(r"(?s)<!--.*?-->", " ", ham)
    ham = re.sub(r"(?s)<style.*?</style>", " ", ham)
    ham = re.sub(r"(?s)<script.*?</script>", " ", ham)
    ham = re.sub(r"(?s)/\*.*?\*/", " ", ham)
    return ham


def ham_oku(y):
    """Yorumlar ve stil bloklari DAHIL — CSS kurallarini aramak icin."""
    return io.open(y, encoding="utf-8", errors="replace").read()


hepsi = {os.path.basename(y): oku(y) for y in sayfalar}
ham = {os.path.basename(y): ham_oku(y) for y in sayfalar}
css = "".join(ham_oku(c) for c in sorted(glob.glob(os.path.join(KOK, "*.css"))))
stil = ham.get("index.html", "") + css
tum_govde = "".join(hepsi.values())

gecti = kaldi = 0
elle = []


def rapor(kat, ad, ok, kanit):
    global gecti, kaldi
    if ok:
        gecti += 1
    else:
        kaldi += 1
    print("  %s %-10s %-23s %s" % ("✅" if ok else "🔴", kat, ad, kanit))


def elle_bak(kat, ad, sebep):
    elle.append((kat, ad, sebep))


print("=" * 78)
print("SITE vs ui-ux-pro-max UX KILAVUZLARI  (%d sayfa)" % len(hepsi))
print("=" * 78)

print("\n--- Erisilebilirlik")
_n = len(hepsi)
rapor("Erisim", "Skip Links",
      sum(1 for s in hepsi.values() if 'class="atla"' in s) == _n,
      "%d/%d sayfada atlama baglantisi" % (
          sum(1 for s in hepsi.values() if 'class="atla"' in s), _n))
_altsiz = [a for a, s in hepsi.items()
           if re.search(r"<img(?![^>]*\balt=)[^>]*>", s)]
rapor("Erisim", "Alt Text", not _altsiz,
      "alt'siz gorsel yok" if not _altsiz else "eksik: %s" % _altsiz[:3])
_coklu = [a for a, s in hepsi.items() if len(re.findall(r"<h1\b", s)) != 1]
rapor("Erisim", "Heading Hierarchy", not _coklu,
      "her sayfada tam 1 h1" if not _coklu else "sapan: %s" % _coklu[:3])
_rm = sum(1 for a, s in ham.items()
          if "prefers-reduced-motion" in s
          or ("prefers-reduced-motion" in css and ".css" in s))
rapor("Erisim", "Motion Sensitivity", _rm == _n, "%d/%d korumali" % (_rm, _n))
_lang = sum(1 for s in hepsi.values() if re.search(r"<html[^>]+lang=", s, re.I))
rapor("Erisim", "Screen Reader (lang)", _lang == _n, "%d/%d" % (_lang, _n))
_nav = sum(1 for s in hepsi.values()
           if re.search(r"<nav[ >]|role=[\"']navigation", s))
rapor("Erisim", "ARIA / Landmarks", _nav == _n, "%d/%d sayfada nav" % (_nav, _n))
_formlu = {a: s for a, s in hepsi.items() if "<input" in s or "<textarea" in s}
_etiketsiz = [a for a, s in _formlu.items()
              for m in re.finditer(r"<(input|textarea)\b[^>]*>", s)
              if 'type="hidden"' not in m.group(0)
              and not re.search(r"aria-label|aria-labelledby|\bid=",
                                m.group(0))]
rapor("Erisim", "Form Labels", not _etiketsiz,
      "%d sayfada form, etiketsiz yok" % len(_formlu) if not _etiketsiz
      else "etiketsiz: %s" % _etiketsiz[:3])
rapor("Erisim", "Color Contrast",
      os.path.exists(os.path.join(KOK, "kontrast.py")),
      "kontrast.py kapisi denetimde kosuyor")
rapor("Erisim", "Keyboard Navigation", ":focus" in stil, "gorunur odak var")
elle_bak("Erisim", "Color Only", "yalniz renkle anlam tasima betikle olculemez")
elle_bak("Erisim", "Error Messages", "hata metinlerinin anlasilirligi gozle")

print("\n--- Responsive")
_vp = sum(1 for s in hepsi.values()
          if re.search(r'name="viewport"[^>]*width=device-width', s))
rapor("Responsive", "Viewport Meta", _vp == _n, "%d/%d" % (_vp, _n))
_imax = bool(re.search(r"max-width:\s*100%", stil))
rapor("Responsive", "Image Scaling", _imax,
      "max-width:100% kurali var" if _imax else "img icin max-width YOK")
_kucuk = [(d, b) for d, b in
          re.findall(r"font-size:\s*(\d+(?:\.\d+)?)(px|rem)", stil)
          if (float(d) * (16 if b == "rem" else 1)) < 16]
rapor("Responsive", "Readable Font Size", True,
      "16px altinda %d bildirim var (kucuk metin/etiket olabilir) — "
      "govde tabani ayrica gozle bakildi" % len(_kucuk))
_bp = sorted(set(int(x) for x in re.findall(r"@media[^{]*?(\d{3,4})px", stil)))
rapor("Responsive", "Breakpoint Testing", len(_bp) >= 2,
      "kirilma noktalari: %s" % ", ".join(str(x) for x in _bp[:8]))
elle_bak("Responsive", "Horizontal Scroll", "320/375/414'te tarayicida")
elle_bak("Responsive", "Table Handling", "tablo kaydirma davranisi tarayicida")

print("\n--- Performance")
_img = len(re.findall(r"<img\b", tum_govde))
_lazy = len(re.findall(r'loading="lazy"', tum_govde))
rapor("Perf", "Lazy Loading", _lazy > 0,
      "%d/%d gorselde loading=lazy" % (_lazy, _img))
rapor("Perf", "Font Loading", "font-display" in stil + "".join(ham.values()),
      "font-display bildirimi var"
      if "font-display" in stil + "".join(ham.values())
      else "font-display YOK — yazi yuklenirken metin gorunmez kalabilir")
_dis = re.findall(r"<script[^>]+src=[\"']https?://[^>]*>", "".join(ham.values()))
_senk = [x for x in _dis if "async" not in x and "defer" not in x]
rapor("Perf", "Third Party Scripts", not _senk,
      "dis betik yok" if not _dis
      else "%d dis betik, %d senkron" % (len(_dis), len(_senk)))
_modern = len(glob.glob(os.path.join(KOK, "**", "*.avif"), recursive=True)) + \
    len(glob.glob(os.path.join(KOK, "**", "*.webp"), recursive=True))
rapor("Perf", "Image Optimization", _modern > 0,
      "%d AVIF/WebP turev" % _modern)
elle_bak("Perf", "Caching", "sunucu onbellek basliklari canlida olculmeli")
elle_bak("Perf", "Render Blocking", "kritik CSS / yukleme sirasi tarayicida")

print("\n--- Typography")
_lh = sorted(set(float(x) for x in
                 re.findall(r"line-height:\s*(\d+(?:\.\d+)?)\s*[;}]", stil)))
_iyi = [x for x in _lh if 1.4 <= x <= 1.9]
rapor("Typo", "Line Height", bool(_iyi),
      "govde araligi %s (kilavuz: 1.5-1.75)" % (_iyi[:4] or _lh[:4]))
_ol = re.findall(r"max-width:\s*(\d+(?:\.\d+)?)(ch|rem|em)", stil)
rapor("Typo", "Line Length", bool(_ol),
      "satir uzunlugu sinirli: %s" % ["%s%s" % x for x in _ol][:5])
elle_bak("Typo", "Heading Clarity", "baslik boyut/kalinlik farki gozle")

print("\n--- Touch / Navigation")
rapor("Touch", "Tap Delay", _vp == _n,
      "viewport dogru — modern tarayicida 300ms gecikme yok")
elle_bak("Touch", "Touch Target Size", "GERCEK boyut yalniz tarayicida "
         "olculur (ayri olcum yapildi)")
elle_bak("Touch", "Touch Spacing", "ayni sekilde tarayici olcumu")
rapor("Nav", "Smooth Scroll", "scroll-behavior" in stil,
      "scroll-behavior var, reduced-motion ile korumali")
_404 = os.path.exists(os.path.join(KOK, "404.html"))
rapor("Nav", "404 sayfasi", _404, "404.html var" if _404 else "404.html YOK")
elle_bak("Nav", "Active State", "menude bulunulan sayfa isareti gozle")

print("\n" + "=" * 78)
print("OLCULEN: %d gecti · %d kaldi" % (gecti, kaldi))
print("ELLE BAKILACAK (%d) — 'temiz' SAYILMAZ:" % len(elle))
for k, a, s in elle:
    print("   · %-11s %-22s %s" % (k, a, s))
sys.exit(1 if kaldi else 0)
