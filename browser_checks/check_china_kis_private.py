"""Opt-in localhost KIS Stage journey; no provider requests or publication."""
import check_dashboard_navigation as nav
from playwright.sync_api import expect
from table_checks import wait_chart


def exercise(page, base, output):
    page.route('**/*', lambda route: route.continue_()
               if route.request.url.startswith(base + '/') else route.abort())
    page.goto(base, wait_until='domcontentloaded')
    nav.click(page.get_by_text('KIS API · 미국·한국', exact=True))
    page.get_by_label('KIS 모드 비밀번호', exact=True).fill(nav.TEST_PASSWORD)
    nav.click(page.get_by_role('button', name='잠금 해제', exact=True))
    header = page.locator('.st-key-analysis_navigation')
    nav.click(header.get_by_text('업종', exact=True))
    nav.click(page.get_by_text('중국 본토 SSE · 연구·관찰 12종', exact=True))
    wait_chart(page, 'china_research_selected_chart', '512800')
    for period in ('일봉', '주봉'):
        nav.click(page.locator('.st-key-china_research_selected_chart_asset_card').get_by_text(period, exact=True))
        wait_chart(page, 'china_research_selected_chart', '512800')
    nav.click(page.locator('.st-key-china_research_pick_512400 button'))
    wait_chart(page, 'china_research_selected_chart', '512400')
    page.screenshot(path=str(output / 'kis-512400-private.png'))
    nav.click(page.get_by_text('3×3 차트', exact=True).last)
    expect(page.locator('[class*="st-key-china_research_grid_"][class*="_asset_card"]')).to_have_count(9)
    next_button = page.locator('.st-key-china_research_grid_next button:visible')
    next_button.scroll_into_view_if_needed()
    page.wait_for_timeout(300)
    scroll_before = page.evaluate('()=>document.querySelector("[data-testid=stMain]").scrollTop')
    nav.click(next_button)
    expect(page.locator('[class*="st-key-china_research_grid_"][class*="_asset_card"]')).to_have_count(3)
    wait_chart(page, 'china_research_grid_512400', '512400')
    page.wait_for_timeout(2800)
    scroll_after = page.evaluate('()=>document.querySelector("[data-testid=stMain]").scrollTop')
    assert abs(scroll_after - scroll_before) < 3, (scroll_before, scroll_after)
    for width in (1440, 800, 390):
        page.set_viewport_size({'width': width, 'height': 1000})
        page.wait_for_timeout(400)
        assert page.evaluate('()=>document.querySelector("[data-testid=stMain]").scrollWidth') <= width + 1
        page.screenshot(path=str(output / f'kis-grid-private-{width}.png'))
    page.set_viewport_size({'width': 1440, 'height': 1000})
    nav.click(page.get_by_text('중국 Stage2 후보만 표시', exact=True))
    expect(page.locator('[class*="st-key-china_research_grid_"][class*="_asset_card"]')).to_have_count(2)
    nav.click(header.get_by_text('Stage 2 후보', exact=True))
    nav.click(header.get_by_text('업종', exact=True))
    expect(page.locator('[class*="st-key-china_research_grid_"][class*="_asset_card"]')).to_have_count(2)
    nav.click(page.get_by_text('중국 Stage2 후보만 표시', exact=True))
    nav.click(page.get_by_text('차트 고정 목록', exact=True).last)
    wait_chart(page, 'china_research_selected_chart', '512400')
    assert not page.locator('[data-testid=stException]').count()
    return dict(private_kis=True, grid_pages=[9, 3], stage2_filter=2,
                chart_512400=True, widths=[1440, 800, 390],
                paging_scroll_delta_px=scroll_after - scroll_before,
                operational_activation=False)


if __name__ == '__main__':
    nav.exercise = exercise
    nav.main()
