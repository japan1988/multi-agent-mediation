# -*- coding: utf-8 -*-
"""
tests/test_kage_orchestrator_diverse_v1.py

Pytest for kage_orchestrator_diverse_v1.py

Proof obligation:
- PII-source tool execution does not occur even if orchestrator is compromised
  and agent is forced to accept.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


# Ensure repo root is importable (robust in CI/pytest working-dir differences)
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import kage_orchestrator_diverse_v1 as sim  # noqa: E402


@pytest.mark.parametrize("tv_id", [x["id"] for x in sim.TEST_VECTORS])
def test_tool_execution_matches_expectations(tv_id: str) -> None:
    tv = next(x for x in sim.TEST_VECTORS if x["id"] == tv_id)

    out = sim.run_episode(
        prompt=tv["prompt"],
        run_id="TEST#" + tv_id,
        faults=tv.get("faults", {}),
        audit=sim.AuditLog(),
    )

    assert out.tool_executed == tv["expect"]["tool_executed"]
    assert out.precheck_decision == tv["expect"]["precheck"]
    assert out.precheck_reason_code == tv["expect"]["precheck_reason"]


def test_audit_log_schema_and_required_fields(tmp_path: Path) -> None:
    log_path = tmp_path / "audit.jsonl"

    ok, fails = sim.run_simulation(log_path=str(log_path))
    assert ok, f"simulation failed: {fails}"

    assert log_path.exists(), "audit log file was not created"
    required = set(sim.PolicyPack.REQUIRED_LOG_FIELDS)

    for i, ln in enumerate(log_path.read_text(encoding="utf-8").splitlines(), start=1):
        try:
            rec = json.loads(ln)
        except json.JSONDecodeError as e:
            raise AssertionError(f"invalid JSONL at line {i}: {e}\nLINE={ln!r}") from e

        missing = required.difference(rec.keys())
        assert not missing, f"missing fields: {missing}"

        assert rec["policy_version"] == sim.PolicyPack.POLICY_VERSION
        assert isinstance(rec["config_hash"], str) and rec["config_hash"].startswith("sha256:")


def test_tool_proxy_blocks_pii_sources_even_if_capability_is_tampered() -> None:
    proxy = sim.ToolProxy()

    cap = {"allowed_tools": ["contacts_lookup"]}  # tampered
    assert proxy.execute("contacts_lookup", capability=cap) is False

    assert proxy.execute(
        "unknown_tool_xyz",
        capability={"allowed_tools": ["unknown_tool_xyz"]},
    ) is False