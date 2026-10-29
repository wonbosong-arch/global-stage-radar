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
import traceback
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
        panel.scroll_into_view_if_needed()
        page.wait_for_timeout(200)
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
        panel.scroll_into_view_if_needed()
        page.wait_for_timeout(200)
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
    header = page.locator('.st-key-analysis_header')
    header.wait_for(timeout=60000)
    expect(header.get_by_role('radio', name='Stage 2 후보', exact=True)).to_be_checked()
    expect(page.get_by_role('radio', name='표 보기', exact=True)).to_have_count(0)

    def tab(label):
        header.get_by_text(label, exact=True).click()
        expect(header.get_by_role('radio', name=label, exact=True)).to_be_checked()
        page.wait_for_timeout(400)

    def ready():
        page.wait_for_function('''()=>[...document.querySelectorAll('[data-testid=stPlotlyChart]')]
          .every(e=>e.querySelector('.js-plotly-plot')?._fullLayout && e.querySelector('.radar-price-scale'))''')
        page.wait_for_timeout(300)

    def scroll():
        return page.evaluate('()=>document.querySelector("[data-testid=stMain]").scrollTop')

    ready()
    quick_layout = check_split_layout(page, 'candidate_quick_chart_symbol_compact_list', 'candidate_quick_preview_chart', output, 'stage2')
    quick = page.locator('[class*=st-key-candidate_quick_pick_] button:visible').last
    quick_symbol = re.search(r'\(([^)]+)\)$', quick.inner_text().split('\n')[0]).group(1)
    quick.click()
    page.wait_for_function('(s)=>document.querySelector(".js-plotly-plot")?.layout?.title?.text?.replace(/<[^>]*>/g,"")===s', arg=quick_symbol)
    page.locator('.st-key-candidate_quick_chart_period').get_by_text('일봉', exact=True).click()
    tab('국가 및 원자재')
    heatmap = check_country_heatmap(page, output)
    page.locator('.st-key-markets_commodities_view_mode').get_by_text('3×3 차트', exact=True).click()
    ready()
    next_page=page.locator('.st-key-markets_commodities_grid_next button')
    next_page.scroll_into_view_if_needed()
    before=scroll()
    next_page.click()
    page.wait_for_function('()=>document.body.innerText.includes("3×3 차트 · 2 /")')
    page.wait_for_timeout(500)
    delta=scroll()-before
    assert abs(delta)<3, delta
    # Header stays on screen even at the grid footer.
    box=header.bounding_box()
    assert 0 <= box['y'] < 100, (box, header.evaluate('e=>{let a=[];for(let p=e;p;p=p.parentElement)a.push({tag:p.tagName,cls:p.className,test:p.dataset.testid,pos:getComputedStyle(p).position,top:getComputedStyle(p).top,overflow:getComputedStyle(p).overflow,y:p.getBoundingClientRect().y,h:p.getBoundingClientRect().height});return a;}'))
    tab('업종')
    expect(page.locator('.st-key-sectors_view_mode').get_by_role('radio',name='차트 고정 목록',exact=True)).to_be_checked()
    ready()
    sector_layout=check_split_layout(page,'sectors_selected_symbol_compact_list','sectors_selected_chart',output,'sectors')
    tab('국가 및 원자재')
    expect(page.locator('.st-key-markets_commodities_view_mode').get_by_role('radio',name='3×3 차트',exact=True)).to_be_checked()
    page.wait_for_function('()=>document.body.innerText.includes("3×3 차트 · 2 /")')
    page.locator('.st-key-markets_commodities_view_mode').get_by_text('차트 고정 목록',exact=True).click()
    page.locator('[class*=st-key-markets_commodities_selected_symbol_pick_SPY] button').click()
    page.locator('[class*=st-key-markets_commodities_open_country_sectors_SPY] button').click()
    expect(header.get_by_role('radio',name='업종',exact=True)).to_be_checked()
    page.locator('[class*=st-key-back_to_country_list_from_sectors] button').click()
    expect(header.get_by_role('radio',name='국가 및 원자재',exact=True)).to_be_checked()
    tab('Stage 2 후보')
    expect(page.locator('.st-key-candidate_quick_chart_period').get_by_role('radio',name='일봉',exact=True)).to_be_checked()
    page.wait_for_function('(s)=>document.querySelector(".js-plotly-plot")?.layout?.title?.text?.replace(/<[^>]*>/g,"")===s',arg=quick_symbol)
    # Stored active universe has no approved stocks; verify stock UI with explicit synthetic demo data.
    tab('종목')
    page.get_by_text('가상 데모',exact=True).click()
    page.locator('.st-key-stocks_selected_symbol_compact_list').wait_for(timeout=60000)
    ready()
    stock_layout=check_split_layout(page,'stocks_selected_symbol_compact_list','stocks_selected_chart',output,'stocks-demo')
    # Arrow keys act on the focused list without scrolling the analysis workspace.
    picks=page.locator('[class*=st-key-stocks_selected_symbol_pick_] button:visible')
    first,second=picks.nth(0),picks.nth(1)
    second_symbol=re.search(r'\(([^)]+)\)$',second.inner_text().split('\n')[0]).group(1)
    first.click();page.wait_for_timeout(300)
    keyboard_before=scroll()
    page.keyboard.press('ArrowDown')
    page.wait_for_function('(s)=>document.querySelector("[class*=st-key-stocks_selected_chart] .js-plotly-plot")?.layout?.title?.text?.replace(/<[^>]*>/g,"")===s',arg=second_symbol)
    assert abs(scroll()-keyboard_before)<3
    page.locator('.st-key-stocks_favorite button').click()
    page.locator('.st-key-stocks_favorites_only').get_by_role('checkbox').check()
    expect(picks).to_have_count(1)
    expect(picks.first).to_contain_text('★')
    page.locator('.st-key-stocks_favorites_only').get_by_role('checkbox').uncheck()
    expect(picks).to_have_count(3)
    page.locator('.st-key-stocks_selected_period_'+second_symbol).get_by_text('일봉',exact=True).click()
    price_scale=page.locator('[class*=st-key-stocks_selected_chart] .radar-price-scale')
    price_scale.select_option('log')
    tab('업종');tab('종목')
    expect(price_scale).to_have_value('log')
    # Safe UI preferences survive a real reload; credentials and favorites do not travel in the URL.
    page.reload(wait_until='domcontentloaded')
    header.wait_for(timeout=60000)
    expect(header.get_by_role('radio',name='종목',exact=True)).to_be_checked()
    expect(page.locator('.st-key-stocks_selected_period_'+second_symbol).get_by_role('radio',name='일봉',exact=True)).to_be_checked()
    expect(price_scale).to_have_value('log')
    page.wait_for_function('()=>document.querySelector("[class*=st-key-stocks_selected_chart] .js-plotly-plot")?._fullLayout.yaxis.type==="log"')
    assert 'kis_authenticated' not in page.url
    # Filtering a selected stock out of the list keeps its companion chart.
    chosen=page.locator('[class*=st-key-stocks_selected_chart] .js-plotly-plot').evaluate('e=>e.layout.title.text.replace(/<[^>]*>/g,"")')
    search=page.locator('.st-key-stocks_search input')
    search.fill('NO_SUCH_TICKER');search.press('Enter')
    expect(page.get_by_text('선택 종목은 현재 목록 필터 밖에 있습니다. 차트를 유지합니다.',exact=True)).to_be_visible()
    assert page.locator('[class*=st-key-stocks_selected_chart] .js-plotly-plot').evaluate('e=>e.layout.title.text.replace(/<[^>]*>/g,"")') == chosen
    search.fill('');search.press('Enter')
    tab('국가 및 원자재')
    page.locator('.st-key-markets_commodities_selected_symbol_pick_USMKT button').click()
    page.locator('.st-key-markets_commodities_open_country_sectors_USMKT button').click()
    page.locator('.st-key-sectors_selected_symbol_pick_TECH button:visible').click()
    page.locator('.st-key-sectors_open_stocks_TECH button').click()
    expect(header.get_by_role('radio',name='종목',exact=True)).to_be_checked()
    page.locator('.st-key-stocks_back_to_sectors button').click()
    expect(header.get_by_role('radio',name='업종',exact=True)).to_be_checked()
    page.locator('.st-key-back_to_country_list_from_sectors button').click()
    expect(header.get_by_role('radio',name='국가 및 원자재',exact=True)).to_be_checked()
    page.set_viewport_size({'width':390,'height':1000})
    header.scroll_into_view_if_needed()
    page.wait_for_timeout(400)
    assert header.locator('[role=radiogroup]').evaluate('e=>e.scrollWidth>e.clientWidth')
    expect(page.locator('[data-testid=stException]')).to_have_count(0)
    page.screenshot(path=str(output/'shell-mobile.png'))
    return {'grid_scroll_delta_px':delta,'heatmap':heatmap,'sector_layout':sector_layout,'quick_layout':quick_layout,'sticky_header':True,'independent_tabs':True,'stock_demo_layout':stock_layout,'country_sector_stock_round_trip':True,'filtered_selection_preserved':True,'keyboard_selection':True,'favorites':True,'reload_preferences':True}


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
                    print('::error::' + traceback.format_exc().replace('%', '%25').replace('\n', '%0A'), flush=True)
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
