"""Pytest configuration.

Ensures that the repository root is importable so that modules such as
``api`` and ``ui`` can be resolved when tests are executed.  Without this
adjustment the default ``sys.path`` configured by ``pytest`` omits the project
root which results in ``ModuleNotFoundError`` during collection.
"""

import sys
from pathlib import Path

# Add the repository root (the directory containing this file) to ``sys.path``
# if it is not already present.  This mirrors the behaviour of running Python
# scripts directly from the project root.
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# The integration test included with the repository requires external
# services and Windows-specific dependencies.  It is ignored so that the unit
# test suite can run in this execution environment.
collect_ignore = ["test_integration.py"]
