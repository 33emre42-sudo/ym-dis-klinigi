#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DIS KAYNAK KONTROLU TESTI — gizlilik sozu gercekten korunuyor mu?

    python test-dis-kaynak.py

Gizlilik sayfamiz su sozu veriyor: "Sayfayi actiginizda tarayiciniz
hicbir ucuncu taraf sunucusuna istek gondermez." Bu iddiayi koruyan
kontrol `denetle.py` icinde.

3. turda o kontrol yalnizca .css ve font uzantilarina bakiyordu.
4. turda ise icon/apple-touch-icon/mask-icon/manifest iliskileri,
style="" oznitelikleri ve SVG image/use kaynaklari eksikti.

Bu test her kaynak turu icin bir KIRMIZI (yakalanmali) ve gerektiginde
bir YESIL (yanlis alarm vermemeli) ornek tutar.
"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# denetle.py ice aktarilinca butun denetimi calistirir; bu yuzden
# yalnizca ihtiyacimiz olan parcayi kendimiz kuruyoruz.
import re                                        # noqa: E402
from html.parser import HTMLParser               # noqa: E402

_YERLI = re.compile(r"^(?:https?:)?//(?:www\.)?ymdisklinigi\.com", re.I)


def _dis_mi(deger):
    d = (deger or "").strip()
    if not d or d.startswith(("data:", "#", "mailto:", "tel:")):
        return False
    if d.startswith(("//", "http://", "https://")):
        return not _YERLI.match(d)
    return False


class _KaynakToplayici(HTMLParser):
    HEDEF = {"script": ("src",), "img": ("src", "srcset"),
             "source": ("src", "srcset"), "iframe": ("src",),
             "video": ("src", "poster"), "audio": ("src",),
             "embed": ("src",), "object": ("data",),
             "track": ("src",), "input": ("src",),
             "image": ("href", "xlink:href"),
             "use": ("href", "xlink:href")}
    YUKLEYEN_REL = ("stylesheet", "preload", "prefetch", "preconnect",
                    "modulepreload", "dns-prefetch", "icon",
                    "apple-touch-icon", "mask-icon", "manifest")

    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.dis = []

    def handle_starttag(self, etiket, oznitelikler):
        d = {k.lower(): (v or "") for k, v in oznitelikler}
        for oz in self.HEDEF.get(etiket, ()):
            for parca in re.split(r"\s*,\s*", d.get(oz, "")):
                aday = parca.split()[0] if parca.split() else ""
                if _dis_mi(aday):
                    self.dis.append("%s[%s]" % (etiket, oz))
        if etiket == "link":
            rel = (d.get("rel") or "").lower()
            if any(r in rel.split() for r in self.YUKLEYEN_REL):
                if _dis_mi(d.get("href")):
                    self.dis.append("link[%s]" % rel)
        for m in re.finditer(r"url\(\s*['\"]?([^'\")]+)", d.get("style", "")):
            if _dis_mi(m.group(1)):
                self.dis.append("style url()")

    def handle_startendtag(self, e, o):
        self.handle_starttag(e, o)

    def error(self, m):
        pass


def dis_kaynaklar(s_):
    t = _KaynakToplayici()
    try:
        t.feed(s_)
        t.close()
    except Exception:
        pass
    b = list(t.dis)
    for css in re.findall(r"<style[^>]*>(.*?)</style>", s_, re.S | re.I):
        for m in re.finditer(r"@import\s+(?:url\()?['\"]?([^'\")\s]+)", css):
            if _dis_mi(m.group(1)):
                b.append("@import")
        for m in re.finditer(r"url\(\s*['\"]?([^'\")]+)", css):
            if _dis_mi(m.group(1)):
                b.append("css url()")
    return b


sonuc = []


def bekle(ad, govde, yakalanmali):
    html = ("<!DOCTYPE html><html><head><title>T</title>%s</head>"
            "<body>%s</body></html>"
            % (govde if "<link" in govde or "<style" in govde else "",
               "" if "<link" in govde or "<style" in govde else govde))
    b = dis_kaynaklar(html)
    gecti = bool(b) == yakalanmali
    sonuc.append((ad, gecti,
                  "" if gecti else "BULUNAN: %s" % (b or "temiz")))


D = "https://kotu-ucuncu-taraf.example"

# --- KIRMIZI: hepsi yakalanmali ---
bekle("script src", '<script src="%s/a.js"></script>' % D, True)
bekle("img src", '<img src="%s/a.jpg">' % D, True)
bekle("img srcset", '<img srcset="%s/a.webp 1x, %s/b.webp 2x">' % (D, D), True)
bekle("iframe src", '<iframe src="%s/x"></iframe>' % D, True)
bekle("video poster", '<video poster="%s/p.jpg"></video>' % D, True)
bekle("audio src", '<audio src="%s/a.mp3"></audio>' % D, True)
bekle("object data", '<object data="%s/o.swf"></object>' % D, True)
bekle("link stylesheet", '<link rel="stylesheet" href="%s/a.css">' % D, True)
bekle("link preload", '<link rel="preload" href="%s/f.woff2" as="font">' % D, True)
# 4. tur b5 — bunlar eksikti:
bekle("link icon (b5)", '<link rel="icon" href="%s/f.png">' % D, True)
bekle("link apple-touch-icon (b5)",
      '<link rel="apple-touch-icon" href="%s/t.png">' % D, True)
bekle("link mask-icon (b5)", '<link rel="mask-icon" href="%s/m.svg">' % D, True)
bekle("link manifest (b5)", '<link rel="manifest" href="%s/m.json">' % D, True)
bekle("style oznitelik url() (b5)",
      '<div style="background:url(%s/bg.jpg)">x</div>' % D, True)
bekle("SVG image href (b5)",
      '<svg><image href="%s/i.png"/></svg>' % D, True)
bekle("SVG use href (b5)", '<svg><use href="%s/s.svg#a"/></svg>' % D, True)
bekle("CSS @import", '<style>@import url("%s/a.css");</style>' % D, True)
bekle("CSS url()", '<style>body{background:url(%s/b.jpg)}</style>' % D, True)

# --- YESIL: yanlis alarm vermemeli ---
bekle("yerel bagil yol", '<img src="gorsel.jpg">', False)
bekle("yerel mutlak alan", '<img src="https://ymdisklinigi.com/g.jpg">', False)
bekle("www.ymdisklinigi.com", '<script src="https://www.ymdisklinigi.com/a.js"></script>', False)
bekle("data: URI", '<img src="data:image/gif;base64,R0lGOD">', False)
bekle("tel: baglantisi", '<a href="tel:+905417324376">Ara</a>', False)
bekle("wa.me TIKLAMA baglantisi (kaynak degil)",
      '<a href="https://wa.me/905417324376">WhatsApp</a>', False)
bekle("dis harita baglantisi (tiklamayla acilir)",
      '<a href="https://maps.app.goo.gl/abc">Yol tarifi</a>', False)
bekle("yerel style url()", '<div style="background:url(desen.png)">x</div>', False)

print("=" * 70)
print("DIS KAYNAK KONTROLU — gizlilik sozu korunuyor mu?")
print("=" * 70)
g = 0
for ad, ok, n in sonuc:
    print("  %s %-44s %s" % ("GECTI " if ok else "KALDI!", ad, n))
    g += 1 if ok else 0
print("=" * 70)
print("%d/%d gecti" % (g, len(sonuc)))
sys.exit(0 if g == len(sonuc) else 1)
