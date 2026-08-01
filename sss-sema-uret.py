#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SSS SEMASINI SAYFADAN URETIR.

    python sss-sema-uret.py

Neden var: Google, FAQPage semasindaki cevabin sayfada GORUNUR olmasini
sart kosuyor. Semayi elle yazinca metinler kaciyor — 1 Agu 2026'daki
Codex denetiminde tam bu yakalandi ve `denetle.py` artik iki metni
karakter karakter karsilastiriyor.

Bu betik iliskiyi tersine cevirir: sema ARTIK ELLE YAZILMAZ.
`sik-sorulan-sorular.html` icindeki <details class="sss-ogesi"> bloklari
okunur, ayni duzlestirme kurallariyla (denetle.py ile birebir ayni)
metne cevrilir ve FAQPage blogu yeniden yazilir.

Yeni soru eklerken: sadece HTML'e ekleyin, sonra bu betigi calistirin.
"""
import html as html_mod
import io
import json
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

SAYFA = "sik-sorulan-sorular.html"


def duzlestir(metin):
    """denetle.py icindeki fonksiyonun AYNISI. Ikisi ayrisirsa denetim
    kalir — degistirirken iki dosyayi birlikte degistirin."""
    metin = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", metin,
                   flags=re.S | re.I)
    metin = re.sub(r"<[^>]+>", " ", metin)
    metin = html_mod.unescape(metin)
    return re.sub(r"\s+", " ", metin).strip()


with io.open(SAYFA, encoding="utf-8") as f:
    html = f.read()

ogeler = re.findall(
    r'<details class="sss-ogesi">\s*<summary>(.*?)</summary>\s*'
    r'<div class="sss-cevap">(.*?)</div>\s*</details>', html, re.S)

if not ogeler:
    print("HATA: %s icinde SSS ogesi bulunamadi." % SAYFA)
    sys.exit(1)

sorular = []
for soru, cevap in ogeler:
    sorular.append({
        "@type": "Question",
        "name": duzlestir(soru),
        "acceptedAnswer": {"@type": "Answer", "text": duzlestir(cevap)},
    })

# Ayni soru iki kez yazilmis olabilir — sema tarafinda sessizce
# birlesirdi, denetim de "sayi esit degil" derdi. Burada acikca soyle.
adlar = [q["name"] for q in sorular]
tekrar = sorted({a for a in adlar if adlar.count(a) > 1})
if tekrar:
    print("HATA: ayni soru birden fazla kez var:")
    for t in tekrar:
        print("   - %s" % t)
    sys.exit(1)

sema = {"@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": sorular}
yeni_blok = ('<script type="application/ld+json">\n%s\n</script>'
             % json.dumps(sema, ensure_ascii=False, indent=None,
                          separators=(",", ":")))

desen = re.compile(
    r'<script type="application/ld\+json">\s*\{[^<]*?"@type"\s*:\s*"FAQPage".*?</script>',
    re.S)
if not desen.search(html):
    print("HATA: %s icinde FAQPage blogu bulunamadi." % SAYFA)
    sys.exit(1)

yeni_html = desen.sub(lambda m: yeni_blok, html, count=1)

if yeni_html == html:
    print("Degisiklik yok — sema zaten guncel. (%d soru)" % len(sorular))
else:
    with io.open(SAYFA, "w", encoding="utf-8", newline="\n") as f:
        f.write(yeni_html)
    print("FAQPage semasi yeniden yazildi — %d soru." % len(sorular))

for q in sorular:
    print("  · %s" % q["name"][:66])
