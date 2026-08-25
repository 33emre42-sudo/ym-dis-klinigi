#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FAQ şemasını mevcut görünür sorulardan üretir ve sayfalara yayar.

    python faq-sema-yay.py            # ne değişecek, yazar (kuru koşu)
    python faq-sema-yay.py --uygula   # uygular

NEDEN VAR — 25 Ağustos 2026'da ölçüldü (K84):

35 bilgi sayfasında toplam 107 soru-cevap çifti GÖRÜNÜR metin olarak
zaten yayında; ancak yalnız 1 sayfada (sik-sorulan-sorular.html)
FAQPage şeması var. Google zengin sonuç ve AI Overview/ChatGPT gibi
cevap motorları soru-cevap içeriğini makine okunur FAQPage şemasından
çok daha güvenilir çeker. 2026 ölçümlerinde FAQ şeması CTR'a ve AI
cevaplarında alıntılanmaya somut katkı sağlıyor.

⛔ YENİ İDDİA ÜRETMEZ. Şemaya giren her soru ve cevap, sayfada ZATEN
görünür olan metnin aynısıdır. Bu betik metin YAZMAZ; yalnız var olan
"Sık sorulanlar" bölümünü JSON-LD'ye çevirir. Görünür içerikle şema
içeriği bire bir aynı kalır — Google'ın FAQ politikasının şartı budur.

⛔ DEĞERLER ELLE YAZILMAZ. Kaynak, sayfanın kendi <h2
id="sik-sorulanlar"> bölümündeki <p><strong>"Soru?"</strong> Cevap</p>
kalıbıdır. Sayfa güncellenince betik yeniden koşar; şema görünür
metinden yeniden üretilir, bayatlamaz.

Kalıp (bilgi sayfası şablonunun standart FAQ bölümü):

    <h2 id="sik-sorulanlar">Sık sorulanlar</h2>
    <p><strong>"Soru metni?"</strong>
       Cevap metni.</p>
"""
import glob
import html as html_mod
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

KOK = os.path.dirname(os.path.abspath(__file__))
ISARET = "<!-- faq-semasi: faq-sema-yay.py uretir, ELLE DUZENLEME -->"
BLOK = re.compile(
    r'\n?' + re.escape(ISARET) +
    r'\n<script type="application/ld\+json">.*?</script>', re.S)

# Mekanik yayin kapisinin (mekanik-kapi-yayin.py YASAK_DIFF_DESEN) otomatik
# seritte yasakladigi desenlerin kopyasi. Bu desenlerden birini iceren
# soru-cevap cifti SEMAYA GIRMEZ; boylece uretilen diff otomatik yayin
# kapisindan gecebilir. Gorunur metin degismez — sema, gorunur icerigin
# kapi-uyumlu ALT KUMESIDIR (Google FAQ politikasi alt kumeye izin verir).
# Kaynak listeyle senkron tutulmali; senkron bozulursa kapi zaten durdurur.
KAPI_YASAK = [
    r"112",
    r"\bacil\b",
    r"\bbayil",
    r"\bkanama\b",
    r"\btitreme\b",
    r"\bates\b|\bateş\b",
    r"\bTL\b|\b₺|\bfiyat|\bucret|\bücret|\bindirim|\bkampanya",
    r"\bgaranti|\bkesin sonuc|\bkesin sonuç|\bagrisiz|\bağrısız",
    r"\ben iyi\b|\ben basarili|\ben başarılı|\buzman kadro|\blider\b",
    r"\byorum|\böncesi-sonrası|\boncesi-sonrasi|\bhasta memnuniyet",
]


def kapiya_uygun(metin):
    dusuk = metin.lower()
    return not any(re.search(desen, dusuk) for desen in KAPI_YASAK)


def _oku(yol):
    with io.open(yol, encoding="utf-8") as f:
        return f.read()


def _yaz(yol, icerik):
    with io.open(yol, "w", encoding="utf-8", newline="") as f:
        f.write(icerik)


def _duz_metin(parca):
    """HTML parçasını düz metne indirger (etiketler + fazla boşluk gider)."""
    parca = re.sub(r"<[^>]+>", " ", parca)
    parca = html_mod.unescape(parca)
    return re.sub(r"\s+", " ", parca).strip()


def sorulari_cikar(sayfa_metni):
    """Sayfanın 'Sık sorulanlar' bölümündeki görünür soru-cevapları döner."""
    bolum = re.search(
        r'<h2 id="sik-sorulanlar">.*?</h2>(.*?)(?=<h2 |<div class="cagri"|</article>)',
        sayfa_metni, re.S)
    if not bolum:
        return []
    ciftler = []
    for soru_ham, cevap_ham in re.findall(
            r"<p><strong>(.*?)</strong>(.*?)</p>", bolum.group(1), re.S):
        soru = _duz_metin(soru_ham).strip('"“”„«»')
        cevap = _duz_metin(cevap_ham)
        if "?" not in soru or len(soru) < 10 or len(cevap) < 20:
            continue
        # GUVENLIK: mekanik yayin kapisinin yasakladigi deseni (112, acil,
        # kanama, fiyat...) iceren cift semaya girmez — bkz. KAPI_YASAK.
        if not kapiya_uygun(soru + " " + cevap):
            continue
        ciftler.append((soru, cevap))
    return ciftler


def faq_dugumu(url, ciftler):
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "@id": url + "#faq",
        "inLanguage": "tr",
        "mainEntity": [
            {
                "@type": "Question",
                "name": soru,
                "acceptedAnswer": {"@type": "Answer", "text": cevap},
            }
            for soru, cevap in ciftler
        ],
    }


def sayfa_url(dosya):
    return "https://ymdisklinigi.com/" + dosya


def isle(dosya, uygula):
    metin = _oku(os.path.join(KOK, dosya))
    if "FAQPage" in BLOK.sub("", metin):
        return "atlandi-baska-faq"
    ciftler = sorulari_cikar(metin)
    if not ciftler:
        return "atlandi-soru-yok"
    dugum = faq_dugumu(sayfa_url(dosya), ciftler)
    script = (ISARET + '\n<script type="application/ld+json">\n' +
              json.dumps(dugum, ensure_ascii=False,
                         separators=(",", ":")) + "\n</script>")
    yeni = BLOK.sub("", metin)
    if "</head>" not in yeni:
        return "atlandi-head-yok"
    yeni = yeni.replace("</head>", script + "\n</head>", 1)
    if yeni == metin:
        return "guncel"
    if uygula:
        _yaz(os.path.join(KOK, dosya), yeni)
    return f"{len(ciftler)} soru"


def main():
    uygula = "--uygula" in sys.argv
    print("=" * 68)
    print("FAQ SEMASINI SAYFALARA YAY" + ("" if uygula else "   (KURU KOSU)"))
    print("=" * 68)
    eklendi = 0
    for dosya in sorted(glob.glob(os.path.join(KOK, "*.html"))):
        ad = os.path.basename(dosya)
        if ad == "404.html":
            continue
        sonuc = isle(ad, uygula)
        if sonuc.endswith("soru"):
            eklendi += 1
            print(f"  {'EKLENDI' if uygula else 'EKLENECEK':10s} {ad}: {sonuc}")
        elif sonuc == "guncel":
            print(f"  {'GUNCEL':10s} {ad}")
    print(f"\n  toplam: {eklendi} sayfa")
    return 0


if __name__ == "__main__":
    sys.exit(main())
