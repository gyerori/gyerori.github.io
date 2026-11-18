"""Build the public gyerori blog from approved content only."""
from argparse import ArgumentParser
from datetime import date
from html import escape, unescape
from pathlib import Path
from string import Template
import json
import re
import shutil

import markdown

ROOT = Path(__file__).resolve().parents[1]


def read_posts():
    posts = []
    for path in sorted((ROOT / 'content/posts').glob('*.md')):
        source = path.read_text(encoding='utf-8')
        if not source.startswith('---\n'):
            raise ValueError(f'Missing front matter: {path.name}')
        front, body = source[4:].split('\n---\n', 1)
        metadata = {}
        for line in front.splitlines():
            key, value = line.split(':', 1)
            metadata[key.strip()] = json.loads(value.strip())
        if metadata.get('published') is not True:
            continue
        slug = metadata['slug']
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', slug):
            raise ValueError(f'Invalid post slug: {slug}')
        date.fromisoformat(metadata['date'])
        rendered = markdown.markdown(body.strip(), extensions=['extra'])
        headings = re.findall(r'<h2>(.*?)</h2>', rendered)
        for index, heading in enumerate(headings):
            rendered = rendered.replace(f'<h2>{heading}</h2>', f'<h2 id="part-{index}">{heading}</h2>', 1)
        metadata.update(body=rendered, headings=headings, url=f'/posts/{slug}/')
        posts.append(metadata)
    slugs = [post['slug'] for post in posts]
    if len(slugs) != len(set(slugs)):
        raise ValueError('Duplicate post slug')
    return sorted(posts, key=lambda post: (post['date'], post['slug']), reverse=True)


def plain(text):
    return unescape(re.sub(r'<[^>]+>', '', text))


def render_page(site, title, description, url, content, section, extra_head='', og_type='website'):
    sidebar = (ROOT / 'templates/sidebar.html').read_text(encoding='utf-8')
    if section in ('home', 'about'):
        sidebar = sidebar.replace(f'data-nav="{section}"', f'data-nav="{section}" aria-current="page"')
    values = {
        'title': escape(title, quote=True),
        'description': escape(description, quote=True),
        'canonical': escape(site['url'].rstrip('/') + url, quote=True),
        'og_type': og_type,
        'extra_head': '<link rel="alternate" type="application/rss+xml" title="gyerori" href="/feed.xml">' + extra_head,
        'sidebar': sidebar,
        'content': content,
        'footer': (ROOT / 'templates/footer.html').read_text(encoding='utf-8'),
    }
    template = Template((ROOT / 'templates/layout.html').read_text(encoding='utf-8'))
    return template.substitute(values)


def build(destination):
    destination.mkdir(parents=True, exist_ok=True)
    marker = destination / '.gyerori-generated'
    if any(destination.iterdir()):
        if not marker.is_file():
            raise ValueError('Refusing to overwrite a non-generated output directory')
        for child in destination.iterdir():
            if child.is_dir() and not child.is_symlink():
                shutil.rmtree(child)
            else:
                child.unlink()
    marker.write_text('Generated website output\n', encoding='utf-8')
    site = json.loads((ROOT / 'site.json').read_text(encoding='utf-8'))
    posts = read_posts()
    if not posts:
        raise ValueError('No approved posts to publish')

    def output(path, content):
        target = destination / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')

    features = []
    for post in posts:
        title = escape(post['title'])
        display_title = title.replace('다시 디자인을 ', '다시 디자인을<br class="desktop-break">', 1)
        paragraphs = re.findall(r'<p>.*?</p>', post['body'], re.S)[:3]
        label = escape(post.get('label', post['date']))
        features.append(
            '<article class="feature"><div class="feature-text">'
            f'<p class="feature-kicker">{label}</p>'
            f'<h1 class="post-title"><a href="{post["url"]}">{display_title}</a></h1>'
            '<div class="feature-excerpt">' + ''.join(paragraphs) + '</div>'
            f'<a href="{post["url"]}" class="read-link">첫 글 읽기</a></div></article>'
        )
        toc_items = ''.join(
            f'<li><a href="#part-{index}">{heading}</a></li>'
            for index, heading in enumerate(post['headings'])
        )
        toc = f'<details class="toc"><summary>이 글의 목차</summary><ul>{toc_items}</ul></details>'
        article_title = title.replace('다시 디자인을 ', '다시 디자인을<br>', 1)
        article = (
            '<section id="article" class="view reading" aria-label="첫 글">'
            '<a href="/" class="back">글 목록으로 돌아가기</a>'
            f'<p class="feature-kicker">{label}</p><h1 class="post-title">{article_title}</h1>'
            f'<div class="byline"><span>{escape(site["name"])}</span>'
            f'<time datetime="{post["date"]}">{post["date"].replace("-", ".")}</time></div>'
            f'{toc}<div class="article-body">{post["body"]}</div>'
            '<div class="article-end">gyerori의 첫 번째 기록입니다.<br>'
            '<a href="/" class="back">글 목록으로 돌아가기</a></div></section>'
        )
        schema = {
            '@context': 'https://schema.org', '@type': 'BlogPosting',
            'headline': post['title'], 'datePublished': post['date'],
            'author': {'@type': 'Person', 'name': site['name'], 'url': site['url'] + '/about/'},
            'mainEntityOfPage': site['url'] + post['url'], 'inLanguage': 'ko',
        }
        extra = '<script type="application/ld+json">' + json.dumps(schema, ensure_ascii=False).replace('<', '\\u003c') + '</script>'
        output('posts/' + post['slug'] + '/index.html', render_page(
            site, post['title'] + ' | ' + site['name'], plain(post['body'])[:150],
            post['url'], article, 'article', extra, 'article',
        ))
    home = '<section id="home" class="view home" aria-label="글 목록">' + ''.join(features) + '</section>'
    output('index.html', render_page(site, site['name'], site['description'], '/', home, 'home'))
    about = '<section id="about" class="view about-view" aria-label="소개">' + (ROOT / 'content/about.html').read_text(encoding='utf-8') + '</section>'
    output('about/index.html', render_page(site, '소개 | ' + site['name'], site['description'], '/about/', about, 'about'))
    not_found = '<section class="about-view"><h1>페이지를 찾을 수 없습니다.</h1><p>주소가 바뀌었거나 없는 페이지입니다.</p><a class="read-link" href="/">글 목록으로 돌아가기</a></section>'
    output('404.html', render_page(site, '페이지를 찾을 수 없습니다 | ' + site['name'], site['description'], '/404.html', not_found, '', '<meta name="robots" content="noindex">'))
    shutil.copytree(ROOT / 'assets', destination / 'assets')
    output('.nojekyll', '')
    urls = ['/', '/about/'] + [post['url'] for post in posts]
    sitemap = '<?xml version="1.0" encoding="utf-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    sitemap += ''.join('<url><loc>' + escape(site['url'] + url) + '</loc></url>' for url in urls)
    output('sitemap.xml', sitemap + '</urlset>\n')
    output('robots.txt', 'User-agent: *\nAllow: /\nSitemap: ' + site['url'] + '/sitemap.xml\n')
    feed = '<?xml version="1.0" encoding="utf-8"?>\n<rss version="2.0"><channel>'
    feed += '<title>' + escape(site['name']) + '</title><link>' + escape(site['url']) + '/</link>'
    feed += '<description>' + escape(site['description']) + '</description><language>ko</language>'
    for post in posts:
        link = escape(site['url'] + post['url'])
        feed += '<item><title>' + escape(post['title']) + '</title><link>' + link + '</link>'
        feed += '<guid isPermaLink="true">' + link + '</guid><description>' + escape(plain(post['body'])[:200]) + '</description></item>'
    output('feed.xml', feed + '</channel></rss>\n')
    return len(posts)


if __name__ == '__main__':
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, default=ROOT / '_site')
    arguments = parser.parse_args()
    count = build(arguments.destination.resolve())
    print(f'Built {count} approved post(s)')
