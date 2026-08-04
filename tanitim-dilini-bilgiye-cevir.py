#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Yabanci kanal tedavisi sayfalarindaki TANITIM dilini bilgiye cevirir.

SITE-16 B3. Bes dilde ayni kalip vardi:

    <h2>Other treatments</h2>
    <p>We also carry out fillings, scaling, extractions and
       paediatric dental care.</p>

Bu "su alan nedir" degil, "BIZ SUNLARI DA YAPIYORUZ" — yani hizmet
tanitimi. Turkce asil sayfada (`kanal-tedavisi.html`) boyle bir bolum
HIC YOK; ceviri sirasinda eklenmis.

⚠️ NEDEN ONEMLI: dil bolumleri yayina "yalnizca BILGILENDIRME" gerekcesiyle
girdi — saglik turizmi yetki belgesi YOK. Hizmet sayma, o gerekceyi
deliyor. Ayrica mevzuatta talep yaratma yasak; desen tarayicisi bunu
goremez (kelime yasak degil, CERCEVE yanlis).

Yeni hali ayni bilgiyi veriyor ama alani TARIF ediyor ve muayene sartini
hatirlatiyor — Turkce sayfalarin dilinin aynisi.

Betik TEKRAR CALISTIRILABILIR ve cipa tutmazsa SESSIZCE GECMEZ.
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
KOK = os.path.dirname(os.path.abspath(__file__))

DEGISIM = [
    ("en/root-canal-and-general-dentistry.html",
     "<h2>Other treatments</h2>",
     "<h2>General dentistry</h2>",
     "<p>We also carry out fillings, scaling, extractions and paediatric\n"
     "   dental care.</p>",
     "<p>Fillings, scaling, extractions and paediatric dental care are\n"
     "   part of general dentistry. Whether any treatment is needed can\n"
     "   only be decided after an examination.</p>"),

    ("es/endodoncia-y-odontologia-general.html",
     "<h2>Otros tratamientos</h2>",
     "<h2>Odontología general</h2>",
     "<p>También realizamos empastes, limpiezas dentales, extracciones y\n"
     "   atención odontológica infantil.</p>",
     "<p>Los empastes, las limpiezas dentales, las extracciones y la\n"
     "   atención odontológica infantil forman parte de la odontología\n"
     "   general. La necesidad de tratamiento solo puede decidirse tras\n"
     "   una exploración.</p>"),

    ("fr/traitement-de-racine-et-dentisterie-generale.html",
     "<h2>Autres soins</h2>",
     "<h2>Dentisterie générale</h2>",
     "<p>Nous réalisons également des obturations, des détartrages, des\n"
     "   extractions et des soins dentaires pour les enfants.</p>",
     "<p>Les obturations, les détartrages, les extractions et les soins\n"
     "   dentaires pour les enfants relèvent de la dentisterie générale.\n"
     "   La nécessité d'un soin ne peut être établie qu'après un\n"
     "   examen.</p>"),

    ("de/wurzelbehandlung-und-allgemeine-zahnmedizin.html",
     "<h2>Weitere Behandlungen</h2>",
     "<h2>Allgemeine Zahnmedizin</h2>",
     "<p>Wir führen außerdem Füllungen, Zahnsteinentfernung, Extraktionen und\n"
     "   zahnärztliche Betreuung von Kindern durch.</p>",
     "<p>Füllungen, Zahnsteinentfernung, Extraktionen und die\n"
     "   zahnärztliche Betreuung von Kindern gehören zur allgemeinen\n"
     "   Zahnmedizin. Ob eine Behandlung nötig ist, lässt sich erst nach\n"
     "   einer Untersuchung entscheiden.</p>"),

    ("ru/lechenie-kanalov-i-obshchaya-stomatologiya.html",
     "<h2>Другие процедуры</h2>",
     "<h2>Общая стоматология</h2>",
     "<p>Мы также делаем пломбирование, снятие зубного камня, удаление зубов\n"
     "   и стоматологический приём детей.</p>",
     "<p>Пломбирование, снятие зубного камня, удаление зубов и\n"
     "   стоматологический приём детей относятся к общей стоматологии.\n"
     "   Нужно ли лечение, можно решить только после осмотра.</p>"),
]

# Meta aciklamalarinda da ayni cerceve vardi ("...ve yaptigimiz diger
# tedaviler") — orasi arama sonucunda GORUNEN metin, ayrica duzeltiliyor.
META = [
    # EN meta ZATEN temiz ("...not the same as healing." ile bitiyor) —
    # listede tutulmuyor ki "bulunamadi" gurultusu yapmasin.
    ("es/endodoncia-y-odontologia-general.html",
     "y qué otros tratamientos realizamos",
     "y qué abarca la odontología general"),
    ("fr/traitement-de-racine-et-dentisterie-generale.html",
     "et les autres soins que nous réalisons",
     "et ce que comprend la dentisterie générale"),
    ("de/wurzelbehandlung-und-allgemeine-zahnmedizin.html",
     "und welche weiteren Behandlungen wir durchführen",
     "und was die allgemeine Zahnmedizin umfasst"),
    ("ru/lechenie-kanalov-i-obshchaya-stomatologiya.html",
     "и какие ещё процедуры мы проводим",
     "и что охватывает общая стоматология"),
]


def main():
    kontrol = "--kontrol" in sys.argv
    tamam = sorun = 0

    for ad, eski_h2, yeni_h2, eski_p, yeni_p in DEGISIM:
        yol = os.path.join(KOK, ad)
        if not os.path.isfile(yol):
            print("  🔴 DOSYA YOK: %s" % ad)
            sorun += 1
            continue
        t = io.open(yol, encoding="utf-8").read()
        if yeni_h2 in t:
            print("  atlandi (zaten duzeltilmis): %s" % ad)
            continue
        eksik = [a for a, s in (("h2", eski_h2), ("p", eski_p))
                 if s not in t]
        if eksik:
            # ⚠️ SESSIZCE GECME: tanitim dili yerinde kalirsa dil
            # bolumlerinin yayin gerekcesi delik kalir.
            print("  🔴 CIPA TUTMADI (%s): %s — ELLE BAK"
                  % ("+".join(eksik), ad))
            sorun += 1
            continue
        t = t.replace(eski_h2, yeni_h2, 1).replace(eski_p, yeni_p, 1)
        if not kontrol:
            io.open(yol, "w", encoding="utf-8").write(t)
        print("  duzeltildi: %s" % ad)
        tamam += 1

    print("")
    for ad, eski, yeni in META:
        yol = os.path.join(KOK, ad)
        if not os.path.isfile(yol):
            continue
        t = io.open(yol, encoding="utf-8").read()
        if yeni in t:
            print("  meta atlandi (zaten): %s" % ad)
        elif eski in t:
            if not kontrol:
                io.open(yol, "w", encoding="utf-8").write(
                    t.replace(eski, yeni))
            print("  meta duzeltildi: %s" % ad)
        else:
            print("  ℹ️ meta kalibi bulunamadi (baska yazilmis): %s" % ad)

    print("")
    print("govde duzeltilen: %d · SORUNLU: %d" % (tamam, sorun))
    if kontrol:
        print("(--kontrol: dosya YAZILMADI)")
    return 1 if sorun else 0


if __name__ == "__main__":
    sys.exit(main())
