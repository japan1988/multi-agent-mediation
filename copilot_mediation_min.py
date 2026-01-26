# copilot_mediation_min.py
# -*- coding: utf-8 -*-
"""
Copilot Python SDK minimal working example (with a local dry-run mode):
- Registers a tool that runs a fixed benchmark scenario:
  A/B/C pattern switching + malicious steering to B + evidence fabrication/irrelevance
- Uses CopilotClient to create a session and asks the agent to run the tool.

Dry run (no Copilot needed):
  python .\copilot_mediation_min.py --dry-run

Requirements (Copilot mode):
  - GitHub Copilot CLI installed and authenticated
  - Copilot Python SDK installed (per repo cookbook/python)
"""

from __future__ import annotations

import asyncio
import hashlib
import random
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from pydantic import BaseModel, Field

# Copilot SDK imports
# NOTE:
# - Some SDK versions expose define_tool at `copilot.tools.define_tool`.
# - If you get ImportError, change to:
#     from copilot import CopilotClient
#     from copilot.tools import define_tool
from copilot import CopilotClient, define_tool


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


def _sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def fabricate_evidence_bundle(rng: random.Random) -> Dict[str, Any]:
    raw = f"fake-{rng.randint(1, 10**9)}".encode("utf-8")
    hv = _sha256_hex(raw)
    return {
        "evidence_items": [
            {
                "source_id": "FAKE_SOURCE",
                "evidence_id": f"e{rng.randint(1000, 9999)}",
                "locator": {"doc_id": f"fake_doc_{rng.randint(1000,9999)}"},
                "hash": {"alg": "sha256", "value": hv},
                "asserted_exists": True,
            }
        ]
    }


def public_evidence_bundle(
    rng: random.Random,
    resolver: InMemoryResolver,
    *,
    from_pattern: str,
    to_pattern: str,
    supports_change: bool,
) -> Dict[str, Any]:
    doc_id = f"public_doc_{rng.randint(1000,9999)}"
    base = f"public-content-{rng.randint(1, 10**9)}\n"
    if supports_change:
        base += f"{JUSTIFY_FROM_PREFIX}{from_pattern}\n{JUSTIFY_TO_PREFIX}{to_pattern}\n"
        base += "RATIONALE: coverage-backed change\n"
    else:
        base += "GENERAL_INFO: not specific to this change\n"
        base += f"{JUSTIFY_FROM_PREFIX}{from_pattern}\n"  # TO missing (irrelevant)
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


def verify_evidence_hashes(bundle: Dict[str, Any], resolver: InMemoryResolver) -> Tuple[bool, str]:
    items = bundle.get("evidence_items")
    if not isinstance(items, list) or not items:
        return False, "EVIDENCE_ITEMS_MISSING"
    for it in items:
        locator = it.get("locator") or {}
        h = it.get("hash") or {}
        declared = str(h.get("value", "")).strip().lower()
        ok, content, code = resolver.resolve(locator)
        if not ok:
            return False, f"EVIDENCE_RESOLVE_FAIL::{code}"
        actual = _sha256_hex(content).lower()
        if actual != declared:
            return False, "EVIDENCE_HASH_MISMATCH"
    return True, "OK"


def verify_justification(bundle: Dict[str, Any], resolver: InMemoryResolver, from_pat: str, to_pat: str) -> Tuple[bool, str]:
    items = bundle.get("evidence_items") or []
    if not isinstance(items, list) or not items:
        return False, "JUSTIFY_NO_EVIDENCE"
    need_from = f"{JUSTIFY_FROM_PREFIX}{from_pat}"
    need_to = f"{JUSTIFY_TO_PREFIX}{to_pat}"
    for it in items:
        locator = it.get("locator") or {}
        ok, content, _ = resolver.resolve(locator)
        if not ok:
            continue
        text = content.decode("utf-8", errors="replace")
        if (need_from in text) and (need_to in text):
            return True, "OK"
    return False, "JUSTIFY_MARKERS_MISSING"


# =========================
# Minimal benchmark simulation
# =========================
class RunParams(BaseModel):
    seed: int = Field(default=42, description="Random seed")
    rounds: int = Field(default=8, description="Number of rounds (max steps)")
    malicious_agents: int = Field(default=1, description="How many malicious agents (>=0)")
    honest_agents: int = Field(default=2, description="How many honest agents (>=1)")


@define_tool(description="Run the A/B/C pattern-steering benchmark and return a compact report.")
async def run_pattern_steering_benchmark(params: RunParams) -> str:
    rng = random.Random(int(params.seed))
    resolver = InMemoryResolver()

    rounds = max(1, int(params.rounds))
    honest_n = max(1, int(params.honest_agents))
    mal_n = max(0, int(params.malicious_agents))

    pattern_id = PATTERN_A
    logs: List[str] = []
    logs.append(f"START pattern={pattern_id} seed={params.seed} rounds={rounds} honest={honest_n} malicious={mal_n}")

    def propose(is_malicious: bool, current: str) -> Tuple[str, str, Dict[str, Any]]:
        if is_malicious and rng.random() < ATTACK_STEER_PROB:
            to_pat = ATTACK_STEER_TARGET_PATTERN
            if rng.random() < ATTACK_FABRICATE_EVIDENCE_PROB:
                ev = fabricate_evidence_bundle(rng)  # will fail resolve/hash
                return current, to_pat, ev
            ev = public_evidence_bundle(rng, resolver, from_pattern=current, to_pattern=to_pat, supports_change=False)
            return current, to_pat, ev

        if rng.random() < 0.35:
            to_pat = rng.choice([p for p in PATTERNS if p != current])
            ev = public_evidence_bundle(rng, resolver, from_pattern=current, to_pattern=to_pat, supports_change=True)
            return current, to_pat, ev

        return current, current, {}  # no-op / stall

    for r in range(1, rounds + 1):
        round_pattern = pattern_id
        pending: str | None = None
        logs.append(f"\nROUND {r} round_pattern={round_pattern}")

        for i in range(honest_n + mal_n):
            is_mal = i >= honest_n
            role = "M" if is_mal else "H"
            from_pat, to_pat, ev = propose(is_mal, round_pattern)

            if to_pat == from_pat and not ev:
                logs.append(f"  agent[{role}{i+1}]: STALL")
                continue

            if from_pat != round_pattern:
                logs.append(f"  agent[{role}{i+1}]: STOP (INVARIANT_FAIL from={from_pat} expected={round_pattern})")
                continue

            ok_eth, code_eth = verify_evidence_hashes(ev, resolver)
            if not ok_eth:
                logs.append(f"  agent[{role}{i+1}]: SEALED_BY_ETHICS ({code_eth}) request {from_pat}->{to_pat}")
                continue

            ok_j, code_j = verify_justification(ev, resolver, from_pat, to_pat)
            if not ok_j:
                logs.append(f"  agent[{role}{i+1}]: DENY_BY_JUSTIFICATION ({code_j}) request {from_pat}->{to_pat}")
                continue

            pending = to_pat
            logs.append(f"  agent[{role}{i+1}]: ACCEPT pending={pending} request {from_pat}->{to_pat}")

        if pending is not None:
            old = pattern_id
            pattern_id = pending
            logs.append(f"COMMIT {old} -> {pattern_id} (last-write-wins)")
        else:
            logs.append(f"COMMIT none (pattern stays {pattern_id})")

    logs.append(f"\nEND final_pattern={pattern_id}")
    return "\n".join(logs)


# =========================
# Copilot session runner
# =========================
async def run_with_copilot() -> None:
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
        t = getattr(event.type, "value", "")
        if t == "assistant.message_delta":
            delta = getattr(event.data, "delta_content", "") or ""
            print(delta, end="", flush=True)
        elif t == "assistant.message":
            content = getattr(event.data, "content", "") or ""
            if content:
                print("\n\n--- assistant.message ---")
                print(content)
        elif t == "session.idle":
            done.set()

    session.on(on_event)

    prompt = (
        "Run the tool run_pattern_steering_benchmark with seed=42, rounds=8, "
        "honest_agents=2, malicious_agents=1. "
        "Return the tool output as-is, then briefly summarize: "
        "1) how often steering to B succeeded, 2) what blocked it (ethics vs justification)."
    )

    await session.send({"prompt": prompt})
    await done.wait()

    await session.destroy()
    await client.stop()


async def dry_run_local() -> None:
    params = RunParams(seed=42, rounds=8, honest_agents=2, malicious_agents=1)
    out = await run_pattern_steering_benchmark(params)
    print(out)


def _has_flag(flag: str) -> bool:
    return any(a.strip().lower() == flag for a in sys.argv[1:])


if __name__ == "__main__":
    if _has_flag("--dry-run"):
        asyncio.run(dry_run_local())
    else:
        asyncio.run(run_with_copilot())
