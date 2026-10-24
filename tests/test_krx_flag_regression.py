import unittest

from krx_master import parse_krx_master_bytes
from test_krx_master import make_record


class KRXFlagRegressionTests(unittest.TestCase):
    def test_numeric_preferred_flag_excludes_non_common_security(self):
        payload = b"".join([
            make_record("KOSPI", "005930", "Samsung", group="ST", preferred="0"),
            make_record("KOSPI", "005935", "Samsung preferred", group="ST", preferred="1"),
        ])
        result = parse_krx_master_bytes(payload, "KOSPI").set_index("symbol")
        self.assertFalse(bool(result.loc["005930", "is_preferred_share"]))
        self.assertTrue(bool(result.loc["005935", "is_preferred_share"]))
        self.assertEqual(result.loc["005935", "instrument_class"], "unknown")

    def test_spac_flag_excludes_kosdaq_spac_candidate(self):
        payload = make_record("KOSDAQ", "999999", "Example SPAC", group="ST", spac="Y")
        result = parse_krx_master_bytes(payload, "KOSDAQ")
        self.assertTrue(bool(result.loc[0, "is_spac_candidate"]))
        self.assertEqual(result.loc[0, "instrument_class"], "unknown")


if __name__ == "__main__":
    unittest.main()
