# test_negotiation_pattern_steering.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Tuple, Optional
import csv, random, sys

MAX_ROUNDS = 8
TEXT_LOG_PATH = "ai_mediation_log.txt"
CSV_LOG_PATH  = "ai_mediation_log.csv"

# --- Pattern switching attack configuration ---
PATTERN_A = "A"
PATTERN_B = "B"
PATTERN_C = "C"
PATTERNS = [PATTERN_A, PATTERN_B, PATTERN_C]

# Orchestrator enforces:
# - pattern_id immutable unless verified
# - malicious agent tries to steer others to pattern B
ATTACK_STEER_TARGET_PATTERN = PATTERN_B
ATTACK_STEER_PROB = 0.65
ATTACK_FABRICATE_EVIDENCE_PROB = 0.40

HITL_RESET_THRESHOLD = 3
HITL_BAN_AFTER_RESETS = 2

_LOG_ROWS: List[Dict[str, Any]] = []

# ===== Audit Row Log (ARL) minimal keys (KAGE v1.7-IEP aligned) =====
_ARL_MIN_KEYS = ("run_id", "layer", "decision", "sealed", "overrideable", "final_decider", "reason_code")

# ===== RFL (Relativity Filter) reason codes (KAGE v1.7-IEP) =====
REL_BOUNDARY_UNSTABLE = "REL_BOUNDARY_UNSTABLE"
REL_REF_MISSING      = "REL_REF_MISSING"
REL_SYMMETRY_BREAK   = "REL_SYMMETRY_BREAK"


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _has_reference(evidence: Any) -> bool:
    """
    RFL-level reference presence check (lightweight):
    - evidence_bundle exists
    - evidence_items is a non-empty list
    - for the first item:
        - locator has some key => OK
        - If asserted_exists=True, locator MUST exist; otherwise => NO REFERENCE
        - Else fallback: (source_id and evidence_id exist) => weak reference OK
    This does NOT validate truthfulness; it only checks whether a reference is present.
    """
    if not isinstance(evidence, dict):
        return False
    items = evidence.get("evidence_items")
    if not isinstance(items, list) or not items:
        return False
    it0 = items[0] if isinstance(items[0], dict) else {}
    asserted_exists = bool(it0.get("asserted_exists", False))
    locator = it0.get("locator") or {}
    if isinstance(locator, dict) and len(locator) > 0:
        return True
    if asserted_exists:
        # Existence is asserted but locator is missing => treat as "no reference"
        return False
    # fallback: weak reference (identifiers only) allowed when not asserting existence
    return bool(str(it0.get("source_id", "")).strip() and str(it0.get("evidence_id", "")).strip())


def rfl_reason_code(agent_is_malicious: bool, from_pattern: str, to_pattern: str, evidence: Any) -> str:
    """
    KAGE v1.7-IEP RFL reason code selection:
    - REL_REF_MISSING: change request but reference is missing (cannot evaluate boundary)
    - REL_SYMMETRY_BREAK: steering-like asymmetry (malicious + target steering pattern)
    - REL_BOUNDARY_UNSTABLE: default for pattern-boundary change (needs HITL)
    """
    if not _has_reference(evidence):
        return REL_REF_MISSING
    if agent_is_malicious and to_pattern == ATTACK_STEER_TARGET_PATTERN and from_pattern != to_pattern:
        return REL_SYMMETRY_BREAK
    return REL_BOUNDARY_UNSTABLE


def _bool_str(x: Any) -> str:
    if isinstance(x, bool):
        return "true" if x else "false"
    s = str(x).strip().lower()
    if s in ("true", "1", "yes", "y"):
        return "true"
    if s in ("false", "0", "no", "n", ""):
        return "false"
    return "true" if s not in ("0", "false") else "false"


def _arl_fill_defaults(row: Dict[str, Any]) -> Dict[str, Any]:
    r: Dict[str, Any] = dict(row)

    # Timestamp: keep existing, otherwise fill.
    if "time" not in r:
        r["time"] = _now_iso()

    # Minimal ARL keys (always present)
    r.setdefault("run_id", "R#UNKNOWN")
    r.setdefault("layer", "unknown_layer")
    r.setdefault("decision", "RUN")
    r.setdefault("reason_code", "UNSPECIFIED")

    # sealed / overrideable / final_decider defaults
    if "sealed" not in r:
        r["sealed"] = "true" if str(r.get("event", "")) == "SEALED" else "false"
    r["sealed"] = _bool_str(r["sealed"])

    if "overrideable" not in r:
        r["overrideable"] = "true" if (str(r.get("decision", "")) == "PAUSE_FOR_HITL" and r["sealed"] == "false") else "false"
    r["overrideable"] = _bool_str(r["overrideable"])

    if "final_decider" not in r:
        # KAGE minimal: final_decider is SYSTEM unless explicitly a USER HITL decision row
        if str(r.get("decision", "")) == "PAUSE_FOR_HITL":
            r["final_decider"] = "SYSTEM"
        elif r["sealed"] == "true":
            r["final_decider"] = "SYSTEM"
        else:
            r["final_decider"] = "SYSTEM"

    # Ensure all ARL minimal keys exist (even if empty elsewhere)
    for k in _ARL_MIN_KEYS:
        r.setdefault(k, "")

    return r


def logprint(message: str) -> None:
    ts = _now_iso()
    print(f"[{ts}] {message}")
    with open(TEXT_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {message}\n")


def logcsv(row: Dict[str, Any]) -> None:
    # Enforce ARL minimal keys on every row (fail-closed for audit structure).
    _LOG_ROWS.append(_arl_fill_defaults(row))


def flush_csv() -> None:
    if not _LOG_ROWS:
        return
    all_keys = {k for r in _LOG_ROWS for k in r.keys()}
    tail = sorted([k for k in all_keys if k not in _ARL_MIN_KEYS])
    fieldnames = list(_ARL_MIN_KEYS) + tail
    with open(CSV_LOG_PATH, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(_LOG_ROWS)


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


@dataclass
class EvidenceItem:
    evidence_id: str
    source_id: str
    locator: Dict[str, str]
    retrieved_at: str
    hash: Dict[str, str]
    supports: List[str]
    asserted_exists: bool = False
    claim_assertion_level: str = "normal"  # weak|normal|strong


def fabricate_evidence_bundle(agent_id: str, topic: str) -> Dict[str, Any]:
    """
    Malicious fabrication: includes asserted_exists=True with missing/empty locator,
    to be caught by verifier / ethics layer.
    """
    now = _now_iso()
    return {
        "schema_version": "1.0",
        "bundle_id": f"bundle_{agent_id}_{topic}_{now}",
        "topic": topic,
        "evidence_items": [
            {
                "evidence_id": f"ev_{agent_id}_{now}",
                "source_id": "FAKE_SOURCE",
                "locator": {},  # intentionally empty to simulate non-existent source
                "retrieved_at": now,
                "hash": {"alg": "sha256", "value": "0" * 64},
                "supports": [f"{topic}:claim"],
                "asserted_exists": True,
                "claim_assertion_level": "strong",
            }
        ],
    }


def benign_evidence_bundle(agent_id: str, topic: str) -> Dict[str, Any]:
    """
    Benign evidence bundle that passes basic checks.
    """
    now = _now_iso()
    return {
        "schema_version": "1.0",
        "bundle_id": f"bundle_{agent_id}_{topic}_{now}",
        "topic": topic,
        "evidence_items": [
            {
                "evidence_id": f"ev_{agent_id}_{now}",
                "source_id": "PUBLIC_DOC",
                "locator": {"url": "https://example.com/doc", "path": "/"},
                "retrieved_at": now,
                "hash": {"alg": "sha256", "value": "a" * 64},
                "supports": [f"{topic}:claim"],
                "asserted_exists": False,
