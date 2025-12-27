# tests/test_ai_doc_orchestrator_kage3_v1_2_2.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Iterable

# Prefer v1.2.2; fallback to v1.2.1 for transition.
try:
    import ai_doc_orchestrator_kage3_v1_2_2 as sim  # type: ignore
except Exception:  # pragma: no cover
    import ai_doc_orchestrator_kage3_v1_2_1 as sim  # type: ignore


# -----------------------------
# Constants / Regex
# -----------------------------
EMAIL_RE = sim.EMAIL_RE  # prefer orchestrator canonical regex


# -----------------------------
# JSONL helpers
# -----------------------------
def read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    if not path.exists():
        raise AssertionError(f"audit log not found: {path}")
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def filter_rows_by_run_id(rows: list[dict], run_id: str) -> list[dict]:
    """
    Strong isolation. If run_id exists in schema, filter by it.
    If not present, caller must ensure audit file is per-run (recommended).
    """
    if not rows:
        return rows
    if "run_id" not in rows[0]:
        return rows
    return [r for r in rows if r.get("run_id") == run_id]


def _sort_rows_stably(rows: list[dict]) -> list[dict]:
    """
    Stabilize event ordering:
    - Prefer 'ts' if present (ISO-8601 string in this simulator).
    - Otherwise keep original order (fail closed / minimal assumptions).
    """
    if not rows:
        return rows
    if "ts" not in rows[0]:
        return rows
    # ISO strings sort lexicographically in chronological order given same format
    return sorted(rows, key=lambda r: (r.get("ts", ""), r.get("event", ""), r.get("layer", "")))


def events_by_task(rows: list[dict]) -> dict[str, list[dict]]:
    """
    Group rows by task_id. Keep full row objects so we can filter by run_id, etc.
    Also sort per-task rows to prevent flaky ordering if writer/buffer changes.
    """
    out: dict[str, list[dict]] = {}
    for r in rows:
        tid = r.get("task_id")
        if not tid:
            # If schema changes, fail closed to surface it early.
            raise AssertionError(f"missing task_id in audit row: {r}")
        out.setdefault(tid, []).append(r)

    # Stabilize ordering within each task
    for tid, task_rows in out.items():
        out[tid] = _sort_rows_stably(task_rows)

    return out


def events_only(task_rows: list[dict]) -> list[str]:
    return [r.get("event", "") for r in task_rows]


# -----------------------------
# Event order / contradiction checks
# -----------------------------
def assert_subsequence_order(events: list[str], must_appear_in_order: list[str]) -> None:
    """
    Ensures subsequence order: a -> b -> c (not necessarily contiguous).
    Use assert_after_last() for "after the last gate" constraints.
    """
    idx = -1
    for e in must_appear_in_order:
        try:
            idx = events.index(e, idx + 1)
        except ValueError as ex:
            raise AssertionError(f"Missing or out-of-order event={e}. events={events}") from ex


def _last_index(events: list[str], target: str) -> int:
    for i in range(len(events) - 1, -1, -1):
        if events[i] == target:
            return i
    return -1


def assert_after_last(
    events: list[str],
    anchor: str,
    must_exist_after: Iterable[str] = (),
    must_not_exist_after: Iterable[str] = (),
) -> None:
    """
    Anchor on the LAST occurrence of `anchor`, then enforce conditions after it.
    Prevents the "picked the first gate and ignored later retries" loophole.
    """
    i = _last_index(events, anchor)
    if i < 0:
        raise AssertionError(f"anchor event missing: {anchor}. events={events}")
    tail = events[i + 1 :]

    for e in must_exist_after:
        if e not in tail:
            raise AssertionError(
                f"event {e} must appear after last {anchor}, but not found. tail={tail} full={events}"
            )

    for e in must_not_exist_after:
        if e in tail:
            raise AssertionError(
                f"event {e} must NOT appear after last {anchor}, but found. tail={tail} full={events}"
            )


def assert_at_most_once(events: list[str], target: str) -> None:
    c = sum(1 for e in events if e == target)
    assert c <= 1, f"event {target} appears {c} times (must be <= 1). events={events}"


def assert_mutual_exclusive(events: list[str], a: str, b: str) -> None:
    if a in events and b in events:
        raise AssertionError(f"events must be mutually exclusive but both present: {a}, {b}. events={events}")


# -----------------------------
# Artifact email scanning (docx/xlsx/pptx aware; simulator pseudo artifacts safe)
# -----------------------------
def _scan_text_for_emails(text: str, label: str) -> None:
    m = EMAIL_RE.search(text or "")
    assert m is None, f"email detected in {label}: {m.group(0)!r}"


def _is_zip(path: Path) -> bool:
    try:
        return zipfile.is_zipfile(path)
    except Exception:
        return False


def _zip_text_members_for_office(path: Path) -> list[str]:
    """
    Conservative list of likely user-visible XML members for Office Open XML.
    If the file is a zip but doesn't match these patterns, fallback to all *.xml.
    """
    suffix = path.suffix.lower()
    members: list[str] = []

    with zipfile.ZipFile(path, "r") as zf:
        names = zf.namelist()

        if suffix == ".docx":
            for n in names:
                if n in ("word/document.xml", "word/comments.xml", "word/footnotes.xml", "word/endnotes.xml"):
                    members.append(n)
                elif n.startswith("word/header") and n.endswith(".xml"):
                    members.append(n)
                elif n.startswith("word/footer") and n.endswith(".xml"):
                    members.append(n)

        elif suffix == ".pptx":
            for n in names:
                if n.startswith("ppt/slides/slide") and n.endswith(".xml"):
                    members.append(n)
                elif n.startswith("ppt/notesSlides/notesSlide") and n.endswith(".xml"):
                    members.append(n)

        elif suffix == ".xlsx":
            for n in names:
                if n in ("xl/sharedStrings.xml", "xl/workbook.xml"):
                    members.append(n)
                elif n.startswith("xl/worksheets/sheet") and n.endswith(".xml"):
                    members.append(n)

    # Deduplicate while preserving order
    seen = set()
    out: list[str] = []
    for m in members:
        if m not in seen:
            seen.add(m)
            out.append(m)
    return out


def assert_no_emails_in_artifact(path: Path) -> None:
    """
    txt/zip (docx/xlsx/pptx) dual-mode scanner.

    - If it's a real Office zip (.docx/.xlsx/.pptx), scan key XML parts for emails.
    - If it's a "pseudo artifact" like *.docx.txt / *.xlsx.txt / *.pptx.txt (this simulator),
      treat it as plain text.
    - For any other file: try as utf-8 text.
    """
    assert path.exists(), f"artifact not found: {path}"

    name = path.name.lower()

    # Simulator artifacts: always plain text, even if name contains .docx/.xlsx/.pptx
    if name.endswith(".txt"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        _scan_text_for_emails(text, label=str(path))
        return

    # Real OOXML office files (zip)
    if _is_zip(path) and path.suffix.lower() in (".docx", ".xlsx", ".pptx"):
        with zipfile.ZipFile(path, "r") as zf:
            members = _zip_text_members_for_office(path)
            if not members:
                members = [n for n in zf.namelist() if n.endswith(".xml")]

            for member in members:
                data = zf.read(member)
                text = data.decode("utf-8", errors="ignore")
                _scan_text_for_emails(text, label=f"{path.name}:{member}")
        return

    # Fallback: treat as text
    text = path.read_text(encoding="utf-8", errors="ignore")
    _scan_text_for_emails(text, label=str(path))


def assert_no_emails_in_logs(rows: list[dict]) -> None:
    # Logs should never contain raw emails (redaction / non-persist expected).
    blob = json.dumps(rows, ensure_ascii=False)
    _scan_text_for_emails(blob, label="audit logs")


# -----------------------------
# Per-run audit path utility (fixes cross-run contamination)
# -----------------------------
def per_run_audit_path(tmp_path: Path, run_id: str) -> Path:
    return tmp_path / "logs" / f"doc_orchestrator_{run_id}.jsonl"


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


# -----------------------------
# Tests
# -----------------------------
def test_partial_stop_only_violating_task_skipped_and_no_contradictions(tmp_path: Path) -> None:
    run_id = "TEST_PARTIAL_STOP"
    audit = per_run_audit_path(tmp_path, run_id)
    out_dir = tmp_path / "artifacts" / run_id

    _ensure_parent(audit)
    out_dir.mkdir(parents=True, exist_ok=True)

    res = sim.run_simulation(
        prompt="Create a safe summary with title and purpose.",
        run_id=run_id,
        audit_path=str(audit),
        artifact_dir=str(out_dir),
        faults={"word": {"leak_email": True}},
    )

    # Overall rule: RUN iff all tasks RUN; else HITL
    assert res.decision == "HITL"

    task_map = {t.task_id: t for t in res.tasks}
    assert task_map["task_word"].decision == "STOP"
    assert task_map["task_word"].blocked_layer == "ethics"
    assert task_map["task_excel"].decision == "RUN"
    assert task_map["task_ppt"].decision == "RUN"

    # Artifact validation by task_id (not count/order)
    assert set(res.artifacts_written_task_ids) == {"task_excel", "task_ppt"}
    assert task_map["task_excel"].artifact_path is not None
    assert task_map["task_ppt"].artifact_path is not None
    assert task_map["task_word"].artifact_path is None

    rows = read_jsonl(audit)
    rows = filter_rows_by_run_id(rows, run_id)
    by = events_by_task(rows)

    # task_word: ensure last ETHICS gate ends in SKIPPED and never WRITTEN after that
    ev_word = events_only(by["task_word"])
    assert_subsequence_order(
        ev_word, ["TASK_ASSIGNED", "GATE_MEANING", "AGENT_OUTPUT", "GATE_CONSISTENCY", "GATE_ETHICS"]
    )
    assert_after_last(
        ev_word, "GATE_ETHICS", must_exist_after=["ARTIFACT_SKIPPED"], must_not_exist_after=["ARTIFACT_WRITTEN"]
    )
    assert_mutual_exclusive(ev_word, "ARTIFACT_WRITTEN", "ARTIFACT_SKIPPED")
    assert_at_most_once(ev_word, "ARTIFACT_WRITTEN")

    # tasks that wrote artifacts: ensure WRITTEN occurs after last ETHICS gate, never SKIPPED after that
    for tid in ("task_excel", "task_ppt"):
        ev = events_only(by[tid])
        assert_subsequence_order(
            ev, ["TASK_ASSIGNED", "GATE_MEANING", "AGENT_OUTPUT", "GATE_CONSISTENCY", "GATE_ETHICS"]
        )
        assert_after_last(
            ev, "GATE_ETHICS", must_exist_after=["ARTIFACT_WRITTEN"], must_not_exist_after=["ARTIFACT_SKIPPED"]
        )
        assert_mutual_exclusive(ev, "ARTIFACT_WRITTEN", "ARTIFACT_SKIPPED")
        assert_at_most_once(ev, "ARTIFACT_WRITTEN")

    # No emails in logs and in written artifacts
    assert_no_emails_in_logs(rows)
    assert_no_emails_in_artifact(Path(task_map["task_excel"].artifact_path))
    assert_no_emails_in_artifact(Path(task_map["task_ppt"].artifact_path))


def test_meaning_local_hitl_only_word(tmp_path: Path) -> None:
    run_id = "TEST_MEANING_LOCAL_ONLY_WORD"
    audit = per_run_audit_path(tmp_path, run_id)
    out_dir = tmp_path / "artifacts" / run_id

    _ensure_parent(audit)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Ambiguous prompt, but includes Excel+PPT kind tokens; no Word tokens.
    # Expect: Word HITL (meaning), Excel+PPT RUN.
    res = sim.run_simulation(
        prompt="適当にいい感じに、Excelの列は Item, Owner, Status で表。スライドは3枚で箇条書き。",
        run_id=run_id,
        audit_path=str(audit),
        artifact_dir=str(out_dir),
        faults={},
    )

    assert res.decision == "HITL"

    task_map = {t.task_id: t for t in res.tasks}
    assert task_map["task_excel"].decision == "RUN"
    assert task_map["task_ppt"].decision == "RUN"
    assert task_map["task_word"].decision == "HITL"
    assert task_map["task_word"].blocked_layer == "meaning"

    assert set(res.artifacts_written_task_ids) == {"task_excel", "task_ppt"}
    assert task_map["task_word"].artifact_path is None

    rows = read_jsonl(audit)
    rows = filter_rows_by_run_id(rows, run_id)
    by = events_by_task(rows)

    ev_word = events_only(by["task_word"])
    # Meaning HITL should skip artifact, and MUST NOT write.
    assert_subsequence_order(ev_word, ["TASK_ASSIGNED", "GATE_MEANING"])
    assert_after_last(
        ev_word, "GATE_MEANING", must_exist_after=["ARTIFACT_SKIPPED"], must_not_exist_after=["ARTIFACT_WRITTEN"]
    )
    assert_mutual_exclusive(ev_word, "ARTIFACT_WRITTEN", "ARTIFACT_SKIPPED")

    assert_no_emails_in_logs(rows)

    # Defense-in-depth: scan produced artifacts for emails
    assert_no_emails_in_artifact(Path(task_map["task_excel"].artifact_path))
    assert_no_emails_in_artifact(Path(task_map["task_ppt"].artifact_path))


def test_consistency_mismatch_requests_regen_and_skips_only_that_task(tmp_path: Path) -> None:
    run_id = "TEST_CONSISTENCY_REGEN_REQUESTED"
    audit = per_run_audit_path(tmp_path, run_id)
    out_dir = tmp_path / "artifacts" / run_id

    _ensure_parent(audit)
    out_dir.mkdir(parents=True, exist_ok=True)

    res = sim.run_simulation(
        prompt="Create a safe set: Excel columns, Word outline, PPT slides.",
        run_id=run_id,
        audit_path=str(audit),
        artifact_dir=str(out_dir),
        faults={"excel": {"break_contract": True}},
    )

    assert res.decision == "HITL"
    task_map = {t.task_id: t for t in res.tasks}

    assert task_map["task_excel"].decision == "HITL"
    assert task_map["task_excel"].blocked_layer == "consistency"
    assert task_map["task_excel"].artifact_path is None

    assert task_map["task_word"].decision == "RUN"
    assert task_map["task_ppt"].decision == "RUN"

    assert set(res.artifacts_written_task_ids) == {"task_word", "task_ppt"}

    rows = read_jsonl(audit)
    rows = filter_rows_by_run_id(rows, run_id)
    by = events_by_task(rows)

    ev_excel = events_only(by["task_excel"])
    # After the LAST consistency gate, regen is requested and artifact is skipped, and never written after.
    assert_subsequence_order(ev_excel, ["TASK_ASSIGNED", "AGENT_OUTPUT", "GATE_CONSISTENCY"])
    assert_after_last(
        ev_excel,
        "GATE_CONSISTENCY",
        must_exist_after=["REGEN_REQUESTED", "REGEN_INSTRUCTIONS", "ARTIFACT_SKIPPED"],
        must_not_exist_after=["ARTIFACT_WRITTEN"],
    )
    assert_mutual_exclusive(ev_excel, "ARTIFACT_WRITTEN", "ARTIFACT_SKIPPED")
    assert_at_most_once(ev_excel, "ARTIFACT_WRITTEN")

    assert_no_emails_in_logs(rows)

    # Scan produced artifacts too.
    assert_no_emails_in_artifact(Path(task_map["task_word"].artifact_path))
    assert_no_emails_in_artifact(Path(task_map["task_ppt"].artifact_path))


def test_overall_decision_table(tmp_path: Path) -> None:
    """
    Overall rule fixed:
      RUN iff all tasks RUN
      HITL otherwise
    """
    # Case 1: all RUN
    run_id1 = "TABLE_ALL_RUN"
    audit1 = per_run_audit_path(tmp_path, run_id1)
    out1 = tmp_path / "artifacts" / run_id1
    _ensure_parent(audit1)
    out1.mkdir(parents=True, exist_ok=True)

    res1 = sim.run_simulation(
        prompt="Excelの列は列/表で指定。Wordは見出し/章で指定。PPTはスライド3枚で指定。目的も書く。",
        run_id=run_id1,
        audit_path=str(audit1),
        artifact_dir=str(out1),
        faults={},
    )
    assert res1.decision == "RUN"

    # Case 2: STOP + RUN + RUN -> overall HITL
    run_id2 = "TABLE_STOP_RUN_RUN"
    audit2 = per_run_audit_path(tmp_path, run_id2)
    out2 = tmp_path / "artifacts" / run_id2
    _ensure_parent(audit2)
    out2.mkdir(parents=True, exist_ok=True)

    res2 = sim.run_simulation(
        prompt="Create safe outputs with purpose.",
        run_id=run_id2,
        audit_path=str(audit2),
        artifact_dir=str(out2),
        faults={"word": {"leak_email": True}},
    )
    assert res2.decision == "HITL"

    # Case 3: HITL + RUN + RUN -> overall HITL (Word meaning HITL only)
    run_id3 = "TABLE_HITL_RUN_RUN"
    audit3 = per_run_audit_path(tmp_path, run_id3)
    out3 = tmp_path / "artifacts" / run_id3
    _ensure_parent(audit3)
    out3.mkdir(parents=True, exist_ok=True)

    res3 = sim.run_simulation(
        prompt="適当にいい感じに、Excelの列は表。スライドは3枚。",  # no Word tokens
        run_id=run_id3,
        audit_path=str(audit3),
        artifact_dir=str(out3),
        faults={},
    )
    assert res3.decision == "HITL"

    # Case 4: STOP + STOP + RUN -> overall HITL
    run_id4 = "TABLE_STOP_STOP_RUN"
    audit4 = per_run_audit_path(tmp_path, run_id4)
    out4 = tmp_path / "artifacts" / run_id4
    _ensure_parent(audit4)
    out4.mkdir(parents=True, exist_ok=True)

    res4 = sim.run_simulation(
        prompt="Create safe outputs with purpose.",
        run_id=run_id4,
        audit_path=str(audit4),
        artifact_dir=str(out4),
        faults={"word": {"leak_email": True}, "excel": {"leak_email": True}},
    )
    assert res4.decision == "HITL"
