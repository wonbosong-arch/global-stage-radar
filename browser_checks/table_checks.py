"""Real DOM contracts for the shared ticker table and chart controls."""
import re
from playwright.sync_api import expect


def settle_native_ui(page):
    # The status icon can disappear before a full sidebar rerun replaces stale
    # widgets. Interact only after the script and its streamed DOM have settled.
    page.wait_for_function('''()=>
      document.querySelector('[data-testid=stApp]')?.getAttribute('data-test-script-state')==='notRunning'
      && !document.querySelector('[data-stale=true]')
    ''', timeout=60000)


def wait_chart(page, chart_key, symbol=None):
    page.wait_for_function('''({key,symbol})=>{
      const g=document.querySelector(`.st-key-${key} .js-plotly-plot`);
      return g?._fullLayout && g.layout?.meta?.asset_symbol &&
        (!symbol || g.layout.meta.asset_symbol===symbol);
    }''', arg={'key':chart_key, 'symbol':symbol}, timeout=30000)


def check_chart_controls(card):
    if 'st-key-stocks_selected_chart_asset_card' in (card.get_attribute('class') or ''):
        period = card.get_by_role('button', name='일/주', exact=True)
        scale = card.get_by_role('switch', name='로그', exact=True)
        expect(period).to_be_visible()
        expect(scale).to_be_visible()
        assert abs(period.bounding_box()['y'] - scale.bounding_box()['y']) < 12
        return
    period = card.locator('[data-testid=stRadio] [role=radiogroup]')
    scale = card.locator('.radar-price-scale')
    expect(period.get_by_role('radio', name='일봉', exact=True)).to_have_count(1)
    expect(period.get_by_role('radio', name='주봉', exact=True)).to_have_count(1)
    expect(scale.get_by_role('radio', name='선형', exact=True)).to_have_count(1)
    expect(scale.get_by_role('radio', name='로그', exact=True)).to_have_count(1)
    a = period.locator('label:has(input)').first.bounding_box()
    period_right = period.locator('label:has(input)').last.bounding_box()
    b = scale.bounding_box()
    c = card.bounding_box()
    same_line = abs(a['y']-b['y']) < 2 and b['x'] >= period_right['x']+period_right['width']
    wrapped = b['y'] >= a['y']+a['height']-1 and abs(a['x']-b['x']) < 2
    assert same_line if c['width'] >= 240 else same_line or wrapped, (a,b)
    assert b['x']+b['width'] <= c['x']+c['width']-5, (b,c)
    assert '가격 축' not in card.locator('[class*="_controls"]').inner_text()
    assert card.locator('select.radar-price-scale').count() == 0


def check_ticker_table(page, state_key, chart_key, output, *, check_star=False):
    # A sidebar rerun can resize the table between successive box measurements.
    settle_native_ui(page)
    panel = page.locator(f'.st-key-{state_key}_compact_list')
    stock = state_key == 'stocks_selected_symbol'
    ticker_title = '티커' if stock else '자산 / 티커'
    ticker_selector = 'button[kind]:not([class*="_table_star_"] button)'
    ticker_pick = f'{ticker_selector}:visible'
    header = page.locator(f'.st-key-{state_key}_table_header')
    rows = panel.locator('[class*="_table_row_"].stHorizontalBlock')
    expect(rows.first).to_be_attached(timeout=30000)
    page.wait_for_function('key=>document.querySelector(`.st-key-${key}_compact_list`)?.dataset.radarTableReady==="true"', arg=state_key)
    panel.scroll_into_view_if_needed()
    panel.evaluate('e=>{e.scrollTop=0;e.scrollLeft=0;}')
    page.wait_for_timeout(150)
    names = header.locator('button[kind]:visible').all_text_contents()
    if stock:
        # Verify the initial viewport and exact second-screen column order.
        assert [name.split(' ↓')[0] for name in names[:6]] == [
            '☆', '티커', '26주 수익률', 'Stage', '시가총액($B)', '1년 수익률',
        ], names
        assert '13주 수익률' not in names
        fifth_column = header.locator(':scope > div').nth(4).bounding_box()
        viewport_right = panel.evaluate('e=>e.getBoundingClientRect().left + e.clientWidth')
        assert abs(viewport_right - fifth_column['x']) < 3
        expect(panel.locator('.radar-table-name')).to_have_count(0)
    else:
        assert names[:2] == ['자산 / 티커', '26주 수익률'], names
        assert '관심' in names and not any('30주' in name for name in names)
        assert rows.first.locator('.radar-table-name').inner_text().strip()
    symbols = rows.evaluate_all('(es,s)=>es.map(e=>e.querySelector(s).textContent.trim())', ticker_selector)
    assert all(re.fullmatch(r'[A-Za-z0-9._/-]+', s) for s in symbols), symbols
    sizes = rows.evaluate_all('es=>es.map(e=>e.getBoundingClientRect().height)')
    low, high = (30, 34) if stock else (44, 48)
    assert all(low <= height <= high for height in sizes), sizes[:3]
    # Chromium 158 serializes flex-start as flow-start in computed styles.
    ticker = rows.first.locator(ticker_pick)
    justify = ticker.evaluate('e=>getComputedStyle(e).justifyContent')
    assert justify in ('flex-start', 'flow-start'), justify
    assert ticker.locator('p').evaluate('e=>getComputedStyle(e).textAlign') == 'left'
    assert ticker.evaluate('''e=>{
      const p=e.querySelector('p'),range=document.createRange();range.selectNodeContents(p);
      return Math.abs(range.getBoundingClientRect().left-e.getBoundingClientRect().left-10)<2;
    }'''), 'Ticker glyphs must align with the left cell padding'
    assert header.locator('button[kind]:visible p').evaluate_all('es=>es.every(e=>e.scrollWidth<=e.clientWidth+1)')
    assert panel.locator('.radar-table-number').evaluate_all('es=>es.every(e=>getComputedStyle(e).textAlign==="right")')
    alignment = page.evaluate('''key=>{
      const p=document.querySelector(`.st-key-${key}_compact_list`);
      const h=p.querySelector('[class*="_table_header"].stHorizontalBlock');
      const r=p.querySelector('[class*="_table_row_"].stHorizontalBlock');
      return [...h.children].every((c,i)=>Math.abs(c.getBoundingClientRect().x-r.children[i].getBoundingClientRect().x)<1);
    }''', state_key)
    assert alignment
    outer = page.locator('[data-testid=stMain]').evaluate('e=>e.scrollTop')
    dimensions = panel.evaluate('e=>({w:e.clientWidth,sw:e.scrollWidth,h:e.clientHeight,sh:e.scrollHeight})')
    assert dimensions['sw'] > dimensions['w'], dimensions
    panel.evaluate('e=>{e.scrollLeft=160;e.scrollTop=Math.min(68,e.scrollHeight-e.clientHeight);}')
    page.wait_for_timeout(200)
    p = panel.bounding_box()
    h = header.bounding_box()
    first_header = header.locator('button[kind]:visible').first.bounding_box()
    assert abs(h['y'] - (p['y']+1)) < 2, (p,h)
    assert abs(first_header['x'] - (p['x']+1)) < 2, (p,first_header)
    assert abs(page.locator('[data-testid=stMain]').evaluate('e=>e.scrollTop')-outer) < 3
    panel.evaluate('e=>{e.scrollTop=0;e.scrollLeft=0;}')
    chart = page.locator(f'.st-key-{chart_key} .js-plotly-plot')
    wait_chart(page, chart_key)
    selected = chart.evaluate('e=>e.layout.meta.asset_symbol')
    check_chart_controls(page.locator(f'.st-key-{chart_key}_asset_card'))
    settle_native_ui(page)
    header.get_by_role('button', name=ticker_title, exact=True).click()
    expect(header.get_by_role('button', name=f'{ticker_title} ↑', exact=True)).to_be_visible(timeout=60000)
    settle_native_ui(page)
    page.wait_for_function('''([key,selector])=>{
      const a=[...document.querySelectorAll(`.st-key-${key}_compact_list [class*="_table_row_"].stHorizontalBlock`)]
        .map(r=>r.querySelector(selector).textContent.trim());
      return a.join('|')===[...a].sort().join('|');
    }''', arg=[state_key, ticker_selector])
    wait_chart(page, chart_key, selected)
    header.get_by_role('button', name=f'{ticker_title} ↑', exact=True).click()
    expect(header.get_by_role('button', name=f'{ticker_title} ↓', exact=True)).to_be_visible(timeout=60000)
    settle_native_ui(page)
    page.wait_for_function('''([key,selector])=>{
      const a=[...document.querySelectorAll(`.st-key-${key}_compact_list [class*="_table_row_"].stHorizontalBlock`)]
        .map(r=>r.querySelector(selector).textContent.trim());
      return a.join('|')===[...a].sort().reverse().join('|');
    }''', arg=[state_key, ticker_selector])
    header.get_by_role('button', name='26주 수익률', exact=True).click()
    expect(header.get_by_role('button', name='26주 수익률 ↓', exact=True)).to_be_visible(timeout=60000)
    settle_native_ui(page)
    if check_star:
        row = rows.filter(has=page.locator('button[kind="secondary"]')).first
        target = row.locator(ticker_pick).inner_text().strip()
        if target == selected:
            row = rows.nth(1)
        star = row.locator('[class*="_table_star_"] button[kind]:visible')
        previous = star.get_attribute('kind')
        star.click()
        expect(star).to_have_attribute('kind', 'secondary' if previous == 'primary' else 'primary', timeout=30000)
        wait_chart(page, chart_key, selected)
        star.click()
        expect(star).to_have_attribute('kind', previous, timeout=30000)
        wait_chart(page, chart_key, selected)
    # Non-button cells select the same row, independently from its star.
    row = rows.nth(min(1, len(symbols)-1))
    target = row.locator(ticker_pick).inner_text().strip()
    row.locator('.radar-table-number').first.click()
    page.wait_for_function('''({key,target})=>document.querySelector(`.st-key-${key} .js-plotly-plot`)?.layout?.meta?.asset_symbol===target''',
                           arg={'key':chart_key, 'target':target})
    assert abs(page.locator('[data-testid=stMain]').evaluate('e=>e.scrollTop')-outer) < 3
    panel.scroll_into_view_if_needed()
    page.screenshot(path=str(output/f'{state_key}-ticker-table.png'))
    return {'columns':names, 'rows':len(symbols), 'row_height':sizes[0],
            'horizontal_scroll':True, 'sticky_header_and_ticker':True,
            'sort_preserves_chart':True, 'row_click':True, 'independent_star':check_star}
