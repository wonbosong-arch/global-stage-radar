"""Read-only US dashboard inputs from saved KIS prices and approved classification.

No collection, activation, CSV writes or Nasdaq market-cap screening. Research
ETF proposals reuse the existing exact taxonomy/identity/conflict rules.
"""
from datetime import datetime, timezone
import json

import numpy as np
import pandas as pd
import requests

from market_data import completed_bar_cutoff_date
from nasdaq_github_store import BRANCH, CSV_PATH, RECEIPT_PATH, REPO, verified_dates
from nasdaq_local_csv_review import read_table
from nasdaq_single_source import mapping_packets
from stage_engine import relative_return_difference, volume_confirmation
from us_kis_evidence_readiness import assess_candidates
from us_stage_connection_plan import OfflineStageReplay, text

US_VENUES = {"NAS", "NYS", "AMS"}
PRICE_COLS = ["date", "symbol", "open", "high", "low", "close", "volume"]


def approved_classification():
    """Anonymous, bounded reads of the existing user-approved public CSV only."""
    def read(path, limit):
        url = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{path}"
        with requests.get(url, timeout=(5, 15), stream=True, allow_redirects=False) as response:
            response.raise_for_status()
            body = bytearray()
            for chunk in response.iter_content(65536):
                body.extend(chunk)
                if len(body) > limit:
                    raise ValueError("Classification input exceeds limit")
            return bytes(body)
    receipt = json.loads(read(RECEIPT_PATH, 10000))
    raw = read(CSV_PATH, 2_000_000)
    verified_dates(raw, receipt, datetime.now(timezone.utc))
    return raw, receipt


def size_screen(row, master_rows, supplement_rows=None):
    """KIS USD caps first; saved Yahoo supplement only if KIS has no value.

    Observation/effective-date differences never trigger another provider call.
    Nasdaq capitalization is deliberately absent from this function.
    """
    values = []
    if len(master_rows) == 1:
        values.append((master_rows.iloc[0].get("market_cap_usd"), "KIS master"))
    if text(row.get("discovery_source")) == "KIS market-cap ranking":
        values.append((row.get("discovery_market_cap_usd"), "KIS ranking"))
    for value, source in values:
        value = pd.to_numeric(value, errors="coerce")
        if pd.notna(value) and np.isfinite(value) and value > 0:
            return float(value), source
    if supplement_rows is not None and len(supplement_rows) == 1:
        observation = supplement_rows.iloc[0]
        value = pd.to_numeric(observation.get("market_cap_usd_b_secondary"), errors="coerce") * 1e9
        if (observation.get("source") == "Yahoo Finance" and observation.get("quote_type") == "EQUITY"
                and observation.get("observation_status") == "observed_usd"
                and pd.notna(value) and np.isfinite(value) and value > 0):
            return float(value), "Yahoo saved supplement"
    source = text(row.get("market_cap_source_url"))
    if "finance.yahoo.com/" in source:
        value = pd.to_numeric(row.get("market_cap_usd_b_secondary"), errors="coerce") * 1e9
        if pd.notna(value) and np.isfinite(value) and value > 0:
            return float(value), "Yahoo saved supplement"
    return np.nan, "시총 미확보"


def build_research(registry, master, universe, candidate_prices, active_prices,
                   existing_report, *, raw=None, receipt=None, supplement=None, as_of=None, now=None):
    """Return report + chart prices. Every row stays pending and read-only."""
    now = now or datetime.now(timezone.utc)
    as_of = pd.Timestamp(as_of or now.date()).normalize()
    us = registry[registry.exchange.isin(US_VENUES)
                  & registry.activation_status.eq("pending_review")].copy()
    if us.symbol.duplicated().any():
        raise ValueError("Duplicate US candidate identity")
    identities = {p["symbol"]: p for p in assess_candidates(us, master, {})}
    packets = {}
    if raw is not None:
        verified_dates(raw, receipt, now)
        _, columns, rows = read_table(raw)
        # Market Cap is an existing parser contract, never used as size evidence.
        packets = {p["symbol"]: p for p in mapping_packets(
            rows, columns, us, master, universe, {}, identities=identities)}
    old = existing_report.set_index("symbol").to_dict("index")
    metadata = universe.set_index("symbol").to_dict("index")
    groups = {s: g for s, g in master.groupby("symbol")}
    supplements = {s: g for s, g in supplement.groupby("symbol")} if supplement is not None else {}
    mappings, needed = {}, set(us.symbol)
    for row in us.to_dict("records"):
        saved = old.get(row["symbol"], {})
        mapping = {"market": "United States", "asset_type": "stock",
                   "sector": text(saved.get("proposed_sector")),
                   "market_benchmark": text(saved.get("market_benchmark")) or "SPY",
                   "sector_benchmark": text(saved.get("suggested_sector_benchmark"))}
        packet = packets.get(row["symbol"], {})
        basis = "저장 제안 · 미승인"
        if not mapping["sector_benchmark"] and packet.get("batch_mapping"):
            mapping = packet["batch_mapping"].copy()
            basis = "Nasdaq Sector/Industry · 연구 ETF 제안"
        mappings[row["symbol"]] = mapping, basis, packet
        needed.update([mapping["market_benchmark"], mapping["sector_benchmark"]])
    # Only saved KIS prices. Active KIS benchmarks take precedence at overlap.
    frames = [candidate_prices[~candidate_prices.symbol.isin(active_prices.symbol)][PRICE_COLS],
              active_prices[PRICE_COLS]]
    prices = pd.concat(frames, ignore_index=True)
    prices = prices[prices.symbol.isin(needed)].copy()
    exchanges = dict(zip(us.symbol, us.exchange))
    exchanges.update({s: m.get("exchange", "") for s, m in metadata.items()})
    prices["date"] = pd.to_datetime(prices["date"], errors="coerce")
    # All US venues share the existing completed-session contract. Apply its
    # per-venue cutoff vectorially rather than scanning 700k rows per ticker.
    cutoffs = {v: pd.Timestamp(completed_bar_cutoff_date(v, now_kst=now))
               for v in set(exchanges.values()) if v in US_VENUES}
    limits = prices.symbol.map(exchanges).map(cutoffs)
    prices = prices[limits.isna() | prices.date.le(limits)].copy()
    for column in PRICE_COLS[2:]:
        prices[column] = pd.to_numeric(prices[column], errors="coerce")
    # Conflicting duplicates within an input still fail the replay validator.
    prices = prices.drop_duplicates(PRICE_COLS)
    replay = OfflineStageReplay(prices, as_of)
    valid = prices[prices.symbol.isin(replay.daily)].copy()
    daily_groups = {s: g.sort_values("date") for s, g in valid.groupby("symbol")}
    rows = []
    for row in us.to_dict("records"):
        symbol = row["symbol"]
        mapping, basis, packet = mappings[symbol]
        run = replay.replay(symbol, mapping)
        reasons = list(run["reasons"])
        cap, cap_source = size_screen(row, groups.get(symbol, master.iloc[:0]), supplements.get(symbol))
        if not (pd.notna(cap) and cap >= 1e9):
            reasons.append("market_cap_below_1b_or_missing")
        if identities[symbol]["identity_basis"] != "kis_master_consistent":
            reasons.append("kis_identity_review_required")
        for kind in ("market", "sector"):
            bench = metadata.get(mapping[kind + "_benchmark"], {})
            if (bench.get("provider") != "KIS" or str(bench.get("active")).lower() != "true"
                    or bench.get("asset_type") != kind + "_etf"
                    or (kind == "sector" and bench.get("sector") != mapping["sector"])):
                reasons.append(kind + "_benchmark_metadata_missing")
        daily = daily_groups.get(symbol, valid.iloc[:0])
        if not daily.empty and daily.close.pct_change().abs().gt(.5).any():
            reasons.append("price_anomaly_review_required")
        weekly = replay.weekly.get(symbol)
        last = weekly.iloc[-1] if weekly is not None and not weekly.empty else pd.Series(dtype=float)
        rs = []
        for kind in ("market", "sector"):
            bw = replay.weekly.get(mapping[kind + "_benchmark"])
            rs.append(relative_return_difference(weekly, bw, 26).iloc[-1]
                      if weekly is not None and not weekly.empty and bw is not None and not bw.empty else np.nan)
        rows.append({"symbol": symbol, "name": row["name"], "exchange": row["exchange"],
            "proposed_sector": mapping["sector"], "market_benchmark": mapping["market_benchmark"],
            "suggested_sector_benchmark": mapping["sector_benchmark"],
            "native_sector": packet.get("native_sector") if packet.get("native_classification_join_pass") else "",
            "native_industry": packet.get("native_industry") if packet.get("native_classification_join_pass") else "",
            "classification_basis": basis, "market_cap_usd": cap, "cap_source": cap_source,
            "candidate_latest_daily_date": replay.latest.get(symbol),
            "completed_weekly_date": last.get("date"), "weekly_bars": run["completed_weeks"][symbol],
            "close": last.get("close"), "ma30": last.get("ma30"),
            "ma30_slope_4w_pct": last.get("slope4_pct"),
            "market_rs_26w_pct": rs[0], "sector_rs_26w_pct": rs[1],
            "volume_context": volume_confirmation(last.get("vol_ratio", np.nan)),
            "provisional_stage_label": run["review_only_stage_label"] if not reasons else "연구 판정 보류",
            "research_eligible": not reasons, "data_status": run["engine_freshness"],
            "review_note": ", ".join(dict.fromkeys(reasons)),
            "activation_status": "pending_review_not_activated"})
    report = pd.DataFrame(rows)
    for column in ("candidate_latest_daily_date", "completed_weekly_date"):
        report[column] = pd.to_datetime(report[column]).dt.strftime("%Y-%m-%d")
    return report, valid[valid.symbol.isin(us.symbol)].copy()
