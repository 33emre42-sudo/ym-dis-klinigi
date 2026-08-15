# -*- coding: utf-8 -*-
import unittest
from pathlib import Path

from robots_kurallari import kok_erisimi_engelli


class RobotsKurallariTesti(unittest.TestCase):
    def test_seo_araci_kapaliyken_google_acik_kalir(self):
        metin = """
User-agent: Googlebot
Allow: /

User-agent: AhrefsBot
Disallow: /

User-agent: *
Allow: /
"""
        self.assertFalse(kok_erisimi_engelli(metin, "Googlebot"))
        self.assertTrue(kok_erisimi_engelli(metin, "AhrefsBot"))

    def test_wildcard_kok_kapisi_googlei_engeller(self):
        metin = """
User-agent: *
Disallow: /
"""
        self.assertTrue(kok_erisimi_engelli(metin, "Googlebot"))

    def test_ozel_allow_wildcard_disallowdan_daha_ozeldir(self):
        metin = """
User-agent: Googlebot
Allow: /

User-agent: *
Disallow: /
"""
        self.assertFalse(kok_erisimi_engelli(metin, "Googlebot"))
        self.assertTrue(kok_erisimi_engelli(metin, "BilinmeyenBot"))

    def test_esit_uzunlukta_allow_kazanir(self):
        metin = """
User-agent: Googlebot
Disallow: /
Allow: /
"""
        self.assertFalse(kok_erisimi_engelli(metin, "Googlebot"))

    def test_joker_ve_son_isaretli_kural_koku_engeller(self):
        for kural in ("/*", "/$", "/*$"):
            with self.subTest(kural=kural):
                metin = "User-agent: *\nDisallow: %s\n" % kural
                self.assertTrue(kok_erisimi_engelli(metin, "Googlebot"))

    def test_alt_yol_kurali_koku_engellemez(self):
        metin = "User-agent: *\nDisallow: /ozel/\n"
        self.assertFalse(kok_erisimi_engelli(metin, "Googlebot"))

    def test_surumu_ekli_googlebot_grubu_googlebotla_esdegerdir(self):
        metin = "User-agent: Googlebot/1.2\nDisallow: /\n"
        self.assertTrue(kok_erisimi_engelli(metin, "Googlebot"))

    def test_yildiz_ekli_googlebot_grubu_googlebotla_esdegerdir(self):
        metin = "User-agent: Googlebot*\nDisallow: /\n"
        self.assertTrue(kok_erisimi_engelli(metin, "Googlebot"))

    def test_bos_user_agent_gecerli_grup_olusturmaz(self):
        metin = "User-agent:\nDisallow: /\n"
        self.assertFalse(kok_erisimi_engelli(metin, "Googlebot"))

    def test_kok_yolu_olmayan_kural_yok_sayilir(self):
        metin = "User-agent: *\nDisallow: *\n"
        self.assertFalse(kok_erisimi_engelli(metin, "Googlebot"))

    def test_iki_denetcinin_robots_sozlesmesi_ortak_yardimcidadir(self):
        kok = Path(__file__).resolve().parent
        for dosya_adi in ("denetle.py", "seo-denetle.py"):
            kaynak = (kok / dosya_adi).read_text(encoding="utf-8")
            with self.subTest(dosya=dosya_adi):
                self.assertIn(
                    "from robots_kurallari import kok_erisimi_engelli", kaynak
                )
                self.assertIn("kok_erisimi_engelli(", kaynak)


if __name__ == "__main__":
    unittest.main()
