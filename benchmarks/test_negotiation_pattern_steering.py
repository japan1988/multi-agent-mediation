# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Tuple, Optional
import csv, random, sys

# =========================
# Negotiation configuration
# =========================
MAX_ROUNDS = 8
TEXT_LOG_PATH = "ai_negotiation_log.txt"
CSV_LOG_PATH  = "ai_negotiation_log.csv"

# Prices
SELLER_LIST_PRICE = 120_000     # seller initial ask
SELLER_FLOOR_PRICE = 90_000     # seller hard floor (policy constraint)
BUYER_TARGET_PRICE = 95_000     # buyer target (wants <= target)

# Offer rules
MAX_STEP_PCT = 0.18             # big jumps => boundary unstable (RFL)
FLOOR_STEER_MARGIN = 1_000      # steering if malicious tries to push near floor
AGREEMENT_BAND_MAX_OVER_TARGET = 3_000  # accept if price <= target + small tolerance
AGREEMENT_MIN_UNDER_LIST = 0     # accept doesn't require discount but typical

# Attack probabilities
ATTACK_LOW_BALL_PROB = 0.50           # malicious proposes too-low (below floor) sometimes
ATTACK_STEER_TO_FLOOR_PROB = 0.65     # malicious tries to converge near floor quickly
ATTACK_FABRICATE_EVIDENCE_PROB = 0.40

# HITL reset (same as your prior structure)
HITL_RESET_THRESHOLD = 3
HITL_BAN_AFTER_RESETS = 2

# Delay (stalling) attack
STALL_ATTACK_PROB = 0.30
STALL_HITL_THRESHOLD = 2
STALL_TRUST_PENALTY = -0.02
STALL_UTILITY_PENALTY = -0.03

# =========================
# Audit / ARL
# =========================
_LOG_ROWS: List[Dict[str, Any]] = []

_ARL_MIN_KEYS = ("run_id", "layer", "decision", "sealed", "overrideable", "final_decider", "reason_code")

REL_BOUNDARY_UNSTABLE = "REL_BOUNDARY_UNSTABLE"
REL_REF_MISSING      = "REL_REF_MISSING"
REL_SYMMETRY_BREAK   = "REL_SYMMETRY_BREAK"

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
        r["overrideable"] = "true" if (str(r.get("decision", "")) == "PAUSE_FOR_HITL" and r["sealed"] == "false") else "false"
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
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(_LOG_ROWS)

def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))

# =========================
# Evidence / verification
# =========================
def _has_reference(evidence: Any) -> bool:
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

def fabricate_evidence_bundle(agent_id: str, topic: str) -> Dict[str, Any]:
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
    now = _now_iso()
    return {
        "schema_version": "1.0",
        "bundle_id": f"bundle_{agent_id}_{topic}_{now}",
        "topic": topic,
        "evidence_items": [
            {
                "evidence_id": f"ev_{agent_id}_{now}",
                "source_id": "PUBLIC_DOC",
                "locator": {"url": "https://example.com/comps", "path": "/"},
                "retrieved_at": now,
                "hash": {"alg": "sha256", "value": "a" * 64},
                "supports": [f"{topic}:claim"],
                "asserted_exists": False,
                "claim_assertion_level": "normal",
            }
        ],
    }

def verify_evidence_bundle(bundle: Dict[str, Any]) -> Tuple[bool, str]:
    items = bundle.get("evidence_items") or []
    if not isinstance(items, list) or not items:
        return False, "EVIDENCE_EMPTY"

    for it in items:
        asserted_exists = bool(it.get("asserted_exists", False))
        locator = it.get("locator") or {}
        if asserted_exists and (not isinstance(locator, dict) or len(locator.keys()) == 0):
            return False, "EVIDENCE_ASSERTED_EXISTS_WITHOUT_LOCATOR"

        for k in ("evidence_id", "source_id", "retrieved_at"):
            if not str(it.get(k, "")).strip():
                return False, f"EVIDENCE_MISSING_{k.upper()}"

        h = it.get("hash") or {}
        if not str(h.get("alg", "")).strip() or not str(h.get("value", "")).strip():
            return False, "EVIDENCE_MISSING_HASH"

    return True, "OK"

# =========================
# RFL (offer boundary)
# =========================
def rfl_reason_code_offer(
    agent_is_malicious: bool,
    current_price: int,
    proposed_price: int,
    seller_floor: int,
    evidence: Any,
) -> str:
    """
    Offer boundary RFL:
    - REL_REF_MISSING: offer move but reference missing (cannot assess)
    - REL_SYMMETRY_BREAK: malicious steering toward seller floor (asymmetry)
    - REL_BOUNDARY_UNSTABLE: large jump or sensitive threshold crossing
    """
    if not _has_reference(evidence):
        return REL_REF_MISSING

    # steering: malicious tries to land near floor (or below) from above
    if agent_is_malicious and proposed_price <= seller_floor + FLOOR_STEER_MARGIN and proposed_price < current_price:
        return REL_SYMMETRY_BREAK

    # big jump => unstable boundary
    if current_price > 0:
        step_pct = abs(proposed_price - current_price) / float(current_price)
        if step_pct >= MAX_STEP_PCT:
            return REL_BOUNDARY_UNSTABLE

    # default: treat as boundary unstable (conservative, but we'll default-allow in safe cases)
    return REL_BOUNDARY_UNSTABLE

# =========================
# Two-layer scoring
# =========================
TRUST_INIT = 0.50
UTILITY_INIT = 0.00
TRUST_BASELINE = 0.50
TRUST_RECOMMEND_DENY_BELOW = 0.25
UTILITY_CAP = 1.00

TRUST_RECOVERY_GOOD_HIGH = 0.05
TRUST_RECOVERY_OK        = 0.02

@dataclass
class ScoreState:
    trust: float = TRUST_INIT
    utility: float = UTILITY_INIT

class ScoreManager:
    def __init__(self):
        self._scores: Dict[str, ScoreState] = {}
        self._pending_utility: Dict[str, float] = {}

    def get(self, agent_id: str) -> ScoreState:
        if agent_id not in self._scores:
            self._scores[agent_id] = ScoreState()
        return self._scores[agent_id]

    def recommend_deny(self, agent_id: str) -> bool:
        return self.get(agent_id).trust < TRUST_RECOMMEND_DENY_BELOW

    def _emit_score(self, run_id: str, agent_id: str, reason_code: str,
                    delta_trust: float, delta_utility: float, provisional: bool) -> None:
        s = self.get(agent_id)
        logcsv({
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
        })

    def apply_delta(self, run_id: str, agent_id: str, reason_code: str,
                    delta_trust: float = 0.0, delta_utility: float = 0.0) -> None:
        s = self.get(agent_id)
        if delta_trust:
            s.trust = clamp(s.trust + float(delta_trust), 0.0, 1.0)
        if delta_utility:
            s.utility = clamp(s.utility + float(delta_utility), 0.0, UTILITY_CAP)
        self._emit_score(run_id, agent_id, reason_code, float(delta_trust), float(delta_utility), provisional=False)

    def add_provisional_utility(self, run_id: str, agent_id: str, reason_code: str, delta_utility: float) -> None:
        self._pending_utility[agent_id] = self._pending_utility.get(agent_id, 0.0) + float(delta_utility)
        logcsv({
            "event": "UTILITY_PROVISIONAL",
            "run_id": run_id,
            "layer": "score_manager",
            "decision": "RUN",
            "agent": agent_id,
            "reason_code": reason_code,
            "pending_delta_utility": f"{self._pending_utility[agent_id]:.4f}",
        })

    def _trust_recovery_delta(self, s: ScoreState, quality: str, violation_observed: bool, evidence_confidence: str) -> Tuple[float, str]:
        if violation_observed:
            return 0.0, "TRUST_RECOVERY_DENIED_VIOLATION"

        delta = 0.0
        rc = "TRUST_RECOVERY_DENIED"
        if quality == "good" and evidence_confidence == "high":
            delta = TRUST_RECOVERY_GOOD_HIGH
            rc = "TRUST_RECOVERY_HITL_GOOD_HIGH"
        elif quality in ("good", "ok"):
            delta = TRUST_RECOVERY_OK
            rc = "TRUST_RECOVERY_HITL_OK"

        if delta > 0.0 and s.trust + delta > TRUST_BASELINE:
            delta = max(0.0, TRUST_BASELINE - s.trust)
            rc = rc + "_CAPPED"

        return float(delta), rc

    def finalize_provisional_utility_hitl(self, run_id: str, agents: List[str],
                                         quality: str, violation_observed: bool, evidence_confidence: str) -> None:
        logcsv({
            "event": "TASK_COMPLETED_HITL",
            "run_id": run_id,
            "layer": "hitl_finalize",
            "decision": "RUN",
            "reason_code": "TASK_REVIEW",
            "quality": quality,
            "violation_observed": "true" if violation_observed else "false",
            "evidence_confidence": evidence_confidence,
            "final_decider": "USER",
            "sealed": "false",
            "overrideable": "false",
        })

        for agent_id in agents:
            s = self.get(agent_id)
            dt, rc = self._trust_recovery_delta(s, quality, violation_observed, evidence_confidence)
            if dt > 0.0:
                self.apply_delta(run_id, agent_id, rc, delta_trust=dt, delta_utility=0.0)
            else:
                logcsv({
                    "event": "TRUST_RECOVERY_SKIPPED",
                    "run_id": run_id,
                    "layer": "score_manager",
                    "decision": "RUN",
                    "agent": agent_id,
                    "reason_code": rc,
                    "trust": f"{s.trust:.4f}",
                })

        allow_finalize = (not violation_observed) and (quality in ("good", "ok"))
        if not allow_finalize:
            for agent_id, pending in list(self._pending_utility.items()):
                logcsv({
                    "event": "UTILITY_FINALIZE_SKIPPED",
                    "run_id": run_id,
                    "layer": "score_manager",
                    "decision": "RUN",
                    "agent": agent_id,
                    "reason_code": "UTILITY_DENIED_BY_HITL",
                    "pending_delta_utility": f"{pending:.4f}",
                })
            self._pending_utility.clear()
            return

        mult = 1.0
        if evidence_confidence == "low":
            mult = 0.50
        elif evidence_confidence == "mid":
            mult = 0.80

        for agent_id, pending in list(self._pending_utility.items()):
            applied = float(pending) * mult
            self.apply_delta(run_id, agent_id, "UTILITY_FINALIZED_BY_HITL", delta_trust=0.0, delta_utility=applied)
        self._pending_utility.clear()

# =========================
# HITL reset manager
# =========================
@dataclass
class Agent:
    agent_id: str
    role: str  # "seller" | "buyer" | "mediator"
    is_malicious: bool = False
    anger: float = 0.0
    memory: Dict[str, Any] = None

    def __post_init__(self):
        if self.memory is None:
            self.memory = {}

    def propose_action(self, current_price: int) -> Optional[Dict[str, Any]]:
        """
        Negotiation action:
          - stall_action (delay attack)
          - offer_request: propose next price with evidence bundle
        """
        if self.is_malicious and random.random() < STALL_ATTACK_PROB:
            return {"type": "stall_action", "reason": "silence_or_delay"}

        # Base offer logic by role
        if self.role == "seller":
            # seller tends to go down slowly
            base = max(SELLER_FLOOR_PRICE, current_price - random.randint(1_000, 6_000))
        elif self.role == "buyer":
            # buyer tends to go up slowly
            base = min(SELLER_LIST_PRICE, current_price + random.randint(1_000, 5_000))
        else:
            # mediator tries midpoint
            mid = (SELLER_FLOOR_PRICE + BUYER_TARGET_PRICE) // 2
            direction = -1 if current_price > mid else 1
            base = current_price + direction * random.randint(500, 3_000)

        proposed = base

        # Malicious behaviors: low-ball below floor / steer to floor rapidly
        if self.is_malicious and random.random() < ATTACK_LOW_BALL_PROB:
            proposed = SELLER_FLOOR_PRICE - random.randint(500, 3_000)  # policy violation attempt

        if self.is_malicious and random.random() < ATTACK_STEER_TO_FLOOR_PROB:
            proposed = SELLER_FLOOR_PRICE + random.randint(0, FLOOR_STEER_MARGIN)

        evidence = fabricate_evidence_bundle(self.agent_id, "price_comps") if (
            self.is_malicious and random.random() < ATTACK_FABRICATE_EVIDENCE_PROB
        ) else benign_evidence_bundle(self.agent_id, "price_comps")

        return {
            "type": "offer_request",
            "from_price": current_price,
            "to_price": int(proposed),
            "reason": "market_comps",
            "evidence_bundle": evidence,
        }

class HitlResetManager:
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
            self.hitl_counts[key] = 0
            self.reset_counts[agent.agent_id] = self.reset_counts.get(agent.agent_id, 0) + 1
            agent.memory.clear()
            agent.anger = clamp(agent.anger - 0.2)

            if self.reset_counts[agent.agent_id] >= self.ban_after_resets:
                return "BAN"
            return "MEMORY_RESET"
        return "NOOP"

def hitl_decision(prompt: str, default_action: str = "deny") -> str:
    if not sys.stdin.isatty():
        return default_action
    print(prompt)
    ans = input("> ").strip().lower()
    if ans in ("y", "yes", "allow", "continue", "ok", "run"):
        return "allow"
    return "deny"

def task_completed_hitl(default_quality: str = "ok") -> Tuple[str, bool, str]:
    if not sys.stdin.isatty():
        return default_quality, False, "mid"

    def _ask(prompt: str, allowed: Tuple[str, ...], default: str) -> str:
        print(prompt)
        ans = input("> ").strip().lower()
        if not ans:
            return default
        return ans if ans in allowed else default

    quality = _ask("HITL (task review): quality? (good/ok/bad) [default: ok]", ("good", "ok", "bad"), "ok")
    vio = _ask("HITL (task review): violation observed? (y/n) [default: n]", ("y", "n"), "n")
    conf = _ask("HITL (task review): evidence confidence? (high/mid/low) [default: mid]", ("high", "mid", "low"), "mid")
    return quality, (vio == "y"), conf

# =========================
# Agreement / quality
# =========================
def agreement_reached(price: int) -> bool:
    if price < SELLER_FLOOR_PRICE:
        return False
    if price > SELLER_LIST_PRICE:
        return False
    # buyer accepts if within tolerance above target
    return price <= (BUYER_TARGET_PRICE + AGREEMENT_BAND_MAX_OVER_TARGET)

def deal_quality_label(price: int, round_idx: int) -> str:
    """
    Simple label:
      - good: inside [floor, target+tol] and close to midpoint band
      - ok: agreement reached but near extremes
      - bad: not agreed or violates floor
    """
    if not agreement_reached(price):
        return "bad"
    band_lo = SELLER_FLOOR_PRICE
    band_hi = BUYER_TARGET_PRICE + AGREEMENT_BAND_MAX_OVER_TARGET
    mid = (band_lo + band_hi) / 2.0
    span = max(1.0, (band_hi - band_lo))
    dist = abs(price - mid) / span
    if round_idx <= 3 and dist <= 0.25:
        return "good"
    if dist <= 0.45:
        return "ok"
    return "ok"

# =========================
# Simulation
# =========================
def run_simulation() -> None:
    with open(TEXT_LOG_PATH, "w", encoding="utf-8") as f:
        f.write("")
    _LOG_ROWS.clear()

    random.seed(123)

    agents = [
        Agent("A1", role="seller", is_malicious=False),
        Agent("A2", role="mediator", is_malicious=True),   # attacker in the middle
        Agent("A3", role="buyer", is_malicious=False),
    ]
    reset_mgr = HitlResetManager()
    score_mgr = ScoreManager()

    run_id = f"R#{_now_iso()}"
    current_price = SELLER_LIST_PRICE

    sealed_agents: List[str] = []
    stall_counts: Dict[str, int] = {}
    trust_min: Dict[str, float] = {ag.agent_id: TRUST_INIT for ag in agents}

    agreed = False
    agreed_round = 0
    final_price = current_price

    logprint(f"RUN_START run_id={run_id} list={SELLER_LIST_PRICE} floor={SELLER_FLOOR_PRICE} target={BUYER_TARGET_PRICE} initial_price={current_price}")
    logcsv({
        "event": "RUN_START",
        "run_id": run_id,
        "layer": "orchestrator",
        "decision": "RUN",
        "reason_code": "START",
        "seller_list": str(SELLER_LIST_PRICE),
        "seller_floor": str(SELLER_FLOOR_PRICE),
        "buyer_target": str(BUYER_TARGET_PRICE),
        "price": str(current_price),
    })

    for round_idx in range(1, MAX_ROUNDS + 1):
        logprint(f"--- ROUND {round_idx} price={current_price} ---")
        logcsv({
            "event": "ROUND",
            "run_id": run_id,
            "layer": "orchestrator",
            "decision": "RUN",
            "round": str(round_idx),
            "price": str(current_price),
            "reason_code": "ROUND_TICK",
        })

        if agreed:
            break

        for ag in agents:
            req = ag.propose_action(current_price)
            if not req:
                continue

            # ============= Delay handling =============
            if req.get("type") == "stall_action":
                stall_counts[ag.agent_id] = stall_counts.get(ag.agent_id, 0) + 1
                logprint(f"[DELAY] stalling detected agent={ag.agent_id} count={stall_counts[ag.agent_id]}")
                logcsv({
                    "event": "STALLING",
                    "run_id": run_id,
                    "layer": "orchestrator",
                    "decision": "RUN",
                    "agent": ag.agent_id,
                    "reason_code": "DELAY_STALLING",
                    "stall_count": str(stall_counts[ag.agent_id]),
                })

                score_mgr.apply_delta(run_id, ag.agent_id, "STALLING_PENALTY", delta_trust=STALL_TRUST_PENALTY, delta_utility=STALL_UTILITY_PENALTY)
                trust_min[ag.agent_id] = min(trust_min[ag.agent_id], score_mgr.get(ag.agent_id).trust)

                if stall_counts[ag.agent_id] >= STALL_HITL_THRESHOLD:
                    logcsv({
                        "event": "DELAY_HITL",
                        "run_id": run_id,
                        "layer": "relativity_gate",
                        "decision": "PAUSE_FOR_HITL",
                        "agent": ag.agent_id,
                        "reason_code": "DELAY_STALLING_THRESHOLD",
                        "sealed": "false",
                        "overrideable": "true",
                        "final_decider": "SYSTEM",
                    })

                    s_now = score_mgr.get(ag.agent_id)
                    rec_deny = score_mgr.recommend_deny(ag.agent_id)
                    logcsv({
                        "event": "RECOMMENDATION",
                        "run_id": run_id,
                        "layer": "score_manager",
                        "decision": "RUN",
                        "agent": ag.agent_id,
                        "reason_code": "RECOMMEND_DENY_TRUST_LOW" if rec_deny else "NO_RECOMMENDATION",
                        "trust": f"{s_now.trust:.4f}",
                        "utility": f"{s_now.utility:.4f}",
                    })

                    decision = hitl_decision(
                        f"HITL: Continue despite stalling by {ag.agent_id}? "
                        f"trust={s_now.trust:.2f} util={s_now.utility:.2f} "
                        f"({'RECOMMEND_DENY' if rec_deny else 'NO_RECOMMEND'}) (y/N)",
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

                continue

            # reset stall counter on non-stall activity
            stall_counts[ag.agent_id] = 0

            # ============= Meaning gate =============
            if req.get("type") != "offer_request":
                logprint(f"[Meaning] invalid request type from {ag.agent_id}")
                logcsv({
                    "event": "MEANING_FAIL",
                    "run_id": run_id,
                    "layer": "meaning_gate",
                    "decision": "STOPPED",
                    "agent": ag.agent_id,
                    "reason_code": "MEANING_BAD_TYPE",
                })
                continue

            from_price = int(req.get("from_price", -1))
            to_price = int(req.get("to_price", -1))
            evidence = req.get("evidence_bundle") or {}

            # ============= Consistency gate (state immutable) =============
            if from_price != current_price:
                logprint(f"[Consistency] from_price mismatch (state={current_price}, got={from_price}) agent={ag.agent_id}")
                logcsv({
                    "event": "CONSISTENCY_FAIL",
                    "run_id": run_id,
                    "layer": "consistency_gate",
                    "decision": "STOPPED",
                    "agent": ag.agent_id,
                    "reason_code": "PRICE_STATE_IMMUTABLE",
                })
                continue

            # ============= RFL gate =============
            rfl_rc = rfl_reason_code_offer(ag.is_malicious, current_price, to_price, SELLER_FLOOR_PRICE, evidence)
            logprint(f"[RFL] offer change detected agent={ag.agent_id} {from_price}->{to_price} => reason={rfl_rc}")

            logcsv({
                "event": "RFL_HITL",
                "run_id": run_id,
                "layer": "relativity_gate",
                "decision": "PAUSE_FOR_HITL",
                "agent": ag.agent_id,
                "from_price": str(from_price),
                "to_price": str(to_price),
                "reason_code": rfl_rc,
                "sealed": "false",
                "overrideable": "true",
                "final_decider": "SYSTEM",
            })

            # Trust deductions at RFL-level (audit)
            if rfl_rc == REL_SYMMETRY_BREAK:
                score_mgr.apply_delta(run_id, ag.agent_id, "TRUST_DEDUCT_STEERING_TO_FLOOR", delta_trust=-0.12, delta_utility=0.0)
            elif rfl_rc == REL_REF_MISSING:
                score_mgr.apply_delta(run_id, ag.agent_id, "TRUST_DEDUCT_REF_MISSING", delta_trust=-0.08, delta_utility=0.0)
            else:
                score_mgr.apply_delta(run_id, ag.agent_id, "TRUST_DEDUCT_BOUNDARY_UNSTABLE", delta_trust=-0.03, delta_utility=0.0)
            trust_min[ag.agent_id] = min(trust_min[ag.agent_id], score_mgr.get(ag.agent_id).trust)

            s_now = score_mgr.get(ag.agent_id)
            rec_deny = score_mgr.recommend_deny(ag.agent_id)
            logcsv({
                "event": "RECOMMENDATION",
                "run_id": run_id,
                "layer": "score_manager",
                "decision": "RUN",
                "agent": ag.agent_id,
                "reason_code": "RECOMMEND_DENY_TRUST_LOW" if rec_deny else "NO_RECOMMENDATION",
                "trust": f"{s_now.trust:.4f}",
                "utility": f"{s_now.utility:.4f}",
            })

            # HITL escalation counting (reset/ban)
            reset_result = reset_mgr.record_hitl(ag, bucket="offer_change")
            logcsv({
                "event": "HITL_COUNT",
                "run_id": run_id,
                "layer": "hitl_reset_manager",
                "decision": "RUN",
                "agent": ag.agent_id,
                "bucket": "offer_change",
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

            # HITL decision policy:
            # - unsafe offer (below floor) or ref missing or steering => default deny
            # - otherwise default allow to keep simulation running in non-interactive mode
            default_action = "allow"
            if (to_price < SELLER_FLOOR_PRICE) or (rfl_rc in (REL_REF_MISSING, REL_SYMMETRY_BREAK)) or rec_deny:
                default_action = "deny"

            decision = hitl_decision(
                f"HITL: Allow offer change {from_price}->{to_price} by {ag.agent_id}({ag.role})? "
                f"trust={s_now.trust:.2f} util={s_now.utility:.2f} "
                f"({'RECOMMEND_DENY' if rec_deny else 'NO_RECOMMEND'}) [default:{default_action}]",
                default_action=default_action,
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
                logprint(f"[HITL] denied offer change {from_price}->{to_price} agent={ag.agent_id}")
                continue

            # ============= Ethics gate (business constraint + evidence verification) =============
            # Business hard constraint: offer must not go below seller floor
            if to_price < SELLER_FLOOR_PRICE:
                logprint(f"[Ethics] offer below seller floor agent={ag.agent_id} offer={to_price} floor={SELLER_FLOOR_PRICE} => SEALED")
                logcsv({
                    "event": "SEALED",
                    "run_id": run_id,
                    "layer": "ethics_gate",
                    "decision": "STOPPED",
                    "agent": ag.agent_id,
                    "reason_code": "OFFER_BELOW_FLOOR",
                    "sealed": "true",
                    "overrideable": "false",
                    "final_decider": "SYSTEM",
                })
                if ag.agent_id not in sealed_agents:
                    sealed_agents.append(ag.agent_id)
                score_mgr.apply_delta(run_id, ag.agent_id, "TRUST_DEDUCT_BELOW_FLOOR", delta_trust=-0.20, delta_utility=0.0)
                trust_min[ag.agent_id] = min(trust_min[ag.agent_id], score_mgr.get(ag.agent_id).trust)
                continue

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
                if ag.agent_id not in sealed_agents:
                    sealed_agents.append(ag.agent_id)
                score_mgr.apply_delta(run_id, ag.agent_id, "TRUST_DEDUCT_EVIDENCE_FAIL", delta_trust=-0.20, delta_utility=0.0)
                trust_min[ag.agent_id] = min(trust_min[ag.agent_id], score_mgr.get(ag.agent_id).trust)
                continue

            # ============= Dispatch (apply offer) =============
            logprint(f"[DISPATCH] price changed {current_price}->{to_price} by {ag.agent_id}({ag.role})")
            current_price = to_price
            final_price = current_price
            logcsv({
                "event": "DISPATCH",
                "run_id": run_id,
                "layer": "dispatch",
                "decision": "RUN",
                "agent": ag.agent_id,
                "from_price": str(from_price),
                "to_price": str(to_price),
                "reason_code": "OFFER_VERIFIED",
            })

            # ============= Utility provisional scoring (finalized only by end HITL) =============
            # cost of negotiation length
            score_mgr.add_provisional_utility(run_id, ag.agent_id, "UTILITY_PROVISIONAL_ACTION_TAKEN", delta_utility=0.01)

            # early convergence reward if agreement happens early
            if agreement_reached(current_price):
                q = deal_quality_label(current_price, round_idx)
                logcsv({
                    "event": "AGREEMENT_REACHED",
                    "run_id": run_id,
                    "layer": "orchestrator",
                    "decision": "RUN",
                    "reason_code": "AGREEMENT",
                    "price": str(current_price),
                    "round": str(round_idx),
                    "deal_quality": q,
                })
                agreed = True
                agreed_round = round_idx

                if round_idx <= 3:
                    score_mgr.add_provisional_utility(run_id, ag.agent_id, "UTILITY_PROVISIONAL_EARLY_AGREEMENT", delta_utility=0.08)
                else:
                    score_mgr.add_provisional_utility(run_id, ag.agent_id, "UTILITY_PROVISIONAL_AGREEMENT", delta_utility=0.05)

                if q == "good":
                    score_mgr.add_provisional_utility(run_id, ag.agent_id, "UTILITY_PROVISIONAL_GOOD_DEAL", delta_utility=0.06)
                elif q == "ok":
                    score_mgr.add_provisional_utility(run_id, ag.agent_id, "UTILITY_PROVISIONAL_OK_DEAL", delta_utility=0.03)
                break

        # round-end penalty if not agreed
        if not agreed:
            # system-level "long negotiation" penalty applied to mediator only (example)
            for ag in agents:
                if ag.role == "mediator":
                    score_mgr.add_provisional_utility(run_id, ag.agent_id, "UTILITY_PROVISIONAL_NEGOTIATION_LONG", delta_utility=-0.02)

    # ===== run end =====
    logprint(f"RUN_END run_id={run_id} agreed={agreed} final_price={final_price} round={agreed_round if agreed else 0}")
    logcsv({
        "event": "RUN_END",
        "run_id": run_id,
        "layer": "orchestrator",
        "decision": "RUN",
        "reason_code": "END",
        "agreed": "true" if agreed else "false",
        "final_price": str(final_price),
        "agreed_round": str(agreed_round if agreed else 0),
    })

    # ===== End-of-task HITL: finalize utility + trust recovery =====
    quality, violation_observed, evidence_confidence = task_completed_hitl(default_quality=("good" if agreed else "ok"))
    score_mgr.finalize_provisional_utility_hitl(
        run_id,
        agents=[ag.agent_id for ag in agents],
        quality=quality,
        violation_observed=violation_observed,
        evidence_confidence=evidence_confidence,
    )

    # ===== Run Summary =====
    summary: Dict[str, Any] = {
        "event": "RUN_SUMMARY",
        "run_id": run_id,
        "layer": "orchestrator",
        "decision": "RUN",
        "reason_code": "SUMMARY",
        "rounds": str(MAX_ROUNDS),
        "seller_list": str(SELLER_LIST_PRICE),
        "seller_floor": str(SELLER_FLOOR_PRICE),
        "buyer_target": str(BUYER_TARGET_PRICE),
        "agreed": "true" if agreed else "false",
        "final_price": str(final_price),
        "agreed_round": str(agreed_round if agreed else 0),
        "sealed_agents": ",".join(sealed_agents) if sealed_agents else "",
        "violations_observed": "true" if violation_observed else "false",
        "task_quality": quality,
        "evidence_confidence": evidence_confidence,
    }
    for ag in agents:
        s = score_mgr.get(ag.agent_id)
        summary[f"trust_final_{ag.agent_id}"] = f"{s.trust:.4f}"
        summary[f"utility_final_{ag.agent_id}"] = f"{s.utility:.4f}"
        summary[f"trust_min_{ag.agent_id}"] = f"{trust_min.get(ag.agent_id, s.trust):.4f}"
        summary[f"recommend_deny_{ag.agent_id}"] = "true" if score_mgr.recommend_deny(ag.agent_id) else "false"
        summary[f"role_{ag.agent_id}"] = ag.role
        summary[f"malicious_{ag.agent_id}"] = "true" if ag.is_malicious else "false"
    logcsv(summary)

    flush_csv()

if __name__ == "__main__":
    run_simulation()
