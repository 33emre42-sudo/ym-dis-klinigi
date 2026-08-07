#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`arayuz.js` baglantisini menu/dil secici bulunan tum sayfalara ekler.

⚠️ Ayri dosya, satir ici DEGIL. CSP satir ici betige izin veriyor
(`script-src 'self' 'unsafe-inline'`) ama ayni mantigi 77 sayfaya
kopyalamak bu projede defalarca ayrisma uretmis bir kalip. Tek kaynak.

Dil klasorlerindeki sayfalar icin yol `../arayuz.js` olur.

Kullanim:
    python arayuz-js-ekle.py            # KURU
    python arayuz-js-ekle.py --uygula   # yazar
"""
import io
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
UYGULA = "--uygula" in sys.argv
DILLER = ("de", "en", "es", "fr", "ru")
_BODY = re.compile(r'(\s*</body>)')


def oku(y):
    return io.open(y, encoding="utf-8").read()


def yaz(y, s):
    with io.open(y, "w", encoding="utf-8", newline="") as f:
        f.write(s)


def sayfalar():
    s = [a for a in os.listdir(".") if a.endswith(".html")]
    for d in DILLER:
        if os.path.isdir(d):
            s += ["%s/%s" % (d, a) for a in os.listdir(d) if a.endswith(".html")]
    return sorted(s)


def ekle(y):
    s = oku(y)
    # Kapsam: acilir menusu olan sayfalar. gizlilik.html'de ikisi de yok.
    if 'class="menu-ac"' not in s and 'class="dil-sec"' not in s:
        return False, "acilir menu yok (kapsam disi)"
    if "arayuz.js" in s:
        return False, "zaten var"
    yol = "../arayuz.js" if "/" in y else "arayuz.js"
    etiket = '\n<script src="%s" defer></script>\n' % yol
    yeni, n = _BODY.subn(lambda m: etiket + m.group(1), s, count=1)
    if n == 0:
        return False, "⚠️ </body> BULUNAMADI"
    if UYGULA:
        yaz(y, yeni)
    return True, yol


def main():
    print("=" * 62)
    print("arayuz.js BAGLANTISI" + ("" if UYGULA else "  —  KURU CALISMA"))
    print("=" * 62)
    ek, atl, sorun = 0, 0, []
    for y in sayfalar():
        ok, sebep = ekle(y)
        if ok:
            ek += 1
        elif str(sebep).startswith("⚠️"):
            sorun.append((y, sebep))
        else:
            atl += 1
    print("  eklenen : %d sayfa" % ek)
    print("  atlanan : %d" % atl)
    for y, s in sorun:
        print("  ⚠️ %-40s %s" % (y, s))
    print("=" * 62)
    print("YAZILDI." if UYGULA else "HICBIR DOSYA DEGISMEDI. --uygula ile yaz.")
    return 1 if sorun else 0


if __name__ == "__main__":
    sys.exit(main())
