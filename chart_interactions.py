"""Browser-only interactions shared by existing native Streamlit Plotly charts."""
from pathlib import Path
import json
import streamlit.components.v2 as components
from plotly.offline import get_plotlyjs

# Bundle locally: no CDN, provider request or injected user content.
_interactions = components.component(
    'price_chart_interactions',
    js=get_plotlyjs() + '\n' + Path(__file__).with_suffix('.js').read_text(),
)


def mount_chart_interactions():
    release = json.loads(Path(__file__).with_name('release_info.json').read_text())
    _interactions(key='price_chart_interactions', data={'release': release['version']})
