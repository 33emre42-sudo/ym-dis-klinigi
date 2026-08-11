#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`llms-full.txt` üretir — yapay zekâ motorlarının okuduğu TAM METİN.

    python llms-full-uret.py            # ne değişecek, yazar
    python llms-full-uret.py --uygula   # uygular

NEDEN VAR — 9 Ağustos 2026:

Bugün kliniğe **ilk kez yapay zekâ tavsiyesiyle bir hasta geldi.**
Aynı hafta `llms.txt` yayına girmiş ve klinik şeması 78 sayfaya
yayılmıştı. Yani makine okunurluğunun ölçülebilir bir karşılığı var.

`llms.txt` bir **içerik haritası**: başlık + açıklama + adres.
`llms-full.txt` ise **metnin kendisi**. Fark önemli — bir model
"gece diş ağrısında ne yapmalıyım" sorusuna cevap ararken haritadan
hangi sayfaya bakacağını anlar, ama cevabı ancak metinden alır.

Ölçüldü: 15 rakip klinikte `llms-full.txt` **yok** (10'u ölçülebildi,
10'unda da yok). Bizde de 404 dönüyordu.

⛔ RAKİBİN HATASINA DÜŞME: ozbudent.com'un `llms-full.txt` dosyasının
**%6'sı yanlışlıkla CSS ve JavaScript** dolmuş. Bu yüzden burada
`<script>`, `<style>`, `<template>` ve gezinme/altbilgi blokları
gövde çıkarılmadan ÖNCE atılıyor ve sonuç ayrıca denetleniyor.

⛔ İÇERİK UYDURULMAZ. Her satır sayfanın kendi görünür metninden
gelir. Yeni cümle yazılmaz, özet üretilmez.

MEVZUAT: kaynak sayfalar `denetle.py`nin mevzuat taramasından zaten
geçiyor; bu dosya onların metnini taşıdığı için ayrı bir iddia
üretmiyor. Yine de "24 saat açık" bilerek korunuyor — kanunun izin
verdiği çalışma saati kalemi ve tek gerçek üstünlüğümüz.
"""
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

KOK = os.path.dirname(os.path.abspath(__file__))
SITE = "https://ymdisklinigi.com/"
CIKTI = os.path.join(KOK, "llms-full.txt")

# Gövdeden ÖNCE atılacak bloklar. Sıra önemli: script/style içeriği
# metne karışırsa rakibin düştüğü hataya düşülür.
ATILACAK_BLOK = re.compile(
    r"<(script|style|template|noscript|svg)\b.*?</\1>", re.S | re.I)
# Gezinme, altbilgi, sabit çubuk: her sayfada aynı, tekrarı gürültü.
ATILACAK_BOLUM = re.compile(
    r"<(nav|header|footer)\b.*?</\1>", re.S | re.I)

BASLIK = "YM Diş Kliniği — tam metin"
ONSOZ = (
    "Bağcılar Kirazlı'da ağız ve diş sağlığı kliniği. Hafta sonu ve "
    "resmî tatiller dahil her gün 24 saat açık. İki genel diş hekimi: "
    "Dt. Yunus Emre Çetin ve Dt. Mert Daştan. "
    "Adres: Kirazlı Mah. Mevlana Cad. No: 47 D, Bağcılar / İstanbul. "
    "Telefon: 0541 732 43 76.\n\n"
    "Bu dosya sitedeki sayfaların görünür metnini içerir. İçerik "
    "sayfalardan doğrudan alınmıştır; özetlenmemiş ve yeniden "
    "yazılmamıştır."
)

# Bu izler metinde geçiyorsa CSS/JS sızmış demektir — üretim durur.
#
# ⚠️ KELIME SINIRI ŞART. İlk yazımda düz alt dize araması vardı ve
# `"var "` izi 12 kez eşleşti — hepsi İspanyolca metnin içinde
# ("conser**var e**l diente"). Kendi kapım yanlış alarm verdi.
# Sürekli yanlış alarm veren kapı, kapatılmış kapıdır.
#
# `var` JS anahtar kelimesi olarak ARANMIYOR: Türkçede de İspanyolcada
# da çok sıradan bir dize ve gerçek bir sızıntı zaten aşağıdaki
# ötekilerden birine takılır (süslü parantez, `function(`, `document.`).
SIZINTI_IZLERI = (
    (r"[{}]", "süslü parantez (CSS/JS)"),
    (r"\bfunction\s*\(", "function("),
    (r"\d+px\b", "px ölçüsü (CSS)"),
    (r"@media\b", "@media (CSS)"),
    (r"\baddEventListener\b", "addEventListener"),
    (r"\bdocument\.(querySelector|getElementById)\b", "document.*"),
)


def _oku(yol):
    with io.open(yol, encoding="utf-8") as f:
        return f.read()


def _yerel_dosya(loc):
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
    return re.sub(r"\s+", " ", m.group(1)).strip()


def govde(s):
    """Sayfanın GÖRÜNÜR metni. script/style/nav/footer önce atılır."""
    s = ATILACAK_BLOK.sub(" ", s)
    s = ATILACAK_BOLUM.sub(" ", s)
    m = re.search(r"<main\b.*?>(.*?)</main>", s, re.S | re.I)
    if m:
        s = m.group(1)
    # ⛔ 11 AGU 2026 — IKI HATA BIRDEN. Olculdu: uretilen dosyanin
    # govde satirlarinin %44'u cumle ORTASINDA kiriliyordu ve dosyada
    # tek bir alt baslik, liste ya da kalin vurgu yoktu (### 0, "- " 0,
    # ** 0). Bu dosya YAPAY ZEKAYA DOGRUDAN servis ettigimiz tam metin;
    # 9 Agu 2026'da ilk hasta o kanaldan geldi.
    #
    # (1) KAYNAKTAKI SATIR SONLARI. HTML dosyalari 70-75 karakterde
    #     sarilarak yaziliyor; o ham satir sonlari metne aynen tasiniyor
    #     ve asagidaki bolme onlari da satir sayiyordu. Once bosluga
    #     cevriliyor — bolmeyi YALNIZCA blok sinirlari yapsin.
    #
    # (2) YAPI DUZLESIYORDU. Butun etiketler bosluga cevrildigi icin
    #     H2 basliklar, listeler ve kalin vurgular kayboluyordu.
    #     Sayfalar aslinda iyi yapilandirilmis; modelin hangi cumlenin
    #     baslik, hangisinin madde oldugunu bilmesi degerli.
    #
    # Bolme isareti NUL: HTML'de asla bulunmaz, metinle karisamaz.
    s = re.sub(r"[\r\n]+", " ", s)
    s = re.sub(r"<(strong|b)\b[^>]*>(.*?)</\1\s*>", r"**\2**",
               s, flags=re.I | re.S)
    s = re.sub(r"<h2\b[^>]*>", "\x00### ", s, flags=re.I)
    s = re.sub(r"<h3\b[^>]*>", "\x00#### ", s, flags=re.I)
    s = re.sub(r"<li\b[^>]*>", "\x00- ", s, flags=re.I)
    s = re.sub(r"</(p|li|h[1-6]|div|section|tr|summary|details)>",
               "\x00", s, flags=re.I)
    s = re.sub(r"<br\s*/?>", "\x00", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = (s.replace("&nbsp;", " ").replace("&amp;", "&")
          .replace("&lt;", "<").replace("&gt;", ">")
          .replace("&#8220;", "“").replace("&#8221;", "”")
          .replace("&quot;", '"').replace("&#39;", "'"))
    satirlar = [re.sub(r"[ \t]+", " ", x).strip() for x in s.split("\x00")]
    # Bos madde imi ("- ") ya da bos baslik ("###") birakilmaz.
    return "\n".join(x for x in satirlar if x and x.strip("#- *").strip())


def uret():
    sm = _oku(os.path.join(KOK, "sitemap.xml"))
    urller = re.findall(r"<loc>([^<]+)</loc>", sm)
    parcalar = ["# %s" % BASLIK, "", "> %s" % ONSOZ.replace("\n", "\n> "), ""]
    yazilan, atlanan = 0, []
    for u in urller:
        p = _yerel_dosya(u)
        if not p:
            atlanan.append(u)
            continue
        s = _oku(p)
        baslik = _alan(s, r"<title>(.*?)</title>")
        metin = govde(s)
        if not metin:
            atlanan.append(u + " (govde bos)")
            continue
        parcalar.append("---")
        parcalar.append("")
        parcalar.append("## %s" % (baslik or u))
        parcalar.append("URL: %s" % u)
        parcalar.append("")
        parcalar.append(metin)
        parcalar.append("")
        yazilan += 1
    return "\n".join(parcalar).rstrip() + "\n", yazilan, atlanan


def main():
    uygula = "--uygula" in sys.argv
    metin, yazilan, atlanan = uret()

    print("=" * 66)
    print("llms-full.txt URETIMI")
    print("=" * 66)
    print("  sayfa      : %d yazildi" % yazilan)
    if atlanan:
        print("  ⚠️ atlanan : %d — %s" % (len(atlanan), ", ".join(atlanan[:3])))
    print("  boyut      : %d bayt (%.0f KB)"
          % (len(metin.encode("utf-8")), len(metin.encode("utf-8")) / 1024.0))

    # ⛔ SIZINTI KAPISI — rakibin dosyasinin %6'si CSS/JS dolmustu.
    bulunan = []
    for desen, ad in SIZINTI_IZLERI:
        m = re.search(desen, metin)
        if m:
            i = m.start()
            bulunan.append("%s -> …%s…"
                           % (ad, metin[max(0, i - 40):i + 30]
                              .replace("\n", " ")))
    if bulunan:
        print("")
        print("  🔴 CSS/JS SIZINTISI:")
        for b in bulunan[:4]:
            print("     %s" % b)
        print("     Uretim DURDU — gorunur metin disinda bir sey karisti.")
        return 2
    print("  ✅ sizinti yok (%d ayri iz ARANDI)" % len(SIZINTI_IZLERI))

    eski = _oku(CIKTI) if os.path.exists(CIKTI) else None
    if eski == metin:
        print("\n  Zaten guncel.")
        return 0
    if not uygula:
        print("\n  %s — uygulamak icin --uygula"
              % ("DEGISECEK" if eski is not None else "OLUSTURULACAK"))
        return 0
    with io.open(CIKTI, "w", encoding="utf-8", newline="\n") as f:
        f.write(metin)
    print("\n  YAZILDI: llms-full.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
