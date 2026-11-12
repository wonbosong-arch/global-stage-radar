"""Separate verified private-host analysis from password-protected operations.

Community Cloud's private-app gateway is the authentication boundary. The URL
below selects the one deployment whose Sharing settings, sole owner, and fresh
anonymous-session rejection were verified on 2026-11-12. A hostname is NOT an
identity claim. Keep that deployment private; re-verify access before changing
this allowlist or hosting. Other deployments and local runs retain the lock.
"""
from urllib.parse import urlsplit

KIS_MODE = "KIS API · 미국·한국"
VERIFIED_PRIVATE_HOST = "global-stage-radar-kmb524zemj5vawb3ipampm.streamlit.app"


def private_analysis_deployment(st):
    """Fail closed when the verified deployment context is absent or different."""
    try:
        url = urlsplit(st.context.url)
        return (url.scheme == "https" and url.hostname == VERIFIED_PRIVATE_HOST
                and url.port in (None, 443) and url.username is None
                and url.password is None and url.path.rstrip("/") in ("", "/~/+"))
    except (AttributeError, KeyError, RuntimeError, TypeError, ValueError):
        return False


def management_unlocked(st):
    # This server-session flag is set only by the existing APP_PASSWORD form.
    # Never copy it from URLs, browser storage, or the private-deployment check.
    return bool(st.session_state.get("kis_authenticated", False))


def kis_read_only(st):
    return (st.session_state.get("data_source_mode") == KIS_MODE
            and not management_unlocked(st))


def protected_download(st, *args, **kwargs):
    """Do not create a media payload/URL while operations are locked."""
    if kis_read_only(st):
        return False
    return st.download_button(*args, **kwargs)


def management_table(st, *args, **kwargs):
    """Do not serialize raw review/management frames to an analysis session."""
    if kis_read_only(st):
        return None
    return st.dataframe(*args, **kwargs)


def chart_config(st, **config):
    if kis_read_only(st):
        config["modeBarButtonsToRemove"] = list(dict.fromkeys(
            [*config.get("modeBarButtonsToRemove", []), "toImage"]))
    return config
