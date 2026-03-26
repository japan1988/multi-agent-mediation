## 結論

この断片は**そのままだと壊れています**。
主な原因は **インデント崩れ** なので、下の形に直してください。

## 理由

壊れている点は主に3つです。

1. `decider_set = ...` の行頭に余計なスペースがある
   → トップレベルで `IndentationError` の原因になります。

2. `def test_required_reason_codes_exist(...)` の中身が字下げされていない
   → 関数本体として解釈されません。

3. `def test_sample_rows_keep_core_invariants(...)` の中身も字下げされていない
   → 同じく構文エラーになります。

## 補足

そのまま置き換えるなら、こうです。

```python
def test_codebook_roundtrip_and_sets(codebook: Dict[str, Any]) -> None:
    layer_set = _layer_set_from_codebook(codebook)
    decision_set = _decision_set_from_codebook(codebook)
    decider_set = _decider_set_from_codebook(codebook)

    assert "relativity_gate" in layer_set
    assert "ethics_gate" in layer_set
    assert "acc_gate" in layer_set

    assert "RUN" in decision_set
    assert "PAUSE_FOR_HITL" in decision_set
    assert "STOPPED" in decision_set

    assert "SYSTEM" in decider_set
    assert "USER" in decider_set

    packed = _pack_header(
        codebook,
        layer="relativity_gate",
        decision="PAUSE_FOR_HITL",
        sealed=False,
        overrideable=True,
        final_decider="SYSTEM",
        reason_code="REL_BOUNDARY_UNSTABLE",
    )
    decoded = _unpack_header(codebook, packed)

    assert decoded["layer"] == "relativity_gate"
    assert decoded["decision"] == "PAUSE_FOR_HITL"
    assert decoded["sealed"] is False
    assert decoded["overrideable"] is True
    assert decoded["final_decider"] == "SYSTEM"
    assert decoded["reason_code"] == "REL_BOUNDARY_UNSTABLE"


def test_required_reason_codes_exist(codebook: Dict[str, Any]) -> None:
    rc_set = _rc_set_from_codebook(codebook)
    required = {
        "REL_BOUNDARY_UNSTABLE",
        "REL_REF_MISSING",
        "REL_SYMMETRY_BREAK",
    }
    missing = sorted(required - rc_set)
    assert not missing, f"Required reason codes missing from codebook: {missing}"


def test_sample_rows_keep_core_invariants() -> None:
    rows = [
        {
            "layer": "relativity_gate",
            "decision": "PAUSE_FOR_HITL",
            "sealed": False,
            "overrideable": True,
            "final_decider": "SYSTEM",
            "reason_code": "REL_BOUNDARY_UNSTABLE",
        },
        {
            "layer": "ethics_gate",
            "decision": "STOPPED",
            "sealed": True,
            "overrideable": False,
            "final_decider": "SYSTEM",
            "reason_code": "SEALED_BY_ETHICS",
        },
    ]
    _assert_rows_keep_core_invariants(rows)
```

補足で1点あります。
最初のブロックは関数外に置くより、**今のように `test_codebook_roundtrip_and_sets(...)` として1つのテスト関数にまとめる方が安全**です。
**確実性：高い／日付：2026-03-26**
