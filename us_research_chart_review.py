"""Reviewed market moves for the saved US KIS research charts."""

# Each entry identifies both sessions and the approximate signed move in percent.
# These reviews use ChartExchange's venue-specific histories, with FinanceCharts
# for IBTA and Quiver Quantitative for ZBIO. No external prices enter the chart.
VERIFIED_PRICE_MOVES = {
    ("NAS", "AAOI", "2026-02-26", "2026-02-27"): 56.9,
    ("NAS", "AGIO", "2025-11-18", "2025-11-19"): -50.9,
    ("NYS", "AGL", "2026-05-06", "2026-05-07"): 117.8,
    ("NAS", "AMLX", "2026-08-17", "2026-08-18"): 63.8,
    ("NAS", "BAND", "2026-04-29", "2026-04-30"): 52.1,
    ("NYS", "BFLY", "2026-02-25", "2026-02-26"): 50.6,
    ("NYS", "BFLY", "2026-06-17", "2026-06-18"): 55.9,
    ("NAS", "BRZE", "2026-10-19", "2026-10-20"): 51.7,
    ("NAS", "COGT", "2025-11-07", "2025-11-10"): 119.0,
    ("NAS", "CORT", "2025-12-30", "2025-12-31"): -50.4,
    ("NYS", "CTVA", "2026-09-30", "2026-10-01"): -83.8,
    ("NAS", "ELVN", "2026-01-07", "2026-01-08"): 50.3,
    ("NAS", "FSLY", "2026-02-11", "2026-02-12"): 72.3,
    ("NAS", "GRAL", "2026-02-19", "2026-02-20"): -50.5,
    ("NYS", "IBTA", "2026-08-03", "2026-08-04"): 51.9,
    ("NAS", "INBX", "2025-10-23", "2025-10-24"): 102.0,
    ("NAS", "INOD", "2026-05-07", "2026-05-08"): 86.0,
    ("NAS", "JANX", "2025-12-01", "2025-12-02"): -53.3,
    ("NYS", "KD", "2026-02-06", "2026-02-09"): -54.9,
    ("NAS", "KOD", "2025-09-19", "2025-09-22"): 57.5,
    ("NAS", "KOD", "2026-03-25", "2026-03-26"): 74.8,
    ("NAS", "KOD", "2026-09-25", "2026-09-28"): 178.0,
    ("NAS", "LQDA", "2026-09-29", "2026-09-30"): -57.2,
    ("NYS", "LRN", "2025-10-28", "2025-10-29"): -54.4,
    ("NAS", "MAZE", "2025-09-10", "2025-09-11"): 54.8,
    ("NAS", "MBX", "2025-09-19", "2025-09-22"): 100.0,
    ("NAS", "MGRT", "2025-12-16", "2025-12-17"): 143.9,
    ("NAS", "MGRT", "2025-12-19", "2025-12-22"): 70.4,
    ("NAS", "MGRT", "2026-02-11", "2026-02-12"): 112.4,
    ("NAS", "MGRT", "2026-03-31", "2026-04-01"): 89.8,
    ("NAS", "MGRT", "2026-04-07", "2026-04-08"): 58.2,
    ("NAS", "MGRT", "2026-04-15", "2026-04-16"): 54.0,
    ("NAS", "MLTX", "2025-09-26", "2025-09-29"): -89.9,
    ("NAS", "MLYS", "2025-08-29", "2025-09-02"): 86.4,
    ("NAS", "MRNA", "2026-08-18", "2026-08-19"): 177.0,
    ("NAS", "MXL", "2026-04-23", "2026-04-24"): 76.1,
    ("NAS", "NKTR", "2026-02-09", "2026-02-10"): 51.1,
    ("NAS", "OMER", "2025-10-14", "2025-10-15"): 154.1,
    ("NAS", "OMER", "2025-12-23", "2025-12-24"): 75.5,
    ("NAS", "OPEN", "2025-09-10", "2025-09-11"): 79.5,
    ("NYS", "PACS", "2025-11-19", "2025-11-20"): 55.3,
    ("NAS", "PLSE", "2026-02-05", "2026-02-06"): 51.6,
    ("NAS", "PRAX", "2025-10-15", "2025-10-16"): 183.7,
    ("NYS", "PRIM", "2026-05-05", "2026-05-06"): -50.1,
    ("NAS", "QURE", "2025-09-23", "2025-09-24"): 247.7,
    ("NAS", "QURE", "2026-06-16", "2026-06-17"): 78.4,
    ("NAS", "RAPP", "2025-09-05", "2025-09-08"): 119.2,
    ("NAS", "REPL", "2025-10-17", "2025-10-20"): 98.8,
    ("NAS", "REPL", "2026-04-10", "2026-04-13"): -64.3,
    ("NAS", "REPL", "2026-05-28", "2026-05-29"): 85.7,
    ("NAS", "REPL", "2026-07-30", "2026-07-31"): 107.0,
    ("NAS", "RGC", "2026-01-06", "2026-01-07"): 60.1,
    ("NAS", "STRL", "2026-05-04", "2026-05-05"): 52.2,
    ("NAS", "TNGX", "2026-06-05", "2026-06-08"): 53.0,
    ("NAS", "TRAX", "2026-07-08", "2026-07-09"): 56.0,
    ("NAS", "TSHA", "2025-10-01", "2025-10-02"): 53.5,
    ("NYS", "UTZ", "2026-07-20", "2026-07-21"): 88.7,
    ("NAS", "VCYT", "2026-11-04", "2026-11-05"): -54.3,
    ("NAS", "ZBIO", "2026-01-02", "2026-01-05"): -51.9,
}

# The NYSE reused CDLR for Cadeler plc ordinary shares after Cadeler A/S ADSs
# stopped trading. A symbol-only price history cannot stitch these instruments.
# https://ir.cadeler.com/financials/all-sec-filings/content/0000876661-26-000891/0000876661-26-000891.pdf
PRICE_SERIES_IDENTITY_CHANGES = {("NYS", "CDLR"): "2026-11-05"}


def chart_price_review(daily, exchange, symbol, large_moves):
    """Return a chart hold reason for mixed identities or unreviewed moves."""
    identity_change = PRICE_SERIES_IDENTITY_CHANGES.get((exchange, symbol))
    if not identity_change and large_moves.empty:
        return ""
    dates = daily.date.dt.strftime("%Y-%m-%d")
    if identity_change and dates.lt(identity_change).any() and dates.ge(identity_change).any():
        return "price_series_identity_conflict"
    if large_moves.empty:
        return ""

    prior_dates = dates.shift()
    for index, move in large_moves.items():
        expected = VERIFIED_PRICE_MOVES.get((exchange, symbol, prior_dates.at[index], dates.at[index]))
        # Allow one tenth of a percentage point for the rounded review value.
        if expected is None or abs(move * 100 - expected) > 0.1:
            return "price_anomaly_review_required"
    return ""
