"""Exercise a hosting wrapper that drops the inner app URL on full reload."""
import argparse
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen

from playwright.sync_api import expect, sync_playwright
import check_hosted_dashboard as hosted
from table_checks import check_chart_controls


def check_current_shared_ui(surface, state_key, chart_key):
    """Current branch contract; the live-host inspector can target an older release."""
    panel = surface.locator(f'.st-key-{state_key}_compact_list')
    expect(panel).to_be_visible(timeout=30000)
    header = surface.locator(f'.st-key-{state_key}_table_header')
    stock = state_key == 'stocks_selected_symbol'
    expect(header.get_by_role('button', name='티커' if stock else '자산 / 티커', exact=True)).to_have_count(1)
    expect(header.get_by_role('button', name='26주 수익률 ↓' if stock else '26주 수익률', exact=True)).to_have_count(1)
    rows = panel.locator('[class*="_table_row_"].stHorizontalBlock')
    expect(rows.first).to_be_attached(timeout=30000)
    low, high = (30, 34) if stock else (44, 48)
    assert low <= rows.first.evaluate('e=>e.getBoundingClientRect().height') <= high
    if stock:
        expect(panel.locator('.radar-table-name')).to_have_count(0)
    else:
        assert rows.first.locator('.radar-table-name').inner_text().strip()
    assert panel.locator('.radar-table-number').evaluate_all('es=>es.every(e=>getComputedStyle(e).textAlign==="right")')
    assert panel.evaluate('e=>e.scrollWidth>e.clientWidth')
    card = surface.locator(f'.st-key-{chart_key}_asset_card')
    expect(card.locator('.radar-price-scale')).to_be_visible(timeout=30000)
    check_chart_controls(card)
    symbol = card.locator('.js-plotly-plot').evaluate('e=>e.layout.meta.asset_symbol')
    expect(card.locator('h4')).to_have_text(symbol)
    return {'rows': rows.count(), 'ticker_header': True, 'button_controls': True, 'visible_names': not stock}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--browser')
    parser.add_argument('--output-dir', type=Path, default=Path('artifacts/embedded-reload'))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parents[1]
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    base = f'http://127.0.0.1:{port}'
    with tempfile.TemporaryDirectory() as tmp, (args.output_dir / 'server.log').open('w') as log:
        secret = Path(tmp) / 'secrets.toml'
        secret.write_text('')
        # The existing isolated server rejects all provider requests.
        server = subprocess.Popen([sys.executable, str(root / 'browser_checks/check_dashboard_navigation.py'),
            '--serve', '--port', str(port), '--secret-file', str(secret)], cwd=root,
            stdout=log, stderr=subprocess.STDOUT)
        try:
            for _ in range(120):
                try:
                    with urlopen(base + '/_stcore/health', timeout=1):
                        break
                except OSError:
                    time.sleep(.25)
            else:
                raise RuntimeError('Local embedded app did not start')
            hosted.APP_URL = base + '/hosting-wrapper'
            # Reuse every existing bookmark/filter/full-frame reload step while
            # checking this branch's intentional name/row/toolbar presentation.
            hosted.check_shared_ui = check_current_shared_ui
            expected = json.loads((root / 'release_info.json').read_text())['version']
            with sync_playwright() as p:
                browser = p.chromium.launch(executable_path=args.browser, headless=True, args=['--no-sandbox'])
                page = browser.new_page(viewport={'width': 1440, 'height': 1000})
                page.route('**/hosting-wrapper', lambda route: route.fulfill(content_type='text/html',
                    body='<style>body{margin:0}</style><iframe src="/" style="width:100%;height:100vh;border:0"></iframe>'))
                try:
                    result = hosted.verify(page, expected, 60, args.output_dir)
                    (args.output_dir / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
                    print(json.dumps(result))
                except Exception:
                    page.screenshot(path=str(args.output_dir / 'failure.png'))
                    raise
                finally:
                    browser.close()
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()


if __name__ == '__main__':
    main()
