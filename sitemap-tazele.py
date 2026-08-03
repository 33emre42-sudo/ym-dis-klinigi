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

⛔ Tarih UYDURMAZ: dosyanın gerçek değiştirilme zamanını okur.
"""
import io
import os
import re
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
KOK = os.path.dirname(os.path.abspath(__file__))
SITE = "https://ymdisklinigi.com/"


def yerel_dosya(loc):
    """Sitemap URL'inden diskteki dosyayı bulur.

    Her dilin ana sayfası TEMİZ ADRESLE yayımlanıyor (`/`, `/en/`);
    diskteki karşılığı `index.html` / `en/index.html`.
    """
    yol = loc[len(SITE):] if loc.startswith(SITE) else loc
    if yol == "" or yol == "/":
        yol = "index.html"
    elif yol.endswith("/"):
        yol = yol + "index.html"
    p = os.path.join(KOK, yol.replace("/", os.sep))
    return p if os.path.exists(p) else None


def main():
    uygula = "--uygula" in sys.argv
    p = os.path.join(KOK, "sitemap.xml")
    s = io.open(p, encoding="utf-8").read()

    degisen, bulunamayan = [], []

    def yenile(m):
        loc, lastmod = m.group(2), m.group(4)
        y = yerel_dosya(loc)
        if not y:
            bulunamayan.append(loc)
            return m.group(0)
        gercek = time.strftime("%Y-%m-%d", time.localtime(os.path.getmtime(y)))
        if gercek == lastmod:
            return m.group(0)
        degisen.append((loc, lastmod, gercek))
        return m.group(1) + loc + m.group(3) + gercek + m.group(5)

    yeni = re.sub(r"(<loc>)([^<]+)(</loc>\s*<lastmod>)([^<]+)(</lastmod>)",
                  yenile, s)

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
        io.open(p, "w", encoding="utf-8", newline="").write(yeni)
        print("  YAZILDI.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
