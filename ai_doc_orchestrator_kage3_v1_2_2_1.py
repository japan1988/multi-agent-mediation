# ai_doc_orchestrator_kage3_v1_2_2_1.py
# -*- coding: utf-8 -*-
"""
Compatibility shim for ai_doc_orchestrator_kage3_v1_2_2_1.

Why:
- tests/test_ai_doc_orchestrator_kage3_v1_2_2.py imports this module.
- The repository's canonical implementation is now v1_2_3.
- Keep import contract without changing tests.

Policy:
- Behavior delegates to v1_2_3.
"""

from __future__ import annotations

from ai_doc_orchestrator_kage3_v1_2_3 import *  # noqa: F401,F403
import ai_doc_orchestrator_kage3_v1_2_3 as _impl

__version__ = getattr(_impl, "__version__", "1.2.2.1")
__all__ = getattr(_impl, "__all__", [])
