# 📘 Maestro Orchestrator — マルチエージェント・オーケストレーション・フレームワーク

> English: [README.md](README.md)

GitHub Stars Open Issues License Python App CI Tasukeru Advisory  
Python Version Ruff Last Commit

Maestro Orchestrator は、マルチエージェント・ガバナンス、fail-closed 制御、HITL エスカレーション、checkpoint による再開、改ざん検知可能なシミュレーションワークフローを扱う、研究志向のオーケストレーション・フレームワークです。

このリポジトリには、複数のシミュレーター系統が含まれています。一部のファイルは KAGE 的なゲート挙動と mediator 分離に焦点を当てており、別のファイル群は document-task の batch 実行、checkpoint、監査整合性、artifact 検証に焦点を当てています。

## 初めて読む人向けガイド

このリポジトリを初めて読む場合は、ここから始めてください。

1. まず **Safety and scope / 安全性と適用範囲** を読んでください。
2. **Tasukeru Analysis / 助ける君** を読み、レビュー補助ワークフローの役割を理解してください。
3. **Advisory-only policy / 助言専用ポリシー** を読み、この workflow が何をしないかを理解してください。
4. **HITL decision support / HITL 判断支援** を読み、どのような場合に人間レビューが必要になるかを確認してください。
5. 安全境界を理解した後で、**Current simulator lines / 現在のシミュレーター系統** を読んでください。

このリポジトリは、研究・教育目的のテストベンチです。  
出力は研究用 artifact であり、本番承認や安全保証ではありません。

挙動が不明な場合は、変更を適用する前に、関連する実装と対応するテストを一緒に確認してください。

## 安全性と適用範囲

このリポジトリは研究用プロトタイプです。

次の用途は意図していません。

- 本番環境での自律的意思決定
- 無監督の現実世界制御
- 法律、医療、金融、規制に関する助言
- 実在する個人データや機密運用データの処理
- 完全または普遍的な安全性カバレッジの証明
- 外部への自動提出、アップロード、送信、デプロイ
- 外部副作用に対する HITL レビューの迂回

各サンプルは、以下として読むべきです。

- 研究用シミュレーション
- 教育用リファレンス
- ガバナンス / 安全性テストベンチ
- fail-closed と HITL 設計の例
- 監査ログと checkpoint 整合性の実験
- ローカルシミュレーション向けの batch orchestration 例

外部への submit / upload / push / send は、HITL によって gate されるべきです。

## 責任ある利用と禁止用途

Tasukeru Analysis とシミュレーター例は、ユーザー自身が所有するリポジトリ、または明示的な許可を得たリポジトリに対する防御的レビューを目的としています。

このリポジトリやツールを、次の目的で使用しないでください。

- 無許可の脆弱性探索
- 攻撃的な偵察
- 第三者のシステムやコードの exploit
- 認証情報、token、secret の収集
- 許可のないリポジトリやシステムのスキャン
- 実在する対象に対する exploit 手順の生成または検証
- アクセス制御、rate limit、security boundary の迂回
- responsible disclosure なしに機密性の高い finding を公開すること

finding は、安全性、信頼性、追跡性、ガバナンスを改善するために使用してください。第三者または OSS のコードをレビューする場合は、そのプロジェクトの security policy と responsible disclosure process に従ってください。

## Tasukeru Analysis / 助ける君

Tasukeru Analysis は、防御的なリポジトリレビューのための advisory workflow です。

以下のような静的解析およびリポジトリ固有のチェックを実行します。

- Ruff
- Bandit
- pip-audit
- Tasukeru logic review
- documentation review
- HITL decision support classification

この workflow は、すべての advisory finding を自動的に blocking failure として扱うのではなく、保守性、安全レビュー、開発者の使いやすさを改善するように設計されています。

Tasukeru Analysis は warning を隠すことを目的としていません。代わりに、active repair candidates、review-only findings、historical-version warnings、likely noise を分離し、maintainer が重要な項目に集中できるようにします。

## Advisory-only policy / 助言専用ポリシー

Tasukeru Analysis は advisory-only のレビュー補助です。

以下は行いません。

- branch の自動作成
- pull request の自動作成
- 自動 commit
- 自動 push
- 自動 fix 適用
- 自動 merge

PR comment を生成し得るのは、`HITL_REQUIRED` finding のみです。

`FIX_RECOMMENDED`、`REVIEW_RECOMMENDED`、`NOISE_CANDIDATE`、`INFO_ONLY` を含むその他の finding は、人間レビュー用に GitHub Step Summary と workflow artifact に集約されます。

Tasukeru Analysis は、人間の review 負荷を下げることを目的としており、人間の意思決定を置き換えるものではありません。

## 人間可読性ポリシー

Tasukeru Analysis は、人間が安全に読める、レビューできる、保守できるコードを優先します。

AI や自動化ツールにとって処理しやすいという理由だけで、その変更を良い修正とみなすべきではありません。人間にとっての可読性、レビューしやすさ、保守性を下げる可能性がある変更は、人間レビューへ戻されるべきです。

## セキュリティレビュー出力ポリシー

Tasukeru Analysis は、防御的レビューと安全な修正方針の提示に限定されます。

公開 PR comment には、以下を含めるべきではありません。

- exploit payload
- 攻撃コマンド
- 攻撃的な再現手順
- step-by-step の exploit 手順
- 第三者対象の exploit 詳細

セキュリティ関連 finding は、以下に焦点を当てるべきです。

- 影響を受けるファイルと行
- レビューが必要な防御上の理由
- 期待される安全性への影響
- 安全な修正方針
- 人間レビューが必要かどうか

## HITL decision support / HITL 判断支援

Tasukeru Analysis は、maintainer が actionable issue と想定される noise を分離できるように、finding を review level に分類します。

現在の review level は以下です。

- `HITL_REQUIRED`: merge または次の action の前に人間レビューが必要
- `FIX_RECOMMENDED`: 具体的な修正が適切である可能性が高い
- `REVIEW_RECOMMENDED`: 判断前に文脈レビューが必要
- `NOISE_CANDIDATE`: tests、demo、research simulation では許容される可能性が高い
- `INFO_ONLY`: historical-version warning を含む情報提供 finding

この分類は標準では advisory です。maintainer が、修正、文書化、抑制、許容のいずれを選ぶべきか判断するための補助です。

## Active review queue

main review queue は、コンパクトに保つことを意図しています。

即時対応が必要な finding は、以下として表示されるべきです。

- `HITL_REQUIRED`
- `FIX_RECOMMENDED`
- `REVIEW_RECOMMENDED`

これらの count が 0 の場合、Tasukeru が現在、人間による修正またはレビューの優先対象として推奨している active advisory item はない、という意味です。

これは、リポジトリに warning が存在しないという意味ではありません。残っている warning が likely noise または historical / informational records として分類されている、という意味です。

## Historical-version warnings

historical-version warning は完全には除外されません。

Tasukeru Analysis は、superseded または historical simulator file からの finding を、audit visibility のために有用であり active repair target ではない場合、`INFO_ONLY` として可視化します。

これにより、active review queue は現在人間の注意を必要とする finding に集中しつつ、以下の目的で保持された古い versioned file への可視性を維持します。

- 再現性
- regression comparison
- historical reference
- versioned experiments
- design comparison

historical warning は、そのファイルが再び active entry point になった場合に再確認すべきです。

## Typical classification examples / 典型的な分類例

### B603 subprocess execution

通常は `HITL_REQUIRED` です。

subprocess execution は外部副作用を作る可能性があるため、レビューが必要です。

### B404 subprocess import

通常は `REVIEW_RECOMMENDED` です。

subprocess を import すること自体は、外部副作用ではありません。

### B101 assert usage in tests

通常は `NOISE_CANDIDATE` です。

pytest の test では、一般的に `assert` を使用します。

### B101 assert usage in active runtime code

通常は `FIX_RECOMMENDED` です。

runtime の assert statement は、Python optimization flag によって削除される可能性があります。

### B101 assert usage in superseded historical simulator files

通常は `INFO_ONLY` です。

完全に除外するのではなく、historical-version warning として可視化されます。そのファイルが active entry point にならない限り、即時修正は不要です。

### B108 temporary path usage in tests

`tmp_path` のような isolated pytest fixture を使用している場合、通常は `NOISE_CANDIDATE` です。

`/tmp/name` のような hard-coded shared path を使用している場合は、レビューすべきです。

### B311 pseudo-random generator usage in active simulations

通常は `REVIEW_RECOMMENDED` です。

deterministic simulation randomness は、secret、token、authentication、authorization、cryptography に使用されていない場合は許容されることがあります。

許容する場合は、その randomness が simulation-only であることをコード上に文書化すべきです。

### B311 pseudo-random generator usage in superseded historical simulator files

通常は `INFO_ONLY` です。

historical-version warning として可視化されます。security-sensitive behavior や active runtime behavior に再利用されない限り、即時修正は不要です。

### Dependency vulnerabilities from pip-audit

通常は `FIX_RECOMMENDED` です。

## Evidence, explanation, and prediction

Tasukeru Analysis は、finding に構造化された decision-support metadata を付与することがあります。

これには以下が含まれます。

- `evidence`: source tool、rule ID、file、line、snippet、artifact reference
- `explanation`: なぜその finding が重要か、なぜその修正方針が提案されるか
- `fix_prediction`: 提案変更によって期待される安全性または保守性への影響
- `fix_verification`: candidate verification の placeholder または result data

`fix_prediction` は保証ではありません。review aid です。

`fix_verification` が有効な場合も、advisory-only のままでなければなりません。candidate check は temporary file または isolated file を使うべきであり、人間が明示的に手動適用を選ばない限り、repository file を変更してはいけません。

## Output artifacts

Tasukeru Analysis は、以下の review artifact を生成することがあります。

- `tasukeru_advisory_summary.md`
- `tasukeru_hitl_review.md`
- `tasukeru_hitl_review.json`
- `tasukeru_notification_state.json`
- `tasukeru_pr_comment.md`
- `tasukeru_dradm_draft.md`
- `tasukeru_dradm_draft.json`
- `tasukeru_confidence_report.md`
- `tasukeru_confidence_report.json`

`tasukeru_advisory_summary.md` は簡潔な概要を提供します。

`tasukeru_hitl_review.md` は、以下を含む人間向けのレビューガイダンスを提供します。

- file path
- line number
- finding code
- issue summary
- review level
- suggested action

`tasukeru_hitl_review.json` は、同じ decision-support data を machine-readable format で提供します。

`tasukeru_notification_state.json` は、fingerprint-based incident aggregation が適用される場合を含め、critical-notification state を記録します。

`tasukeru_pr_comment.md` は、`HITL_REQUIRED` incident が PR notification の条件を満たす場合にのみ使用される PR comment body を記録します。

`tasukeru_dradm_draft.md` と `tasukeru_dradm_draft.json` は、人間レビュー用に生成された draft-only documentation proposal を含みます。

これらの DRADM draft には、提案される最小 diff、full draft text、hash、evidence、review checklist が含まれることがあります。これらは repository file を変更せず、自動適用されてはいけません。

`tasukeru_confidence_report.md` と `tasukeru_confidence_report.json` は、Tasukeru の classification、explanation、draft recommendation に対する confidence を要約します。

confidence score は review-aid metadata にすぎません。finding を無視してよいことを示すものではなく、自動 fix、自動 PR 作成、自動 commit、自動 push、自動 merge を有効化してはいけません。

## Advisory behavior

Tasukeru Analysis は標準では advisory です。

maintainer が以下を判断する支援を行います。

- どの finding が likely noise か
- どの finding を review すべきか
- どの file に注意が必要か
- なぜその finding が関連するのか
- 提案される fix は何か
- merge 前に HITL が必要か
- active repair candidate か historical-version warning か

この workflow は人間レビューを置き換えません。より安全な repository maintenance のための triage と documentation aid です。

## Repository purpose

このリポジトリの主目的は、明示的な gate、再現可能な log、中断点、人間レビューによって agentic workflow をどのように制御できるかを探索することです。

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

このリポジトリは、完全な AI safety coverage を提供すると主張するものではありません。orchestration behavior を研究するための、研究・教育用 test bench です。

## Architecture diagrams

production-oriented Doc Orchestrator simulator の詳細な architecture diagram は、以下にまとめられています。

- Doc Orchestrator Architecture Diagrams

この document には以下が含まれます。

- Doc Orchestrator overview
- task processing flow
- audit HMAC chain
- checkpoint resume flow
- data structure map

direct diagram link も利用できます。

- Doc Orchestrator overview
- Task processing flow
- Audit HMAC chain
- Checkpoint resume flow
- Data structure map

その他の diagram、reference file、bundle、documentation asset については、以下を参照してください。

- Documentation Index

README は overview を簡潔に保ち、詳細 diagram は `docs/architecture.md` に分離し、より広い documentation index は `docs/index.md` に分離しています。

## Current simulator lines

### 1. Mediator-based gate simulator

例:

- `ai_doc_orchestrator_with_mediator_v1_0.py`
- `tests/test_doc_orchestrator_with_mediator_v1_0.py`

この simulator は、以下の流れに焦点を当てています。

```text
Agent → Mediator → Orchestrator
