"""Build deterministic figures by executing the app's actual chart code."""
import ast
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def chart_case(case, bars=220):
    app = Path(__file__).resolve().parents[1] / 'app.py'
    tree = ast.parse(app.read_text())
    names = {'configure_price_volume_hover', 'make_price_chart'}
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    dates = pd.date_range(end='2026-10-23', periods=bars, freq='B' if case == 'daily' else 'W-FRI')
    close = 100 + np.arange(bars) * .2 + np.sin(np.arange(bars) / 5)
    frame = pd.DataFrame(dict(date=dates, symbol='TEST', open=close-.3, high=close+1,
                              low=close-1, close=close, volume=1000+np.arange(bars)*10))
    frame['ma30'] = frame.close.rolling(30).mean()
    namespace = dict(pd=pd, go=go, make_subplots=make_subplots, prices=frame,
                     weekly_by_symbol={'TEST': frame})
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(app), 'exec'), namespace)
    if case != 'review':
        fig = namespace['make_price_chart']('TEST', compact=case == 'compact',
                                          period_is_weekly=case != 'daily',
                                          chart_period='일봉' if case == 'daily' else '주봉')
    else:
        # Execute the nested review chart's construction block, including its
        # real layout and hover configuration, without loading live providers.
        render = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                      and n.name == 'render_pending_candidate_chart_explorer')
        block = next(n.body for n in ast.walk(render) if isinstance(n, ast.With)
                     and any(isinstance(s, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'fig'
                             for t in s.targets) for s in n.body))
        start = next(i for i, n in enumerate(block) if isinstance(n, ast.Assign)
                     and any(isinstance(t, ast.Name) and t.id == 'fig' for t in n.targets))
        end = next(i for i, n in enumerate(block) if isinstance(n, ast.Expr)
                   and isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Attribute)
                   and n.value.func.attr == 'plotly_chart')
        frame['change_pct'] = frame.close.pct_change() * 100
        namespace.update(chart_data=frame, ma=frame.ma30, ma_name='30주 이동평균',
                         period='주봉', selected='TEST', labels={'TEST': 'TEST'})
        exec(compile(ast.Module(body=block[start:end], type_ignores=[]), str(app), 'exec'), namespace)
        fig = namespace['fig']
    fig.update_layout(title_text=case)
    return fig
