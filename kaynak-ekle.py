# -*- coding: utf-8 -*-
"""Bilgi yazilarina KAYNAKLAR bolumu ve sema citation'i yazar.

Neden var: 8 Agu 2026 olcumu — 35 bilgi yazisinin 35'inde de dis otorite
bagi YOKTU. GEO arastirmasinin (KDD 2024) ikinci sirasindaki etken kaynak
gostermektir; YMYL saglik icerigi icin E-E-A-T'nin de temelidir.

⛔ KURAL: buradaki her URL ELLE DOGRULANDI (HTTP 200 + icerik okundu).
Yeni kaynak eklerken ayni citayi koru — 'olmasi lazim' yeterli degil.
Kaynak, sayfadaki HEKIM ONAYLI cumleyi DESTEKLEMELI; celisiyorsa
kaynak da cumle de hekime gider (seo-geo skill).

Kullanim:  python kaynak-ekle.py            (kuru calisma)
           python kaynak-ekle.py --uygula   (yazar)
"""
import io, os, re, sys, json

KOK = os.path.dirname(os.path.abspath(__file__))

# --------------------------------------------------------------------------
# Kaynak kunyeleri.  (url, gorunur ad, kurum)
# --------------------------------------------------------------------------
WHO_AGIZ = ("https://www.who.int/news-room/fact-sheets/detail/oral-health",
            "Oral health", "Dünya Sağlık Örgütü (WHO)")
WHO_TUTUN = ("https://www.who.int/news-room/fact-sheets/detail/tobacco",
             "Tobacco", "Dünya Sağlık Örgütü (WHO)")
WHO_DIYABET = ("https://www.who.int/news-room/fact-sheets/detail/diabetes",
               "Diabetes", "Dünya Sağlık Örgütü (WHO)")

NHS_APSE = ("https://www.nhs.uk/conditions/dental-abscess/",
            "Dental abscess", "NHS — Birleşik Krallık Ulusal Sağlık Servisi")
NHS_KOKU = ("https://www.nhs.uk/conditions/bad-breath/",
            "Bad breath", "NHS")
NHS_KURU = ("https://www.nhs.uk/conditions/dry-mouth/",
            "Dry mouth", "NHS")
NHS_AFT = ("https://www.nhs.uk/conditions/mouth-ulcers/",
           "Mouth ulcers", "NHS")
NHS_DISETI = ("https://www.nhs.uk/conditions/gum-disease/",
              "Gum disease", "NHS")
NHS_CURUK = ("https://www.nhs.uk/conditions/tooth-decay/",
             "Tooth decay", "NHS")
NHS_YIRMI = ("https://www.nhs.uk/conditions/wisdom-tooth-removal/",
             "Wisdom tooth removal", "NHS")
NHS_KANAL = ("https://www.nhs.uk/conditions/root-canal-treatment/",
             "Root canal treatment", "NHS")
NHS_SIKMA = ("https://www.nhs.uk/conditions/teeth-grinding/",
             "Teeth grinding (bruxism)", "NHS")
NHS_TEL = ("https://www.nhs.uk/conditions/braces-and-orthodontics/",
           "Braces and orthodontics", "NHS")
NHS_BEYAZ = ("https://www.nhs.uk/conditions/teeth-whitening/",
             "Teeth whitening", "NHS")
NHS_AGRI = ("https://www.nhs.uk/conditions/toothache/",
            "Toothache", "NHS")
NHS_PROTEZ = ("https://www.nhs.uk/tests-and-treatments/dentures/",
              "Dentures", "NHS")
NHS_TEMIZ = ("https://www.nhs.uk/live-well/healthy-teeth-and-gums/how-to-keep-your-teeth-clean/",
             "How to keep your teeth clean", "NHS")
NHS_COCUK = ("https://www.nhs.uk/live-well/healthy-teeth-and-gums/taking-care-of-childrens-teeth/",
             "Taking care of children's teeth", "NHS")
NHS_TEDAVI = ("https://www.nhs.uk/live-well/healthy-teeth-and-gums/dental-treatments/",
              "Dental treatments", "NHS")
NHS_GEBE = ("https://www.nhs.uk/pregnancy/common-symptoms/bleeding-gums/",
            "Bleeding gums in pregnancy", "NHS")
NHSE_KORKU = ("https://www.england.nhs.uk/long-read/clinical-guide-for-dental-anxiety-management/",
              "Clinical guide for dental anxiety management", "NHS England")

NICE_TA1 = ("https://www.nice.org.uk/guidance/ta1/chapter/1-Recommendations",
            "Guidance on the extraction of wisdom teeth (TA1)",
            "NICE — Birleşik Krallık Ulusal Sağlık ve Bakım Mükemmeliyet Enstitüsü")
SDCEP_KAN = ("https://www.sdcep.org.uk/published-guidance/anticoagulants-and-antiplatelets/",
             "Management of Dental Patients Taking Anticoagulants or Antiplatelet Drugs",
             "SDCEP — İskoçya Diş Hekimliği Klinik Etkililik Programı")

COCH_PLAK = ("https://www.cochrane.org/evidence/CD005514_occlusal-splints-treating-sleep-bruxism-tooth-grinding",
             "Occlusal splints for treating sleep bruxism", "Cochrane sistematik derlemesi")
COCH_TASTEMIZ = ("https://www.cochrane.org/evidence/CD004625_routine-scale-and-polish-periodontal-health-adults",
                 "Routine scale and polish for periodontal health in adults",
                 "Cochrane sistematik derlemesi")
COCH_ARAYUZ = ("https://www.cochrane.org/evidence/CD012018_home-use-devices-cleaning-between-teeth-addition-toothbrushing-prevent-and-control-gum-diseases-and",
               "Home use of devices for cleaning between the teeth",
               "Cochrane sistematik derlemesi")

IADT_DUSEN = ("https://iadt-dentaltrauma.org/knocked-out/",
              "Knocked out — ilk yardım", "IADT — Uluslararası Diş Travmatolojisi Derneği")
IADT_KILAVUZ = ("https://iadt-dentaltrauma.org/guidelines-and-resources/guidelines/",
                "Dental trauma guidelines (2020)", "IADT")

FDA_RONTGEN = ("https://www.fda.gov/radiation-emitting-products/medical-x-ray-imaging/selection-patients-dental-radiographic-examinations",
               "The Selection of Patients for Dental Radiographic Examinations",
               "FDA — ABD Gıda ve İlaç Dairesi")
PMC_HASSAS = ("https://pmc.ncbi.nlm.nih.gov/articles/PMC8908863/",
              "Formulations of desensitizing toothpastes for dentin hypersensitivity",
              "Hakemli derleme (PubMed Central)")

# --------------------------------------------------------------------------
# Sayfa -> kaynaklar
# --------------------------------------------------------------------------
HARITA = {
    "agiz-kokusu.html":              [NHS_KOKU, NHS_DISETI],
    "agiz-kurulugu.html":            [NHS_KURU],
    "agiz-yarasi-aft.html":          [NHS_AFT],
    "cocukta-ilk-dis.html":          [NHS_COCUK],
    "curuk-nasil-olusur.html":       [NHS_CURUK, WHO_AGIZ],
    "dis-apsesi.html":               [NHS_APSE, NHS_AGRI],
    "dis-beyazlatma-gercekleri.html":[NHS_BEYAZ],
    "dis-cekimi.html":               [NHS_TEDAVI, NHS_AGRI],
    "dis-cekimi-sonrasi-sislik.html":[NHS_YIRMI],
    "dis-dolgusu.html":              [NHS_TEDAVI, NHS_CURUK],
    "dis-hassasiyeti.html":          [PMC_HASSAS, NHS_AGRI],
    "dis-hekimi-korkusu.html":       [NHSE_KORKU],
    "dis-ipi-kullanimi.html":        [COCH_ARAYUZ, NHS_TEMIZ],
    "dis-rontgeni.html":             [FDA_RONTGEN],
    "dis-sikma-gece-plagi.html":     [NHS_SIKMA, COCH_PLAK],
    "dis-tasi-temizligi.html":       [NHS_DISETI, COCH_TASTEMIZ],
    "dis-teli-ortodonti.html":       [NHS_TEL],
    "diseti-cekilmesi.html":         [NHS_DISETI, WHO_AGIZ],
    "diseti-kanamasi.html":          [NHS_DISETI],
    "diyabet-ve-agiz-sagligi.html":  [WHO_DIYABET, NHS_DISETI],
    "dolgu-kaplama-dustu.html":      [NHS_TEDAVI],
    "florur-nedir.html":             [NHS_TEMIZ, WHO_AGIZ],
    "gece-dis-agrisi.html":          [NHS_AGRI],
    "gece-hafta-sonu-dis-hekimi.html":[NHS_AGRI],
    "hamilelikte-dis-sagligi.html":  [NHS_GEBE, NHS_DISETI],
    "implant-sureci.html":           [NHS_TEDAVI],
    "kan-sulandirici-dis-tedavisi.html":[SDCEP_KAN],
    "kanal-tedavisi.html":           [NHS_KANAL],
    "kirilan-dis-ne-yapmali.html":   [IADT_DUSEN, IADT_KILAVUZ],
    "nobetci-dis-hekimi-acil-dis.html":[NHS_AGRI],
    "protez-kaplama.html":           [NHS_PROTEZ, NHS_TEDAVI],
    "seffaf-plak.html":              [NHS_TEL],
    "sigara-ve-agiz-sagligi.html":   [WHO_TUTUN, WHO_AGIZ],
    "sik-sorulan-sorular.html":      [WHO_AGIZ, NHS_AGRI, NHS_DISETI],
    "sut-disi-curugu.html":          [NHS_COCUK, WHO_AGIZ],
    "yirmi-yas-disi.html":           [NICE_TA1, NHS_YIRMI],
}

GIRIS = ("Bu sayfadaki bilgiler aşağıdaki kurumların yayınlarıyla uyumludur. "
         "Bağlantılar yeni sekmede açılır ve kliniğimizle ilgisi yoktur.")


def blok_uret(kaynaklar):
    satirlar = []
    for url, ad, kurum in kaynaklar:
        satirlar.append(
            '        <li><a href="%s" target="_blank" rel="noopener external">%s</a>'
            ' — %s</li>' % (url, ad, kurum))
    return (
        '    <h2 id="kaynaklar">Kaynaklar</h2>\n'
        '    <div class="kaynaklar">\n'
        '      <p>%s</p>\n'
        '      <ol>\n%s\n      </ol>\n'
        '    </div>\n' % (GIRIS, "\n".join(satirlar)))


def citation_uret(kaynaklar):
    return json.dumps(
        [{"@type": "WebPage", "name": ad, "url": url, "publisher":
          {"@type": "Organization", "name": kurum}}
         for url, ad, kurum in kaynaklar],
        ensure_ascii=False, separators=(",", ":"))


CAPA = re.compile(r'\n(  </div>\n\n  <p class="yazi-bilgi">)')
ESKI_BLOK = re.compile(
    r'    <h2 id="kaynaklar">Kaynaklar</h2>\n    <div class="kaynaklar">.*?</div>\n',
    re.S)
ESKI_CIT = re.compile(r'"citation":\[.*?\],\n(?="lastReviewed")', re.S)


def sayfa_isle(dosya, kaynaklar):
    yol = os.path.join(KOK, dosya)
    s = io.open(yol, encoding="utf-8").read()
    onceki = s

    s = ESKI_BLOK.sub("", s)          # tekrar calistirilabilir olsun
    s = ESKI_CIT.sub("", s)

    if not CAPA.search(s):
        return None, "capa bulunamadi (yazi-bilgi bloguna ulasilamadi)"
    s = CAPA.sub("\n" + blok_uret(kaynaklar) + r"\1", s, count=1)

    # Sema citation'i yalniz MedicalWebPage tasiyan sayfalara eklenir.
    # sik-sorulan-sorular.html'de yalniz FAQPage var; orada GORUNUR
    # kaynak bolumu yeter — olmayan bir sema alani uydurulmaz.
    if '"lastReviewed"' in s:
        s = s.replace('"lastReviewed"',
                      '"citation":%s,\n"lastReviewed"' % citation_uret(kaynaklar), 1)

    return s, ("degisti" if s != onceki else "ayni")


def main():
    uygula = "--uygula" in sys.argv
    yazilan = hata = 0
    for dosya in sorted(HARITA):
        if not os.path.exists(os.path.join(KOK, dosya)):
            print("  ATLANDI  %-34s dosya yok" % dosya); hata += 1; continue
        yeni, durum = sayfa_isle(dosya, HARITA[dosya])
        if yeni is None:
            print("  HATA     %-34s %s" % (dosya, durum)); hata += 1; continue
        if uygula:
            io.open(os.path.join(KOK, dosya), "w", encoding="utf-8",
                    newline="").write(yeni)
        yazilan += 1
        print("  %-8s %-34s %d kaynak" % ("YAZILDI" if uygula else "kuru",
                                          dosya, len(HARITA[dosya])))
    print("-" * 66)
    print("%d sayfa · %d hata%s" % (yazilan, hata,
          "" if uygula else "  ·  KURU CALISMA (--uygula ver)"))
    return 1 if hata else 0


if __name__ == "__main__":
    sys.exit(main())
