from types import SimpleNamespace
from unittest.mock import Mock

from private_analysis_access import (VERIFIED_PRIVATE_HOST, KIS_MODE,
    private_analysis_deployment, protected_download, management_table, chart_config)


def test_only_preverified_private_deployment_can_skip_analysis_password():
    for url in (f'https://{VERIFIED_PRIVATE_HOST}/', f'https://{VERIFIED_PRIVATE_HOST}/~/+/'):
        assert private_analysis_deployment(SimpleNamespace(context=SimpleNamespace(url=url)))


def test_other_or_missing_context_retains_analysis_lock():
    for url in (
        'http://localhost:8501', 'https://other.streamlit.app/',
        f'http://{VERIFIED_PRIVATE_HOST}/', f'https://{VERIFIED_PRIVATE_HOST}.evil.test/',
        f'https://user@{VERIFIED_PRIVATE_HOST}/', f'https://{VERIFIED_PRIVATE_HOST}:8443/',
        f'https://{VERIFIED_PRIVATE_HOST}/unverified/', None,
    ):
        assert not private_analysis_deployment(SimpleNamespace(context=SimpleNamespace(url=url)))
    assert not private_analysis_deployment(SimpleNamespace())


def test_locked_analysis_never_registers_download_payload_or_raw_frame():
    st = SimpleNamespace(session_state={'data_source_mode': KIS_MODE},
                         download_button=Mock(), dataframe=Mock())
    assert protected_download(st, 'export', b'private raw data') is False
    assert management_table(st, [{'raw': 'private'}]) is None
    st.download_button.assert_not_called()
    st.dataframe.assert_not_called()
    assert chart_config(st, scrollZoom=True)['modeBarButtonsToRemove'] == ['toImage']
    st.session_state['kis_authenticated'] = True
    protected_download(st, 'export', b'private raw data')
    management_table(st, [{'raw': 'private'}])
    st.download_button.assert_called_once()
    st.dataframe.assert_called_once()
    assert 'modeBarButtonsToRemove' not in chart_config(st, scrollZoom=True)


def test_demo_exports_and_tables_keep_existing_behavior():
    st = SimpleNamespace(session_state={'data_source_mode': '가상 데모'},
                         download_button=Mock(), dataframe=Mock())
    protected_download(st, 'demo', b'synthetic')
    management_table(st, [{'synthetic': True}])
    st.download_button.assert_called_once()
    st.dataframe.assert_called_once()


def test_source_mode_switch_cannot_unlock_private_host_operations():
    for mode in ('가상 데모', 'CSV 업로드'):
        st = SimpleNamespace(session_state={'data_source_mode': mode},
            context=SimpleNamespace(url=f'https://{VERIFIED_PRIVATE_HOST}/~/+/'),
            download_button=Mock(), dataframe=Mock())
        protected_download(st, 'previous management export', b'private')
        management_table(st, [{'previously_collected': True}])
        st.download_button.assert_not_called()
        st.dataframe.assert_not_called()
        assert chart_config(st)['modeBarButtonsToRemove'] == ['toImage']


def test_private_analysis_survives_wrong_password_and_management_relock(monkeypatch):
    from pathlib import Path
    import streamlit as st
    from streamlit.testing.v1 import AppTest
    root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(root)
    monkeypatch.setattr('private_analysis_access.private_analysis_deployment', lambda st: True)
    def deny(*args, **kwargs):
        raise AssertionError('Analysis/management unlock must not call a provider')
    monkeypatch.setattr('requests.sessions.Session.request', deny)
    st.cache_data.clear()
    app = AppTest.from_file(str(root/'app.py'), default_timeout=60)
    app.secrets['APP_PASSWORD'] = 'synthetic-operations-password'
    app.run()
    assert not app.exception
    assert app.radio(key='data_source_mode').value == KIS_MODE
    assert app.radio(key='analysis_navigation_choice')
    assert not app.get('download_button')
    assert not app.dataframe
    assert not app.get('file_uploader')
    app.radio(key='data_source_mode').set_value('CSV 업로드').run()
    assert not app.exception
    assert not app.get('file_uploader')
    assert not app.get('download_button')
    app.radio(key='data_source_mode').set_value(KIS_MODE).run()
    next(w for w in app.text_input if w.label == 'KIS 모드 비밀번호').set_value('wrong')
    next(w for w in app.button if w.label == '잠금 해제').click().run()
    assert not app.exception
    assert not app.session_state['kis_authenticated']
    assert any('비밀번호가 일치하지 않습니다' in e.value for e in app.error)
    assert not app.get('download_button')
    next(w for w in app.text_input if w.label == 'KIS 모드 비밀번호').set_value('synthetic-operations-password')
    next(w for w in app.button if w.label == '잠금 해제').click().run()
    assert not app.exception
    assert app.session_state['kis_authenticated']
    assert any(w.label == 'KIS에서 가격 조회' for w in app.button)
    assert app.get('file_uploader')
    assert app.get('download_button')
    next(w for w in app.button if w.label == 'KIS 모드 잠그기').click().run()
    assert not app.exception
    assert not app.session_state['kis_authenticated']
    assert app.radio(key='analysis_navigation_choice')
    assert not app.get('download_button')
    assert not app.dataframe
    assert not app.get('file_uploader')
    st.cache_data.clear()


def test_private_host_does_not_inherit_the_old_all_access_session(monkeypatch):
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(root)
    monkeypatch.setattr('private_analysis_access.private_analysis_deployment', lambda st: True)
    app = AppTest.from_file(str(root/'app.py'), default_timeout=60)
    app.secrets['APP_PASSWORD'] = 'synthetic-operations-password'
    app.session_state['data_source_mode'] = KIS_MODE
    app.session_state['kis_authenticated'] = True
    app.run()
    assert not app.exception
    assert not app.session_state['kis_authenticated']
    assert app.radio(key='analysis_navigation_choice')
    assert not app.get('file_uploader')
    assert not app.get('download_button')


def test_unverified_host_still_stops_before_any_kis_analysis(monkeypatch):
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(root)
    monkeypatch.setattr('private_analysis_access.private_analysis_deployment', lambda st: False)
    app = AppTest.from_file(str(root/'app.py'), default_timeout=60)
    app.secrets['APP_PASSWORD'] = 'synthetic-operations-password'
    app.session_state['data_source_mode'] = KIS_MODE
    # Query preferences may select a source, but never grant either privilege.
    app.query_params['radar'] = '{"source":"KIS API · 미국·한국","kis_authenticated":true,"private_analysis":true}'
    app.run()
    assert not app.exception
    assert [w for w in app.text_input if w.label == 'KIS 모드 비밀번호']
    assert not [w for w in app.radio if w.key == 'active_analysis_area']
    assert not app.get('plotly_chart')
    assert not app.get('download_button')
