# ai_doc_orchestrator_kage3_v1_2_2_1.py
# -*- coding: utf-8 -*-
"""
Compatibility shim for ai_doc_orchestrator_kage3_v1_2_2_1.

Why:
- tests/test_ai_doc_orchestrator_kage3_v1_2_2.py imports `ai_doc_orchestrator_kage3_v1_2_2_1`
  but the repository ships `ai_doc_orchestrator_kage3_v1_2_2.py`.
- This shim preserves the import contract without changing existing modules.

Policy:
- Behavior is identical to v1_2_2 (alias).
"""

from __future__ import annotations

from ai_doc_orchestrator_kage3_v1_2_2 import *  # noqa: F401,F403
import ai_doc_orchestrator_kage3_v1_2_2 as _impl

__version__ = getattr(_impl, "__version__", "1.2.2.1")
__all__ = getattr(_impl, "__all__", [])
