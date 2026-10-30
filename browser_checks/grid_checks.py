"""Actual nine-chart scales, per-period overrides and compact footer paging."""
import json
import re

from playwright.sync_api import expect


SNAPSHOT = '''prefix=>[...document.querySelectorAll(`.st-key-${prefix}_grid_canvas [data-testid=stPlotlyChart]`)].map(e=>{
  const g=e.querySelector('.js-plotly-plot'), c=g?._fullData?.find(t=>t.type==='candlestick');
  const ma=g?._fullData?.find(t=>t.name==='30주 이동평균'||t.name==='50일 이동평균');
  return {symbol:g?.layout?.meta?.asset_symbol,period:c?.name,
    scale:(e.closest('[class*="_asset_card"]')||e).querySelector('.radar-price-scale')?.value,axis:g?._fullLayout?.yaxis?.type,
    volume:g?._fullLayout?.yaxis2?.type,ma:ma?.name,shared:ma?.yaxis===c?.yaxis};
})'''


def pager_button(page, prefix, forward):
    return page.locator(f'.st-key-{prefix}_grid_{"next" if forward else "prev"}').get_by_role(
        'button',name='›' if forward else '‹',exact=True)


def wait_axes(page, prefix, expected):
    try:
        page.wait_for_function('''({prefix,expected})=>{
          const rows=('''+SNAPSHOT+''')(prefix);
          return rows.length===Object.keys(expected).length && rows.every(r=>{
            const wanted=expected[r.symbol];
            return wanted && r.period===wanted[0] && r.scale===wanted[1] && r.axis===wanted[1]
              && r.volume==='linear' && r.shared
              && r.ma===(r.period==='주봉'?'30주 이동평균':'50일 이동평균');});
        }''', arg={'prefix':prefix,'expected':expected}, timeout=30000)
    except Exception:
        print('::error::Grid axes '+json.dumps(page.evaluate(SNAPSHOT,prefix),ensure_ascii=False),flush=True)
        raise


def assert_footer(page, prefix):
    footer=page.locator(f'.st-key-{prefix}_grid_pager')
    prev=pager_button(page,prefix,False)
    next_=pager_button(page,prefix,True)
    expect(prev).to_have_text('‹')
    expect(next_).to_have_text('›')
    text=footer.locator('[data-testid=stCaptionContainer]').inner_text().strip()
    assert re.fullmatch(r'\d+ / \d+',text),text
    current,total=map(int,text.split(' / '))
    assert prev.is_disabled()==(current==1)
    assert next_.is_disabled()==(current==total)
    footer.scroll_into_view_if_needed()
    last=page.locator(f'.st-key-{prefix}_grid_canvas [data-testid=stPlotlyChart]').last.bounding_box()
    box=footer.bounding_box()
    assert box['y']>=last['y']+last['height']-1,(box,last)
    a,b=prev.bounding_box(),next_.bounding_box()
    assert abs(a['y']-b['y'])<2,(a,b)
    assert abs((a['x']+a['width']+b['x'])/2-(box['x']+box['width']/2))<4
    return current,total


def check_grid_defaults(page, prefix, count):
    charts=page.locator(f'.st-key-{prefix}_grid_canvas [data-testid=stPlotlyChart]')
    expect(charts).to_have_count(count,timeout=30000)
    page.wait_for_function('''({prefix,count})=>{
      const plots=[...document.querySelectorAll(`.st-key-${prefix}_grid_canvas .js-plotly-plot`)];
      return plots.length===count && plots.every(g=>g._fullData?.some(t=>t.type==='candlestick'));}
    ''',arg={'prefix':prefix,'count':count})
    symbols=[row['symbol'] for row in page.evaluate(SNAPSHOT,prefix)]
    wait_axes(page,prefix,{s:['주봉','log'] for s in symbols})
    assert_footer(page,prefix)
    return symbols


def check_grid_scales(page, prefix, output):
    symbols=check_grid_defaults(page,prefix,9)
    expected={s:['주봉','log'] for s in symbols}
    wait_axes(page,prefix,expected)
    # Exercise each real period control; rerenders must not reset neighboring axes.
    for symbol in symbols:
        page.locator(f'.st-key-{prefix}_grid_period_{symbol}').get_by_text('일',exact=True).click()
        expected[symbol]=['일봉','linear']
        wait_axes(page,prefix,expected)
    first=symbols[0]
    def scale_for(symbol):
        key=f'{prefix}_grid_chart_{symbol}' if prefix=='candidate_quick' else f'{prefix}_grid_{symbol}'
        return page.locator(f'.st-key-{key}_asset_card .radar-price-scale')
    scale_for(first).select_option('log')
    expected[first]=['일봉','log']
    wait_axes(page,prefix,expected)
    for symbol in symbols:
        page.locator(f'.st-key-{prefix}_grid_period_{symbol}').get_by_text('주',exact=True).click()
        expected[symbol]=['주봉','log']
        wait_axes(page,prefix,expected)
    scale_for(first).select_option('linear')
    expected[first]=['주봉','linear']
    wait_axes(page,prefix,expected)
    current,total=assert_footer(page,prefix)
    assert current==1 and total>1
    scroll=lambda:page.evaluate('()=>document.querySelector("[data-testid=stMain]").scrollTop')
    before=scroll()
    pager_button(page,prefix,True).click()
    expect(page.locator(f'.st-key-{prefix}_grid_pager [data-testid=stCaptionContainer]')).to_have_text(f'2 / {total}',timeout=30000)
    page.wait_for_function('''({prefix,old})=>{
      const charts=[...document.querySelectorAll(`.st-key-${prefix}_grid_canvas .js-plotly-plot`)];
      return charts.length>0 && charts.every(g=>g._fullData && !old.includes(g.layout.meta.asset_symbol));}
    ''',arg={'prefix':prefix,'old':symbols})
    second={r['symbol']:['주봉','log'] for r in page.evaluate(SNAPSHOT,prefix)}
    wait_axes(page,prefix,second)
    page.wait_for_timeout(2700)
    delta=scroll()-before
    assert abs(delta)<3,delta
    pager_button(page,prefix,False).click()
    wait_axes(page,prefix,expected)
    page.wait_for_timeout(2700)
    assert abs(scroll()-before)<3,scroll()-before
    page.locator(f'.st-key-{prefix}_grid_period_{first}').get_by_text('일',exact=True).click()
    expected[first]=['일봉','log']
    wait_axes(page,prefix,expected)
    page.locator(f'.st-key-{prefix}_grid_period_{symbols[1]}').get_by_text('일',exact=True).click()
    expected[symbols[1]]=['일봉','linear']
    wait_axes(page,prefix,expected)
    for width in (1440,390):
        page.set_viewport_size({'width':width,'height':1000})
        page.wait_for_timeout(500)
        assert_footer(page,prefix)
        page.screenshot(path=str(output/f'{prefix}-grid-footer-{width}.png'))
    page.set_viewport_size({'width':1440,'height':1000})
    return {'weekly_defaults':9,'daily_defaults':9,'independent_manual_scales':True,'paging_scroll_delta_px':delta}
