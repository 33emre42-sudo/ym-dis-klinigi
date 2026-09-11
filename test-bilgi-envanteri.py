"""Exercise the real site validator against a newly registered article."""
import json
import ast
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import stat

ROOT = Path(__file__).resolve().parent


def inventory_function():
    tree = ast.parse((ROOT / 'denetle.py').read_text(encoding='utf-8'))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                and n.name == 'bilgi_envanteri')
    namespace = {'os': os}
    exec(compile(ast.Module(body=[node], type_ignores=[]), 'inventory', 'exec'), namespace)
    return namespace['bilgi_envanteri']


def listing(names):
    entries = [{'@type': 'ListItem', 'position': i + 1, 'name': name,
                'url': 'https://ymdisklinigi.com/' + name}
               for i, name in enumerate(names)]
    return {'@type': 'CollectionPage',
            'url': 'https://ymdisklinigi.com/bilgi-yazilari.html',
            'mainEntity': {'@type': 'ItemList', 'numberOfItems': len(entries),
                           'itemListElement': entries}}


def document(data):
    links = ''.join('<a href="' + e['url'] + '">Article</a>'
                    for e in data['mainEntity']['itemListElement'])
    return '<html><head><script type="application/ld+json">' + json.dumps(data) + \
           '</script></head><body>' + links + '</body></html>'


class InventoryContract(unittest.TestCase):
    def collect(self, text):
        return inventory_function()(['aktif.html'], [], var_mi=lambda _: False,
                                    dizin_html=text)

    def test_registration_is_not_conditional_on_file_existence(self):
        self.assertEqual(['aktif.html', 'yeni.html'],
                         self.collect(document(listing(['aktif.html', 'yeni.html']))))

    def test_missing_active_registration_is_rejected(self):
        with self.assertRaises(ValueError):
            self.collect(document(listing(['yeni.html'])))

    def test_invalid_records_rejected(self):
        mutations = [
            lambda d: d['mainEntity'].update(numberOfItems=True),
            lambda d: d['mainEntity'].update(numberOfItems=7),
            lambda d: d['mainEntity']['itemListElement'][1].update(position=1),
            lambda d: d['mainEntity']['itemListElement'][1].update(position=True),
            lambda d: d['mainEntity']['itemListElement'][1].update(url='https://evil.example/yeni.html'),
            lambda d: d['mainEntity']['itemListElement'][1].update(url='https://ymdisklinigi.com/../yeni.html'),
            lambda d: d['mainEntity']['itemListElement'][1].update(url='https://ymdisklinigi.com/%79eni.html'),
            lambda d: d['mainEntity']['itemListElement'][1].update(url='https://ymdisklinigi.com/yeni.html?q=1'),
            lambda d: d['mainEntity']['itemListElement'][1].update(url='https://ymdisklinigi.com/index.html'),
            lambda d: d['mainEntity']['itemListElement'][1].update(url='https://ymdisklinigi.com/aktif.html'),
            lambda d: d.update(url='https://evil.example/bilgi-yazilari.html'),
        ]
        for mutation in mutations:
            data = listing(['aktif.html', 'yeni.html'])
            mutation(data)
            with self.subTest(data=data), self.assertRaises(ValueError):
                self.collect(document(data))

    def test_json_alone_is_not_a_directory_card(self):
        text = document(listing(['aktif.html', 'yeni.html']))
        text = text.replace('<a href="https://ymdisklinigi.com/yeni.html">Article</a>', '')
        with self.assertRaises(ValueError):
            self.collect(text)

    def test_ambiguous_or_broken_registry_rejected(self):
        text = document(listing(['aktif.html', 'yeni.html']))
        for bad in ('', text + text, text.replace('"numberOfItems": 2',
                '"numberOfItems": 2, "numberOfItems": 2'), text.replace('</script>', '')):
            with self.subTest(text=bad[:70]), self.assertRaises(ValueError):
                self.collect(bad)

    def test_nested_second_registry_rejected(self):
        text = document(listing(['aktif.html', 'yeni.html']))
        for extra in ({'@graph': [listing(['aktif.html'])]}, [listing(['aktif.html'])]):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                self.collect(text + '<script type="application/ld+json">' +
                             json.dumps(extra) + '</script>')

    def test_nonfinite_json_rejected(self):
        data = listing(['aktif.html', 'yeni.html'])
        data['mainEntity']['itemListElement'][1]['name'] = float('nan')
        with self.assertRaises(ValueError):
            self.collect(document(data))

    def test_reparse_or_nonregular_target_rejected_before_content_read(self):
        for mode, attributes in ((stat.S_IFLNK, 0), (stat.S_IFREG, 1024),
                                 (stat.S_IFDIR, 0)):
            with self.subTest(mode=mode, attributes=attributes), patch('os.lstat',
                    return_value=SimpleNamespace(st_mode=mode, st_file_attributes=attributes)), \
                    self.assertRaises(ValueError):
                self.collect(document(listing(['aktif.html', 'yeni.html'])))


class InventoryIntegration(unittest.TestCase):
    def test_unregistered_file_still_fails_inventory_gate(self):
        with tempfile.TemporaryDirectory(prefix='ym-content-unregistered-') as tmp:
            site = Path(tmp) / 'site'
            shutil.copytree(ROOT, site, ignore=shutil.ignore_patterns(
                '.git', '__pycache__', '.worktrees'))
            (site / 'test-kayitsiz.html').write_text('<html></html>', encoding='utf-8')
            result = subprocess.run([sys.executable, '-B', 'denetle.py'], cwd=site,
                capture_output=True, encoding='utf-8', errors='replace', timeout=90,
                env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
            self.assertNotEqual(0, result.returncode)
            self.assertRegex(result.stdout, r'HATA\s+denetlenmeyen HTML yok')

    def test_registered_new_article_enters_full_validation(self):
        with tempfile.TemporaryDirectory(prefix='ym-content-inventory-') as tmp:
            site = Path(tmp) / 'site'
            shutil.copytree(ROOT, site, ignore=shutil.ignore_patterns(
                '.git', '__pycache__', '.worktrees'))
            index = site / 'bilgi-yazilari.html'
            text = index.read_text(encoding='utf-8')
            pattern = r'(?s)(<script type="application/ld\+json">)(.*?)(</script>)'
            def register(match):
                data = json.loads(match[2])
                listing = data.get('mainEntity', {})
                if listing.get('@type') == 'ItemList':
                    listing['itemListElement'].append({
                        '@type': 'ListItem', 'position': 39, 'name': 'Test fixture',
                        'url': 'https://ymdisklinigi.com/test-yeni-yazi.html'})
                    listing['numberOfItems'] = 39
                    return match[1] + json.dumps(data, ensure_ascii=False) + match[3]
                return match[0]
            updated = re.sub(pattern, register, text).replace('</body>',
                '<a href="test-yeni-yazi.html">Test fixture</a></body>')
            index.write_text(updated, encoding='utf-8')
            # Deliberately invalid content must be INCLUDED and then rejected,
            # not accepted or merely left outside the medical article checks.
            (site / 'test-yeni-yazi.html').write_text(
                '<html><body>Test fixture</body></html>', encoding='utf-8')
            result = subprocess.run([sys.executable, '-B', 'denetle.py'], cwd=site,
                capture_output=True, encoding='utf-8', errors='replace', timeout=90,
                env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
            self.assertTrue('bilgi yazilari (39 sayfa)' in result.stdout,
                            'New registered article never entered full article validation')
            self.assertNotEqual(0, result.returncode)
            self.assertRegex(result.stdout, r'HATA\s+test-yeni-yazi.html')


if __name__ == '__main__':
    unittest.main()
