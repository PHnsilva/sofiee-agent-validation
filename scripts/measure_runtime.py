"""Measure the deterministic validation handler without external access."""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_runtime.contracts import TOOLS
from agent_runtime.validation import execute


def main() -> int:
    request = TOOLS["validation.verifyClaim"]["examples"]["validInput"]
    iterations = 1000
    start = time.perf_counter()
    for _ in range(iterations):
        result = execute("validation.verifyClaim", request)
        if result.get("verdict") != "inconclusive":
            raise RuntimeError("Unexpected result while measuring local handler.")
    elapsed_ms = (time.perf_counter() - start) * 1000
    print(f"handler_calls={iterations} elapsed_ms={elapsed_ms:.2f} average_ms={elapsed_ms / iterations:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
