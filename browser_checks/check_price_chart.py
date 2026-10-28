"""Run with Playwright installed; no provider access or application secrets needed."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.request import urlopen

from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--browser', help='Optional local Chromium executable')
    parser.add_argument('--output-dir', type=Path, default=Path('artifacts/chart-browser'))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    base = f'http://127.0.0.1:{port}'
    log = (args.output_dir / 'streamlit.log').open('w')
    server = subprocess.Popen([sys.executable, '-m', 'streamlit', 'run',
                               str(root / 'browser_checks/chart_fixture.py'),
                               '--server.address=127.0.0.1', f'--server.port={port}',
                               '--server.headless=true', '--browser.gatherUsageStats=false'],
                              cwd=root, stdout=log, stderr=subprocess.STDOUT)
    results = []
    try:
        for _ in range(120):
            try:
                with urlopen(base + '/_stcore/health', timeout=1) as response:
                    if response.status == 200:
                        break
            except OSError:
                time.sleep(.25)
        else:
            raise RuntimeError('Local chart fixture did not start')
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path=args.browser, headless=True,
                                                args=['--no-sandbox'])
            page = browser.new_page(viewport={'width': 1440, 'height': 1000})
            page.route('**/*', lambda route: route.continue_()
                       if route.request.url.startswith(base + '/') else route.abort())
            page.goto(base, wait_until='domcontentloaded')
            for case in ('weekly', 'daily', 'compact', 'review'):
                page.get_by_text(case, exact=True).first.click()
                try:
                    page.wait_for_function('(name)=>[...document.querySelectorAll(".js-plotly-plot")].some(e=>e._fullLayout && e.layout.title.text.replace(/<[^>]*>/g,"")===name)', arg=case)
                except Exception:
                    page.screenshot(path=str(args.output_dir / 'failure.png'))
                    (args.output_dir / 'failure.txt').write_text(page.locator('body').inner_text())
                    print('Figure readiness failed', case, page.locator('.js-plotly-plot').evaluate_all('(es)=>es.map(e=>({title:e.layout?.title,ready:!!e._fullLayout}))'))
                    raise
                chart = page.locator('.js-plotly-plot').first
                chart.scroll_into_view_if_needed()
                state = chart.evaluate('''e=>({x:e.data[0].x,
                    range:e._fullLayout.xaxis2.range, y:e._fullLayout.yaxis.range,
                    y2:e._fullLayout.yaxis2.range, fixed:[e._fullLayout.yaxis.fixedrange,e._fullLayout.yaxis2.fixedrange]})''')
                errors = []
                parse = lambda date: datetime.fromisoformat(str(date).replace('Z', '+00:00'))
                visible = sum(parse(state['range'][0]) <= parse(x) <= parse(state['range'][1]) for x in state['x'])
                if visible != 150:
                    errors.append(f'Expected 150 visible bars, got {visible}')
                if state['fixed'] != [True, True]:
                    errors.append('Vertical axes are not fixed')
                for index in (120, 180):
                    point = chart.evaluate('''(e,i)=>({x:e._fullLayout.xaxis2._offset+e._fullLayout.xaxis2.d2p(e.data[0].x[i]),
                        y:e._fullLayout.yaxis._offset+e._fullLayout.yaxis._length*.4,
                        bottom:e._fullLayout.yaxis2._offset+e._fullLayout.yaxis2._length})''', index)
                    box = chart.bounding_box()
                    page.mouse.move(box['x']+point['x'], box['y']+point['y'])
                    page.wait_for_timeout(150)
                    hover = chart.evaluate('''e=>(e._hoverdata||[]).filter(p=>p.data.type==='bar'||p.data.type==='candlestick'||p.data.name==='캔들 정보')
                        .map(p=>({type:p.data.type,name:p.data.name,point:p.pointNumber,x:p.x}))''')
                    if len(hover) != 2 or any(item['point'] != index for item in hover):
                        errors.append(f'OHLC/volume date mismatch at bar {index}: {hover}')
                    spikes = chart.locator('.spikeline').evaluate_all('(es)=>es.map(e=>Number(e.getAttribute("y2")))')
                    if not spikes or max(spikes) < point['bottom'] - 1:
                        errors.append(f'Crosshair stops before volume at bar {index}')
                    tooltip = chart.locator('.hoverlayer').text_content()
                    if not all(label in tooltip for label in ('시가', '고가', '저가', '종가', '전일/전주 대비', '거래량')):
                        errors.append('OHLC/change/volume hover information is missing')
                page.screenshot(path=str(args.output_dir / f'{case}.png'))
                # Real wheel interaction must zoom time without changing either price scale.
                page.mouse.wheel(0, -240)
                page.wait_for_timeout(400)
                zoomed = chart.evaluate('e=>({range:e._fullLayout.xaxis2.range,y:e._fullLayout.yaxis.range,y2:e._fullLayout.yaxis2.range})')
                if zoomed['range'] == state['range']:
                    errors.append('Wheel zoom did not change the time range')
                if zoomed['y'] != state['y'] or zoomed['y2'] != state['y2']:
                    errors.append('Wheel zoom changed a locked vertical scale')
                axis = chart.evaluate('''e=>({x:e._fullLayout.xaxis2._offset-15,
                    y:e._fullLayout.yaxis._offset+e._fullLayout.yaxis._length*.5})''')
                box = chart.bounding_box()
                page.mouse.move(box['x']+axis['x'], box['y']+axis['y'])
                page.mouse.down()
                page.mouse.move(box['x']+axis['x'], box['y']+axis['y']-60, steps=5)
                page.mouse.up()
                if chart.evaluate('e=>e._fullLayout.yaxis.range') != state['y']:
                    errors.append('Dragging the price axis changed its locked range')
                center = chart.evaluate('''e=>({x:e._fullLayout.xaxis2._offset+e._fullLayout.xaxis2._length*.5,
                    y:e._fullLayout.yaxis._offset+e._fullLayout.yaxis._length*.5})''')
                box = chart.bounding_box()
                page.mouse.move(box['x']+center['x'], box['y']+center['y'])
                page.mouse.down()
                page.mouse.move(box['x']+center['x']+60, box['y']+center['y'], steps=5)
                page.mouse.up()
                page.wait_for_timeout(150)
                if chart.evaluate('e=>e._fullLayout.xaxis2.range') == zoomed['range']:
                    errors.append('Horizontal drag did not pan the time axis')
                results.append({'case': case, 'visible_bars': visible, 'errors': errors})
            browser.close()
        (args.output_dir / 'results.json').write_text(json.dumps(results, indent=2, ensure_ascii=False))
        print(json.dumps(results, ensure_ascii=False))
        if any(result['errors'] for result in results):
            raise SystemExit(1)
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait()
        log.close()


if __name__ == '__main__':
    main()
