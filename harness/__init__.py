"""External agent harnesses (Grok CLI headless, Hermes Agent)."""
from .grok_cli import escalate_via_harness, harness_available
from .hermes_cli import (
    escalate_via_hermes,
    find_hermes,
    hermes_status,
    harness_available as hermes_available,
)

__all__ = [
    "escalate_via_harness",
    "harness_available",
    "escalate_via_hermes",
    "hermes_available",
    "find_hermes",
    "hermes_status",
]
