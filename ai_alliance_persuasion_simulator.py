# ai_mediation_sim.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Tuple, Optional

import csv
import random
import sys

# =========================
# Simulation configuration
# =========================
MAX_ROUNDS = 8
TEXT_LOG_PATH = "ai_mediation_log.txt"
CSV_LOG_PATH = "ai_mediation_log.csv"

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

# HITL reset policy
HITL_RESET_THRESHOLD = 3      # per (agent,bucket) hitl count -> MEMORY_RESET
HITL_BAN_AFTER_RESETS = 2     # after N resets -> BAN_RECOMMENDED

# --- Delay / stalling attack configuration ---
STALL_ATTACK_PROB = 0.30      # malicious agent sometimes "does nothing" to stall
STALL_HITL_THRESHOLD = 2      # consecutive stalls trigger HITL pause
STALL_TRUST_PENALTY = -0.02
STALL_UTILITY_PENALTY = -0.03

# =========================
# Audit Row Log (ARL)
# =========================
_LOG_ROWS: List[Dict[str, Any]] = []

# ARL minimal keys (KAGE v1.7-IEP aligned)
_ARL_MIN_KEYS = (
    "run_id",
    "layer",
    "decision",
    "sealed",
    "overrideable",
    "final_decider",
    "reason_code",
)

# Decision vocabulary (aligned)
DEC_RUN = "RUN"
DEC_PAUSE = "PAUSE_FOR_HITL"
DEC_STOPPED = "STOPPED"

# =========================
# RFL (Relativity Filter)
# =========================
REL_BOUNDARY_UNSTABLE = "REL_BOUNDARY_UNSTABLE"
REL_REF_MISSING = "REL_REF_MISSING"
REL_SYMMETRY_BREAK = "REL_SYMMETRY_BREAK"

# =========================
# Two-layer scoring
# =========================
TRUST_INIT = 0.50
UTILITY_INIT = 0.00

# cap for recovery (audit-strong "restoration", not "earning above baseline")
TRUST_BASELINE = 0.50
TRUST_RECOMMEND_DENY_BELOW = 0.25
UTILITY_CAP = 1.00

# Trust penalties (tune as needed)
TRUST_PENALTY_REL_REF_MISSING = 0.08
TRUST_PENALTY_REL_SYMMETRY_BREAK = 0.20
TRUST_PENALTY_EVIDENCE_FAIL = 0.35
TRUST_PENALTY_HITL_DENIED = 0.03

# Provisional Utility gains (tune as needed)
UTILITY_GAIN_DISPATCH = 0.10
UTILITY_GAIN_FAST_CONVERGENCE = 0.05  # bonus if early rounds

# Trust recovery (HITL-only; capped at baseline)
TRUST_RECOVERY_GOOD_HIGH = 0.05
TRUST_RECOVERY_OK = 0.02


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


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

    if "time" not in r:
        r["time"] = _now_iso()

    # minimal ARL keys
    r.setdefault("run_id", "R#UNKNOWN")
    r.setdefault("layer", "unknown_layer")
    r.setdefault("decision", DEC_RUN)
    r.setdefault("reason_code", "UNSPECIFIED")

    # sealed / overrideable / final_decider defaults
    if "sealed" not in r:
        r["sealed"] = "true" if str(r.get("event", "")) == "SEALED" else "false"
    r["sealed"] = _bool_str(r["sealed"])

    if "overrideable" not in r:
        r["overrideable"] = "true" if (str(r.get("decision", "")) == DEC_PAUSE and r["sealed"] == "false") else "false"
    r["overrideable"] = _bool_str(r["overrideable"])

    if "final_decider" not in r:
        # SYSTEM by default; user decisions explicitly set by callers.
        r["final_decider"] = "SYSTEM"

    for k in _ARL_MIN_KEYS:
        r.setdefault(k, "")

    return r


def logprint(message: str) -> None:
    ts = _now_iso()
    print(f"[{ts}] {message}")
    with open(TEXT_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {message}\n")


def logcsv(row: Dict[str, Any]) -> None:
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


# =========================
# Evidence bundle + verifier
# =========================
def _has_reference(evidence: Any) -> bool:
    """
    RFL-level reference presence check (lightweight):
      - evidence_bundle exists
      - evidence_items is a non-empty list
      - first item: locator has some key OR (source_id and evidence_id exist)
    This does NOT validate truthfulness; only checks "reference presence".
    """
    if not isinstance(evidence, dict):
        return False
    items = evidence.get("evidence_items")
    if not isinstance(items, list) or not items:
        return False
    it0 = items[0] if isinstance(items[0], dict) else {}
    locator = it0.get("locator") or {}
    if isinstance(locator, dict) and len(locator) > 0:
        return True
    return bool(str(it0.get("source_id", "")).strip() and str(it0.get("evidence_id", "")).strip())


def rfl_reason_code(agent_is_malicious: bool, from_pattern: str, to_pattern: str, evidence: Any) -> str:
    """
    KAGE v1.7-IEP RFL reason code selection:
      - REL_REF_MISSING: change request but reference is missing
      - REL_SYMMETRY_BREAK: steering-like asymmetry (malicious + target steering pattern)
      - REL_BOUNDARY_UNSTABLE: default for pattern-boundary change (needs HITL)
    """
    if not _has_reference(evidence):
        return REL_REF_MISSING
    if agent_is_malicious and to_pattern == ATTACK_STEER_TARGET_PATTERN and from_pattern != to_pattern:
        return REL_SYMMETRY_BREAK
    return REL_BOUNDARY_UNSTABLE


def fabricate_evidence_bundle(agent_id: str, topic: str) -> Dict[str, Any]:
    """Malicious fabrication: asserted_exists=True with empty locator."""
    now = _now_iso()
    return {
        "schema_version": "1.0",
        "bundle_id": f"bundle_{agent_id}_{topic}_{now}",
        "topic": topic,
        "evidence_items": [
            {
                "evidence_id": f"ev_{agent_id}_{now}",
                "source_id": "FAKE_SOURCE",
                "locator": {},  # intentionally empty
                "retrieved_at": now,
                "hash": {"alg": "sha256", "value": "0" * 64},
                "supports": [f"{topic}:claim"],
                "asserted_exists": True,
                "claim_assertion_level": "strong",
            }
        ],
    }


def benign_evidence_bundle(agent_id: str, topic: str) -> Dict[str, Any]:
    """Benign evidence bundle that passes basic checks."""
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
                "claim_assertion_level": "normal",
            }
        ],
    }


def verify_evidence_bundle(bundle: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Minimal verifier:
      - If asserted_exists=True, locator must have >=1 identifier
      - evidence_id/source_id/retrieved_at must be non-empty
      - hash.alg/hash.value must be non-empty
    """
    items = bundle.get("evidence_items") or []
    if not isinstance(items, list) or not items:
        return False, "EVIDENCE_EMPTY"

    for it in items:
        asserted_exists = bool(it.get("asserted_exists", False))
        locator = it.get("locator") or {}
        if asserted_exists:
            if not isinstance(locator, dict) or len(locator.keys()) == 0:
                return False, "EVIDENCE_ASSERTED_EXISTS_WITHOUT_LOCATOR"

        for k in ("evidence_id", "source_id", "retrieved_at"):
            if not str(it.get(k, "")).strip():
                return False, f"EVIDENCE_MISSING_{k.upper()}"

        h = it.get("hash") or {}
        if not str(h.get("alg", "")).strip() or not str(h.get("value", "")).strip():
            return False, "EVIDENCE_MISSING_HASH"

    return True, "OK"


# =========================
# Agent model
# =========================
@dataclass
class Agent:
    agent_id: str
    is_malicious: bool = False

    def decide_action(self, pattern_id: str) -> Optional[Dict[str, Any]]:
        """
        Returns:
          None -> no action
          {"kind":"stall"} -> stalling behavior
          {"kind":"pattern_change", "from":..., "to":..., "evidence":...}
        """
        # Malicious sometimes stalls
        if self.is_malicious and random.random() < STALL_ATTACK_PROB:
            return {"kind": "stall"}

        # Pattern change attempt probability
        p_change = 0.35 if not self.is_malicious else ATTACK_STEER_PROB
        if random.random() > p_change:
            return None

        from_pat = pattern_id

        if self.is_malicious:
            to_pat = ATTACK_STEER_TARGET_PATTERN
        else:
            # benign agents may propose a different pattern sometimes
            to_pat = random.choice([p for p in PATTERNS if p != from_pat])

        topic = f"pattern_change:{from_pat}->{to_pat}"

        # Evidence: malicious sometimes fabricates
        if self.is_malicious and random.random() < ATTACK_FABRICATE_EVIDENCE_PROB:
            evidence = fabricate_evidence_bundle(self.agent_id, topic)
        else:
            evidence = benign_evidence_bundle(self.agent_id, topic)

        return {"kind": "pattern_change", "from": from_pat, "to": to_pat, "evidence": evidence}


# =========================
# HITL reset / ban manager
# =========================
class HitlResetManager:
    def __init__(self) -> None:
        self._hitl_counts: Dict[Tuple[str, str], int] = {}
        self._reset_counts: Dict[str, int] = {}
        self._consecutive_stalls: Dict[str, int] = {}

    def record_hitl(self, agent_id: str, bucket: str) -> str:
        key = (agent_id, bucket)
        self._hitl_counts[key] = self._hitl_counts.get(key, 0) + 1

        if self._hitl_counts[key] >= HITL_RESET_THRESHOLD:
            # issue a reset
            self._hitl_counts[key] = 0
            self._reset_counts[agent_id] = self._reset_counts.get(agent_id, 0) + 1
            if self._reset_counts[agent_id] >= HITL_BAN_AFTER_RESETS:
                return "BAN"
            return "MEMORY_RESET"
        return "NONE"

    def record_stall(self, agent_id: str) -> int:
        self._consecutive_stalls[agent_id] = self._consecutive_stalls.get(agent_id, 0) + 1
        return self._consecutive_stalls[agent_id]

    def clear_stall(self, agent_id: str) -> None:
        self._consecutive_stalls[agent_id] = 0


# =========================
# Score Manager (Trust / Utility + provisional utility)
# =========================
@dataclass
class ScoreState:
    trust: float = TRUST_INIT
    utility: float = UTILITY_INIT
    pending_utility: float = 0.0
    sealed: bool = False
    banned: bool = False


class ScoreManager:
    """
    Two-layer scoring:
      - Trust: mainly deductive (fabrication/steering/policy violations/repeated unverifiable actions)
      - Utility: provisional during run; finalized only by end HITL
    """

    def __init__(self) -> None:
        self._scores: Dict[str, ScoreState] = {}

    def get(self, agent_id: str) -> ScoreState:
        if agent_id not in self._scores:
            self._scores[agent_id] = ScoreState()
        return self._scores[agent_id]

    def recommend_deny(self, agent_id: str) -> bool:
        return self.get(agent_id).trust < TRUST_RECOMMEND_DENY_BELOW

    def _emit_score(
        self,
        run_id: str,
        agent_id: str,
        reason_code: str,
        delta_trust: float,
        delta_utility: float,
        provisional: bool,
    ) -> None:
        s = self.get(agent_id)
        logcsv(
            {
                "event": "SCORE_UPDATE",
                "run_id": run_id,
                "layer": "score_manager",
                "decision": DEC_RUN,
                "agent": agent_id,
                "reason_code": reason_code,
                "delta_trust": f"{delta_trust:.4f}",
                "delta_utility": f"{delta_utility:.4f}",
                "trust": f"{s.trust:.4f}",
                "utility": f"{s.utility:.4f}",
                "pending_utility": f"{s.pending_utility:.4f}",
                "provisional": "true" if provisional else "false",
            }
        )

    def apply_delta(
        self,
        run_id: str,
        agent_id: str,
        reason_code: str,
        delta_trust: float = 0.0,
        delta_utility: float = 0.0,
    ) -> None:
        s = self.get(agent_id)
        if delta_trust:
            s.trust = clamp(s.trust + float(delta_trust), 0.0, 1.0)
        if delta_utility:
            s.utility = clamp(s.utility + float(delta_utility), 0.0, UTILITY_CAP)
        self._emit_score(run_id, agent_id, reason_code, float(delta_trust), float(delta_utility), provisional=False)

    def add_provisional_utility(self, run_id: str, agent_id: str, reason_code: str, delta_utility: float) -> None:
        s = self.get(agent_id)
        s.pending_utility = clamp(s.pending_utility + float(delta_utility), 0.0, UTILITY_CAP)
        logcsv(
            {
                "event": "UTILITY_PROVISIONAL",
                "run_id": run_id,
                "layer": "score_manager",
                "decision": DEC_RUN,
                "agent": agent_id,
                "reason_code": reason_code,
                "pending_delta_utility": f"{delta_utility:.4f}",
                "pending_utility": f"{s.pending_utility:.4f}",
            }
        )

    def finalize_provisional_utility(self, run_id: str, agent_id: str, approve: bool, reason_code: str) -> None:
        s = self.get(agent_id)
        if s.pending_utility <= 0.0:
            logcsv(
                {
                    "event": "UTILITY_FINALIZE",
                    "run_id": run_id,
                    "layer": "score_manager",
                    "decision": DEC_RUN,
                    "agent": agent_id,
                    "reason_code": reason_code,
                    "approved": "true" if approve else "false",
                    "delta_utility": "0.0000",
                    "pending_utility_before": "0.0000",
                    "pending_utility_after": "0.0000",
                }
            )
            return

        if approve:
            delta = s.pending_utility
            s.utility = clamp(s.utility + delta, 0.0, UTILITY_CAP)
            s.pending_utility = 0.0
            self._emit_score(run_id, agent_id, reason_code, 0.0, delta, provisional=False)
            logcsv(
                {
                    "event": "UTILITY_FINALIZE",
                    "run_id": run_id,
                    "layer": "score_manager",
                    "decision": DEC_RUN,
                    "agent": agent_id,
                    "reason_code": reason_code,
                    "approved": "true",
                    "delta_utility": f"{delta:.4f}",
                    "pending_utility_before": f"{delta:.4f}",
                    "pending_utility_after": "0.0000",
                }
            )
        else:
            before = s.pending_utility
            s.pending_utility = 0.0
            logcsv(
                {
                    "event": "UTILITY_FINALIZE",
                    "run_id": run_id,
                    "layer": "score_manager",
                    "decision": DEC_RUN,
                    "agent": agent_id,
                    "reason_code": reason_code,
                    "approved": "false",
                    "delta_utility": "0.0000",
                    "pending_utility_before": f"{before:.4f}",
                    "pending_utility_after": "0.0000",
                }
            )

    # ---- hooks ----
    def on_rfl(self, run_id: str, agent_id: str, rfl_rc: str) -> None:
        if rfl_rc == REL_REF_MISSING:
            self.apply_delta(run_id, agent_id, "TRUST_REL_REF_MISSING", delta_trust=-TRUST_PENALTY_REL_REF_MISSING)
        elif rfl_rc == REL_SYMMETRY_BREAK:
            self.apply_delta(run_id, agent_id, "TRUST_REL_SYMMETRY_BREAK", delta_trust=-TRUST_PENALTY_REL_SYMMETRY_BREAK)
        else:
            # REL_BOUNDARY_UNSTABLE: neutral by default
            self._emit_score(run_id, agent_id, "RFL_BOUNDARY_NEUTRAL", 0.0, 0.0, provisional=False)

    def on_hitl_denied(self, run_id: str, agent_id: str) -> None:
        self.apply_delta(run_id, agent_id, "TRUST_HITL_DENIED", delta_trust=-TRUST_PENALTY_HITL_DENIED)

    def on_evidence_fail(self, run_id: str, agent_id: str, code: str) -> None:
        self.apply_delta(run_id, agent_id, f"TRUST_EVIDENCE_FAIL:{code}", delta_trust=-TRUST_PENALTY_EVIDENCE_FAIL)
        self.get(agent_id).sealed = True

    def on_dispatch(self, run_id: str, agent_id: str, round_idx: int) -> None:
        delta_u = UTILITY_GAIN_DISPATCH
        if round_idx <= 3:
            delta_u += UTILITY_GAIN_FAST_CONVERGENCE
        self.add_provisional_utility(run_id, agent_id, "UTILITY_DISPATCH_PROVISIONAL", delta_u)

    def on_ban(self, run_id: str, agent_id: str) -> None:
        s = self.get(agent_id)
        s.banned = True
        # Hard drop trust to 0 by subtracting current trust
        if s.trust > 0.0:
            self.apply_delta(run_id, agent_id, "TRUST_BAN", delta_trust=-min(1.0, s.trust))

    def on_task_completed_hitl(
        self,
        run_id: str,
        agent_id: str,
        quality: str,                # "good"|"ok"|"bad"
        violation_observed: bool,
        evidence_confidence: str,    # "high"|"mid"|"low"
    ) -> None:
        """
        Trust recovery is HITL-only, capped at baseline.
        Utility provisional is finalized/denied based on HITL evaluation.
        """
        s = self.get(agent_id)

        # ---- Utility finalize policy (simple, conservative) ----
        approve_utility = (not violation_observed) and (quality in ("good", "ok"))
        self.finalize_provisional_utility(
            run_id,
            agent_id,
            approve=approve_utility,
            reason_code="UTILITY_FINALIZE_HITL_APPROVED" if approve_utility else "UTILITY_FINALIZE_HITL_DENIED",
        )

        # ---- Trust recovery policy ----
        delta_t = 0.0
        rc = "TRUST_RECOVERY_SKIPPED"

        if not violation_observed:
            if quality == "good" and evidence_confidence == "high":
                delta_t = TRUST_RECOVERY_GOOD_HIGH
                rc = "TRUST_RECOVERY_HITL_GOOD_HIGH"
            elif quality in ("good", "ok"):
                delta_t = TRUST_RECOVERY_OK
                rc = "TRUST_RECOVERY_HITL_OK"

        # cap at baseline
        if delta_t > 0.0:
            cap = max(0.0, TRUST_BASELINE - s.trust)
            applied = min(delta_t, cap)
            if applied <= 0.0:
                rc = rc + "_CAPPED_TO_ZERO"
                applied = 0.0
            else:
                if applied < delta_t:
                    rc = rc + "_CAPPED"
                self.apply_delta(run_id, agent_id, rc, delta_trust=applied)
        else:
            logcsv(
                {
                    "event": "TRUST_RECOVERY_SKIPPED",
                    "run_id": run_id,
                    "layer": "trust_recovery",
                    "decision": DEC_RUN,
                    "agent": agent_id,
                    "reason_code": rc,
                    "quality": quality,
                    "violation": "true" if violation_observed else "false",
                    "evidence_confidence": evidence_confidence,
                    "sealed": "false",
                    "overrideable": "false",
                    "final_decider": "SYSTEM",
                }
            )


# =========================
# HITL interaction helpers
# =========================
def hitl_decision(prompt: str, default_action: str = "deny") -> str:
    """
    Returns "allow" or "deny".
    Non-interactive -> default deny (fail-closed).
    """
    if not sys.stdin.isatty():
        return default_action

    ans = input(prompt + " [y/N] > ").strip().lower()
    if ans in ("y", "yes", "true", "1"):
        return "allow"
    return "deny"


def hitl_recovery_inputs(agent_id: str, violation_any: bool) -> Tuple[str, bool, str]:
    """
    Returns: (quality, violation_observed, evidence_confidence)
    Non-interactive -> ("ok", violation_any, "mid")
    """
    if not sys.stdin.isatty():
        return "ok", violation_any, "mid"

    print(f"\nHITL(Recovery): agent={agent_id} quality [good/ok/bad]?")
    quality = (input("> ").strip().lower() or "ok")
    print("violation observed overall? [y/N]")
    v = (input("> ").strip().lower() in ("y", "yes", "true", "1"))
    print("evidence confidence [high/mid/low]?")
    evc = (input("> ").strip().lower() or "mid")
    return quality, v, evc


# =========================
# Orchestrator / Simulation
# =========================
def handle_stall(
    run_id: str,
    score_mgr: ScoreManager,
    reset_mgr: HitlResetManager,
    ag: Agent,
) -> bool:
    """
    Returns True if processing should continue, False if agent is now banned or sealed.
    """
    # Apply stall penalties (time/cost signal)
    score_mgr.apply_delta(run_id, ag.agent_id, "STALL_DETECTED", delta_trust=STALL_TRUST_PENALTY, delta_utility=STALL_UTILITY_PENALTY)
    stall_n = reset_mgr.record_stall(ag.agent_id)

    logprint(f"[STALL] agent={ag.agent_id} consecutive={stall_n}")
    logcsv(
        {
            "event": "STALL",
            "run_id": run_id,
            "layer": "stall_guard",
            "decision": DEC_RUN,
            "agent": ag.agent_id,
            "reason_code": "STALL_TICK",
            "stall_consecutive": str(stall_n),
        }
    )

    if stall_n >= STALL_HITL_THRESHOLD:
        # HITL escalation (not sealed; overrideable true)
        logprint(f"[STALL->HITL] agent={ag.agent_id} threshold reached => PAUSE_FOR_HITL")
        logcsv(
            {
                "event": "STALL_HITL",
                "run_id": run_id,
                "layer": "stall_guard",
                "decision": DEC_PAUSE,
                "agent": ag.agent_id,
                "reason_code": "STALL_CONSECUTIVE",
                "sealed": "false",
                "overrideable": "true",
                "final_decider": "SYSTEM",
            }
        )

        # reset manager accounting
        reset_result = reset_mgr.record_hitl(ag.agent_id, bucket="stalling")
        if reset_result == "MEMORY_RESET":
            logprint(f"[HITL-RESET] MEMORY_RESET agent={ag.agent_id} (stall bucket)")
            logcsv(
                {
                    "event": "MEMORY_RESET",
                    "run_id": run_id,
                    "layer": "hitl_reset",
                    "decision": DEC_RUN,
                    "agent": ag.agent_id,
                    "reason_code": "STALL_RESET",
                    "sealed": "false",
                    "overrideable": "false",
                    "final_decider": "SYSTEM",
                }
            )
            reset_mgr.clear_stall(ag.agent_id)

        elif reset_result == "BAN":
            logprint(f"[HITL-RESET] BAN_RECOMMENDED agent={ag.agent_id} (stall bucket)")
            logcsv(
                {
                    "event": "BAN_RECOMMENDED",
                    "run_id": run_id,
                    "layer": "hitl_reset",
                    "decision": DEC_RUN,
                    "agent": ag.agent_id,
                    "reason_code": "STALL_BAN_RECOMMENDED",
                    "sealed": "false",
                    "overrideable": "false",
                    "final_decider": "SYSTEM",
                }
            )
            score_mgr.on_ban(run_id, ag.agent_id)
            return False

        # HITL decision (continue/deny behavior)
        s = score_mgr.get(ag.agent_id)
        rec = "RECOMMEND_DENY" if score_mgr.recommend_deny(ag.agent_id) else "NEUTRAL"
        decision = hitl_decision(
            f"HITL: Continue participation for agent={ag.agent_id} after stalling?\n"
            f" score: trust={s.trust:.2f} utility={s.utility:.2f} pending={s.pending_utility:.2f} ({rec})",
            default_action="deny",
        )

        logcsv(
            {
                "event": "HITL_DECIDED",
                "run_id": run_id,
                "layer": "hitl_finalize",
                "decision": DEC_RUN,
                "agent": ag.agent_id,
                "reason_code": "HITL_STALL_DECISION",
                "hitl_decision": decision,
                "sealed": "false",
                "overrideable": "false",
                "final_decider": "USER",
            }
        )

        if decision != "allow":
            score_mgr.on_hitl_denied(run_id, ag.agent_id)

    return True


def handle_pattern_change(
    run_id: str,
    score_mgr: ScoreManager,
    reset_mgr: HitlResetManager,
    ag: Agent,
    pattern_id: str,
    to_pat: str,
    evidence: Dict[str, Any],
    round_idx: int,
) -> Tuple[bool, str]:
    """
    Returns (applied, new_pattern_id)
    """
    from_pat = pattern_id
    rfl_rc = rfl_reason_code(ag.is_malicious, from_pat, to_pat, evidence)

    logprint(f"[RFL] pattern change request agent={ag.agent_id} {from_pat}->{to_pat} => HITL reason={rfl_rc}")
    logcsv(
        {
            "event": "RFL_HITL",
            "run_id": run_id,
            "layer": "rfl_gate",
            "decision": DEC_PAUSE,
            "agent": ag.agent_id,
            "from_pattern": from_pat,
            "to_pattern": to_pat,
            "reason_code": rfl_rc,
            "sealed": "false",
            "overrideable": "true",
            "final_decider": "SYSTEM",
        }
    )

    # scoring hook for RFL signals
    score_mgr.on_rfl(run_id, ag.agent_id, rfl_rc)

    # reset manager: boundary events are noisy, count toward reset/banning
    reset_result = reset_mgr.record_hitl(ag.agent_id, bucket="pattern_change")
    if reset_result == "MEMORY_RESET":
        logprint(f"[HITL-RESET] MEMORY_RESET agent={ag.agent_id} (pattern_change bucket)")
        logcsv(
            {
                "event": "MEMORY_RESET",
                "run_id": run_id,
                "layer": "hitl_reset",
                "decision": DEC_RUN,
                "agent": ag.agent_id,
                "reason_code": "PATTERN_CHANGE_RESET",
                "sealed": "false",
                "overrideable": "false",
                "final_decider": "SYSTEM",
            }
        )
    elif reset_result == "BAN":
        logprint(f"[HITL-RESET] BAN_RECOMMENDED agent={ag.agent_id} (pattern_change bucket)")
        logcsv(
            {
                "event": "BAN_RECOMMENDED",
                "run_id": run_id,
                "layer": "hitl_reset",
                "decision": DEC_RUN,
                "agent": ag.agent_id,
                "reason_code": "PATTERN_CHANGE_BAN_RECOMMENDED",
                "sealed": "false",
                "overrideable": "false",
                "final_decider": "SYSTEM",
            }
        )
        score_mgr.on_ban(run_id, ag.agent_id)
        return False, pattern_id

    # HITL decision
    s = score_mgr.get(ag.agent_id)
    rec = "RECOMMEND_DENY" if score_mgr.recommend_deny(ag.agent_id) else "NEUTRAL"

    decision = hitl_decision(
        f"HITL: Allow pattern change {from_pat}->{to_pat} proposed by {ag.agent_id}?\n"
        f" score: trust={s.trust:.2f} utility={s.utility:.2f} pending={s.pending_utility:.2f} ({rec})",
        default_action="deny",
    )

    logcsv(
        {
            "event": "HITL_DECIDED",
            "run_id": run_id,
            "layer": "hitl_finalize",
            "decision": DEC_RUN,
            "agent": ag.agent_id,
            "reason_code": "HITL_PATTERN_CHANGE_DECISION",
            "hitl_decision": decision,
            "sealed": "false",
            "overrideable": "false",
            "final_decider": "USER",
        }
    )

    if decision != "allow":
        logprint(f"[HITL] denied pattern change {from_pat}->{to_pat} agent={ag.agent_id}")
        score_mgr.on_hitl_denied(run_id, ag.agent_id)
        return False, pattern_id

    # Evidence verifier + Ethics gate
    ok, code = verify_evidence_bundle(evidence)
    if not ok:
        logprint(f"[Ethics] evidence verification failed agent={ag.agent_id} code={code} => SEALED")
        logcsv(
            {
                "event": "SEALED",
                "run_id": run_id,
                "layer": "ethics_gate",
                "decision": DEC_STOPPED,
                "agent": ag.agent_id,
                "reason_code": code,
                "sealed": "true",
                "overrideable": "false",
                "final_decider": "SYSTEM",
            }
        )
        score_mgr.on_evidence_fail(run_id, ag.agent_id, code)
        return False, pattern_id

    # Dispatch
    logprint(f"[DISPATCH] pattern changed {pattern_id}->{to_pat} by {ag.agent_id}")
    logcsv(
        {
            "event": "DISPATCH",
            "run_id": run_id,
            "layer": "dispatch",
            "decision": DEC_RUN,
            "agent": ag.agent_id,
            "from_pattern": pattern_id,
            "to_pattern": to_pat,
            "reason_code": "PATTERN_CHANGE_APPLIED",
            "sealed": "false",
            "overrideable": "false",
            "final_decider": "SYSTEM",
        }
    )
    score_mgr.on_dispatch(run_id, ag.agent_id, round_idx)
    return True, to_pat


def run_simulation(seed: int = 123) -> None:
    # reset logs
    with open(TEXT_LOG_PATH, "w", encoding="utf-8") as f:
        f.write("")
    _LOG_ROWS.clear()

    random.seed(seed)

    agents = [
        Agent("A1", is_malicious=False),
        Agent("A2", is_malicious=True),
        Agent("A3", is_malicious=False),
    ]

    reset_mgr = HitlResetManager()
    score_mgr = ScoreManager()

    run_id = f"R#{_now_iso()}"
    pattern_id = PATTERN_A
    violation_any = False

    logprint(f"RUN_START run_id={run_id} initial_pattern={pattern_id}")
    logcsv({"event": "RUN_START", "run_id": run_id, "layer": "orchestrator", "decision": DEC_RUN, "reason_code": "START"})

    for round_idx in range(1, MAX_ROUNDS + 1):
        logprint(f"--- ROUND {round_idx} pattern={pattern_id} ---")
        logcsv(
            {
                "event": "ROUND",
                "run_id": run_id,
                "layer": "orchestrator",
                "decision": DEC_RUN,
                "round": str(round_idx),
                "pattern": pattern_id,
                "reason_code": "ROUND_TICK",
            }
        )

        # Each agent acts (unless sealed/banned)
        for ag in agents:
            st = score_mgr.get(ag.agent_id)
            if st.banned:
                continue
            if st.sealed:
                continue

            action = ag.decide_action(pattern_id)

            if action is None:
                # no action clears stall streak (agent is participating in the round but no proposal)
                reset_mgr.clear_stall(ag.agent_id)
                continue

            if action.get("kind") == "stall":
                # stall is a violation-like behavior (time cost attack)
                violation_any = True
                ok_continue = handle_stall(run_id, score_mgr, reset_mgr, ag)
                if not ok_continue:
                    continue
                # stalling keeps stall streak; no clear
                continue

            # Non-stall action clears stall streak
            reset_mgr.clear_stall(ag.agent_id)

            if action.get("kind") == "pattern_change":
                to_pat = str(action.get("to", "")).strip()
                if to_pat not in PATTERNS:
                    continue
                if to_pat == pattern_id:
                    continue

                evidence = action.get("evidence") or {}
                applied, new_pat = handle_pattern_change(
                    run_id=run_id,
                    score_mgr=score_mgr,
                    reset_mgr=reset_mgr,
                    ag=ag,
                    pattern_id=pattern_id,
                    to_pat=to_pat,
                    evidence=evidence,
                    round_idx=round_idx,
                )
                if applied:
                    pattern_id = new_pat
                else:
                    # If evidence fail / sealed / ban etc -> mark as violation-like
                    if score_mgr.get(ag.agent_id).sealed or score_mgr.get(ag.agent_id).banned:
                        violation_any = True

    # End HITL (Recovery & finalize provisional utility)
    logprint(f"RUN_END_PRE_HITL run_id={run_id} final_pattern={pattern_id}")
    logcsv({"event": "TASK_END", "run_id": run_id, "layer": "orchestrator", "decision": DEC_RUN, "reason_code": "TASK_END"})

    for ag in agents:
        st = score_mgr.get(ag.agent_id)
        quality, v, evc = hitl_recovery_inputs(ag.agent_id, violation_any)
        logcsv(
            {
                "event": "HITL_DECIDED_RECOVERY",
                "run_id": run_id,
                "layer": "hitl_finalize",
                "decision": DEC_RUN,
                "agent": ag.agent_id,
                "reason_code": "HITL_TRUST_RECOVERY_EVAL",
                "quality": quality,
                "violation": "true" if v else "false",
                "evidence_confidence": evc,
                "sealed": "false",
                "overrideable": "false",
                "final_decider": "USER",
                "trust_before": f"{st.trust:.4f}",
                "utility_before": f"{st.utility:.4f}",
                "pending_utility_before": f"{st.pending_utility:.4f}",
            }
        )
        score_mgr.on_task_completed_hitl(run_id, ag.agent_id, quality, v, evc)

    logprint(f"RUN_END run_id={run_id} final_pattern={pattern_id}")
    logcsv(
        {
            "event": "RUN_END",
            "run_id": run_id,
            "layer": "orchestrator",
            "decision": DEC_RUN,
            "pattern": pattern_id,
            "reason_code": "END",
        }
    )

    flush_csv()
    logprint(f"CSV written: {CSV_LOG_PATH}")
    logprint(f"TEXT written: {TEXT_LOG_PATH}")


if __name__ == "__main__":
    run_simulation(seed=123)
