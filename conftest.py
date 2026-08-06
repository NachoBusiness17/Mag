"""Project-wide pytest setup."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def pytest_configure(config):
    """Keep concurrent Windows test runs out of each other's temp directory."""
    if not config.option.basetemp:
        config.option.basetemp = str(ROOT / "agents" / f"pytest-tmp-{os.getpid()}")
