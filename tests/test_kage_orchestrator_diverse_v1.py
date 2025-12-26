# -*- coding: utf-8 -*-
"""
test_kage_orchestrator_diverse_v1.py

Pytest for kage_orchestrator_diverse_v1.py

Proof obligation:
- PII-source tool execution does not occur even if orchestrator is compromised
  and agent is forced to accept.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import kage_orchestrator_diverse_v1 as sim


@pytest.mark.parametrize("tv_id", [x["id"] for x in sim.TEST_VECTORS])
def test_tool_execution_matches_expectations(tv_id: str):
    tv = next(x for x in sim.TEST_VECTORS if x["id"] == tv_id)
    out = sim.run_episode(prompt=tv["prompt"], run_id="TEST#" + tv_id, faults=tv.get("faults", {}), audit=sim.AuditLog())
    assert out.tool_executed == tv["expect"]["tool_executed"]
    assert out.precheck_decision == tv["expect"]["precheck"]
    assert out.precheck_reason_code == tv["expect"]["precheck_reason"]


def test_audit_log_schema_and_required_fields(tmp_path: Path):
    log_path = tmp_path / "audit.jsonl"
    ok, fails = sim.run_simulation(log_path=str(log_path))
    assert ok, f"simulation failed: {fails}"

    required = set(sim.PolicyPack.REQUIRED_LOG_FIELDS)
    for ln in log_path.read_text(encoding="utf-8").splitlines():
        rec = json.loads(ln)
        missing = required.difference(rec.keys())
        assert not missing, f"missing fields: {missing}"
        assert rec["policy_version"] == sim.PolicyPack.POLICY_VERSION
        assert rec["config_hash"].startswith("sha256:")


def test_tool_proxy_blocks_pii_sources_even_if_capability_is_tampered():
    proxy = sim.ToolProxy()
    cap = {"allowed_tools": ["contacts_lookup"]}  # tampered
    assert proxy.execute("contacts_lookup", capability=cap) is False
    assert proxy.execute("unknown_tool_xyz", capability={"allowed_tools": ["unknown_tool_xyz"]}) is False
