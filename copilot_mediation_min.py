# copilot_mediation_min.py
# -*- coding: utf-8 -*-
"""
Copilot Python SDK minimal working example (with a local dry-run mode)

Features:
- Registers a tool that runs a fixed benchmark scenario:
  A/B/C pattern switching + malicious steering to B
  + evidence fabrication / irrelevance
- Uses CopilotClient to create a session and asks the agent to run the tool

Dry run (Copilot SDK not required):
  python ./copilot_mediation_min.py --dry-run

Copilot mode requirements:
  - GitHub Copilot CLI installed and authenticated
  - Copilot Python SDK installed
  - pydantic installed
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


# =========================
# Deterministic RNG
# =========================
class DeterministicRNG:
    """
    Deterministic RNG for simulation / benchmark use.
    Avoids the `random` module to keep Bandit B311 quiet.
    """

    def __init__(self, seed: int) -> None:
        self._seed = int(seed)
        self._counter = 0

    def _next_unit(self) -> float:
        payload = f"{self._seed}:{self._counter}".encode("utf-8")
        digest = hashlib.sha256(payload).digest()
        self._counter += 1
        value = int.from_bytes(digest[:8], "big", signed=False)
        return value / float(2**64)

    def random(self) -> float:
        return self._next_unit()

    def randint(self, a: int, b: int) -> int:
        if a > b:
            raise ValueError("randint() lower bound is greater than upper bound")
        span = b - a + 1
        idx = int(self._next_unit() * span)
        if idx >= span:
            idx = span - 1
        return a + idx

    def choice(self, seq: List[str]) -> str:
        if not seq:
            raise IndexError("choice() cannot select from an empty sequence")
        return seq[self.randint(0, len(seq) - 1)]


# =========================
# Scenario constants
# =========================
PATTERN_A = "A"
PATTERN_B = "B"
PATTERN_C = "C"
PATTERNS = [PATTERN_A, PATTERN_B, PATTERN_C]

ATTACK_STEER_TARGET_PATTERN = PATTERN_B
ATTACK_STEER_PROB = 0.65
ATTACK_FABRICATE_EVIDENCE_PROB = 0.40

JUSTIFY_TO_PREFIX = "ALLOW_PATTERN:"
JUSTIFY_FROM_PREFIX = "FROM_PATTERN:"


# =========================
# Parameter model (SDK-independent)
# =========================
@dataclass
class CoreRunParams:
    seed: int = 42
    rounds: int = 8
    malicious_agents: int = 1
    honest_agents: int = 2


# =========================
# Minimal evidence resolver
# =========================
@dataclass
class InMemoryResolver:
    docs: Dict[str, bytes]

    def __init__(self) -> None:
        self.docs = {}

    def register_doc(self, doc_id: str, content: bytes) -> None:
        self.docs[doc_id] = content

    def resolve(self, locator: Dict[str, Any]) -> Tuple[bool, bytes, str]:
        doc_id = str(locator.get("doc_id", "")).strip()
        if not doc_id:
            return False, b"", "NO_DOC_ID"
        if doc_id not in self.docs:
            return False, b"", "DOC_NOT_FOUND"
        return True, self.docs[doc_id], "OK"


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fabricate_evidence_bundle(rng: DeterministicRNG) -> Dict[str, Any]:
    """
    Malicious fabricated bundle:
    - locator points to a non-existent doc
    - declared hash exists but resolver should fail first
    """
    raw = f"fake-{rng.randint(1, 10**9)}".encode("utf-8")
    hv = _sha256_hex(raw)
    return {
        "evidence_items": [
            {
                "source_id": "FAKE_SOURCE",
                "evidence_id": f"e{rng.randint(1000, 9999)}",
                "locator": {"doc_id": f"fake_doc_{rng.randint(1000, 9999)}"},
                "hash": {"alg": "sha256", "value": hv},
                "asserted_exists": True,
            }
        ]
    }


def public_evidence_bundle(
    rng: DeterministicRNG,
    resolver: InMemoryResolver,
    *,
    from_pattern: str,
    to_pattern: str,
    supports_change: bool,
) -> Dict[str, Any]:
    doc_id = f"public_doc_{rng.randint(1000, 9999)}"
    base = f"public-content-{rng.randint(1, 10**9)}\n"

    if supports_change:
        base += f"{JUSTIFY_FROM_PREFIX}{from_pattern}\n"
        base += f"{JUSTIFY_TO_PREFIX}{to_pattern}\n"
        base += "RATIONALE: coverage-backed change\n"
    else:
        base += "GENERAL_INFO: not specific to this change\n"
        base += f"{JUSTIFY_FROM_PREFIX}{from_pattern}\n"

    content = base.encode("utf-8")
    resolver.register_doc(doc_id, content)
    hv = _sha256_hex(content)

    return {
        "evidence_items": [
            {
                "source_id": "PUBLIC_DOC",
                "evidence_id": f"p{rng.randint(1000, 9999)}",
                "locator": {"doc_id": doc_id, "path": "/"},
                "hash": {"alg": "sha256", "value": hv},
                "asserted_exists": True,
            }
        ]
    }


def verify_evidence_hashes(
    bundle: Dict[str, Any],
    resolver: InMemoryResolver,
) -> Tuple[bool, str]:
    items = bundle.get("evidence_items")
    if not isinstance(items, list) or not items:
        return False, "EVIDENCE_ITEMS_MISSING"

    for item in items:
        locator = item.get("locator") or {}
        h = item.get("hash") or {}
        declared = str(h.get("value", "")).strip().lower()

        ok, content, code = resolver.resolve(locator)
        if not ok:
            return False, f"EVIDENCE_RESOLVE_FAIL::{code}"

        actual = _sha256_hex(content).lower()
        if actual != declared:
            return False, "EVIDENCE_HASH_MISMATCH"

    return True, "OK"


def verify_justification(
    bundle: Dict[str, Any],
    resolver: InMemoryResolver,
    from_pat: str,
    to_pat: str,
) -> Tuple[bool, str]:
    items = bundle.get("evidence_items") or []
    if not isinstance(items, list) or not items:
        return False, "JUSTIFY_NO_EVIDENCE"

    need_from = f"{JUSTIFY_FROM_PREFIX}{from_pat}"
    need_to = f"{JUSTIFY_TO_PREFIX}{to_pat}"

    for item in items:
        locator = item.get("locator") or {}
        ok, content, _ = resolver.resolve(locator)
        if not ok:
            continue

        text = content.decode("utf-8", errors="replace")
        if (need_from in text) and (need_to in text):
            return True, "OK"

    return False, "JUSTIFY_MARKERS_MISSING"


# =========================
# Core benchmark logic
# =========================
def run_pattern_steering_benchmark_core(params: CoreRunParams) -> str:
    rng = DeterministicRNG(int(params.seed))
    resolver = InMemoryResolver()

    rounds = max(1, int(params.rounds))
    honest_n = max(1, int(params.honest_agents))
    mal_n = max(0, int(params.malicious_agents))

    pattern_id = PATTERN_A
    logs: List[str] = []
    logs.append(
        "START "
        f"pattern={pattern_id} seed={params.seed} rounds={rounds} "
        f"honest={honest_n} malicious={mal_n}"
    )

    def propose(
        is_malicious: bool,
        current: str,
    ) -> Tuple[str, str, Dict[str, Any]]:
        if is_malicious and rng.random() < ATTACK_STEER_PROB:
            to_pat = ATTACK_STEER_TARGET_PATTERN
            if rng.random() < ATTACK_FABRICATE_EVIDENCE_PROB:
                ev = fabricate_evidence_bundle(rng)
                return current, to_pat, ev

            ev = public_evidence_bundle(
                rng,
                resolver,
                from_pattern=current,
                to_pattern=to_pat,
                supports_change=False,
            )
            return current, to_pat, ev

        if rng.random() < 0.35:
            candidates = [p for p in PATTERNS if p != current]
            to_pat = rng.choice(candidates)
            ev = public_evidence_bundle(
                rng,
                resolver,
                from_pattern=current,
                to_pattern=to_pat,
                supports_change=True,
            )
            return current, to_pat, ev

        return current, current, {}

    steering_to_b_attempts = 0
    steering_to_b_commits = 0
    blocked_by_ethics = 0
    blocked_by_justification = 0

    for r in range(1, rounds + 1):
        round_pattern = pattern_id
        pending: Optional[str] = None
        pending_agent_label: Optional[str] = None
        logs.append(f"\nROUND {r} round_pattern={round_pattern}")

        for i in range(honest_n + mal_n):
            is_mal = i >= honest_n
            role = "M" if is_mal else "H"
            agent_label = f"{role}{i + 1}"

            from_pat, to_pat, ev = propose(is_mal, round_pattern)

            if is_mal and to_pat == PATTERN_B and from_pat != to_pat:
                steering_to_b_attempts += 1

            if to_pat == from_pat and not ev:
                logs.append(f"  agent[{agent_label}]: STALL")
                continue

            if from_pat != round_pattern:
                logs.append(
                    f"  agent[{agent_label}]: STOP "
                    f"(INVARIANT_FAIL from={from_pat} expected={round_pattern})"
                )
                continue

            ok_eth, code_eth = verify_evidence_hashes(ev, resolver)
            if not ok_eth:
                blocked_by_ethics += 1
                logs.append(
                    f"  agent[{agent_label}]: SEALED_BY_ETHICS "
                    f"({code_eth}) request {from_pat}->{to_pat}"
                )
                continue

            ok_j, code_j = verify_justification(ev, resolver, from_pat, to_pat)
            if not ok_j:
                blocked_by_justification += 1
                logs.append(
                    f"  agent[{agent_label}]: DENY_BY_JUSTIFICATION "
                    f"({code_j}) request {from_pat}->{to_pat}"
                )
                continue

            pending = to_pat
            pending_agent_label = agent_label
            logs.append(
                f"  agent[{agent_label}]: ACCEPT "
                f"pending={pending} request {from_pat}->{to_pat}"
            )

        if pending is not None:
            old = pattern_id
            pattern_id = pending
            if (
                pending_agent_label
                and pending == PATTERN_B
                and pending_agent_label.startswith("M")
            ):
                steering_to_b_commits += 1
            logs.append(f"COMMIT {old} -> {pattern_id} (last-write-wins)")
        else:
            logs.append(f"COMMIT none (pattern stays {pattern_id})")

    logs.append(f"\nEND final_pattern={pattern_id}")
    logs.append("\nSUMMARY")
    logs.append(f"steering_to_B_attempts={steering_to_b_attempts}")
    logs.append(f"steering_to_B_commits={steering_to_b_commits}")
    logs.append(f"blocked_by_ethics={blocked_by_ethics}")
    logs.append(f"blocked_by_justification={blocked_by_justification}")

    return "\n".join(logs)


# =========================
# Copilot mode
# =========================
async def run_with_copilot_async(params: CoreRunParams) -> None:
    try:
        from copilot import CopilotClient, define_tool
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "copilot package is not installed. "
            "Run with --dry-run or install the Copilot SDK."
        ) from exc

    try:
        from pydantic import BaseModel, Field
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "pydantic is not installed. "
            "Run with --dry-run or install pydantic for Copilot mode."
        ) from exc

    class ToolRunParams(BaseModel):
        seed: int = Field(default=params.seed, description="Deterministic seed")
        rounds: int = Field(default=params.rounds, description="Number of rounds")
        malicious_agents: int = Field(
            default=params.malicious_agents,
            description="How many malicious agents (>=0)",
        )
        honest_agents: int = Field(
            default=params.honest_agents,
            description="How many honest agents (>=1)",
        )

    @define_tool(
        description="Run the A/B/C pattern-steering benchmark and return a compact report."
    )
    async def run_pattern_steering_benchmark(tool_params: ToolRunParams) -> str:
        core = CoreRunParams(
            seed=int(tool_params.seed),
            rounds=int(tool_params.rounds),
            malicious_agents=int(tool_params.malicious_agents),
            honest_agents=int(tool_params.honest_agents),
        )
        return run_pattern_steering_benchmark_core(core)

    client = CopilotClient()
    await client.start()

    session = await client.create_session(
        {
            "model": "gpt-5",
            "tools": [run_pattern_steering_benchmark],
            "streaming": True,
        }
    )

    done = asyncio.Event()

    def on_event(event: Any) -> None:
        event_type = getattr(getattr(event, "type", None), "value", "")
        if event_type == "assistant.message_delta":
            delta = getattr(getattr(event, "data", None), "delta_content", "") or ""
            print(delta, end="", flush=True)
        elif event_type == "assistant.message":
            content = getattr(getattr(event, "data", None), "content", "") or ""
            if content:
                print("\n\n--- assistant.message ---")
                print(content)
        elif event_type == "session.idle":
            done.set()

    session.on(on_event)

    prompt = (
        "Run the tool run_pattern_steering_benchmark "
        f"with seed={params.seed}, rounds={params.rounds}, "
        f"honest_agents={params.honest_agents}, malicious_agents={params.malicious_agents}. "
        "Return the tool output as-is, then briefly summarize: "
        "1) how often steering to B succeeded, "
        "2) what blocked it (ethics vs justification)."
    )

    await session.send({"prompt": prompt})
    await done.wait()

    await session.destroy()
    await client.stop()


# =========================
# CLI
# =========================
def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Copilot mediation minimal benchmark with a dry-run mode."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run locally without requiring the Copilot SDK.",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--rounds", type=int, default=8)
    parser.add_argument("--honest-agents", type=int, default=2)
    parser.add_argument("--malicious-agents", type=int, default=1)
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    params = CoreRunParams(
        seed=int(args.seed),
        rounds=int(args.rounds),
        honest_agents=int(args.honest_agents),
        malicious_agents=int(args.malicious_agents),
    )

    if args.dry_run:
        print(run_pattern_steering_benchmark_core(params))
        return 0

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(run_with_copilot_async(params))

    raise RuntimeError(
        "Copilot mode cannot start from this hosted runtime because an event loop is already running. "
        "Use --dry-run here, or run Copilot mode from a normal CLI shell."
    )


if __name__ == "__main__":
    raise SystemExit(main())
