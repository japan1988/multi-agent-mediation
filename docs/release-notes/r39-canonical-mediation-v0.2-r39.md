# R39 Canonical Mediation Simulator v0.2-r39

**Status:** Release candidate frozen for human review  
**Date:** 2026-08-18

## Summary

This release candidate freezes the consolidation-first R39 mediation simulator after the final cleanup and validation pass.

The runtime is reduced to four canonical responsibilities:

- `CANONICAL_AUTHORITY_CONTRACT`
- `CANONICAL_SIM_PROOF`
- `CANONICAL_SIM_TRANSACTION`
- `DURABLE_CANONICAL_SIM_LOG`

The release keeps explicit USER decision authority, semantic/role continuity, fail-closed behavior, and reconstructible durable history as purpose invariants.

## Release identity

- File: `territory_mediation_sim_v0_2_hardened_r39.py`
- Model ID: `HM-R39-CANONICAL-MEDIATION-V1`
- Simulator version: `0.2-r39`
- Canonical schema: `R39_CLEANUP_CANONICAL_SIM_V1`
- Schema changed for release: **No**
- Frozen source SHA-256: `092386e1275e4b1163d8e4be9007e19e450f25f67af3be4e78b471ebd5d4d2b6`

## Final validation

The exact frozen release-candidate file was evaluated in this order:

1. normal simulation
2. consistency / non-contradiction / purpose-means checks
3. adversarial review

Results:

- Normal simulation: `ALLOW`
- Behavioral contracts: `30/30 PASS`
- Consistency / non-contradiction / purpose-means: `ALLOW`
- Adversarial review: `ALLOW`
- Recovery: `ALLOW`
- Exact state recovery: `true`
- Cleanup findings: none

Validation evidence is recorded in:

`docs/release-validation/r39-v0.2-r39-three-stage-validation.json`

The release freeze record is:

`docs/release-freeze/r39-v0.2-r39-freeze-manifest.json`

## Consolidated behavior

This release candidate includes the reviewed cleanup work that:

- binds canonical record issuance to the canonical authority contract and exact authorized issuance path;
- removes caller-supplied actor authority from canonical record issuance;
- validates canonical payload shape before append and during full-log validation;
- references canonical transaction facts across stages rather than copying them;
- merges stored proof state into minimal `TX_PREPARED` state while retaining proof verification as a distinct responsibility;
- derives the prepared-proof semantic digest from canonical `TX_PREPARED` content;
- preserves `previous_proof_hash` as the semantic-continuity link, separate from durable-log ordering;
- ensures invalid evidence cannot leave a durable `TX_PREPARED` record;
- restricts `TX_ABORTED` to the finalization failure path rather than exposing a separate abort authority;
- removes duplicated `AUTH_REQUEST.transaction_id`, unused `intent_hash`, and the unused `validate_candidate()` path.

## Adversarial boundaries checked

The final adversarial pass confirmed fail-closed handling for the reviewed simulator boundary, including:

- direct canonical-record forgery attempts;
- direct independent abort attempts;
- invalid evidence before `TX_PREPARED` append;
- missing or extra canonical payload fields;
- rehashed actor-role mismatch;
- semantic-chain tampering;
- legacy transaction-fact injection into `TX_PREPARED`;
- commit-log append failure without partial state change.

These checks are simulator evidence, not a production security certification.

## Non-goals

This release does not claim or implement:

- TPM, HSM, or secure-enclave emulation;
- OS-principal isolation guarantees;
- external monotonic rollback protection;
- real-world autonomous execution;
- production trust-infrastructure guarantees.

The code remains a local research and educational simulator.

## Release boundary

This release candidate does not authorize automatic merge, automatic deployment, or automatic tagging.

Final merge remains a Human Owner decision after pull-request review. Tagging is manual after merge.

---

# R39 Canonical Mediation Simulator v0.2-r39 — 日本語

**状態:** 人による最終確認用Release Candidateとして固定  
**日付:** 2026-08-18

## 概要

このRelease Candidateは、R39調停シミュレーターについて、重複責務の統合を優先したCleanupと最終検証を完了した時点のコードを固定するものです。

RuntimeのCanonical責務は次の4つです。

- `CANONICAL_AUTHORITY_CONTRACT`
- `CANONICAL_SIM_PROOF`
- `CANONICAL_SIM_TRANSACTION`
- `DURABLE_CANONICAL_SIM_LOG`

目的不変条件として、明示的なUSER決定権、意味/役割の連続性、fail-closed、耐久ログからの再構築可能性を維持します。

## Release識別情報

- ファイル: `territory_mediation_sim_v0_2_hardened_r39.py`
- Model ID: `HM-R39-CANONICAL-MEDIATION-V1`
- Simulator version: `0.2-r39`
- Canonical schema: `R39_CLEANUP_CANONICAL_SIM_V1`
- ReleaseのためのSchema変更: **なし**
- 固定ソースSHA-256: `092386e1275e4b1163d8e4be9007e19e450f25f67af3be4e78b471ebd5d4d2b6`

## 最終検証

完全に同一の固定Release Candidateファイルに対して、次の順番で検証しました。

1. 通常シミュレーション
2. 整合性 / 矛盾 / 目的手段チェック
3. 敵対的レビュー

結果:

- 通常シミュレーション: `ALLOW`
- Behavioral Contracts: `30/30 PASS`
- 整合性 / 矛盾 / 目的手段: `ALLOW`
- 敵対的レビュー: `ALLOW`
- Recovery: `ALLOW`
- State Recovery Exact: `true`
- Cleanup findings: なし

検証Evidence:

`docs/release-validation/r39-v0.2-r39-three-stage-validation.json`

Freeze Manifest:

`docs/release-freeze/r39-v0.2-r39-freeze-manifest.json`

## 統合された設計

このRelease Candidateでは、確認済みのCleanupとして次を反映しています。

- Canonical Recordの発行をCanonical Authority Contractと正規の発行経路へBinding;
- caller supplied `actor_role`をAuthorityとして扱わない;
- Canonical payload shapeをappend前とfull-log validationの双方で検証;
- Transaction factsを段階ごとにコピーせずCanonical Record参照で解決;
- 独立Proof保存オブジェクトを削除し、最小Proof Stateを`TX_PREPARED`へ統合しつつ、Proof verification責務は維持;
- prepared proof semantic digestをCanonical `TX_PREPARED`内容から導出;
- `previous_proof_hash`をLog orderingとは別のSemantic continuity linkとして維持;
- 不正EvidenceではDurable `TX_PREPARED`を残さない;
- `TX_ABORTED`を独立Abort Authorityにせずfinalize失敗時の内部Terminal outcomeに限定;
- 重複した`AUTH_REQUEST.transaction_id`、unused `intent_hash`、unused `validate_candidate()`を削除。

## 敵対的レビューで確認した境界

最終レビューでは、Simulatorの対象範囲内で次のFail-closedを確認しています。

- Canonical Recordの直接偽造;
- 独立Abortの直接実行;
- `TX_PREPARED`前の不正Evidence;
- Canonical payloadのmissing / extra field;
- actor role改ざん後のHash再計算;
- Semantic chain改ざん;
- 旧形式Transaction factの`TX_PREPARED`注入;
- Commit log append失敗時にStateを部分変更しないAtomicity。

これらはSimulator上の検証Evidenceであり、本番Security Certificationではありません。

## Non-goals

このReleaseでは次を主張・実装しません。

- TPM/HSM/Secure Enclaveのエミュレーション;
- OS principal isolation保証;
- 外部monotonic rollback protection;
- 現実環境での自律実行;
- Production trust infrastructure保証。

本コードはローカルの研究・教育用Simulatorです。

## Release境界

このRelease Candidateは自動Merge、自動Deploy、自動Tagを許可しません。

最終MergeはPull Request確認後のHuman Owner判断です。TagはMerge後に手動で実施します。
