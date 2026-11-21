"""Start the deployed Streamlit entry point in a fresh interpreter."""

from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DashboardStartupTests(unittest.TestCase):
    def test_clean_process_renders_dashboard_navigation(self):
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                """
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

with patch(
    "requests.sessions.Session.request",
    side_effect=AssertionError("Dashboard startup must use saved data"),
):
    dashboard = AppTest.from_file("app.py", default_timeout=60).run()

if dashboard.exception:
    raise RuntimeError(dashboard.exception[0].message)

dashboard.radio(key="analysis_navigation_choice")
""",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=90,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
