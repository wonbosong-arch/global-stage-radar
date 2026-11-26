"""Real native sidebar clicks and common visual contracts on every analysis tab."""
from playwright.sync_api import expect


def check_shared_shell(page, output, *, reload=True):
    nav = page.locator('.st-key-analysis_navigation')
    sidebar = page.locator('[data-testid=stSidebar]')
    close = page.get_by_role('button', name='Collapse sidebar', exact=True)
    expand = page.get_by_role('button', name='Expand sidebar', exact=True)
    areas = {'대시보드':'briefing', 'Stage 2 후보':'stage2', '국가 및 원자재':'markets_commodities',
             '업종':'sectors', '종목':'stocks', '차트 비교':'chart_comparison', '관심 목록':'favorites'}
    def settle(label):
        # The first direct stock-tab entry may cold-replay 2,335 stored US
        # research histories; the existing full-suite limit is 20 minutes.
        # Do not mistake a visible progress spinner for a failed navigation.
        page.wait_for_function('''area=>{try{return JSON.parse(new URL(location.href).searchParams.get('radar')).tab===area;}catch{return false;}}''',
                               arg=areas[label], timeout=180000)
        page.wait_for_function('''()=>document.querySelector('[data-testid=stApp]')?.getAttribute('data-test-script-state')==='notRunning'
          && !document.querySelector('[data-stale=true]')''', timeout=60000)
        page.wait_for_timeout(350)  # Native sidebar transition and final chart paint.
    evidence = []
    for width in (1440, 800, 390):
        page.set_viewport_size({'width': width, 'height': 1000})
        page.wait_for_timeout(400)
        # Opening through the actual native control must work after resizing too.
        if expand.is_visible():
            expand.click()
            page.wait_for_timeout(400)
        page.mouse.move(100, 110)
        expect(close).to_be_visible()
        close.click()
        expect(expand).to_be_visible()
        settle('대시보드')
        page.screenshot(path=str(output / f'shell-collapsed-{width}.png'))
        for label in ('Stage 2 후보', '업종', '대시보드'):
            item = nav.get_by_role('radio', name=label, exact=True)
            nav.get_by_text(label, exact=True).click()
            expect(item).to_be_checked()
            settle(label)
            expect(expand).to_be_visible()
            expect(page.locator('[data-testid=stException]')).to_have_count(0)
        # A full app rerun/reload must not strand the collapsed navigation.
        if reload:
            page.reload(wait_until='domcontentloaded')
            expect(nav).to_be_visible(timeout=60000)
        if close.is_visible():
            close.click()
        expect(expand).to_be_visible()
        expand.click()
        expect(close).to_be_visible()
        expect(sidebar).to_be_visible()
        settle('대시보드')
        # Expanded mobile navigation must sit above the native sidebar overlay.
        for label in ('업종', '대시보드'):
            nav.get_by_text(label, exact=True).click()
            settle(label)
        page.screenshot(path=str(output / f'shell-restored-{width}.png'))
        evidence.append({'width': width, 'collapse_navigation_restore': True, 'reload': reload})
    page.set_viewport_size({'width': 1440, 'height': 1000})
    snapshots = []
    for key, label in (('briefing', '대시보드'), ('stage2', 'Stage 2 후보'),
                       ('markets', '국가 및 원자재'), ('sectors', '업종'),
                       ('stocks', '종목'), ('chart_comparison', '차트 비교'), ('favorites', '관심 목록')):
        item = nav.get_by_role('radio', name=label, exact=True)
        nav.get_by_text(label, exact=True).click()
        expect(item).to_be_checked()
        settle(label)
        expect(page.locator('.briefing-brand')).to_be_visible()
        expect(page.locator('.st-key-briefing_search')).to_be_visible()
        page.wait_for_function("""()=>{
          const h=document.querySelector('.st-key-analysis_header')?.getBoundingClientRect();
          const n=document.querySelector('.st-key-analysis_navigation')?.getBoundingClientRect();
          return h&&n&&h.height===65&&n.x===12&&n.width===159;
        }""")
        page.locator('[data-testid=stMain]').evaluate('e=>e.scrollTop=0')
        tokens = page.evaluate("""()=>{
          const rect=s=>{const r=document.querySelector(s).getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height}};
          const css=s=>getComputedStyle(document.querySelector(s));
          return {header:rect('.st-key-analysis_header'),nav:rect('.st-key-analysis_navigation'),
                  sidebar:rect('[data-testid=stSidebar]'),font:css('.stApp').fontFamily,
                  sidebarColor:css('[data-testid=stSidebar]').backgroundColor,
            canvas:css('[data-testid=stAppViewContainer]').backgroundColor,
            mainPadding:css('.stMainBlockContainer').paddingLeft};
        }""")
        assert tokens['sidebar']['width'] == 184, tokens
        assert tokens['sidebarColor'] == 'rgb(39, 54, 75)', tokens
        assert tokens['mainPadding'] == '28px', tokens
        assert page.locator('[data-testid=stMain]').evaluate('e=>e.scrollWidth') <= 1441
        if snapshots:
            assert tokens == snapshots[0]['tokens'], (key, tokens, snapshots[0])
        if key == 'favorites':
            assert nav.evaluate("""nav => {
                const items = [...nav.querySelectorAll('label')];
                const [comparison, favorites] = items.slice(-2);
                const icons = [comparison, favorites].map(item => getComputedStyle(item, '::before').backgroundImage);
                return comparison.textContent.trim() === '차트 비교'
                    && favorites.textContent.trim() === '관심 목록'
                    && icons.every(icon => icon.startsWith('url(')) && icons[0] !== icons[1];
            }""")
        if key not in ('briefing', 'chart_comparison'):
            from body_checks import check_analysis_body
            check_analysis_body(page, key)
        page.screenshot(path=str(output / f'shell-{key}-1440.png'))
        snapshots.append({'tab': key, 'tokens': tokens})
    nav.get_by_text('대시보드', exact=True).click()
    expect(page.locator('.st-key-weekly_briefing')).to_be_visible()
    settle('대시보드')
    return {'responsive_toggle': evidence, 'tabs': snapshots}


if __name__ == '__main__':
    import check_dashboard_navigation as runner
    def exercise(page, base, output):
        page.route('**/*', lambda route: route.continue_()
                   if route.request.url.startswith(base + '/') else route.abort())
        page.goto(base, wait_until='domcontentloaded')
        expect(page.locator('.st-key-analysis_navigation')).to_be_visible(timeout=60000)
        return check_shared_shell(page, output)
    runner.exercise = exercise
    runner.main()
