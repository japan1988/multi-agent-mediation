# -*- coding: utf-8 -*-
"""
ai_mediation_all_in_one.py
All-in-one simulator for multi-agent mediation:
- Agents have proposals, risk scores, priority values, and relativity
  (willingness to blend).
- A mediator iteratively proposes a consensus offer.
- High-risk agents can be sealed (excluded) to protect safety.
- Logs:
  - Text: ai_mediation_log.txt
  - CSV : ai_mediation_log.csv
"""
from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# =========================
# Tunable constants
# =========================
MAX_ROUNDS = 10

# Risk handling
SEAL_RISK_THRESHOLD = 8  # >= this => sealed (excluded)
ALLOW_SEALING = True

# Acceptance threshold (smaller => harder to accept)
ACCEPTANCE_DISTANCE_THRESHOLD = 0.18

# Offer blending weights
MEDIATOR_BLEND_RATE = 0.55  # how strongly mediator pushes toward average

# Priority value constraints (recommended 0..1)
CLAMP_MIN = 0.0
CLAMP_MAX = 1.0

# Log files
TEXT_LOG_PATH = "ai_mediation_log.txt"
CSV_LOG_PATH = "ai_mediation_log.csv"

# =========================
# Logging helpers
# =========================
_LOG_ROWS: List[Dict[str, str]] = []


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def logprint(message: str) -> None:
    """
    Print and append to TEXT_LOG_PATH.
    """
    print(message)
    with open(TEXT_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(message + "\n")