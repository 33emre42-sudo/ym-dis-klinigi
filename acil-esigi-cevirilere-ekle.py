#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Implant cevirilerine ACIL ESIGINI geri koyar (SITE-16 B1).

SORUN — canli sayfalarda hasta guvenligi acigi:
Bes dildeki implant sayfasi "islemden sonra sislik beklenendir, bir
seyin ters gittiginin isareti degildir" deyip DURUYOR. Ne klinigi
arama esigi var, ne 112. Uluslararasi bir hasta, agzi hizla kanarken
ya da yutkunamazken sayfaya bakip "normal" diye dusunebilir.

⚠️ BU YENI TIBBI IDDIA DEGIL. Turkce asil sayfa (`implant-sureci.html`)
esikleri ZATEN iceriyor ve hekim onayindan gecmis:
  · sislik ilk 48-72 saatte zirve yapar, o pencerede artmasi tek basina
    sorun degildir
  · UCUNCU GUNDEN sonra gerilemek yerine artiyorsa, ates ciktiysa,
    basincla duran kanama yeniden basliyorsa, agri giderek
    siddetleniyorsa -> KLINIGI ARA
  · kanama tekrarlanan basinca ragmen durmuyorsa ya da agzi hizla
    dolduruyorsa; nefes/yutkunma guclugu, agiz tabaninda sislik, yuz
    ya da boyunda hizla yayilan sislik, bilinc degisikligi/bayilma
    -> 112 ya da en yakin acil
Ceviriler bu bilgiyi DUSURMUS. Betik onu geri koyuyor — kaynak metin
degismiyor, yalnizca cevirilerdeki eksik kapaniyor.

Betik TEKRAR CALISTIRILABILIR: esik zaten varsa dosyaya dokunmaz.
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
KOK = os.path.dirname(os.path.abspath(__file__))

# (dosya, bulunacak eski paragraf, yerine gececek metin)
DEGISIM = [
    ("en/dental-implants.html",
     "<p>Swelling and discomfort for a few days after the procedure are\n"
     "   expected and not a sign that something has gone wrong.</p>",
     "<p>Mild swelling and tenderness in the first days are expected.\n"
     "   Swelling usually peaks within the first 48–72 hours; increasing\n"
     "   during that window is not by itself a problem.</p>\n"
     "<p><b>Call the clinic</b> if swelling grows instead of easing after\n"
     "   the third day, you develop a fever, bleeding that had stopped\n"
     "   with pressure starts again, or pain steadily worsens. These are\n"
     "   outside the expected course.</p>\n"
     "<p><b>Call 112 or go to the nearest emergency department</b> if\n"
     "   bleeding does not stop despite repeated pressure or rapidly fills\n"
     "   your mouth; if you have difficulty breathing or swallowing,\n"
     "   swelling in the floor of the mouth, rapidly spreading swelling of\n"
     "   the face or neck, or altered consciousness or fainting.</p>"),

    ("es/implantes-dentales.html",
     "<p>La inflamación y las molestias durante unos días tras el\n"
     "   procedimiento son esperables y no indican que algo haya ido mal.</p>",
     "<p>Es esperable una inflamación leve y molestias durante los primeros\n"
     "   días. La inflamación suele alcanzar su máximo en las primeras\n"
     "   48–72 horas; que aumente en ese periodo no significa por sí solo\n"
     "   que haya un problema.</p>\n"
     "<p><b>Llame a la clínica</b> si la inflamación aumenta en lugar de\n"
     "   remitir después del tercer día, aparece fiebre, vuelve a sangrar\n"
     "   tras haberse detenido con presión, o el dolor empeora de forma\n"
     "   progresiva. Esto queda fuera de la evolución esperada.</p>\n"
     "<p><b>Llame al 112 o acuda al servicio de urgencias más cercano</b>\n"
     "   si el sangrado no se detiene pese a la presión repetida o llena\n"
     "   rápidamente la boca; si tiene dificultad para respirar o tragar,\n"
     "   inflamación en el suelo de la boca, inflamación de la cara o el\n"
     "   cuello que se extiende con rapidez, o alteración de la conciencia\n"
     "   o desmayo.</p>"),

    ("fr/implants-dentaires.html",
     "<p>Un gonflement et une gêne pendant quelques jours après\n"
     "   l'intervention sont attendus et n'indiquent pas que quelque chose\n"
     "   s'est mal passé.</p>",
     "<p>Un gonflement léger et une sensibilité les premiers jours sont\n"
     "   attendus. Le gonflement atteint généralement son maximum dans les\n"
     "   48 à 72 premières heures ; qu'il augmente pendant cette période ne\n"
     "   signifie pas à soi seul qu'il y a un problème.</p>\n"
     "<p><b>Appelez la clinique</b> si le gonflement augmente au lieu de\n"
     "   diminuer après le troisième jour, si vous avez de la fièvre, si un\n"
     "   saignement arrêté par la pression reprend, ou si la douleur\n"
     "   s'aggrave progressivement. Cela sort de l'évolution attendue.</p>\n"
     "<p><b>Appelez le 112 ou rendez-vous aux urgences les plus proches</b>\n"
     "   si le saignement ne s'arrête pas malgré une pression répétée ou\n"
     "   remplit rapidement votre bouche ; en cas de difficulté à respirer\n"
     "   ou à avaler, de gonflement du plancher de la bouche, d'un\n"
     "   gonflement du visage ou du cou qui s'étend rapidement, ou de\n"
     "   trouble de la conscience ou d'évanouissement.</p>"),

    ("de/zahnimplantate.html",
     "<p>Eine Schwellung und Beschwerden während einiger Tage nach dem\n"
     "   Eingriff sind zu erwarten und kein Zeichen dafür, dass etwas schief\n"
     "   gelaufen ist.</p>",
     "<p>Eine leichte Schwellung und Empfindlichkeit in den ersten Tagen\n"
     "   sind zu erwarten. Die Schwellung erreicht ihren Höhepunkt meist\n"
     "   innerhalb der ersten 48–72 Stunden; dass sie in diesem Zeitraum\n"
     "   zunimmt, bedeutet für sich genommen kein Problem.</p>\n"
     "<p><b>Rufen Sie die Klinik an</b>, wenn die Schwellung nach dem\n"
     "   dritten Tag zunimmt statt abzuklingen, Fieber auftritt, eine durch\n"
     "   Druck gestillte Blutung erneut beginnt oder die Schmerzen stetig\n"
     "   stärker werden. Das liegt außerhalb des erwarteten Verlaufs.</p>\n"
     "<p><b>Rufen Sie 112 an oder suchen Sie die nächste Notaufnahme auf</b>,\n"
     "   wenn die Blutung trotz wiederholtem Druck nicht aufhört oder den\n"
     "   Mund rasch füllt; bei Atem- oder Schluckbeschwerden, Schwellung des\n"
     "   Mundbodens, sich rasch ausbreitender Schwellung von Gesicht oder\n"
     "   Hals, oder bei Bewusstseinsveränderung oder Ohnmacht.</p>"),

    ("ru/zubnye-implanty.html",
     "<p>Отёк и неприятные ощущения в течение нескольких дней после\n"
     "   процедуры ожидаемы и не означают, что что-то пошло не так.</p>",
     "<p>Небольшой отёк и чувствительность в первые дни ожидаемы. Отёк\n"
     "   обычно достигает максимума в первые 48–72 часа; его нарастание в\n"
     "   этот период само по себе не означает проблему.</p>\n"
     "<p><b>Позвоните в клинику</b>, если после третьего дня отёк\n"
     "   нарастает вместо того, чтобы спадать, поднялась температура,\n"
     "   кровотечение, остановленное давлением, началось снова, или боль\n"
     "   постепенно усиливается. Это выходит за рамки ожидаемого\n"
     "   течения.</p>\n"
     "<p><b>Звоните 112 или обратитесь в ближайшее отделение неотложной\n"
     "   помощи</b>, если кровотечение не останавливается несмотря на\n"
     "   повторное давление или быстро заполняет рот; при затруднении\n"
     "   дыхания или глотания, отёке дна полости рта, быстро\n"
     "   распространяющемся отёке лица или шеи, нарушении сознания или\n"
     "   обмороке.</p>"),
]


def main():
    kontrol = "--kontrol" in sys.argv
    yapilan = atlanan = bulunamayan = 0
    for ad, eski, yeni in DEGISIM:
        yol = os.path.join(KOK, ad)
        if not os.path.isfile(yol):
            print("  🔴 DOSYA YOK: %s" % ad)
            bulunamayan += 1
            continue
        metin = io.open(yol, encoding="utf-8").read()
        if "112" in metin:
            print("  atlandi (esik zaten var): %s" % ad)
            atlanan += 1
            continue
        if eski not in metin:
            # ⚠️ SESSIZCE GECME. Paragraf bulunamadiysa sayfa
            # degismis demektir; guvenlik metni EKSIK kalir.
            print("  🔴 PARAGRAF BULUNAMADI: %s — ELLE BAK" % ad)
            bulunamayan += 1
            continue
        if not kontrol:
            io.open(yol, "w", encoding="utf-8").write(
                metin.replace(eski, yeni, 1))
        print("  eklendi: %s" % ad)
        yapilan += 1

    print("")
    print("eklenen: %d · atlanan: %d · SORUNLU: %d"
          % (yapilan, atlanan, bulunamayan))
    if kontrol:
        print("(--kontrol: dosya YAZILMADI)")
    return 1 if bulunamayan else 0


if __name__ == "__main__":
    sys.exit(main())
