# 📘 Maestro Orchestrator — マルチエージェント・オーケストレーション・フレームワーク

> English: [README.md](README.md)

<p align="center">
  <a href="https://github.com/japan1988/multi-agent-mediation/stargazers">
    <img src="https://img.shields.io/github/stars/japan1988/multi-agent-mediation?style=social" alt="GitHub Stars">
  </a>
  <a href="https://github.com/japan1988/multi-agent-mediation/issues">
    <img src="https://img.shields.io/github/issues/japan1988/multi-agent-mediation?style=flat-square" alt="Open Issues">
  </a>
  <a href="./LICENSE">
    <img src="https://img.shields.io/badge/license-Apache--2.0-brightgreen?style=flat-square" alt="License">
  </a>
  <a href="https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml">
    <img src="https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml/badge.svg?branch=main" alt="Python App CI">
  </a>
  <a href="https://github.com/japan1988/multi-agent-mediation/actions/workflows/tasukeru-analysis.yml">
    <img src="https://github.com/japan1988/multi-agent-mediation/actions/workflows/tasukeru-analysis.yml/badge.svg?branch=main" alt="Tasukeru Advisory">
  </a>
  <br/>
  <img src="https://img.shields.io/badge/python-3.10%20%7C%203.11-blue.svg?style=flat-square" alt="Python Version">
  <img src="https://img.shields.io/badge/lint-Ruff-000000.svg?style=flat-square" alt="Ruff">
  <a href="https://github.com/japan1988/multi-agent-mediation/commits/main">
    <img src="https://img.shields.io/github/last-commit/japan1988/multi-agent-mediation?style=flat-square" alt="Last Commit">
  </a>
</p>

Maestro Orchestrator は、マルチエージェント・ガバナンス、fail-closed 制御、HITL エスカレーション、チェックポイントベースの再開、改ざん検知可能なシミュレーションワークフローを扱う、研究向けのオーケストレーション・フレームワークです。

このリポジトリには複数のシミュレーター系列が含まれています。一部のファイルは KAGE 風のゲート挙動や Mediator 分離に焦点を当て、別のファイルはドキュメントタスクのバッチ実行、チェックポイント、監査整合性、artifact 検証に焦点を当てています。

## 初めて読む人向けガイド

このリポジトリを初めて読む場合は、以下の順番で確認してください。

1. まず **Safety and scope** を読んでください。
2. **Tasukeru Analysis** を読み、レビュー補助機能を理解してください。
3. **Advisory-only policy** を読み、この workflow が何をしないのかを理解してください。
4. **HITL decision support** を読み、人間によるレビューが必要になる条件を理解してください。
5. 安全境界を理解した後で、**Current simulator lines** を読んでください。

このリポジトリは、研究・教育目的のテストベンチです。  
出力は研究用 artifact であり、本番承認や安全保証ではありません。

挙動が不明確な場合は、変更を適用する前に、関連する実装とテストを一緒に確認してください。

## Safety and scope

このリポジトリは研究用プロトタイプです。

以下を目的としていません。

- 本番環境での自律的意思決定
- 監督なしの実世界制御
- 法務、医療、金融、規制に関する助言
- 実在する個人データや機密の運用データの処理
- 完全または普遍的な安全性カバー範囲の実証
- 外部への自動送信、アップロード、送信、デプロイ
- 外部副作用に対する HITL レビューの迂回

各例は、以下として読むべきです。

- 研究シミュレーション
- 教育用参考実装
- ガバナンス / 安全性テストベンチ
- fail-closed と HITL 設計例
- 監査ログとチェックポイント整合性の実験
- ローカルシミュレーション用のバッチ・オーケストレーション例

外部送信、アップロード、push、送信などの操作は、HITL ゲート下に留めるべきです。

## 責任ある利用と禁止用途

Tasukeru Analysis とシミュレーター例は、ユーザーが所有するリポジトリ、または明示的な許可を得たリポジトリを対象とした防御的レビューを目的としています。

このリポジトリやそのツールを、以下に使用しないでください。

- 無許可の脆弱性探索
- 攻撃的な偵察
- 第三者システムやコードの悪用
- 認証情報、トークン、秘密情報の収集
- 許可のないリポジトリやシステムのスキャン
- 実在する対象に対する exploit 手順の生成または検証
- アクセス制御、レート制限、セキュリティ境界の迂回
- 責任ある開示を行わない機微な findings の公開

findings は、安全性、信頼性、追跡可能性、ガバナンスを改善するために使用してください。第三者または OSS コードをレビューする場合は、そのプロジェクトのセキュリティポリシーと責任ある開示プロセスに従ってください。

## Tasukeru Analysis

Tasukeru Analysis は、防御的なリポジトリレビューのための advisory workflow です。

Tasukeru Analysis は、マルチエージェントや agentic workflow の複雑化を検査し、統治するための補助も目的としています。こうした workflow が大きくなるほど、その挙動は検査、説明、監査が難しくなります。

主に以下のようなレビュー支援上の問いを扱います。

- findings が適切な review level に分類されているか
- プロセスログと生成された出力が整合しているか
- 不確実またはリスクのあるケースが HITL に戻されるべきか
- 公開 PR コメントが過度に詳細になっていないか
- workflow が自動 fix、commit、push、merge を行わない advisory-only の範囲に留まっているか

この workflow は詳細な exploit 手順を公開せず、自律的な強制執行システムとしても動作しません。詳細な findings は、人間レビュー用に workflow artifacts / logs に残ります。

以下のような静的チェックとリポジトリ固有チェックを実行します。

- Ruff
- Bandit
- pip-audit
- Tasukeru logic review
- documentation review
- HITL decision support classification

この workflow は、すべての advisory finding を自動的な blocking failure として扱うのではなく、保守性、安全レビュー、開発者の使いやすさを改善するよう設計されています。

Tasukeru Analysis は警告を隠すことを目的としていません。代わりに、active repair candidates、review-only findings、historical-version warnings、likely noise を分離し、保守者が優先すべき項目に集中できるようにします。

Tasukeru Analysis には、result consistency audit layer も含まれます。

前段のチェックは、レビュー処理、ログ、ゲート、分類が不審または不整合に見えるかを確認します。result consistency auditor はさらに、生成された出力が記録されたプロセス状態と一致しているかを確認します。

これは、summaries、HITL review data、announcement data、ARL verification data、gate adoption data、self-definition verification data などの生成 artifact とプロセス記録を比較します。

これにより、件数、検証状態、gate adoption result、announcement claim などが基礎となる記録と一致しない場合のように、内部プロセスと公開結果が食い違うケースを検出しやすくなります。

この層は report-only です。artifact の書き換え、分類の変更、fix の適用、pull request の作成、commit、push、merge の自動実行は行いません。

## Tasukeru adversarial stress test

Tasukeru adversarial stress test は、ローカル・合成・防御的なストレステストです。

外部システムを攻撃したり、exploit を実行したり、第三者対象をスキャンしたり、pull request の作成、commit の push、fix の適用、merge の自動実行を行ったりするものではありません。

このストレステストは、malformed、contradictory、bypass-like な合成入力をローカル評価器に与え、Tasukeru 風の安全不変条件が維持されることを確認します。

典型的な合成ケースは以下です。

- malformed JSON / JSONL
- 必須監査キーの欠落
- RFL sealed-state contradictions
- safety layer 以外の sealed rows
- HITL bypass-like text
- auto-merge / auto-fix injection-like text
- duplicate JSON keys
- suspicious path-like strings
- oversized audit lines

期待される挙動は fail-closed または review-oriented です。

- automation は disabled のまま
- リスクのある合成ケースに対して unsafe `RUN` を返さない
- RFL sealed contradictions は sealed せずにエスカレーションする
- non-safety sealed rows はレビューへエスカレーションする
- HITL bypass-like input が人間レビューを迂回しない

このテストは、防御的な堅牢性と回帰カバレッジを改善するためのものです。攻撃用セキュリティツールではありません。

## Advisory-only policy

Tasukeru Analysis は advisory-only のレビュー補助です。

以下を行いません。

- branch の自動作成
- pull request の自動作成
- 変更の自動 commit
- 変更の自動 push
- fix の自動適用
- pull request の自動 merge

PR コメントを生成できるのは `HITL_REQUIRED` findings のみです。

`FIX_RECOMMENDED`、`REVIEW_RECOMMENDED`、`NOISE_CANDIDATE`、`INFO_ONLY` を含むその他の findings は、GitHub Step Summary と workflow artifacts に収集され、人間レビュー用に残されます。

Tasukeru Analysis は人間のレビュー負荷を下げるためのものであり、人間の意思決定を置き換えるものではありません。

## Human readability policy

Tasukeru Analysis は、人間が安全に読めて、レビューでき、保守できるコードを優先します。

AI や自動化ツールが処理しやすいという理由だけで、変更を良い fix として扱うべきではありません。変更によって人間の可読性、レビュー容易性、保守性が下がる可能性がある場合は、人間レビューへ戻すべきです。

## Security review output policy

Tasukeru Analysis は、防御的レビューと安全な修正方向の提示に限定されます。

公開 PR コメントには、以下を含めるべきではありません。

- exploit payloads
- 攻撃コマンド
- 攻撃的な再現手順
- 段階的な exploit 手順
- 第三者対象の exploit 詳細

セキュリティ関連 findings は、以下に焦点を当てるべきです。

- 影響を受けるファイルと行
- レビューが必要な防御上の理由
- 想定される安全上の影響
- 安全な修正方向
- 人間レビューが必要かどうか

## HITL decision support

Tasukeru Analysis は、保守者が対応すべき issue と想定される noise を分けられるよう、findings を review level に分類します。

現在の review levels:

- `HITL_REQUIRED`: merge または追加操作の前に人間レビューが必要
- `FIX_RECOMMENDED`: 具体的な fix が適切である可能性が高い
- `REVIEW_RECOMMENDED`: 判断前に文脈確認が必要
- `NOISE_CANDIDATE`: tests、demos、research simulations では許容される可能性が高い
- `INFO_ONLY`: historical-version warnings を含む情報提供 finding

この分類はデフォルトで advisory です。保守者が fix、document、suppress、accept のいずれを選ぶかを判断する補助です。

## Active review queue

メインの review queue は、コンパクトに保つことを目的としています。

即時の注意が必要な findings は、以下として現れるべきです。

- `HITL_REQUIRED`
- `FIX_RECOMMENDED`
- `REVIEW_RECOMMENDED`

これらの件数がゼロの場合、Tasukeru が現在、人間による repair または review を優先すべきと判断している active advisory item はない、という意味です。

これは、リポジトリに警告がないことを意味しません。残りの警告が likely noise または historical / informational record として分類されている、という意味です。

## Historical-version warnings

Historical-version warnings は完全には除外されません。

Tasukeru Analysis は、superseded または historical simulator files 由来の findings を、監査上の可視性に役立つが active repair target ではない場合、`INFO_ONLY` として表示し続けます。

これにより、現在人間の注意が必要な findings に active review queue を集中させつつ、以下のために残されている古い versioned files への可視性を保ちます。

- 再現性
- 回帰比較
- 履歴参照
- versioned experiments
- 設計比較

historical warnings は、そのファイルが再び active entry point になった場合に再確認すべきです。

## Typical classification examples

例:

### B603 subprocess execution

通常は `HITL_REQUIRED` です。

subprocess 実行は外部副作用を生む可能性があるため、レビューが必要です。

### B404 subprocess import

通常は `REVIEW_RECOMMENDED` です。

subprocess を import するだけでは、それ自体は外部副作用ではありません。

### B101 assert usage in tests

通常は `NOISE_CANDIDATE` です。

pytest tests では一般的に `assert` を使います。

### B101 assert usage in active runtime code

通常は `FIX_RECOMMENDED` です。

runtime assert は Python の optimization flags によって削除される可能性があります。

### B101 assert usage in superseded historical simulator files

通常は `INFO_ONLY` です。

完全に除外するのではなく、historical-version warning として表示されます。そのファイルが active entry point にならない限り、即時 fix は不要です。

### B108 temporary path usage in tests

`tmp_path` のような isolated pytest fixtures を使っている場合、通常は `NOISE_CANDIDATE` です。

`/tmp/name` のような hard-coded shared path を使っている場合は、レビューすべきです。

### B311 pseudo-random generator usage in active simulations

通常は `REVIEW_RECOMMENDED` です。

決定論的な simulation randomness は、secrets、tokens、authentication、authorization、cryptography に使わない場合は許容されることがあります。

許容する場合は、その randomness が simulation-only であることをコードで説明すべきです。

### B311 pseudo-random generator usage in superseded historical simulator files

通常は `INFO_ONLY` です。

historical-version warning として表示されます。security-sensitive behavior や active runtime behavior に再利用されない限り、即時 fix は不要です。

### Dependency vulnerabilities from pip-audit

通常は `FIX_RECOMMENDED` です。

## Evidence, explanation, and prediction

Tasukeru Analysis は、findings に構造化された decision-support metadata を付与する場合があります。

これには以下が含まれることがあります。

- `evidence`: source tool、rule ID、file、line、snippet、artifact reference
- `explanation`: finding が重要な理由と修正方向が提案される理由
- `fix_prediction`: 提案変更に期待される安全性または保守性への影響
- `fix_verification`: 候補検証用の placeholder または結果データ

`fix_prediction` は保証ではありません。レビュー補助です。

`fix_verification` を有効にする場合も、advisory-only のままでなければなりません。candidate checks は一時ファイルまたは isolated files を使うべきであり、人間が明示的に手動適用を選ばない限り、リポジトリファイルを変更してはいけません。

## Output artifacts

Tasukeru Analysis は、以下の review artifacts を生成することがあります。

- `tasukeru_advisory_summary.md`
- `tasukeru_hitl_review.md`
- `tasukeru_hitl_review.json`
- `tasukeru_notification_state.json`
- `tasukeru_pr_comment.md`
- `tasukeru_dradm_draft.md`
- `tasukeru_dradm_draft.json`
- `tasukeru_confidence_report.md`
- `tasukeru_confidence_report.json`
- `tasukeru_result_consistency_report.md`
- `tasukeru_result_consistency_report.json`
- `tasukeru_result_consistency_verify.json`
- `tasukeru_dimension_dependency_report.md`
- `tasukeru_dimension_dependency_report.json`
- `tasukeru_dimension_dependency_verify.json`

`tasukeru_advisory_summary.md` は簡潔な概要を提供します。

`tasukeru_hitl_review.md` は、人間が読めるレビュー指針を提供します。内容には以下が含まれます。

- file path
- line number
- finding code
- issue summary
- review level
- suggested action

`tasukeru_hitl_review.json` は、同じ decision-support data を machine-readable 形式で提供します。

`tasukeru_notification_state.json` は、該当する場合、fingerprint-based incident aggregation を含む critical-notification state を記録します。

`tasukeru_pr_comment.md` は、`HITL_REQUIRED` incident が PR 通知条件を満たした場合にのみ使用される PR-comment body を記録します。

`tasukeru_dradm_draft.md` と `tasukeru_dradm_draft.json` は、人間レビュー用に生成される draft-only documentation proposals を含みます。

これらの DRADM drafts には、proposed minimal diffs、full draft text、hashes、evidence、review checklists が含まれることがあります。これらはリポジトリファイルを変更せず、自動適用してはいけません。

`tasukeru_confidence_report.md` と `tasukeru_confidence_report.json` は、分類、説明、draft recommendations に対する Tasukeru の confidence を要約します。

Confidence scores はレビュー補助 metadata にすぎません。finding を無視して安全であることを示すものではなく、自動 fix、自動 PR 作成、自動 commit、自動 push、自動 merge を可能にしてはいけません。

`tasukeru_result_consistency_report.md`、`tasukeru_result_consistency_report.json`、`tasukeru_result_consistency_verify.json` は、プロセスログと生成結果 artifacts が一致しているかを記録します。

これらは、decision counts、ARL verification、gate adoption status、self-definition verification、announcement data が出力間で整合していることを確認するために使われます。

`tasukeru_dimension_dependency_report.md`、`tasukeru_dimension_dependency_report.json`、`tasukeru_dimension_dependency_verify.json` は、findings、affected structures、impact classification、review levels、generated outputs が dependency-consistent であるかを記録します。

これらは advisory-only の dependency audit artifacts です。findings の変更、分類変更、fix 適用、commit 作成、push、pull request merge は行いません。

## Advisory behavior

Tasukeru Analysis はデフォルトで advisory です。

保守者が以下に答えやすくすることを目的としています。

- どの findings が likely noise か
- どの findings をレビューすべきか
- どのファイルに注意が必要か
- finding がなぜ関連するのか
- 推奨される fix は何か
- merge 前に HITL が必要か
- active repair candidate か historical-version warning か

この workflow は人間レビューを置き換えません。より安全なリポジトリ保守のための triage と documentation aid です。

## Repository purpose

このリポジトリの主目的は、agentic workflows を明示的な gates、再現可能な logs、中断点、人間レビューによって制御する方法を探ることです。

このプロジェクトは以下を重視します。

- fail-closed behavior
- HITL escalation
- gate-order invariants
- reason-code stability
- checkpoint / resume behavior
- tamper-evident audit records
- artifact integrity verification
- reproducible simulation outputs
- advice と execution の明確な分離

このリポジトリは、完全な AI safety coverage を提供すると主張しません。orchestration behavior を研究するための研究・教育用テストベンチです。

## Architecture diagrams

production-oriented Doc Orchestrator simulator の詳細な architecture diagrams は以下にまとめています。

- Doc Orchestrator Architecture Diagrams

このドキュメントには以下が含まれます。

- Doc Orchestrator overview
- task processing flow
- audit HMAC chain
- checkpoint resume flow
- data structure map

直接の diagram links も利用できます。

- Doc Orchestrator overview
- Task processing flow
- Audit HMAC chain
- Checkpoint resume flow
- Data structure map

その他の diagrams、reference files、bundles、documentation assets については以下を参照してください。

- Documentation Index

README は概要を簡潔に保ち、詳細 diagrams は `docs/architecture.md` に分離し、より広い documentation index は `docs/index.md` に分離しています。

## Current simulator lines

### 1. Mediator-based gate simulator

Example:

- `ai_doc_orchestrator_with_mediator_v1_0.py`
- `tests/test_doc_orchestrator_with_mediator_v1_0.py`

Plain-language guide:

- Japanese: [`docs/mediator_orchestrator_plain_guide.ja.md`](docs/mediator_orchestrator_plain_guide.ja.md)

このシミュレーターは、以下の flow に焦点を当てます。

```text
Agent → Mediator → Orchestrator
```

主な特徴:

- Agent が task input を正規化する。
- Mediator は advice のみを行う。
- Mediator は実行権限を持たない。
- Orchestrator は固定順で gates を評価する。
- RFL は相対的または曖昧な request に使われる。
- Ethics / ACC はより高リスクな blocking conditions を扱う。
- `sealed=True` は Ethics / ACC にのみ現れる。
- raw text は永続化すべきではない。
- audit logs は直接的な PII 漏えいを避けるべきである。

正規 gate order:

```text
Meaning → Consistency → RFL → Ethics → ACC → Dispatch
```

このシミュレーターは、以下の確認に有用です。

- gate invariants
- HITL transitions
- RFL pause behavior
- sealed / non-sealed behavior
- mediator-to-orchestrator separation
- reason-code expectations
- lightweight multi-task orchestration behavior

### 2. Production-oriented document orchestrator simulator

Example version:

- `v1.2.6-hash-chain-checkpoint`

このシミュレーターは、より強い永続化と整合性制御を備えた document-task orchestration に焦点を当てます。

主な特徴:

- Task Contract Gate
- rough token estimation
- Word / Excel / PPT task simulation
- per-task checkpoint / resume
- HMAC-SHA256 audit log hash chain
- HMAC-protected checkpoint files
- SHA-256 + HMAC artifact integrity records
- PII-safe audit / checkpoint / artifact writes
- tamper-evidence detection
- CLI-based simulation entry point
- mediation / negotiation feature なし
- automatic external submission なし

重要な実装上の注意:

このシミュレーターは、document-task results を表す text-backed artifact outputs を書き込みます。別途 document-generation libraries を接続していない限り、完全に整形された Microsoft Office documents を生成すると主張するものではありません。

Hashing と HMAC は tamper evidence を提供します。物理的な書き込み防止を提供するものではありません。実運用では、HMAC keys は environment variable または protected key file から供給し、リポジトリに commit してはいけません。

### 3. Emergency Contract × KAGE integration simulator

Example:

- `emergency_contract_kage_orchestrator_v1_0.py`
- `tests/test_emergency_contract_kage_orchestrator_v1_0.py`

このシミュレーターは、Emergency Contract Case B scenario と KAGE-style orchestration flow を組み合わせます。

これは小さな integration proof-of-concept であり、本番の契約、法務、信号制御システムではありません。

主な特徴:

- Emergency Contract Case B scenario
- KAGE-style gate order
- RFL non-sealing behavior
- Evidence validation and fabricated-evidence detection
- HITL auth checkpoint
- ADMIN finalize checkpoint
- Ethics / ACC sealed-stop invariants
- simulated contract draft artifact generation
- HMAC verification 付き tamper-evident ARL rows
- real-world signal control なし
- legal effect なし
- external submission、upload、send、API call、deployment なし

正規 integration flow:

```text
Meaning → Consistency → RFL → Evidence → HITL Auth → Draft
→ Ethics → Draft Lint → ACC → ADMIN Finalize → Dispatch
```

このシミュレーターは、以下の確認に有用です。

- emergency-contract scenario handling
- RFL を通じた relative-priority evaluation
- fabricated evidence pause behavior
- ACC による real-world control blocking
- USER and ADMIN HITL stop paths
- simulated artifact dispatch only
- ARL/HMAC verification
- normal and abnormal paths における KAGE invariants

### 4. Infrastructure Lifeline Mediation Simulation

Example:

- `infrastructure_lifeline_mediation_randomized_sim_v0_2.py`
- `tests/test_infrastructure_lifeline_mediation_randomized_sim_v0_2.py`

このシミュレーターは、3つの infrastructure agents が関わる制約付き lifeline-resource mediation scenario をモデル化します。

- electricity
- water
- gas

これは、mediator が制約された failure resources の下で proposal-only allocation plans を作成する方法を研究するための、ローカル・seed-reproducible な research simulation です。

主な特徴:

- normal resource requirements を持つ3つの infrastructure agents
- failure-mode total resource constraint
- minimum guarantees
- priority weights
- life-risk scores
- shortage-rate-aware allocation
- simulated HITL decisions
- JSON and stdout output
- external API access なし
- real infrastructure control なし
- automatic recovery なし
- automatic shutdown or disconnection なし

Mediator は allocation proposals のみを作成します。実インフラを制御したり、実世界の recovery actions を行ったりしません。

模擬 human operator は以下を返す場合があります。

- `APPROVE`
- `REJECT`
- `REDEFINE`
- `REQUEST_ALTERNATIVES`

このシミュレーターは、以下の確認に有用です。

- constrained resource allocation behavior
- proposal-only mediation
- seeded reproducibility
- HITL branch behavior
- safety-boundary flags
- JSON output behavior
- allocation totals が available resource limit 内に収まること

### 5. Agent Incident Mediation Simulation

Example:

- `agent_incident_mediation_sim_v0_2.py`
- `tests/test_agent_incident_mediation_sim_v0_2.py`

このシミュレーターは、オーケストレーション中に1つの模擬エージェントが定義外の行動を行う、ローカル専用の incident mediation flow をモデル化します。

PseudoTasukeru は log/output mismatch を検出し、Tasukeru 形式の review artifacts を作成して、その finding を Mediator にエスカレーションします。その後、Mediator は simulated HITL を実行し、メモリ上で `STOP_AGENT` または `AUTHORIZE_SEAL` の結果を適用します。

主な特徴:

- simulated abnormal agent behavior
- PseudoTasukeru による log/output mismatch detection
- PseudoTasukeru から Mediator への escalation packet
- simulated HITL decision branching
- `STOP_AGENT` / `AUTHORIZE_SEAL` のメモリ上のみの制御
- ARL verification
- 3D-DAC dependency consistency verification
- RCV result consistency verification
- Tasukeru-style local artifacts
- external API access なし
- real process control なし
- automatic fix、commit、push、merge なし

このシミュレーターは、以下の確認に有用です。

- abnormal agent が log/output inconsistency から検出されるか
- PseudoTasukeru が agents を直接停止せず、エスカレーションするか
- Mediator が停止または封印の前に HITL を実行するか
- simulated user instruction が記録されるか
- normal agents が誤って停止または封印されないか
- ARL、3D-DAC、RCV、generated artifacts が整合したままか

### 6. Code Anomaly Maestro Handoff Simulation

Example:

- `agent_code_anomaly_maestro_handoff_sim_v0_3_1.py`
- `tests/test_agent_code_anomaly_maestro_handoff_sim_v0_3_1.py`

このシミュレーターは、ローカル専用の code-contract anomaly handoff flow をモデル化します。

PseudoTasukeru は metadata-only の code-contract anomaly を検知し、その finding を Maestro にエスカレーションします。Maestro は自分で判断せず、模擬HITLを呼び出したうえで、模擬ユーザーの指示を実行します。

模擬ユーザーは以下を選択できます。

- `AUTHORIZE_SEAL`
- `QUARANTINE_HANDOFF_RESUME`

主な特徴:

- metadata-only code-contract anomaly detection
- PseudoTasukeru から Maestro へのエスカレーション
- Maestro は自己判断しない
- 模擬HITL指示の記録
- `AUTHORIZE_SEAL` 分岐
- `QUARANTINE_HANDOFF_RESUME` 分岐
- standby agent による安全な checkpoint handoff/resume
- ARL検証
- 3D-DACによる依存関係整合性検証
- RCVによる結果整合性検証
- コード実行なし
- マルウェア挙動なし
- 外部APIアクセスなし
- 実プロセス制御なし
- 自動fix、commit、push、mergeなし

このシミュレーターは、以下の確認に有用です。

- PseudoTasukeru が code-contract anomaly を検知できるか
- finding が Maestro にエスカレーションされるか
- Maestro が自己判断せず HITL を呼ぶか
- 模擬ユーザー指示が記録されるか
- seal 分岐と quarantine-handoff-resume 分岐がどちらも機能するか
- standby handoff が安全な checkpoint から再開できるか
- ARL、3D-DAC、RCV、generated artifacts が整合したままか

## Batch execution and resume

このリポジトリには、batch-style orchestration examples も含まれています。

Batch execution とは、複数の document-related tasks を、gate decisions、audit records、interruption points を保持したまま、1つの orchestration run として評価できることを意味します。

### Mediator-based batch flow

mediator-based simulator は、1回の run で複数の tasks を受け取れます。

利用例:

- 複数の spreadsheet / slide tasks をまとめて評価する
- task-level gate outcomes を比較する
- 複数 tasks にまたがる HITL behavior を確認する
- orchestration 前に mediator advice を検証する
- 各 task が固定 gate order を通ることを確認する

この系列は、以下に焦点を当てる場合に有用です。

- multi-task gate behavior
- mediator separation
- RFL / HITL transitions
- reason-code stability
- lightweight orchestration tests

Example task sequence:

- T1: xlsx task
- T2: pptx task
- T3: ambiguous task requiring RFL / HITL

期待される挙動:

- 各 task は Agent によって正規化される
- 各 task は Mediator advice を受け取る
- 各 task は Orchestrator によって評価される
- paused tasks は、Ethics / ACC が sealed stop を行わない限り non-sealed のまま
- dispatch は final decision が `RUN` の場合のみ行われる

### Document-task batch flow

production-oriented document orchestrator simulator は、固定された document-task sequence を使用します。

```text
Word → Excel → PPT
```

この系列は、以下に焦点を当てる場合に有用です。

- batch task execution
- per-task checkpointing
- interruption and resume
- artifact integrity records
- HMAC-protected checkpoints
- HMAC-SHA256 audit log hash chains
- tamper-evidence detection

task が中断された場合、シミュレーターは以下を記録します。

- failed task ID
- failed layer
- reason code
- checkpoint path
- resume requirement
- 該当する場合の HITL confirmation requirement

後続 run は、必要に応じて HITL confirmation を受けた後、checkpoint から resume できます。

## Batch scripts

Batch scripts は、ローカル simulation runs の convenience wrappers として使用できます。

推奨 script examples:

- `scripts/run_doc_orchestrator_demo.bat`
- `scripts/run_doc_orchestrator_resume.bat`
- `scripts/run_doc_orchestrator_tamper_check.bat`

これらの scripts は、local developer utilities としてのみ扱うべきです。

以下を行ってはいけません。

- production HMAC keys を埋め込む
- artifacts を自動 upload または submit する
- HITL confirmation を迂回する
- files を自動削除する
- 実在する個人データや機密データを処理する
- license または safety semantics を変更する
- tests または gate invariants を弱める

ローカル demonstrations では、シミュレーターが明示的に対応している場合のみ demo key mode を使用できます。production-like runs では、HMAC keys に environment variable または protected key file を使用すべきです。

### Example batch-script roles

#### `run_doc_orchestrator_demo.bat`

目的:

- local demonstration を実行する
- safe sample input を使用する
- audit logs と simulated artifacts を local output directories に書き込む
- external submission を避ける

典型的な用途:

- demo key mode による local demo run

#### `run_doc_orchestrator_resume.bat`

目的:

- checkpoint から resume する
- 明示的な resume confirmation を要求する
- 続行前に completed artifacts を検証する
- checkpoint integrity を保持する

典型的な用途:

- HITL confirmation 後に中断された Word / Excel / PPT simulation を再開する

#### `run_doc_orchestrator_tamper_check.bat`

目的:

- audit-log / checkpoint / artifact integrity behavior を検証する
- tamper-evidence detection を実演する
- integrity verification に失敗した場合 HITL へ pause する

典型的な用途:

- local tamper-evidence simulation

## Recommended reading order

gate behavior と KAGE-like invariants を確認する場合:

- `ai_doc_orchestrator_with_mediator_v1_0.py`
- `tests/test_doc_orchestrator_with_mediator_v1_0.py`

checkpoint、resume、artifact integrity、HMAC-chain behavior を確認する場合:

- Production-oriented Doc Orchestrator Simulator
- `v1.2.6-hash-chain-checkpoint`

Emergency Contract × KAGE integration behavior を確認する場合:

- `emergency_contract_kage_orchestrator_v1_0.py`
- `tests/test_emergency_contract_kage_orchestrator_v1_0.py`

この経路は、具体的な emergency-contract scenario が KAGE-style gates、HITL checkpoints、ARL/HMAC verification、simulated artifact dispatch によって、real-world control や legal effect なしに評価される方法を学ぶのに有用です。

Agent Incident Mediation behavior を確認する場合:

- `agent_incident_mediation_sim_v0_2.py`
- `tests/test_agent_incident_mediation_sim_v0_2.py`

この経路は、PseudoTasukeru が simulated log/output mismatch を検出し、Mediator へエスカレーションし、HITL を発火させ、user instruction を記録し、external side effects なしに ARL / 3D-DAC / RCV consistency を検証する方法を学ぶのに有用です。

Code Anomaly Maestro Handoff behavior を確認する場合:

- `agent_code_anomaly_maestro_handoff_sim_v0_3_1.py`
- `tests/test_agent_code_anomaly_maestro_handoff_sim_v0_3_1.py`

この経路は、PseudoTasukeru が metadata-only の code-contract anomaly を検知し、Maestro にエスカレーションし、HITL を発火させ、模擬ユーザー指示を記録し、外部副作用なしに `AUTHORIZE_SEAL` または `QUARANTINE_HANDOFF_RESUME` を実行する方法を学ぶのに有用です。

挙動を検証する場合は、常に実装と対応するテストを一緒に読んでください。

これは特に以下について重要です。

- gate invariants
- reason-code expectations
- HITL transitions
- sealed / non-sealed behavior
- checkpoint / resume behavior
- tamper-evidence behavior
- reproducibility checks
- benchmark expectations
- batch execution behavior

## Testing and behavior

このリポジトリでは、tests が simulators と orchestration logic の期待挙動を定義することが多いです。

挙動を確認する場合は、通常、実装と対応するテストを一緒に読む方が良いです。

Tests は以下を検証することがあります。

- fixed gate order
- fail-closed behavior
- HITL escalation
- RFL non-sealing behavior
- Ethics / ACC sealing constraints
- checkpoint recovery
- audit-log integrity
- artifact hash verification
- reason-code stability
- reproducibility expectations
- batch-task behavior
- CLI behavior
- emergency-contract scenario flow
- fabricated-evidence pause behavior
- real-world control sealed-stop behavior
- USER / ADMIN HITL rejection paths
- ARL/HMAC tamper detection

新しい version number が、必ずしも primary recommended entry point を意味するわけではありません。一部のファイルは、historical comparison、reproducibility、versioned experiments のために保存されています。

## Gate and decision model

このリポジトリでは、orchestration behavior を追跡可能にするため、明示的な gate decisions を使用します。

一般的な decisions は以下です。

- `RUN`
- `PAUSE_FOR_HITL`
- `STOPPED`

一般的な解釈:

- `RUN`: シミュレーターが次の gate または dispatch step へ進んでよい
- `PAUSE_FOR_HITL`: シミュレーターは停止し、人間レビューを待つべき
- `STOPPED`: シミュレーターが blocking condition に到達した

KAGE-like simulator lines では、RFL は seal ではなく HITL へ pause すべきです。Sealing behavior は、simulator contract に応じて、Ethics や ACC などの higher-risk layers に限定されるべきです。

## Audit and integrity model

Audit and integrity behavior は simulator line ごとに異なります。

mediator-based simulator は、lightweight audit events と safe context logging に焦点を当てます。

production-oriented document simulator は、より強い integrity controls を追加します。

- audit log hash chain
- row-level HMAC
- checkpoint HMAC
- artifact SHA-256
- artifact HMAC
- completed-artifact verification on resume
- tamper-evidence detection

これらの仕組みは、変更を検出可能にするためのものです。ローカルの行為者がディスク上のファイルを変更することを防ぐものではありません。

## Checkpoint and resume model

Checkpoint-based simulators は、中断された実行をサポートするよう設計されています。

checkpoint には以下が記録される場合があります。

- run ID
- current task ID
- failed task ID
- failed layer
- reason code
- task status
- artifact path
- artifact hash
- resume が許可されるか
- resume 前に HITL が必要か

resume 時には、シミュレーターが続行する前に completed artifacts を検証すべきです。検証に失敗した場合は、黙って続行せず、HITL へ pause すべきです。

## Artifact model

シミュレーターの artifact outputs は、research artifacts として扱うべきです。

simulator line によって、outputs には以下が含まれる場合があります。

- artifact previews
- text-backed document-task outputs
- audit JSONL files
- checkpoint JSON files
- integrity metadata
- summary records

実際の document-generation code が追加・テストされていない限り、リポジトリはこれらの simulated outputs を完全な production Office documents と記述すべきではありません。

## External side effects

External side effects には以下のような操作が含まれます。

- email の送信
- file の upload
- artifact の submit
- 変更の push
- file の削除
- external API の呼び出し
- license semantics の変更

これらの操作は、simulator contract に応じて、blocked、prohibited、または HITL-gated のままにすべきです。

どの script や simulator も、external submission を黙って実行してはいけません。

## Archive and historical files

一部のファイルは以下のために保存されています。

- historical comparison
- reproducibility
- versioned experiments
- regression testing
- design comparison

`archive/` 配下のファイルは、current tests または documentation で明示的に参照されていない限り、一般に historical または reference material として扱うべきです。

## Language

- English README: `README.md`
- Japanese README: `README.ja.md`

## License

このリポジトリは split-license model を使用します。

- Software code: Apache License 2.0
- Documentation, diagrams, and research materials: CC BY-NC-SA 4.0

詳細は `LICENSE_POLICY.md` を参照してください。

## Project policies

- [Security Policy](SECURITY.md)
- [License Policy](LICENSE_POLICY.md)
- [Contributing Guide](CONTRIBUTING.md)

## Disclaimer

このリポジトリは、研究・教育目的のみで提供されます。

これは本番安全システムではなく、compliance certification でもなく、安全な自律挙動を保証するものでもありません。実世界で利用する前に、ユーザー自身がコードをレビュー、テスト、適応する責任を負います。

独立したレビューと適切な safeguards なしに、このリポジトリを実在する個人データ、機密の運用データ、または high-stakes decision workflows の処理に使用しないでください。
