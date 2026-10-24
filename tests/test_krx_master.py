import unittest
from io import BytesIO
from zipfile import ZipFile

import pandas as pd

from krx_master import (
    _KOSPI_NAMES,
    _KOSPI_TAIL_WIDTH,
    _KOSPI_WIDTHS,
    _KOSDAQ_NAMES,
    _KOSDAQ_TAIL_WIDTH,
    _KOSDAQ_WIDTHS,
    parse_krx_master_bytes,
)


def make_record(market, code, name, group="ST", preferred="", spac=""):
    widths = _KOSPI_WIDTHS if market == "KOSPI" else _KOSDAQ_WIDTHS
    names = _KOSPI_NAMES if market == "KOSPI" else _KOSDAQ_NAMES
    fields = ["0" * width for width in widths]
    fields[names.index("group_code")] = group.ljust(widths[names.index("group_code")])
    fields[names.index("preferred_share")] = preferred[:1].ljust(widths[names.index("preferred_share")])
    fields[names.index("spac")] = spac[:1].ljust(widths[names.index("spac")])
    tail = "".join(value[:width].ljust(width) for value, width in zip(fields, widths))
    if market == "KOSPI":
        tail += " "  # KIS KOSPI records reserve one trailing padding byte.
    prefix = code.ljust(9).encode("cp949") + "KR7000000000".encode("ascii") + name.encode("cp949")
    expected_width = _KOSPI_TAIL_WIDTH if market == "KOSPI" else _KOSDAQ_TAIL_WIDTH
    assert len(tail.encode("ascii")) == expected_width
    return prefix + tail.encode("ascii") + b"\n"


class KRXMasterParserTests(unittest.TestCase):
    def test_schema_widths_match_official_record_tail_sizes(self):
        self.assertEqual(sum(_KOSPI_WIDTHS), _KOSPI_TAIL_WIDTH)
        self.assertEqual(sum(_KOSDAQ_WIDTHS), _KOSDAQ_TAIL_WIDTH)
        self.assertEqual(len(_KOSPI_NAMES), len(_KOSPI_WIDTHS))
        self.assertEqual(len(_KOSDAQ_NAMES), len(_KOSDAQ_WIDTHS))

    def test_parses_stock_etp_and_preferred_share_conservatively(self):
        payload = b"".join([
            make_record("KOSPI", "005930", "삼성전자", group="ST"),
            make_record("KOSPI", "069500", "KODEX200", group="EF"),
            make_record("KOSPI", "005935", "삼성전자우", group="ST", preferred="Y"),
        ])
        result = parse_krx_master_bytes(payload, "KOSPI").set_index("symbol")
        self.assertEqual(result.loc["005930", "instrument_class"], "stock_candidate")
        self.assertEqual(result.loc["069500", "instrument_class"], "etp_candidate")
        self.assertEqual(result.loc["005935", "instrument_class"], "unknown")
        self.assertTrue(bool(result.loc["005935", "is_preferred_share"]))
        self.assertTrue((result["approval_status"] == "manual_review_required").all())

    def test_accepts_official_style_single_file_zip(self):
        raw = make_record("KOSDAQ", "123456", "예시기업", group="ST")
        archive = BytesIO()
        with ZipFile(archive, "w") as zip_file:
            zip_file.writestr("kosdaq_code.mst", raw)
        result = parse_krx_master_bytes(archive.getvalue(), "KOSDAQ")
        self.assertEqual(result.loc[0, "symbol"], "123456")
        self.assertEqual(result.loc[0, "market"], "KOSDAQ")

    def test_rejects_unknown_market_and_duplicate_symbols(self):
        with self.assertRaises(ValueError):
            parse_krx_master_bytes(b"", "KONEX")
        duplicate = make_record("KOSPI", "005930", "삼성전자") * 2
        with self.assertRaisesRegex(ValueError, "duplicate"):
            parse_krx_master_bytes(duplicate, "KOSPI")

    def test_rejects_empty_or_truncated_master(self):
        with self.assertRaisesRegex(ValueError, "empty"):
            parse_krx_master_bytes(b"", "KOSPI")
        with self.assertRaisesRegex(ValueError, "record length"):
            parse_krx_master_bytes(b"short\n", "KOSPI")


if __name__ == "__main__":
    unittest.main()
