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


def click(locator):
    # A rerun briefly retains stale widgets while mounting replacements.
    locator = locator.filter(visible=True)
    expect(locator).to_have_count(1, timeout=30000)
    locator.click()


def assert_header(page):
    header=page.locator('.st-key-analysis_header')
    page.wait_for_function("""()=>{
      const h=document.querySelector('.st-key-analysis_header')?.getBoundingClientRect();
      const t=document.querySelector('.st-key-analysis_header h3')?.getBoundingClientRect();
      const r=document.querySelector('.st-key-analysis_header [role=radiogroup]')?.getBoundingClientRect();
      const b=document.querySelector('[data-testid=stHeader]')?.getBoundingClientRect();
      return h&&t&&r&&b&&t.y>=b.bottom&&t.bottom<=r.y+1&&h.y>=0&&h.bottom<240;
    }""")
    h=header.bounding_box();title=header.locator('h3').bounding_box()
    banner=page.locator('[data-testid=stHeader]').bounding_box()
    tabs=header.locator('[role=radiogroup]').bounding_box()
    assert title['y'] >= banner['y']+banner['height'], (title,banner)
    assert title['y']+title['height'] <= tabs['y']+1, (title,tabs)
    assert h['y'] >= 0 and h['y']+h['height'] < 240, h
    # Native accessible radios keep their keys; decorative circles are hidden.
    assert header.locator('[data-testid=stRadioOption] > div > div:not([data-testid=stMarkdownContainer])').evaluate_all('es=>es.every(e=>getComputedStyle(e).display==="none")')
    selected=header.locator('label:has(input:checked)')
    assert selected.evaluate('e=>getComputedStyle(e).borderTopLeftRadius') == '8px'


def check_split_layout(page, panel_key, chart_key, output, name):
    panel = page.locator(f'.st-key-{panel_key}')
    chart = page.locator(f'.st-key-{chart_key}_asset_card')
    sizes = []
    for width in (1440, 800, 390):
        page.set_viewport_size({'width': width, 'height': 1000})
        page.wait_for_timeout(500)
        assert_header(page)
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
    click(tile)
    page.wait_for_function('()=>document.querySelector("[class*=st-key-markets_commodities_selected_chart] .js-plotly-plot")?.layout?.meta?.asset_symbol==="SPY"')
    after = page.evaluate('()=>document.querySelector("[data-testid=stMain]").scrollTop')
    assert abs(after-before) < 3, f'Heatmap selection scrolled {after-before}px'
    close_sidebar = page.locator('[data-testid=stSidebarCollapseButton]')
    if close_sidebar.is_visible():
        click(close_sidebar)
    panel = page.locator('.st-key-country_heatmap_panel')
    chart = page.locator('.st-key-markets_commodities_selected_chart_asset_card')
    responsive = []
    for width in (1440, 800, 390):
        page.set_viewport_size({'width': width, 'height': 1000})
        page.wait_for_timeout(500)
        assert_header(page)
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
            assert second['x'] > first['x'] + 10, (first, second, page.locator('.st-key-dashboard_list_width [role=slider]').get_attribute('aria-valuenow'), left)
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
    click(page.get_by_text('KIS API · 미국·한국', exact=True))
    page.get_by_label('KIS 모드 비밀번호', exact=True).fill(TEST_PASSWORD)
    click(page.get_by_role('button', name='잠금 해제', exact=True))
    header = page.locator('.st-key-analysis_header')
    header.wait_for(timeout=60000)
    assert page.title() == 'Global Stage Radar'
    assert_header(page)
    expect(header.get_by_role('radio', name='Stage 2 후보', exact=True)).to_be_checked()
    expect(page.get_by_role('radio', name='표 보기', exact=True)).to_have_count(0)

    def tab(label):
        click(header.get_by_text(label, exact=True))
        expect(header.get_by_role('radio', name=label, exact=True)).to_be_checked()
        page.wait_for_timeout(400)

    def ready():
        page.wait_for_function('''()=>[...document.querySelectorAll('[data-testid=stPlotlyChart]')]
          .every(e=>e.querySelector('.js-plotly-plot')?._fullLayout && (e.closest('[class*="_asset_card"]')||e).querySelector('.radar-price-scale'))''')
        page.wait_for_timeout(300)

    def scroll():
        return page.evaluate('()=>document.querySelector("[data-testid=stMain]").scrollTop')

    ready()
    sidebar=page.locator('[data-testid=stSidebar]')
    click(sidebar.get_by_text('화면 설정',exact=True))
    width=sidebar.get_by_role('slider')
    expect(width).to_have_value('33')
    width.press('End')
    expect(width).to_have_value('45')
    click(sidebar.get_by_text('화면 설정',exact=True))
    page.wait_for_timeout(900)
    ready()
    quick_layout = check_split_layout(page, 'candidate_quick_chart_symbol_compact_list', 'candidate_quick_preview_chart', output, 'stage2')
    quick = page.locator('[class*=st-key-candidate_quick_pick_] button:visible').last
    quick_symbol = re.search(r'\(([^)]+)\)', quick.inner_text().split('\n')[0]).group(1)
    list_panel=page.locator('.st-key-candidate_quick_chart_symbol_compact_list')
    list_panel.scroll_into_view_if_needed()
    list_panel.evaluate('e=>e.scrollTop=e.scrollHeight')
    inner_scroll=list_panel.evaluate('e=>e.scrollTop')
    outer_scroll=scroll()
    click(quick)
    page.wait_for_function('(s)=>document.querySelector(".js-plotly-plot")?.layout?.meta?.asset_symbol===s', arg=quick_symbol)
    assert abs(list_panel.evaluate('e=>e.scrollTop')-inner_scroll)<3
    assert abs(scroll()-outer_scroll)<3
    click(page.locator('.st-key-candidate_quick_chart_period').get_by_text('일', exact=True))
    tab('국가 및 원자재')
    heatmap = check_country_heatmap(page, output)
    click(page.locator('.st-key-markets_commodities_view_mode').get_by_text('3×3 차트', exact=True))
    ready()
    next_page=page.locator('.st-key-markets_commodities_grid_next button:visible')
    last_chart=page.locator('.st-key-markets_commodities_grid_canvas [data-testid=stPlotlyChart]').last
    assert next_page.bounding_box()['y'] > last_chart.bounding_box()['y']+last_chart.bounding_box()['height']
    next_page.scroll_into_view_if_needed()
    before=scroll()
    click(next_page)
    page.wait_for_function('()=>document.body.innerText.includes("3×3 차트 · 2 /")')
    page.wait_for_timeout(500)
    delta=scroll()-before
    assert abs(delta)<3, delta
    # Header stays on screen even at the grid footer.
    box=header.bounding_box()
    assert_header(page)
    assert 0 <= box['y'] < 100, (box, header.evaluate('e=>{let a=[];for(let p=e;p;p=p.parentElement)a.push({tag:p.tagName,cls:p.className,test:p.dataset.testid,pos:getComputedStyle(p).position,top:getComputedStyle(p).top,overflow:getComputedStyle(p).overflow,y:p.getBoundingClientRect().y,h:p.getBoundingClientRect().height});return a;}'))
    tab('업종')
    expect(page.locator('.st-key-sectors_view_mode').get_by_role('radio',name='목록',exact=True)).to_be_checked()
    ready()
    sector_layout=check_split_layout(page,'sectors_selected_symbol_compact_list','sectors_selected_chart',output,'sectors')
    tab('국가 및 원자재')
    expect(page.locator('.st-key-markets_commodities_view_mode').get_by_role('radio',name='3×3 차트',exact=True)).to_be_checked()
    page.wait_for_function('()=>document.body.innerText.includes("3×3 차트 · 2 /")')
    click(page.locator('.st-key-markets_commodities_view_mode').get_by_text('목록',exact=True))
    click(page.locator('[class*=st-key-markets_commodities_selected_symbol_pick_SPY] button:visible'))
    click(page.locator('[class*=st-key-markets_commodities_open_country_sectors_SPY] button:visible'))
    expect(header.get_by_role('radio',name='업종',exact=True)).to_be_checked()
    click(page.locator('[class*=st-key-back_to_country_list_from_sectors] button:visible'))
    expect(header.get_by_role('radio',name='국가 및 원자재',exact=True)).to_be_checked()
    tab('Stage 2 후보')
    expect(page.locator('.st-key-candidate_quick_chart_period').get_by_role('radio',name='일',exact=True)).to_be_checked()
    page.wait_for_function('(s)=>document.querySelector(".js-plotly-plot")?.layout?.meta?.asset_symbol===s',arg=quick_symbol)
    # Stored active universe has no approved stocks; verify stock UI with explicit synthetic demo data.
    tab('종목')
    click(page.get_by_text('가상 데모',exact=True))
    page.locator('.st-key-stocks_selected_symbol_compact_list').wait_for(timeout=60000)
    ready()
    stock_layout=check_split_layout(page,'stocks_selected_symbol_compact_list','stocks_selected_chart',output,'stocks-demo')
    # Arrow keys act on the focused list without scrolling the analysis workspace.
    picks=page.locator('[class*=st-key-stocks_selected_symbol_pick_] button:visible')
    first,second=picks.nth(0),picks.nth(1)
    second_symbol=re.search(r'\(([^)]+)\)',second.inner_text().split('\n')[0]).group(1)
    click(first);page.wait_for_timeout(300)
    keyboard_before=scroll()
    page.keyboard.press('ArrowDown')
    page.wait_for_function('(s)=>document.querySelector("[class*=st-key-stocks_selected_chart] .js-plotly-plot")?.layout?.meta?.asset_symbol===s',arg=second_symbol)
    assert abs(scroll()-keyboard_before)<3
    click(page.locator('.st-key-stocks_favorite button:visible'))
    click(page.locator('.st-key-stocks_favorites_only').get_by_text('관심 목록만',exact=True))
    expect(page.locator('.st-key-stocks_favorites_only').get_by_role('checkbox')).to_be_checked()
    expect(picks).to_have_count(1)
    expect(picks.first).to_contain_text('★')
    click(page.locator('.st-key-stocks_favorites_only').get_by_text('관심 목록만',exact=True))
    expect(page.locator('.st-key-stocks_favorites_only').get_by_role('checkbox')).not_to_be_checked()
    expect(picks).to_have_count(3)
    click(page.locator('.st-key-stocks_selected_period_'+second_symbol).get_by_text('일',exact=True))
    page.wait_for_function('()=>document.querySelector("[class*=st-key-stocks_selected_chart] .js-plotly-plot")?._fullData?.find(t=>t.type==="candlestick")?.name==="일봉"')
    price_scale=page.locator('[class*=st-key-stocks_selected_chart] .radar-price-scale')
    price_scale.select_option('log')
    tab('업종');tab('종목')
    expect(price_scale).to_have_value('log',timeout=30000)
    # Safe UI preferences survive a real reload; credentials and favorites do not travel in the URL.
    page.wait_for_function("""()=>{try{const p=JSON.parse(new URL(location.href).searchParams.get('radar'));return p.tab==='stocks' && p.stocks.period==='일봉';}catch{return false;}}""")
    page.reload(wait_until='domcontentloaded')
    header.wait_for(timeout=60000)
    expect(header.get_by_role('radio',name='종목',exact=True)).to_be_checked()
    expect(page.locator('.st-key-stocks_selected_period_'+second_symbol).get_by_role('radio',name='일',exact=True)).to_be_checked()
    expect(price_scale).to_have_value('log',timeout=30000)
    page.wait_for_function('()=>document.querySelector("[class*=st-key-stocks_selected_chart] .js-plotly-plot")?._fullLayout.yaxis.type==="log"')
    assert 'kis_authenticated' not in page.url
    # Filtering a selected stock out of the list keeps its companion chart.
    chosen=page.locator('[class*=st-key-stocks_selected_chart] .js-plotly-plot').evaluate('e=>e.layout.meta.asset_symbol')
    search=page.locator('.st-key-stocks_search input')
    search.fill('NO_SUCH_TICKER');search.press('Enter')
    expect(page.get_by_text('선택 종목은 현재 목록 필터 밖에 있습니다. 차트를 유지합니다.',exact=True)).to_be_visible()
    assert page.locator('[class*=st-key-stocks_selected_chart] .js-plotly-plot').evaluate('e=>e.layout.meta.asset_symbol') == chosen
    search.fill('');search.press('Enter')
    tab('국가 및 원자재')
    click(page.locator('.st-key-markets_commodities_selected_symbol_pick_USMKT button:visible'))
    click(page.locator('.st-key-markets_commodities_open_country_sectors_USMKT button:visible'))
    click(page.locator('.st-key-sectors_selected_symbol_pick_TECH button:visible'))
    click(page.locator('.st-key-sectors_open_stocks_TECH button:visible'))
    expect(header.get_by_role('radio',name='종목',exact=True)).to_be_checked()
    click(page.locator('.st-key-stocks_back_to_sectors button:visible'))
    expect(header.get_by_role('radio',name='업종',exact=True)).to_be_checked()
    click(page.locator('.st-key-back_to_country_list_from_sectors button:visible'))
    expect(header.get_by_role('radio',name='국가 및 원자재',exact=True)).to_be_checked()
    page.set_viewport_size({'width':320,'height':1000})
    header.scroll_into_view_if_needed()
    page.wait_for_timeout(400)
    assert header.locator('[role=radiogroup]').evaluate('e=>e.scrollWidth>e.clientWidth')
    expect(page.locator('[data-testid=stException]')).to_have_count(0)
    click(page.locator('.st-key-markets_commodities_view_mode').get_by_text('3×3 차트',exact=True))
    ready()
    footer=page.locator('.st-key-markets_commodities_grid_pager')
    footer.scroll_into_view_if_needed()
    page.wait_for_timeout(300)
    last=page.locator('.st-key-markets_commodities_grid_canvas [data-testid=stPlotlyChart]').last.bounding_box()
    box=footer.bounding_box()
    assert box['y']>=last['y']+last['height']-1
    assert 0<=box['x'] and box['x']+box['width']<=320
    expect(page.locator('.st-key-markets_commodities_grid_prev button:visible')).to_be_disabled()
    expect(page.locator('.st-key-markets_commodities_grid_next button:visible')).to_be_disabled()
    page.screenshot(path=str(output/'shell-mobile.png'))
    # The shared star uses venue-qualified browser-tab storage, independent of Stage.
    page.set_viewport_size({'width':1440,'height':1000})
    tab('종목')
    click(page.locator('.st-key-stocks_view_mode').get_by_text('목록',exact=True))
    chart=page.locator('.st-key-stocks_selected_chart .js-plotly-plot')
    chart.wait_for()
    chosen=chart.evaluate('e=>e.layout.meta.asset_symbol')
    favorite=page.locator('.st-key-stocks_favorite button:visible')
    if favorite.inner_text().startswith('☆'):
        click(favorite)
    expect(favorite).to_have_accessible_name(re.compile('★ 관심 해제'))
    page.wait_for_function('(symbol)=>{try{return JSON.parse(sessionStorage.getItem("global-stage-radar:favorites:v2")||"[]").some(r=>r.symbol===symbol);}catch{return false;}}',arg=chosen)
    assert not chart.evaluate('e=>!!e.layout.title?.text')
    card=page.locator('.st-key-stocks_selected_chart_asset_card')
    expect(card.locator('h4')).to_have_count(1)
    assert card.locator('.radar-price-scale').count()==1
    period_box=card.locator('[role=radiogroup]').bounding_box()
    axis_box=card.locator('.radar-price-scale').bounding_box()
    assert abs(period_box['y']-axis_box['y'])<16
    tab('☆ 관심 목록')
    expect(page.locator('.st-key-favorites_selected_chart_asset_card')).to_be_visible()
    click(page.locator('.st-key-favorites_area_filter').get_by_role('combobox'))
    click(page.get_by_role('option',name='업종',exact=True))
    expect(page.get_by_text('현재 필터에 해당하는 관심 자산이 없습니다.',exact=False)).to_be_visible()
    click(page.locator('.st-key-favorites_area_filter').get_by_role('combobox'))
    click(page.get_by_role('option',name='종목',exact=True))
    click(page.locator('.st-key-favorites_view_mode').get_by_text('3×3 차트',exact=True))
    ready()
    expect(page.locator('.st-key-favorites_grid_canvas [data-testid=stPlotlyChart]')).to_have_count(1)
    page.wait_for_function("""()=>{try{return JSON.parse(new URL(location.href).searchParams.get('radar')).tab==='favorites';}catch{return false;}}""")
    page.reload(wait_until='domcontentloaded')
    expect(header.get_by_role('radio',name='☆ 관심 목록',exact=True)).to_be_checked()
    ready()
    expect(page.locator('.st-key-favorites_grid_canvas button:visible').filter(has_text='★ 관심 해제')).to_have_count(1)
    isolated=page.context.browser.new_page()
    isolated.route('**/*',lambda route:route.continue_() if route.request.url.startswith(base+'/') else route.abort())
    isolated.goto(page.url,wait_until='domcontentloaded')
    expect(isolated.get_by_text('현재 필터에 해당하는 관심 자산이 없습니다.',exact=False)).to_be_visible(timeout=30000)
    assert isolated.evaluate('()=>JSON.parse(sessionStorage.getItem("global-stage-radar:favorites:v2")||"[]").length')==0
    isolated.close()
    for width in (1440,800,390):
        page.set_viewport_size({'width':width,'height':1000})
        page.wait_for_timeout(400)
        assert page.evaluate('()=>document.querySelector("[data-testid=stMain]").scrollWidth')<=width+1
        page.screenshot(path=str(output/f'favorites-{width}.png'))
    click(page.locator('.st-key-favorites_grid_canvas button:visible').filter(has_text='★ 관심 해제'))
    expect(page.get_by_text('현재 필터에 해당하는 관심 자산이 없습니다.',exact=False)).to_be_visible()
    page.wait_for_function('(symbol)=>!JSON.parse(sessionStorage.getItem("global-stage-radar:favorites:v2")||"[]").some(r=>r.symbol===symbol)',arg=chosen)
    tab('종목')
    expect(page.locator('.st-key-stocks_favorite button:visible')).to_have_accessible_name(re.compile('☆ 관심 등록'))
    return {'grid_scroll_delta_px':delta,'heatmap':heatmap,'sector_layout':sector_layout,'quick_layout':quick_layout,'sticky_header':True,'independent_tabs':True,'stock_demo_layout':stock_layout,'country_sector_stock_round_trip':True,'filtered_selection_preserved':True,'keyboard_selection':True,'favorites':True,'watchlist_reload_and_filters':True,'shared_card_controls':True,'reload_preferences':True}


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
