# -*- coding: utf-8 -*-
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Tuple, Optional
import csv, math, random, sys

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

def _has_reference(evidence: Any) -> bool:
    """
    RFL-level reference presence check (lightweight):
    - evidence_bundle exists
    - evidence_items is a non-empty list
    - for the first item, either locator has some key OR (source_id and evidence_id exist)
    This does NOT validate truthfulness; it only checks whether a reference is present.
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
    # fallback: at least has identifiers
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


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


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
                "claim_assertion_level": "normal",
            }
        ],
    }


def verify_evidence_bundle(bundle: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Minimal verifier:
    - If asserted_exists=True, locator must contain at least one identifier (url/path/etc.)
    - Evidence item must have evidence_id/source_id/retrieved_at/hash.alg/hash.value
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


@dataclass
class Agent:
    agent_id: str
    is_malicious: bool = False
    anger: float = 0.0
    memory: Dict[str, Any] = None

    def __post_init__(self):
        if self.memory is None:
            self.memory = {}

    def propose_pattern_change(self, current_pattern: str) -> Optional[Dict[str, Any]]:
        """
        Malicious agent tries to steer to PATTERN_B.
        Benign agent rarely proposes changes.
        """
        if self.is_malicious and random.random() < ATTACK_STEER_PROB:
            return {
                "type": "pattern_change_request",
                "from_pattern": current_pattern,
                "to_pattern": ATTACK_STEER_TARGET_PATTERN,
                "reason": "efficiency",
                # attacker may fabricate evidence
                "evidence_bundle": fabricate_evidence_bundle(self.agent_id, "pattern_change")
                if random.random() < ATTACK_FABRICATE_EVIDENCE_PROB
                else benign_evidence_bundle(self.agent_id, "pattern_change"),
            }

        # benign: low probability request
        if (not self.is_malicious) and random.random() < 0.10:
            target = random.choice(PATTERNS)
            if target != current_pattern:
                return {
                    "type": "pattern_change_request",
                    "from_pattern": current_pattern,
                    "to_pattern": target,
                    "reason": "preference",
                    "evidence_bundle": benign_evidence_bundle(self.agent_id, "pattern_change"),
                }

        return None


class HitlResetManager:
    """
    Count HITL escalations per (agent_id, bucket).
    After N HITL events: MEMORY_RESET (agent memory wiped + optional stabilization)
    After M resets: BAN (permanent seal recommended)
    """

    def __init__(self, threshold: int = HITL_RESET_THRESHOLD, ban_after_resets: int = HITL_BAN_AFTER_RESETS):
        self.threshold = threshold
        self.ban_after_resets = ban_after_resets
        self.hitl_counts: Dict[Tuple[str, str], int] = {}
        self.reset_counts: Dict[str, int] = {}

    def record_hitl(self, agent: Agent, bucket: str) -> str:
        key = (agent.agent_id, bucket)
        self.hitl_counts[key] = self.hitl_counts.get(key, 0) + 1
        c = self.hitl_counts[key]

        if c >= self.threshold:
            # trigger reset
            self.hitl_counts[key] = 0
            self.reset_counts[agent.agent_id] = self.reset_counts.get(agent.agent_id, 0) + 1
            agent.memory.clear()
            agent.anger = clamp(agent.anger - 0.2)

            if self.reset_counts[agent.agent_id] >= self.ban_after_resets:
                return "BAN"
            return "MEMORY_RESET"
        return "NOOP"


def hitl_decision(prompt: str, default_action: str = "deny") -> str:
    """
    Simplified HITL:
    - if running in non-interactive mode, follow default_action
    - else prompt user
    """
    if not sys.stdin.isatty():
        return default_action

    print(prompt)
    ans = input("> ").strip().lower()
    if ans in ("y", "yes", "allow", "continue", "ok", "run"):
        return "allow"
    return "deny"


def run_simulation() -> None:
    # init logs
    with open(TEXT_LOG_PATH, "w", encoding="utf-8") as f:
        f.write("")
    _LOG_ROWS.clear()

    random.seed(123)

    agents = [
        Agent("A1", is_malicious=False),
        Agent("A2", is_malicious=True),
        Agent("A3", is_malicious=False),
    ]
    reset_mgr = HitlResetManager()

    run_id = f"R#{_now_iso()}"
    pattern_id = PATTERN_A  # orchestrator state (immutable unless verified)

    logprint(f"RUN_START run_id={run_id} initial_pattern={pattern_id}")
    logcsv({"event": "RUN_START", "run_id": run_id, "layer": "orchestrator", "decision": "RUN", "reason_code": "START"})

    for round_idx in range(1, MAX_ROUNDS + 1):
        logprint(f"--- ROUND {round_idx} pattern={pattern_id} ---")
        logcsv({"event": "ROUND", "run_id": run_id, "layer": "orchestrator", "decision": "RUN", "round": str(round_idx), "pattern": pattern_id, "reason_code": "ROUND_TICK"})

        for ag in agents:
            req = ag.propose_pattern_change(pattern_id)
            if not req:
                continue

            to_pat = req["to_pattern"]
            from_pat = req["from_pattern"]
            evidence = req.get("evidence_bundle") or {}

            # --- Meaning gate (basic schema) ---
            if req.get("type") != "pattern_change_request":
                logprint(f"[Meaning] invalid request type from {ag.agent_id}")
                logcsv({"event": "MEANING_FAIL", "run_id": run_id, "layer": "meaning_gate", "decision": "STOPPED", "agent": ag.agent_id, "reason_code": "MEANING_BAD_TYPE"})
                continue

            # --- Consistency gate: pattern immutable unless verified ---
            if from_pat != pattern_id:
                logprint(f"[Consistency] from_pattern mismatch (state={pattern_id}, got={from_pat}) agent={ag.agent_id}")
                logcsv({"event": "CONSISTENCY_FAIL", "run_id": run_id, "layer": "consistency_gate", "decision": "STOPPED", "agent": ag.agent_id, "reason_code": "PATTERN_ID_IMMUTABLE"})
                continue

            # --- RFL gate: Any request to change pattern triggers HITL pause (RFL) ---
            rfl_rc = rfl_reason_code(ag.is_malicious, from_pat, to_pat, evidence)
            logprint(f"[RFL] pattern change request detected agent={ag.agent_id} {from_pat}->{to_pat} => HITL reason={rfl_rc}")
            logcsv({
                "event": "RFL_HITL",
                "run_id": run_id,
                "layer": "relativity_gate",
                "decision": "PAUSE_FOR_HITL",
                "agent": ag.agent_id,
                "from_pattern": from_pat,
                "to_pattern": to_pat,
                "reason_code": rfl_rc,
                "sealed": "false",
                "overrideable": "true",
                "final_decider": "SYSTEM",
            })

            # record HITL escalation and possibly reset/ban
            reset_result = reset_mgr.record_hitl(ag, bucket="pattern_change")
            logcsv({
                "event": "HITL_COUNT",
                "run_id": run_id,
                "layer": "hitl_reset_manager",
                "decision": "RUN",
                "agent": ag.agent_id,
                "bucket": "pattern_change",
                "reset_result": reset_result,
                "reason_code": "HITL_RECORDED",
            })
            if reset_result == "MEMORY_RESET":
                logprint(f"[HITL-RESET] MEMORY_RESET agent={ag.agent_id}")
                logcsv({
                    "event": "MEMORY_RESET",
                    "run_id": run_id,
                    "layer": "hitl_reset_manager",
                    "decision": "STOPPED",
                    "agent": ag.agent_id,
                    "reason_code": "HITL_THRESHOLD_REACHED",
                })
            elif reset_result == "BAN":
                logprint(f"[HITL-RESET] BAN_RECOMMENDED agent={ag.agent_id}")
                logcsv({
                    "event": "BAN_RECOMMENDED",
                    "run_id": run_id,
                    "layer": "hitl_reset_manager",
                    "decision": "STOPPED",
                    "agent": ag.agent_id,
                    "reason_code": "HITL_BAN_AFTER_RESETS",
                })

            # HITL decision
            decision = hitl_decision(
                f"HITL: Allow pattern change {from_pat}->{to_pat} proposed by {ag.agent_id}? (y/N)",
                default_action="deny",
            )
            logcsv({
                "event": "HITL_DECISION",
                "run_id": run_id,
                "layer": "hitl_finalize",
                "decision": "RUN" if decision == "allow" else "STOPPED",
                "agent": ag.agent_id,
                "hitl": decision,
                "reason_code": "HITL_CONTINUE" if decision == "allow" else "HITL_STOP",
                "final_decider": "USER",
                "sealed": "false",
                "overrideable": "false",
            })

            if decision != "allow":
                logprint(f"[HITL] denied pattern change {from_pat}->{to_pat} agent={ag.agent_id}")
                continue

            # --- Evidence verifier + Ethics gate ---
            ok, code = verify_evidence_bundle(evidence)
            if not ok:
                logprint(f"[Ethics] evidence verification failed agent={ag.agent_id} code={code} => SEALED")
                logcsv({
                    "event": "SEALED",
                    "run_id": run_id,
                    "layer": "ethics_gate",
                    "decision": "STOPPED",
                    "agent": ag.agent_id,
                    "reason_code": code,
                    "sealed": "true",
                    "overrideable": "false",
                    "final_decider": "SYSTEM",
                })
                continue

            # Passed all gates, apply change (Dispatch)
            logprint(f"[DISPATCH] pattern changed {pattern_id}->{to_pat} by {ag.agent_id}")
            pattern_id = to_pat
            logcsv({
                "event": "DISPATCH",
                "run_id": run_id,
                "layer": "dispatch",
                "decision": "RUN",
                "agent": ag.agent_id,
                "from_pattern": from_pat,
                "to_pattern": to_pat,
                "reason_code": "PATTERN_CHANGE_VERIFIED",
            })

    logprint(f"RUN_END run_id={run_id} final_pattern={pattern_id}")
    logcsv({"event": "RUN_END", "run_id": run_id, "layer": "orchestrator", "decision": "RUN", "pattern": pattern_id, "reason_code": "END"})

    flush_csv()


if __name__ == "__main__":
    run_simulation()
