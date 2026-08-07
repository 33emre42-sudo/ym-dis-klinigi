#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mobil menuyu YATAY KAYDIRMADAN hamburger panele cevirir + serit tasmasi.

⚠️ NEDEN (hekim iki ekran goruntusuyle bildirdi, olculdu):

1) MENUNUN YARISI GORUNMUYOR. 390px'te menu icerigi 718px — yani
   328px gizli. Hekim yana kaydirdiginda menu satiri TAMAMEN BOSALDI
   (ekranda yalnizca etkin sekme cizgisi kaldi). Kaydirilabilir sekme
   seridi dar ekranda kesfedilemiyor.

2) DIL BUTONU SERIDIN DISINDA. Olculdu: serit 390px, dil butonu
   363..428 — yani 38px TASIYOR.
   ⚠️ Bunu BEN URETTIM: onceki turda marka adini `white-space:nowrap`
   ile tek satira sabitledim, ad genisledi (144px), telefon dugmesini
   (156px) sağa itti ve dil butonunu disari tasidi. Duzeltmenin
   yan etkisini olcmeden birakmisim.
   Cozum: mobilde telefon dugmesi IKON-ONLY olur. Numara zaten hem
   giris bolumunde hem de ekrana yapisik alt cubukta ("Ara") duruyor;
   seritte tekrar sart degil.

Yaklasim: JS YOK. Dil secici zaten `<details>` ile calisiyor, ayni
kalip kullaniliyor — daha az hareketli parca, her tarayicida ayni.

⚠️ FAIL-SAFE: panel `:has()` seciciyle aciliyor. Destegi olmayan bir
tarayicida hamburger HIC GORUNMEZ ve eski kaydirilabilir menu yerinde
kalir. Yani en kotu ihtimalde bugunku davranisa duser; menusuz sayfa
olusmaz. (`@supports selector(:has(*))` kapisi bunun icin.)

Kullanim:
    python menu-hamburger.py            # KURU — hicbir sey yazmaz
    python menu-hamburger.py --uygula   # yazar

Tekrar kosulabilir.
"""
import io
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
UYGULA = "--uygula" in sys.argv
DILLER = ("de", "en", "es", "fr", "ru")

# Hamburger, seridin EN SOLUNA — logodan once (hekim "sol uste" dedi).
# Ikon sitenin oteki SVG'leriyle ayni bicimde: currentColor + stroke.
HAMBURGER = (
    '<details class="menu-ac"><summary aria-label="Men&uuml; / Menu">'
    '<svg class="ikon" width="18" height="18" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
    'aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg>'
    '</summary></details>\n  '
)

_SERIT = re.compile(r'(<div class="serit"><div class="sar">\s*)(<a class="marka")')

CSS = """
  /* --- mobil hamburger menu (8 Agu 2026) ---------------------------
     Dar ekranda sekme seridi yatay kaydirmaliydi ve icerigin 328px'i
     gizli kaliyordu; kaydirinca satir bosaliyordu. Artik panel olarak
     aciliyor. Dil secicideki gibi `details` ogesiyle — JS yok.
     ⚠️ Bu yorumda ACIK ETIKET YAZILMAZ: denetle.py etiket dengesini
     duz metinde sayiyor ve yorumdaki bir ornek etiket, GERCEK bir
     dengesizligi maskeleyebilir. (Ilk yazilista tam bunu yaptim ve
     denetim "3 ac / 2 kapa" diyerek yakaladi.)
     ⚠️ Acilma `:has()` ile; destegi yoksa hamburger gorunmez ve ESKI
     kaydirilabilir menu yerinde kalir (menusuz sayfa olusmaz). */
  .menu-ac{display:none}
  .menu-ac>summary{list-style:none;cursor:pointer;display:inline-flex;
    align-items:center;justify-content:center;width:40px;height:40px;
    border-radius:12px;border:1px solid var(--cizgi);background:var(--kat);
    color:var(--murekkep);flex:0 0 auto}
  .menu-ac>summary::-webkit-details-marker{display:none}
  .menu-ac>summary::marker{content:""}
  .menu-ac[open]>summary{border-color:var(--vurgu);color:var(--vurgu)}

  @media (max-width:640px){
    @supports selector(:has(*)){
      .menu-ac{display:block}
      .menu{display:none}
      .serit:has(.menu-ac[open]) + .menu{display:block}
      .menu .sar{flex-direction:column;gap:0;overflow-x:visible}
      .menu a{padding:14px 2px;font-size:15.5px;
        border-bottom:1px solid var(--cizgi);border-left:2px solid transparent}
      .menu a:last-child{border-bottom:none}
      .menu a[aria-current="page"]{border-bottom-color:var(--cizgi);
        border-left-color:var(--vurgu);padding-left:10px}
    }
    /* Serit tasmasi: numara giris bolumunde ve alt cubukta zaten var. */
    .serit-tel span{display:none}
    .serit-tel{padding:9px 12px}
  }
"""


def oku(y):
    return io.open(y, encoding="utf-8").read()


def yaz(y, s):
    # ⚠️ UTF-8 acikca. PowerShell'in cp1254 tuzagi siteyi bir kez
    # 20 dakika okunamaz hale getirmisti.
    with io.open(y, "w", encoding="utf-8", newline="") as f:
        f.write(s)


def sayfalar():
    s = [a for a in os.listdir(".") if a.endswith(".html")]
    for d in DILLER:
        if os.path.isdir(d):
            s += ["%s/%s" % (d, a) for a in os.listdir(d) if a.endswith(".html")]
    return sorted(s)


def html_ekle(y):
    s = oku(y)
    if '<nav class="menu"' not in s:
        return False, "menu yok"
    if 'class="menu-ac"' in s:
        return False, "zaten var"
    yeni, n = _SERIT.subn(lambda m: m.group(1) + HAMBURGER + m.group(2), s, count=1)
    if n == 0:
        return False, "⚠️ SERIT DESENI TUTMADI — elle bakilmali"
    if UYGULA:
        yaz(y, yeni)
    return True, "eklendi"


def css_ekle(yol, girintili):
    s = oku(yol)
    if ".menu-ac" in s:
        return False, "zaten var"
    css = CSS if girintili else "\n".join(
        (l[2:] if l.startswith("  ") else l) for l in CSS.split("\n"))
    # Menu kurallarinin hemen ardina — ilgili blokla YAN YANA dursun.
    m = re.search(r'^[ \t]*@media \(max-width:640px\)\{\.menu a\{[^\n]*\n', s, re.M)
    if not m:
        return False, "⚠️ menu kural blogu bulunamadi"
    s = s[:m.end()] + css + s[m.end():]
    if UYGULA:
        yaz(yol, s)
    return True, "eklendi"


def main():
    print("=" * 70)
    print("MOBIL HAMBURGER MENU" + ("" if UYGULA else "  —  KURU CALISMA"))
    print("=" * 70)

    print("\n--- stil dosyalari ---")
    for yol, gir in (("index.html", True), ("bilgi.css", False)):
        if not os.path.exists(yol):
            print("  ATLANDI  %-12s dosya yok" % yol)
            continue
        ok, sebep = css_ekle(yol, gir)
        print("  %-8s %-12s %s" % ("YAZILDI" if ok else "atlandi", yol, sebep))

    print("\n--- sayfalar ---")
    ek, atl, sorun = 0, 0, []
    for y in sayfalar():
        ok, sebep = html_ekle(y)
        if ok:
            ek += 1
        elif str(sebep).startswith("⚠️"):
            sorun.append((y, sebep))
        else:
            atl += 1
    print("  hamburger eklenen : %d sayfa" % ek)
    print("  atlanan           : %d" % atl)
    for y, s in sorun:
        print("  ⚠️ %-44s %s" % (y, s))

    print("\n" + "=" * 70)
    print("YAZILDI. Simdi: python denetle.py" if UYGULA
          else "HICBIR DOSYA DEGISMEDI. Uygulamak icin: --uygula")
    return 1 if sorun else 0


if __name__ == "__main__":
    sys.exit(main())
