### Minimal entrypoint E2E (exit codes + logs)

```python
def test_min_entrypoint_run_exit_code_and_logs(tmp_path: Path) -> None:
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
    assert (
        "prompt_hash" in last
        and isinstance(last["prompt_hash"], str)
        and len(last["prompt_hash"]) == 64
    )


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
    rows = _read_jsonl(log_path)
    last = rows[-1]
    assert last["run_id"] == "DEMO_HITL"
    assert last["decision"] == "HITL"


