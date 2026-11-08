"""Two-step manual upload with optional public GitHub storage for review only."""
from __future__ import annotations

from datetime import date, datetime, time, timezone
import hashlib
import json
from pathlib import Path
import tempfile

from nasdaq_github_store import (
    BRANCH, CSV_PATH, INTERVAL, PUBLIC_MAX_BYTES, REPO, StoreError, verified_dates,
)
from nasdaq_local_csv_review import read_table
from nasdaq_monthly_refresh import MAX_BYTES, SOURCE, digest, quality
from nasdaq_single_source import check_local_manifest

KEY = "nasdaq_upload_state"
PREFIX = "nasdaq_upload_"
MIN_ROWS = 5000
ERROR = "CSV 검증 또는 승인 실패. 마지막 승인본을 유지합니다. 파일 구조·크기·분류·변동 폭과 다운로드일을 확인하세요."

STORE_ERROR = "공개 저장소 연결 또는 무결성 확인에 실패했습니다. 마지막 정상본을 유지합니다."
SAVE_ERROR = "GitHub 저장 성공을 확인하지 못했습니다. 다시 검증하여 현재 저장본을 확인하세요."
STALE_ERROR = "검증 후 저장소가 변경됐습니다. 최신 저장본을 기준으로 다시 검증하세요."
PUBLIC_ERROR = "공개용 CSV 검사에 실패했습니다. 개인정보·자격 증명·비정상 셀이 없는 원본을 사용하세요."
INTERVAL_ERROR = "공개 저장은 7일에 한 번 가능하며, 다운로드일이 더 최근인 새 내용이어야 합니다."


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


def reload_public(state, store, data_dir, *, now=None):
    """Refresh the baseline; only verified reads may replace the session copy."""
    now = now or datetime.now(timezone.utc)
    try:
        head = store.head()
        if head == state.get("head"):
            state.pop("error", None)
            return True
        snapshot = store.read(head)
        if snapshot is None:
            if state.get("good"):
                raise StoreError("Approved files disappeared")
        else:
            raw, receipt = snapshot
            downloaded, approved = verified_dates(raw, receipt, now)
            store.check(raw)
            # Replay at approval time so the intake age cutoff does not erase a
            # historical last-good snapshot. The UI separately warns on age.
            good = prepare(raw, downloaded, data_dir, now=approved)
            state["good"] = {**good, "approved_at": approved.isoformat()}
        state["head"] = head
    except Exception:
        state["error"] = STORE_ERROR
        return False
    state.pop("error", None)
    return True


def publication_due(previous, raw, downloaded_on, now):
    if not previous:
        return True
    manifest = previous["manifest"]
    approved = datetime.fromisoformat(previous["approved_at"])
    downloaded = datetime.fromisoformat(manifest["downloaded_at_utc"]).date()
    return (now - approved >= INTERVAL and downloaded_on > downloaded
            and digest(raw) != manifest["csv_sha256"])


def public_checks(state, store, raw, downloaded_on, now):
    try:
        store.check(raw)
    except Exception:
        state["error"] = PUBLIC_ERROR
        return False
    if not publication_due(state.get("good"), raw, downloaded_on, now):
        state["error"] = INTERVAL_ERROR
        return False
    return True


def validate(state, raw, downloaded_on, data_dir, *, now=None, store=None):
    state.pop("pending", None)
    now = now or datetime.now(timezone.utc)
    if store is not None and not (reload_public(state, store, data_dir, now=now)
                                  and public_checks(state, store, raw, downloaded_on, now)):
        return False
    try:
        state["pending"] = prepare(raw, downloaded_on, data_dir, state.get("good"), now=now)
    except Exception:
        # Do not emit parser exceptions, filenames, rows, paths or tracebacks.
        state["error"] = ERROR
        return False
    if store is not None:
        state["pending"]["head"] = state["head"]
    state.pop("error", None)
    return True


def approve(state, raw, downloaded_on, data_dir, *, now=None, store=None, publication_consent=False):
    now = now or datetime.now(timezone.utc)
    pending = state.pop("pending", None)
    if not pending or pending["binding"] != binding(raw, downloaded_on):
        state["error"] = ERROR
        return False
    if store is not None:
        if not publication_consent:
            state["error"] = ERROR
            return False
        if not reload_public(state, store, data_dir, now=now):
            return False
        if pending.get("head") != state["head"]:
            state["error"] = STALE_ERROR
            return False
        if not public_checks(state, store, raw, downloaded_on, now):
            return False
    try:
        # Revalidate the full current KIS snapshot as well as the selected bytes.
        replacement = prepare(raw, downloaded_on, data_dir, state.get("good"), now=now)
    except Exception:
        state["error"] = ERROR
        return False
    if store is not None:
        try:
            state["head"] = store.commit(pending["head"], raw, downloaded_on, now)
        except Exception:
            # A timeout can occur after GitHub accepted the commit. Never
            # retry the write automatically or claim success without an OID.
            state["error"] = SAVE_ERROR
            return False
    state["good"] = {**replacement, "approved_at": now.isoformat()}
    state.pop("error", None)
    return True


def freshness(good, *, now=None):
    now = now or datetime.now(timezone.utc)
    uploaded = datetime.fromisoformat(good["approved_at"])
    downloaded = datetime.fromisoformat(good["manifest"]["downloaded_at_utc"])
    return "overdue" if max((now - uploaded).days, (now - downloaded).days) >= 7 else "current"


def selected_bytes(uploaded, max_bytes=None):
    max_bytes = MAX_BYTES if max_bytes is None else max_bytes
    if uploaded is None:
        raise ValueError("No upload")
    # Check metadata before copying the BytesIO; independently enforce real size.
    if uploaded.size > max_bytes:
        raise ValueError("Upload too large")
    raw = uploaded.getvalue()
    if not raw or len(raw) > max_bytes:
        raise ValueError("Upload size gate")
    return raw


def render_upload(st, data_dir, *, store=None):
    from nasdaq_private_review import review_frame
    state = st.session_state.setdefault(KEY, {})
    st.caption("일요일에 공식 NASDAQ Stock Screener에서 Download CSV로 내려받은 파일을 선택하세요.")
    max_bytes = MAX_BYTES
    if store is None:
        st.warning("영구 저장소 미연결. 재접속·앱 재시작 후에는 다시 업로드해야 합니다.")
    else:
        st.warning(f"공개 저장 대상은 {REPO}의 {BRANCH} 브랜치, {CSV_PATH}입니다. 승인한 원본은 Git 기록에 공개됩니다.")
        max_bytes = PUBLIC_MAX_BYTES
        reload_clicked = st.button("GitHub 승인본 다시 읽기", key=PREFIX + "reload")
        if reload_clicked or not state.get("initial_read"):
            state["initial_read"] = True
            state.pop("pending", None)
            reload_public(state, store, data_dir)
    # Preserve a stricter existing server upload limit.
    limit = min(max_bytes // 1_000_000, st.get_option("server.maxUploadSize"))
    upload = st.file_uploader("NASDAQ 공식 CSV", type=["csv"], key=PREFIX + "file", max_upload_size=limit)
    downloaded_on = st.date_input("직접 다운로드한 날짜 (UTC)", value=None, max_value=datetime.now(timezone.utc).date(), key=PREFIX + "date")
    raw = None
    try:
        raw = selected_bytes(upload, max_bytes)
    except Exception:
        if upload is not None:
            state["error"] = ERROR
    current_binding = binding(raw, downloaded_on) if raw and downloaded_on else None
    if state.get("pending", {}).get("binding") != current_binding:
        state.pop("pending", None)
    if st.button("CSV 품질 검증", key=PREFIX + "validate", disabled=current_binding is None):
        validate(state, raw, downloaded_on, data_dir, store=store)
    pending = state.get("pending")
    if pending:
        q = pending["quality"]
        st.caption(f"검증 통과 · {q['rows']:,}행 · 분류 완성 {q['native_classification_complete']:,}행 · SHA256 {q['csv_sha256']}")
        st.caption("원본 기준일은 미확인입니다.")
        consent = False
        label = "정상본 승인 · 세션 보관"
        if store is not None:
            consent = st.checkbox(
                "이 CSV의 공개 재배포 권한을 확인했고, 원본을 공개 GitHub 기록에 저장하는 데 동의합니다.",
                key=PREFIX + "publish_" + pending["binding"],
            )
            label = "정상본 승인 · 공개 GitHub에 저장"
        if st.button(label, key=PREFIX + "approve", disabled=store is not None and not consent):
            approve(state, raw, downloaded_on, data_dir, store=store, publication_consent=consent)
    if state.get("error"):
        st.warning(state["error"])
    good = state.get("good")
    if not good:
        st.info("아직 승인한 NASDAQ CSV가 없습니다.")
        return
    st.caption(f"최근 승인 성공 (UTC): {good['approved_at']} · 다운로드일: {good['manifest']['downloaded_at_utc'][:10]} · 원본 기준일: 미확인")
    location = f"GitHub 커밋 {state['head']}" if store is not None else "세션 보관 중"
    st.caption(f"마지막 정상본 SHA256 {good['quality']['csv_sha256']} · {location}")
    if freshness(good) == "overdue":
        st.warning("7일 이상 갱신되지 않았습니다. 마지막 승인본을 유지하며 최신성을 보증하지 않습니다.")
    frame = review_frame(good["review"]["report"])
    choice = st.selectbox("업로드 검토 필터", ["전체", "검토 가능", "보류"], key=PREFIX + "filter")
    if choice != "전체":
        frame = frame[frame["검토 가능"].eq(choice == "검토 가능")]
    st.dataframe(frame, hide_index=True, use_container_width=True)
    st.caption("분류와 신규 심볼 후보는 검토용입니다. 운영 종목에 자동 편입되지 않습니다.")
