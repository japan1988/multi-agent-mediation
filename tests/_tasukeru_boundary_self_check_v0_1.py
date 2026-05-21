

# Artifact groups that should stay aligned across PR Draft, upload, and ARL.
# The tuple is: (logical name, file name in artifact zip, Python path symbol).
BOUNDARY_ARTIFACTS: tuple[tuple[str, str, str], ...] = (
    ("3D-VAF markdown", "tasukeru_3d_vulnerability_review.md", "three_d_vaf_md_path"),
    ("3D-VAF json", "tasukeru_3d_vulnerability_review.json", "three_d_vaf_json_path"),
    ("SIS markdown", "tasukeru_safety_impact_simulation.md", "sis_md_path"),
    ("SIS json", "tasukeru_safety_impact_simulation.json", "sis_json_path"),
    ("3D-TBRL markdown", "tasukeru_trust_boundary_risk_report.md", "trust_boundary_risk_md_path"),
    ("3D-TBRL json", "tasukeru_trust_boundary_risk_report.json", "trust_boundary_risk_json_path"),
    ("3D-TBRL verify", "tasukeru_trust_boundary_risk_verify.json", "trust_boundary_risk_verify_path"),
    ("3D-DAC markdown", "tasukeru_dimension_dependency_report.md", "dimension_dependency_md_path"),
    ("3D-DAC json", "tasukeru_dimension_dependency_report.json", "dimension_dependency_json_path"),
    ("3D-DAC verify", "tasukeru_dimension_dependency_verify.json", "dimension_dependency_verify_path"),
    ("PEL markdown", "tasukeru_probabilistic_escalation_report.md", "probabilistic_escalation_md_path"),
    ("PEL json", "tasukeru_probabilistic_escalation_report.json", "probabilistic_escalation_json_path"),
    ("PEL verify", "tasukeru_probabilistic_escalation_verify.json", "probabilistic_escalation_verify_path"),
    ("PR Draft markdown", "tasukeru_pr_draft.md", "pr_draft_md_path"),
    ("PR Draft json", "tasukeru_pr_draft.json", "pr_draft_json_path"),
    ("PR Draft verify", "tasukeru_pr_draft_verify.json", "pr_draft_verify_path"),
    ("Clean Run markdown", "tasukeru_clean_run_draft.md", "clean_run_draft_md_path"),
    ("Clean Run json", "tasukeru_clean_run_draft.json", "clean_run_draft_json_path"),
    ("Clean Run verify", "tasukeru_clean_run_draft_verify.json", "clean_run_draft_verify_path"),
)


CORE_INTEGRITY_ARTIFACTS: tuple[tuple[str, str, str], ...] = (
    ("Finding Validation markdown", "tasukeru_finding_validation_report.md", "finding_validation_report_md_path"),
    ("Finding Validation json", "tasukeru_finding_validation_report.json", "finding_validation_report_json_path"),
    ("Finding Validation verify", "tasukeru_finding_validation_verify.json", "finding_validation_verify_path"),
    ("Self Definition effective", "tasukeru_self_definition_effective.json", "self_definition_effective_path"),
    ("Self Definition chain", "tasukeru_self_definition_chain.jsonl", "self_definition_chain_path"),
    ("Self Definition verify", "tasukeru_self_definition_verify.json", "self_definition_verify_path"),
)


def test_workflow_yaml_and_embedded_python_are_parseable(workflow_text: str) -> None:
    yaml = pytest.importorskip("yaml")
    yaml.safe_load(workflow_text)

    scripts = _embedded_python_scripts(workflow_text)
    assert scripts, "no embedded Python heredocs found"
    labels = [label for label, _script in scripts]
    assert any("POST_SCRIPT" in label for label in labels), "POST_SCRIPT is not covered by Python compile checks"
    for index, (label, script) in enumerate(scripts):
        compile(script, f"tasukeru_embedded_python_{index}_{label}.py", "exec")


def test_changed_file_boundary_is_split_between_actual_and_relevant(workflow_text: str) -> None:
    assert "changed-files-all.txt" in workflow_text, "actual PR diff list is not recorded"
    assert "tasukeru_changed_files.txt" in workflow_text, "relevant changed-file list is not recorded"
    assert "relevant_changed_files" in workflow_text, "PR Draft does not expose relevant_changed_files separately"
    assert "changed_files\": \"tasukeru_logs/changed-files-all.txt" in workflow_text
    assert "relevant_changed_files\": \"tasukeru_changed_files.txt" in workflow_text


def test_pip_audit_outputs_are_aggregated_before_parsing(workflow_text: str) -> None:
    assert "Aggregate per-requirements pip-audit reports" in workflow_text
    assert "glob(\"pip-audit-*.json\")" in workflow_text
    assert "log_dir.joinpath(\"pip-audit.json\").write_text" in workflow_text
    assert "pip_raw = read_json(log_dir / \"pip-audit.json\", {})" in workflow_text


def test_pr_draft_generated_artifact_list_covers_boundary_layers(workflow_text: str) -> None:
    block = _pr_draft_artifact_block(workflow_text)
    missing = [f"{logical}: {symbol}" for logical, _filename, symbol in BOUNDARY_ARTIFACTS if symbol not in block]
    assert not missing, "PR Draft generated_artifacts is missing: " + ", ".join(missing)


def test_upload_artifacts_cover_boundary_layers(workflow_text: str) -> None:
    block = _upload_block(workflow_text)
    required_files = [filename for _logical, filename, _symbol in BOUNDARY_ARTIFACTS + CORE_INTEGRITY_ARTIFACTS]
    missing = [filename for filename in required_files if filename not in block]
    assert not missing, "upload-artifact path list is missing: " + ", ".join(missing)


def test_arl_artifact_integrity_covers_boundary_layers_without_self_reference(workflow_text: str) -> None:
    block = _arl_artifact_block(workflow_text)
    required_symbols = [symbol for _logical, _filename, symbol in BOUNDARY_ARTIFACTS + CORE_INTEGRITY_ARTIFACTS]
    missing = [symbol for symbol in required_symbols if symbol not in block]
    assert not missing, "ARL artifact_paths is missing: " + ", ".join(missing)

    # RCV is generated after ARL and checks ARL; hashing RCV inside the same ARL
    # pass would create a stale/self-referential boundary.
    assert "result_consistency_report" not in block
    assert "result_consistency_verify" not in block


def test_rcv_and_clean_run_observe_pr_draft_boundaries(workflow_text: str) -> None:
    assert "pr_draft_verified_if_generated" in workflow_text
    assert "pr_draft_changed_files_available_if_pr" in workflow_text
    assert "# Rebuild Clean Run after PR Draft" in workflow_text
    assert "field=\"tbrl.entry_count\"" in workflow_text
    assert "RESULT_TBRL_ENTRY_COUNT_MISMATCH" in workflow_text


def test_public_comment_uses_matching_headline_for_failure_type(workflow_text: str) -> None:
    comment_block = _section(workflow_text, "comment_body = ", "api_root = ")
    assert "headline," in comment_block
    assert '"ARL verification failed."' not in comment_block


def test_report_only_and_no_auto_control_invariants_are_preserved(workflow_text: str) -> None:
    required_false_flags = (
        "auto_branch_allowed",
        "auto_pr_creation_allowed",
        "auto_commit_allowed",
        "auto_push_allowed",
        "autofix_allowed",
        "auto_merge_allowed",
        "auto_control_executed",
        "changes_existing_decisions",
    )
    for flag in required_false_flags:
        assert flag in workflow_text, f"missing automation boundary flag: {flag}"

    assert "No branch, PR, commit, push, auto-fix, or auto-merge was performed." in workflow_text
    assert "defensive_advice_only" in workflow_text
    assert "offensive_details_allowed" in workflow_text
    assert "exploit_steps_allowed" in workflow_text
    assert "payloads_allowed" in workflow_text
    assert "attack_chain_allowed" in workflow_text


def test_boundary_artifact_matrix_stress_has_no_missing_edges(workflow_text: str) -> None:
    """Deterministic stress matrix for Tasukeru's own artifact boundaries.

    Every required artifact must be visible in:
      1. PR Draft generated_artifacts,
      2. Upload artifact paths,
      3. ARL artifact_integrity paths.

    This catches the exact class of regressions where a new layer is generated
    but not surfaced, uploaded, or hash-recorded.
    """
    pr_draft_block = _pr_draft_artifact_block(workflow_text)
    upload_block = _upload_block(workflow_text)
    arl_block = _arl_artifact_block(workflow_text)

    failures: list[str] = []
    for logical, filename, symbol in itertools.chain(BOUNDARY_ARTIFACTS, CORE_INTEGRITY_ARTIFACTS):
        checks = {
            "pr_draft": symbol in pr_draft_block,
            "upload": filename in upload_block,
            "arl": symbol in arl_block,
        }
        for edge, ok in checks.items():
            if not ok:
                failures.append(f"{logical} missing from {edge} boundary")

    assert not failures, "Boundary artifact matrix failures: " + "; ".join(failures)
