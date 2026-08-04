#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bilgi yazilarinin JSON-LD semasina YAZAR ve TARIH alanlarini ekler.

NEDEN VAR (4 Agu 2026 arastirmasi):
Saglik icerigi Google'in YMYL sinifinda — en siki denetlenen kategori.
2026 yonergelerinde tibbi icerikten beklenen sinyaller: yazar kimligi,
hekim onayi, yayin/guncelleme tarihi, dogrulanabilir unvan.

Olcum: 453 arama gosteriminin TAMAMI ana sayfaya gidiyor, 35 bilgi
yazisinin hicbiri arama sonucunda gorunmuyor. Semada `reviewedBy`
(kim inceledi) vardi ama `author` (kim yayimladi) ve tarihler YOKTU.

⚠️ DURUSTLUK KURALI — burasi onemli:
`author` olarak BIR INSAN YAZILMIYOR. Yazilari hekimler yazmadi;
hekimler TIBBEN INCELEDI ve bu zaten sayfada aleni yaziyor. Uydurma
insan yazar koymak, tam da YMYL'in denetledigi seyi ihlal ederdi.
Dogru yapi: yazar = KLINIK (kurum), inceleyen = iki hekim.

`hasCredential` de yalnizca "Dt." unvaninin ZATEN gerektirdigi seyi
soyluyor: dis hekimligi diplomasi. Universite, uzmanlik, yil gibi
DOGRULANMAMIS hicbir sey eklenmiyor (K38: ikisi de genel dis hekimi).

Tarihler git'ten geliyor — uydurulmuyor:
  datePublished = dosyanin depoya EKLENDIGI tarih
  dateModified  = son ICERIK degisikligi (bu betikten ONCE)

Betik TEKRAR CALISTIRILABILIR: `author` zaten varsa dosyaya dokunmaz.

Kullanim:  python sema-yazar-ekle.py [--kontrol]
"""
import io
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
KOK = os.path.dirname(os.path.abspath(__file__))

# Yazar = kurum. Klinik nesnesi ana sayfada tanimli, burada yalnizca
# ATIF yapiliyor (kopya nesne 5. tur bulgusuydu).
YAZAR = '"author":{"@id":"https://ymdisklinigi.com/#klinik"},'

# Hekim unvani + diploma. Yalnizca "Dt."nin zaten gerektirdigi kadar.
UNVAN = ('"honorificPrefix":"Dt.",'
         '"hasCredential":{"@type":"EducationalOccupationalCredential",'
         '"credentialCategory":"degree","name":"Diş Hekimliği Diploması"}')

ESKI_HEKIM = '"jobTitle":"Diş Hekimi"}'
YENI_HEKIM = '"jobTitle":"Diş Hekimi",' + UNVAN + '}'

# ⚠️ hekimlerimiz.html'de yapi FARKLI: jobTitle'dan sonra satir sonu ve
# `worksFor` geliyor, kapanis parantezi ayni satirda degil. Ilk surum bu
# dosyayi SESSIZCE atliyordu — oysa hekim kimliginin ASIL tanimlandigi
# sayfa orasi; yazilardaki `@id` atiflari oraya isaret ediyor.
ESKI_HEKIM2 = '"jobTitle":"Diş Hekimi",\n"worksFor"'
YENI_HEKIM2 = '"jobTitle":"Diş Hekimi",' + UNVAN + ',\n"worksFor"'

AUDIENCE = '"audience":{"@type":"Patient"},'


def git_tarih(dosya, ilk):
    """Dosyanin git'teki eklenme (ilk=True) ya da son degisim tarihi."""
    if ilk:
        k = ["git", "log", "--diff-filter=A", "--format=%ad",
             "--date=short", "--", dosya]
    else:
        k = ["git", "log", "-1", "--format=%ad", "--date=short",
             "--", dosya]
    try:
        c = subprocess.run(k, cwd=KOK, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
    except OSError:
        return None
    satirlar = [s for s in (c.stdout or "").split("\n") if s.strip()]
    if not satirlar:
        return None
    return satirlar[-1].strip() if ilk else satirlar[0].strip()


def main():
    kontrol = "--kontrol" in sys.argv
    dosyalar = sorted(a for a in os.listdir(KOK)
                      if a.endswith(".html"))
    islenen = atlanan = hekim_guncel = 0
    eksik_tarih = []

    for ad in dosyalar:
        yol = os.path.join(KOK, ad)
        metin = io.open(yol, encoding="utf-8").read()
        yeni = metin

        # 1) Hekim nesnelerine unvan + diploma (yazi olmayan sayfalarda da
        #    gecerli: hekimlerimiz.html, index.html)
        if UNVAN not in yeni:
            if ESKI_HEKIM in yeni:
                yeni = yeni.replace(ESKI_HEKIM, YENI_HEKIM)
                hekim_guncel += 1
            elif ESKI_HEKIM2 in yeni:
                yeni = yeni.replace(ESKI_HEKIM2, YENI_HEKIM2)
                hekim_guncel += 1
            elif '"jobTitle":"Diş Hekimi"' in yeni:
                # ⚠️ Ucuncu bir yapi cikmis. SESSIZCE GECME — hekim
                # kimligi eksik kalirsa YMYL sinyali yarim olur.
                print("  🔴 UYARI: %s icinde jobTitle var ama yapisi "
                      "taninmadi — unvan EKLENMEDI." % ad)

        # 2) Yalnizca bilgi yazilarina yazar + tarih
        if "MedicalWebPage" in metin:
            if '"author":' in metin:
                atlanan += 1
            elif AUDIENCE not in metin:
                print("  ATLANDI (beklenen yapi yok): %s" % ad)
                atlanan += 1
            else:
                yayin = git_tarih(ad, True)
                degisim = git_tarih(ad, False)
                if not yayin or not degisim:
                    eksik_tarih.append(ad)
                    print("  ATLANDI (git tarihi yok): %s" % ad)
                    atlanan += 1
                else:
                    yeni = yeni.replace(
                        AUDIENCE, AUDIENCE + "\n" + YAZAR, 1)
                    yeni = re.sub(
                        r'("lastReviewed":"[\d-]+",)',
                        r'\1\n"datePublished":"%s",'
                        r'\n"dateModified":"%s",' % (yayin, degisim),
                        yeni, count=1)
                    islenen += 1

        if yeni != metin and not kontrol:
            io.open(yol, "w", encoding="utf-8").write(yeni)

    print("")
    print("yazar+tarih eklenen : %d" % islenen)
    print("hekim unvani eklenen: %d dosya" % hekim_guncel)
    print("atlanan             : %d" % atlanan)
    if eksik_tarih:
        print("⚠️ git tarihi bulunamayan: %s" % ", ".join(eksik_tarih))
    if kontrol:
        print("(--kontrol: hicbir dosya YAZILMADI)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
