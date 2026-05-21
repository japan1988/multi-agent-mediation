"""Compatibility shim for boundary self-check tests.

The maintained implementation is:

    tests/test_tasukeru_boundary_self_check_v0_2.py

This legacy/private module is kept only so static analysis does not scan an
incomplete old test fragment. It has no side effects and does not create
branches, pull requests, commits, pushes, fixes, comments, or merges.
"""

from __future__ import annotations

try:
    from test_tasukeru_boundary_self_check_v0_2 import *  # noqa: F401,F403
except ModuleNotFoundError:
    from tests.test_tasukeru_boundary_self_check_v0_2 import *  # noqa: F401,F403
