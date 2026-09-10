#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""guncelleme-tarihi-tazele.py davranis testleri."""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock


KOK = Path(__file__).resolve().parent
KAYNAK = KOK / "guncelleme-tarihi-tazele.py"


def komut(args, cwd, env=None):
    sonuc = subprocess.run(args, cwd=str(cwd), env=env, capture_output=True,
                           text=True, encoding="utf-8", errors="replace")
    if sonuc.returncode != 0:
        raise RuntimeError("komut basarisiz: %r\n%s\n%s" %
                           (args, sonuc.stdout, sonuc.stderr))


def tarih_mtime(yol, yil, ay, gun):
    an = time.mktime((yil, ay, gun, 12, 0, 0, 0, 0, -1))
    os.utime(yol, (an, an))


def yukle(repo):
    ad = "guncelleme_tarihi_test_%d" % time.time_ns()
    spec = importlib.util.spec_from_file_location(ad, KAYNAK)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    modul.KOK = str(repo)
    return modul


class GuncellemeTarihiTesti(unittest.TestCase):
    def repo_olustur(self, footer_tarihi="1 Ağustos 2026",
                     commit_tarihi="2026-08-01T12:00:00+03:00"):
        gecici = tempfile.TemporaryDirectory(prefix="tarih-tazele-")
        self.addCleanup(gecici.cleanup)
        repo = Path(gecici.name)
        komut(["git", "init", "-q"], repo)
        komut(["git", "config", "user.email", "test@example.invalid"], repo)
        komut(["git", "config", "user.name", "Tarih Testi"], repo)
        index = repo / "index.html"
        index.write_text(
            "<!doctype html><body><footer><p>Son güncelleme: "
            "%s</p></footer></body>\n" % footer_tarihi, encoding="utf-8")
        (repo / "temiz.html").write_text("<p>temiz</p>\n", encoding="utf-8")
        komut(["git", "add", "index.html", "temiz.html"], repo)
        cevre = os.environ.copy()
        cevre["GIT_AUTHOR_DATE"] = commit_tarihi
        cevre["GIT_COMMITTER_DATE"] = commit_tarihi
        komut(["git", "commit", "-q", "-m", "ilk html"], repo, cevre)
        return repo, index

    def calistir(self, modul, uygula=False):
        onceki_argv = list(sys.argv)
        cikti = io.StringIO()
        try:
            modul.sys.argv = [str(KAYNAK)] + (["--uygula"] if uygula else [])
            with contextlib.redirect_stdout(cikti):
                kod = modul.main()
        finally:
            modul.sys.argv = onceki_argv
        return kod, cikti.getvalue()

    def sahte_git_ile_calistir(self, repo, durum, git_ciktisi="2026-08-01\n",
                               git_kodu=0):
        modul = yukle(repo)
        gercek_cagir = modul.subprocess.run
        cagrilar = []

        def sahte_cagir(args, **kwargs):
            cagrilar.append(tuple(args))
            if args[1] == "log":
                return subprocess.CompletedProcess(
                    args, git_kodu, stdout=git_ciktisi, stderr="")
            if args[1] == "status":
                return subprocess.CompletedProcess(
                    args, 0, stdout=durum, stderr=b"")
            return gercek_cagir(args, **kwargs)

        with mock.patch.object(modul.subprocess, "run", side_effect=sahte_cagir):
            sonuc = self.calistir(modul, uygula=True)
        return sonuc + (cagrilar,)

    def test_staged_html_mtime_is_canonical_date(self):
        repo, index = self.repo_olustur()
        aday = repo / "yeni-yazi.html"
        aday.write_text("<p>aday</p>\n", encoding="utf-8")
        komut(["git", "add", "yeni-yazi.html"], repo)
        tarih_mtime(aday, 2026, 8, 3)

        kod, _ = self.calistir(yukle(repo), uygula=True)

        self.assertEqual(kod, 0)
        self.assertIn("Son güncelleme: 3 Ağustos 2026",
                      index.read_text(encoding="utf-8"))

    def test_clean_checkout_mtime_does_not_override_git_date(self):
        repo, index = self.repo_olustur(footer_tarihi="31 Temmuz 2026")
        tarih_mtime(index, 2026, 8, 20)

        kod, _ = self.calistir(yukle(repo), uygula=True)

        self.assertEqual(kod, 0)
        self.assertIn("Son güncelleme: 1 Ağustos 2026",
                      index.read_text(encoding="utf-8"))

    def test_unstaged_html_mtime_is_canonical_date(self):
        repo, index = self.repo_olustur()
        aday = repo / "temiz.html"
        aday.write_text("<p>degisti</p>\n", encoding="utf-8")
        tarih_mtime(aday, 2026, 8, 4)

        kod, _ = self.calistir(yukle(repo), uygula=True)

        self.assertEqual(kod, 0)
        self.assertIn("Son güncelleme: 4 Ağustos 2026",
                      index.read_text(encoding="utf-8"))

    def test_untracked_html_mtime_is_canonical_date(self):
        repo, index = self.repo_olustur()
        aday = repo / "bagimsiz-yeni.html"
        aday.write_text("<p>yeni</p>\n", encoding="utf-8")
        tarih_mtime(aday, 2026, 8, 5)

        kod, _ = self.calistir(yukle(repo), uygula=True)

        self.assertEqual(kod, 0)
        self.assertIn("Son güncelleme: 5 Ağustos 2026",
                      index.read_text(encoding="utf-8"))

    def test_newer_commit_date_never_moves_backward_for_dirty_html(self):
        repo, index = self.repo_olustur(
            footer_tarihi="31 Temmuz 2026",
            commit_tarihi="2026-08-06T12:00:00+03:00")
        aday = repo / "temiz.html"
        aday.write_text("<p>degisti</p>\n", encoding="utf-8")
        tarih_mtime(aday, 2026, 8, 3)

        kod, _ = self.calistir(yukle(repo), uygula=True)

        self.assertEqual(kod, 0)
        self.assertIn("Son güncelleme: 6 Ağustos 2026",
                      index.read_text(encoding="utf-8"))

    def test_deleted_html_history_does_not_date_clean_tracked_site(self):
        repo, index = self.repo_olustur(footer_tarihi="31 Temmuz 2026")
        komut(["git", "rm", "-q", "temiz.html"], repo)
        cevre = os.environ.copy()
        cevre["GIT_AUTHOR_DATE"] = "2026-08-10T12:00:00+03:00"
        cevre["GIT_COMMITTER_DATE"] = "2026-08-10T12:00:00+03:00"
        komut(["git", "commit", "-q", "-m", "silinen html"], repo, cevre)

        kod, _ = self.calistir(yukle(repo), uygula=True)

        self.assertEqual(kod, 0)
        self.assertIn("Son güncelleme: 1 Ağustos 2026",
                      index.read_text(encoding="utf-8"))

    def test_ambiguous_status_records_fail_closed_without_writing(self):
        durumlar = [
            ("malformed", b"M index.html\0"),
            ("trailing-nul-yok", b"?? aday.html"),
            ("delete", b" D temiz.html\0"),
            ("rename", b"R  yeni.html\0eski.html\0"),
            ("conflict", b"UU temiz.html\0"),
            ("dot-path", b"?? ./aday.html\0"),
            ("backslash", b"?? alt\\aday.html\0"),
            ("non-ascii", "?? ç.html\0".encode("utf-8")),
            ("casefold", b"?? aday.html\0?? ADAY.html\0"),
        ]
        for ad, durum in durumlar:
            with self.subTest(ad=ad):
                repo, index = self.repo_olustur(footer_tarihi="31 Temmuz 2026")
                (repo / "aday.html").write_text("<p>aday</p>\n", encoding="utf-8")
                (repo / "alt").mkdir()
                (repo / "alt" / "aday.html").write_text("<p>aday</p>\n",
                                                            encoding="utf-8")
                (repo / "ç.html").write_text("<p>aday</p>\n", encoding="utf-8")
                once = index.read_bytes()

                kod, _, cagrilar = self.sahte_git_ile_calistir(repo, durum)

                self.assertNotEqual(kod, 0)
                self.assertEqual(index.read_bytes(), once)
                durum_cagrisi = [c for c in cagrilar if c[1] == "status"]
                self.assertEqual(len(durum_cagrisi), 1)
                self.assertIn("-z", durum_cagrisi[0])

    def test_bad_git_dates_fail_closed_without_writing(self):
        durumlar = [
            ("nonzero", "", 7),
            ("empty", "", 0),
            ("surrounded-by-whitespace", "\n2026-08-01\n", 0),
            ("not-a-date", "2026-08-xx\n", 0),
            ("invalid-calendar-date", "2026-02-30\n", 0),
        ]
        for ad, git_ciktisi, git_kodu in durumlar:
            with self.subTest(ad=ad):
                repo, index = self.repo_olustur(footer_tarihi="31 Temmuz 2026")
                once = index.read_bytes()

                kod, _cikti, _ = self.sahte_git_ile_calistir(
                    repo, b"", git_ciktisi, git_kodu)

                self.assertNotEqual(kod, 0)
                self.assertEqual(index.read_bytes(), once)


    def test_casefold_equivalent_dirty_path_to_tracked_html_fails_closed(self):
        repo, index = self.repo_olustur(footer_tarihi="31 Temmuz 2026")
        (repo / "TEMIZ.html").write_text("<p>aday</p>\n", encoding="utf-8")
        once = index.read_bytes()

        kod, _, _ = self.sahte_git_ile_calistir(repo, b"?? TEMIZ.html\0")

        self.assertNotEqual(kod, 0)
        self.assertEqual(index.read_bytes(), once)

    def test_dirty_html_metadata_failure_leaves_index_unchanged(self):
        repo, index = self.repo_olustur(footer_tarihi="31 Temmuz 2026")
        aday = repo / "aday.html"
        aday.write_text("<p>aday</p>\n", encoding="utf-8")
        once = index.read_bytes()
        modul = yukle(repo)
        gercek_lstat = modul.os.lstat
        hedef = os.path.normcase(os.path.abspath(aday))

        def lstat_hatasi(yol):
            if os.path.normcase(os.path.abspath(yol)) == hedef:
                raise OSError("sahte lstat hatasi")
            return gercek_lstat(yol)

        with mock.patch.object(modul.os, "lstat", side_effect=lstat_hatasi):
            kod, _ = self.calistir(modul, uygula=True)

        self.assertNotEqual(kod, 0)
        self.assertEqual(index.read_bytes(), once)

    def test_dirty_html_reparse_point_leaves_index_unchanged(self):
        repo, index = self.repo_olustur(footer_tarihi="31 Temmuz 2026")
        aday = repo / "aday.html"
        aday.write_text("<p>aday</p>\n", encoding="utf-8")
        once = index.read_bytes()
        modul = yukle(repo)
        gercek_lstat = modul.os.lstat
        bilgi = gercek_lstat(aday)
        hedef = os.path.normcase(os.path.abspath(aday))

        class ReparseNoktasi:
            st_mode = bilgi.st_mode
            st_mtime = bilgi.st_mtime
            st_file_attributes = 0x400

        def reparse_lstat(yol):
            if os.path.normcase(os.path.abspath(yol)) == hedef:
                return ReparseNoktasi()
            return gercek_lstat(yol)

        with mock.patch.object(modul.os, "lstat", side_effect=reparse_lstat):
            kod, _ = self.calistir(modul, uygula=True)

        self.assertNotEqual(kod, 0)
        self.assertEqual(index.read_bytes(), once)

    def test_atomic_write_failures_leave_original_and_only_sentinel_temp(self):
        for ad in ("short-write", "write-error", "replace-error"):
            with self.subTest(ad=ad):
                repo, index = self.repo_olustur(footer_tarihi="31 Temmuz 2026")
                once = index.read_bytes()
                sentinel = repo / ".guncelleme-tarihi-baska.tmp"
                sentinel.write_bytes(b"dokunma")
                modul = yukle(repo)

                def kisa_yaz(dosya, veri):
                    dosya.write(veri[:-1])
                    return len(veri) - 1

                with contextlib.ExitStack() as yigin:
                    if ad == "short-write":
                        yigin.enter_context(mock.patch.object(
                            modul, "_tam_yaz", side_effect=kisa_yaz,
                            create=True))
                    elif ad == "write-error":
                        yigin.enter_context(mock.patch.object(
                            modul, "_tam_yaz", side_effect=OSError("sahte yazma"),
                            create=True))
                    else:
                        yigin.enter_context(mock.patch.object(
                            modul.os, "replace", side_effect=OSError("sahte replace")))
                    kod, _ = self.calistir(modul, uygula=True)

                self.assertNotEqual(kod, 0)
                self.assertEqual(index.read_bytes(), once)
                self.assertEqual(sentinel.read_bytes(), b"dokunma")
                self.assertEqual(
                    sorted(p.name for p in repo.glob(".guncelleme-tarihi-*.tmp")),
                    [sentinel.name])

    def test_atomic_fsync_failure_leaves_original_without_temp_residue(self):
        repo, index = self.repo_olustur(footer_tarihi="31 Temmuz 2026")
        once = index.read_bytes()
        modul = yukle(repo)
        with mock.patch.object(modul.os, "fsync", side_effect=OSError("sahte fsync")), \
                mock.patch.object(modul.os, "replace") as replace:
            kod, cikti = self.calistir(modul, uygula=True)

        self.assertNotEqual(kod, 0)
        self.assertNotIn("YAZILDI", cikti)
        self.assertEqual(index.read_bytes(), once)
        self.assertEqual(replace.call_count, 0)
        self.assertEqual(list(repo.glob(".guncelleme-tarihi-*.tmp")), [])

    def test_atomic_cleanup_failure_is_explicit_hold(self):
        repo, index = self.repo_olustur(footer_tarihi="31 Temmuz 2026")
        once = index.read_bytes()
        modul = yukle(repo)
        gercek_unlink = modul.os.unlink
        kalintilar = []

        def unlink_hatasi(yol, *args, **kwargs):
            if Path(yol).name.startswith(".guncelleme-tarihi-"):
                kalintilar.append(Path(yol))
                raise OSError("sahte temizleme")
            return gercek_unlink(yol, *args, **kwargs)

        try:
            with mock.patch.object(
                    modul, "_tam_yaz", side_effect=OSError("sahte yazma")), \
                    mock.patch.object(modul.os, "unlink", side_effect=unlink_hatasi):
                kod, cikti = self.calistir(modul, uygula=True)

            self.assertNotEqual(kod, 0)
            self.assertNotIn("YAZILDI", cikti)
            self.assertIn("temizleme basarisiz", cikti)
            self.assertEqual(index.read_bytes(), once)
            self.assertEqual(len(kalintilar), 1)
            self.assertTrue(kalintilar[0].is_file())
        finally:
            for kalinti in kalintilar:
                if kalinti.exists():
                    gercek_unlink(kalinti)

    def test_atomic_write_fsyncs_and_replaces_from_index_directory(self):
        repo, index = self.repo_olustur(footer_tarihi="31 Temmuz 2026")
        modul = yukle(repo)
        gercek_replace = modul.os.replace
        cagrilar = []

        def replace_izle(kaynak, hedef):
            cagrilar.append((Path(kaynak), Path(hedef)))
            return gercek_replace(kaynak, hedef)

        with mock.patch.object(modul.os, "replace", side_effect=replace_izle), \
                mock.patch.object(modul.os, "fsync", wraps=modul.os.fsync) as fsync:
            kod, _ = self.calistir(modul, uygula=True)

        self.assertEqual(kod, 0)
        self.assertEqual(len(cagrilar), 1)
        self.assertEqual(os.path.normcase(str(cagrilar[0][0].parent)),
                         os.path.normcase(str(repo)))
        self.assertEqual(os.path.normcase(str(cagrilar[0][1])),
                         os.path.normcase(str(index)))
        self.assertGreaterEqual(fsync.call_count, 1)
        self.assertIn("Son güncelleme: 1 Ağustos 2026",
                      index.read_text(encoding="utf-8"))

    def test_footer_replacement_changes_only_footer_marker(self):
        repo, index = self.repo_olustur()
        once = (
            b"once Son guncelleme: 99 Ocak 2000\r\n"
            b"<footer><p>Son g\xc3\xbcncelleme: 31 Temmuz 2026</p></footer>\r\n"
            b"sonra\r\n")
        index.write_bytes(once)
        tarih_mtime(index, 2026, 8, 1)

        kod, _ = self.calistir(yukle(repo), uygula=True)

        beklenen = once.replace(
            "31 Temmuz 2026".encode("utf-8"),
            "1 Ağustos 2026".encode("utf-8"), 1)
        self.assertEqual(kod, 0)
        self.assertEqual(index.read_bytes(), beklenen)

    def test_footer_contract_failures_never_write(self):
        icerikler = [
            b"<body><p>Son g\xc3\xbcncelleme: 31 Temmuz 2026</p></body>\n",
            (b"<footer>Son g\xc3\xbcncelleme: 31 Temmuz 2026</footer>"
             b"<footer>Son g\xc3\xbcncelleme: 31 Temmuz 2026</footer>\n"),
            (b"<footer>Son g\xc3\xbcncelleme: 31 Temmuz 2026; "
             b"Son g\xc3\xbcncelleme: 30 Temmuz 2026</footer>\n"),
        ]
        for icerik in icerikler:
            with self.subTest(icerik=icerik):
                repo, index = self.repo_olustur()
                index.write_bytes(icerik)
                once = index.read_bytes()

                kod, _ = self.calistir(yukle(repo), uygula=True)

                self.assertNotEqual(kod, 0)
                self.assertEqual(index.read_bytes(), once)

    def test_second_apply_is_byte_idempotent(self):
        repo, index = self.repo_olustur(footer_tarihi="31 Temmuz 2026")
        modul = yukle(repo)

        ilk_kod, _ = self.calistir(modul, uygula=True)
        ilk_bayt = index.read_bytes()
        ikinci_kod, _ = self.calistir(modul, uygula=True)

        self.assertEqual(ilk_kod, 0)
        self.assertEqual(ikinci_kod, 0)
        self.assertEqual(index.read_bytes(), ilk_bayt)


if __name__ == "__main__":
    unittest.main(verbosity=2)
