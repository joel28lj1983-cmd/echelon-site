"""Validate the static production site with Python's standard library."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
import json
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://echelonadvisorygroup.org'

class Page(HTMLParser):
    def __init__(self, path):
        super().__init__(convert_charrefs=True)
        self.path, self.links, self.ids, self.canonical = path, [], [], []
        self.h1 = self.main = self.title = 0
        self.schema = []
        self.metadata = {}
        self.lang = None
        self.in_schema = False
        self.feed(path.read_text(encoding='utf-8'))

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'html': self.lang = a.get('lang')
        if tag == 'meta':
            key = a.get('name', a.get('property', 'charset'))
            self.metadata.setdefault(key, []).append(a.get('content', a.get('charset', '')))
        if 'id' in a:
            self.ids.append(a['id'])
        for key in ('href', 'src'):
            if key in a:
                self.links.append(a[key])
        if tag == 'h1': self.h1 += 1
        if tag == 'main': self.main += 1
        if tag == 'title': self.title += 1
        if tag == 'link' and a.get('rel') == 'canonical': self.canonical.append(a['href'])
        if tag == 'script' and a.get('type') == 'application/ld+json': self.in_schema = True

    def handle_endtag(self, tag):
        if tag == 'script': self.in_schema = False

    def handle_data(self, data):
        if self.in_schema: self.schema.append(json.loads(data))

def validate():
    pages = {p.resolve(): Page(p) for p in ROOT.rglob('*.html') if not any(x.startswith('.') for x in p.relative_to(ROOT).parts)}
    errors = []
    public_files = {p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and not any(x.startswith('.') for x in p.relative_to(ROOT).parts)}
    forbidden = re.compile(r'\b(?:AI|agents?|automation|Command Center|Claude|Codex|Grok|unlock value|maximize potential|transform your business|actionable insights|revenue recovery ecosystem|innovative solutions|cutting-edge|leverage technology|game-changing|trusted partner)\b', re.I)
    for path, page in pages.items():
        relative = path.relative_to(ROOT).as_posix()
        raw = path.read_text(encoding='utf-8')
        if forbidden.search(raw): errors.append(f'{relative}: prohibited public wording')
        if page.lang != 'en': errors.append(f'{relative}: missing language')
        for key in ('charset', 'viewport', 'description'):
            if len(page.metadata.get(key, [])) != 1 or not page.metadata[key][0]: errors.append(f'{relative}: missing/duplicate {key}')
        if (page.h1, page.main, page.title) != (1, 1, 1): errors.append(f'{relative}: heading/main/title count')
        if len(page.ids) != len(set(page.ids)): errors.append(f'{relative}: duplicate IDs')
        if relative != '404.html':
            expected = BASE + '/' + relative.removesuffix('index.html')
            if page.canonical != [expected]: errors.append(f'{relative}: incorrect canonical')
            if page.metadata.get('og:url') != [expected]: errors.append(f'{relative}: incorrect social URL')
            for key in ('og:type', 'og:title', 'og:description', 'og:image', 'og:image:alt', 'twitter:card'):
                if len(page.metadata.get(key, [])) != 1 or not page.metadata[key][0]: errors.append(f'{relative}: missing/duplicate {key}')
            image_url = page.metadata.get('og:image', [''])[0]
            if image_url != BASE + '/assets/og-card.png': errors.append(f'{relative}: incorrect social image')
        elif page.metadata.get('robots') != ['noindex,follow']:
            errors.append('404 must be excluded from indexing')
        for schema in page.schema:
            if schema.get('@context') != 'https://schema.org' or not schema.get('@type'): errors.append(f'{relative}: invalid schema identity')
            if schema.get('@type') == 'Article':
                if schema.get('mainEntityOfPage') != page.canonical[0] or not all(schema.get(k) for k in ('headline', 'author', 'publisher', 'datePublished', 'dateModified')): errors.append(f'{relative}: incomplete article schema')
            if schema.get('@type') == 'Service' and not all(schema.get(k) for k in ('name', 'provider', 'serviceType')): errors.append(f'{relative}: incomplete service schema')
        for link in page.links:
            url = urlsplit(link)
            if url.scheme or url.netloc: continue
            target = ROOT / unquote(url.path.lstrip('/')) if url.path.startswith('/') else path.parent / unquote(url.path) if url.path else path
            if target.is_dir(): target /= 'index.html'
            target = target.resolve()
            if not target.exists(): errors.append(f'{relative}: missing {link}')
            elif target.relative_to(ROOT).as_posix() not in public_files: errors.append(f'{relative}: wrong-case or excluded asset {link}')
            elif url.fragment and target in pages and url.fragment not in pages[target].ids: errors.append(f'{relative}: missing anchor {link}')
        if '\ufffd' in path.read_text(encoding='utf-8'): errors.append(f'{relative}: replacement character')
    sitemap = ET.parse(ROOT / 'sitemap.xml')
    locations = {e.text for e in sitemap.findall('.//{*}loc')}
    expected = {p.canonical[0] for p in pages.values() if p.canonical}
    if locations != expected: errors.append('Sitemap and canonical pages differ')
    if (ROOT / 'CNAME').read_text().strip() != 'echelonadvisorygroup.org': errors.append('Incorrect Pages custom domain')
    if not (ROOT / '.nojekyll').exists(): errors.append('Missing .nojekyll')
    if f'Sitemap: {BASE}/sitemap.xml' not in (ROOT / 'robots.txt').read_text(): errors.append('Missing sitemap discovery')
    ET.parse(ROOT / 'favicon.svg')
    card = (ROOT / 'assets/og-card.png').read_bytes()
    if card[:8] != b'\x89PNG\r\n\x1a\n' or (int.from_bytes(card[16:20]), int.from_bytes(card[20:24])) != (1200, 630): errors.append('Invalid social card format/dimensions')
    assert not errors, '\n'.join(errors)
    print(f'PASS: {len(pages)} HTML pages; links, case-sensitive assets, anchors, landmarks, metadata, canonical URLs, JSON-LD, UTF-8, sitemap, brand wording, GitHub Pages files, SVG and social card.')

if __name__ == '__main__': validate()
