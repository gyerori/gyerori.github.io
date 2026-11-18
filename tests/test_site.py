from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
POST = 'posts/dasi-design/index.html'


class PublicationTests(unittest.TestCase):
    def build(self, directory):
        result = subprocess.run(
            [sys.executable, str(ROOT / 'scripts/build.py'), '--destination', str(directory)],
            cwd=ROOT, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_builds_only_the_approved_home_article_and_introduction(self):
        with tempfile.TemporaryDirectory(prefix='gyerori-test-') as directory:
            output = Path(directory)
            self.build(output)
            pages = ['index.html', POST, 'about/index.html']
            for name in pages:
                self.assertTrue((output / name).is_file(), name)
                text = (output / name).read_text()
                self.assertIn('lang="ko"', text)
                self.assertIn('gyerori', text)
                self.assertNotIn('noindex,nofollow', text)
                for private_marker in ['검토 원고', '아직 발행하지 않은', '디자인 검토', '가안입니다', '/Users/', 'file://']:
                    self.assertNotIn(private_marker, text)
            home = (output / 'index.html').read_text()
            article = (output / POST).read_text()
            about = (output / 'about/index.html').read_text()
            self.assertIn('href="/posts/dasi-design/"', home)
            self.assertIn('href="/about/"', home)
            self.assertIn('잘 모르겠다.', article)
            self.assertIn('다시 디자인을 잘하고 싶어졌다. 첫 글은 그 마음부터 남겨본다.', article)
            self.assertEqual(article.count('<h2 id="part-'), 4)
            self.assertIn('지금은 다시 프로덕트 디자이너로 일하고 있습니다.', about)
            self.assertIn('class="about-break"', about)
            self.assertEqual(len(list((output / 'posts').glob('*/index.html'))), 1)

    def test_search_and_feed_reference_only_published_urls(self):
        # Only parse XML generated locally by this trusted build, never external input.
        import xml.etree.ElementTree as ET
        with tempfile.TemporaryDirectory(prefix='gyerori-test-') as directory:
            output = Path(directory)
            self.build(output)
            self.assertTrue((output / 'sitemap.xml').is_file())
            self.assertTrue((output / 'feed.xml').is_file())
            sitemap = ET.parse(output / 'sitemap.xml')
            urls = [node.text for node in sitemap.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
            self.assertEqual(set(urls), {
                'https://gyerori.github.io/',
                'https://gyerori.github.io/about/',
                'https://gyerori.github.io/posts/dasi-design/',
            })
            feed = ET.parse(output / 'feed.xml')
            self.assertEqual(len(feed.findall('./channel/item')), 1)
            self.assertEqual(feed.findtext('./channel/item/link'), 'https://gyerori.github.io/posts/dasi-design/')
            self.assertIn('Sitemap: https://gyerori.github.io/sitemap.xml', (output / 'robots.txt').read_text())
            for name in ['index.html', POST, 'about/index.html']:
                text = (output / name).read_text()
                self.assertIn('rel="canonical"', text)
                self.assertIn('application/rss+xml', text)

    def test_not_found_page_links_back_to_home(self):
        with tempfile.TemporaryDirectory(prefix='gyerori-test-') as directory:
            output = Path(directory)
            self.build(output)
            self.assertTrue((output / '404.html').is_file())
            page = (output / '404.html').read_text()
            self.assertIn('페이지를 찾을 수 없습니다', page)
            self.assertIn('href="/"', page)
            self.assertIn('name="robots" content="noindex"', page)


if __name__ == '__main__':
    unittest.main()
