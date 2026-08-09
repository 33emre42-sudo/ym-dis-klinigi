#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sayfalardaki her karakterin yazi tipinde KARSILIGI var mi, olcer.

    python harf-kapsam.py            # rapor
    python harf-kapsam.py --dokum    # kullanilan butun latin-ext harfleri de yaz

NEDEN VAR — 9 Agustos 2026'da olculdu:

`fontlar.css` her `@font-face` icin bir `unicode-range` bildiriyor.
Tarayici bir karakteri cizerken o karakter HICBIR bildirilen araligin
icinde degilse bizim yazi tipimizi KULLANMAZ; sistem yedegine duser.
Sonuc sessizdir — hata yok, uyari yok, sadece o harf cevresindeki
metinden farkli gorunur.

Olcum: iki ok karakteri tam da bu durumdaydi.

    ←  U+2190   gizlilik.html
    →  U+2192   index.html (2 yerde)

Altkume `↑ U+2191` ve `↓ U+2193` iceriyor ama `←` ile `→` icermiyor —
yani dortlunun ikisi bizim yazi tipimizle, ikisi sistem yedegiyle
ciziliyordu. Kimse fark etmemisti cunku bakan bir kapi yoktu.

⚠️ EMOJI AYRI: 🦷 gibi karakterler zaten sistemin emoji yazi tipiyle
cizilir, bizim altkumemizde olmalari BEKLENMEZ. Onlar muaf.

⚠️ KIRIL AYRI: `ru/` sayfalarindaki Kiril harflerinin altkumesi hic
indirilmiyor (fontlar.css'te yalniz latin + latin-ext var). Bu bilinen
ve KABUL EDILMIS bir durum — sayfa sistem yazi tipiyle duzgun
goruntuleniyor. Ayri raporlanir, ihlal sayilmaz.

Bu betik hicbir dosyayi degistirmez.
"""
import glob
import io
import os
import re
import sys
import unicodedata

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

KOK = os.path.dirname(os.path.abspath(__file__))
CSS = os.path.join(KOK, "fontlar.css")

# Sistemin kendi yazi tipine BILEREK birakilanlar.
MUAF_BLOKLAR = (
    (0x1F000, 0x1FAFF),   # emoji
    (0x2600, 0x27BF),     # semboller / dingbats (✦ dahil)
    (0xFE00, 0xFE0F),     # varyasyon seciciler
    (0x200D, 0x200D),     # ZWJ
    (0x0400, 0x04FF),     # Kiril — ru/ sayfalari, ayri raporlanir
)

# Bosluk ve denetim karakterleri harf degil.
GORMEZDEN = set("\t\n\r\x0b\x0c  ​﻿")


def araliklari_oku():
    """`fontlar.css`teki BUTUN unicode-range bildirimlerini birlestirir."""
    if not os.path.exists(CSS):
        return None
    with io.open(CSS, encoding="utf-8") as f:
        s = f.read()
    araliklar = []
    for blok in re.findall(r"unicode-range:\s*([^;]+);", s, re.I):
        for p in blok.split(","):
            p = p.strip()
            m = re.match(r"U\+([0-9A-Fa-f]+)-([0-9A-Fa-f]+)$", p)
            if m:
                araliklar.append((int(m.group(1), 16), int(m.group(2), 16)))
                continue
            m = re.match(r"U\+([0-9A-Fa-f]+)$", p)
            if m:
                k = int(m.group(1), 16)
                araliklar.append((k, k))
                continue
            # `U+00??` joker biciminde de yazilabiliyor
            m = re.match(r"U\+([0-9A-Fa-f]*)(\?+)$", p)
            if m:
                taban, joker = m.group(1), m.group(2)
                alt = int(taban + "0" * len(joker), 16)
                ust = int(taban + "F" * len(joker), 16)
                araliklar.append((alt, ust))
    return araliklar or None


def icinde(kod, araliklar):
    return any(a <= kod <= b for a, b in araliklar)


def gorunur_metin(html):
    """Etiketleri, `<script>`/`<style>` govdesini ve yorumlari atar.

    JSON-LD `<script type="application/ld+json">` icinde durur ve
    ekranda GORUNMEZ — bu yuzden script blogu tumden atiliyor.
    """
    h = re.sub(r"<(script|style)\b.*?</\1>", " ", html, flags=re.S | re.I)
    h = re.sub(r"<!--.*?-->", " ", h, flags=re.S)
    return re.sub(r"<[^>]+>", " ", h)


def sayfalar():
    return sorted(glob.glob(os.path.join(KOK, "*.html")) +
                  glob.glob(os.path.join(KOK, "*", "*.html")))


def olc():
    """(kapsam_disi, kiril_sayfa, aralik_sayisi, sayfa_sayisi)."""
    araliklar = araliklari_oku()
    if araliklar is None:
        return None, None, 0, 0

    disi = {}
    kiril = set()
    dosyalar = sayfalar()
    for p in dosyalar:
        with io.open(p, encoding="utf-8", errors="replace") as f:
            metin = gorunur_metin(f.read())
        ad = os.path.relpath(p, KOK).replace(os.sep, "/")
        for ch in metin:
            if ch in GORMEZDEN:
                continue
            k = ord(ch)
            if k < 0x80 or icinde(k, araliklar):
                continue
            if any(a <= k <= b for a, b in MUAF_BLOKLAR):
                if 0x0400 <= k <= 0x04FF:
                    kiril.add(ad)
                continue
            disi.setdefault(ch, set()).add(ad)
    return disi, kiril, len(araliklar), len(dosyalar)


def main():
    disi, kiril, n_aralik, n_sayfa = olc()

    print("=" * 68)
    print("HARF KAPSAMI — yazi tipi altkumeleri sayfalari karsiliyor mu?")
    print("=" * 68)

    if disi is None:
        # ⚠️ Fail-open BILEREK: olculemeyeni ihlal saymak surekli kirmizi
        # bir gosterge uretir, o da yok sayilir. Ama SESSIZ de gecmez.
        print("  ⚠️ OLCULEMEDI — fontlar.css yok. Kontrol atlandi.")
        return 0

    print("  %d sayfa · fontlar.css'te %d unicode araligi"
          % (n_sayfa, n_aralik))

    if kiril:
        print("  ℹ️ Kiril: %d sayfa sistem yazi tipiyle ciziliyor "
              "(bilinen, kabul edilmis)" % len(kiril))

    if not disi:
        print("")
        print("  ✅ Gorunur her karakterin altkumede karsiligi var.")
        return 0

    print("")
    print("  🔴 ALTKUMEDE OLMAYAN %d KARAKTER — sistem yedegiyle cizilir:"
          % len(disi))
    for ch in sorted(disi, key=ord):
        ad = unicodedata.name(ch, "?")
        yerler = sorted(disi[ch])
        print("     %s  U+%04X  %-38s  %d sayfa: %s"
              % (ch, ord(ch), ad[:38], len(yerler),
                 ", ".join(yerler[:3]) + (" …" if len(yerler) > 3 else "")))
    print("")
    print("  Cozum iki turlu: ya karakteri metinden cikar, ya da yazi")
    print("  tipi altkumesine ekle (fontlar elle duzenlenmez —")
    print("  scratchpad'deki font-indir.py yeniden kosulur).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
