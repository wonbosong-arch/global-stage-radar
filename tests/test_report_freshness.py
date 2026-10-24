import pandas as pd

from candidate_review_queue import assess_report_freshness


def test_stale_queue_and_mismatched_summary_are_detected():
    now = pd.Timestamp("2026-10-25T00:00:00Z")
    result = assess_report_freshness(
        "2026-10-23T00:00:00Z",
        "2026-10-23T00:01:00Z",
        now=now,
    )
    assert result["queue_stamp_valid"]
    assert result["summary_stamp_valid"]
    assert not result["stamps_match"]
    assert result["queue_stale"]
    assert result["queue_age_hours"] == 48


def test_missing_or_invalid_stamps_are_not_treated_as_fresh():
    result = assess_report_freshness(
        "",
        "not-a-timestamp",
        now=pd.Timestamp("2026-10-25T00:00:00Z"),
    )
    assert not result["queue_stamp_valid"]
    assert not result["summary_stamp_valid"]
    assert not result["stamps_match"]
    assert result["queue_age_hours"] is None
    assert not result["queue_stale"]


def test_equivalent_timezone_stamps_match():
    result = assess_report_freshness(
        "2026-10-24T23:30:00Z",
        "2026-10-25T08:30:00+09:00",
        now=pd.Timestamp("2026-10-25T00:00:00Z"),
    )
    assert result["stamps_match"]
    assert not result["queue_stale"]
    assert result["queue_age_hours"] == 0.5



def test_materially_future_dated_queue_is_flagged():
    result = assess_report_freshness(
        "2026-10-25T00:10:00Z",
        "2026-10-25T00:10:00Z",
        now=pd.Timestamp("2026-10-25T00:00:00Z"),
    )
    assert result["queue_timestamp_in_future"]
    assert not result["queue_stale"]


def test_small_future_clock_skew_is_tolerated():
    result = assess_report_freshness(
        "2026-10-25T00:03:00Z",
        "2026-10-25T00:03:00Z",
        now=pd.Timestamp("2026-10-25T00:00:00Z"),
    )
    assert not result["queue_timestamp_in_future"]
