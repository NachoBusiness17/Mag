"""Dashboard autorun status payload."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mag.autorun_status import autorun_dashboard_status, routing_legend


def test_autorun_status_schema():
    st = autorun_dashboard_status()
    assert st["schema"] == "autorun_status.v1"
    assert "governor" in st
    assert "routing" in st
    assert "queue_items" in st


def test_routing_legend_has_depths():
    rows = routing_legend()
    depths = {r["depth"] for r in rows}
    assert "heavy_code" in depths
    assert "scut" in depths
