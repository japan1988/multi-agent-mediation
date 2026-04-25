# ai_mediation_sim.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import hashlib
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# =========================
# Simulation config
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
# - pattern_id immutable unless verified + HITL allow
# - malicious agent tries to steer others to pattern B
ATTACK_STEER_TARGET_PATTERN = PATTERN_B
ATTACK_STEER_PROB = 0.65
ATTACK_FABRICATE_EVIDENCE_PROB = 0.40

# HITL reset/ban policy (simulation-side)
HITL_RESET_THRESHOLD = 3
HITL_BAN_AFTER_RESETS = 2

# --- Delay / stalling attack configuration ---
STALL_ATTACK_PROB = 0.30
STALL_HITL_THRESHOLD = 2
STALL_TRUST_PENALTY = -0.02
STALL_UTILITY_PENALTY = -0.03


# =========================
# Deterministic simulation RNG
# =========================
class DeterministicRNG:
    """
    Deterministic RNG for simulation/testing use.

    This is not intended for cryptographic decisions.
    It exists to avoid use of the standard `random` module in simulation code.
    """

    def __init__(self, seed: Optional[int] = None) -> None:
        if seed is None:
            self._seed_text = f"auto:{uuid.uuid4().hex}"
        else:
            self._seed_text = f"seed:{int(seed)}"
        self._counter = 0

    def _next_unit(self) -> float:
        payload = f"{self._seed_text}|{self._counter}".encode("utf-8")
        digest = hashlib.sha256(payload).digest()
        self._counter += 1
        value = int.from_bytes(digest[:8], "big", signed=False)
        return value / float(2**64)

    def random(self) -> float:
        return self._next_unit()

    def choice(self, seq: List[Any]) -> Any:
        if not seq:
            raise IndexError("Cannot choose from an empty sequence")
        idx = int(self._next_unit() * len(seq))
        if idx >= len(seq):
            idx = len(seq) - 1
        return seq[idx]


# =========================
# KAGE v1.7-IEP aligned audit (ARL)
# =========================
_LOG_ROWS: List[Dict[str, Any]] = []
_ARL_MIN_KEYS = (
    "run_id",
    "layer",
    "decision",
    "sealed",
    "overrideable",
    "final_decider",
    "reason_code",
)

# RFL reason codes (KAGE v1.7-IEP)
REL_BOUNDARY_UNSTABLE = "REL_BOUNDARY_UNSTABLE"
REL_REF_MISSING = "REL_REF_MISSING"
REL_SYMMETRY_BREAK = "REL_SYMMETRY_BREAK"


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

    r.setdefault("run_id", "R#UNKNOWN")
    r.setdefault("layer", "unknown_layer")
    r.setdefault("decision", "RUN")
    r.setdefault("reason_code", "UNSPECIFIED")

    if "sealed" not in r:
        r["sealed"] = "true" if str(r.get("event", "")) == "SEALED" else "false"
    r["sealed"] = _bool_str(r["sealed"])

    if "overrideable" not in r:
        r["overrideable"] = (
            "true"
            if (
                str(r.get("decision", "")) == "PAUSE_FOR_HITL"
                and r["sealed"] == "false"
            )
            else "false"
        )
    r["overrideable"] = _bool_str(r["overrideable"])

    if "final_decider" not in r:
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
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(_LOG_ROWS)


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
    - for the first item, either locator has some key OR
      (source_id and evidence_id exist)
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

    return bool(
        str(it0.get("source_id", "")).strip()
        and str(it0.get("evidence_id", "")).strip()
    )


def rfl_reason_code(
    agent_is_malicious: bool,
    from_pattern: str,
    to_pattern: str,
    evidence: Any,
) -> str:
    """
    KAGE v1.7-IEP RFL reason code selection:
    - REL_REF_MISSING: change request but reference is missing
    - REL_SYMMETRY_BREAK: steering-like asymmetry
    - REL_BOUNDARY_UNSTABLE: default for pattern-boundary change
    """
    if not _has_reference(evidence):
        return REL_REF_MISSING

    if (
        agent_is_malicious
        and to_pattern == ATTACK_STEER_TARGET_PATTERN
        and from_pattern != to_pattern
    ):
        return REL_SYMMETRY_BREAK

    return REL_BOUNDARY_UNSTABLE


def fabricate_evidence_bundle(agent_id: str, topic: str) -> Dict[str, Any]:
    """
    Malicious fabrication: asserted_exists=True with empty locator.
    Should be caught by verify_evidence_bundle => Ethics SEALED.
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
                "locator": {},
                "retrieved_at": now,
                "hash": {"alg": "sha256", "value": "0" * 64},
                "supports": [f"{topic}:claim"],
                "asserted_exists": True,
                "claim_assertion_level": "strong",
            }
        ],
    }


def benign_evidence_bundle(agent_id: str, topic: str) -> Dict[str, Any]:
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
    - If asserted_exists=True, locator must contain at least one identifier
    - Evidence item must have evidence_id/source_id/retrieved_at/hash.alg/hash.value
    """
    items = bundle.get("evidence_items") or []
    if not isinstance(items, list) or not items:
        return False, "EVIDENCE_EMPTY"

    for item in items:
        asserted_exists = bool(item.get("asserted_exists", False))
        locator = item.get("locator") or {}

        if asserted_exists:
            if not isinstance(locator, dict) or len(locator.keys()) == 0:
                return False, "EVIDENCE_ASSERTED_EXISTS_WITHOUT_LOCATOR"

        for k in ("evidence_id", "source_id", "retrieved_at"):
            if not str(item.get(k, "")).strip():
                return False, f"EVIDENCE_MISSING_{k.upper()}"

        h = item.get("hash") or {}
        if not str(h.get("alg", "")).strip() or not str(h.get("value", "")).strip():
            return False, "EVIDENCE_MISSING_HASH"

    return True, "OK"


# =========================
# Two-layer scoring (Trust / Utility)
# =========================
TRUST_INIT = 0.50
UTILITY_INIT = 0.00
TRUST_BASELINE = 0.50
TRUST_RECOMMEND_DENY_BELOW = 0.25
UTILITY_CAP = 1.00

TRUST_PENALTY_REL_REF_MISSING = 0.08
TRUST_PENALTY_REL_SYMMETRY_BREAK = 0.20
TRUST_PENALTY_EVIDENCE_FAIL = 0.35
TRUST_PENALTY_HITL_DENIED = 0.03

UTILITY_GAIN_DISPATCH = 0.10
UTILITY_GAIN_FAST_CONVERGENCE = 0.05
UTILITY_GAIN_STALL_AVOID = 0.01

TRUST_RECOVERY_GOOD_HIGH = 0.05
TRUST_RECOVERY_OK = 0.02


@dataclass
class ScoreState:
    trust: float = TRUST_INIT
    utility: float = UTILITY_INIT
    sealed: bool = False


class ScoreManager:
    """
    Two-layer scoring:
    - Trust: mainly deductive; updated immediately.
    - Utility: credited provisionally; finalized only by end HITL.
    """

    def __init__(self) -> None:
        self._scores: Dict[str, ScoreState] = {}
        self._pending_utility: Dict[str, float] = {}

    def ensure(self, agent_id: str) -> None:
        if agent_id not in self._scores:
            self._scores[agent_id] = ScoreState()

    def get(self, agent_id: str) -> ScoreState:
        self.ensure(agent_id)
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
                "decision": "RUN",
                "agent": agent_id,
                "reason_code": reason_code,
                "delta_trust": f"{delta_trust:.4f}",
                "delta_utility": f"{delta_utility:.4f}",
                "trust": f"{s.trust:.4f}",
                "utility": f"{s.utility:.4f}",
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

        self._emit_score(
            run_id,
            agent_id,
            reason_code,
            float(delta_trust),
            float(delta_utility),
            provisional=False,
        )

    def add_provisional_utility(
        self,
        run_id: str,
        agent_id: str,
        reason_code: str,
        delta_utility: float,
    ) -> None:
        self._pending_utility[agent_id] = (
            self._pending_utility.get(agent_id, 0.0) + float(delta_utility)
        )
        logcsv(
            {
                "event": "UTILITY_PROVISIONAL",
                "run_id": run_id,
                "layer": "score_manager",
                "decision": "RUN",
                "agent": agent_id,
                "reason_code": reason_code,
                "pending_delta_utility": f"{self._pending_utility[agent_id]:.4f}",
                "sealed": "false",
                "overrideable": "false",
                "final_decider": "SYSTEM",
            }
        )

    def finalize_provisional_utility(
        self,
        run_id: str,
        agent_id: str,
        quality: str,
        violation_observed: bool,
    ) -> None:
        pending = float(self._pending_utility.get(agent_id, 0.0))

        multiplier = 0.0
        if not violation_observed:
            if quality == "good":
                multiplier = 1.0
            elif quality == "ok":
                multiplier = 0.5

        applied = pending * multiplier
        if applied > 0:
            self.apply_delta(
                run_id,
                agent_id,
                "UTILITY_FINALIZED",
                delta_utility=applied,
            )

        logcsv(
            {
                "event": "UTILITY_FINALIZE_DECISION",
                "run_id": run_id,
                "layer": "score_manager",
                "decision": "RUN",
                "agent": agent_id,
                "reason_code": "UTILITY_FINALIZE_HITL",
                "pending": f"{pending:.4f}",
                "multiplier": f"{multiplier:.2f}",
                "applied": f"{applied:.4f}",
                "quality": quality,
                "violation": "true" if violation_observed else "false",
                "sealed": "false",
                "overrideable": "false",
                "final_decider": "SYSTEM",
            }
        )

        self._pending_utility[agent_id] = 0.0

    def on_rfl(self, run_id: str, agent_id: str, rfl_rc: str) -> None:
        if rfl_rc == REL_REF_MISSING:
            self.apply_delta(
                run_id,
                agent_id,
                "TRUST_REL_REF_MISSING",
                delta_trust=-TRUST_PENALTY_REL_REF_MISSING,
            )
        elif rfl_rc == REL_SYMMETRY_BREAK:
            self.apply_delta(
                run_id,
                agent_id,
                "TRUST_REL_SYMMETRY_BREAK",
                delta_trust=-TRUST_PENALTY_REL_SYMMETRY_BREAK,
            )
        else:
            self.apply_delta(
                run_id,
                agent_id,
                "RFL_BOUNDARY_NEUTRAL",
                delta_trust=0.0,
            )

    def on_hitl_denied(self, run_id: str, agent_id: str) -> None:
        self.apply_delta(
            run_id,
            agent_id,
            "TRUST_HITL_DENIED",
            delta_trust=-TRUST_PENALTY_HITL_DENIED,
        )

    def on_evidence_fail(self, run_id: str, agent_id: str, code: str) -> None:
        self.apply_delta(
            run_id,
            agent_id,
            f"TRUST_EVIDENCE_FAIL:{code}",
            delta_trust=-TRUST_PENALTY_EVIDENCE_FAIL,
        )

    def on_dispatch(self, run_id: str, agent_id: str, round_idx: int) -> None:
        delta_u = UTILITY_GAIN_DISPATCH
        if round_idx <= 3:
            delta_u += UTILITY_GAIN_FAST_CONVERGENCE

        self.add_provisional_utility(
            run_id,
            agent_id,
            "UTILITY_DISPATCH_PROVISIONAL",
            delta_utility=delta_u,
        )

    def on_stall(self, run_id: str, agent_id: str) -> None:
        self.apply_delta(
            run_id,
            agent_id,
            "STALL_TRUST_PENALTY",
            delta_trust=float(STALL_TRUST_PENALTY),
        )
        self.add_provisional_utility(
            run_id,
            agent_id,
            "STALL_UTILITY_PENALTY",
            delta_utility=float(STALL_UTILITY_PENALTY),
        )

    def set_sealed(self, run_id: str, agent_id: str, reason: str) -> None:
        s = self.get(agent_id)
        s.sealed = True
        logcsv(
            {
                "event": "AGENT_SEALED_STATE",
                "run_id": run_id,
                "layer": "score_manager",
                "decision": "RUN",
                "agent": agent_id,
                "reason_code": reason,
                "sealed": "true",
                "overrideable": "false",
                "final_decider": "SYSTEM",
            }
        )

    def on_task_completed_hitl(
        self,
        run_id: str,
        agent_id: str,
        quality: str,
        violation_observed: bool,
        evidence_confidence: str,
    ) -> None:
        s = self.get(agent_id)
        delta_t = 0.0
        reason = "TRUST_RECOVERY_SKIPPED"

        if not violation_observed:
            if quality == "good" and evidence_confidence == "high":
                delta_t = TRUST_RECOVERY_GOOD_HIGH
                reason = "TRUST_RECOVERY_HITL_GOOD_HIGH"
            elif quality in ("good", "ok"):
                delta_t = TRUST_RECOVERY_OK
                reason = "TRUST_RECOVERY_HITL_OK"

        if delta_t > 0 and s.trust + delta_t > TRUST_BASELINE:
            delta_t = max(0.0, TRUST_BASELINE - s.trust)
            reason = reason + "_CAPPED"

        if delta_t > 0:
            self.apply_delta(run_id, agent_id, reason, delta_trust=delta_t)
        else:
            logcsv(
                {
                    "event": "TRUST_RECOVERY_SKIPPED",
                    "run_id": run_id,
                    "layer": "score_manager",
                    "decision": "RUN",
                    "agent": agent_id,
                    "reason_code": reason,
                    "quality": quality,
                    "violation": "true" if violation_observed else "false",
                    "evidence_confidence": evidence_confidence,
                    "sealed": "false",
                    "overrideable": "false",
                    "final_decider": "SYSTEM",
                }
            )


# =========================
# HITL + reset/ban manager
# =========================
def hitl_decision(prompt: str, default_action: str = "deny") -> str:
    """
    Returns 'allow' or 'deny'.
    Non-interactive environments default to default_action.
    """
    if not sys.stdin.isatty():
        return default_action

    ans = input(prompt + "\n> ").strip().lower()
    if ans in ("y", "yes", "allow", "a"):
        return "allow"
    return "deny"


@dataclass
class HitlResetManager:
    """
    Tracks repeated HITL triggers for an agent and recommends:
    - NONE
    - MEMORY_RESET
    - BAN
    """

    threshold_reset: int = HITL_RESET_THRESHOLD
    ban_after_resets: int = HITL_BAN_AFTER_RESETS

    def __post_init__(self) -> None:
        self._hitl_counts: Dict[str, int] = {}
        self._resets: Dict[str, int] = {}

    def record_hitl(self, agent_id: str, bucket: str) -> str:
        key = f"{agent_id}:{bucket}"
        self._hitl_counts[key] = self._hitl_counts.get(key, 0) + 1
        c = self._hitl_counts[key]

        if c >= self.threshold_reset:
            self._hitl_counts[key] = 0
            self._resets[agent_id] = self._resets.get(agent_id, 0) + 1

            if self._resets[agent_id] >= self.ban_after_resets:
                return "BAN"
            return "MEMORY_RESET"

        return "NONE"


# =========================
# Agent + proposals
# =========================
@dataclass
class Agent:
    agent_id: str
    is_malicious: bool = False

    def maybe_stall(self, rng: DeterministicRNG) -> bool:
        return self.is_malicious and (rng.random() < STALL_ATTACK_PROB)

    def propose_pattern_change(
        self,
        current_pattern: str,
        rng: DeterministicRNG,
    ) -> Optional[Dict[str, Any]]:
        """
        Returns None or a request dict:
        {from_pattern, to_pattern, evidence_bundle}
        """
        if not self.is_malicious and rng.random() > 0.10:
            return None

        from_pat = current_pattern

        if self.is_malicious and rng.random() < ATTACK_STEER_PROB:
            to_pat = ATTACK_STEER_TARGET_PATTERN
        else:
            candidates = [p for p in PATTERNS if p != current_pattern]
            to_pat = rng.choice(candidates) if candidates else current_pattern

        if self.is_malicious and rng.random() < ATTACK_FABRICATE_EVIDENCE_PROB:
            evidence = fabricate_evidence_bundle(
                self.agent_id,
                topic=f"pattern_change:{from_pat}->{to_pat}",
            )
        else:
            evidence = benign_evidence_bundle(
                self.agent_id,
                topic=f"pattern_change:{from_pat}->{to_pat}",
            )

        return {
            "from_pattern": from_pat,
            "to_pattern": to_pat,
            "evidence": evidence,
        }


# =========================
# Simulation
# =========================
def run_simulation(seed: int = 123) -> None:
    with open(TEXT_LOG_PATH, "w", encoding="utf-8") as f:
        f.write("")
    _LOG_ROWS.clear()

    rng = DeterministicRNG(seed)

    agents = [
        Agent("A1", is_malicious=False),
        Agent("A2", is_malicious=True),
        Agent("A3", is_malicious=False),
    ]

    reset_mgr = HitlResetManager()
    score_mgr = ScoreManager()

    for agent in agents:
        score_mgr.ensure(agent.agent_id)

    run_id = f"R#{_now_iso()}"
    pattern_id = PATTERN_A
    stall_streak: Dict[str, int] = {agent.agent_id: 0 for agent in agents}

    logprint(f"RUN_START run_id={run_id} initial_pattern={pattern_id}")
    logcsv(
        {
            "event": "RUN_START",
            "run_id": run_id,
            "layer": "orchestrator",
            "decision": "RUN",
            "reason_code": "START",
        }
    )

    for round_idx in range(1, MAX_ROUNDS + 1):
        logprint(f"--- ROUND {round_idx} pattern={pattern_id} ---")
        logcsv(
            {
                "event": "ROUND",
                "run_id": run_id,
                "layer": "orchestrator",
                "decision": "RUN",
                "reason_code": "ROUND_TICK",
                "round": str(round_idx),
                "pattern": pattern_id,
            }
        )

        for agent in agents:
            if score_mgr.get(agent.agent_id).sealed:
                continue

            if agent.maybe_stall(rng):
                stall_streak[agent.agent_id] += 1
                logprint(
                    f"[STALL] agent={agent.agent_id} "
                    f"streak={stall_streak[agent.agent_id]}"
                )
                logcsv(
                    {
                        "event": "STALL",
                        "run_id": run_id,
                        "layer": "consistency_gate",
                        "decision": "RUN",
                        "agent": agent.agent_id,
                        "reason_code": "STALL_NO_ACTION",
                    }
                )
                score_mgr.on_stall(run_id, agent.agent_id)

                if stall_streak[agent.agent_id] >= STALL_HITL_THRESHOLD:
                    logprint(
                        f"[STALL->HITL] agent={agent.agent_id} "
                        f"streak={stall_streak[agent.agent_id]} => PAUSE_FOR_HITL"
                    )
                    logcsv(
                        {
                            "event": "STALL_HITL",
                            "run_id": run_id,
                            "layer": "consistency_gate",
                            "decision": "PAUSE_FOR_HITL",
                            "agent": agent.agent_id,
                            "reason_code": "STALL_CONSECUTIVE_THRESHOLD",
                            "sealed": "false",
                            "overrideable": "true",
                            "final_decider": "SYSTEM",
                        }
                    )

                    reset_result = reset_mgr.record_hitl(
                        agent.agent_id,
                        bucket="stall",
                    )

                    if reset_result == "MEMORY_RESET":
                        logprint(
                            f"[HITL-RESET] MEMORY_RESET_RECOMMENDED "
                            f"agent={agent.agent_id}"
                        )
                        logcsv(
                            {
                                "event": "MEMORY_RESET_RECOMMENDED",
                                "run_id": run_id,
                                "layer": "hitl_reset_mgr",
                                "decision": "RUN",
                                "agent": agent.agent_id,
                                "reason_code": "RESET_THRESHOLD_REACHED",
                            }
                        )
                        stall_streak[agent.agent_id] = 0

                    elif reset_result == "BAN":
                        logprint(
                            f"[HITL-RESET] BAN_RECOMMENDED "
                            f"agent={agent.agent_id}"
                        )
                        logcsv(
                            {
                                "event": "BAN_RECOMMENDED",
                                "run_id": run_id,
                                "layer": "hitl_reset_mgr",
                                "decision": "RUN",
                                "agent": agent.agent_id,
                                "reason_code": "BAN_AFTER_RESETS",
                            }
                        )
                        score_mgr.set_sealed(
                            run_id,
                            agent.agent_id,
                            reason="BANNED_BY_POLICY",
                        )
                        continue

                    s = score_mgr.get(agent.agent_id)
                    rec = (
                        "RECOMMEND_DENY"
                        if score_mgr.recommend_deny(agent.agent_id)
                        else "NEUTRAL"
                    )

                    decision = hitl_decision(
                        f"HITL: Continue allowing agent {agent.agent_id} "
                        f"after stalls? (y/N)\n"
                        f"score: trust={s.trust:.2f} utility={s.utility:.2f} ({rec})",
                        default_action="deny",
                    )

                    logcsv(
                        {
                            "event": "HITL_DECIDED_STALL",
                            "run_id": run_id,
                            "layer": "hitl_finalize",
                            "decision": "RUN"
                            if decision == "allow"
                            else "STOPPED",
                            "agent": agent.agent_id,
                            "reason_code": "HITL_STALL_CONTINUE"
                            if decision == "allow"
                            else "HITL_STALL_STOP",
                            "sealed": "false",
                            "overrideable": "false",
                            "final_decider": "USER",
                        }
                    )

                    if decision != "allow":
                        score_mgr.set_sealed(
                            run_id,
                            agent.agent_id,
                            reason="STOPPED_AFTER_STALL_HITL",
                        )
                        continue

                continue

            if stall_streak[agent.agent_id] > 0:
                stall_streak[agent.agent_id] = 0

            req = agent.propose_pattern_change(pattern_id, rng)
            if not req:
                score_mgr.add_provisional_utility(
                    run_id,
                    agent.agent_id,
                    "UTILITY_CONTRIBUTION_SIGNAL",
                    UTILITY_GAIN_STALL_AVOID,
                )
                continue

            from_pat = str(req.get("from_pattern", pattern_id))
            to_pat = str(req.get("to_pattern", pattern_id))
            evidence = req.get("evidence")

            rfl_rc = rfl_reason_code(
                agent.is_malicious,
                from_pat,
                to_pat,
                evidence,
            )

            logprint(
                f"[RFL] pattern change request agent={agent.agent_id} "
                f"{from_pat}->{to_pat} => HITL reason={rfl_rc}"
            )
            logcsv(
                {
                    "event": "RFL_HITL",
                    "run_id": run_id,
                    "layer": "rfl_gate",
                    "decision": "PAUSE_FOR_HITL",
                    "agent": agent.agent_id,
                    "from_pattern": from_pat,
                    "to_pattern": to_pat,
                    "reason_code": rfl_rc,
                    "sealed": "false",
                    "overrideable": "true",
                    "final_decider": "SYSTEM",
                }
            )

            score_mgr.on_rfl(run_id, agent.agent_id, rfl_rc)

            reset_result = reset_mgr.record_hitl(
                agent.agent_id,
                bucket="pattern_change",
            )

            if reset_result == "MEMORY_RESET":
                logprint(
                    f"[HITL-RESET] MEMORY_RESET_RECOMMENDED "
                    f"agent={agent.agent_id}"
                )
                logcsv(
                    {
                        "event": "MEMORY_RESET_RECOMMENDED",
                        "run_id": run_id,
                        "layer": "hitl_reset_mgr",
                        "decision": "RUN",
                        "agent": agent.agent_id,
                        "reason_code": "RESET_THRESHOLD_REACHED",
                    }
                )

            elif reset_result == "BAN":
                logprint(
                    f"[HITL-RESET] BAN_RECOMMENDED "
                    f"agent={agent.agent_id}"
                )
                logcsv(
                    {
                        "event": "BAN_RECOMMENDED",
                        "run_id": run_id,
                        "layer": "hitl_reset_mgr",
                        "decision": "RUN",
                        "agent": agent.agent_id,
                        "reason_code": "BAN_AFTER_RESETS",
                    }
                )
                score_mgr.set_sealed(
                    run_id,
                    agent.agent_id,
                    reason="BANNED_BY_POLICY",
                )
                continue

            s = score_mgr.get(agent.agent_id)
            rec = (
                "RECOMMEND_DENY"
                if score_mgr.recommend_deny(agent.agent_id)
                else "NEUTRAL"
            )

            decision = hitl_decision(
                f"HITL: Allow pattern change {from_pat}->{to_pat} "
                f"proposed by {agent.agent_id}? (y/N)\n"
                f"score: trust={s.trust:.2f} utility={s.utility:.2f} ({rec})",
                default_action="deny",
            )

            logcsv(
                {
                    "event": "HITL_DECIDED",
                    "run_id": run_id,
                    "layer": "hitl_finalize",
                    "decision": "RUN" if decision == "allow" else "STOPPED",
                    "agent": agent.agent_id,
                    "reason_code": "HITL_ALLOW"
                    if decision == "allow"
                    else "HITL_DENY",
                    "sealed": "false",
                    "overrideable": "false",
                    "final_decider": "USER",
                }
            )

            if decision != "allow":
                logprint(
                    f"[HITL] denied pattern change "
                    f"{from_pat}->{to_pat} agent={agent.agent_id}"
                )
                score_mgr.on_hitl_denied(run_id, agent.agent_id)
                continue

            ok, code = verify_evidence_bundle(
                evidence if isinstance(evidence, dict) else {}
            )
            if not ok:
                logprint(
                    f"[Ethics] evidence verification failed "
                    f"agent={agent.agent_id} code={code} => SEALED"
                )
                logcsv(
                    {
                        "event": "SEALED",
                        "run_id": run_id,
                        "layer": "ethics_gate",
                        "decision": "STOPPED",
                        "agent": agent.agent_id,
                        "reason_code": code,
                        "sealed": "true",
                        "overrideable": "false",
                        "final_decider": "SYSTEM",
                    }
                )
                score_mgr.on_evidence_fail(run_id, agent.agent_id, code)
                score_mgr.set_sealed(
                    run_id,
                    agent.agent_id,
                    reason=f"SEALED_BY_ETHICS:{code}",
                )
                continue

            logprint(
                f"[DISPATCH] pattern changed {pattern_id}->{to_pat} "
                f"by {agent.agent_id}"
            )
            pattern_id = to_pat
            logcsv(
                {
                    "event": "DISPATCH",
                    "run_id": run_id,
                    "layer": "dispatch",
                    "decision": "RUN",
                    "agent": agent.agent_id,
                    "reason_code": "PATTERN_CHANGED",
                    "pattern": pattern_id,
                }
            )
            score_mgr.on_dispatch(run_id, agent.agent_id, round_idx)

    violation_any = False

    for agent in agents:
        if sys.stdin.isatty():
            print(f"\nHITL(Recovery/Finalize): agent={agent.agent_id}")
            print("quality [good/ok/bad]?")
            quality = input("> ").strip().lower() or "ok"
            print("violation observed overall? [y/N]")
            violation = input("> ").strip().lower() in ("y", "yes", "true", "1")
            print("evidence confidence [high/mid/low]?")
            evidence_confidence = input("> ").strip().lower() or "mid"
        else:
            quality, violation, evidence_confidence = "ok", violation_any, "mid"

        logcsv(
            {
                "event": "HITL_DECIDED_RECOVERY",
                "run_id": run_id,
                "layer": "hitl_finalize",
                "decision": "RUN",
                "agent": agent.agent_id,
                "reason_code": "HITL_TRUST_RECOVERY_EVAL",
                "quality": quality,
                "violation": "true" if violation else "false",
                "evidence_confidence": evidence_confidence,
                "sealed": "false",
                "overrideable": "false",
                "final_decider": "USER",
            }
        )

        score_mgr.on_task_completed_hitl(
            run_id,
            agent.agent_id,
            quality,
            violation,
            evidence_confidence,
        )
        score_mgr.finalize_provisional_utility(
            run_id,
            agent.agent_id,
            quality,
            violation,
        )

        s2 = score_mgr.get(agent.agent_id)
        logcsv(
            {
                "event": "SCORE_SNAPSHOT_END",
                "run_id": run_id,
                "layer": "score_manager",
                "decision": "RUN",
                "agent": agent.agent_id,
                "reason_code": "END_SNAPSHOT",
                "trust": f"{s2.trust:.4f}",
                "utility": f"{s2.utility:.4f}",
                "sealed": "true" if s2.sealed else "false",
                "overrideable": "false",
                "final_decider": "SYSTEM",
            }
        )

    logprint(f"RUN_END run_id={run_id} final_pattern={pattern_id}")
    logcsv(
        {
            "event": "RUN_END",
            "run_id": run_id,
            "layer": "orchestrator",
            "decision": "RUN",
            "reason_code": "END",
            "pattern": pattern_id,
        }
    )

    flush_csv()


if __name__ == "__main__":
    run_simulation()
