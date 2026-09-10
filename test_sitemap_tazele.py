#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic regression tests for sitemap lastmod refreshes."""
import contextlib
import importlib.util
import io
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock


SITE = "https://ymdisklinigi.com/"
KOK = Path(__file__).resolve().parent
KAYNAK_BETIK = KOK / "sitemap-tazele.py"


def tarih_mtime_ata(yol, tarih):
    """Set a local-file mtime at a noon UTC instant for a stable calendar day."""
    an = datetime.strptime(tarih, "%Y-%m-%d").replace(
        hour=12, tzinfo=timezone.utc).timestamp()
    os.utime(yol, (an, an))


class SitemapTazeleTesti(unittest.TestCase):
    def setUp(self):
        self.gecici = tempfile.TemporaryDirectory(prefix="sitemap-lastmod-")
        self.kok = Path(self.gecici.name) / "repo"
        self.kok.mkdir()
        shutil.copy2(KAYNAK_BETIK, self.kok / "sitemap-tazele.py")
        (self.kok / "en").mkdir()
        (self.kok / "index.html").write_text("root", encoding="utf-8")
        (self.kok / "en" / "index.html").write_text("locale", encoding="utf-8")
        (self.kok / "tracked.html").write_text("tracked", encoding="utf-8")
        (self.kok / "staged.html").write_text("staged", encoding="utf-8")
        (self.kok / "unstaged.html").write_text("unstaged", encoding="utf-8")
        self.sitemap_yaz({
            SITE: "2001-01-01",
            SITE + "en/": "2001-01-01",
            SITE + "tracked.html": "2001-01-01",
            SITE + "staged.html": "2001-01-01",
            SITE + "unstaged.html": "2001-01-01",
        })
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Sitemap Test")
        self.git("add", ".")
        self.git("commit", "-q", "-m", "fixture", tarih="2024-02-03T12:00:00+00:00")
        self.checkout_tarihi = "2035-08-09"
        for goreli in ("index.html", "en/index.html", "tracked.html",
                       "staged.html", "unstaged.html"):
            tarih_mtime_ata(self.kok / goreli, self.checkout_tarihi)

    def tearDown(self):
        self.gecici.cleanup()

    def git(self, *args, tarih=None):
        ortam = os.environ.copy()
        if tarih:
            ortam["GIT_AUTHOR_DATE"] = tarih
            ortam["GIT_COMMITTER_DATE"] = tarih
        sonuc = subprocess.run(
            ["git", *args], cwd=self.kok, env=ortam, text=True,
            encoding="utf-8", errors="replace", capture_output=True)
        self.assertEqual(
            sonuc.returncode, 0,
            "git failed: %s\n%s" % (" ".join(args), sonuc.stderr))
        return sonuc

    def sitemap_yaz(self, tarihler):
        url_bolumleri = []
        kayitlar = tarihler.items() if hasattr(tarihler, "items") else tarihler
        for loc, lastmod in kayitlar:
            url_bolumleri.append(
                "  <url><loc>%s</loc><lastmod>%s</lastmod></url>" %
                (loc, lastmod))
        (self.kok / "sitemap.xml").write_text(
            "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
            "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">\n"
            "%s\n</urlset>\n" % "\n".join(url_bolumleri),
            encoding="utf-8", newline="\n")

    def sitemap_tarihleri(self):
        return dict(re.findall(
            r"<loc>([^<]+)</loc>\s*<lastmod>([^<]+)</lastmod>",
            (self.kok / "sitemap.xml").read_text(encoding="utf-8")))

    def araci_calistir(self, *args):
        return subprocess.run(
            [sys.executable, "-B", "sitemap-tazele.py", *args], cwd=self.kok,
            text=True, encoding="utf-8", errors="replace", capture_output=True)

    def modul_yukle(self):
        ad = "sitemap_tazele_fixture_%d" % id(self)
        spec = importlib.util.spec_from_file_location(
            ad, self.kok / "sitemap-tazele.py")
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        modul = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modul)
        return modul

    def test_clean_tracked_pages_use_commit_dates_not_checkout_mtime(self):
        sonuc = self.araci_calistir("--uygula")
        self.assertEqual(sonuc.returncode, 0, sonuc.stdout + sonuc.stderr)
        tarihler = self.sitemap_tarihleri()
        for loc in (SITE, SITE + "en/", SITE + "tracked.html"):
            with self.subTest(loc=loc):
                self.assertEqual(tarihler[loc], "2024-02-03")
                self.assertNotEqual(tarihler[loc], self.checkout_tarihi)

    def test_changed_staged_and_untracked_pages_use_local_mtime(self):
        (self.kok / "unstaged.html").write_text("unstaged change", encoding="utf-8")
        tarih_mtime_ata(self.kok / "unstaged.html", "2036-04-05")
        (self.kok / "staged.html").write_text("staged change", encoding="utf-8")
        tarih_mtime_ata(self.kok / "staged.html", "2036-05-06")
        self.git("add", "staged.html")
        (self.kok / "untracked.html").write_text("new page", encoding="utf-8")
        tarih_mtime_ata(self.kok / "untracked.html", "2036-06-07")
        self.sitemap_yaz({
            SITE + "unstaged.html": "2001-01-01",
            SITE + "staged.html": "2001-01-01",
            SITE + "untracked.html": "2001-01-01",
        })

        sonuc = self.araci_calistir("--uygula")
        self.assertEqual(sonuc.returncode, 0, sonuc.stdout + sonuc.stderr)
        tarihler = self.sitemap_tarihleri()
        self.assertEqual(tarihler[SITE + "unstaged.html"], "2036-04-05")
        self.assertEqual(tarihler[SITE + "staged.html"], "2036-05-06")
        self.assertEqual(tarihler[SITE + "untracked.html"], "2036-06-07")

    def test_git_status_nul_records_are_exact_and_fail_closed(self):
        beklenen_komut = [
            "git", "status", "--porcelain=v1", "-z", "--untracked-files=all",
            "--", "tracked.html",
        ]
        for durum in ("M ", " M", "MM", "A ", "AM", "??"):
            with self.subTest(izinli_durum=durum):
                modul = self.modul_yukle()
                cagrilar = []

                def sahte_git(komut):
                    cagrilar.append(komut)
                    return subprocess.CompletedProcess(
                        komut, 0, stdout=durum + " tracked.html\0", stderr="")

                with mock.patch.object(modul, "git_calistir", side_effect=sahte_git):
                    self.assertTrue(modul.git_degisiklik_var_mi(
                        str(self.kok / "tracked.html")))
                self.assertEqual(cagrilar, [beklenen_komut])

        bozuk_durumlar = (
            ("non-NUL", " M tracked.html\n"),
            ("truncated", " M tracked.html"),
            ("malformed", "MM\ttracked.html\0"),
            ("extra record", " M tracked.html\0?? other.html\0"),
            ("deleted", "D  tracked.html\0"),
            ("rename", "R  tracked.html\0old.html\0"),
            ("copy", "C  tracked.html\0old.html\0"),
            ("conflict", "UU tracked.html\0"),
            ("wrong path", " M other.html\0"),
        )
        for ad, durum in bozuk_durumlar:
            with self.subTest(bozuk_durum=ad):
                self.sitemap_yaz({SITE + "tracked.html": "2001-01-01"})
                modul = self.modul_yukle()
                once = (self.kok / "sitemap.xml").read_bytes()

                def sahte_git(komut):
                    self.assertEqual(komut, beklenen_komut)
                    return subprocess.CompletedProcess(
                        komut, 0, stdout=durum, stderr="")

                with mock.patch.object(modul, "git_calistir", side_effect=sahte_git):
                    with mock.patch.object(
                            modul.sys, "argv", ["sitemap-tazele.py", "--uygula"]):
                        with contextlib.redirect_stdout(io.StringIO()):
                            donus = modul.main()
                self.assertNotEqual(donus, 0)
                self.assertEqual((self.kok / "sitemap.xml").read_bytes(), once)
                self.assertEqual(list(self.kok.glob(".sitemap-tazele-*")), [])

    def test_apply_is_atomic_and_idempotent_under_write_failures(self):
        modul = self.modul_yukle()
        yer_degistirmeler = []
        fsync_cagrilari = []
        gercek_replace = os.replace
        gercek_fsync = os.fsync

        def izle(kaynak, hedef):
            yer_degistirmeler.append((Path(kaynak), Path(hedef)))
            return gercek_replace(kaynak, hedef)

        def fsync_izle(tanimlayici):
            fsync_cagrilari.append(tanimlayici)
            return gercek_fsync(tanimlayici)

        with mock.patch.object(modul.os, "fsync", side_effect=fsync_izle):
            with mock.patch.object(modul.os, "replace", side_effect=izle):
                with mock.patch.object(
                        modul.sys, "argv", ["sitemap-tazele.py", "--uygula"]):
                    with contextlib.redirect_stdout(io.StringIO()):
                        ilk_donus = modul.main()
                ilk_bayt = (self.kok / "sitemap.xml").read_bytes()
                with mock.patch.object(
                        modul.sys, "argv", ["sitemap-tazele.py", "--uygula"]):
                    with contextlib.redirect_stdout(io.StringIO()):
                        ikinci_donus = modul.main()

        self.assertEqual(ilk_donus, 0)
        self.assertEqual(ikinci_donus, 0)
        self.assertEqual(len(yer_degistirmeler), 1)
        self.assertGreaterEqual(len(fsync_cagrilari), 1)
        kaynak, hedef = yer_degistirmeler[0]
        self.assertEqual(kaynak.resolve().parent, self.kok.resolve())
        self.assertEqual(hedef.resolve(), (self.kok / "sitemap.xml").resolve())
        self.assertEqual((self.kok / "sitemap.xml").read_bytes(), ilk_bayt)
        self.assertEqual(list(self.kok.glob(".sitemap-tazele-*")), [])

        self.sitemap_yaz({SITE + "tracked.html": "2001-01-01"})
        once = (self.kok / "sitemap.xml").read_bytes()
        with mock.patch.object(modul.os, "fsync", side_effect=OSError("fsync fail")):
            with mock.patch.object(
                    modul.sys, "argv", ["sitemap-tazele.py", "--uygula"]):
                with contextlib.redirect_stdout(io.StringIO()):
                    fsync_donus = modul.main()
        self.assertNotEqual(fsync_donus, 0)
        self.assertEqual((self.kok / "sitemap.xml").read_bytes(), once)
        self.assertEqual(list(self.kok.glob(".sitemap-tazele-*")), [])

        self.sitemap_yaz({SITE + "tracked.html": "2001-01-01"})
        once = (self.kok / "sitemap.xml").read_bytes()
        with mock.patch.object(modul.os, "replace", side_effect=OSError("replace fail")):
            with mock.patch.object(
                    modul.sys, "argv", ["sitemap-tazele.py", "--uygula"]):
                with contextlib.redirect_stdout(io.StringIO()):
                    replace_donus = modul.main()
        self.assertNotEqual(replace_donus, 0)
        self.assertEqual((self.kok / "sitemap.xml").read_bytes(), once)
        self.assertEqual(list(self.kok.glob(".sitemap-tazele-*")), [])

    def test_short_atomic_write_fails_without_replacing_sitemap(self):
        modul = self.modul_yukle()
        hedef = self.kok / "sitemap.xml"
        once = hedef.read_bytes()
        gercek_ac = modul.io.open

        class KisaYazan:
            def __init__(self, dosya):
                self.dosya = dosya

            def __enter__(self):
                self.dosya.__enter__()
                return self

            def __exit__(self, *args):
                return self.dosya.__exit__(*args)

            def write(self, metin):
                self.dosya.write(metin)
                return len(metin) - 1

            def flush(self):
                return self.dosya.flush()

            def fileno(self):
                return self.dosya.fileno()

        def kisa_ac(*args, **kwargs):
            return KisaYazan(gercek_ac(*args, **kwargs))

        with mock.patch.object(modul.io, "open", side_effect=kisa_ac):
            with self.assertRaises(OSError):
                modul.atomik_yaz(str(hedef), "forced short write")
        self.assertEqual(hedef.read_bytes(), once)
        self.assertEqual(list(self.kok.glob(".sitemap-tazele-*")), [])

    def test_cleanup_failure_is_hold_and_never_claims_sitemap_was_written(self):
        self.sitemap_yaz({SITE + "tracked.html": "2001-01-01"})
        modul = self.modul_yukle()
        hedef = self.kok / "sitemap.xml"
        once = hedef.read_bytes()
        geciciler = []
        gercek_unlink = modul.os.unlink

        def replace_basarisiz(kaynak, hedef_yol):
            geciciler.append(kaynak)
            raise OSError("replace fail")

        def temizlik_basarisiz(yol):
            if yol in geciciler:
                raise OSError("cleanup fail")
            return gercek_unlink(yol)

        try:
            with mock.patch.object(modul.os, "replace", side_effect=replace_basarisiz):
                with mock.patch.object(modul.os, "unlink", side_effect=temizlik_basarisiz):
                    with mock.patch.object(
                            modul.sys, "argv", ["sitemap-tazele.py", "--uygula"]):
                        ekran = io.StringIO()
                        with contextlib.redirect_stdout(ekran):
                            donus = modul.main()
            self.assertNotEqual(donus, 0)
            self.assertIn("cleanup fail", ekran.getvalue())
            self.assertNotIn("YAZILDI", ekran.getvalue())
            self.assertEqual(hedef.read_bytes(), once)
            self.assertEqual(len(geciciler), 1)
            self.assertTrue(os.path.lexists(geciciler[0]))
        finally:
            for gecici in geciciler:
                if os.path.lexists(gecici):
                    gercek_unlink(gecici)
        self.assertFalse(os.path.lexists(geciciler[0]))
        self.assertEqual(list(self.kok.glob(".sitemap-tazele-*")), [])

    def test_noncanonical_or_escaping_urls_fail_closed_without_writing(self):
        (self.kok.parent / "outside.html").write_text("outside", encoding="utf-8")
        senaryolar = (
            ("foreign origin", "https://example.invalid/tracked.html"),
            ("dot segment", SITE + "en/../tracked.html"),
            ("outside repo", SITE + "../outside.html"),
            ("backslash", SITE + "\\tracked.html"),
            ("percent escape", SITE + "%74racked.html"),
            ("absolute-looking", SITE + "/tracked.html"),
        )
        for ad, loc in senaryolar:
            with self.subTest(ad=ad):
                self.sitemap_yaz({loc: "2001-01-01"})
                once = (self.kok / "sitemap.xml").read_bytes()
                sonuc = self.araci_calistir("--uygula")
                self.assertNotEqual(sonuc.returncode, 0, sonuc.stdout + sonuc.stderr)
                self.assertEqual((self.kok / "sitemap.xml").read_bytes(), once)
                self.assertEqual(list(self.kok.glob(".sitemap-tazele-*")), [])

    def test_non_ascii_or_unsafe_url_characters_fail_closed_without_writing(self):
        senaryolar = (
            ("DEL", SITE + "tracked\x7f.html"),
            ("nonbreaking space", SITE + "tracked\u00a0.html"),
            ("zero width", SITE + "tracked\u200b.html"),
            ("bidi control", SITE + "tracked\u202e.html"),
            ("uppercase", SITE + "Tracked.html"),
            ("underscore", SITE + "tracked_name.html"),
        )
        for ad, loc in senaryolar:
            with self.subTest(ad=ad):
                self.sitemap_yaz({loc: "2001-01-01"})
                once = (self.kok / "sitemap.xml").read_bytes()
                sonuc = self.araci_calistir("--uygula")
                self.assertNotEqual(sonuc.returncode, 0, sonuc.stdout + sonuc.stderr)
                self.assertEqual((self.kok / "sitemap.xml").read_bytes(), once)
                self.assertEqual(list(self.kok.glob(".sitemap-tazele-*")), [])

    def test_inside_symlink_path_fails_closed_without_writing(self):
        bag = self.kok / "alias.html"
        try:
            try:
                os.symlink("tracked.html", bag)
            except (NotImplementedError, OSError) as hata:
                self.skipTest("symlink olusturulamadi: %s" % hata)
            self.sitemap_yaz({SITE + "alias.html": "2001-01-01"})
            once = (self.kok / "sitemap.xml").read_bytes()
            sonuc = self.araci_calistir("--uygula")
            self.assertNotEqual(sonuc.returncode, 0, sonuc.stdout + sonuc.stderr)
            self.assertEqual((self.kok / "sitemap.xml").read_bytes(), once)
            self.assertEqual(list(self.kok.glob(".sitemap-tazele-*")), [])
        finally:
            if os.path.lexists(bag):
                os.unlink(bag)

    def test_lstat_symlink_path_fails_closed_without_writing(self):
        self.sitemap_yaz({SITE + "tracked.html": "2001-01-01"})
        modul = self.modul_yukle()
        once = (self.kok / "sitemap.xml").read_bytes()

        class BagDurumu:
            st_mode = stat.S_IFLNK

        with mock.patch.object(modul.os, "lstat", return_value=BagDurumu()):
            with mock.patch.object(modul.os.path, "realpath", side_effect=os.path.abspath):
                with mock.patch.object(
                        modul.sys, "argv", ["sitemap-tazele.py", "--uygula"]):
                    with contextlib.redirect_stdout(io.StringIO()):
                        donus = modul.main()
        self.assertNotEqual(donus, 0)
        self.assertEqual((self.kok / "sitemap.xml").read_bytes(), once)
        self.assertEqual(list(self.kok.glob(".sitemap-tazele-*")), [])

    def test_lstat_reparse_attribute_path_fails_closed_without_writing(self):
        if not hasattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT"):
            self.skipTest("reparse bayragi bu platformda yok")
        self.sitemap_yaz({SITE + "tracked.html": "2001-01-01"})
        modul = self.modul_yukle()
        once = (self.kok / "sitemap.xml").read_bytes()

        class ReparseDurumu:
            st_mode = stat.S_IFREG
            st_file_attributes = stat.FILE_ATTRIBUTE_REPARSE_POINT

        with mock.patch.object(modul.os, "lstat", return_value=ReparseDurumu()):
            with mock.patch.object(modul.os.path, "realpath", side_effect=os.path.abspath):
                with mock.patch.object(
                        modul.sys, "argv", ["sitemap-tazele.py", "--uygula"]):
                    with contextlib.redirect_stdout(io.StringIO()):
                        donus = modul.main()
        self.assertNotEqual(donus, 0)
        self.assertEqual((self.kok / "sitemap.xml").read_bytes(), once)
        self.assertEqual(list(self.kok.glob(".sitemap-tazele-*")), [])

    def test_duplicate_or_casefold_alias_paths_fail_closed_without_writing(self):
        senaryolar = (
            ("duplicate", [
                (SITE + "tracked.html", "2001-01-01"),
                (SITE + "tracked.html", "2001-01-01"),
            ]),
            ("casefold alias", [
                (SITE + "tracked.html", "2001-01-01"),
                (SITE + "TRACKED.html", "2001-01-01"),
            ]),
        )
        for ad, kayitlar in senaryolar:
            with self.subTest(ad=ad):
                self.sitemap_yaz(kayitlar)
                once = (self.kok / "sitemap.xml").read_bytes()
                sonuc = self.araci_calistir("--uygula")
                self.assertNotEqual(sonuc.returncode, 0, sonuc.stdout + sonuc.stderr)
                self.assertEqual((self.kok / "sitemap.xml").read_bytes(), once)
                self.assertEqual(list(self.kok.glob(".sitemap-tazele-*")), [])

    def test_git_and_calendar_date_failures_leave_sitemap_unchanged(self):
        senaryolar = (
            ("status", 7, 0, "2024-02-03\n"),
            ("log", 0, 7, ""),
            ("empty date", 0, 0, ""),
            ("bad calendar date", 0, 0, "2024-02-30\n"),
        )
        for ad, durum_kodu, log_kodu, log_ciktisi in senaryolar:
            with self.subTest(ad=ad):
                modul = self.modul_yukle()
                once = (self.kok / "sitemap.xml").read_bytes()
                cagrilar = []

                def sahte_git(komut, **kwargs):
                    cagrilar.append(komut)
                    self.assertIsInstance(komut, list)
                    self.assertFalse(kwargs.get("shell", False))
                    if len(komut) > 1 and komut[1] == "status":
                        return subprocess.CompletedProcess(
                            komut, durum_kodu, stdout="", stderr="status fail")
                    if len(komut) > 1 and komut[1] == "log":
                        return subprocess.CompletedProcess(
                            komut, log_kodu, stdout=log_ciktisi, stderr="log fail")
                    self.fail("unexpected Git command: %r" % (komut,))

                with mock.patch.object(modul.subprocess, "run", side_effect=sahte_git):
                    with mock.patch.object(
                            modul.sys, "argv", ["sitemap-tazele.py", "--uygula"]):
                        with contextlib.redirect_stdout(io.StringIO()):
                            donus = modul.main()
                self.assertNotEqual(donus, 0)
                self.assertEqual((self.kok / "sitemap.xml").read_bytes(), once)
                self.assertEqual(list(self.kok.glob(".sitemap-tazele-*")), [])
                self.assertGreaterEqual(len(cagrilar), 1)

    def test_dirty_local_impossible_mtime_date_fails_closed_without_writing(self):
        self.sitemap_yaz({SITE + "tracked.html": "2001-01-01"})
        modul = self.modul_yukle()
        once = (self.kok / "sitemap.xml").read_bytes()
        beklenen_komut = [
            "git", "status", "--porcelain=v1", "-z", "--untracked-files=all",
            "--", "tracked.html",
        ]

        def sahte_git(komut):
            self.assertEqual(komut, beklenen_komut)
            return subprocess.CompletedProcess(
                komut, 0, stdout=" M tracked.html\0", stderr="")

        with mock.patch.object(modul, "git_calistir", side_effect=sahte_git):
            with mock.patch.object(modul.time, "strftime", return_value="2026-02-30"):
                with mock.patch.object(
                        modul.sys, "argv", ["sitemap-tazele.py", "--uygula"]):
                    with contextlib.redirect_stdout(io.StringIO()):
                        donus = modul.main()
        self.assertNotEqual(donus, 0)
        self.assertEqual((self.kok / "sitemap.xml").read_bytes(), once)
        self.assertEqual(list(self.kok.glob(".sitemap-tazele-*")), [])

    def test_dirty_local_stat_or_time_failure_fails_closed_without_writing(self):
        senaryolar = (
            ("stat", "getmtime", OSError("stat fail")),
            ("clock", "localtime", OverflowError("clock fail")),
        )
        beklenen_komut = [
            "git", "status", "--porcelain=v1", "-z", "--untracked-files=all",
            "--", "tracked.html",
        ]
        for ad, hedef, hata in senaryolar:
            with self.subTest(ad=ad):
                self.sitemap_yaz({SITE + "tracked.html": "2001-01-01"})
                modul = self.modul_yukle()
                once = (self.kok / "sitemap.xml").read_bytes()

                def sahte_git(komut):
                    self.assertEqual(komut, beklenen_komut)
                    return subprocess.CompletedProcess(
                        komut, 0, stdout=" M tracked.html\0", stderr="")

                yama = mock.patch.object(
                    modul.os.path if hedef == "getmtime" else modul.time,
                    hedef, side_effect=hata)
                with mock.patch.object(modul, "git_calistir", side_effect=sahte_git):
                    with yama:
                        with mock.patch.object(
                                modul.sys, "argv", ["sitemap-tazele.py", "--uygula"]):
                            with contextlib.redirect_stdout(io.StringIO()):
                                try:
                                    donus = modul.main()
                                except (OSError, OverflowError) as sizan:
                                    self.fail("yerel zaman hatasi sizdi: %s" % sizan)
                self.assertNotEqual(donus, 0)
                self.assertEqual((self.kok / "sitemap.xml").read_bytes(), once)
                self.assertEqual(list(self.kok.glob(".sitemap-tazele-*")), [])

    def test_missing_page_is_reported_without_inventing_a_date(self):
        eksik = SITE + "missing.html"
        self.sitemap_yaz({
            SITE + "tracked.html": "2001-01-01",
            eksik: "2001-01-01",
        })
        sonuc = self.araci_calistir("--uygula")
        self.assertEqual(sonuc.returncode, 0, sonuc.stdout + sonuc.stderr)
        self.assertIn("Diskte karsiligi bulunamayan 1 URL", sonuc.stdout)
        self.assertIn(eksik, sonuc.stdout)
        tarihler = self.sitemap_tarihleri()
        self.assertEqual(tarihler[SITE + "tracked.html"], "2024-02-03")
        self.assertEqual(tarihler[eksik], "2001-01-01")


if __name__ == "__main__":
    unittest.main()
