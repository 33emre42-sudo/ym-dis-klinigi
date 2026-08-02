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


sonuc.append(("kapi: alt klasordeki HTML denetimi DURDURUR",
              _alt_klasor_kapisi(),
              "denetim sifir dondu — sayfa denetimsiz yayina giderdi"))

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
