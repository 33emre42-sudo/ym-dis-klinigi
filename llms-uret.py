#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`llms.txt` uretir — yapay zeka tarayicilari icin icerik haritasi.

    python llms-uret.py            # ne degisecek, yazar
    python llms-uret.py --uygula   # uygular

NEDEN VAR — 9 Agustos 2026'da olculdu:

ChatGPT'ye "Bagcilar'da gece acik dis klinigi" diye sorulunca bizi
ONERMIYOR; dort rakibi oneriyor ve biri gece acik bile degil. Site
teknik olarak taranabilir durumda (butun AI tarayicilari 200 aliyor,
`X-Robots-Tag` yok) ama yapay zeka motorlarinin okudugu ICERIK
HARITASI yoktu: `/llms.txt` 404 donuyordu.

Rakip ozbudent.com bunu kurmus. Kurmayan biziz.

⛔ ICERIK UYDURULMAZ: her satir sayfanin KENDI `<title>` ve
`<meta name="description">` degerinden gelir. Bolumler de sitenin
kendi kaynagindan turetilir (`bilgi-yazilari.html` hangi sayfalarin
bilgi yazisi oldugunu zaten soyluyor) — buraya elle liste GOMULMEZ,
yoksa sayfa eklendiginde harita sessizce bayatlar.

⚠️ RAKIBIN HATASINA DUSME: ozbudent'in `llms-full.txt` dosyasinin
%6'si yanlislikla CSS ve JavaScript dolmus. Biz tam metin surumu
URETMIYORUZ; yalnizca baslik + aciklama haritasi. Gerekirse govde
cikarilirken `<script>`/`<style>` MUTLAKA atilmali.

MEVZUAT: metinde fiyat/kampanya/garanti/uzmanlik iddiasi gecemez.
"24 saat acik" YAZILIR — kanunun izin verdigi "calisma gun ve
saatleri" kalemi ve tek gercek ustunlugumuz.
"""
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

KOK = os.path.dirname(os.path.abspath(__file__))
SITE = "https://ymdisklinigi.com/"
CIKTI = os.path.join(KOK, "llms.txt")

# Acil/gece kumesi: baslik ya da aciklamada bu desen geciyorsa yazi
# "Acil ve gece" bolumune duser. Sabit dosya listesi DEGIL, desen —
# yeni bir gece yazisi eklendiginde kendiliginden dogru yere gider.
ACIL_DESEN = re.compile(r"gece|acil|nöbetçi|apse|kırıl|şişlik|düştü",
                        re.I)

BASLIK = "YM Diş Kliniği"
OZET = (
    "Bağcılar Kirazlı'da, Mevlana Caddesi üzerinde ağız ve diş sağlığı "
    "kliniği. Hafta sonu ve resmî tatiller dahil **her gün 24 saat "
    "açık**. İki genel diş hekimi: Dt. Yunus Emre Çetin ve "
    "Dt. Mert Daştan. Adres: Kirazlı Mah. Mevlana Cad. No: 47 D, "
    "Bağcılar / İstanbul. Telefon: 0541 732 43 76. Kirazlı Metro'ya "
    "yürüme mesafesinde."
)

DILLER = ("en", "es", "fr", "de", "ru")


def _oku(yol):
    return io.open(yol, encoding="utf-8").read()


def _yerel_dosya(loc):
    """Sitemap URL'inden diskteki dosyayi bulur (sitemap-tazele ile ayni)."""
    y = loc[len(SITE):] if loc.startswith(SITE) else loc
    if y in ("", "/"):
        y = "index.html"
    elif y.endswith("/"):
        y += "index.html"
    p = os.path.join(KOK, y.replace("/", os.sep))
    return p if os.path.exists(p) else None


def _alan(s, desen):
    m = re.search(desen, s, re.I | re.S)
    if not m:
        return ""
    # HTML varliklarini sadelestir; satir sonlarini tek bosluga indir
    t = re.sub(r"\s+", " ", m.group(1)).strip()
    return (t.replace("&amp;", "&").replace("&#8220;", "“")
             .replace("&#8221;", "”").replace("&quot;", '"'))


def _bilgi_yazilari():
    """Bilgi yazisi olan sayfalar — SITENIN KENDI dizininden.

    Elle liste tutmak yerine `bilgi-yazilari.html`i okuyoruz: yeni yazi
    eklenince dizine zaten ekleniyor (denetle.py bunu ayrica dogruluyor),
    dolayisiyla harita da kendiliginden dogru kaliyor.
    """
    yol = os.path.join(KOK, "bilgi-yazilari.html")
    if not os.path.exists(yol):
        return set()
    s = _oku(yol)
    # ⚠️ TUM sayfadan baglanti cekmek YANLIS: menu ve altbilgi de
    # `.html` baglantisi tasiyor, kurumsal sayfalar "bilgi yazisi"
    # sayiliyor ve Kurumsal bolumu bosaliyordu (ilk kosuda 1 URL).
    # Yalniz yazi listesini tasiyan kapsayici okunur.
    kutular = re.findall(r'<div class="dizin-yazi".*?(?=<div class="dizin-yazi"|</main)',
                         s, re.S)
    if not kutular:
        return set()
    yazilar = set(re.findall(r'href="([a-z0-9-]+\.html)"',
                             " ".join(kutular)))
    # ⚠️ MENUDE gecen sayfa bilgi yazisi DEGIL, kurumsal sayfadir.
    # Ilk kosuda `sik-sorulan-sorular.html` dizin kapsayicisindan
    # sizip "Acil ve gece" bolumune dusmustu (aciklamasinda "gece
    # dis agrisi" gectigi icin). Menu, kurumsal/yazi ayriminin
    # sitedeki dogal kaynagi.
    menu = re.search(r'<nav class="menu".*?</nav>', s, re.S)
    if menu:
        yazilar -= set(re.findall(r'href="([a-z0-9-]+\.html)"',
                                  menu.group(0)))
    return yazilar


def topla():
    sm = _oku(os.path.join(KOK, "sitemap.xml"))
    urller = re.findall(r"<loc>([^<]+)</loc>", sm)
    yazilar = _bilgi_yazilari()

    bolum = {"Acil ve gece": [], "Bilgi yazıları": [],
             "Kurumsal": [], "Other languages": []}
    atlanan = []
    for u in urller:
        p = _yerel_dosya(u)
        if not p:
            atlanan.append(u)
            continue
        s = _oku(p)
        baslik = _alan(s, r"<title>(.*?)</title>")
        acik = _alan(s, r'<meta name="description" content="(.*?)"')
        ad = os.path.basename(p)
        dil = u[len(SITE):].split("/")[0]

        if dil in DILLER:
            hedef = "Other languages"
        elif ad in yazilar and ACIL_DESEN.search(baslik + " " + acik):
            hedef = "Acil ve gece"
        elif ad in yazilar:
            hedef = "Bilgi yazıları"
        else:
            hedef = "Kurumsal"
        bolum[hedef].append((baslik, u, acik))
    return bolum, atlanan


def uret():
    bolum, atlanan = topla()
    p = ["# %s" % BASLIK, "", "> %s" % OZET, ""]
    for ad in ("Acil ve gece", "Kurumsal", "Bilgi yazıları",
               "Other languages"):
        satirlar = bolum[ad]
        if not satirlar:
            continue
        p.append("## %s" % ad)
        for baslik, u, acik in satirlar:
            p.append("- [%s](%s): %s" % (baslik, u, acik))
        p.append("")
    return "\n".join(p).rstrip() + "\n", bolum, atlanan


def main():
    uygula = "--uygula" in sys.argv
    metin, bolum, atlanan = uret()

    print("=" * 66)
    print("llms.txt URETIMI")
    print("=" * 66)
    for ad, satirlar in bolum.items():
        if satirlar:
            print("  %-18s %3d URL" % (ad, len(satirlar)))
    if atlanan:
        print("  ⚠️ diskte bulunamayan %d URL: %s"
              % (len(atlanan), ", ".join(atlanan[:3])))
    print("  toplam            %3d URL · %d bayt"
          % (sum(len(v) for v in bolum.values()), len(metin.encode("utf-8"))))

    eski = _oku(CIKTI) if os.path.exists(CIKTI) else None
    if eski == metin:
        print("\n  Zaten guncel — yapacak bir sey yok.")
        return 0
    if not uygula:
        print("\n  %s — uygulamak icin --uygula"
              % ("DEGISECEK" if eski is not None else "OLUSTURULACAK"))
        return 0
    io.open(CIKTI, "w", encoding="utf-8", newline="\n").write(metin)
    print("\n  YAZILDI: llms.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
