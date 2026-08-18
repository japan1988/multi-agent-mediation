# Phase 5B Validation Hardening Status

**Status:** Validation hardening in progress  
**Date:** 2026-08-17

The initial Phase 5B handoff-gate implementation is available. A post-implementation audit identified a validation gap: matching artifact hashes do not, by themselves, prove that the contents of the Phase 5A artifacts conform to the intended contract.

Until the hardening work is complete, a successful Phase 5B CLAIM must not be treated as proof that the Phase 5A artifact contents are valid.

The current hardening work is being handled one issue at a time and includes:

- strict content schemas for the four Phase 5A artifacts;
- validation of required keys, allowed keys, types, fixed values, and enumerated values;
- content-level and cross-artifact consistency checks;
- deterministic, unique stop reasons;
- irreversible rejection of invalid CLAIM attempts;
- regression and determinism testing.

This repository remains a research and educational simulator. The workflow does not call an external AI API, use an AI API key, perform billable AI processing, or automatically commit, push, merge, or deploy changes.

A follow-up release note will be published after the additional tests, regression checks, repeatability checks, and diff audit are complete.

---

# Phase 5B 検証強化の進捗状況

**状態:** 検証強化作業中  
**日付:** 2026-08-17

Phase 5B handoff gateの初期実装は利用可能ですが、実装後の監査により検証上の不足が確認されました。成果物のハッシュが一致していても、それだけではPhase 5A成果物の内容が想定した契約に適合していることを証明できません。

強化作業が完了するまでは、Phase 5BのCLAIM成功を、Phase 5A成果物の内容まで妥当であることの証明として扱わないでください。

現在、問題を混在させず、次の項目を一件ずつ検討・修正しています。

- Phase 5Aの4成果物に対する厳格な内容schema
- 必須キー、許可キー、型、固定値、列挙値の検証
- 成果物内部および成果物間の内容整合性検証
- 決定的で一意な停止理由
- 不正なCLAIM試行の不可逆な拒否
- 非回帰テストおよび決定性テスト

本リポジトリは研究・教育用シミュレーターです。workflowは外部AI APIを呼び出さず、AI APIキーを使用せず、課金可能なAI処理を行わず、変更のcommit、push、merge、deployを自動実行しません。

追加テスト、非回帰確認、反復実行による決定性確認、diff監査が完了した後、改めて続報のリリースノートを公開します。
