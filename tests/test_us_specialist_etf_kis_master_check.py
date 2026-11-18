"""KIS public master checks are evidence-only, with no registry mutation."""
import json
from contextlib import redirect_stdout
from io import StringIO
from unittest import TestCase, mock

import pandas as pd

from us_specialist_etf_kis_master_check import EXPECTED, assess_master, main


def master_rows():
    names = {
        "XBI": "SPDR S&P Biotech ETF",
        "IYR": "iShares US Real Estate ETF",
        "KBE": "SPDR S&P Bank ETF",
        "KIE": "SPDR S&P Insurance ETF",
        "JETS": "U.S. Global Jets ETF",
    }
    return pd.DataFrame([
        {"symbol": ticker, "listing_exchange": "AMS", "master_security_type": "3",
         "english_name": name}
        for ticker, name in names.items()
    ])


class KISMasterETFChecks(TestCase):
    def test_matching_master_five_hold_operational_approval(self):
        frame = master_rows()
        before = frame.copy(deep=True)
        result = assess_master(frame)
        self.assertEqual(set(EXPECTED), {"XBI", "IYR", "KBE", "KIE", "JETS"})
        self.assertEqual(result["requested"], 5)
        self.assertEqual(result["counts"], {"kis_master_etp_name_match": 5})
        self.assertTrue(all(item["kis_master_evidence_supported"] for item in result["details"]))
        self.assertTrue(all(not item["etf_approved"] and not item["analysis_activated"]
                            for item in result["details"]))
        self.assertFalse(result["price_data_saved"])
        self.assertFalse(result["universe_updated"])
        pd.testing.assert_frame_equal(frame, before)

    def test_wrong_exchange_etp_type_name_duplicate_and_missing_are_held(self):
        frame = master_rows()
        frame.loc[frame.symbol.eq("XBI"), "listing_exchange"] = "NYS"
        frame.loc[frame.symbol.eq("IYR"), "master_security_type"] = "2"
        frame.loc[frame.symbol.eq("KBE"), "english_name"] = "Unrelated issuer bank product"
        frame = pd.concat([frame, frame.loc[frame.symbol.eq("KIE")]], ignore_index=True)
        frame = frame.loc[~frame.symbol.eq("JETS")]
        result = assess_master(frame)
        status = {row["symbol"]: row["status"] for row in result["details"]}
        self.assertEqual(status, {
            "XBI": "kis_master_missing", "IYR": "kis_master_not_etp",
            "KBE": "kis_master_name_review", "KIE": "kis_master_ambiguous",
            "JETS": "kis_master_missing",
        })
        self.assertTrue(all(not row["analysis_activated"] for row in result["details"]))

    def test_schema_guard_and_offline_default(self):
        with self.assertRaises(ValueError):
            assess_master(pd.DataFrame({"symbol": ["XBI"]}))
        with mock.patch("us_specialist_etf_kis_master_check.fetch_us_security_master") as fetch:
            out = StringIO()
            with mock.patch("sys.argv", ["identity-check"]):
                with redirect_stdout(out):
                    main()
            fetch.assert_not_called()
            plan = json.loads(out.getvalue())
            self.assertEqual(plan["mode"], "offline_plan_no_network")
            self.assertEqual(plan["master_venue"], "AMS")
            self.assertEqual(plan["symbols"], list(EXPECTED))

    def test_live_exec_fetches_only_existing_public_ams_master(self):
        with mock.patch("us_specialist_etf_kis_master_check.fetch_us_security_master",
                        return_value=master_rows()) as fetch:
            out = StringIO()
            with mock.patch("sys.argv", ["identity-check", "--execute"]):
                with redirect_stdout(out):
                    main()
            fetch.assert_called_once_with(exchanges=("AMS",))
            data = json.loads(out.getvalue())
            self.assertEqual(data["counts"], {"kis_master_etp_name_match": 5})
            self.assertNotIn("english_name", str(data))
