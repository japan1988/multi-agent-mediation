========================
FILE: README.md  (FULL REPLACE)
========================
# 📘 Maestro Orchestrator — Multi-Agent Orchestration Framework

Maestro Orchestrator is a multi-agent mediation / orchestration simulator focused on **fail-closed guardrails**, **audit logs**, and **HITL escalation**.

This repository is designed for experimentation: it helps you model how an “orchestrator” can route tasks, validate outputs, and stop or escalate when safety or consistency is unclear.

---

## 🎯 Purpose

- Provide a minimal but concrete orchestration pattern:
  - **RUN** when the request is safe and unambiguous
  - **STOP** when it is unsafe
  - **HITL** (Human-in-the-Loop) when it is ambiguous or requires an explicit human decision
- Keep outcomes reproducible via **JSONL audit logs**
- Offer testable entrypoints so CI can verify “fail-closed” behavior

---

## 🧱 Structure (high-level)

| Layer | Role | Responsibility |
|---|---|---|
| Agent Layer | Execution | task processing (proposal/generation/verification) |
| Supervisor Layer | Control | routing, consistency checks, STOP, HITL |

---

## 🔬 Context Flow (unchanged image path)

<p align="center">
  <img src="docs/sentiment_context_flow.png" width="720" alt="Context Flow Diagram">
</p>

### Flow (description updated)

1. **Perception** — decompose input into executable units (tasking)
2. **Context** — extract constraints / assumptions / risk factors (guardrail evidence)
3. **Action** — dispatch to agents, validate outputs, then branch (RUN / STOP / HITL)

> Safety is prioritized at every stage: unsafe or ambiguous cases are stopped or escalated.

---

## ⚙️ Quickstart

### 1) Install dependencies

```bash
python -m pip install -r requirements.txt
````

### 2) Run tests

```bash
pytest -q
```

### 3) Run the minimal orchestrator entrypoint (recommended)

This command always writes a JSONL log file.

```bash
python run_orchestrator_min.py --prompt "hello" --run-id DEMO
```

Log output (default):

* `logs/orchestrator_min.jsonl`

### 4) Run an orchestrator experiment (examples)

```bash
python kage_orchestrator_diverse_v1.py
# or
python ai_mediation_all_in_one.py
```

---

## 🧪 Testing

* CI should pass via GitHub Actions.
* Locally:

```bash
pytest -q
```

---

## 🛡️ Safety scope (important)

This repository provides an **experimental, fail-closed orchestration pattern** (RUN / STOP / HITL) and audit logging.

It does **not** guarantee safety for real-world deployment. You are responsible for validation, threat modeling, and operational controls (rate limits, sandboxing, tool permissioning, red-teaming, monitoring, etc.).

---

## 📜 License

Apache License 2.0. See `LICENSE` for details.

========================
FILE: run_orchestrator_min.py  (NEW)
====================================

# -*- coding: utf-8 -*-

"""
run_orchestrator_min.py

Minimal orchestrator entrypoint (RUN / STOP / HITL) with fail-closed behavior and JSONL audit logging.

Goals:

* Provide a single, stable CLI entrypoint.
* Always write a JSONL log line (even on errors).
* Demonstrate a minimal HITL gate (ambiguous/safety-sensitive prompts -> HITL).
* Keep dependencies in the Python standard library only.

Usage:
python run_orchestrator_min.py --prompt "hello" --run-id DEMO

Default log:
logs/orchestrator_min.jsonl

Exit codes:
0: RUN
1: STOP (blocked or fail-closed)
2: HITL (human decision required)
"""

from **future** import annotations

import argparse
import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Literal, Optional

Decision = Literal["RUN", "STOP", "HITL"]

# ---- Minimal patterns (intentionally conservative; fail-closed) ----

STOP_PATTERNS = [
# explicit wrongdoing / doxxing / credential theft cues
r"\bdoxx\b",
r"\bpassword\b",
r"\bsteal\b",
r"\bcredit\s*card\b",
r"\bssn\b",
r"\bsocial\s*security\b",
r"\bapi\s*key\b",
r"\bsecret\b",
]

HITL_PATTERNS = [
# ambiguous “might be sensitive” cues (HITL instead of guessing)
r"\bpersonal\s*data\b",
r"\bprivate\s*info\b",
r"\baddress\b",
r"\bphone\b",
r"\bemail\b",
r"\bidentify\b",
r"\bfind\s*someone\b",
]

def _utc_now_iso() -> str:
return datetime.now(timezone.utc).isoformat()

def _hash_text(text: str) -> str:
return sha256(text.encode("utf-8")).hexdigest()

def _match_any(patterns: list[str], text: str) -> Optional[str]:
for pat in patterns:
if re.search(pat, text, flags=re.IGNORECASE):
return pat
return None

@dataclass
class AuditEvent:
ts_utc: str
run_id: str
prompt_hash: str
decision: Decision
reason_code: str
reason_detail: str
log_version: str = "orchestrator_min.v1"

def decide(prompt: str) -> tuple[Decision, str, str]:
"""
Minimal decision policy:
- STOP if clearly unsafe
- HITL if ambiguous / potentially sensitive
- RUN otherwise
Fail-closed principle: when unsure -> HITL (not RUN).
"""
stop_hit = _match_any(STOP_PATTERNS, prompt)
if stop_hit:
return ("STOP", "STOP_PATTERN", f"matched={stop_hit}")

```
hitl_hit = _match_any(HITL_PATTERNS, prompt)
if hitl_hit:
    return ("HITL", "HITL_PATTERN", f"matched={hitl_hit}")

return ("RUN", "OK", "safe_unambiguous")
```

def write_jsonl(path: Path, event: AuditEvent) -> None:
path.parent.mkdir(parents=True, exist_ok=True)
with path.open("a", encoding="utf-8") as f:
f.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")

def main(argv: Optional[list[str]] = None) -> int:
p = argparse.ArgumentParser()
p.add_argument("--prompt", required=True, help="Input prompt for the orchestrator gate")
p.add_argument("--run-id", required=True, help="Run identifier for audit correlation")
p.add_argument(
"--log-path",
default="logs/orchestrator_min.jsonl",
help="JSONL log path (default: logs/orchestrator_min.jsonl)",
)
args = p.parse_args(argv)

```
prompt: str = args.prompt
run_id: str = args.run_id
log_path = Path(args.log_path)

# Fail-closed: any exception still emits a log line.
try:
    decision, reason_code, reason_detail = decide(prompt)
    event = AuditEvent(
        ts_utc=_utc_now_iso(),
        run_id=run_id,
        prompt_hash=_hash_text(prompt),
        decision=decision,
        reason_code=reason_code,
        reason_detail=reason_detail,
    )
    write_jsonl(log_path, event)

    if decision == "RUN":
        print("RUN: accepted (minimal orchestrator).")
        return 0
    if decision == "HITL":
        print("HITL: human decision required. See audit log for details.")
        return 2

    print("STOP: blocked by safety gate. See audit log for details.")
    return 1

except Exception as e:  # noqa: BLE001
    event = AuditEvent(
        ts_utc=_utc_now_iso(),
        run_id=run_id,
        prompt_hash=_hash_text(prompt),
        decision="STOP",
        reason_code="EXCEPTION_FAIL_CLOSED",
        reason_detail=f"{type(e).__name__}: {e}",
    )
    try:
        write_jsonl(log_path, event)
    except Exception:
        # Last resort: do not raise.
        pass
    print("STOP: fail-closed due to exception. See audit log if available.")
    return 1
```

if **name** == "**main**":
raise SystemExit(main())

========================
FILE: tests/test_run_orchestrator_min.py  (NEW)
===============================================

# -*- coding: utf-8 -*-

from **future** import annotations

import json
import subprocess
import sys
from pathlib import Path

def _repo_root() -> Path:
# tests/ 配下から repo root を推定
return Path(**file**).resolve().parents[1]

def _script_path() -> Path:
return _repo_root() / "run_orchestrator_min.py"

def _read_jsonl(path: Path) -> list[dict]:
lines = path.read_text(encoding="utf-8").splitlines()
return [json.loads(x) for x in lines if x.strip()]

def test_min_entrypoint_writes_jsonl_and_runs(tmp_path: Path) -> None:
# README と同じ「デフォルトログパス(相対)」を使うため、cwd を tmp にして汚さない
cmd = [
sys.executable,
str(_script_path()),
"--prompt",
"hello",
"--run-id",
"DEMO",
]
r = subprocess.run(cmd, cwd=tmp_path, capture_output=True, text=True)
assert r.returncode == 0, r.stdout + "\n" + r.stderr

```
log_path = tmp_path / "logs" / "orchestrator_min.jsonl"
assert log_path.exists()

rows = _read_jsonl(log_path)
assert len(rows) >= 1
last = rows[-1]

assert last["run_id"] == "DEMO"
assert last["decision"] == "RUN"
assert "prompt_hash" in last and isinstance(last["prompt_hash"], str) and len(last["prompt_hash"]) == 64
```

def test_min_entrypoint_hitl_exit_code_and_logs(tmp_path: Path) -> None:
cmd = [
sys.executable,
str(_script_path()),
"--prompt",
"please identify someone by email address",
"--run-id",
"DEMO_HITL",
]
r = subprocess.run(cmd, cwd=tmp_path, capture_output=True, text=True)
assert r.returncode == 2, r.stdout + "\n" + r.stderr

```
log_path = tmp_path / "logs" / "orchestrator_min.jsonl"
rows = _read_jsonl(log_path)
last = rows[-1]
assert last["run_id"] == "DEMO_HITL"
assert last["decision"] == "HITL"
```

========================
OPTIONAL: .gitignore  (APPEND)
==============================

# runtime logs

logs/

```

