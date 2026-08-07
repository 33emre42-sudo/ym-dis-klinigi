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
})();
