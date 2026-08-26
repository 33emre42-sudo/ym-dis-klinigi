#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ekrana yapisik "Ara + WhatsApp" cubugunu TUM sayfalara yayar.

⚠️ NEDEN: cubuk yalnizca `index.html`'deydi (olculdu: 1/78 sayfa).
Oysa acil dis hastasi Google'dan ANA SAYFAYA degil, `gece-dis-agrisi`
ya da `dis-apsesi` gibi bir YAZIYA dusuyor — 35 bilgi yazisinin varlik
sebebi bu. O sayfalarda hasta yaziyi okuyup asagi iniyor ve altinda
arama/WhatsApp dugmesi bulamiyordu. Yapiskan seritteki telefon dugmesi
duruyor ama tek dokunusla WhatsApp yok.

Sohbet widget'i BILEREK yayilmiyor (hekim karari): bot hastaya cevap
veriyor, 35 tibbi yazinin altina koymak ayri bir karar.

⚠️ IKI SESSIZ TUZAK VAR, ikisi de burada kapatiliyor:

  1. `.dugme.ikincil` bilgi.css'te TANIMSIZ. index.html kendi gomulu
     stilinde tanimliyor. Isaretlemeyi oldugu gibi kopyalasak WhatsApp
     dugmesi 77 sayfada bicemsiz kalirdi. Kural bilgi.css'e ekleniyor
     ki isaretleme her sayfada AYNI olsun.

  2. "Ara" Turkce. 35 yabanci sayfaya Turkce dugme koymak, denetimdeki
     "her dil AYNI operasyonel sozu veriyor" ilkesine aykiri. Etiket
     sayfanin diline gore yaziliyor.

Kullanim:
    python sabit-cubuk.py            # KURU — hicbir sey yazmaz
    python sabit-cubuk.py --uygula   # yazar

Tekrar kosulabilir.
"""
import io
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
UYGULA = "--uygula" in sys.argv
DILLER = ("de", "en", "es", "fr", "ru")

# Dugme etiketi sayfanin dilinde. WhatsApp her dilde ayni.
ARA = {"": "Ara", "en": "Call", "es": "Llamar",
       "fr": "Appeler", "de": "Anrufen", "ru": "&#1055;&#1086;&#1079;&#1074;&#1086;&#1085;&#1080;&#1090;&#1100;"}

_TEL_SVG = ('<svg class="ikon" width="17" height="17" viewBox="0 0 24 24" '
            'fill="none" stroke="currentColor" stroke-width="1.6" '
            'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
            '<path d="M6.5 3h3l1.5 4-2 1.5a12 12 0 0 0 5.5 5.5L16 12l4 1.5v3a2 '
            '2 0 0 1-2.2 2A16.5 16.5 0 0 1 4 6.2 2 2 0 0 1 6 4V3Z"/></svg>')
_WA_SVG = ('<svg class="ikon" width="17" height="17" viewBox="0 0 24 24" '
           'fill="none" stroke="currentColor" stroke-width="1.6" '
           'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
           '<path d="M20 12a7.5 7.5 0 0 1-11 6.6L4.5 20l1.4-4.4A7.5 7.5 0 1 1 '
           '20 12Z"/></svg>')


def cubuk(kod):
    return (
        '\n<div class="sabit">\n'
        '  <a class="dugme birincil" href="tel:+905417324376">%s %s</a>\n'
        '  <a class="dugme ikincil" href="https://wa.me/905417324376">%s WhatsApp</a>\n'
        '</div>\n' % (_TEL_SVG, ARA[kod], _WA_SVG))


CSS = """
/* --- ekrana yapisik "Ara + WhatsApp" cubugu (8 Agu 2026) ------------
   index.html disindaki 77 sayfaya yayildi. Acil hasta aramadan bir
   BILGI YAZISINA dusuyor; o sayfada da tek dokunusla ulasabilmeli.
   ⚠️ .dugme.ikincil burada tanimlaniyor — index.html kendi gomulu
   stilinde tanimliyordu ve bilgi.css'te YOKTU; olmadan WhatsApp
   dugmesi bicemsiz kalirdi. Isaretleme her sayfada ayni olsun diye
   kural buraya tasindi, isaretleme degil. */
.dugme.ikincil{border-color:var(--cizgi);color:var(--murekkep);
  background:var(--kat)}
.sabit{position:fixed;left:0;right:0;bottom:0;z-index:40;display:none;gap:9px;
  padding:11px 20px calc(11px + env(safe-area-inset-bottom));
  background:color-mix(in srgb, var(--kagit) 88%, transparent);
  backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);
  border-top:1px solid var(--cizgi);opacity:0;pointer-events:none;
  transform:translateY(calc(100% + env(safe-area-inset-bottom)));
  transition:opacity .18s ease,transform .18s ease}
.sabit .dugme{flex:1;justify-content:center}
.sabit.sabit-gorunur{opacity:1;pointer-events:auto;transform:translateY(0)}
@media (max-width:720px){
  .sabit{display:flex}
  body{padding-bottom:88px}
}
"""

_BODY = re.compile(r'(\s*</body>)')


def oku(y):
    return io.open(y, encoding="utf-8").read()


def yaz(y, s):
    with io.open(y, "w", encoding="utf-8", newline="") as f:
        f.write(s)


def dil_kodu(y):
    d = os.path.dirname(y).replace(os.sep, "/").strip("./")
    k = d.split("/")[0] if d else ""
    return k if k in ARA else None


def sayfalar():
    s = [a for a in os.listdir(".") if a.endswith(".html")]
    for d in DILLER:
        if os.path.isdir(d):
            s += ["%s/%s" % (d, a) for a in os.listdir(d) if a.endswith(".html")]
    return sorted(s)


def ekle(y):
    s = oku(y)
    if '<nav class="menu"' not in s:
        return False, "menu yok (kapsam disi)"
    if 'class="sabit"' in s:
        return False, "zaten var"
    kod = dil_kodu(y)
    if kod is None:
        return False, "⚠️ dil kodu cozulemedi"
    yeni, n = _BODY.subn(lambda m: cubuk(kod) + m.group(1), s, count=1)
    if n == 0:
        return False, "⚠️ </body> BULUNAMADI — elle bakilmali"
    if UYGULA:
        yaz(y, yeni)
    return True, ARA[kod].replace("&#1055;", "Поз…")[:10]


def css_ekle():
    s = oku("bilgi.css")
    if ".sabit{" in s:
        return False, "zaten var"
    if UYGULA:
        yaz("bilgi.css", s.rstrip() + "\n" + CSS)
    return True, "eklendi"


def main():
    print("=" * 68)
    print("SABIT EYLEM CUBUGU" + ("" if UYGULA else "  —  KURU CALISMA"))
    print("=" * 68)

    ok, sebep = css_ekle()
    print("\n  %-8s bilgi.css   %s" % ("YAZILDI" if ok else "atlandi", sebep))

    print("\n--- sayfalar ---")
    ek, atl, sorun = 0, 0, []
    for y in sayfalar():
        ok, sebep = ekle(y)
        if ok:
            ek += 1
        elif str(sebep).startswith("⚠️"):
            sorun.append((y, sebep))
        else:
            atl += 1
    print("  cubuk eklenen : %d sayfa" % ek)
    print("  atlanan       : %d" % atl)
    for y, s in sorun:
        print("  ⚠️ %-42s %s" % (y, s))

    print("\n" + "=" * 68)
    print("YAZILDI. Simdi: python denetle.py" if UYGULA
          else "HICBIR DOSYA DEGISMEDI. Uygulamak icin: --uygula")
    return 1 if sorun else 0


if __name__ == "__main__":
    sys.exit(main())
