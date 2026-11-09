"""Authenticated, review-only Nasdaq panel with a private local-file mode."""
from __future__ import annotations

import csv
from datetime import date, datetime, timezone
import hashlib
import hmac
import json
from pathlib import Path

import pandas as pd

from nasdaq_github_store import GitHubStore
from nasdaq_single_source import build_report, check_local_manifest, private_path
from nasdaq_local_csv_review import read_table
from us_stage_mapping_expansion import INPUTS, fingerprint
from nasdaq_web_upload import clear_upload, render_public_upload, render_upload

STATE = "nasdaq_private_review_state"
AUTH = "nasdaq_private_review_auth"
MAX_CSV_BYTES = 20_000_000
MAX_MANIFEST_BYTES = 100_000
MAX_AGE_DAYS = 45
ROOT = Path(__file__).resolve().parent
PUBLIC_CONTEXT = "public_github_upload"


def enabled(env):
    return (env.get("NASDAQ_PRIVATE_REVIEW_ENABLED") == "1"
            and env.get("NASDAQ_PRIVATE_REVIEW_CONTEXT") in {"local_private", PUBLIC_CONTEXT})


def public_upload_enabled(env):
    return enabled(env) and env.get("NASDAQ_PRIVATE_REVIEW_CONTEXT") == PUBLIC_CONTEXT


def source_freshness(manifest, today):
    """Unknown dates remain unknown; filesystem mtime is never a source date."""
    stamp = manifest.get("source_as_of")
    if stamp:
        source_date = date.fromisoformat(stamp)
    elif manifest.get("downloaded_at_utc"):
        source_date = datetime.fromisoformat(manifest["downloaded_at_utc"].replace("Z", "+00:00")).date()
    else:
        return "unknown"
    age = (today - source_date).days
    if age < 0:
        raise ValueError("Future source/download date")
    if age > MAX_AGE_DAYS:
        raise ValueError("Source/download date is older than the review window")
    return "within_review_window"


def load_review(csv_path, manifest_path, data_dir, *, now=None):
    """Validate a complete replacement before the caller swaps session state.

    Both original CSV and manifest stay outside *every* Git checkout. The
    existing offline engine supplies identity, KIS cap/price/RS and Stage gates.
    No stored review JSON is trusted as an input and no output file is created.
    """
    now = now or datetime.now(timezone.utc)
    source, manifest_file = private_path(Path(csv_path)), private_path(Path(manifest_path))
    if source.stat().st_size > MAX_CSV_BYTES or manifest_file.stat().st_size > MAX_MANIFEST_BYTES:
        raise ValueError("Private input exceeds size limit")
    raw = source.read_bytes()
    manifest_raw = manifest_file.read_bytes()
    if len(raw) > MAX_CSV_BYTES or len(manifest_raw) > MAX_MANIFEST_BYTES:
        raise ValueError("Private input exceeds size limit")
    digest = hashlib.sha256(raw).hexdigest()
    manifest = json.loads(manifest_raw.decode("utf-8-sig"))
    if not isinstance(manifest, dict):
        raise ValueError("Manifest must be an object")
    aliases = manifest.get("symbol_aliases", [])
    if not isinstance(aliases, list) or any(not isinstance(entry, dict) for entry in aliases):
        raise ValueError("Alias declarations must be objects")
    check_local_manifest(manifest, digest, now)
    freshness = source_freshness(manifest, now.date())
    _, columns, rows = read_table(raw)
    required = {"Symbol", "Name", "Sector", "Industry", "Market Cap"}
    if not rows or not required.issubset(columns) or any(not row["Symbol"] or not row["Name"] for row in rows):
        raise ValueError("Nonempty screener CSV with required fields expected")
    data_dir = Path(data_dir)
    before = {name: fingerprint(data_dir / name) for name in INPUTS}
    report = build_report(source, manifest_file, data_dir, now.date().isoformat(), now=now)
    if (report["csv_sha256"] != digest
            or report["manifest_sha256"] != hashlib.sha256(manifest_raw).hexdigest()
            or source.read_bytes() != raw or manifest_file.read_bytes() != manifest_raw
            or report["input_files"] != before
            or any(fingerprint(data_dir / name) != before[name] for name in INPUTS)):
        raise ValueError("Inputs changed during review; retry a complete snapshot")
    if (report["mode"] != "private_offline_review_only"
            or report["operational_additions"] != 0 or report["network_requests"] != 0):
        raise ValueError("Expected offline review only")
    return {"report": report, "freshness": freshness}


def refresh_review(state, csv_path, manifest_path, data_dir, *, now=None):
    """Failed/missing replacements retain the previous verified session copy."""
    try:
        replacement = load_review(csv_path, manifest_path, data_dir, now=now)
    except (OSError, ValueError, TypeError, KeyError, csv.Error, OverflowError):
        # No exception text: a parser/path error could contain private data.
        return False
    state.clear()
    state.update(replacement)
    return True


def review_frame(report):
    """One row per symbol; original85 are independently replayed, never summed twice."""
    baseline = report["same_date_baseline"]["rows"]
    saved = {row["symbol"] for row in baseline}
    rows = [(row, "기존 검토군") for row in baseline]
    rows += [(row, "추가 검토군") for row in report["candidates"] if row["symbol"] not in saved]
    return pd.DataFrame([{
        "symbol": row["symbol"], "검토군": cohort,
        "검토 가능": row["offline_review_eligible"],
        "검토 Stage": row.get("review_only_stage_label") or "보류",
        "NASDAQ Sector": row.get("native_sector", ""),
        "NASDAQ Industry": row.get("native_industry", ""),
        "검토 ETF": (row.get("batch_mapping") or {}).get("sector_benchmark", ""),
        "보류 사유": "; ".join(row.get("blocking_reasons", [])),
    } for row, cohort in rows])


def render_private_review(st, env, get_secret):
    """Authenticated panel independent of the operational screen/universe."""
    if not enabled(env):
        st.session_state.pop("nasdaq_review_context", None)
        clear_upload(st)
        st.session_state.pop(STATE, None)
        st.session_state.pop(AUTH, None)
        return
    public = public_upload_enabled(env)
    context = "public" if public else "private"
    if st.session_state.get("nasdaq_review_context") != context:
        clear_upload(st)
        st.session_state.pop(STATE, None)
        st.session_state.pop(AUTH, None)
        st.session_state.pop("nasdaq_private_review_consent", None)
        st.session_state["nasdaq_review_context"] = context
    title = "NASDAQ CSV 업로드" if public else "비공개 NASDAQ · 오프라인 검토"
    with st.expander(title, expanded=False):
        if not public:
            st.caption("개인 전용 검토 · 운영 목록 편입 0 · 영구 저장소 미연결")
        password = get_secret("APP_PASSWORD")
        if not password:
            clear_upload(st)
            st.session_state.pop(STATE, None)
            st.session_state.pop(AUTH, None)
            st.info("앱 비밀번호를 설정하면 관리자 업로드를 사용할 수 있습니다." if public
                    else "기존 앱 비밀번호를 설정해야 검토할 수 있습니다.")
            return
        password = str(password)
        # Invalidate authentication when the existing app password rotates.
        auth_tag = hashlib.sha256(password.encode()).hexdigest()
        if st.session_state.get(AUTH) != auth_tag:
            clear_upload(st)
            st.session_state.pop(STATE, None)
            st.session_state.pop(AUTH, None)
            with st.form("nasdaq_private_review_login"):
                entered = st.text_input("앱 비밀번호" if public else "비공개 검토 비밀번호", type="password")
                submitted = st.form_submit_button("업로드 잠금 해제" if public else "비공개 검토 잠금 해제")
            if submitted and hmac.compare_digest(entered.encode(), password.encode()):
                st.session_state[AUTH] = auth_tag
                st.rerun()
            elif submitted:
                st.error("비밀번호가 일치하지 않습니다.")
            return
        if st.button("업로드 잠그기" if public else "비공개 검토 잠그기", key="nasdaq_private_review_lock"):
            clear_upload(st)
            st.session_state.pop(STATE, None)
            st.session_state.pop(AUTH, None)
            st.rerun()
        if public:
            token = get_secret("NASDAQ_GITHUB_TOKEN")
            if not token:
                clear_upload(st)
                st.info("공개 저장소 연결이 필요합니다. 운영자가 연결하면 CSV를 올릴 수 있습니다.")
                return
            render_public_upload(st, ROOT / "data", GitHubStore(str(token), password))
            return
        st.warning("비공개 세션 모드입니다. 세션이 끝나면 검토본을 다시 읽어야 합니다.")
        consent = st.checkbox("개인 앱의 비공개 입력을 검토하는 데 동의합니다", key="nasdaq_private_review_consent")
        if not consent:
            clear_upload(st)
            st.session_state.pop(STATE, None)
            return
        source_mode = st.radio("NASDAQ 입력 방식", ["웹 CSV 업로드", "기존 로컬 파일"], key="nasdaq_private_review_source")
        if source_mode == "웹 CSV 업로드":
            render_upload(st, ROOT / "data")
            return
        state = st.session_state.setdefault(STATE, {})
        if st.button("현재 비공개 CSV 검증·읽기", key="nasdaq_private_review_load"):
            ok = refresh_review(state, env.get("NASDAQ_PRIVATE_CSV", ""),
                                env.get("NASDAQ_PRIVATE_MANIFEST", ""), ROOT / "data")
            if not ok:
                st.warning("입력 없음 또는 검증 실패. 이전 정상 세션 검토본이 있으면 유지합니다. 운영 목록은 그대로입니다.")
        if "report" not in state:
            st.info("검증된 비공개 입력이 없습니다. 기존 운영 목록은 계속 이용할 수 있습니다.")
            return
        report = state["report"]
        st.caption(f"고정 검토 기준일 {report['as_of']} · CSV SHA256 {report['csv_sha256']} · {report['quality']['rows']:,}행")
        st.caption(f"직접 확인한 원본 기준일: {report.get('source_as_of') or '미확인'} · 다운로드일: {report.get('downloaded_at_utc') or '미확인'}")
        if state["freshness"] == "unknown":
            st.warning("원본 기준일·다운로드일 미확인. 현재 분류의 최신성을 보증하지 않는 검토본입니다.")
        if report["as_of"] != datetime.now(timezone.utc).date().isoformat():
            st.warning("이전 날짜의 고정 검토본입니다. 현재 상태로 사용하려면 입력을 다시 검증하세요.")
        st.caption("KIS 신원·시총·가격 품질 및 시장/업종 RS gate를 재사용합니다. 미대응 업종과 class/alias 충돌은 보류합니다.")
        frame = review_frame(report)
        status = st.selectbox("비공개 검토 필터", ["전체", "검토 가능", "보류"], key="nasdaq_private_review_filter")
        if status != "전체":
            frame = frame[frame["검토 가능"].eq(status == "검토 가능")]
        st.dataframe(frame, hide_index=True, use_container_width=True)
        st.caption("신규 종목 활성화·관심 목록 자동 추가·운영 CSV 내보내기는 수행하지 않습니다.")
