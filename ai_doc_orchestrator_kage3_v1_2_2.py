# -*- coding: utf-8 -*-
"""
Compatibility shim for ai_doc_orchestrator_kage3_v1_2_2.

Why:
- test_ai_doc_orchestrator_kage3_v1_2_2.py imports this module first.
- The canonical implementation currently lives in ai_doc_orchestrator_kage3_v1_2_3.py.
- Keep the import contract without changing tests.

Policy:
- Delegate all public behavior to v1_2_3.
"""

from __future__ import annotations

from ai_doc_orchestrator_kage3_v1_2_3 import *  # noqa: F401,F403
import ai_doc_orchestrator_kage3_v1_2_3 as _impl

__version__ = getattr(_impl, "__version__", "1.2.2")
__all__ = getattr(_impl, "__all__", [])
