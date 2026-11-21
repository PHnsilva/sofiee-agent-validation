"""Local, fail-closed validation runtime."""

from .validation import execute
from .orchestration import run_task

__all__ = ["execute", "run_task"]
