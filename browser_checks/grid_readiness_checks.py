"""Deterministic Chromium regression for intermediate and broken footer layouts."""
from grid_checks import assert_footer


def check_grid_readiness(browser):
    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
    try:
        page.set_content('''<style>
          .st-key-fixture_grid_pager {width:260px;margin:auto;display:flex;align-items:center;gap:8px}
          .column {flex:1} .info {flex:2;text-align:center}
          button {width:100%;height:40px}
        </style>
        <div class="st-key-fixture_grid_canvas">
          <div data-testid="stPlotlyChart" style="height:100px">
            <div class="js-plotly-plot"></div><div class="radar-price-scale"></div>
          </div>
        </div>
        <div class="st-key-fixture_grid_pager">
          <div class="column"><div class="st-key-fixture_grid_prev"><button disabled>‹</button></div>
            <div data-stale="true" style="height:170px">previous list</div></div>
          <div class="info" data-testid="stCaptionContainer">1 / 1</div>
          <div class="column st-key-fixture_grid_next"><button disabled>›</button></div>
        </div>''')
        page.evaluate('''()=>{
          setTimeout(()=>document.querySelector('[data-stale]').remove(),350);
          setTimeout(()=>{
            const g=document.querySelector('.js-plotly-plot');
            g._fullLayout={};g._fullData=[{type:'candlestick'}];
          },600);
        }''')
        assert assert_footer(page, 'fixture') == (1, 1)
        assert page.locator('[data-stale]').count() == 0
        assert page.locator('.js-plotly-plot').evaluate('g=>!!g._fullLayout')
        # A settled but genuinely misaligned footer must still fail immediately.
        page.locator('.st-key-fixture_grid_next').evaluate("e=>e.style.transform='translateY(30px)'")
        try:
            assert_footer(page, 'fixture')
        except AssertionError:
            pass
        else:
            raise AssertionError('A permanent footer misalignment was accepted')
        return {'delayed_stale_cleanup': True, 'delayed_plotly_init': True,
                'permanent_misalignment_rejected': True}
    finally:
        page.close()
