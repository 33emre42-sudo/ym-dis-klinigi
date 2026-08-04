#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ana sayfadaki tedavi listesini, o tedaviyi ANLATAN sayfaya baglar.

SORUN (4 Agu 2026 olcumu):
Ana sayfada `Dentist.availableService` icinde dokuz `MedicalProcedure`
var ama HICBIRININ `url`'si yok:

    {"@type":"MedicalProcedure","name":"İmplant"}

Ote yandan `implant-sureci.html` sayfasinin `about` alani ZATEN
`MedicalProcedure / Diş implantı` diyor. Yani parcalar iki ucta da
duruyor ama BIRBIRINE BAGLI DEGIL.

Sonuc: Google "bu klinik implant yapiyor" bilgisini goruyor, "implanti
anlatan sayfa su" bilgisini de goruyor, ama ikisinin AYNI SEY oldugunu
bilmiyor. Varlik grafigi tam ise yarayacagi yerde kopuk.

Olculdu: 453 arama gosteriminin tamami ana sayfaya gidiyor, tedavi
sayfalarinin hicbiri gorunmuyor. Bu baglanti, tedavi sorgularinda o
sayfalarin aday olmasinin on sarti.

⚠️ YENI TIBBI IDDIA YOK. Tek yapilan, var olan iki bilgiyi baglamak:
`url` + ortak `@id`. Metin degismiyor.

⚠️ Eslesmeyen tedavi UYDURULMAZ. Bir tedaviyi anlatan sayfa yoksa o
girdi `url`siz kalir — yanlis sayfaya baglamak, olmayan baglantidan
kotudur.
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
KOK = os.path.dirname(os.path.abspath(__file__))
TABAN = "https://ymdisklinigi.com/"

# ana sayfadaki ad  ->  o tedaviyi anlatan sayfa
# Eslesmeler ELLE dogrulandi: her hedef sayfanin `about` alani gercekten
# o tedaviyi tanimliyor (ya da tedavinin konusu olan durumu anlatiyor).
ESLESME = {
    "Diş dolgusu":          "dis-dolgusu.html",
    "Kanal tedavisi":       "kanal-tedavisi.html",
    "Diş çekimi":           "dis-cekimi.html",
    "İmplant":              "implant-sureci.html",
    "Protez ve kaplama":    "protez-kaplama.html",
    "Ortodonti":            "dis-teli-ortodonti.html",
    "Diş taşı temizliği":   "dis-tasi-temizligi.html",
    # ⚠️ Asagidaki ikisinin `about` alani MedicalProcedure DEGIL,
    # MedicalCondition. Yine de konuyu anlatan sayfa onlar; hastanin
    # aradigi bilgi orada. `url` veriliyor ama ortak `@id` VERILMIYOR —
    # ayni varlik olduklarini iddia etmek yanlis olurdu.
    "Çocuk diş hekimliği":  "cocukta-ilk-dis.html",
    "Diş eti tedavisi":     "diseti-cekilmesi.html",
}

# Ortak kimlik verilecekler: sayfanin `about`u gercekten MedicalProcedure
AYNI_VARLIK = {"Diş dolgusu", "Kanal tedavisi", "Diş çekimi", "İmplant",
               "Protez ve kaplama", "Ortodonti", "Diş taşı temizliği"}


def main():
    kontrol = "--kontrol" in sys.argv
    yol = os.path.join(KOK, "index.html")
    t = io.open(yol, encoding="utf-8").read()
    degisen = atlanan = sorun = 0

    for ad, sayfa in ESLESME.items():
        if not os.path.isfile(os.path.join(KOK, sayfa)):
            print("  🔴 HEDEF SAYFA YOK: %s -> %s" % (ad, sayfa))
            sorun += 1
            continue

        eski = '{"@type":"MedicalProcedure","name":"%s"}' % ad
        if eski not in t:
            if '"name":"%s","url"' % ad in t:
                print("  atlandi (zaten bagli): %s" % ad)
                atlanan += 1
            else:
                # ⚠️ SESSIZCE GECME: ad degismisse baglanti kurulmaz ve
                # kimse fark etmez.
                print("  🔴 CIPA TUTMADI: %s — ELLE BAK" % ad)
                sorun += 1
            continue

        if ad in AYNI_VARLIK:
            # Ortak `@id`: ana sayfadaki hizmet ile sayfanin anlattigi
            # tedavi AYNI varlik. Sayfa tarafina da ayni kimlik yazilir.
            yeni = ('{"@type":"MedicalProcedure",'
                    '"@id":"%s%s#tedavi","name":"%s","url":"%s%s"}'
                    % (TABAN, sayfa, ad, TABAN, sayfa))
        else:
            yeni = ('{"@type":"MedicalProcedure","name":"%s","url":"%s%s"}'
                    % (ad, TABAN, sayfa))

        t = t.replace(eski, yeni, 1)
        degisen += 1
        print("  bagli: %-22s -> %s" % (ad, sayfa))

    if degisen and not kontrol:
        io.open(yol, "w", encoding="utf-8").write(t)

    # --- Sayfa tarafi: ayni `@id` -------------------------------------
    kimlik = 0
    for ad in AYNI_VARLIK:
        sayfa = ESLESME[ad]
        sy = os.path.join(KOK, sayfa)
        st = io.open(sy, encoding="utf-8").read()
        if '#tedavi' in st:
            continue
        # about icindeki MedicalProcedure nesnesine @id ekle
        hedef = '"about":{"@type":"MedicalProcedure","name":"'
        i = st.find(hedef)
        if i < 0:
            print("  ℹ️ %s: about/MedicalProcedure kalibi farkli, "
                  "@id eklenmedi" % sayfa)
            continue
        st2 = st.replace(
            hedef,
            '"about":{"@type":"MedicalProcedure",'
            '"@id":"%s%s#tedavi","name":"' % (TABAN, sayfa), 1)
        if not kontrol:
            io.open(sy, "w", encoding="utf-8").write(st2)
        kimlik += 1

    print("")
    print("baglanan: %d · atlanan: %d · sayfaya kimlik: %d · SORUNLU: %d"
          % (degisen, atlanan, kimlik, sorun))
    if kontrol:
        print("(--kontrol: dosya YAZILMADI)")
    return 1 if sorun else 0


if __name__ == "__main__":
    sys.exit(main())
