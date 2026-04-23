 assert counter_value == saved + 1

    incident_ids = set()
    for row in index_rows:
        incident_id = row.get("incident_id")
        arl_path = Path(row.get("arl_path", ""))

        assert incident_id
        assert incident_id not in incident_ids
        assert arl_path.exists()

        incident_ids.add(incident_id)

    assert st2 is not None
    assert trust2_out is trust2
    assert rows2, "Expected non-empty ARL rows for fabricated-evidence run"
    assert any(r["sealed"] is True for r in rows2), (
        "Expected at least one SEALED row"
    )
    for r in rows2:
        assert r["reason_code"] in rc_set, (
            f"Unknown reason_code in ARL: {r['reason_code']}"
        )
    _assert_rows_keep_core_invariants(rows2)


def test_v512_sealed_invariants_under_mixed_load(
    monkeypatch, tmp_path: Path
) -> None:
    """
    keep_runs=True の中規模 runs で、
    sealed は ethics / acc のみ、
    RFL は sealed にならない不変条件を確認する。
    """
    _patch_store_paths(monkeypatch, tmp_path)

    r = sim.run_simulation(
        runs=200,
        fabricate=False,
        fabricate_rate=0.15,
        seed=99,
        reset=True,
        reset_eval=True,
        keep_runs=True,
        queue_max_items=50,
        sample_runs=0,
    )

    assert "runs" in r and isinstance(r["runs"], list)
    assert len(r["runs"]) == 200

    _assert_sealed_only_ethics_or_acc(r)
