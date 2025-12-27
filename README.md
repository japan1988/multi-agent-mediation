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

### 4) Run orchestrator experiments (examples)

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

### Minimal pytest (README-aligned)

Create:

* `tests/test_min_entrypoint_v1.py`

```python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    # tests/ 配下から repo root を推定
    return Path(__file__).resolve().parents[1]


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

    log_path = tmp_path / "logs" / "orchestrator_min.jsonl"
    assert log_path.exists()

    rows = _read_jsonl(log_path)
    assert len(rows) >= 1

    last = rows[-1]
    assert last["run_id"] == "DEMO"
    assert last["decision"] == "RUN"
    assert "prompt_hash" in last and isinstance(last["prompt_hash"], str) and len(last["prompt_hash"]) == 64


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

    log_path = tmp_path / "logs" / "orchestrator_min.jsonl"
    assert log_path.exists()

    rows = _read_jsonl(log_path)
    assert len(rows) >= 1

    last = rows[-1]
    assert last["run_id"] == "DEMO_HITL"
    assert last["decision"] == "HITL"
```

---

## 🧾 .gitignore (append)

If you do not want runtime logs in git, append:

```gitignore
# runtime logs
logs/
```

---

## 🛡️ Safety scope (important)

This repository provides an **experimental, fail-closed orchestration pattern** (RUN / STOP / HITL) and audit logging.

It does **not** guarantee safety for real-world deployment. You are responsible for validation, threat modeling, and operational controls (rate limits, sandboxing, tool permissioning, red-teaming, monitoring, etc.).

---

## 📜 License

Licensed under the Apache License 2.0. See `LICENSE` for details. Safety scope: this repository demonstrates fail-closed behavior in experiments; it does not provide safety guarantees for real-world deployments.


