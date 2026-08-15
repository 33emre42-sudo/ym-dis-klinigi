#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DENETCININ KENDI TESTI — `denetle.py` gercekten yakaliyor mu?

    python test-denetle.py

Neden var: `denetle.py` sitenin mevzuat bekcisi. Bekcinin sessizce
korlesmesi, hic bekci olmamasindan daha tehlikeli — cunku "TAMAM"
yaziyor ve kimse bakmiyor. 2. tur Codex denetiminde tam bu cikti:
muafiyet mantigi butun yasak siniflarina uygulaniyordu ve
`alt="En iyi diş kliniği"` gibi oznitelikler hic taranmiyordu.

Her duzeltilen bulgu icin buraya bir KIRMIZI ornek (yakalanmali) ve
bir YESIL ornek (yanlis alarm vermemeli) eklenir.
"""
import io
import sys
import tempfile
import urllib.parse
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import mevzuat  # noqa: E402  — desenlerin tek kaynagi

sonuc = []


def bekle(ad, html, yakalanmali, ipucu="", kod=None):
    """yakalanmali=True  -> mevzuat_tara EN AZ bir sorun bulmali
       yakalanmali=False -> hic sorun bulmamali (yanlis alarm yok)
       kod              -> HANGI kuralin calistigi (or. "K15: taksit")

    ⚠️ 3. tur bulgu 8: `kod` eskiden yoktu. Test yalnizca "bir sorun
    bulundu mu" diye bakiyordu. "Kampanyamız başladı" ornegi hem
    YASAKLI hem TICARI tarafindan yakalandigi icin, TICARI muafiyeti
    tamamen bozuk olsa bile test GECIYORDU. Artik beklenen kural
    acikca dogrulaniyor."""
    sorunlar = mevzuat.mevzuat_tara(html, "test")
    gecti = bool(sorunlar) == yakalanmali
    if gecti and kod:
        gecti = any(s.startswith(kod) for s in sorunlar)
        if not gecti:
            ipucu = "BEKLENEN kural '%s' · BULUNAN: %s" % (kod, sorunlar[:3])
    if not gecti and not ipucu:
        ipucu = ("BEKLENEN: %s · BULUNAN: %s"
                 % ("yakala" if yakalanmali else "temiz",
                    sorunlar[:2] or "temiz"))
    sonuc.append((ad, gecti, ipucu))


def sar(govde):
    """Test parcasini gercekci bir HTML iskeletine oturtur."""
    return ("<!DOCTYPE html><html lang=\"tr\"><head>"
            "<meta charset=\"utf-8\"><title>Test</title></head>"
            "<body>%s</body></html>" % govde)


# --- 2. tur bulgu 5: MUAF fail-open ------------------------------------
# ⚠️ 5. tur bulgu 2: muafiyet artik ONAYLI_CUMLE ile TAM CUMLE
# esitligine dayaniyor. Bu blogun cumleleri, listedeki onayli
# bicimlere gore yazildi — senaryolar aynen korundu.
# Fiyat aciklamasi TEK BASINA gecmeli.
bekle("muaf: fiyat aciklamasi tek basina gecer",
      sar("<p>Mevzuat gereği fiyat bilgisi paylaşamıyoruz.</p>"),
      False)

# Ayni metne eklenen "en iyi" AFFEDILMEMELI. Eski kod bunu geciriyordu.
bekle("muaf: yakindaki fiyat aciklamasi 'en iyi'yi AFFETMEZ",
      sar("<p>Mevzuat gereği fiyat bilgisi paylaşamıyoruz. "
          "En iyi kliniğiz.</p>"),
      True)

# Ayni sekilde bagimsiz bir "kampanya" da affedilmemeli.
bekle("muaf: yakindaki aciklama 'kampanya'yi AFFETMEZ",
      sar("<p>Mevzuat gereği fiyat bilgisi paylaşamıyoruz. "
          "Kampanyamız başladı.</p>"),
      True)

# Muafiyet AYNI CUMLEDE calismaya devam etmeli.
bekle("muaf: ayni cumlede ucret aciklamasi gecer",
      sar("<p>Mevzuat gereği ücret bilgisi yayımlayamıyoruz.</p>"),
      False)

# --- 3. tur bulgu 5: muafiyet KENDI eslesmesine bagli olmali ----------
# Fiyat aciklamasi, komsu yan cumledeki BASKA bir ticari iddiayi
# affetmemeli.
bekle("muaf: komsu yan cumledeki 'taksit' AFFEDILMEZ",
      sar("<p>Mevzuat gereği fiyat bilgisi paylaşamıyoruz; "
          "taksit seçeneğimiz var.</p>"),
      True, kod="K15: taksit")

bekle("muaf: unlem sonrasi 'gece farki' AFFEDILMEZ",
      sar("<p>Mevzuat gereği fiyat bilgisi paylaşamıyoruz! "
          "Gece farkı almıyoruz.</p>"),
      True, kod="K15: gece farkı")

# Ayri, noktasiz HTML parcalari birbirini affetmemeli.
bekle("muaf: ayri parcalar birbirini AFFETMEZ",
      "<!DOCTYPE html><html><head>"
      "<meta name=\"description\" content=\"Fiyat yayımlayamıyoruz\">"
      "</head><body><p>Taksit imkânı</p></body></html>",
      True, kod="K15: taksit")

# --- 2. tur bulgu 6: oznitelikler taranmiyordu -------------------------
bekle("oznitelik: img alt icindeki 'en iyi' yakalanir",
      sar('<img src="a.jpg" alt="En iyi diş kliniği">'),
      True)

bekle("oznitelik: aria-label icindeki 'ucretsiz' yakalanir",
      sar('<button aria-label="Ücretsiz muayene">Tıkla</button>'),
      True)

bekle("oznitelik: title icindeki fiyat rakami yakalanir",
      sar('<a href="#" title="Muayene 500 TL">Bilgi</a>'),
      True)

bekle("oznitelik: placeholder icindeki 'garanti' yakalanir",
      sar('<input placeholder="Garantili tedavi">'),
      True)

bekle("oznitelik: masum alt metni yanlis alarm vermez",
      sar('<img src="a.jpg" alt="Kliniğin haritadaki konumu">'),
      False)

# --- 3. tur bulgu 6: tek tirnak, HTML varligi, gizli alan -------------
bekle("oznitelik: TEK TIRNAKLI alt yakalanir",
      sar("<img src='a.jpg' alt='En iyi diş kliniği'>"),
      True, kod="en iyi")

bekle("oznitelik: HTML varligiyla gizlenen ihlal yakalanir",
      sar('<img src="a.jpg" alt="En &#105;yi diş kliniği">'),
      True, kod="en iyi")

bekle("oznitelik: tek tirnakli meta content yakalanir",
      "<!DOCTYPE html><html><head>"
      "<meta name='description' content='Ücretsiz muayene'>"
      "</head><body><p>x</p></body></html>",
      True, kod="ucretsiz")

bekle("oznitelik: GIZLI input degeri yanlis alarm VERMEZ",
      sar('<input type="hidden" value="kampanya_v2">'),
      False)

bekle("oznitelik: gorunur dugme degeri taranir",
      sar('<input type="submit" value="Ücretsiz randevu">'),
      True, kod="ucretsiz")

# --- 3. tur bulgu 7: mesru guvenlik metni ENGELLENMEMELI --------------
bekle("mesru: 'sonuç garanti edilemez' GECER",
      sar("<p>Hiçbir tedavinin sonucu garanti edilemez; iyileşme "
          "kişiden kişiye değişir.</p>"),
      False)

bekle("mesru: 'kampanya bulunmamaktadır' GECER",
      sar("<p>Kliniğimizde kampanya bulunmamaktadır.</p>"),
      False)

# 2 Agu 2026: "sindirim" icindeki "indirim" K15 alarmi veriyordu —
# TICARI deseninde kelime siniri yoktu. Tibbi metin yazarken cikti.
bekle("mesru: 'sindirim sistemi' YANLIS ALARM VERMEZ",
      sar("<p>Reflü ve bazı sindirim sistemi sorunları da ağız "
          "kokusuna yol açabilir.</p>"), False)

bekle("gerileme: gercek 'indirim' hala YAKALANIR",
      sar("<p>Bu ay implantta indirim var.</p>"), True)

bekle("mesru: sosyoekonomik cumle GECER",
      sar("<p>Ekonomik koşullar ağız sağlığı hizmetine erişimi "
          "etkileyebilir.</p>"),
      False)

# Ama gercek iddialar hala yakalanmali:
bekle("gerileme: 'garanti ediyoruz' hala yakalanir",
      sar("<p>Sonucu garanti ediyoruz.</p>"), True, kod="garanti")

bekle("gerileme: 'kampanyamız başladı' hala yakalanir",
      sar("<p>Kampanyamız başladı.</p>"), True, kod="kampanya")

bekle("ortulu ticari: 'ekonomik tedavi' yakalanir",
      sar("<p>Ekonomik tedavi seçenekleri sunuyoruz.</p>"),
      True, kod="K15: ekonomik tedavi")

# --- 4. tur bulgu 4: OLUMSUZLUGU TERSINE CEVIREN cumleler -------------
# 3. turdaki ileri bakis bunlari muaf sayiyordu; hepsi ticari iddia.
bekle("tersine cevirme: 'Garanti etmez değiliz' YAKALANIR",
      sar("<p>Garanti etmez değiliz.</p>"), True, kod="garanti")

bekle("tersine cevirme: 'Kampanya yoktur sanmayın' YAKALANIR",
      sar("<p>Kampanya yoktur sanmayın.</p>"), True, kod="kampanya")

bekle("tersine cevirme: 'İndirim yoktur demiyoruz' YAKALANIR",
      sar("<p>İndirim yoktur demiyoruz.</p>"), True, kod="indirim")

# Onaylanmis TAM cumleler hala yesil:
bekle("beyaz liste: onayli garanti cumlesi GECER",
      sar("<p>Hiçbir tedavinin sonucu garanti edilemez; sonuç kişiden "
          "kişiye değişir.</p>"), False)

bekle("beyaz liste: onayli kampanya cumlesi GECER",
      sar("<p>Kliniğimizde kampanya bulunmamaktadır.</p>"), False)

# --- 6. tur bulgu 3: NOKTALAMA ILE TERSLEME -------------------------
# Muafiyet "eslesmenin cumlesi onayli mi" diye bakiyordu ve `;` `:` `.`
# cumleyi bitirdigi icin tersine cevirme AYRI bir cumleye tasinabiliyordu.
# Denetci uc yolu da gosterdi; ucu de denetimden geciyordu. Sozlesme
# "cevresine ek yazilamaz" diyordu — dogru degildi.
bekle("tersleme: '; demiyoruz' YAKALANIR",
      sar("<p>Hiçbir tedavinin sonucu garanti edilemez; demiyoruz.</p>"),
      True, kod="garanti")

bekle("tersleme: ': aslında paylaşabiliriz' YAKALANIR",
      sar("<p>Mevzuat gereği fiyat bilgisi paylaşamıyoruz: aslında "
          "paylaşabiliriz.</p>"), True)

bekle("tersleme: '. Demiyoruz.' AYRI CUMLEDE YAKALANIR",
      sar("<p>Hiçbir tedavinin sonucu garanti edilemez. Demiyoruz.</p>"),
      True, kod="garanti")

bekle("tersleme: 'tam tersi' YAKALANIR",
      sar("<p>Kliniğimizde kampanya bulunmamaktadır. Tam tersi.</p>"),
      True, kod="kampanya")

# --- 7. tur bulgu 1: _TERSLEME iki yonlu hataliydi ------------------
# Denetci dort ornek verdi, dordu de calistirilarak dogrulandi.
# KACIYORDU: listede olmayan tersleme, ve araya notr cumle koyarak gizleme.
bekle("tersleme: '. Öyle değil.' YAKALANIR",
      sar("<p>Hiçbir tedavinin sonucu garanti edilemez. Öyle değil.</p>"),
      True, kod="garanti")

bekle("tersleme: araya notr cumle koyarak GIZLENEMEZ",
      sar("<p>Hiçbir tedavinin sonucu garanti edilemez. "
          "Bu yalnızca bir açıklamadır. Tam tersi.</p>"),
      True, kod="garanti")

# YANLIS ALARM veriyordu: yalin "gercekte/aslinda" aciklama baglacidir,
# tersleme degil. Bunlar yazmamiz GEREKEN cumleler.
# --- 8. tur bulgu 4: konu siniri --------------------------------------
# "Uc cumle" butcesi HTML blok ayraclarini da sayiyordu; ayri
# paragraflara yazilan tersleme butceyi tuketip KACIYORDU.
bekle("tersleme: AYRI PARAGRAFLARDA gizlenemez",
      sar("<p>Hiçbir tedavinin sonucu garanti edilemez.</p>"
          "<p>Bu yalnızca genel bir açıklamadır.</p>"
          "<p>Tam tersi.</p>"), True, kod="garanti")

bekle("tersleme: ayni paragrafta DORDUNCU cumlede gizlenemez",
      sar("<p>Hiçbir tedavinin sonucu garanti edilemez. "
          "Bu açıklama geneldir. Her hasta farklıdır. "
          "Muayene gerekir. Tam tersi.</p>"), True, kod="garanti")

# Korumanin bedeli: YENI BIR BASLIK altindaki bagimsiz "Tam tersi"
# yanlis alarm vermemeli. Konu siniri tam bunun icin.
bekle("mesru: yeni basliktaki bagimsiz 'Tam tersi' GECER",
      sar("<p>Hiçbir tedavinin sonucu garanti edilemez.</p>"
          "<h2>Kanayan yeri fırçalamamak doğru mu?</h2>"
          "<p>Tam tersi. Nazikçe temizliğe devam edilmelidir.</p>"), False)

# --- 8. tur bulgu 5: Turkce cekimler ----------------------------------
bekle("ticari cekim: 'ödemeyi' YAKALANIR",
      sar("<p>Ödemeyi çevrim içi yapabilirsiniz.</p>"), True)

bekle("ticari cekim: 'ödemeye' YAKALANIR",
      sar("<p>Ödemeye ilişkin bilgi alın.</p>"), True)

bekle("ticari cekim: 'paketimizden' YAKALANIR",
      sar("<p>Tedavi paketimizden yararlanabilirsiniz.</p>"), True)

# --- 9. tur bulgu 3: istisnalar cekimleri kapsamiyordu ---------------
# `ödemesi` istisnasi yalnizca YALIN hali kapsiyordu; dogal tibbi
# cekimler yanlis alarm veriyordu. "steril paketli" de ticari sanildi.
bekle("ticari: tibbi 'doku ödemesinin' YANLIS ALARM VERMEZ",
      sar("<p>Yumuşak doku ödemesinin azalması beklenir.</p>"), False)

bekle("ticari: tibbi 'doku ödemesine' YANLIS ALARM VERMEZ",
      sar("<p>Doku ödemesine karşı soğuk uygulama önerilebilir.</p>"),
      False)

bekle("ticari: 'steril paketli alet' YANLIS ALARM VERMEZ",
      sar("<p>Steril paketli alet işlem öncesinde açılır.</p>"), False)

# Istisnalar gercek ticari dili ortmemeli:
bekle("gerileme: 'Ödemeyi kredi kartıyla' YAKALANIR",
      sar("<p>Ödemeyi kredi kartıyla yapabilirsiniz.</p>"), True)

bekle("gerileme: 'tedavi paketlidir' YAKALANIR",
      sar("<p>Tedavi paketlidir ve uygun fiyat sunar.</p>"), True)

bekle("mesru devam: 'Gerçekte iyileşme değişir' GECER",
      sar("<p>Hiçbir tedavinin sonucu garanti edilemez. "
          "Gerçekte iyileşme kişiden kişiye değişir.</p>"), False)

bekle("mesru devam: 'Aslında bu durum sık görülür' GECER",
      sar("<p>Hiçbir tedavinin sonucu garanti edilemez. "
          "Aslında bu durum sık görülür.</p>"), False)

# --- 7. tur bulgu 6: TICARI tibbi kelimeleri yakaliyordu -------------
bekle("ticari: tibbi 'doku ödemesi' YANLIS ALARM VERMEZ",
      sar("<p>Çekim sonrası yumuşak doku ödemesi olabilir.</p>"), False)

bekle("ticari: 'steril paketleme' YANLIS ALARM VERMEZ",
      sar("<p>Aletler steril paketleme sonrasında saklanır.</p>"), False)

bekle("ticari: tibbi 'dahildir' YANLIS ALARM VERMEZ",
      sar("<p>Bu bulgu değerlendirmeye dahildir.</p>"), False)

bekle("gerileme: gercek 'ödeme' hala YAKALANIR",
      sar("<p>Ödeme seçenekleri için bizi arayın.</p>"), True)

bekle("gerileme: gercek 'paket' hala YAKALANIR",
      sar("<p>Tedavi paketlerimiz vardır.</p>"), True)

# Korumanin bedeli olmamali: MESRU devam cumleleri yesil kalmali.
# Ilk denemede sinirdan `;` cikarilmisti ve bu iki cumle kirmiziya
# donmustu — yazmamiz GEREKEN durustce aciklamalar tam bu bicimde.
bekle("mesru devam: '; iyileşme kişiden kişiye değişir' GECER",
      sar("<p>Hiçbir tedavinin sonucu garanti edilemez; iyileşme "
          "kişiden kişiye değişir.</p>"), False)

bekle("mesru devam: ayri cumlede aciklama GECER",
      sar("<p>Hiçbir tedavinin sonucu garanti edilemez. Sonuç muayenede "
          "değerlendirilir.</p>"), False)

# --- 4. tur bulgu 6: teknik value'lar yanlis alarm vermemeli ----------
bekle("value: <button value> TEKNIK, alarm VERMEZ",
      sar('<button value="kampanya_v2">Gönder</button>'), False)

bekle("value: <option value> TEKNIK, alarm VERMEZ",
      sar('<select><option value="ekonomik">Standart</option></select>'),
      False)

# --- Cift kodlama tespiti (1 Agu 2026 olayi) --------------------------
# index.html'in butun Turkce karakterleri bir kabuk komutu yuzunden
# cift kodlandi ve 20 dakika oyle yayinda kaldi. Hicbir denetim
# gormedi: dosya gecerli UTF-8, kelime sayisi normal, yasak kelime yok.
#
# Ilk yazdigim tespit fonksiyonu HASARI KACIRIYORDU: gercek bozuk
# dosyada 41 adet U+009E vardi ve `encode("cp1254")` bu karakterde
# hata verip "temiz" sonucunu donduruyordu. Asagidaki testler tam o
# durumu yeniden uretiyor.
def kodlama_bekle(ad, metin, bozuk_olmali):
    oldu = mevzuat.cift_kodlanmis(metin)
    sonuc.append((ad, oldu == bozuk_olmali,
                  "" if oldu == bozuk_olmali
                  else "BEKLENEN: %s · BULUNAN: %s" % (bozuk_olmali, oldu)))


def hasar_uret(saglam):
    """PowerShell'in yaptigi seyin birebir taklidi."""
    return mevzuat.ansi_okumasi(saglam.encode("utf-8"))


SAGLAM = ("YM Diş Kliniği — Bağcılar/Kirazlı. Şikâyetiniz varsa "
          "kliniğimize başvurunuz. Çocuk diş hekimliği, implant, "
          "protez ve kanal tedavisi.")

kodlama_bekle("kodlama: saglam Turkce metin TEMIZ", SAGLAM, False)
kodlama_bekle("kodlama: cift kodlanmis metin YAKALANIR",
              hasar_uret(SAGLAM), True)
# Gercek hasarda 0x9E vardi ("Ş" harfinin ikinci bayti) — ilk
# fonksiyonu tam bu karakter atlatmisti.
kodlama_bekle("kodlama: U+009E iceren hasar YAKALANIR",
              hasar_uret("BAĞCILAR · ŞİŞLİK · DİŞ HEKİMLİĞİ"), True)
kodlama_bekle("kodlama: sadece ASCII yanlis alarm VERMEZ",
              "Plain ascii content, nothing to see here.", False)
kodlama_bekle("kodlama: Turkce + emoji TEMIZ",
              "Diş 🦷 randevu · ⚠️ acil durumda 112", False)
kodlama_bekle("kodlama: cift kodlanmis emoji YAKALANIR",
              hasar_uret("Diş 🦷 randevu"), True)

# --- 8. tur bulgu 6: IZOLE karakter bozulmasi -------------------------
# Yukaridaki emoji testi aslinda emojiyi degil "Diş" icindeki `ÅŸ` izini
# yakaliyordu. Saglam Turkce metnin icine YALNIZCA bozuk bir ozel
# karakter girerse (tam metin cozumu saglam Turkce'de patlar, ozel iz de
# listede yoksa) kismi hasar kaciyordu. Yedisi de dogrulandi.
for _ad, _kar in (("telif ©", "©"), ("carpi ×", "×"),
                  ("sapkali a", "â"), ("sapkali i", "î"),
                  ("sag ok →", "→"), ("yildiz ✦", "✦"),
                  ("dis emojisi", "🦷")):
    kodlama_bekle("kodlama: yalniz bozuk %s izi YAKALANIR" % _ad,
                  SAGLAM + " / " + hasar_uret(_kar), True)

kodlama_bekle("kodlama: saglam ozel karakterler YANLIS ALARM VERMEZ",
              "Resmî açıklama © 2×2 → bilgi ✦ 🦷", False)

# --- 9. tur bulgu 4: BIRLESTIRICI KARAKTER --------------------------
# iletisim.html'de baslik "Çalişma saatleri̇." diye yayina cikmisti:
# `"ÇALIŞMA SAATLERİ".capitalize()` Turkce bilmedigi icin "İ" harfini
# "i" + U+0307 COMBINING DOT ABOVE'a cevirmisti. Ekranda neredeyse
# dogru gorunuyor; cift kodlama kontrolu de goremiyor — ayri sinif.
def birlestirici_bekle(ad, metin, olmali):
    var = bool(mevzuat.birlestirici_var(metin))
    sonuc.append((ad, var == olmali,
                  "" if var == olmali
                  else "BEKLENEN: %s · BULUNAN: %s" % (olmali, var)))


# Once hasarin gercekten olustugunu kanitla — yoksa asagidaki test
# hicbir sey ispatlamaz.
_capitalize_hatasi = "ÇALIŞMA SAATLERİ".capitalize()
sonuc.append(("kodlama: capitalize() Turkce'yi gercekten bozuyor",
              "̇" in _capitalize_hatasi,
              "" if "̇" in _capitalize_hatasi
              else "bozukluk uretilemedi: %r" % _capitalize_hatasi))

birlestirici_bekle("kodlama: birlestirici karakter YAKALANIR",
                   _capitalize_hatasi, True)
birlestirici_bekle("kodlama: saglam Turkce'de birlestirici YOK",
                   "Çalışma saatleri · Diş Kliniği · Bağcılar", False)

# --- 6. tur bulgu 5: KISMI ve GEC hasar ------------------------------
# Tespit iki yerden kaciriyordu: (1) yalnizca ilk 40.000 karaktere
# bakiyordu — index.html 89.000'den uzun, yani yarisindan cogu hic
# taranmiyordu; (2) TUM ornegin cozulmesini bekliyordu, oysa saglam
# Turkce bir bolum cozumu patlatir. Gercek hasar da boyle gorunur:
# dosyanin bir bolumu bozulur, gerisi saglam kalir.
kodlama_bekle("kodlama: saglam metin + TEK bozuk parca YAKALANIR",
              SAGLAM + " " + hasar_uret("Diş"), True)

kodlama_bekle("kodlama: 40.000 karakterden SONRAKI hasar YAKALANIR",
              "A" * 40001 + hasar_uret("Şişlik"), True)

kodlama_bekle("kodlama: uzun SAGLAM metin yanlis alarm VERMEZ",
              (SAGLAM + " ") * 400, False)

# --- 7. tur bulgu 5: iz taramasi tek karaktere bakiyordu -------------
# Sitede cok kullanilan noktalamanin cift kodlanmis hali Ã/Ä/Å
# ICERMIYOR: "—" -> "â€”", "·" -> "Â·", "’" -> "â€™". Yalnizca
# noktalamasi bozulmus kismi hasar tespitten kaciyordu.
kodlama_bekle("kodlama: bozuk EM DASH (—) YAKALANIR",
              SAGLAM + " " + hasar_uret("—"), True)
kodlama_bekle("kodlama: bozuk ORTA NOKTA (·) YAKALANIR",
              SAGLAM + " " + hasar_uret("·"), True)
kodlama_bekle("kodlama: bozuk KESME (’) YAKALANIR",
              SAGLAM + " " + hasar_uret("’"), True)

# Ters yon: tek basina "Å" iceren gecerli bir yabanci ozel ad
# hasarli sayilmamali.
kodlama_bekle("kodlama: 'Ångström' YANLIS ALARM VERMEZ",
              "Uzunluk Ångström birimiyle de ifade edilebilir.", False)

# --- 10. tur bulgu 1: ACIL ESIGI ATESE BAGLANAMAZ ---------------------
# 112 gerektiren belirtiler "ve" ile atese baglanirsa cumle "ikisi de
# olmali" diye okunur. Hava yolu belirtisi TEK BASINA acildir; ates ise
# ayni gun degerlendirme esigi. Hasta "atesim yok, beklerim" derse
# gecikme olur.
def acil_bekle(ad, parca, olmali):
    bulunan = mevzuat.acil_esik_hatalari(parca)
    sonuc.append((ad, bool(bulunan) == olmali,
                  "" if bool(bulunan) == olmali
                  else "BEKLENEN: %s · BULUNAN: %s" % (olmali, bulunan[:1])))


# Gercekte YAYINDA olan cumle — dis-apsesi.html dokuz tur denetimden
# gecti ve kimse gormedi. Once yakalandigini kanitla.
acil_bekle("acil esik: 've yüksek ateş' kalibi YAKALANIR",
           "<p>Göze ya da boyuna yayılan şişlik, nefes veya yutma "
           "güçlüğü ve yüksek ateş acil durumdur: "
           "<strong>112'yi arayın.</strong></p>", True)

acil_bekle("acil esik: diyabet sayfasindaki hali YAKALANIR",
           "<p>Yüzde hızla yayılan şişlik, nefes ya da yutma güçlüğü ve "
           "yüksek ateş varsa beklemeyin: <strong>112'yi arayın.</strong>"
           "</p>", True)

# Duzeltilmis hali: ates AYRI cumlede.
acil_bekle("acil esik: ates ayri cumledeyse TEMIZ",
           "<p>Nefes ya da yutma güçlüğü, bilinç bulanıklığı varsa "
           "beklemeyin: <strong>112'yi arayın.</strong> Bu belirtiler "
           "olmadan yüksek ateş varsa aynı gün değerlendirilmeniz "
           "gerekir.</p>", False)

# YANLIS ALARM KAPISI: listedeki "Yüksek ateş" maddesi ile alttaki 112
# paragrafi AYRI bloklardir. Ilk yazdigim surum bunu hata sayiyordu —
# butun acil kutulari kirmizi yanardi.
acil_bekle("acil esik: <li> ates + <p> 112 yanlis alarm VERMEZ",
           "<div class=\"uyari\"><ul>"
           "<li>Yüksek ateş, titreme, bilinç bulanıklığı</li>"
           "<li>Ağzı tam açamama</li></ul>"
           "<p>Nefes alma veya yutkunma güçlüğü varsa "
           "<strong>112'yi arayın.</strong></p></div>", False)

acil_bekle("acil esik: atessiz 112 cumlesi TEMIZ",
           "<p>Bilinç değişikliği, nöbet ya da nefes alma güçlüğünde "
           "112'yi arayın.</p>", False)

# --- 11. tur bulgu 2: tehlike atese ozgu degil --------------------------
# Tek basina acil olan bir belirtiyi "ve" ile ikinci bir bulguya baglamak
# atessiz de ayni yanlis okumayi uretiyor.
acil_bekle("acil esik: atessiz 've' baglamasi YAKALANIR",
           "<p>Nefes güçlüğü ve şiddetli ağrı varsa "
           "<strong>112'yi arayın.</strong></p>", True)

acil_bekle("acil esik: 112 basta yazilsa da 've' baglamasi YAKALANIR",
           "<p>Şunlarda <strong>112'yi arayın:</strong> "
           "nefes güçlüğü ve şiddetli ağrı.</p>", True)

acil_bekle("acil esik: 'nefes ve yutma güçlüğü' YAKALANIR",
           "<p>Nefes ve yutma güçlüğünde <strong>112'yi arayın.</strong>"
           "</p>", True)

acil_bekle("acil esik: acik alternatif ('veya') TEMIZ",
           "<p>Nefes veya yutma güçlüğü varsa "
           "<strong>112'yi arayın.</strong></p>", False)

# ⚠️ Denetci "cumlede veya/ya da varsa muaf tut" onerdi; o kacis kapisi
# asagidaki gercek hatayi SUSTURURDU. Dar kalip kullanildigi icin
# yakalaniyor — bu test o karari koruyor.
acil_bekle("acil esik: mesru 'veya' hatayi GIZLEYEMEZ",
           "<p>Nefes veya yutma güçlüğü ve şiddetli ağrı varsa "
           "<strong>112'yi arayın.</strong></p>", True)

# Ters yon: belirti olmayan bir kelimeden sonraki "ve" yanlis alarm
# vermemeli. "yüzde" bir belirti degil, "yüzde ve boyunda" mesru.
acil_bekle("acil esik: 'yüzde ve boyunda' yanlis alarm VERMEZ",
           "<p>Nefes ya da yutma güçlüğü, yüzde ve boyunda hızla yayılan "
           "şişlik varsa beklemeyin: <strong>112'yi arayın.</strong></p>",
           False)

# --- 12. tur bulgu 4: desen genisletildi ---------------------------------
acil_bekle("acil esik: TERS SIRA ('… ve nefes güçlüğü') YAKALANIR",
           "<p>Şiddetli ağrı ve nefes güçlüğü varsa "
           "<strong>112'yi arayın.</strong></p>", True)

acil_bekle("acil esik: 'hem … hem' YAKALANIR",
           "<p>Hem nefes güçlüğü hem şiddetli ağrı varsa "
           "<strong>112'yi arayın.</strong></p>", True)

acil_bekle("acil esik: HAL EKLI bicim ('güçlüğünde ve') YAKALANIR",
           "<p>Nefes güçlüğünde ve şiddetli ağrıda "
           "<strong>112'yi arayın.</strong></p>", True)

acil_bekle("acil esik: ASCII 'ates' YAKALANIR",
           "<p>Yuksek ates ve nefes guclugu varsa "
           "<strong>112'yi arayin.</strong></p>", True)

acil_bekle("acil esik: 'durdurulamayan kanama' belirti sayilir",
           "<p>Durdurulamayan kanama ve ağrı varsa "
           "<strong>112'yi arayın.</strong></p>", True)

# ⚠️ Denetci "ile"yi de baglac saymayi onerdi. ALINMADI: asagidaki cumle
# mesru ve "ile" orada baglac degil. Yanlis alarm veren bekci kapatilir.
acil_bekle("acil esik: 'ile karşılaşırsanız' yanlis alarm VERMEZ",
           "<p>Nefes güçlüğü ile karşılaşırsanız "
           "<strong>112'yi arayın.</strong></p>", False)

# --- 13. tur bulgu 4: "ve"/"hem" disindaki baglaclar ---------------------
# "ile birlikte" ve "eşlik ediyorsa" tek basina acil bir belirtiyi ikinci
# bir bulguya bagimli kilabiliyordu; desen yalnizca "ve"/"hem" ariyordu.
acil_bekle("acil esik: 'ile birlikte' YAKALANIR",
           "<p>Nefes güçlüğü ile birlikte ateş varsa "
           "<strong>112'yi arayın.</strong></p>", True)

acil_bekle("acil esik: YONELME hali + 'eşlik ediyorsa' YAKALANIR",
           "<p>Nefes güçlüğüne şiddetli ağrı eşlik ediyorsa "
           "<strong>112'yi arayın.</strong></p>", True)

acil_bekle("acil esik: 'yanında' YAKALANIR",
           "<p>Yutkunma güçlüğü yanında ağrı varsa "
           "<strong>112'yi arayın.</strong></p>", True)

# ⚠️ YANLIS ALARM KAPISI — kan-sulandirici-dis-tedavisi.html'de YAYINDA
# olan cumle. Burada "eşlik ediyorsa" bir 112 sebebini kisitlamiyor,
# "ya da" ile listeye YENI bir sebep ekliyor. Cumle duzeyinde
# "belirti + kesin baglac" arayan ilk surumum bunu kirmizi yakti;
# komsuluk/yonelme sarti tam da bunu onlemek icin var.
acil_bekle("acil esik: eklenen sebep olarak 'eşlik ediyorsa' TEMIZ",
           "<p><strong>Şunlarda 112'yi arayın:</strong> kanama baskıya "
           "rağmen durmuyorsa, ağzınızı hızla dolduruyorsa ya da kanamaya "
           "belirgin baş dönmesi, bayılacak gibi olma, nefes darlığı veya "
           "çarpıntı eşlik ediyorsa.</p>", False)

# --- 13. tur: duz "nefes" hayati belirti DEGILDIR -----------------------
# Nitelemeler istege bagliydi; blok duzeyinde tarayan yeni surum
# agiz-kurulugu.html'deki mesru cumleyi kirmizi yakti.
# --- 15. tur SITE bulgu 2: KESIN KIPTE SONUC VAADI ----------------------
# ⚠️ "Bunların hepsi gece başlatılabilir — ağrı varsa GIDERILIR" cumlesi
# YAYINA GIRDI. Bekci "ağrısız/garanti/en iyi" ariyordu; kesin kipte
# cozum vaadini gormuyordu. Her agri tek ziyarette tamamen
# giderilemeyebilir; hasta kesin rahatlama bekleyip yola cikar.
for _m in ("Ağrı varsa giderilir.", "Ağrınız giderilir.",
           "Ağrınız geçer.", "Şikâyetiniz biter.", "Sorununuz çözülür."):
    bekle("sonuc vaadi: %r YAKALANIR" % _m,
          "<p>%s</p>" % _m, True, kod="sonuc vaadi")
# ⚠️ YANLIS ALARM KAPISI — hepsi sitede GERCEKTEN kullanilan mesru
# ifadeler. Kalip OZNEYE bagli: hastanin sikayetine kesin soz mu
# veriliyor, yoksa klinik sira/imkan mi anlatiliyor?
for _m in ("Önceliğimiz ağrının giderilmesi ve durumun kontrolü.",
           "Yüzeydeki renklenmenin bir kısmı temizlikle giderilebilir.",
           "Çürük ve dişeti sorunları tedaviye başlamadan önce giderilir.",
           "Varsa ağrıyı azaltmaya yönelik işlem yapılabilir.",
           "Hekiminizin önerdiği ağrı kesiciyle geçmeyen ağrı.",
           "Ağrı kendiliğinden geçerse ne olur?"):
    bekle("sonuc vaadi: %r yanlis alarm VERMEZ" % _m[:34],
          "<p>%s</p>" % _m, False)

# --- 14. tur bulgu 2: kesin baglacin TERS yonu ---------------------------
# 13. turdaki iki bicim de belirtinin ONCE gelmesini bekliyordu. Bagimlilik
# ters sirayla da kurulabiliyor ve anlami ayni: agrisi olmayan hasta bekler.
acil_bekle("acil esik: TERS 'ile birlikte' YAKALANIR",
           "<p>Şiddetli ağrıyla birlikte nefes güçlüğü varsa "
           "<strong>112'yi arayın.</strong></p>", True)

acil_bekle("acil esik: TERS 'eşlik ettiği' YAKALANIR",
           "<p>Şiddetli ağrının eşlik ettiği nefes güçlüğünde "
           "<strong>112'yi arayın.</strong></p>", True)

acil_bekle("acil esik: ayri yazilmis 'ile birlikte' YAKALANIR",
           "<p>Yüksek ateş ile birlikte yutkunma güçlüğü varsa "
           "<strong>112'yi arayın.</strong></p>", True)

# --- 14. tur bulgu 3: sitede KULLANILAN iki belirti bicimi ---------------
# Ikisi de dis-cekimi-sonrasi-sislik.html'de gecen dogru ifadeler, ama
# desende yoktu: "dilinizin altı şişmişse" (agiz tabaninin es anlamlisi)
# ve "şişlik … hızla yayılıyorsa" (mevcut kalibin ters sozcuk sirasi).
acil_bekle("acil belirti: 'dilinizin altı şişmişse' baglamasi YAKALANIR",
           "<p>Dilinizin altı şişmişse ve şiddetli ağrı varsa "
           "<strong>112'yi arayın.</strong></p>", True)

acil_bekle("acil belirti: TERS sirali 'şişlik hızla yayılıyorsa' YAKALANIR",
           "<p>Yüzde şişlik hızla yayılıyorsa ve şiddetli ağrı varsa "
           "<strong>112'yi arayın.</strong></p>", True)

# YANLIS ALARM KAPISI: "dil altı" anatomik olarak da geciyor —
# sigara-ve-agiz-sagligi.html'de muayene anlatiminda. Sislik sarti var.
acil_bekle("acil belirti: anatomik 'dil altı' yanlis alarm VERMEZ",
           "<p>Rutin muayenede yanak içi, dil, dil altı ve damak da "
           "değerlendirilir. Şüpheli bir bulguda 112 gerekmez.</p>", False)

acil_bekle("acil esik: nitelemesiz 'nefes' yanlis alarm VERMEZ",
           "<p>Gece odayı nemlendirin ve burundan nefes almayı "
           "destekleyin. Şikâyet sürerse 112'yi değil kliniği arayın.</p>",
           False)


# --- 12. tur bulgu 4(d): 112'siz kutu MIMARI OLARAK gorunmuyordu --------
# Eski bekci "112 gecmiyorsa bu bloga bakma" diyordu. Hayati belirtiyi
# yalniz klinige yonlendiren bir kutu bu yuzden GORUNMEZDI —
# yirmi-yas-disi.html tam olarak boyleydi ve dokuz tur denetimden gecti.
def klinik_bekle(ad, parca, olmali):
    bulunan = mevzuat.acil_klinige_yonlendirme_hatalari(parca)
    sonuc.append((ad, bool(bulunan) == olmali,
                  "" if bool(bulunan) == olmali
                  else "BEKLENEN: %s · BULUNAN: %s" % (olmali, bulunan[:1])))


klinik_bekle("klinik esigi: hayati belirti + 112 YOK -> YAKALANIR",
             '<div class="uyari"><b>Şu durumlarda hemen arayın</b><ul>'
             '<li>Yüksek ateş, yutkunma ya da nefes güçlüğü</li>'
             '<li>Giderek artan şişlik</li></ul></div>', True)

klinik_bekle("klinik esigi: ayni kutuda 112 varsa TEMIZ",
             '<div class="uyari"><b>Şunlarda kliniği arayın</b><ul>'
             '<li>Giderek artan şişlik</li></ul>'
             '<p>Nefes güçlüğü varsa 112\'yi arayın.</p></div>', False)

klinik_bekle("klinik esigi: hayati belirti YOKSA yanlis alarm VERMEZ",
             '<div class="uyari"><b>Şunlarda kliniği arayın</b><ul>'
             '<li>Giderek artan şişlik ve ağrı</li>'
             '<li>Dikiş erken açıldıysa</li></ul></div>', False)

klinik_bekle("klinik esigi: klinige yonlendirmeyen kutu TEMIZ",
             '<div class="uyari"><b>Olağan olanlar</b><ul>'
             '<li>İlk günlerde hafif şişlik</li></ul></div>', False)

# --- 13. tur bulgu 3: KUTU BOYU MUAFIYET ve DAR KALIP -------------------
# (a) Eski kod "kutuda 112 geciyorsa kutuya hic bakma" diyordu. Muafiyet
#     tam da korunmasi gereken cumleyi ortuyordu: 112 bir belirti icin
#     verilip DIGERI klinige yonlendirilince kutu temiz cikiyordu.
klinik_bekle("klinik esigi: kutuda 112 VARKEN ikinci belirti klinige -> YAKALANIR",
             '<div class="uyari">'
             '<p>Kanama durmuyorsa 112\'yi arayın.</p>'
             '<p>Nefes güçlüğü varsa kliniği arayın.</p></div>', True)

# (b) Kalip dort mesru yonlendirme bicimini kaciriyordu ve dordu de
#     sitede GERCEKTEN kullaniliyor. Rica kipi de emir kipi kadar
#     "acile degil buraya gel" demektir.
klinik_bekle("klinik esigi: 'kliniği arayabilirsiniz' YAKALANIR",
             '<p>Nefes güçlüğü varsa kliniği arayabilirsiniz.</p>', True)

klinik_bekle("klinik esigi: 'kliniğe gelin' YAKALANIR",
             '<p>Ağız tabanında şişlik varsa kliniğe gelin.</p>', True)

klinik_bekle("klinik esigi: 'kliniğe başvurun' YAKALANIR",
             '<p>Bilinç değişikliği varsa kliniğe başvurun.</p>', True)

klinik_bekle("klinik esigi: 'değerlendirmesi alın' YAKALANIR",
             '<p>Yutkunma güçlüğü varsa diş hekimi değerlendirmesi '
             'alın.</p>', True)

# (c) Kapsam kutu disina cikti: ayni desen duz paragrafta da kullaniliyor.
klinik_bekle("klinik esigi: kutusuz paragraf da taranir",
             '<p>Nefes güçlüğünde hemen arayın: 0541 732 43 76</p>', True)

# YANLIS ALARM KAPISI: 112 ile klinik AYNI cumlede ayrilmissa temiz.
klinik_bekle("klinik esigi: esigi ayiran cumle TEMIZ",
             '<p>Nefes güçlüğü varsa 112\'yi arayın. Bu belirtiler yoksa '
             'kliniği arayabilirsiniz.</p>', False)

# --- 14. tur bulgu 1: BASLIK MIRASI -------------------------------------
# 13. turdaki cumle bolmenin kalan deligi: noktalamasiz listede kutunun
# tamami TEK cumle sayiliyor, icinde 112 gectigi icin eleniyor. Tek
# basina <li> ise yonlendirmeyi tasimiyor — o BASLIKTA. Ikisi hicbir
# birimde bulusmuyordu.
klinik_bekle("klinik esigi: BASLIK yonlendirmesi <li>'ye miras -> YAKALANIR",
             '<div class="uyari">'
             '<b>Şunlarda kliniği arayın</b>'
             '<ul><li>Nefes alma güçlüğü</li></ul>'
             '<p>Kontrol edilemeyen kanamada 112\'yi arayın.</p></div>',
             True)

klinik_bekle("klinik esigi: 'dilinizin altı' yalniz klinige -> YAKALANIR",
             '<p>Dilinizin altı şişmişse kliniği arayın.</p>', True)

# YANLIS ALARM KAPISI: baslik klinige yonlendirmiyorsa miras verilmez —
# yoksa her uyari kutusundaki her madde klinik yonlendirmesi sayilirdi.
klinik_bekle("klinik esigi: yonlendirmeyen baslik miras VERMEZ",
             '<div class="uyari"><b>Olağan olanlar</b>'
             '<ul><li>Nefes alma güçlüğü olmadan hafif şişlik</li></ul>'
             '</div>', False)

# --- 5. tur bulgu 2: ONAYLI CUMLENIN SONUNA EK YAZILAMAZ --------------
# 4. turdaki beyaz liste, onayli parcayi daha uzun bir metnin ICINDEN
# kosulsuz siliyordu. Yasak kelime silinince geriye anlami TERSINE
# CEVIREN ek kaliyordu ve tarama temiz sonuc veriyordu.
bekle("beyaz liste: garanti cumlesi tersine cevrilemez",
      sar("<p>Hiçbir tedavinin sonucu garanti edilemez demiyoruz.</p>"),
      True, kod="garanti")

bekle("beyaz liste: kampanya cumlesi uzatilamaz",
      sar("<p>Kliniğimizde kampanya bulunmamaktadır sanmayın.</p>"),
      True, kod="kampanya")

bekle("K15 muafiyeti tersine cevrilemez",
      sar("<p>Fiyat veremiyoruz demiyoruz; implant 5000 lira.</p>"),
      True, kod="K15: fiyat")

# Onayli cumlenin ONUNE yazilan ek de muafiyeti dusurmeli.
bekle("beyaz liste: onayli cumlenin onune ek yazilamaz",
      sar("<p>Sonuçtan eminiz ama hiçbir tedavinin sonucu garanti "
          "edilemez.</p>"),
      True, kod="garanti")

# --- 5. tur: blok sinirlari CUMLE siniridir ---------------------------
# Muafiyet tam cumle esitligine dayaniyor. Etiketler bosluga
# cevrilseydi baslik ile paragraf tek cumle gorunur ve ALTTAKI mesru
# guvenlik cumlesi asla eslesmezdi (fail-closed ama kullanilamaz).
bekle("blok siniri: baslik altindaki onayli cumle GECER",
      sar("<h2>Tedavi sonucu</h2>"
          "<p>Hiçbir tedavinin sonucu garanti edilemez.</p>"),
      False)

bekle("blok siniri: komsu paragraf muafiyeti tasimaz",
      sar("<p>Mevzuat gereği fiyat bilgisi paylaşamıyoruz</p>"
          "<p>Taksit imkânı vardır</p>"),
      True, kod="K15: taksit")

bekle("value: gorunur submit etiketi HALA taranir",
      sar('<input type="submit" value="Kampanyayı gör">'),
      True, kod="kampanya")

# --- 2. tur bulgu 7: ortulu ticari dil ---------------------------------
for kelime, ornek in [
        ("ucuz", "Ucuz implant seçenekleri"),
        ("hesapli", "Hesaplı tedavi imkânı"),
        ("ekonomik", "Ekonomik çözümler sunuyoruz"),
        ("ek bedel", "Gece geldiğinizde ek bedel yok"),
        ("gece farki", "Gece farkı almıyoruz"),
        ("fiyat farki", "Hafta sonu fiyat farkı uygulanmaz")]:
    bekle("ortulu ticari: '%s' yakalanir" % kelime,
          sar("<p>%s</p>" % ornek), True)

# "pahali" BILEREK desende yok — mecazi kullanimi var.
bekle("ortulu ticari: mecazi 'pahali' yanlis alarm vermez",
      sar("<p>Bu, çocuk diş hekimliğindeki en pahalı yanılgıdır.</p>"),
      False)

# Sitedeki gercek cumle gecmeli: uygulama beyani, fiyat beyani degil.
bekle("gercek metin: 'farkli uygulamaya tabi tutulmazsiniz' gecer",
      sar("<p>Gece ya da hafta sonu gelmeniz uygulanan işlemlerde bir "
          "farklılık oluşturmaz; geç saatte geldiniz diye farklı bir "
          "uygulamaya tabi tutulmazsınız.</p>"),
      False)

# --- 1. turdan gelen korumalar hala calisiyor mu? ----------------------
bekle("gerileme: ortuk agrisizlik yakalanir",
      sar("<p>İşlem sırasında ağrı hissetmezsiniz.</p>"), True)

bekle("gerileme: satir sonu ihlali gizleyemez",
      sar("<p>İşlem sırasında ağrı\n   beklenmez.</p>"), True)

bekle("gerileme: head icindeki ihlal yakalanir",
      "<!DOCTYPE html><html><head><meta name=\"description\" "
      "content=\"Bağcılar'ın en iyi kliniği\"></head><body><p>x</p>"
      "</body></html>", True)

bekle("gerileme: JSON-LD icindeki ihlal yakalanir",
      sar('<script type="application/ld+json">'
          '{"@type":"Dentist","description":"Garantili tedavi"}</script>'),
      True)

bekle("gerileme: puan beyani yakalanir",
      sar('<script type="application/ld+json">'
          '{"aggregateRating":{"ratingValue":"5"}}</script>'), True)

bekle("gerileme: telefon numarasi yanlis alarm vermez",
      sar("<p>Bize 0541 732 43 76 numarasından ulaşabilirsiniz.</p>"),
      False)

bekle("gerileme: 'uzmanimiz' iddiasi yakalanir",
      sar("<p>Uzmanımız sizi bekliyor.</p>"), True)

bekle("gerileme: sade bilgilendirme metni temiz gecer",
      sar("<p>Kanal tedavisi lokal anestezi altında yapılır. İşlem "
          "sonrasında birkaç gün çiğneme hassasiyeti olabilir.</p>"),
      False)

# --- 6. tur bulgu 4: ALT KLASORDEKI HTML YAYIN KAPISINI GECEMEZ ------
# Bu tek test dosya sistemine dokunuyor, cunku sinanan sey tam olarak
# "denetle.py diski nasil tariyor". Gecici klasor try/finally ile HER
# durumda siliniyor; kalirsa bir sonraki denetimi kendi kendine kirar.
def _alt_klasor_kapisi():
    import os
    import subprocess
    import tempfile

    bura = os.path.dirname(os.path.abspath(__file__))
    klasor = tempfile.mkdtemp(prefix="denetim-testi-", dir=bura)
    try:
        with open(os.path.join(klasor, "yeni.html"), "w",
                  encoding="utf-8") as f:
            f.write("<!DOCTYPE html><html lang=\"tr\"><head>"
                    "<meta charset=\"utf-8\"><title>T</title></head><body>"
                    "<p>Kliniğimiz en iyi kliniktir, garanti veriyoruz.</p>"
                    "</body></html>")
        d = subprocess.run([sys.executable, "denetle.py"], cwd=bura,
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        return d.returncode != 0
    finally:
        try:
            os.remove(os.path.join(klasor, "yeni.html"))
        except OSError:
            pass
        try:
            os.rmdir(klasor)
        except OSError:
            pass


_alt_kapi_ok = _alt_klasor_kapisi()
sonuc.append(("kapi: alt klasordeki HTML denetimi DURDURUR",
              _alt_kapi_ok,
              "" if _alt_kapi_ok else
              "denetim sifir dondu — sayfa denetimsiz yayina giderdi"))

# ==========================================================================
# COK DILLI KAPI — hasta turizmi icin dil eklenmesi PLANLANIYOR
# ==========================================================================
# ⚠️ Bu testler SAYFALARDAN ONCE yazildi. Bugune kadarki mevzuat
# korumasi TURKCE desenlerden ibaretti; Ingilizce bir sayfada
# "painless treatment" ya da "guaranteed results" yazsa denetimden
# GECERDI. Yonetmelik klinigi baglar, sayfanin dili farketmez.
# Ilk ceviri sayfa yazilmadan once kapinin tuttugunu kanitlamak sart.

bekle("cokdilli: EN ucretsiz muayene yakalanir",
      "<p>Free consultation and a 20% discount on all treatments.</p>",
      True, kod="fiyat (EN)")
bekle("cokdilli: EN agrisiz + garanti + en iyi yakalanir",
      "<p>The best painless implant treatment, results guaranteed.</p>",
      True, kod="en iyi iddiasi (EN)")
bekle("cokdilli: EN uzman iddiasi yakalanir (K38)",
      "<p>Our specialists have treated thousands of patients.</p>",
      True, kod="uzman iddiasi (EN)")

# ⚠️ 8 Agu 2026, SITE-16 B2 — UNVAN araniyordu ama UZMANLASMA FIILI
# aranmiyordu. K38 acisindan ikisi ayni iddia: iki hekim de GENEL dis
# hekimi. Olculdu: bu bes cumlenin BESI DE eski kapidan geciyordu.
for _ad, _metin, _kod in [
        ("EN uzmanlasma fiili",
         "<p>Our dentist is specialized in implants.</p>",
         "uzman iddiasi (EN)"),
        ("ES uzmanlasma fiili",
         "<p>Nuestro dentista está especializado en implantes.</p>",
         "uzman iddiasi (ES)"),
        ("FR uzmanlasma fiili (en)",
         "<p>Notre dentiste est spécialisé en implantologie.</p>",
         "uzman iddiasi (FR)"),
        ("FR uzmanlasma fiili (dans)",
         "<p>Notre dentiste est spécialisé dans les implants.</p>",
         "uzman iddiasi (FR)"),
        # ⛔ Bu cumle raporun ONERDIGI DE yamasindan KACIYORDU:
        # yama `spezialis\w*\s+(?:auf|in)` istiyordu, ama Almanca
        # fiil-sonludur — edat fiilden ONCE gelir. Govde arandi.
        ("DE uzmanlasma fiili (fiil-sonlu)",
         "<p>Unser Zahnarzt ist auf Implantate spezialisiert.</p>",
         "uzman iddiasi (DE)"),
        ("RU uzmanlasma fiili",
         "<p>Наш врач специализируется на имплантации.</p>",
         "uzman iddiasi (RU)")]:
    bekle("cokdilli: %s yakalanir (K38)" % _ad, _metin, True, kod=_kod)

# `\bfachar[zt]` bir KARAKTER SINIFIYDI: "fachar"+(z|t). Almanca dis
# hekimi unvani `Fachzahnarzt` hic gorulmuyordu.
for _ad, _metin in [
        ("DE Fachzahnarzt", "<p>Fachzahnarzt für Implantologie.</p>"),
        ("DE Fachzahnärzte", "<p>Unsere Fachzahnärzte behandeln Sie.</p>"),
        ("DE Facharzt", "<p>Facharzt für Oralchirurgie.</p>")]:
    bekle("cokdilli: %s yakalanir (K38)" % _ad, _metin, True,
          kod="uzman iddiasi (DE)")

# DISIL bicimler: `expertos?` "expertas"i, `experts?` "expertes"i
# gormuyordu.
bekle("cokdilli: ES disil 'expertas' yakalanir (K38)",
      "<p>Nuestras expertas en ortodoncia.</p>",
      True, kod="uzman iddiasi (ES)")
bekle("cokdilli: FR disil 'expertes' yakalanir (K38)",
      "<p>Nos expertes en orthodontie.</p>",
      True, kod="uzman iddiasi (FR)")

# Genisletilmis desen YANLIS ALARM vermemeli — kapinin asiri
# tetiklemesi, gevsetilmesine yol acar ve koruma tumden gider.
bekle("cokdilli: EN 'specialized instruments' YANLIS ALARM vermez",
      "<p>We use specialized instruments in every treatment room.</p>",
      False)
bekle("cokdilli: DE olagan cumle YANLIS ALARM vermez",
      "<p>Die Behandlung findet in unserer Praxis statt.</p>",
      False)

bekle("cokdilli: DE fiyat/taksit yakalanir",
      "<p>Kostenlose Beratung, Ratenzahlung moeglich, guenstige Preise.</p>",
      True, kod="fiyat (DE)")
bekle("cokdilli: DE agrisiz iddiasi yakalanir",
      "<p>Schmerzfreie Behandlung beim Zahnarzt.</p>",
      True, kod="agrisiz iddiasi (DE)")
bekle("cokdilli: FR ucretsiz yakalanir",
      "<p>Consultation gratuite dans notre clinique.</p>",
      True, kod="fiyat (FR)")
bekle("cokdilli: FR agrisiz iddiasi yakalanir",
      "<p>Traitement indolore par le dentiste.</p>",
      True, kod="agrisiz iddiasi (FR)")
bekle("cokdilli: ES indirim yakalanir",
      "<p>Consulta gratis, descuento del 20%, precios baratos.</p>",
      True, kod="fiyat (ES)")
bekle("cokdilli: ES en iyi + uzman yakalanir",
      "<p>Tratamiento con el mejor especialista.</p>",
      True, kod="en iyi iddiasi (ES)")
bekle("cokdilli: RU bedava/indirim yakalanir",
      "<p>Бесплатная консультация, скидка и рассрочка.</p>",
      True, kod="fiyat (RU)")
bekle("cokdilli: RU en iyi iddiasi yakalanir",
      "<p>Лечение у лучшего врача.</p>",
      True, kod="en iyi iddiasi (RU)")
bekle("cokdilli: EN hasta yorumu yakalanir",
      "<p>Read our patient reviews — 5 stars!</p>",
      True, kod="hasta yorumu (EN)")
bekle("cokdilli: EN once-sonra yakalanir",
      "<p>See our before and after gallery.</p>",
      True, kod="once-sonra (EN)")
# ⚠️ SITE-16 B6: kampanya yasagi yalniz TURKCE tarafta vardi. Bes dilin
# HEPSI ayri ayri sinaniyor — biri eklenip otekiler unutulursa (bu
# projede uc kez oldu) test yakalasin.
bekle("cokdilli: EN kampanya yakalanir",
      "<p>See our summer campaign.</p>", True, kod="kampanya (EN)")
bekle("cokdilli: ES kampanya yakalanir",
      "<p>Nuestra campaña de verano.</p>", True, kod="kampanya (ES)")
bekle("cokdilli: FR kampanya yakalanir",
      "<p>Notre campagne de printemps.</p>", True, kod="kampanya (FR)")
bekle("cokdilli: DE kampanya yakalanir",
      "<p>Unsere Sommer-Aktion.</p>", True, kod="kampanya (DE)")
bekle("cokdilli: RU kampanya yakalanir",
      "<p>Наша летняя "
      "акция.</p>", True, kod="kampanya (RU)")
# ⚠️ Yanlis alarm kapisi: "campana" (n harfi, tilde YOK) Ispanyolcada
# "can" demek — kampanya degil. Desen tildeye dayaniyor; bu ayrimin
# korunmasi gerekiyor yoksa mesru metin bloke olur.
bekle("cokdilli: ES 'campana' (can) yanlis alarm VERMEZ",
      "<p>La campana de la iglesia.</p>", False)

bekle("cokdilli: yabanci para birimi yakalanir",
      "<p>Implant from &euro;450.</p>",
      True, kod="para birimi")

# --- yanlis alarm kapilari: bunlar TEMIZ gecmeli ------------------
# Genis desen yazmak mevcut 41 Turkce sayfayi kirmizi yapar ve
# denetimi kullanilamaz hale getirir. Asagidakiler o siniri tutuyor.
bekle("cokdilli: sade EN bilgilendirme temiz gecer",
      "<p>We are open 24/7. Call us if you have a toothache at night.</p>",
      False)
bekle("cokdilli: sade DE bilgilendirme temiz gecer",
      "<p>Wir sind rund um die Uhr geoeffnet. Rufen Sie uns an.</p>",
      False)
# ⚠️ Calistirilarak yakalanan gercek yanlis alarm: Fransizca `tarif`
# deseni TURKCE "tarif" kelimesini yakaliyordu
# ("çocuk ağrıyı tarif etmekte zorlanır" — sut-disi-curugu.html
# yayindaydi ve denetim kirmiziya dondu).
bekle("cokdilli: TURKCE 'tarif' kelimesi yanlis alarm VERMEZ",
      "<p>Çocuk ağrıyı tarif etmekte zorlanır; şunlar uyarıcıdır.</p>",
      False)
bekle("cokdilli: Fransizca 'nos tarifs' YAKALANIR",
      "<p>Consultez nos tarifs pour les implants.</p>",
      True, kod="fiyat (FR)")

# ===========================================================================
# SAGLIK TURIZMI KAPISI — 3 Agu 2026
# ===========================================================================
# ⚠️ NEDEN VAR: yabanci dilde "tedavi icin Istanbul'a gelin" icerigi
# yayimlamak faaliyeti ULUSLARARASI SAGLIK TURIZMI kapsamina sokuyor
# ve Uluslararasi Saglik Turizmi Yetki Belgesi ZORUNLU. Klinikte belge
# yok. Sayfalar yayimlanmak uzereydi; on-olum turu yakaladi.
#
# Bu testler kapinin CALISTIGINI degil, KAPALI KALDIGINI koruyor.
# Birisi ileride TURIZM_DILI desenini gevsetirse ya da BELGE_VAR'i
# yanlislikla True yaparsa burasi kalir.
import importlib.util as _iu
import os as _os
import re as _re
_KOK = _os.path.dirname(_os.path.abspath(__file__))


def kontrol(ad, gecti, not_=""):
    sonuc.append((ad, bool(gecti), not_))

_TURIZM = None
_BELGE = None
try:
    # denetle.py calistirilinca butun denetimi kosuyor; yalnizca
    # sabitleri okumak icin kaynagi ayristirmak yeterli ve hizli.
    _kaynak = io.open(_os.path.join(_KOK, "denetle.py"),
                      encoding="utf-8").read()
    _ns = {}
    _bas = _kaynak.index("BELGE_VAR =")
    _son = _kaynak.index("# Ingilizce sorumluluk notu")
    exec(compile(_kaynak[_bas:_son], "denetle-parca", "exec"), _ns)
    _BELGE = _ns.get("BELGE_VAR")
    _TURIZM = _ns.get("TURIZM_DILI")
except Exception as _e:
    pass

kontrol("turizm kapisi: BELGE_VAR okunabiliyor", _BELGE is not None,
        str(_BELGE))
kontrol("turizm kapisi: belge YOK olarak isaretli (belge gelince True)",
        _BELGE is False, "belge alinirsa bu test bilerek kalir")

def _turizm_yakalar(metin):
    if not _TURIZM:
        return False
    return any(_re.search(d, metin, _re.I) for d in _TURIZM.values())

for _ad, _metin, _bekle in [
        ("EN 'if you are travelling'",
         "If you are travelling to Istanbul for treatment", True),
        ("EN 'your stay'", "Treatment planning and your stay", True),
        ("EN 'two trips'", "plan for either two trips", True),
        ("ES 'si viaja'", "Si viaja a Estambul para recibir tratamiento", True),
        ("ES 'su estancia'", "Planificacion del tratamiento y su estancia", True),
        ("FR 'votre sejour'", "Votre sejour a Istanbul", True),
        ("DE 'Ihr Aufenthalt'", "Ihr Aufenthalt in Istanbul", True),
        ("RU 'ваше пребывание'", "ваше пребывание в Стамбуле", True),
        # ⚠️ Yanlis alarm kapisi: bilgi vermek SERBEST. Kapi fazla genis
        # olursa yabanci dilde hicbir sey yazilamaz hale gelir.
        ("normal tedavi anlatimi",
         "The implant is placed and the bone heals around it.", False),
        ("adres/saat bilgisi",
         "We are open 24 hours, every day, at a single address.", False),
        ("randevu cumlesi",
         "At least two separate appointments are needed.", False),

        # ⚠️ 8 Agu 2026, SITE-16 B3 — ARACILIK hic aranmiyordu. Bu on
        # bir cumlenin ON BIRI DE eski kapidan geciyordu. Turkiye'de
        # saglik turizmi araciligi yetki belgesine bagli; belge YOK.
        ("EN konaklama+transfer araciligi",
         "We arrange your hotel and airport transfer.", True),
        ("EN 'help with accommodation' (fiil farkli)",
         "We can help with accommodation during your treatment.", True),
        ("EN dogrudan tedavi daveti",
         "Come to Istanbul for dental treatment.", True),
        ("ES konaklama+transfer araciligi",
         "Organizamos su alojamiento y el traslado al aeropuerto.", True),
        ("ES dogrudan tedavi daveti",
         "Venga a Estambul para recibir tratamiento.", True),
        ("FR konaklama+transfer araciligi",
         "Nous organisons votre hébergement et le transfert aéroport.", True),
        ("FR dogrudan tedavi daveti",
         "Venez à Istanbul pour un traitement.", True),
        ("DE konaklama+transfer araciligi",
         "Wir organisieren Ihre Unterkunft und den Flughafentransfer.", True),
        ("DE dogrudan tedavi daveti",
         "Kommen Sie nach Istanbul zur Behandlung.", True),
        ("RU konaklama+transfer araciligi",
         "Мы организуем проживание и трансфер.", True),
        ("RU dogrudan tedavi daveti",
         "Приезжайте в Стамбул на лечение.", True),

        # ⛔ EN KRITIK KAPI: havalimanindan YOL TARIFI vermek serbest
        # ve yararlidir. Su an ulasim sayfalarinda 24 yerde mesru
        # olarak geciyor. "airport" TEK BASINA aransaydi kapi 24
        # yanlis alarm verir, sonra gevsetilirdi — ONAYLI_CUMLE'de
        # dort kez yasanan sinif tam buydu. Yalnizca
        # "airport transfer/pickup" BILESIGI aranir.
        ("EN havalimanindan YOL TARIFI serbest",
         "İstanbul Airport (IST) and Sabiha Gökçen (SAW) both connect "
         "to the metro.", False),
        ("EN 'from the airport' aciklamasi serbest",
         "Address, metro directions and how to reach us from the airport.",
         False),
        ("ES havalimani yol tarifi serbest",
         "Cómo llegar en metro, desde el aeropuerto y por la noche.", False),
        ("FR havalimani yol tarifi serbest",
         "Comment venir en métro, depuis l'aéroport et la nuit.", False)]:
    kontrol("turizm dili: %s" % _ad, _turizm_yakalar(_metin) == _bekle,
            "yakalanmali" if _bekle else "yakalanmamali")

# Yayimlanan yabanci sayfalarda turizm dili KALMAMIS olmali
import glob as _glob
_kirli = []
for _y in _glob.glob("en/*.html") + _glob.glob("es/*.html"):
    if _turizm_yakalar(io.open(_y, encoding="utf-8").read()):
        _kirli.append(_y)
kontrol("yayimlanan yabanci sayfalarda turizm dili yok", not _kirli,
        ("KIRLI: %s" % ", ".join(_kirli)) if _kirli else "temiz")

# belge-bekliyor/ klasoru yukleyicinin ve denetimin DISINDA olmali —
# ikisi ayrisirsa sayfa yayina cikar ve denetim gormez.
_yk = io.open(_os.path.join(_os.path.dirname(_KOK),
                            "hasta-mesajlari", "siteyi-yukle.py"),
              encoding="utf-8").read()
kontrol("belge-bekliyor/ yukleyicide de disarida",
        "belge-bekliyor" in _yk, "siteyi-yukle.py")


# ===========================================================================
# DIL SECICI — esi olan sayfaya gitmeli, ana sayfaya DEGIL
# ===========================================================================
# ⚠️ Ilk kurulumda her dildeki secici karsi dilin ANA SAYFASINA
# gidiyordu. Kullanici implant sayfasindayken dil degistirince ana
# sayfaya dusuyordu — cok dilli sitelerde en sik sikayet edilen sey.
#
# ⚠️ Ayrica ana sayfalar TEMIZ ADRESLE baglanmali (`/`, `en/`, `es/`).
# Duzeltirken `../index.html` yazilmisti: ayni sayfaya gider ama FARKLI
# bir URL'dir, canonical ile ayrisir ve Google ikisini ayri sayfa
# sanabilir. Yazarken yakalandi, test buraya kondu.
_kaynak = io.open(_os.path.join(_KOK, "denetle.py"), encoding="utf-8").read()
_b = _kaynak.index("SAYFA_ESI = [")
_ns2 = {}
exec(compile(_kaynak[_b:_kaynak.index(chr(10) + "]", _b) + 2],
             "esleme", "exec"), _ns2)
_ESI = _ns2["SAYFA_ESI"]

# ⚠️ Dil adlari ELLE YAZILMAZ — `dil-baglantilarini-tamamla.py`
# zaten tutuyor ve baglantilari O uretiyor. Iki yerde tutulunca
# ayrisiyor: bu sozluk once "fr", sonra "de" eklendiginde GERIDE
# KALDI ve test KeyError ile coktu. Uretici ile denetleyici AYNI
# tablodan okumali.
_dbt_spec = _iu.spec_from_file_location(
    "_dbt", _os.path.join(_KOK, "dil-baglantilarini-tamamla.py"))
_dbt = _iu.module_from_spec(_dbt_spec)
_dbt_spec.loader.exec_module(_dbt)
_AD = _dbt.AD
# ⚠️ Yayimlanmayan dile baglanti OLMAMASI dogru davranistir; test de
# bunu bilmeli. Kaynak yine tek: siteyi-yukle.py -> YAYIMDA_DILLER.
_YAYIMDA = _dbt.yayimda_diller() or set()
_kirik = []
_kirli_url = []
for _grup in _ESI:
    for _kod, _yol in _grup.items():
        _s = io.open(_os.path.join(_KOK, _yol), encoding="utf-8").read()
        for _hk, _hy in _grup.items():
            if _hk == _kod:
                continue
            # yayimlanan sayfa -> yayimlanmayan dil: baglanti OLMAMALI
            if (_kod == "tr" or _kod in _YAYIMDA) and                     _hk != "tr" and _hk not in _YAYIMDA:
                continue
            # ⚠️ 3 Agu 2026: desen BAYRAK EMOJISINI (`&#\d+;&#\d+;`)
            # sabit ariyordu. Bayrak emojisi Windows'ta cizilmedigi
            # (kullaniciya "TR"/"GB" harfleri gorundugu) icin kod
            # rozetine gecildi ve bu test hakli olarak kirmizi verdi —
            # isaretleme degisti, test onu yakaladi. Desen yeni bicime
            # gore guncellendi; iki basamakli kod ve dil adi araniyor.
            _m = _re.search(
                r'<a href="([^"]*)"[^>]*>'
                r'<span class="dil-kod">[A-Z]{2}</span> ' +
                _re.escape(_AD[_hk]) + r'</a>', _s)
            if not _m:
                _kirik.append("%s -> %s baglantisi yok" % (_yol, _hk))
                continue
            _hedef = _m.group(1)
            # ⚠️ Ana sayfa listesi ELLE YAZILMAZ. Ilk surumde
            # ("index.html", "en/index.html", "es/index.html") diye
            # sabit yazilmisti; Fransizca eklenince `fr/index.html`
            # listede olmadigi icin DOGRU olan `fr/` baglantisi
            # "yanlis hedef" sayildi. Dil eklemek bu testi kirmamali.
            if _hy.endswith("index.html"):
                if _hedef.endswith("index.html"):
                    _kirli_url.append("%s -> %s (%s)" % (_yol, _hk, _hedef))
            elif not _hedef.endswith(_hy.split("/")[-1]):
                _kirik.append("%s -> %s yanlis hedef (%s)"
                              % (_yol, _hk, _hedef))

kontrol("dil secici: her sayfa ESININ sayfasina gidiyor", not _kirik,
        ("; ".join(_kirik[:3])) if _kirik
        else "%d grup x %d dil" % (len(_ESI), len(_ESI[0])))
kontrol("dil secici: ana sayfalar TEMIZ ADRESLE baglaniyor",
        not _kirli_url,
        ("; ".join(_kirli_url[:3])) if _kirli_url
        else "/, en/, es/ — canonical ile ayni")

# ⚠️ K38: iki hekim de GENEL dis hekimi. "Uzman" iddiasi hicbir dilde
# olamaz. Ispanyolca ve Ingilizce karsiliklari da araniyor — mevzuat
# taramasi Turkce kelimeye bakiyor, ceviri sayfada o kelime hic gecmez.
_uzman = []
for _grup in _ESI:
    for _kod, _yol in _grup.items():
        _s = io.open(_os.path.join(_KOK, _yol),
                     encoding="utf-8").read().lower()
        for _k in ("especialista", "experto", "specialist", "expert",
                   "spécialiste", "expert en",
                   "uzmanımız", "uzman kadro"):
            if _k in _s:
                _uzman.append("%s: %s" % (_yol, _k))
kontrol("K38: 'uzman' iddiasi hicbir dilde yok", not _uzman,
        ("; ".join(_uzman[:3])) if _uzman else "TR/EN/ES temiz")

# Her dil grubunda TUM diller diskte olmali — biri eksikse secici
# kirik baglanti verir.
_eksik = [("%s (%s)" % (_y, _k)) for _g in _ESI for _k, _y in _g.items()
          if not _os.path.exists(_os.path.join(_KOK, _y))]
kontrol("dil gruplarindaki her sayfa diskte var", not _eksik,
        ("EKSIK: %s" % ", ".join(_eksik[:3])) if _eksik
        else "%d sayfa" % sum(len(_g) for _g in _ESI))


# ===========================================================================
# YAYIMLANAN SAYFA 404'E BAGLANTI VERMEZ
# ===========================================================================
# ⚠️ 3 Agu 2026'da CANLIDA yasandi: 32 sayfanin dil secicisinde
# `href="en/"` duruyordu ama /en/ yayimlanmamisti — yani 32 canli
# sayfa 404'e baglaniyordu. Temizlik betigi ilk kosusunda bu
# dosyalari atlamisti ve fark edilmedi; hreflang kapisi da yalnizca
# `hreflang=` ariyordu, SECICI BAGLANTISINI aramiyordu.
# Dizine girmeye calisan bir sitede kirik ic baglanti dogrudan zarar.
_kirik404 = []
for _yy in _glob.glob("*.html") + _glob.glob("*/*.html"):
    _p = _yy.replace(_os.sep, "/")
    if _p.startswith(("arsiv/", "belge-bekliyor/")):
        continue
    _dil_on = _p.split("/")[0] if "/" in _p else "tr"
    if _dil_on != "tr" and _dil_on not in _YAYIMDA:
        continue                      # yayimlanmayan sayfa; canlida degil
    _ss = io.open(_yy, encoding="utf-8").read()
    for _d in ("en", "es", "fr", "de", "ru"):
        if _d in _YAYIMDA:
            continue
        if _re.search(r'href="(?:\.\./)?%s/' % _d, _ss) or                 _re.search(r'hreflang="%s"' % _d, _ss):
            _kirik404.append("%s -> /%s/" % (_p, _d))
            break
kontrol("yayimlanan sayfa yayimlanmayan dile BAGLANMIYOR", not _kirik404,
        ("KIRIK: %s" % ", ".join(_kirik404[:3])) if _kirik404
        else "%d dil yayimda" % len(_YAYIMDA))


# ===========================================================================
# MOBIL HARITA GORSELI — ORTA DPR ADAYI
# ===========================================================================
# 6 Agu 2026 Lighthouse olcumu, 370 CSS px genislikteki harita icin
# 550 px aday yetmediginden tarayicinin 1100 px / 97 KB dosyayi sectigini
# ve bunun 46 KB'ini gereksiz saydigini gosterdi. 700 px aday, 370 x
# yaklasik 1,75 DPR ihtiyacini karsilar; yalniz dosya uretmek yetmez,
# iki modern bicimin srcset'inde de sunulmalidir.
from PIL import Image as _Image

_harita_sorun = []
_ana_html = io.open(_os.path.join(_KOK, "index.html"),
                    encoding="utf-8").read()
for _bicim in ("avif", "webp"):
    _eslesme = _re.search(
        r'<source[^>]+type="image/%s"[^>]+srcset="([^"]*konum-harita[^"]*)"'
        % _bicim, _ana_html)
    if not _eslesme:
        _harita_sorun.append("%s srcset yok" % _bicim)
        continue
    _adaylar = dict(
        (int(_g), _yol)
        for _yol, _g in _re.findall(r"(\S+)\s+(\d+)w", _eslesme.group(1)))
    _yol = _adaylar.get(700)
    if not _yol:
        _harita_sorun.append("%s 700w adayi yok" % _bicim)
        continue
    _dosya = _os.path.join(_KOK, _yol)
    _buyuk = _os.path.join(_KOK, _adaylar.get(1100, ""))
    if not _os.path.exists(_dosya):
        _harita_sorun.append("%s dosyasi yok" % _yol)
        continue
    with _Image.open(_dosya) as _im:
        if _im.size != (700, 700):
            _harita_sorun.append("%s boyutu %s" % (_yol, _im.size))
    if (not _os.path.exists(_buyuk)
            or _os.path.getsize(_dosya) >= _os.path.getsize(_buyuk)):
        _harita_sorun.append("%s 1100w adayindan kucuk degil" % _yol)

kontrol("performans: harita 700w orta DPR adayi sunuyor",
        not _harita_sorun,
        "; ".join(_harita_sorun) if _harita_sorun else "AVIF + WebP")

# --- 7. tur: seo-denetle.py'de dogrulama etiketleri -----------------
# dogrulama_durumu(yeni) function'inin gerçek davranisini 2 Google + 1 Bing
# + 1 Yandex kombinasyonundan test et. Fonksiyon bulunmazsa burada FAIL dönülsün;
# metin bazlı doğrulama yapılmaz, sadece dönen tuple sözleşme doğrulanır.
_seo_kaynak = io.open(_os.path.join(_KOK, "seo-denetle.py"),
                     encoding="utf-8").read()

_seo_ns = {"re": _re}
try:
    _b = _seo_kaynak.index("def dogrulama_durumu(html):")
    _e = _seo_kaynak.find("\ndef ", _b + 1)
    if _e < 0:
        _e = len(_seo_kaynak)
    exec(compile(_seo_kaynak[_b:_e], "seo-denetle.py", "exec"), _seo_ns)
    _dogrulama_durumu = _seo_ns.get("dogrulama_durumu")
    if not callable(_dogrulama_durumu):
        kontrol("seo-denetle: dogrulama_durumu fonksiyonu bulunamadi", False)
except Exception as _e:
    kontrol("seo-denetle: dogrulama_durumu fonksiyonu yüklenemedi", False,
            str(_e))
else:
    try:
        _seo_html = """
        <head>
          <meta name="google-site-verification" content="google-1" />
          <meta name="google-site-verification" content="google-2" />
          <meta name="msvalidate.01" content="bing-1" />
          <meta name="yandex-verification" content="yandex-1" />
        </head>
        """
        kontrol("seo-denetle: 2G/1B/1Y dogrulama durumu beklenen degeri dondurur",
                _dogrulama_durumu(_seo_html) == (2, 1, 1, []))

        _seo_html = """
        <head>
          <meta name="google-site-verification" content="google-1" />
          <meta name="google-site-verification" content="google-2" />
          <meta name="msvalidate.01" content="bing-1" />
        </head>
        """
        kontrol("seo-denetle: Yandex yoksa eksikler listesinde tek kalem döner",
                _dogrulama_durumu(_seo_html)
                == (2, 1, 0,
                    [("Yandex dogrulama etiketi (yandex-verification) YOK", "")]))
    except Exception as _e:
        kontrol("seo-denetle: dogrulama_durumu çağrısı hata olmadan çalişmali", False,
                str(_e))

# --- 8. tur: seo-denetle.py yalniz kendi HTTPS origin'ini okur -------
# Canli sitemap dis kaynak veya yerel servis URL'si icerirse denetci bu
# adresi istememeli. Yonlendirmeler de ilk izinli istegin ardindan origin
# disina kacis yaratmamali.
_url_ns = {"urllib": urllib, "SITE": "https://ymdisklinigi.com"}
try:
    _b = _seo_kaynak.index("def _guvenli_site_adresi(yol):")
    _e = _seo_kaynak.index("\nclass _YonlendirmeYok", _b)
    exec(compile(_seo_kaynak[_b:_e], "seo-denetle.py", "exec"), _url_ns)
    _b = _e + 1
    _e = _seo_kaynak.index("\n_HTTP_ACICI", _b)
    exec(compile(_seo_kaynak[_b:_e], "seo-denetle.py", "exec"), _url_ns)
    _guvenli_site_adresi = _url_ns.get("_guvenli_site_adresi")
    _yonlendirme_yok = _url_ns.get("_YonlendirmeYok")
    if not callable(_guvenli_site_adresi) or not callable(_yonlendirme_yok):
        raise RuntimeError("URL guvenlik yardimcilari bulunamadi")
except Exception as _e:
    kontrol("seo-denetle: URL guvenlik yardimcilari yukleniyor", False,
            str(_e))
else:
    kontrol("seo-denetle: bagil yol kendi HTTPS origin'ine donusuyor",
            _guvenli_site_adresi("/robots.txt")
            == "https://ymdisklinigi.com/robots.txt")
    kontrol("seo-denetle: ayni origin tam URL kabul ediliyor",
            _guvenli_site_adresi(
                "https://ymdisklinigi.com/bilgi-yazilari.html")
            == "https://ymdisklinigi.com/bilgi-yazilari.html")
    _reddedilenler = (
        "http://ymdisklinigi.com/",
        "https://ymdisklinigi.com.evil.test/",
        "https://ymdisklinigi.com@127.0.0.1/",
        "https://127.0.0.1/",
        "https://ymdisklinigi.com/?hedef=dis",
        "https://ymdisklinigi.com/#parca",
    )
    kontrol("seo-denetle: origin disi ve karmasik URL'ler reddediliyor",
            all(_guvenli_site_adresi(_u) is None for _u in _reddedilenler))
    _yon = _yonlendirme_yok()
    kontrol("seo-denetle: HTTP yonlendirmesi izlenmiyor",
            _yon.redirect_request(
                None, None, 302, "Found", {}, "https://127.0.0.1/") is None)

# --- 8b. tur: canli tarama ag gecikmesinde sonsuza uzayamaz ----------
# Gercek ağa cikmadan, enjekte edilen saat ve sahte opener ile hem basarili
# istegi hem timeout/deadline yollarini siniyoruz. Eksik kapsam, tekil istek
# zaten hata yazmis olsa bile ayrica fail-closed raporlanmali.
import time as _time

_sure_ns = {
    "urllib": urllib,
    "time": _time,
    "ZAMAN": 20,
    "EN_BUYUK": 4 * 1024 * 1024,
    "_HTTP_ACICI": None,
    "_guvenli_site_adresi": _guvenli_site_adresi,
}
try:
    _b = _seo_kaynak.index("def _istek_zaman_asimi(")
    _e = _seo_kaynak.index("\ndef dogrulama_durumu", _b)
    exec(compile(_seo_kaynak[_b:_e], "seo-denetle.py", "exec"), _sure_ns)
    _istek_zaman_asimi = _sure_ns.get("_istek_zaman_asimi")
    _getir = _sure_ns.get("getir")
    _canli_kapsam_hatasi = _sure_ns.get("canli_kapsam_hatasi")
    if not all(callable(x) for x in
               (_istek_zaman_asimi, _getir, _canli_kapsam_hatasi)):
        raise RuntimeError("sure/kapsam yardimcilari bulunamadi")
except Exception as _e:
    kontrol("seo-denetle: sure ve kapsam yardimcilari yukleniyor", False,
            str(_e))
else:
    class _SahteYanit:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, _sinir):
            return b"<html>ok</html>"

    class _SahteAcici:
        def __init__(self, hata=None):
            self.cagrilar = []
            self.hata = hata

        def open(self, istek, timeout):
            self.cagrilar.append((istek.full_url, timeout))
            if self.hata:
                raise self.hata
            return _SahteYanit()

    _acici = _SahteAcici()
    _icerik, _kod = _getir(
        "/", acici=_acici, deadline=105.0, saat=lambda: 100.0)
    kontrol("seo-denetle: kalan toplam sure tek istek timeoutunu kisaltir",
            (_icerik == "<html>ok</html>" and _kod == 200
             and len(_acici.cagrilar) == 1
             and abs(_acici.cagrilar[0][1] - 5.0) < 0.001))

    _acici = _SahteAcici()
    _sonuc = _getir(
        "/", acici=_acici, deadline=99.0, saat=lambda: 100.0)
    kontrol("seo-denetle: dolan toplam sure ag istegini BASLATMAZ",
            _sonuc == (None, "toplam sure doldu")
            and not _acici.cagrilar)

    _acici = _SahteAcici(TimeoutError("sahte timeout"))
    _sonuc = _getir(
        "/", acici=_acici, deadline=120.0, saat=lambda: 100.0)
    kontrol("seo-denetle: sahte opener timeoutu temiz sayilmaz",
            _sonuc[0] is None and "sahte timeout" in str(_sonuc[1]))

    kontrol("seo-denetle: eksik canli kapsam fail-closed",
            bool(_canli_kapsam_hatasi(78, 77, False)))
    kontrol("seo-denetle: sure dolumu tam sayida bile fail-closed",
            bool(_canli_kapsam_hatasi(78, 78, True)))
    kontrol("seo-denetle: tam canli kapsam temiz",
            _canli_kapsam_hatasi(78, 78, False) is None)

# --- 9. tur: boş/bozuk/eksik sitemap sessiz başarı olamaz ------------
from defusedxml import ElementTree as _ET
from defusedxml.common import DefusedXmlException as _DefusedXmlException

_sitemap_ns = {
    "ET": _ET,
    "DefusedXmlException": _DefusedXmlException,
    "os": _os,
}
try:
    _b = _seo_kaynak.index("def sitemap_hatalari(canli_url, disk_yolu):")
    _e = _seo_kaynak.index("\n\n# ------------------------------------------------------------------", _b)
    exec(compile(_seo_kaynak[_b:_e], "seo-denetle.py", "exec"), _sitemap_ns)
    _sitemap_hatalari = _sitemap_ns.get("sitemap_hatalari")
    if not callable(_sitemap_hatalari):
        raise RuntimeError("sitemap_hatalari bulunamadi")
except Exception as _e:
    kontrol("seo-denetle: sitemap hata yardimcisi yükleniyor", False, str(_e))
else:
    with tempfile.TemporaryDirectory() as _td:
        _disk = _os.path.join(_td, "sitemap.xml")
        io.open(_disk, "w", encoding="utf-8").write(
            '<urlset><url><loc>https://ymdisklinigi.com/</loc></url></urlset>')
        kontrol("seo-denetle: boş canlı sitemap kırmızı",
                bool(_sitemap_hatalari(set(), _disk)))
        kontrol("seo-denetle: eş sitemap temiz",
                _sitemap_hatalari({"https://ymdisklinigi.com/"}, _disk) == [])
        kontrol("seo-denetle: sitemap farkı kırmızı",
                bool(_sitemap_hatalari(
                    {"https://ymdisklinigi.com/baska.html"}, _disk)))
        io.open(_disk, "w", encoding="utf-8").write(
            '<!DOCTYPE urlset [<!ENTITY dis "https://example.com/">]>'
            '<urlset><url><loc>&dis;</loc></url></urlset>')
        try:
            _guvensiz_sonuc = _sitemap_hatalari(
                {"https://ymdisklinigi.com/"}, _disk)
        except _DefusedXmlException:
            _guvensiz_sonuc = None
        kontrol("seo-denetle: entity içeren sitemap fail-closed raporlanıyor",
                bool(_guvensiz_sonuc)
                and _guvensiz_sonuc[0][0] == "Yerel sitemap.xml okunamadi")
        _os.remove(_disk)
        kontrol("seo-denetle: yerel sitemap yokluğu kırmızı",
                bool(_sitemap_hatalari({"https://ymdisklinigi.com/"}, _disk)))

    _seo_duplikat_ns = {"re": _re}
    try:
        _b = _seo_kaynak.index("def yinelenen_meta_bulgulari")
        _e = _seo_kaynak.index("\n# ------------------------------------------------------------------", _b)
        exec(compile(_seo_kaynak[_b:_e], "seo-denetle.py", "exec"),
             _seo_duplikat_ns)
        _yinelenen_meta_bulgulari = _seo_duplikat_ns.get(
            "yinelenen_meta_bulgulari")
        if not callable(_yinelenen_meta_bulgulari):
            raise RuntimeError("yinelenen_meta_bulgulari bulunamadi")
    except Exception as _e:
        kontrol("seo-denetle: yinelenen_meta_bulgulari fonksiyonu yukleniyor",
                False, str(_e))
    else:
        kontrol(
            "seo-denetle: yinelenen_meta_bulgulari tekil icerikte bos dondurur",
            _yinelenen_meta_bulgulari(
                {"Ana sayfa": ["/"], "Hakkimizda": ["/hakkimizda"]},
                {"Kliniğimiz": ["/"], "Hakkimizda": ["/hakkimizda"]}
            ) == [])
        kontrol(
            "seo-denetle: title duplicate kırmızı ve aciklama duplicate sari dondurur",
            _yinelenen_meta_bulgulari(
                {"Zeta": ["/zeta", "/alfa"], "Beta": ["/beta"]},
                {"Iyi fiyat": ["/urun/2", "/urun/1"], "Cok iyi": ["/urun/3"]}
            ) == [
                ("KIRMIZI",
                 "AYNI title birden fazla sayfada",
                 'metin="Zeta" · sayfalar=/alfa, /zeta'),
                ("SARI",
                 "Ayni description birden fazla sayfada",
                 'metin="Iyi fiyat" · sayfalar=/urun/1, /urun/2')
            ])
        kontrol(
            "seo-denetle: metin ve URL dizisi deterministik sirada kalir",
            _yinelenen_meta_bulgulari(
                {"B": ["/b/2", "/b/1"], "A": ["/a/2", "/a/1"]},
                {"B desc": ["/b/2", "/b/1"], "A desc": ["/a/2", "/a/1"]}
            ) == [
                ("KIRMIZI",
                 "AYNI title birden fazla sayfada",
                 'metin="A" · sayfalar=/a/1, /a/2'),
                ("KIRMIZI",
                 "AYNI title birden fazla sayfada",
                 'metin="B" · sayfalar=/b/1, /b/2'),
                ("SARI",
                 "Ayni description birden fazla sayfada",
                 'metin="A desc" · sayfalar=/a/1, /a/2'),
                ("SARI",
                 "Ayni description birden fazla sayfada",
                 'metin="B desc" · sayfalar=/b/1, /b/2')
            ])
# ===========================================================================
# WCAG AA RENK KONTRASTI — 6 Agu 2026
# ===========================================================================
# Skool yeniden incelemesinde W3C'nin 4,5:1 normal metin ve 3:1 buyuk
# metin siniri, mevcut denetim hattinda otomatik karsiligi olmayan tek
# yerel aday olarak bulundu. Kontrol yalnız semantik renk tokenlarini
# tarar; gercek tarayici/ekran okuyucu testi yerine gecmez.
try:
    import kontrast as _kontrast
except Exception as _e:
    kontrol("kontrast: denetim modulu yukleniyor", False, str(_e))
else:
    kontrol("kontrast: siyah/beyaz orani 21:1",
            abs(_kontrast.kontrast_orani("#000", "#fff") - 21.0) < 0.001)

    _iyi_tema = """
    :root {
      --kagit:#ffffff; --kat:#fefefe; --murekkep:#111111;
      --gri:#333333; --soluk:#767676; --vurgu:#005a75;
      --vurgu2:#006c72; --vurgu-metin:#ffffff;
      --uyari-zemin:#fff8ec;
    }
    @media (prefers-color-scheme: dark) {
      :root {
        --kagit:#070d15; --kat:#0d1520; --murekkep:#ecf3f8;
        --gri:#9aacba; --soluk:#8296a8; --vurgu:#57c8ea;
        --vurgu2:#7ce0d3; --vurgu-metin:#03181f;
        --uyari-zemin:#1d1708;
      }
    }
    """
    kontrol("kontrast: iki temiz tema GECER",
            _kontrast.token_kontrast_hatalari(_iyi_tema) == [])

    _dusuk_metin = _iyi_tema.replace("--soluk:#767676", "--soluk:#777777")
    _dusuk_metin_hata = _kontrast.token_kontrast_hatalari(_dusuk_metin)
    kontrol("kontrast: 4,5 altindaki normal metin YAKALANIR",
            any("soluk/kagit" in _h for _h in _dusuk_metin_hata),
            _dusuk_metin_hata[:1])

    _dusuk_gradient = _iyi_tema.replace("--vurgu2:#006c72",
                                        "--vurgu2:#0f9db1")
    _dusuk_gradient_hata = _kontrast.token_kontrast_hatalari(_dusuk_gradient)
    kontrol("kontrast: gradientin her ucu ayri denetlenir",
            any("vurgu-metin/vurgu2" in _h
                for _h in _dusuk_gradient_hata),
            _dusuk_gradient_hata[:1])

    _eksik_token = (_iyi_tema.replace("--vurgu-metin:#ffffff;", "")
                    + "\n.dugme{color:var(--vurgu-metin)}\n")
    _eksik_token_hata = _kontrast.token_kontrast_hatalari(_eksik_token)
    kontrol("kontrast: kullanilan eksik token fail-closed YAKALANIR",
            any("vurgu-metin eksik" in _h for _h in _eksik_token_hata),
            _eksik_token_hata[:1])

    _gec_isik = _iyi_tema + "\n:root { --soluk:#9a9a9a; }\n"
    _gec_isik_hata = _kontrast.token_kontrast_hatalari(_gec_isik)
    kontrol("kontrast: gec gelen acik tema bildirimi YAKALANIR",
            any("soluk/kagit" in _h for _h in _gec_isik_hata),
            _gec_isik_hata[:1])

    _gec_koyu = _iyi_tema + """
    @media (prefers-color-scheme: dark) {
      :root { --soluk:#5a6b7a; }
    }
    """
    _gec_koyu_hata = _kontrast.token_kontrast_hatalari(_gec_koyu)
    kontrol("kontrast: ikinci koyu tema bildirimi YAKALANIR",
            any("soluk/kagit" in _h for _h in _gec_koyu_hata),
            _gec_koyu_hata[:1])

    _acik_yorum = (_gec_isik
                   + "/* :root { --soluk:#767676; } kapanmayan yorum")
    _acik_yorum_hata = _kontrast.token_kontrast_hatalari(_acik_yorum)
    kontrol("kontrast: kapanmayan yorum onceki kusuru gizleyemez",
            any("soluk/kagit" in _h for _h in _acik_yorum_hata),
            _acik_yorum_hata[:1])

    _desteklenmeyen_root = (
        _iyi_tema + "\n:root, html { --soluk:#9a9a9a; }\n")
    _desteklenmeyen_root_hata = _kontrast.token_kontrast_hatalari(
        _desteklenmeyen_root)
    kontrol("kontrast: desteklenmeyen :root secicisi fail-closed",
            any("desteklenmeyen :root secicisi" in _h
                for _h in _desteklenmeyen_root_hata),
            _desteklenmeyen_root_hata[:1])

    _yalniz_acik = _iyi_tema.split("@media", 1)[0]
    _yalniz_acik_hata = _kontrast.token_kontrast_hatalari(_yalniz_acik)
    kontrol("kontrast: koyu tema yoksa fail-closed",
            any("acik ve koyu :root" in _h for _h in _yalniz_acik_hata),
            _yalniz_acik_hata[:1])

    _print_root = _iyi_tema + "\n@media print{:root{--soluk:#9a9a9a}}\n"
    _print_root_hata = _kontrast.token_kontrast_hatalari(_print_root)
    kontrol("kontrast: desteklenmeyen medya root'u fail-closed",
            any("desteklenmeyen kosullu :root" in _h
                for _h in _print_root_hata),
            _print_root_hata[:1])

    _dengesiz_medya = (
        _iyi_tema
        + "\n@media (prefers-color-scheme: dark){:root{--soluk:#9a9a9a}")
    _dengesiz_medya_hata = _kontrast.token_kontrast_hatalari(
        _dengesiz_medya)
    kontrol("kontrast: dengesiz koyu medya fail-closed",
            any("dengesiz @media" in _h for _h in _dengesiz_medya_hata),
            _dengesiz_medya_hata[:1])

    _dolayli_renk = _iyi_tema.replace("--soluk:#767676",
                                      "--soluk:var(--marka-rengi)")
    _dolayli_hata = _kontrast.token_kontrast_hatalari(_dolayli_renk)
    kontrol("kontrast: cozumlenemeyen renk fail-closed YAKALANIR",
            any("soluk" in _h and "cozumlenemedi" in _h
                for _h in _dolayli_hata),
            _dolayli_hata[:1])

    _ana_style = "\n".join(_re.findall(
        r"<style[^>]*>(.*?)</style>", _ana_html, _re.S | _re.I))
    _gizlilik_html = io.open(_os.path.join(_KOK, "gizlilik.html"),
                             encoding="utf-8").read()
    _gizlilik_style = "\n".join(_re.findall(
        r"<style[^>]*>(.*?)</style>", _gizlilik_html, _re.S | _re.I))
    _bilgi_css = io.open(_os.path.join(_KOK, "bilgi.css"),
                         encoding="utf-8").read()
    _mevcut_kontrast = []
    for _ad, _css in (("index.html", _ana_style),
                      ("gizlilik.html", _gizlilik_style),
                      ("bilgi.css", _bilgi_css)):
        _mevcut_kontrast.extend(
            "%s: %s" % (_ad, _h)
            for _h in _kontrast.token_kontrast_hatalari(_css))
    kontrol("kontrast: mevcut acik/koyu site paleti WCAG AA",
            not _mevcut_kontrast,
            _mevcut_kontrast[0] if _mevcut_kontrast else "3 tema kaynagi")

    def _kontrast_yayin_kapisi(goreli_yol, eski, yeni, beklenen):
        import os
        import shutil
        import subprocess

        with tempfile.TemporaryDirectory(
                prefix="kontrast-kapi-",
                dir=os.path.dirname(_KOK)) as _td:
            _site = os.path.join(_td, "klinik-sitesi")
            shutil.copytree(
                _KOK, _site,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git"))
            _hasta = os.path.join(_td, "hasta-mesajlari")
            os.mkdir(_hasta)
            shutil.copy2(
                os.path.join(os.path.dirname(_KOK), "hasta-mesajlari",
                             "siteyi-yukle.py"),
                os.path.join(_hasta, "siteyi-yukle.py"))

            _hedef = os.path.join(_site, goreli_yol)
            _icerik = io.open(_hedef, encoding="utf-8").read()
            _bozuk = _icerik.replace(eski, yeni, 1)
            if _bozuk == _icerik:
                return False, "test bozuk kontrast uretemedi: " + goreli_yol
            with io.open(_hedef, "w", encoding="utf-8", newline="\n") as _f:
                _f.write(_bozuk)

            _d = subprocess.run(
                [sys.executable, "denetle.py"], cwd=_site,
                capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=60)
            _cikti = (_d.stdout or "") + (_d.stderr or "")
            _ok = (_d.returncode != 0
                   and "WCAG AA acik/koyu renk tokenlari" in _cikti
                   and beklenen in _cikti)
            return _ok, ("exit=%d" % _d.returncode
                         if _ok else _cikti[-300:])

    _kapi_ok, _kapi_ayrinti = _kontrast_yayin_kapisi(
        "bilgi.css", "--vurgu-metin:#fff;", "--vurgu-metin:#777;",
        "vurgu-metin/vurgu")
    kontrol("kontrast: bozuk ortak palet yayin kapisini DURDURUR",
            _kapi_ok, _kapi_ayrinti)

    def _eksik_varlik_kapisi():
        """Silinen bir yerel varlik yayini DURDURMALI (9 Agu 2026).

        `<picture>`e AVIF/WebP `<source>` eklendi. Hedef turev eksikse
        tarayici SECTIGI kaynaktan bir sonrakine DUSMEZ — gorsel kirik
        cikar. Eski denetim bunu goremiyordu: yalnizca UCUNCU TARAF
        adreslerine bakiyor, yerel yolun diskte karsiligini hic
        sormuyordu. Yani yesil denetimle kirik logo yayinlanabilirdi.
        """
        import os
        import shutil
        import subprocess

        with tempfile.TemporaryDirectory(
                prefix="varlik-kapi-",
                dir=os.path.dirname(_KOK)) as _td:
            _site = os.path.join(_td, "klinik-sitesi")
            shutil.copytree(
                _KOK, _site,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git"))
            _hasta = os.path.join(_td, "hasta-mesajlari")
            os.mkdir(_hasta)
            shutil.copy2(
                os.path.join(os.path.dirname(_KOK), "hasta-mesajlari",
                             "siteyi-yukle.py"),
                os.path.join(_hasta, "siteyi-yukle.py"))

            _kurban = os.path.join(_site, "gorsel",
                                   "logo-isaret-koyu-102.avif")
            if not os.path.exists(_kurban):
                return False, "test kurbani yok: gorsel/logo-isaret-koyu-102.avif"
            os.remove(_kurban)

            _d = subprocess.run(
                [sys.executable, "denetle.py"], cwd=_site,
                capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=120)
            _cikti = (_d.stdout or "") + (_d.stderr or "")
            _ok = (_d.returncode != 0
                   and "her yerel varlik referansinin diskte karsiligi var"
                   in _cikti
                   and "logo-isaret-koyu-102.avif" in _cikti)
            return _ok, ("exit=%d" % _d.returncode
                         if _ok else _cikti[-300:])

    _varlik_ok, _varlik_ayrinti = _eksik_varlik_kapisi()
    kontrol("eksik yerel varlik yayin kapisini DURDURUR",
            _varlik_ok, _varlik_ayrinti)

    _gizlilik_kapi_ok, _gizlilik_kapi_ayrinti = _kontrast_yayin_kapisi(
        "gizlilik.html", "--soluk:#5f7282;", "--soluk:#9a9a9a;",
        "gizlilik.html: acik: soluk/kagit")
    kontrol("kontrast: bozuk gizlilik paleti yayin kapisini DURDURUR",
            _gizlilik_kapi_ok, _gizlilik_kapi_ayrinti)

print("=" * 70)
print("DENETCI TESTI — denetle.py gercekten yakaliyor mu?")
print("=" * 70)
g = 0
for ad, ok, n in sonuc:
    print("  %s %-52s %s" % ("GECTI " if ok else "KALDI!", ad, n))
    g += 1 if ok else 0
print("=" * 70)
print("%d/%d gecti" % (g, len(sonuc)))
sys.exit(0 if g == len(sonuc) else 1)
