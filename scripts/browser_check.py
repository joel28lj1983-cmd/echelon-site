"""Browser smoke checks using a workspace-local Playwright install and Edge."""
from pathlib import Path
import functools
import http.server
import json
import sys
import threading
from urllib.parse import urlsplit, parse_qs

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.qa-deps'))
from playwright.sync_api import sync_playwright

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args): pass
    def send_error(self, code, message=None, explain=None):
        if code == 404:
            body = (ROOT / '404.html').read_bytes()
            self.send_response(404)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            if self.command != 'HEAD': self.wfile.write(body)
        else:
            super().send_error(code, message, explain)

server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(ROOT)))
threading.Thread(target=server.serve_forever, daemon=True).start()
output = ROOT / '.qa-output'
output.mkdir(exist_ok=True)
paths = ['/' + p.relative_to(ROOT).as_posix().removesuffix('index.html') for p in ROOT.rglob('*.html') if not any(x.startswith('.') for x in p.relative_to(ROOT).parts)]
checks, errors, accessibility = [], [], []
axe_path = output / 'axe.min.js'
assert axe_path.exists(), 'Download axe-core 4.10.3 to .qa-output/axe.min.js before the full browser audit.'
try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel='msedge', headless=True)
        for width in (320, 390, 768, 1024, 1440):
            page = browser.new_page(viewport={'width': width, 'height': 1000}, device_scale_factor=1)
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('response', lambda response: errors.append(f'HTTP {response.status}: {response.url}') if response.status >= 400 else None)
            for route in paths:
                page.goto(f'http://127.0.0.1:{server.server_port}{route}')
                page.wait_for_load_state('networkidle')
                overflow = page.evaluate('document.documentElement.scrollWidth > innerWidth')
                assert not overflow, f'Horizontal overflow: {route} at {width}'
                assert page.locator('nav a:visible').count() == 6, f'Navigation hidden: {route} at {width}'
                assert page.locator('h1').is_visible()
                assert page.locator('body > main').count() == 1
                assert page.locator('a:not([href])').count() == 0
                if width in (390, 1440):
                    page.add_script_tag(path=str(axe_path))
                    audit = page.evaluate('''async () => {
                        const result = await axe.run(document, {runOnly: {type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa', 'best-practice']}});
                        return {violations: result.violations, incomplete: result.incomplete};
                    }''')
                    accessibility.append({'route': route, 'width': width, **audit})
                    for violation in audit['violations']:
                        errors.append(f"{route} at {width}: {violation['id']} — " + ', '.join(str(n['target']) for n in violation['nodes']))
                    name = route.strip('/').replace('/', '-') or 'home'
                    page.screenshot(path=str(output / f'{name}-{width}.png'), full_page=True)
                checks.append({'route': route, 'width': width, 'passed': True})
            page.goto(f'http://127.0.0.1:{server.server_port}/')
            page.keyboard.press('Tab')
            assert page.locator('.skip').evaluate('(el) => el === document.activeElement')
            page.keyboard.press('Enter')
            assert page.evaluate('location.hash') == '#main'
            page.locator('summary').first.click()
            assert page.locator('details').first.get_attribute('open') is not None
            page.locator('nav a').first.click()
            assert page.url.endswith('/project-review/')
            page.locator('nav .navcta').click()
            assert page.url.endswith('/contact/')
            mail = urlsplit(page.locator('a.email').get_attribute('href'))
            assert mail.scheme == 'mailto' and mail.path == 'joel@echelonadvisorygroup.org'
            draft = parse_qs(mail.query)
            assert draft['subject'] == ['Project Review']
            assert all(label in draft['body'][0] for label in ('Project type', 'completion date', 'Unresolved items', 'records'))
            page.emulate_media(reduced_motion='reduce')
            assert page.evaluate('getComputedStyle(document.documentElement).scrollBehavior') == 'auto'
            page.close()
        missing = browser.new_page()
        response = missing.goto(f'http://127.0.0.1:{server.server_port}/missing/nested/page/')
        assert response.status == 404
        assert missing.locator('h1').inner_text() == 'That page is not here.'
        missing.locator('main a').click()
        assert missing.url == f'http://127.0.0.1:{server.server_port}/'
        browser.close()
    (output / 'accessibility-results.json').write_text(json.dumps(accessibility, indent=2), encoding='utf-8')
    (output / 'browser-results.json').write_text(json.dumps(checks, indent=2))
    assert not errors, '\n'.join(errors)
    print(f'PASS: {len(checks)} page/viewport checks; {len(accessibility)} axe audits; navigation, overflow, headings, requests, skip link, FAQ, inquiry draft, reduced motion, nested 404 recovery.')
finally:
    server.shutdown()
