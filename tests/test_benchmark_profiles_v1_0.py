def test_benchmark_profile_hitl_observe_ambiguous_prompt() -> None:
    """
    HITL観測用（曖昧系fault）:
    - 曖昧（相対性）トリガー文言を含め、HITL_REQUESTED が必ず観測される前提。
    - 現仕様では、HITL は観測されるが最終結果は STOPPED 側に寄る。
    """
    runs = 90
    hitl_rate, counts = _hitl_requested_rate(
        prompt="ExcelとWordとPPTを作って。どっちがいい？おすすめは？",
        runs=runs,
        seed=7,
        p_continue=0.7,
        faults={},
        enable_runaway_seal=False,
        runaway_threshold=10,
        max_attempts_per_task=2,
    )

    run_rate, pause_rate, stop_rate = _decision_counts_to_rates(counts, runs)

    assert hitl_rate > 0.50
    assert stop_rate > 0.05
    assert pause_rate == 0.0
    assert run_rate == 0.0


def test_benchmark_profile_stress_stop_rate_1_and_no_crash_no_pii() -> None:
    """
    Stress（今回）:
    - stop_rate == 1.0
    - crash == 0
    - '@'違反 == 0
    """
    runs = 60
    faults = {
        "excel": {"break_contract": True, "leak_email": False},
        "word": {"break_contract": True, "leak_email": False},
        "ppt": {"break_contract": True, "leak_email": False},
    }

    report = mod.run_benchmark_suite(
        prompt="Excelで進捗表を作成し、Wordで要約し、PPTでスライドを作成してください。",
        runs=runs,
        seed=42,
        p_continue=1.0,
        faults=faults,
        enable_runaway_seal=True,
        runaway_threshold=2,
        max_attempts_per_task=6,
    )

    run_rate, pause_rate, stop_rate = _decision_counts_to_rates(
        report["overall_decision_counts"], runs
    )

    assert report["crashes"] == 0
    assert report["crash_free_rate"] == 1.0
    assert report["at_sign_violations"] == 0
    assert run_rate == 0.0
    assert pause_rate == 0.0
    assert stop_rate == 1.0
