"""Regression checks for crosshair continuity across price and volume panels."""
from pathlib import Path
import unittest


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


class ChartCrosshairRegressionTests(unittest.TestCase):
    def test_price_and_volume_axes_use_dotted_cross_panel_spikes(self):
        source = APP_PATH.read_text(encoding="utf-8")
        self.assertGreaterEqual(source.count('spikemode="across"'), 4)
        self.assertGreaterEqual(source.count('spikedash="dot"'), 4)
        self.assertGreaterEqual(source.count('spikesnap="cursor"'), 4)
        self.assertIn('hovermode="x", dragmode="pan", hoverdistance=-1', source)
        self.assertIn('hoverlabel=dict(align="left", namelength=-1)', source)
        self.assertIn('title_text="가격", fixedrange=True', source)
        self.assertIn('title_text="거래량", fixedrange=True', source)
        self.assertIn('xaxis2=dict(', source)


if __name__ == "__main__":
    unittest.main()
