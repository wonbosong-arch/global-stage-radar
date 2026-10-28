import unittest
from io import BytesIO
import zipfile
import pandas as pd
from unittest.mock import patch

from kis_universe import fetch_us_market_cap_candidates, fetch_korea_market_cap_candidates, normalize_market_cap_candidates, parse_us_security_master_zip, audit_us_master_ranking_coverage, build_unranked_us_stock_master


class FakeResponse:
    ok = True
    status_code = 200
    text = ""

    def __init__(self, payload, headers=None):
        self._payload = payload
        self.headers = headers or {}

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def get(self, url, headers, params, timeout):
        self.calls.append((url, headers, params, timeout))
        return FakeResponse(self.payload)


class FakeClient:
    base_url = "https://example.test"
    app_key = "key"
    app_secret = "secret"
    timeout = 1
    _last_request_at = 0

    def __init__(self, payload):
        self.session = FakeSession(payload)

    def _get_token(self):
        return "token"


class KISUniverseTests(unittest.TestCase):
    def test_us_candidate_keeps_raw_fields_and_marks_cap_unverified(self):
        client = FakeClient({"rt_cd": "0", "output1": {"NEXT_KEY": "sample-key", "TOTAL_COUNT": "999"}, "output2": [{"symb": "AAPL", "mcap": "unknown"}]})
        result = fetch_us_market_cap_candidates(client, "NAS")
        self.assertEqual(result.iloc[0]["symb"], "AAPL")
        self.assertEqual(result.attrs["ranking_output1_keys"], ["NEXT_KEY", "TOTAL_COUNT"])
        self.assertFalse(bool(result.iloc[0]["market_cap_units_verified"]))
        self.assertEqual(client.session.calls[0][2]["EXCD"], "NAS")
        self.assertEqual(set(client.session.calls[0][2]), {"EXCD", "VOL_RANG", "KEYB", "AUTH", "CURR_GB"})
        self.assertEqual(client.session.calls[0][2].get("CURR_GB"), "0")

    def test_us_ranking_continues_when_kis_marks_first_page_with_f(self):
        class FirstPageSession:
            def __init__(self):
                self.calls = []

            def get(self, url, headers, params, timeout):
                self.calls.append((url, headers, params, timeout))
                if len(self.calls) == 1:
                    return FakeResponse(
                        {"rt_cd": "0", "output1": {"trec": "101"}, "output2": [{"symb": "AAPL"}]},
                        headers={"tr_cont": "F"},
                    )
                return FakeResponse(
                    {"rt_cd": "0", "output1": {"trec": "101"}, "output2": [{"symb": "MSFT"}]},
                    headers={"tr_cont": "D"},
                )

        client = FakeClient({})
        client.session = FirstPageSession()
        with patch("kis_universe.time.sleep", return_value=None):
            result = fetch_us_market_cap_candidates(client, "NAS")
        self.assertEqual(len(client.session.calls), 2)
        self.assertEqual(list(result["symb"]), ["AAPL", "MSFT"])
        self.assertEqual(client.session.calls[1][1]["tr_cont"], "N")
        self.assertEqual(result.attrs["ranking_pages_fetched"], 2)
        self.assertEqual(result.attrs["ranking_page_diagnostics"][0]["response_tr_cont"], "F")

    def test_korea_candidate_keeps_raw_fields_and_marks_cap_unverified(self):
        client = FakeClient({"rt_cd": "0", "output": [{"mksc_shrn_iscd": "005930", "stck_avls": "raw"}]})
        result = fetch_korea_market_cap_candidates(client)
        self.assertEqual(result.iloc[0]["mksc_shrn_iscd"], "005930")
        self.assertFalse(bool(result.iloc[0]["market_cap_units_verified"]))
        self.assertEqual(result.iloc[0]["ranking_market_code"], "0000")
        self.assertEqual(client.session.calls[0][2]["fid_input_iscd"], "0000")
        self.assertEqual(client.session.calls[0][2]["fid_cond_scr_div_code"], "20174")
        self.assertEqual(client.session.calls[0][2]["fid_div_cls_code"], "1")
        self.assertEqual(set(client.session.calls[0][2]), {
            "fid_cond_mrkt_div_code", "fid_cond_scr_div_code", "fid_div_cls_code",
            "fid_input_iscd", "fid_trgt_cls_code", "fid_trgt_exls_cls_code",
            "fid_input_price_1", "fid_input_price_2", "fid_vol_cnt"
        })


    def test_rate_limit_http_500_is_retried(self):
        class RetrySession:
            def __init__(self):
                self.calls = 0

            def get(self, url, headers, params, timeout):
                self.calls += 1
                if self.calls == 1:
                    response = FakeResponse({"rt_cd": "1", "msg1": "rate limit", "msg_cd": "EGW00201"})
                    response.ok = False
                    response.status_code = 500
                    response.text = "rate limit"
                    return response
                return FakeResponse({"rt_cd": "0", "output2": [{"symb": "MSFT"}]})

        client = FakeClient({})
        client.session = RetrySession()
        with patch("kis_universe.time.sleep", return_value=None):
            result = fetch_us_market_cap_candidates(client, "NAS")
        self.assertEqual(client.session.calls, 2)
        self.assertEqual(result.iloc[0]["symb"], "MSFT")


    def test_us_candidate_stops_when_kis_marks_final_page(self):
        class FinalPageSession:
            def __init__(self):
                self.calls = []

            def get(self, url, headers, params, timeout):
                self.calls.append((url, headers, params, timeout))
                return FakeResponse(
                    {"rt_cd": "0", "output2": [{"symb": "AAPL"}]},
                    headers={"tr_cont": "F"},
                )

        client = FakeClient({})
        client.session = FinalPageSession()
        with patch("kis_universe.time.sleep", return_value=None):
            result = fetch_us_market_cap_candidates(client, "NAS")
        self.assertEqual(len(client.session.calls), 1)
        self.assertEqual(list(result["symb"]), ["AAPL"])
        self.assertEqual(result.attrs["ranking_pages_fetched"], 1)
        self.assertFalse(result.attrs["ranking_pagination_stalled"])

    def test_us_candidate_paginates_when_kis_returns_continuation(self):
        class PaginatedSession:
            def __init__(self):
                self.calls = []

            def get(self, url, headers, params, timeout):
                self.calls.append((url, headers, params, timeout))
                if len(self.calls) == 1:
                    return FakeResponse(
                        {"rt_cd": "0", "output2": [{"symb": "AAPL"}]},
                        headers={"tr_cont": "M"},
                    )
                return FakeResponse(
                    {"rt_cd": "0", "output2": [{"symb": "MSFT"}]},
                    headers={"tr_cont": ""},
                )

        client = FakeClient({})
        client.session = PaginatedSession()
        with patch("kis_universe.time.sleep", return_value=None):
            result = fetch_us_market_cap_candidates(client, "NAS")
        self.assertEqual(list(result["symb"]), ["AAPL", "MSFT"])
        self.assertEqual(len(client.session.calls), 2)
        self.assertEqual(client.session.calls[1][1]["tr_cont"], "N")
        self.assertEqual(result.attrs["ranking_pages_fetched"], 2)
        self.assertEqual(result.attrs["ranking_page_diagnostics"][0]["response_tr_cont"], "M")
        self.assertEqual(result.attrs["ranking_page_diagnostics"][0]["rows"], 1)
        self.assertEqual(result.attrs["ranking_page_diagnostics"][0]["new_symbols"], 1)
        self.assertFalse(result.attrs["ranking_page_limit_reached"])


    def test_us_pagination_stops_when_kis_repeats_a_page(self):
        class RepeatedPageSession:
            def __init__(self):
                self.calls = 0

            def get(self, url, headers, params, timeout):
                self.calls += 1
                return FakeResponse(
                    {"rt_cd": "0", "output2": [{"symb": "AAPL"}]},
                    headers={"tr_cont": "M"},
                )

        client = FakeClient({})
        client.session = RepeatedPageSession()
        with patch("kis_universe.time.sleep", return_value=None):
            result = fetch_us_market_cap_candidates(client, "NAS")
        self.assertEqual(client.session.calls, 2)
        self.assertEqual(list(result["symb"]), ["AAPL"])
        self.assertEqual(result.attrs["ranking_pages_fetched"], 2)
        self.assertTrue(result.attrs["ranking_pagination_stalled"])
        self.assertFalse(result.attrs["ranking_page_limit_reached"])

    def test_krx_pagination_stops_when_kis_repeats_a_page(self):
        class RepeatedPageSession:
            def __init__(self):
                self.calls = 0

            def get(self, url, headers, params, timeout):
                self.calls += 1
                return FakeResponse(
                    {"rt_cd": "0", "output": [{"mksc_shrn_iscd": "005930"}]},
                    headers={"tr_cont": "M"},
                )

        client = FakeClient({})
        client.session = RepeatedPageSession()
        with patch("kis_universe.time.sleep", return_value=None):
            result = fetch_korea_market_cap_candidates(client)
        self.assertEqual(client.session.calls, 2)
        self.assertEqual(list(result["mksc_shrn_iscd"]), ["005930"])
        self.assertEqual(result.attrs["ranking_pages_fetched"], 2)
        self.assertTrue(result.attrs["ranking_pagination_stalled"])
        self.assertFalse(result.attrs["ranking_page_limit_reached"])

    def test_us_candidate_pagination_stops_at_sixty_pages(self):
        class LongPaginationSession:
            def __init__(self):
                self.calls = 0

            def get(self, url, headers, params, timeout):
                self.calls += 1
                return FakeResponse(
                    {"rt_cd": "0", "output2": [{"symb": f"SYM{self.calls}"}]},
                    headers={"tr_cont": "M"},
                )

        client = FakeClient({})
        client.session = LongPaginationSession()
        with patch("kis_universe.time.sleep", return_value=None):
            result = fetch_us_market_cap_candidates(client, "NAS", max_pages=60)
        self.assertEqual(client.session.calls, 60)
        self.assertEqual(len(result), 60)
        self.assertEqual(result.attrs["ranking_pages_fetched"], 60)
        self.assertTrue(result.attrs["ranking_page_limit_reached"])

    def test_kis_parameter_error_is_not_retried(self):
        class ErrorSession:
            def __init__(self):
                self.calls = 0

            def get(self, url, headers, params, timeout):
                self.calls += 1
                response = FakeResponse({
                    "rt_cd": "1",
                    "msg1": "ERROR INVALID PARAMETER",
                    "msg_cd": "OPSQ2001",
                })
                response.ok = False
                response.status_code = 500
                response.text = "parameter error"
                return response

        client = FakeClient({})
        client.session = ErrorSession()
        with patch("kis_universe.time.sleep", return_value=None):
            with self.assertRaisesRegex(Exception, "OPSQ2001"):
                fetch_us_market_cap_candidates(client, "NAS")
        self.assertEqual(client.session.calls, 1)

    def test_krx_market_segment_is_preserved(self):
        client = FakeClient({"rt_cd": "0", "output": [{
            "mksc_shrn_iscd": "123456", "stck_avls": "raw"
        }]})
        result = fetch_korea_market_cap_candidates(client, market="1001")
        self.assertEqual(result.loc[0, "ranking_market_code"], "1001")
        self.assertEqual(client.session.calls[0][2]["fid_input_iscd"], "1001")

    def test_invalid_exchange_is_rejected(self):
        with self.assertRaises(ValueError):
            fetch_us_market_cap_candidates(FakeClient({"rt_cd": "0", "output2": []}), "TSE")


    def test_normalization_usd_cap_and_conservative_fund_flag(self):
        raw = pd.DataFrame([
            {"listing_exchange": "NAS", "symb": "AAPL", "ename": "APPLE INC", "tomv": "2500000000000", "last": "250", "shar": "10000000000", "master_security_type": "2"},
            {"listing_exchange": "AMS", "symb": "VOO", "ename": "VANGUARD S&P 500 ETF", "tomv": "1000000000000", "last": "500", "shar": "2000000000"},
        ])
        result = normalize_market_cap_candidates(raw, min_cap_usd=1_000_000_000)
        self.assertEqual(result.loc[0, "market_cap_usd"], 2_500_000_000_000)
        self.assertTrue(bool(result.loc[0, "cap_threshold_pass"]))
        self.assertEqual(result.loc[0, "review_status"], "manual_review")
        self.assertEqual(result.loc[1, "review_status"], "exclude_candidate")
        self.assertEqual(result.loc[1, "instrument_type_guess"], "fund_or_etf_likely")
        self.assertTrue(pd.isna(result.loc[1, "cap_threshold_pass"]))
        self.assertIn("market_cap_threshold_not_applied_to_fund_or_etf", result.loc[1, "review_reason"])

    def test_parse_us_security_master_zip_extracts_symbol_and_type(self):
        row = [""] * 24
        row[0] = "US"
        row[4] = "AAPL"
        row[6] = "애플"
        row[7] = "APPLE INC"
        row[8] = "2"
        row[9] = "USD"
        row[17] = "Y"
        row[18] = "CN"
        row[19] = "IND42"
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("nasmst.cod", ("\t".join(row) + "\n").encode("cp949"))
        result = parse_us_security_master_zip(buffer.getvalue(), "NAS")
        self.assertEqual(result.loc[0, "symbol"], "AAPL")
        self.assertEqual(result.loc[0, "master_security_type"], "2")
        self.assertEqual(result.loc[0, "listing_exchange"], "NAS")
        self.assertEqual(result.loc[0, "master_dr_flag"], "Y")
        self.assertEqual(result.loc[0, "master_dr_country_code"], "CN")
        self.assertEqual(result.loc[0, "master_industry_code"], "IND42")

    def test_master_type_excludes_etp_and_index_from_stock_cap_screen(self):
        raw = pd.DataFrame([
            {"listing_exchange": "NAS", "symb": "ABC", "ename": "ABC CORP", "tomv": "100000000000", "last": "100", "shar": "1000000000", "master_security_type": "2"},
            {"listing_exchange": "NAS", "symb": "FND", "ename": "SAMPLE PRODUCT", "tomv": "100000000000", "last": "100", "shar": "1000000000", "master_security_type": "3"},
            {"listing_exchange": "NAS", "symb": "IDX", "ename": "SAMPLE INDEX", "tomv": "100000000000", "last": "100", "shar": "1000000000", "master_security_type": "1"},
        ])
        result = normalize_market_cap_candidates(raw)
        self.assertEqual(result.loc[0, "master_instrument_type"], "stock")
        self.assertTrue(bool(result.loc[0, "cap_threshold_pass"]))
        self.assertEqual(result.loc[1, "master_instrument_type"], "etp")
        self.assertTrue(pd.isna(result.loc[1, "cap_threshold_pass"]))
        self.assertEqual(result.loc[2, "instrument_type_guess"], "index_security_master")
        self.assertTrue(pd.isna(result.loc[2, "cap_threshold_pass"]))

    def test_adr_is_retained_but_unverified_cap_does_not_pass(self):
        raw = pd.DataFrame([{
            "listing_exchange": "NAS", "symb": "TME", 
            "ename": "TENCENT MUSIC ENTERTAINMENT GROUP ADR",
            "tomv": "50000000000", "last": "100", "shar": "1000000",
            "master_security_type": "2", "master_dr_flag": "Y",
            "master_dr_country_code": "CN",
        }])
        result = normalize_market_cap_candidates(raw)
        self.assertTrue(bool(result.loc[0, "is_adr_candidate"]))
        self.assertEqual(result.loc[0, "instrument_type_guess"], "adr_candidate_unverified")
        self.assertEqual(result.loc[0, "review_status"], "manual_review")
        self.assertTrue(pd.isna(result.loc[0, "market_cap_usd"]))
        self.assertTrue(pd.isna(result.loc[0, "cap_threshold_pass"]))
        self.assertIn("adr_market_cap_requires_depositary_ratio_verification", result.loc[0, "review_reason"])

    def test_depositary_country_code_marks_adr_without_name_hint(self):
        raw = pd.DataFrame([{
            "listing_exchange": "NAS", "symb": "XYZ", "ename": "EXAMPLE HOLDING INC",
            "tomv": "50000000000", "last": "100", "shar": "1000000",
            "master_security_type": "2", "master_dr_flag": "",
            "master_dr_country_code": "CN",
        }])
        result = normalize_market_cap_candidates(raw)
        self.assertTrue(bool(result.loc[0, "is_adr_candidate"]))
        self.assertEqual(result.loc[0, "instrument_type_guess"], "adr_candidate_unverified")
        self.assertEqual(result.loc[0, "master_dr_country_code"], "CN")

    def test_adr_cap_remains_pending_without_depositary_ratio(self):
        raw = pd.DataFrame([{
            "listing_exchange": "NYS", "symb": "BABA",
            "ename": "ALIBABA GROUP HOLDING LTD ADR",
            "tomv": "200000000000", "last": "100", "shar": "2000000000",
            "master_security_type": "2", "master_dr_flag": "Y",
            "master_dr_country_code": "CN",
        }])
        result = normalize_market_cap_candidates(raw)
        self.assertTrue(bool(result.loc[0, "is_adr_candidate"]))
        self.assertEqual(result.loc[0, "review_status"], "manual_review")
        self.assertTrue(pd.isna(result.loc[0, "market_cap_native"]))
        self.assertTrue(pd.isna(result.loc[0, "market_cap_usd"]))
        self.assertTrue(pd.isna(result.loc[0, "cap_threshold_pass"]))
        self.assertIn("adr_market_cap_requires_depositary_ratio_verification", result.loc[0, "review_reason"])

    def test_normalization_rejects_unverified_us_cap_unit(self):
        raw = pd.DataFrame([{
            "listing_exchange": "NAS", "symb": "XYZ", "ename": "EXAMPLE INC",
            "tomv": "2500000000000", "last": "100", "shar": "1000000",
        }])
        result = normalize_market_cap_candidates(raw)
        self.assertTrue(pd.isna(result.loc[0, "market_cap_native"]))
        self.assertTrue(pd.isna(result.loc[0, "market_cap_usd"]))
        self.assertTrue(pd.isna(result.loc[0, "cap_threshold_pass"]))
        self.assertIn("us_market_cap_not_verified_against_price_times_shares", result.loc[0, "review_reason"])

    def test_normalization_flags_etfs_and_non_common_securities(self):
        raw = pd.DataFrame([
            {"listing_exchange": "AMS", "symb": "RSP", "ename": "INVESCO EXCHANGE TRADED FD TR S&P 500 EQUAL WEIG", "tomv": "100000000000"},
            {"listing_exchange": "AMS", "symb": "SPMO", "ename": "INVESCO EXCHANGE TRADED FD TR II S&P 500 MOMENTU", "tomv": "22000000000"},
            {"listing_exchange": "NYS", "symb": "CCZ", "ename": "COMCAST HOLDINGS CORPORATION 2% CNV PREF SEC15/1", "tomv": "160000000000"},
            {"listing_exchange": "NYS", "symb": "TBB", "ename": "AT&T INC 5.35% GLOBAL NOTES DUE 01/11/2066 USD25", "tomv": "120000000000"},
        ])
        result = normalize_market_cap_candidates(raw)
        self.assertEqual(result.loc[0, "instrument_type_guess"], "fund_or_etf_likely")
        self.assertTrue(pd.isna(result.loc[0, "cap_threshold_pass"]))
        self.assertEqual(result.loc[1, "instrument_type_guess"], "fund_or_etf_likely")
        self.assertTrue(pd.isna(result.loc[1, "cap_threshold_pass"]))
        self.assertEqual(result.loc[2, "instrument_type_guess"], "non_common_security_likely")
        self.assertTrue(pd.isna(result.loc[2, "cap_threshold_pass"]))
        self.assertEqual(result.loc[3, "instrument_type_guess"], "non_common_security_likely")
        self.assertTrue(pd.isna(result.loc[3, "cap_threshold_pass"]))

    def test_normalization_krx_cap_requires_fx_for_usd(self):
        raw = pd.DataFrame([{
            "listing_exchange": "KRX",
            "mksc_shrn_iscd": "005930",
            "hts_kor_isnm": "삼성전자",
            "stck_avls": "4130000",
            "stck_prpr": "70000",
            "lstn_stcn": "5900000000",
            "master_security_type": "2",
        }])
        without_fx = normalize_market_cap_candidates(raw)
        self.assertEqual(without_fx.loc[0, "symbol"], "005930")
        self.assertEqual(without_fx.loc[0, "market_cap_native"], 413_000_000_000_000)
        self.assertTrue(pd.isna(without_fx.loc[0, "market_cap_usd"]))
        self.assertTrue(pd.isna(without_fx.loc[0, "cap_threshold_pass"]))
        with_fx = normalize_market_cap_candidates(raw, usdkrw=1400)
        self.assertAlmostEqual(with_fx.loc[0, "market_cap_usd"], 413_000_000_000_000 / 1400)
        self.assertTrue(bool(with_fx.loc[0, "cap_threshold_pass"]))

    def test_normalization_rejects_unverified_krx_cap_unit(self):
        raw = pd.DataFrame([{
            "listing_exchange": "KRX",
            "mksc_shrn_iscd": "005930",
            "hts_kor_isnm": "삼성전자",
            "stck_avls": "12949507",
            "stck_prpr": "70000",
            "lstn_stcn": "5900000000",
        }])
        result = normalize_market_cap_candidates(raw, usdkrw=1400)
        self.assertTrue(pd.isna(result.loc[0, "market_cap_native"]))
        self.assertTrue(pd.isna(result.loc[0, "market_cap_usd"]))
        self.assertTrue(pd.isna(result.loc[0, "cap_threshold_pass"]))
        self.assertIn("krx_market_cap_unit_not_verified", result.loc[0, "review_reason"])

    def test_empty_normalization_returns_master_review_columns(self):
        result = normalize_market_cap_candidates(pd.DataFrame())
        self.assertIn("master_instrument_type", result.columns)
        self.assertIn("master_security_type_code", result.columns)

    def test_normalization_rejects_invalid_fx(self):
        with self.assertRaises(ValueError):
            normalize_market_cap_candidates(pd.DataFrame([{"listing_exchange": "KRX"}]), usdkrw=0)


    def test_us_master_ranking_coverage_is_exchange_specific_and_not_cap_eligibility(self):
        master = pd.DataFrame([
            {"listing_exchange": "NAS", "symbol": "AAPL"},
            {"listing_exchange": "NAS", "symbol": "ETF1"},
            {"listing_exchange": "NYS", "symbol": "IBM"},
            {"listing_exchange": "AMS", "symbol": "FND"},
        ])
        rankings = pd.DataFrame([
            {"listing_exchange": "NAS", "symb": "AAPL"},
            {"listing_exchange": "NAS", "symb": "NEW"},
            {"listing_exchange": "NYS", "symb": "IBM"},
            {"listing_exchange": "AMS", "symb": "FND"},
        ])
        result = audit_us_master_ranking_coverage(master, rankings)
        nas = result[result["exchange"].eq("NAS")].iloc[0]
        self.assertEqual(nas["master_symbol_count"], 2)
        self.assertEqual(nas["ranking_symbol_count"], 2)
        self.assertEqual(nas["ranking_symbols_matched_to_master"], 1)
        self.assertEqual(nas["ranking_symbols_not_in_master"], 1)
        self.assertEqual(nas["master_symbols_not_in_ranking"], 1)
        self.assertEqual(nas["ranking_symbols_matched_to_master_pct"], 50.0)
        self.assertEqual(nas["master_symbols_returned_by_ranking_pct"], 50.0)
        self.assertIn("market cap/eligibility unknown", nas["coverage_interpretation"])
        self.assertEqual(result[result["exchange"].eq("NYS")].iloc[0]["master_symbols_not_in_ranking"], 0)

    def test_unranked_master_builder_returns_empty_frame_without_master(self):
        result = build_unranked_us_stock_master(pd.DataFrame(), pd.DataFrame())
        self.assertTrue(result.empty)


    def test_unranked_us_master_list_filters_ranked_symbols_and_non_stocks(self):
        master = pd.DataFrame([
            {"listing_exchange": "NAS", "symbol": "AAPL", "master_security_type": "2", "english_name": "Apple"},
            {"listing_exchange": "NAS", "symbol": "UNR", "master_security_type": "2", "english_name": "Unranked"},
            {"listing_exchange": "NAS", "symbol": "ETF1", "master_security_type": "3", "english_name": "Fund"},
            {"listing_exchange": "NYS", "symbol": "WRT1", "master_security_type": "4", "english_name": "Warrant"},
        ])
        rankings = pd.DataFrame([
            {"listing_exchange": "NAS", "symb": "AAPL"},
        ])
        result = build_unranked_us_stock_master(master, rankings)
        self.assertEqual(list(zip(result["listing_exchange"], result["symbol"])), [("NAS", "UNR")])
        self.assertTrue(pd.isna(result.iloc[0]["market_cap_usd"]))
        self.assertTrue(pd.isna(result.iloc[0]["cap_threshold_pass"]))
        self.assertEqual(result.iloc[0]["review_status"], "unranked_master_symbol_cap_unknown")


if __name__ == "__main__":
    unittest.main()
