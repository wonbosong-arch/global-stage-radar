"""Local prototype assets; no remote requests or new UI runtime."""
from base64 import b64encode
from functools import lru_cache
from pathlib import Path


@lru_cache
def asset_url(name, color=None):
    path = Path(__file__).with_name('briefing_assets') / name
    mime = 'image/png' if path.suffix == '.png' else 'image/svg+xml'
    data = path.read_bytes()
    if color and path.suffix == '.svg':
        data = data.replace(b'#607898', color.encode('ascii'))
    return f'data:{mime};base64,' + b64encode(data).decode('ascii')


def icon(name):
    colors = {'GlobeHemisphereWest':'#3978ed', 'Factory':'#6979d8', 'ChartBar':'#dfa026', 'Star':'#dfa026'}
    return f'<img class="briefing-icon" alt="" src="{asset_url(name + ".svg", colors.get(name))}">'


@lru_cache
def font_styles():
    """Reuse only the prototype's Latin and briefing Korean font subsets."""
    import json
    root = Path(__file__).with_name('briefing_assets') / 'fonts'
    rules = []
    for entry in json.loads((root / 'index.json').read_text(encoding='utf-8')):
        data = b64encode((root / entry['file']).read_bytes()).decode('ascii')
        rules.append('@font-face{font-family:"Noto Sans KR";font-style:normal;font-display:swap;'
                     f'font-weight:{entry["weight"]};src:url(data:font/woff2;base64,{data}) format("woff2");'
                     f'unicode-range:{entry["unicode"]};}}')
    return ''.join(rules)
