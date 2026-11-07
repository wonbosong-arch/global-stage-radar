"""Private, session-only manual upload. No remote store or activation API."""
from __future__ import annotations

import copy
from datetime import date, datetime, time, timezone
import hashlib
import json
from pathlib import Path
import tempfile

from nasdaq_local_csv_review import read_table
from nasdaq_monthly_refresh import MAX_BYTES, SOURCE, digest, quality
from nasdaq_single_source import check_local_manifest

KEY = "nasdaq_upload_state"
PREFIX = "nasdaq_upload_"
MIN_ROWS = 5000
ERROR = "CSV 검증 또는 승인 실패. 마지막 승인본을 유지합니다. 파일 구조·크기·분류·변동 폭과 다운로드일을 확인하세요."


def clear_upload(st):
    for key in list(st.session_state):
        if key.startswith(PREFIX):
            del st.session_state[key]


def manual_manifest(raw, downloaded_on, now):
    # Date is the user's attestation, never inferred from upload time/name/mtime.
    stamp = datetime.combine(downloaded_on, time.min, tzinfo=timezone.utc)
    manifest = dict(dataset_kind="user_supplied_nasdaq_csv", acquisition_method="user_manual_download",
        scope="private_noncommercial_offline", user_instruction_reference="Authenticated manual upload and private review consent",
        csv_sha256=digest(raw), source_url=SOURCE, source_as_of=None,
        downloaded_at_utc=stamp.isoformat(), downloaded_at_utc_reference="User-attested manual download calendar date (UTC)")
    check_local_manifest(manifest, digest(raw), now)
    if (now.date() - downloaded_on).days > 45:
        raise ValueError("Download too old")
    return manifest


def binding(raw, downloaded_on):
    return hashlib.sha256(raw + b"\0" + downloaded_on.isoformat().encode()).hexdigest()


def prepare(raw, downloaded_on, data_dir, previous=None, *, now=None):
    """Complete quality and actual #219 engine replay before offering approval."""
    from nasdaq_private_review import load_review
    now = now or datetime.now(timezone.utc)
    manifest = manual_manifest(raw, downloaded_on, now)
    measured = quality(raw, manifest, (previous or {}).get("quality"), min_rows=MIN_ROWS)
    _, _, rows = read_table(raw)
    symbols = frozenset(row["Symbol"].strip().upper() for row in rows)
    if previous:
        old = previous["quality"]
        if measured["rows"] > old["rows"] * 1.25 or measured["csv_bytes"] > old["csv_bytes"] * 1.5:
            raise ValueError("Unexpected row/size growth")
        if len(symbols.symmetric_difference(previous["symbols"])) / max(len(symbols), len(previous["symbols"])) > .20:
            raise ValueError("Unexpected symbol turnover")
    # The existing engine accepts paths. Use bounded ephemeral files outside Git,
    # constant names, no uploaded filename, and delete them before returning.
    with tempfile.TemporaryDirectory(prefix="nasdaq-review-") as temp:
        source, mp = Path(temp) / "input.csv", Path(temp) / "manifest.json"
        source.write_bytes(raw)
        mp.write_text(json.dumps(manifest), encoding="utf-8")
        review = load_review(source, mp, data_dir, now=now)
    if review["report"]["csv_sha256"] != digest(raw):
        raise ValueError("Replay hash mismatch")
    return dict(raw=raw, manifest=manifest, quality=measured, symbols=symbols,
                review=review, binding=binding(raw, downloaded_on), validated_at=now.isoformat())


def validate(state, raw, downloaded_on, data_dir, *, now=None):
    state.pop("pending", None)
    try:
        state["pending"] = prepare(raw, downloaded_on, data_dir, state.get("good"), now=now)
    except Exception:
        # Do not emit parser exceptions, filenames, rows, paths or tracebacks.
        state["error"] = ERROR
        return False
    state.pop("error", None)
    return True


def approve(state, raw, downloaded_on, data_dir, *, now=None):
    now = now or datetime.now(timezone.utc)
    pending = state.pop("pending", None)
    try:
        if not pending or pending["binding"] != binding(raw, downloaded_on):
            raise ValueError("Changed input requires validation")
        # Revalidate the full current KIS snapshot as well as the selected bytes.
        replacement = prepare(raw, downloaded_on, data_dir, state.get("good"), now=now)
    except Exception:
        state["error"] = ERROR
        return False
    state["good"] = {**replacement, "approved_at": now.isoformat()}
    state.pop("error", None)
    return True


def freshness(good, *, now=None):
    now = now or datetime.now(timezone.utc)
    uploaded = datetime.fromisoformat(good["approved_at"])
    downloaded = datetime.fromisoformat(good["manifest"]["downloaded_at_utc"])
    return "overdue" if max((now - uploaded).days, (now - downloaded).days) >= 7 else "current"


def selected_bytes(uploaded):
    if uploaded is None:
        raise ValueError("No upload")
    # Check metadata before copying the BytesIO; independently enforce real size.
    if uploaded.size > MAX_BYTES:
        raise ValueError("Upload too large")
    raw = uploaded.getvalue()
    if not raw or len(raw) > MAX_BYTES:
        raise ValueError("Upload size gate")
    return raw


def render_upload(st, data_dir):
    from nasdaq_private_review import review_frame
    state = st.session_state.setdefault(KEY, {})
    st.caption("일요일에 공식 NASDAQ Stock Screener에서 Download CSV로 내려받은 파일을 선택하세요.")
    st.warning("영구 저장소 미연결: 승인본은 현재 세션에만 보관됩니다. 재접속·앱 재시작 후에는 다시 업로드해야 합니다.")
    # Preserve a stricter existing server limit. The independent byte gate is 10 MB.
    limit = min(10, st.get_option("server.maxUploadSize"))
    upload = st.file_uploader("NASDAQ 공식 CSV", type=["csv"], key=PREFIX + "file", max_upload_size=limit)
    downloaded_on = st.date_input("직접 다운로드한 날짜 (UTC)", value=None, max_value=datetime.now(timezone.utc).date(), key=PREFIX + "date")
    raw = None
    try:
        raw = selected_bytes(upload)
    except Exception:
        if upload is not None:
            state["error"] = ERROR
    current_binding = binding(raw, downloaded_on) if raw and downloaded_on else None
    if state.get("pending", {}).get("binding") != current_binding:
        state.pop("pending", None)
    if st.button("CSV 품질 검증", key=PREFIX + "validate", disabled=current_binding is None):
        validate(state, raw, downloaded_on, data_dir)
    pending = state.get("pending")
    if pending:
        q = pending["quality"]
        st.caption(f"검증 통과 · {q['rows']:,}행 · 분류 완성 {q['native_classification_complete']:,}행 · SHA256 {q['csv_sha256']}")
        st.caption("원본 기준일은 미확인입니다. 아래 승인은 개인 검토용 세션 보관에만 적용됩니다.")
        if st.button("정상본 승인 · 세션 보관", key=PREFIX + "approve"):
            approve(state, raw, downloaded_on, data_dir)
    if state.get("error"):
        st.warning(state["error"])
    good = state.get("good")
    if not good:
        st.info("아직 승인한 NASDAQ CSV가 없습니다.")
        return
    st.caption(f"최근 승인 성공 (UTC): {good['approved_at']} · 다운로드일: {good['manifest']['downloaded_at_utc'][:10]} · 원본 기준일: 미확인")
    st.caption(f"마지막 정상본 SHA256 {good['quality']['csv_sha256']} · 세션 보관 중")
    if freshness(good) == "overdue":
        st.warning("7일 이상 갱신되지 않았습니다. 마지막 승인본을 유지하며 최신성을 보증하지 않습니다.")
    frame = review_frame(good["review"]["report"])
    choice = st.selectbox("업로드 검토 필터", ["전체", "검토 가능", "보류"], key=PREFIX + "filter")
    if choice != "전체":
        frame = frame[frame["검토 가능"].eq(choice == "검토 가능")]
    st.dataframe(frame, hide_index=True, use_container_width=True)
    st.caption("분류·신규 심볼 후보는 검토용입니다. 운영 종목 자동 편입·원본 공개·CSV 내보내기는 수행하지 않습니다.")
