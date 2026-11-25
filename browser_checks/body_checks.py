"""Check body geometry as well as the shared shell on rendered analysis tabs."""
from playwright.sync_api import expect


def check_analysis_body(page, area):
    body = page.locator('.st-key-analysis_body')
    expect(body.locator('.analysis-heading h2')).to_have_count(1)
    if area == 'favorites':
        return
    overview = '.analysis-summary'
    if area == 'markets':
        overview += ', .st-key-global_market_overview'
    expect(body.locator(overview)).to_have_count(1)
    if area not in ('stage2', 'sectors', 'stocks'):
        return
    panel = body.locator('[class*="_compact_list"].stVerticalBlock')
    if not panel.count():  # Actual empty operating stock universe is valid.
        return
    table, chart = panel.bounding_box(), body.locator('[class*="_asset_card"].stVerticalBlock').first.bounding_box()
    assert table['y'] < 470, table
    if area == 'stocks':
        card = body.locator('.st-key-stocks_list_card').bounding_box()
        assert card['width'] < chart['width'] and abs(card['y']-chart['y']) < 2, (card, chart)
        assert abs(card['height']-chart['height']) < 2, (card, chart)
        expect(panel.locator('.radar-table-name')).to_have_count(0)
    else:
        assert table['width'] >= chart['width'], (table, chart)
        assert abs(table['y'] - chart['y']) <= 12, (table, chart)
        expect(panel.locator('.radar-table-name').first).to_be_visible()
    # Primary filters occupy one row on desktop.
    fields = (['후보 유형', '자산 영역', '후보 검색', '후보 정렬'] if area == 'stage2'
              else ['국가 / 시장', '그룹 / 업종', 'Stage 필터', '종목명 / 심볼 검색'])
    positions = [body.get_by_label(label, exact=True).bounding_box()['y'] for label in fields]
    assert max(positions) - min(positions) < 4, positions
