/* YM Klinik — kucuk arayuz davranislari.
   ------------------------------------------------------------------
   ⚠️ 8 Agu 2026, hekim bildirdi: "bir ikona tikladiktan sonra kapatmak
   icin bos alana tiklayinca kapanmiyor."

   Dogru tespit. Yerel <details> ogesi DISARI TIKLAMAYLA KAPANMAZ —
   yalnizca kendi summary'sine basilinca kapanir. Hamburger menuyu ve
   dil secicisini <details> ile kurduk (JS'siz calissinlar diye); bu
   davranis o tercihin bedeli. Bedel kucuk ve buradan kapatiliyor.

   Kapsam BILEREK dar:
     · hamburger menu  (details.menu-ac)
     · dil secici      (details.dil-sec)
   Sohbet kutusu KAPSAM DISI: kendi kapatma dugmesi var ve hasta
   yazarken sayfaya dokununca sohbetin kapanmasi zarar verirdi.

   ⚠️ Dosya TEK KAYNAK. Ayni mantigi 77 sayfaya satir ici kopyalamak,
   bu projede defalarca ayrisma uretmis bir kalip.                     */
(function () {
  "use strict";

  var SECICI = "details.menu-ac[open], details.dil-sec[open]";

  /* Tiklanan yer bu menunun KENDI alani mi?
     ⚠️ Dil secicide liste `details`in ICINDE, ama hamburgerde panel
     (`nav.menu`) DISINDA: `:has()` ile acildigi icin DOM'da serit'in
     KARDESI. Duz `contains()` bu yuzden yetmiyordu — panel bosluguna
     dokununca menu kapaniyordu. Panel acikca eslestiriliyor. */
  function icinde(d, hedef) {
    if (!hedef) return false;
    if (d.contains(hedef)) return true;
    if (d.classList.contains("menu-ac")) {
      var serit = d.closest(".serit");
      var panel = serit && serit.nextElementSibling;
      if (panel && panel.classList.contains("menu") && panel.contains(hedef)) {
        return true;
      }
    }
    return false;
  }

  function kapat(haric) {
    var acik = document.querySelectorAll(SECICI);
    for (var i = 0; i < acik.length; i++) {
      if (icinde(acik[i], haric)) continue;
      acik[i].open = false;
    }
  }

  // Bos alana tiklama. `capture` degil normal asama: baglanti
  // tiklamasi once kendi isini yapsin.
  document.addEventListener("click", function (e) {
    kapat(e.target);
  });

  // Esc ile kapatma — klavyeyle gezen kullanici icin (erisilebilirlik).
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" || e.key === "Esc") kapat(null);
  });

  // Biri acilinca oteki kapansin: ikisi yan yana ve ust uste binerlerdi.
  document.addEventListener("toggle", function (e) {
    var t = e.target;
    if (!t || !t.open) return;
    if (!t.matches || !t.matches("details.menu-ac, details.dil-sec")) return;
    kapat(t);
  }, true);   // `toggle` kabarmaz — yakalama asamasinda dinleniyor.

  /* ------------------------------------------------------------------
     MOBIL SABIT CTA — okurken icerigi ortmesin
     ------------------------------------------------------------------
     K89 canli 390x844 olcumunde cubuk 74,8px'lik ilk uyari kartini
     fiziksel olarak kapatiyordu. Header telefonu zaten sticky: cubuk
     sayfa basinda ve asagi okurken gizli, yukari donuste / sayfa sonunda
     gorunur. Gizliyken inert + aria-hidden ile odak tuzagi da yok. */
  var sabit = document.querySelector(".sabit");
  if (sabit) {
    var sonY = Math.max(0, window.scrollY || 0);
    var ctaKareBekliyor = false;

    function ctaGoster(goster) {
      sabit.classList.toggle("sabit-gorunur", goster);
      sabit.setAttribute("aria-hidden", goster ? "false" : "true");
      if (goster) sabit.removeAttribute("inert");
      else sabit.setAttribute("inert", "");
    }

    function ctaKonumGuncelle() {
      var y = Math.max(0, window.scrollY || 0);
      var son = Math.max(0, document.documentElement.scrollHeight - window.innerHeight);
      var asagi = y > sonY + 6;
      var yukari = y < sonY - 6;
      var sonaYakin = son - y <= 24;

      if (y < 120 || asagi) ctaGoster(false);
      else if (yukari || sonaYakin) ctaGoster(true);

      sonY = y;
      ctaKareBekliyor = false;
    }

    ctaGoster(false);
    window.addEventListener("scroll", function () {
      if (ctaKareBekliyor) return;
      ctaKareBekliyor = true;
      window.requestAnimationFrame(ctaKonumGuncelle);
    }, {passive:true});
    window.addEventListener("resize", ctaKonumGuncelle);
  }

  /* ------------------------------------------------------------------
     TIKLA-YUKLE HARITA — 9 Agu 2026
     ------------------------------------------------------------------
     Hekim rakip sitedeki gomulu haritayi gosterip "bizimki de boyle
     etkilesimli olsun" dedi. Dogru istek; ama duz bir <iframe> BU
     SITEYE KONULAMAZ:

       gizlilik.html soz veriyor —
       "Sayfayi actiginizda tarayiciniz hicbir ucuncu taraf sunucusuna
        istek gondermez; dolayisiyla IP adresiniz ... yurt disina
        aktarilmaz."

     `denetle.py` bu sozu ZORUNLU tutuyor ve <iframe src> ucuncu
     tarafa bakiyorsa yayin kapisini kapatiyor (3. tur bulgu 12).

     Cozum sozu bozmak degil: harita ancak ziyaretci DUGMEYE BASINCA
     yukleniyor. denetle.py'nin kendi yorumundaki ayrim bu:
     "kullanicinin TIKLAMASIYLA acilan baglantilar kaynak yuklemesi
     DEGILDIR" — wa.me dugmesiyle ayni kategori.

     ⚠️ ADRES DEGIL KOORDINAT gomuluyor. Yer adiyla gomulunce Google
     isletme kartini aciyor ve orada YILDIZ PUANI cikiyor; rakip
     sitede tam olarak bu goruluyor (4,8 · 148 yorum). Saglikta
     tanitim yonetmeligi hasta yorumu ve puan gosterimini YASAKLIYOR
     (K15) — puan bizim sayfamizda gorunemez. Koordinat gomulunce
     yalnizca sade bir isaretci cikiyor.                              */
  var KOORDINAT = "41.034264,28.8429051";
  var HARITA_URL = "https://maps.google.com/maps?q=" + KOORDINAT +
                   "&z=17&hl=tr&output=embed";

  document.addEventListener("click", function (e) {
    var dugme = e.target.closest && e.target.closest(".harita-onizleme");
    if (!dugme) return;
    var kart = dugme.closest("[data-harita]");
    if (!kart || kart.classList.contains("acildi")) return;

    var cerceve = document.createElement("iframe");
    cerceve.src = HARITA_URL;
    cerceve.title = kart.getAttribute("data-harita-baslik") ||
                    "Klinigin haritadaki konumu";
    cerceve.loading = "lazy";
    cerceve.setAttribute("referrerpolicy", "no-referrer");
    cerceve.setAttribute("allowfullscreen", "");
    // Onizlemenin YERINE degil ONUNE eklenir; `.acildi` onizlemeyi
    // gizler. Boylece geri alinabilir ve DOM'da olcu korunur.
    kart.insertBefore(cerceve, kart.firstChild);
    kart.classList.add("acildi");
  });
})();
