"""Check actual fragment behavior; AppTest reruns cannot expose stale browser widgets."""
import argparse
import json
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen

from playwright.sync_api import expect, sync_playwright


TEST_PASSWORD = 'local-only-navigation-check'


def check_split_layout(page, panel_key, chart_key, output, name):
    panel = page.locator(f'.st-key-{panel_key}')
    chart = page.locator(f'[class*=st-key-{chart_key}]')
    sizes = []
    for width in (1440, 800, 390):
        page.set_viewport_size({'width': width, 'height': 1000})
        page.wait_for_timeout(500)
        left, right = panel.bounding_box(), chart.bounding_box()
        if width == 1440:
            assert right['x'] > left['x'] + left['width'] - 2
            assert right['width'] > left['width']
            assert min(right['y']+right['height'], left['y']+left['height'], 1000) > max(right['y'], left['y'], 0)
        else:
            assert abs(right['x']-left['x']) < 3, (left, right)
            assert right['y'] > left['y'] + left['height'] - 2
            assert left['height'] <= 362
        assert page.evaluate('()=>document.querySelector("[data-testid=stMain]").scrollWidth') <= width + 1
        sizes.append({'width': width, 'list_width': left['width'], 'chart_width': right['width']})
        panel.scroll_into_view_if_needed()
        page.mouse.move(0, 0)
        page.screenshot(path=str(output / f'{name}-{width}.png'))
    page.set_viewport_size({'width': 1440, 'height': 1000})
    return sizes


def check_country_heatmap(page, output):
    expect(page.get_by_role('radio', name='히트맵', exact=True)).to_be_checked()
    tile = page.locator('.st-key-markets_commodities_selected_symbol_heatmap_pick_SPY button:visible').filter(has_text='United States')
    expect(tile).to_have_count(1, timeout=30000)
    expect(tile).to_contain_text('United States')
    expect(tile).to_contain_text('%')
    tile.scroll_into_view_if_needed()
    before = page.evaluate('()=>document.querySelector("[data-testid=stMain]").scrollTop')
    tile.click()
    page.wait_for_function('()=>document.querySelector("[class*=st-key-markets_commodities_selected_chart] .js-plotly-plot")?.layout?.title?.text?.replace(/<[^>]*>/g,"")==="SPY"')
    after = page.evaluate('()=>document.querySelector("[data-testid=stMain]").scrollTop')
    assert abs(after-before) < 3, f'Heatmap selection scrolled {after-before}px'
    close_sidebar = page.locator('[data-testid=stSidebarCollapseButton]')
    if close_sidebar.is_visible():
        close_sidebar.click()
    panel = page.locator('.st-key-country_heatmap_panel')
    chart = page.locator('[class*=st-key-markets_commodities_selected_chart]')
    responsive = []
    for width in (1440, 800, 390):
        page.set_viewport_size({'width': width, 'height': 1000})
        page.wait_for_timeout(500)
        left, right = panel.bounding_box(), chart.bounding_box()
        assert left['height'] <= (680 if width == 1440 else 360) + 2, left
        if width == 1440:
            assert right['x'] > left['x'] + left['width'] - 2
            assert right['width'] > left['width']
            assert min(right['y']+right['height'], left['y']+left['height'], 1000) > max(right['y'], left['y'], 0)
            cards = page.locator('.st-key-country_heatmap_grid > [data-testid=stLayoutWrapper]')
            first, second = cards.nth(0).bounding_box(), cards.nth(1).bounding_box()
            assert second['x'] > first['x'] + 10, (first, second)
        else:
            assert abs(right['x']-left['x']) < 3, (width, left, right)
            assert right['y'] > left['y'] + left['height'] - 2
        assert page.evaluate('()=>document.querySelector("[data-testid=stMain]").scrollWidth') <= width + 1
        responsive.append({'width': width, 'tile_panel_width': left['width'], 'chart_width': right['width']})
        panel.scroll_into_view_if_needed()
        page.screenshot(path=str(output / f'heatmap-{width}.png'))
    page.set_viewport_size({'width': 1440, 'height': 1000})
    return {'selection_scroll_delta_px': after-before, 'responsive': responsive}


def exercise(page, base, output):
    page.route('**/*', lambda route: route.continue_()
               if route.request.url.startswith(base + '/') else route.abort())
    page.goto(base, wait_until='domcontentloaded')
    page.get_by_text('KIS API · 미국·한국', exact=True).click()
    page.get_by_label('KIS 모드 비밀번호', exact=True).fill(TEST_PASSWORD)
    page.get_by_role('button', name='잠금 해제', exact=True).click()
    page.locator('[class*=st-key-markets_commodities_selected_chart] .js-plotly-plot').wait_for(timeout=60000)
    initial_chart_count = page.locator('.js-plotly-plot').count()
    heatmap = check_country_heatmap(page, output)
    expect(page.get_by_role('radio', name='표 보기', exact=True)).to_have_count(0)

    def mode(value):
        radios = page.get_by_role('radio', name=value, exact=True)
        expect(radios).to_have_count(2)
        for radio in radios.all():
            expect(radio).to_be_checked()

    def area(value, old):
        page.locator(f'[class*=st-key-{value}_view_mode]').wait_for()
        page.locator(f'[class*=st-key-{old}_view_mode]').wait_for(state='detached')

    def scroll():
        return page.evaluate('()=>document.querySelector("[data-testid=stMain]").scrollTop')

    def settle():
        page.wait_for_function('''()=>[...document.querySelectorAll('[data-testid=stPlotlyChart]')]
            .every(e=>e.querySelector('.js-plotly-plot')?._fullLayout) && document.fonts.status==='loaded' ''')
        page.wait_for_timeout(200)

    page.get_by_text('3×3 차트', exact=True).first.click()
    mode('3×3 차트')
    next_page = page.locator('[class*=st-key-markets_commodities_grid_next] button')
    next_page.wait_for()
    settle()
    next_page.scroll_into_view_if_needed()
    page.wait_for_timeout(500)
    before = scroll()
    next_page.click()
    page.wait_for_function('()=>document.body.innerText.includes("3×3 차트 · 2 /")')
    page.wait_for_timeout(500)
    grid_delta = scroll() - before
    assert abs(grid_delta) < 3, f'Grid paging scrolled {grid_delta}px'
    mode('3×3 차트')

    areas = page.locator('[data-testid=stRadio]').filter(has_text='분석 영역')
    areas.get_by_text(re.compile(r'^업종 \(')).click()
    area('sectors', 'markets_commodities')
    mode('3×3 차트')
    areas.get_by_text(re.compile(r'^국가 및 원자재 \(')).click()
    area('markets_commodities', 'sectors')
    page.wait_for_function('()=>document.body.innerText.includes("3×3 차트 · 2 /")')
    page.locator('[class*=st-key-markets_commodities_view_mode]').get_by_text('차트 고정 목록', exact=True).click()
    pick = page.locator('[class*=st-key-markets_commodities_selected_symbol_pick_] button').last
    pick.wait_for()
    settle()
    mode('차트 고정 목록')
    symbol = re.search(r'\(([^)]+)\)$', pick.inner_text()).group(1)
    pick.scroll_into_view_if_needed()
    before = scroll()
    pick.click()
    page.wait_for_function('(s)=>[...document.querySelectorAll(".js-plotly-plot")].some(e=>e.layout?.title?.text?.replace(/<[^>]*>/g,"")===s)', arg=symbol)
    page.wait_for_timeout(500)
    list_delta = scroll() - before
    assert abs(list_delta) < 3, f'Asset selection scrolled {list_delta}px'
    mode('차트 고정 목록')
    expect(page.locator('.js-plotly-plot')).to_have_count(initial_chart_count)
    # Country drill-down must coexist with direct chart selection and return.
    page.locator('[class*=st-key-markets_commodities_selected_symbol_pick_SPY] button').click()
    page.locator('[class*=st-key-markets_commodities_open_country_sectors_SPY] button').click()
    area('sectors', 'markets_commodities')
    mode('차트 고정 목록')
    sector_pick = page.locator('[class*=st-key-sectors_selected_symbol_pick_] button:visible').last
    expect(sector_pick).to_contain_text('26주')
    expect(sector_pick).to_contain_text('신규')
    sector_symbol = re.search(r'\(([^)]+)\)', sector_pick.inner_text().split('\n')[0]).group(1)
    sector_pick.scroll_into_view_if_needed()
    before_sector = scroll()
    sector_pick.click()
    page.wait_for_function('(s)=>document.querySelector("[class*=st-key-sectors_selected_chart] .js-plotly-plot")?.layout?.title?.text?.replace(/<[^>]*>/g,"")===s', arg=sector_symbol)
    assert abs(scroll()-before_sector) < 3
    sector_layout = check_split_layout(page, 'sectors_selected_symbol_compact_list', 'sectors_selected_chart', output, 'sectors')
    page.locator('[class*=st-key-back_to_country_list_from_sectors] button').click()
    area('markets_commodities', 'sectors')
    page.wait_for_function('()=>[...document.querySelectorAll(".js-plotly-plot")].some(e=>e.layout?.title?.text?.replace(/<[^>]*>/g,"")==="SPY")')
    mode('차트 고정 목록')
    # The quick-comparison chart is independent of the selected analysis chart.
    quick = page.locator('[class*=st-key-candidate_quick_pick_] button:visible')
    if quick.count():
        quick_pick = quick.last
        quick_symbol = re.search(r'\(([^)]+)\)$', quick_pick.inner_text().split('\n')[0]).group(1)
        quick_pick.click()
        page.wait_for_function('(s)=>document.querySelector(".js-plotly-plot")?.layout?.title?.text?.replace(/<[^>]*>/g,"")===s', arg=quick_symbol)
        assert page.locator('.js-plotly-plot').last.evaluate('e=>e.layout.title.text.replace(/<[^>]*>/g,"")') == 'SPY'
        quick_layout = check_split_layout(page, 'candidate_quick_chart_symbol_compact_list', 'candidate_quick_preview_chart', output, 'stage2')
        page.locator('.st-key-candidate_quick_chart_period').get_by_text('일봉', exact=True).click()
        page.locator('.st-key-global_asset_view_mode').get_by_text('3×3 차트', exact=True).click()
        expect(page.locator('.st-key-candidate_quick_chart_period')).to_have_count(0)
        page.locator('.st-key-global_asset_view_mode').get_by_text('차트 고정 목록', exact=True).click()
        expect(page.locator('.st-key-candidate_quick_chart_period').get_by_role('radio', name='일봉', exact=True)).to_be_checked()
        mode('차트 고정 목록')
    expect(page.locator('[data-testid=stException]')).to_have_count(0)
    page.screenshot(path=str(output / 'navigation.png'))
    return {'grid_scroll_delta_px': grid_delta, 'selection_scroll_delta_px': list_delta,
            'selected_chart': symbol, 'country_return_chart': 'SPY',
            'mode_controls_synchronized': True, 'heatmap': heatmap,
            'sector_layout': sector_layout, 'quick_layout': quick_layout if quick.count() else []}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--browser')
    parser.add_argument('--output-dir', type=Path, default=Path('artifacts/dashboard-browser'))
    parser.add_argument('--serve', action='store_true')
    parser.add_argument('--port', type=int)
    parser.add_argument('--secret-file')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.serve:
        import requests
        def reject_provider(*unused, **kwargs):
            raise AssertionError('Unexpected provider request in snapshot browser test')
        requests.sessions.Session.request = reject_provider
        from streamlit.web import cli
        sys.argv = ['streamlit', 'run', str(root / 'app.py'),
                    '--server.address=127.0.0.1', f'--server.port={args.port}',
                    '--browser.gatherUsageStats=false', '--server.headless=true',
                    f'--secrets.files={args.secret_file}']
        cli.main()
        return
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    base = f'http://127.0.0.1:{port}'
    with tempfile.TemporaryDirectory() as tmp, (args.output_dir / 'streamlit.log').open('w') as log:
        secret = Path(tmp) / 'test-secrets.toml'
        secret.write_text(f'APP_PASSWORD = "{TEST_PASSWORD}"\n')
        server = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--serve',
                                   '--port', str(port), '--secret-file', str(secret)],
                                  cwd=root, stdout=log, stderr=subprocess.STDOUT)
        try:
            for _ in range(120):
                try:
                    with urlopen(base + '/_stcore/health', timeout=1) as response:
                        if response.status == 200:
                            break
                except OSError:
                    time.sleep(.25)
            else:
                raise RuntimeError('Local dashboard did not start')
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(executable_path=args.browser, headless=True,
                                                    args=['--no-sandbox'])
                page = browser.new_page(viewport={'width': 1440, 'height': 1000})
                try:
                    result = exercise(page, base, args.output_dir)
                    (args.output_dir / 'results.json').write_text(json.dumps(result, indent=2))
                    print(json.dumps(result))
                except Exception:
                    page.screenshot(path=str(args.output_dir / 'failure.png'))
                    (args.output_dir / 'failure.txt').write_text(page.locator('body').inner_text())
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
