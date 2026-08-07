#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Site renk tokenlarini WCAG 2.1 AA kontrast esiklerine gore denetler.

Kaynak: https://www.w3.org/TR/WCAG21/#contrast-minimum
Bu statik kontrol semantik paleti korur; tarayici ve ekran okuyucu testi
yerine gecmez.
"""
import re


_NORMAL_ESIK = 4.5
_BUYUK_ESIK = 3.0
_ESLESMELER = (
    ("murekkep", "kagit", _NORMAL_ESIK),
    ("murekkep", "kat", _NORMAL_ESIK),
    ("gri", "kagit", _NORMAL_ESIK),
    ("gri", "kat", _NORMAL_ESIK),
    ("soluk", "kagit", _NORMAL_ESIK),
    ("soluk", "kat", _NORMAL_ESIK),
    ("vurgu", "kagit", _NORMAL_ESIK),
    ("vurgu", "kat", _NORMAL_ESIK),
    # --vurgu2 tek basina yalniz buyuk gradient baslikta kullanilir.
    ("vurgu2", "kagit", _BUYUK_ESIK),
    ("vurgu2", "kat", _BUYUK_ESIK),
    # Dugme ve rozetlerde normal/kucuk metin gradientin iki ucunda da okunur.
    ("vurgu-metin", "vurgu", _NORMAL_ESIK),
    ("vurgu-metin", "vurgu2", _NORMAL_ESIK),
)
_TOKEN = re.compile(r"--([a-zA-Z0-9_-]+)\s*:\s*([^;{}]+)")
_ROOT_SOZ = re.compile(r":root\b", re.I)
_ROOT_ADAY = re.compile(r":root\b(?P<selector>[^{;}]*)\{", re.I)
_VAR = re.compile(r"var\(\s*--([a-zA-Z0-9_-]+)", re.I)
_MEDIA = re.compile(r"@media\b[^{]*\{", re.I)
_KOYU = re.compile(
    r"@media\s*\(\s*prefers-color-scheme\s*:\s*dark\s*\)\s*\{",
    re.I,
)


def _rgb(renk):
    deger = renk.lstrip("#")
    if len(deger) == 3:
        deger = "".join(karakter * 2 for karakter in deger)
    if len(deger) != 6 or not re.fullmatch(r"[0-9a-fA-F]{6}", deger):
        raise ValueError("yalniz #RGB ve #RRGGBB renkleri desteklenir: %r" % renk)
    return tuple(int(deger[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def _bagil_parlaklik(renk):
    kanallar = []
    for kanal in _rgb(renk):
        if kanal <= 0.04045:
            kanallar.append(kanal / 12.92)
        else:
            kanallar.append(((kanal + 0.055) / 1.055) ** 2.4)
    return (0.2126 * kanallar[0] + 0.7152 * kanallar[1]
            + 0.0722 * kanallar[2])


def kontrast_orani(on_plan, arka_plan):
    """Iki opak sRGB rengin WCAG kontrast oranini dondurur."""
    a = _bagil_parlaklik(on_plan)
    b = _bagil_parlaklik(arka_plan)
    acik, koyu = max(a, b), min(a, b)
    return (acik + 0.05) / (koyu + 0.05)


def _yorumlari_sil(metin):
    """Yorumlari konumlari bozmadan sil; kapanmayan yorum EOF'ta biter."""
    karakterler = list(metin)
    konum = 0
    while True:
        bas = metin.find("/*", konum)
        if bas < 0:
            break
        bit = metin.find("*/", bas + 2)
        son = len(metin) if bit < 0 else bit + 2
        for i in range(bas, son):
            if karakterler[i] not in "\r\n":
                karakterler[i] = " "
        konum = son
    return "".join(karakterler)


def _blok_siniri(metin, acilis):
    """`acilis` konumundaki dengeli CSS blogunun [icerik, kapanis] siniri."""
    derinlik = 0
    tirnak = None
    kacis = False
    for konum in range(acilis, len(metin)):
        karakter = metin[konum]
        if tirnak is not None:
            if kacis:
                kacis = False
            elif karakter == "\\":
                kacis = True
            elif karakter == tirnak:
                tirnak = None
            continue
        if karakter in ("'", '"'):
            tirnak = karakter
        elif karakter == "{":
            derinlik += 1
        elif karakter == "}":
            derinlik -= 1
            if derinlik == 0:
                return konum
    return None


def _tokenlari_oku(blok):
    tokenlar = {}
    for ad, deger in _TOKEN.findall(blok or ""):
        tokenlar[ad] = deger.strip()
    return tokenlar


def _temalari_oku(css):
    temiz = _yorumlari_sil(css)
    hatalar = []
    medya = []
    koyu_baslangiclari = {eslesme.start() for eslesme in _KOYU.finditer(temiz)}
    for eslesme in _MEDIA.finditer(temiz):
        kapanis = _blok_siniri(temiz, eslesme.end() - 1)
        if kapanis is None:
            hatalar.append("dengesiz @media blogu")
            continue
        medya.append((
            eslesme.start(),
            kapanis,
            eslesme.start() in koyu_baslangiclari,
        ))

    root_adaylari = {
        eslesme.start(): eslesme for eslesme in _ROOT_ADAY.finditer(temiz)
    }
    acik = {}
    koyu = {}
    acik_bildirimi = False
    koyu_bildirimi = False
    for root_soz in _ROOT_SOZ.finditer(temiz):
        eslesme = root_adaylari.get(root_soz.start())
        if (eslesme is None
                or eslesme.group("selector").strip()):
            hatalar.append("desteklenmeyen :root secicisi")
            continue
        acilis = eslesme.end() - 1
        kapanis = _blok_siniri(temiz, acilis)
        if kapanis is None:
            hatalar.append("dengesiz :root blogu")
            continue
        kapsayan = [aralik for aralik in medya
                    if aralik[0] <= acilis <= aralik[1]]
        if any(not aralik[2] for aralik in kapsayan):
            hatalar.append("desteklenmeyen kosullu :root blogu")
            continue
        koyu_icinde = bool(kapsayan) and all(
            aralik[2] for aralik in kapsayan)
        tokenlar = _tokenlari_oku(temiz[acilis + 1:kapanis])
        if koyu_icinde:
            koyu_bildirimi = True
            koyu.update(tokenlar)
        else:
            acik_bildirimi = True
            acik.update(tokenlar)
            # Koyu medya etkin oldugunda kosulsuz :root da cascade'e katilir.
            koyu.update(tokenlar)

    if not acik_bildirimi or not koyu_bildirimi:
        hatalar.append("acik ve koyu :root renk temalari bulunamadi")
        return None, None, hatalar
    return acik, koyu, hatalar


def token_kontrast_hatalari(css):
    """Kaynakta kullanilan semantik tokenlarin kontrastlarini listeler."""
    temiz = _yorumlari_sil(css)
    if _ROOT_SOZ.search(temiz) is None:
        return []

    aktif_tokenlar = {ad for ad, _ in _TOKEN.findall(temiz)}
    aktif_tokenlar.update(_VAR.findall(temiz))
    acik, koyu, ayrisma_hatalari = _temalari_oku(temiz)
    if acik is None:
        return ayrisma_hatalari

    hatalar = list(ayrisma_hatalari)
    for tema, tokenlar in (("acik", acik), ("koyu", koyu)):
        # Bir eslesme, on-plan tokeni bu kaynakta bildiriliyor veya
        # var(--token) ile kullaniliyorsa bu kaynagin sozlesmesidir.
        eslesmeler = [
            eslesme for eslesme in _ESLESMELER
            if eslesme[0] in aktif_tokenlar
        ]
        if "uyari-zemin" in aktif_tokenlar:
            eslesmeler.extend((
                ("murekkep", "uyari-zemin", _NORMAL_ESIK),
                ("gri", "uyari-zemin", _NORMAL_ESIK),
            ))

        gerekli = {ad for eslesme in eslesmeler for ad in eslesme[:2]}
        eksik = sorted(gerekli.difference(tokenlar))
        hatalar.extend("%s: %s eksik" % (tema, ad) for ad in eksik)

        gecersiz = set()
        for ad in sorted(gerekli.intersection(tokenlar)):
            try:
                _rgb(tokenlar[ad])
            except (TypeError, ValueError):
                gecersiz.add(ad)
                hatalar.append("%s: %s rengi cozumlenemedi: %r"
                                % (tema, ad, tokenlar[ad]))

        for on_plan, arka_plan, esik in eslesmeler:
            if (on_plan not in tokenlar or arka_plan not in tokenlar
                    or on_plan in gecersiz or arka_plan in gecersiz):
                continue
            oran = kontrast_orani(tokenlar[on_plan], tokenlar[arka_plan])
            if oran + 1e-9 < esik:
                hatalar.append(
                    "%s: %s/%s %.3f:1 < %.1f:1"
                    % (tema, on_plan, arka_plan, oran, esik)
                )
    return hatalar
