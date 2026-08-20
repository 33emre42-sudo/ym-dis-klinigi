# -*- coding: utf-8 -*-
"""Acil temali yazilara TRIYAJ DORTLUSUNU tamamlar.

`nobetci-dis-hekimi-acil-dis.html` dort soruyu birden cevapliyor:
    1. hangi sikayet beklemez        2. bunlar 112'ye
    3. sabahi bekleyebilir           4. bunlari yapmayin
Diger acil yazilarda bu dortlunun bir kismi eksikti (olculdu,
19 Agu 2026): "bunlari yapmayin" yalniz dis-apsesi'nde, "sabahi
bekler" yalniz iki sayfada vardi.

⛔ NEDEN KOPYALA-YAPISTIR DEGIL:
`dis-apsesi.html`in "Sunlari yapmayin" listesi kanonikten FARKLI ve
konuya ozel (sisligi patlatma, alkolle calkalama). Hekim onu bilerek
oyle yazmis. Uzerine genel liste basmak, ozellesmis tibbi uyariyi
genel olanla DEGISTIRMEK olurdu — o yuzden apse sayfasina
DOKUNULMUYOR; yalnizca listesi HIC OLMAYAN sayfalara yaziliyor.

⛔ NEDEN TAM LISTE:
LESSONS §12 — bir guvenlik listesinden CIKARMAK da bir iddiadir.
Sayfaya "uygun olanlari" secip koymak, hastanin baska sayfada
gorecegi bir uyariyi burada gormemesi demektir. Dort madde de
konusundan bagimsiz gecerli oldugu icin liste BUTUN olarak gider.

⛔ TEK KAYNAK (LESSONS §5):
Metin burada TEK yerde tanimli. `denetle.py` tasiyan butun sayfalarda
BIREBIR ayni oldugunu dogrular; biri elle degistirilirse yayin durur.

Kullanim:  python triyaj-yay.py            (kuru)
           python triyaj-yay.py --uygula   (yazar)
"""
import io, os, re, sys

KOK = os.path.dirname(os.path.abspath(__file__))

# Kanonik metin — kaynagi nobetci-dis-hekimi-acil-dis.html, hekim onayli.
YAPMAYIN = """    <div class="uyari">
      <b>Bunları yapmayın</b>
      <ul>
        <li><strong>Ağrı kesiciyi diş etinin üzerine koymayın.</strong>
            Ağrıyı geçirmez; temas ettiği yerde kimyasal yanık
            oluşturabilir ve tabloyu ağırlaştırır.</li>
        <li><strong>Şişliğe sıcak uygulamayın.</strong> Sıcak, iltihabın
            yayılmasını kolaylaştırabilir.</li>
        <li>Elinizde kalan eski antibiyotikleri kendi kararınızla
            kullanmayın. Hangi ilacın gerekip gerekmediği muayeneyle
            belirlenir.</li>
        <li>Sallanan dişi zorlamayın, kanamayı görmek için pıhtıyı
            kaldırmayın.</li>
      </ul>
      <p style="margin-top:10px">Gece yola çıkmalı mısınız, yoksa
         sabahı beklemek mi doğru?
         <a href="nobetci-dis-hekimi-acil-dis.html#hangi-sikayet-beklemez">Hangi
         şikâyet beklemez</a> ve
         <a href="nobetci-dis-hekimi-acil-dis.html#sabahi-bekleyebilecek-sikayetler">hangisi
         sabahı bekleyebilir</a> — iki liste de orada.</p>
    </div>

"""

# Listesi HIC olmayan acil temali sayfalar. dis-apsesi.html BILEREK yok.
SAYFALAR = [
    "gece-dis-agrisi.html",
    "gece-hafta-sonu-dis-hekimi.html",
    "kirilan-dis-ne-yapmali.html",
    "dis-cekimi-sonrasi-sislik.html",
    "dolgu-kaplama-dustu.html",
]

CAPA = '    <div class="cagri">'
ESKI = re.compile(r'    <div class="uyari">\n      <b>Bunları yapmayın</b>.*?\n    </div>\n\n',
                  re.S)


def main():
    uygula = "--uygula" in sys.argv
    hata = 0
    for dosya in SAYFALAR:
        yol = os.path.join(KOK, dosya)
        if not os.path.exists(yol):
            print("  HATA    %-34s dosya yok" % dosya); hata += 1; continue
        s = io.open(yol, encoding="utf-8").read()
        s = ESKI.sub("", s)                      # tekrar calistirilabilir
        if s.count(CAPA) != 1:
            print("  HATA    %-34s capa %d kez" % (dosya, s.count(CAPA)))
            hata += 1; continue
        if re.search(r"[Bb]unları yapmayın|[Şş]unları yapmayın", s):
            print("  ATLANDI %-34s zaten kendi listesi var" % dosya)
            continue
        s = s.replace(CAPA, YAPMAYIN + CAPA, 1)
        if uygula:
            io.open(yol, "w", encoding="utf-8", newline="").write(s)
        print("  %-7s %-34s triyaj dortlusu tamamlandi"
              % ("YAZILDI" if uygula else "kuru", dosya))
    print("-" * 62)
    print("%d sayfa · %d hata%s" % (len(SAYFALAR), hata,
          "" if uygula else "  ·  KURU"))
    return 1 if hata else 0


if __name__ == "__main__":
    sys.exit(main())
