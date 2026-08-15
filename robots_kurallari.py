# -*- coding: utf-8 -*-
"""robots.txt gruplarını kök erişimi için yorumlayan küçük yardımcı."""

import re


def _ajan_urunu(deger):
    """User-agent alanından karşılaştırılacak ürün belirtecini çıkarır.

    Google robots yorumunda ``Googlebot/1.2`` ve ``Googlebot*`` gibi
    eşleşmeyen son ekler yok sayılır. Boş veya ürün belirteciyle başlamayan
    değerler geçerli bir grup oluşturmaz.
    """
    deger = deger.strip().casefold()
    if deger == "*":
        return "*"
    eslesme = re.match(r"[a-z0-9_-]+", deger)
    return eslesme.group(0) if eslesme else None


def _gruplar(metin):
    """(user-agent kümesi, allow/disallow kuralları) çiftlerini döndürür."""
    gruplar = []
    ajanlar = []
    kurallar = []

    for ham_satir in metin.splitlines():
        satir = ham_satir.split("#", 1)[0].strip()
        if not satir or ":" not in satir:
            continue
        alan, deger = (parca.strip() for parca in satir.split(":", 1))
        alan = alan.casefold()

        if alan == "user-agent":
            # Bir direktiften sonra gelen yeni User-agent yeni grubu başlatır.
            if kurallar:
                gruplar.append((tuple(ajanlar), tuple(kurallar)))
                ajanlar, kurallar = [], []
            ajan = _ajan_urunu(deger)
            if ajan:
                ajanlar.append(ajan)
        elif alan in {"allow", "disallow"} and ajanlar:
            kurallar.append((alan, deger))

    if ajanlar:
        gruplar.append((tuple(ajanlar), tuple(kurallar)))
    return gruplar


def kok_erisimi_engelli(metin, user_agent):
    """Verilen bot için ``/`` yolunun engellenip engellenmediğini döndürür.

    En özel user-agent grubu seçilir; aynı özgüllükteki gruplar birleştirilir.
    Kök için en uzun eşleşen kural geçerlidir ve eşitlikte Allow kazanır.
    """
    if not isinstance(metin, str) or not isinstance(user_agent, str):
        raise TypeError("metin ve user_agent str olmalı")

    ajan = _ajan_urunu(user_agent)
    if not ajan:
        return False
    eslesen = []
    for ajanlar, kurallar in _gruplar(metin):
        for desen in ajanlar:
            if desen == "*" or ajan.startswith(desen):
                ozgulluk = 0 if desen == "*" else len(desen)
                eslesen.append((ozgulluk, kurallar))

    if not eslesen:
        return False

    en_ozel = max(ozgulluk for ozgulluk, _ in eslesen)
    kok_kurallari = []
    for ozgulluk, kurallar in eslesen:
        if ozgulluk != en_ozel:
            continue
        for tur, yol in kurallar:
            # Boş Disallow hiçbir şeyi engellemez. '*' sıfır veya daha çok
            # karakteri, sondaki '$' ise yol sonunu temsil eder.
            if not yol or not yol.startswith("/"):
                continue
            son_sinirli = yol.endswith("$")
            govde = yol[:-1] if son_sinirli else yol
            desen = "^" + re.escape(govde).replace(r"\*", ".*")
            if son_sinirli:
                desen += "$"
            if re.match(desen, "/"):
                # Özgüllük hesabında jokerin kendisi yol karakteri sayılmaz.
                kok_kurallari.append((tur, len(govde.replace("*", ""))))

    if not kok_kurallari:
        return False
    en_uzun = max(uzunluk for _, uzunluk in kok_kurallari)
    kazananlar = {tur for tur, uzunluk in kok_kurallari if uzunluk == en_uzun}
    return "disallow" in kazananlar and "allow" not in kazananlar
