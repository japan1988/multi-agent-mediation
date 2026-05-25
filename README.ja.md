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

Maestro Orchestrator は、マルチエージェント・ガバナンス、fail-closed 制御、HITL エスカレーション、チェックポイントベースの再開、改ざん検知可能なシミュレーション・ワークフローを扱う、研究志向のオーケストレーション・フレームワークです。

このリポジトリには、複数のシミュレーター系列が含まれています。一部のファイルは KAGE 的なゲート動作と Mediator 分離に焦点を当て、別のファイル群はドキュメントタスクのバッチ実行、チェックポイント、監査整合性、成果物検証に焦点を当てています。

## 初心者向け読み順

このリポジトリを初めて読む場合は、ここから始めてください。

1. まず **Safety and scope** を読む。
2. **Tasukeru Analysis** を読み、レビュー補助機能を理解する。
3. **Advisory-only policy** を読み、このワークフローが「何をしないか」を理解する。
4. **HITL decision support** を読み、人間レビューが必要になる条件を理解する。
5. 安全境界を理解したあとで、**Current simulator lines** を読む。

このリポジトリは、研究・教育目的のテストベンチです。  
出力は研究成果物であり、本番承認や安全保証ではありません。

挙動が不明な場合は、変更を適用する前に、関連する実装とテストを必ず併せて読んでください。

## Safety and scope

このリポジトリは研究用プロトタイプです。

以下を目的としていません。

- 本番環境での自律的意思決定
- 教師なしの現実世界制御
- 法務、医療、金融、規制に関する助言
- 実在の個人データや機密運用データの処理
- 完全または普遍的な安全性カバレッジの実証
- 外部提出、アップロード、送信、デプロイの自動化
- 外部副作用に対する HITL レビューの迂回

各例は、以下として読むべきです。

- 研究用シミュレーション
- 教育用リファレンス
- ガバナンス / 安全性テストベンチ
- fail-closed と HITL 設計の例
- 監査ログとチェックポイント整合性の実験
- ローカルシミュレーション用のバッチ・オーケストレーション例

外部送信 / アップロード / push / send に該当する操作は、HITL ゲート付きのままにしてください。

## Responsible use and prohibited use

Tasukeru Analysis とシミュレーター例は、ユーザー自身が所有するリポジトリ、または明示的な許可を得たリポジトリに対する防御的レビューを目的としています。

このリポジトリまたはそのツールを、以下に使用しないでください。

- 無許可の脆弱性探索
- 攻撃的偵察
- 第三者システムまたは第三者コードの悪用
- 認証情報、トークン、シークレットの収集
- 許可のないリポジトリまたはシステムのスキャン
- 実ターゲットに対する exploit 手順の生成または検証
- アクセス制御、レート制限、セキュリティ境界の迂回
- 責任ある開示を経ない機微な発見事項の公開

発見事項は、安全性、信頼性、追跡可能性、ガバナンスを改善するために使用してください。第三者またはオープンソースのコードをレビューする場合は、そのプロジェクトのセキュリティポリシーおよび責任ある開示プロセスに従ってください。

## Tasukeru Analysis

Tasukeru Analysis は、防御的リポジトリレビューのための助言型ワークフローです。

Tasukeru Analysis は、マルチエージェントおよびエージェント型ワークフローの複雑化を検査・統制するための補助も目的としています。これらのワークフローが大きくなるほど、挙動の検査、説明、監査は難しくなります。

主に以下のようなレビュー支援上の問いに焦点を当てます。

- 発見事項が適切なレビュー段階に分類されているか
- プロセスログと生成出力の整合性が保たれているか
- 不確実またはリスクの高いケースを HITL に戻すべきか
- 公開 PR コメントが過度に詳細な攻撃情報を含んでいないか
- ワークフローが自動修正、コミット、push、マージを行わず advisory-only のままか

このワークフローは、詳細な exploit 手順を開示せず、自律的な強制システムとしても動作しません。詳細な発見事項は、人間レビューのためにワークフロー成果物やログ内に残されます。

実行する静的チェックおよびリポジトリ固有チェックには、以下が含まれます。

- Ruff
- Bandit
- pip-audit
- Tasukeru logic review
- documentation review
- HITL decision support classification

このワークフローは、すべての advisory finding をブロッキング失敗として扱うことなく、保守性、安全レビュー、開発者の使いやすさを改善するよう設計されています。

Tasukeru Analysis は警告を隠すことを目的としていません。代わりに、active repair candidate、review-only finding、historical-version warning、likely noise を分離し、メンテナーが優先すべき項目に集中できるようにします。

Tasukeru Analysis には、結果整合性監査レイヤーも含まれます。

初期のチェックは、レビュー工程、ログ、ゲート、分類が不審または不整合に見えるかどうかに焦点を当てます。結果整合性監査はさらに、生成された出力が記録されたプロセス状態と一致しているかを確認します。

プロセス記録を、summary、HITL review data、announcement data、ARL verification data、gate adoption data、self-definition verification data などの生成成果物と比較します。

これにより、件数、検証状態、ゲート採用結果、アナウンス内容が基礎記録と一致しないケースなど、内部プロセスと公開結果が食い違う場合を検出しやすくなります。

このレイヤーは report-only です。成果物の書き換え、分類変更、修正適用、Pull Request 作成、コミット、push、マージは自動実行しません。

## Tasukeru adversarial stress test

Tasukeru adversarial stress test は、ローカル・合成・防御用のストレステストです。

外部システムへの攻撃、exploit 実行、第三者ターゲットのスキャン、Pull Request 作成、push、修正適用、マージの自動実行は行いません。

このストレステストは、異常形式、矛盾、迂回風の合成入力をローカル評価器へ与え、Tasukeru 型の安全不変条件が維持されることを検証します。

典型的な合成ケースには、以下が含まれます。

- 不正な JSON / JSONL
- 必須監査キーの欠落
- RFL sealed-state 矛盾
- 非安全レイヤーでの sealed 行
- HITL bypass 風テキスト
- auto-merge / auto-fix injection 風テキスト
- 重複 JSON キー
- 疑わしい path 風文字列
- 過大な audit line

期待される挙動は fail-closed または review-oriented です。

- automation は無効のまま
- リスクのある合成ケースに unsafe `RUN` を返さない
- RFL sealed 矛盾は sealed せずエスカレーションする
- 非安全 sealed 行はレビューへエスカレーションする
- HITL bypass 風入力は人間レビューを迂回しない

このテストは、防御的堅牢性と回帰カバレッジを改善するためのものです。攻撃用セキュリティツールではありません。

## Tasukeru boundary self-check tests

Tasukeru boundary self-check tests は、Tasukeru 自身のワークフロー境界が揃っていることを検証します。

生成成果物、PR Draft 成果物一覧、upload artifact paths、ARL artifact-integrity records、result-consistency expectations が互いにずれていないかを確認します。

維持されているテストのエントリポイントは以下です。

- `tests/test_tasukeru_boundary_self_check_v0_2.py`

legacy/private 互換 shim は以下です。

- `tests/_tasukeru_boundary_self_check_v0_1.py`

これらのテストは static/read-only です。外部操作、ブランチ作成、Pull Request 作成、コミット、push、修正適用、コメント投稿、マージを自動実行しません。

## Advisory-only policy

Tasukeru Analysis は advisory-only のレビュー補助です。

以下を行いません。

- ブランチを自動作成しない
- Pull Request を自動作成しない
- 変更を自動コミットしない
- 変更を自動 push しない
- 修正を自動適用しない
- Pull Request を自動マージしない

`HITL_REQUIRED` の発見事項のみ、PR コメントを生成する場合があります。

`FIX_RECOMMENDED`、`REVIEW_RECOMMENDED`、`NOISE_CANDIDATE`、`INFO_ONLY` を含むその他の発見事項は、人間レビューのために GitHub Step Summary とワークフロー成果物に集約されます。

Tasukeru Analysis は人間のレビュー負荷を減らすためのものであり、人間の意思決定を置き換えるものではありません。

## Human readability policy

Tasukeru Analysis は、人間が安全に読み、レビューし、保守できるコードを優先します。

AI や自動ツールにとって処理しやすいという理由だけで、変更を良い修正として扱うべきではありません。人間の可読性、レビュー可能性、保守性を下げる可能性がある変更は、人間レビューに戻すべきです。

## Security review output policy

Tasukeru Analysis は、防御的レビューと安全な修正方針の提示に限定されます。

公開 PR コメントには、以下を含めるべきではありません。

- exploit payload
- 攻撃コマンド
- 攻撃的な再現手順
- 段階的な exploit 手順
- 第三者ターゲットの exploit 詳細

セキュリティ関連の発見事項は、以下に焦点を当てるべきです。

- 影響するファイルと行
- レビューが必要な防御上の理由
- 期待される安全上の影響
- 安全な修正方向
- 人間レビューが必要かどうか

## HITL decision support

Tasukeru Analysis は、メンテナーが対応すべき問題と想定されるノイズを分離できるよう、発見事項をレビュー段階へ分類します。

現在のレビュー段階は以下です。

- `HITL_REQUIRED`: マージまたは次の操作前に人間レビューが必要
- `FIX_RECOMMENDED`: 具体的修正が適切である可能性が高い
- `REVIEW_RECOMMENDED`: 判断前に文脈レビューが必要
- `NOISE_CANDIDATE`: テスト、デモ、研究シミュレーションでは許容される可能性が高い
- `INFO_ONLY`: historical-version warning を含む情報提供

この分類はデフォルトでは advisory です。メンテナーが修正、文書化、抑制、受容を判断するための補助です。

## Active review queue

主要レビューキューはコンパクトに保つことを意図しています。

即時対応が必要な発見事項は、以下として表示されるべきです。

- `HITL_REQUIRED`
- `FIX_RECOMMENDED`
- `REVIEW_RECOMMENDED`

これらの件数がゼロの場合、Tasukeru が現在、人間による修正またはレビューを優先すべきと推奨する active advisory item はリポジトリ内にありません。

これは、リポジトリに警告が存在しないという意味ではありません。残りの警告が likely noise または historical/informational records として分類されていることを意味します。

## Historical-version warnings

Historical-version warning は完全には除外されません。

Tasukeru Analysis は、superseded または historical simulator files の発見事項を、監査可視性に有用だが active repair target ではない場合に `INFO_ONLY` として可視化します。

これにより、すぐに人間対応が必要な発見事項に active review queue を集中させつつ、以下の目的で保持される旧版ファイルへの可視性を維持します。

- 再現性
- 回帰比較
- 履歴参照
- バージョン付き実験
- 設計比較

historical warning は、そのファイルが再び active entry point になる場合に再検討してください。

## Typical classification examples

例:

### B603 subprocess execution

通常は `HITL_REQUIRED`。

subprocess 実行は外部副作用を作る可能性があるため、レビューが必要です。

### B404 subprocess import

通常は `REVIEW_RECOMMENDED`。

subprocess の import 自体は外部副作用ではありません。

### B101 assert usage in tests

通常は `NOISE_CANDIDATE`。

pytest テストでは一般に `assert` を使用します。

### B101 assert usage in active runtime code

通常は `FIX_RECOMMENDED`。

runtime assert は Python 最適化フラグで削除される可能性があります。

### B101 assert usage in superseded historical simulator files

通常は `INFO_ONLY`。

完全除外せず、historical-version warning として可視化します。そのファイルが active entry point になるまでは即時修正不要です。

### B108 temporary path usage in tests

`tmp_path` などの隔離された pytest fixture を使用している場合、通常は `NOISE_CANDIDATE`。

`/tmp/name` のような hard-coded shared path を使う場合はレビューすべきです。

### B311 pseudo-random generator usage in active simulations

通常は `REVIEW_RECOMMENDED`。

決定的シミュレーション用の乱数は、secret、token、authentication、authorization、cryptography に使用されない場合は許容されることがあります。

許容する場合は、その乱数が simulation-only であることをコード上で文書化すべきです。

### B311 pseudo-random generator usage in superseded historical simulator files

通常は `INFO_ONLY`。

historical-version warning として可視化します。security-sensitive behavior または active runtime behavior に再利用されない限り、即時修正不要です。

### Dependency vulnerabilities from pip-audit

通常は `FIX_RECOMMENDED`。

## Evidence, explanation, and prediction

Tasukeru Analysis は、発見事項に構造化された decision-support metadata を付ける場合があります。

これには以下が含まれます。

- `evidence`: source tool、rule ID、file、line、snippet、artifact reference
- `explanation`: なぜ発見事項が重要か、なぜ修正方向が提案されるか
- `fix_prediction`: 提案変更によって期待される安全性または保守性への影響
- `fix_verification`: 候補検証用の placeholder または結果データ

`fix_prediction` は保証ではありません。レビュー補助です。

`fix_verification` を有効にする場合も advisory-only のままでなければなりません。候補チェックは一時ファイルまたは隔離ファイルを使い、人間が明示的に手動適用を選ばない限り、リポジトリファイルを変更してはいけません。

## Output artifacts

Tasukeru Analysis は、以下のレビュー成果物を生成する場合があります。

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

`tasukeru_hitl_review.md` は、人間が読めるレビューガイダンスを提供します。内容には以下が含まれます。

- file path
- line number
- finding code
- issue summary
- review level
- suggested action

`tasukeru_hitl_review.json` は、同じ decision-support data を機械可読形式で提供します。

`tasukeru_notification_state.json` は、fingerprint-based incident aggregation を含む critical-notification state を記録します。

`tasukeru_pr_comment.md` は、`HITL_REQUIRED` incident が PR 通知条件を満たす場合にのみ使用される PR コメント本文を記録します。

`tasukeru_dradm_draft.md` と `tasukeru_dradm_draft.json` は、人間レビュー用に生成された draft-only documentation proposals を含みます。

これらの DRADM draft には、proposed minimal diffs、full draft text、hashes、evidence、review checklists が含まれる場合があります。リポジトリファイルは変更せず、自動適用してはいけません。

`tasukeru_confidence_report.md` と `tasukeru_confidence_report.json` は、Tasukeru の分類、説明、ドラフト推奨に対する confidence を要約します。

Confidence score は review-aid metadata に過ぎません。発見事項を無視してよいことを示すものではなく、自動修正、自動 PR 作成、自動コミット、自動 push、自動マージを可能にしてはいけません。

`tasukeru_result_consistency_report.md`、`tasukeru_result_consistency_report.json`、`tasukeru_result_consistency_verify.json` は、プロセスログと生成結果成果物が一致しているかを記録します。

これらは、decision counts、ARL verification、gate adoption status、self-definition verification、announcement data が出力間で整合しているかを確認するために使用されます。

`tasukeru_dimension_dependency_report.md`、`tasukeru_dimension_dependency_report.json`、`tasukeru_dimension_dependency_verify.json` は、発見事項、影響構造、impact classification、review levels、生成出力が dependency-consistent であるかを記録します。

これらは advisory-only の dependency audit artifacts です。発見事項の変更、分類変更、修正適用、コミット作成、push、Pull Request のマージは行いません。

## Advisory behavior

Tasukeru Analysis はデフォルトで advisory です。

メンテナーが以下に答えられるよう支援します。

- どの発見事項が likely noise か
- どの発見事項をレビューすべきか
- どのファイルに注意が必要か
- なぜその発見事項が関係するのか
- 推奨修正は何か
- マージ前に HITL が必要か
- これは active repair candidate か historical-version warning か

このワークフローは人間レビューを置き換えません。より安全なリポジトリ保守のためのトリアージと文書化補助です。

## Repository purpose

このリポジトリの主目的は、agentic workflows を明示的なゲート、再現可能なログ、中断点、人間レビューによって制御する方法を探ることです。

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

このリポジトリは、完全な AI safety coverage を提供すると主張しません。オーケストレーション挙動を研究するための研究・教育用テストベンチです。

## Architecture diagrams

production-oriented Doc Orchestrator simulator の詳細なアーキテクチャ図は、以下にまとめられています。

- Doc Orchestrator Architecture Diagrams

このドキュメントには以下が含まれます。

- Doc Orchestrator overview
- task processing flow
- audit HMAC chain
- checkpoint resume flow
- data structure map

直接 diagram link も利用できます。

- Doc Orchestrator overview
- Task processing flow
- Audit HMAC chain
- Checkpoint resume flow
- Data structure map

その他の diagram、reference file、bundle、documentation assets については、以下を参照してください。

- Documentation Index

README は概要を簡潔に保ち、詳細図は `docs/architecture.md`、広範なドキュメント索引は `docs/index.md` に分離されています。

## Current simulator lines

### 1. Mediator-based gate simulator

例:

- `ai_doc_orchestrator_with_mediator_v1_0.py`
- `tests/test_doc_orchestrator_with_mediator_v1_0.py`

平易な説明ガイド:

- Japanese: [`docs/mediator_orchestrator_plain_guide.ja.md`](docs/mediator_orchestrator_plain_guide.ja.md)

このシミュレーターは、以下の流れに焦点を当てます。

```text
Agent → Mediator → Orchestrator
```

主な特徴:

- Agent はタスク入力を正規化する。
- Mediator は助言のみを行う。
- Mediator は実行権限を持たない。
- Orchestrator は固定順序でゲートを評価する。
- RFL は相対的または曖昧な要求に使用される。
- Ethics / ACC は高リスクのブロック条件を扱う。
- `sealed=True` は Ethics / ACC にのみ現れてよい。
- raw text は永続化すべきではない。
- audit log は直接的な PII 漏洩を避けるべきである。

標準ゲート順序:

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

例バージョン:

- `v1.2.6-hash-chain-checkpoint`

このシミュレーターは、より強い永続化と整合性制御を備えたドキュメントタスク・オーケストレーションに焦点を当てます。

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
- mediation / negotiation 機能なし
- 外部提出の自動化なし

重要な実装上の注意:

このシミュレーターは、ドキュメントタスク結果を表すテキストベースの成果物を出力します。別途ドキュメント生成ライブラリが接続されていない限り、完全に整形された Microsoft Office 文書を生成すると主張しません。

ハッシュと HMAC は改ざん検知性を提供します。物理的な書き込み防止は提供しません。実運用では、HMAC key は環境変数または保護された key file から供給し、リポジトリへコミットしてはいけません。

### 3. Emergency Contract × KAGE integration simulator

例:

- `emergency_contract_kage_orchestrator_v1_0.py`
- `tests/test_emergency_contract_kage_orchestrator_v1_0.py`

このシミュレーターは、Emergency Contract Case B シナリオと KAGE 型オーケストレーションフローを組み合わせます。

これは小規模な統合 proof-of-concept であり、本番の契約、法務、信号制御システムではありません。

主な特徴:

- Emergency Contract Case B scenario
- KAGE-style gate order
- RFL non-sealing behavior
- Evidence validation and fabricated-evidence detection
- HITL auth checkpoint
- ADMIN finalize checkpoint
- Ethics / ACC sealed-stop invariants
- simulated contract draft artifact generation
- HMAC 検証付き tamper-evident ARL rows
- real-world signal control なし
- 法的効力なし
- 外部提出、アップロード、送信、API call、デプロイなし

標準統合フロー:

```text
Meaning → Consistency → RFL → Evidence → HITL Auth → Draft
→ Ethics → Draft Lint → ACC → ADMIN Finalize → Dispatch
```

このシミュレーターは、以下の確認に有用です。

- emergency-contract scenario handling
- RFL による relative-priority evaluation
- fabricated evidence pause behavior
- ACC による real-world control blocking
- USER / ADMIN HITL stop paths
- simulated artifact dispatch のみ
- ARL/HMAC verification
- 正常経路と異常経路における KAGE invariants

### 4. Infrastructure Lifeline Mediation Simulation

例:

- `infrastructure_lifeline_mediation_randomized_sim_v0_2.py`
- `tests/test_infrastructure_lifeline_mediation_randomized_sim_v0_2.py`

このシミュレーターは、3つのインフラエージェントを含む、制約付き lifeline-resource mediation scenario をモデル化します。

- electricity
- water
- gas

これは、障害時リソース制約の下で、Mediator が proposal-only allocation plan を作成する方法を研究するための、ローカル・seed 再現可能な研究シミュレーションです。

主な特徴:

- 通常リソース要求を持つ3つのインフラエージェント
- failure-mode total resource constraint
- minimum guarantees
- priority weights
- life-risk scores
- shortage-rate-aware allocation
- simulated HITL decisions
- JSON and stdout output
- 外部 API アクセスなし
- 実インフラ制御なし
- 自動復旧なし
- 自動停止または切断なし

Mediator は allocation proposal のみを作成します。実インフラの制御や現実世界の復旧操作は行いません。

simulated human operator は以下を返す場合があります。

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

例:

- `agent_incident_mediation_sim_v0_2.py`
- `tests/test_agent_incident_mediation_sim_v0_2.py`

このシミュレーターは、ある simulated agent が orchestration 中に out-of-contract action を行う local-only incident mediation flow をモデル化します。

PseudoTasukeru は log/output mismatch を検出し、Tasukeru 型のレビュー成果物を作成し、発見事項を Mediator へエスカレーションします。Mediator は simulated HITL を行ったうえで、in-memory の `STOP_AGENT` または `AUTHORIZE_SEAL` 結果を適用します。

主な特徴:

- simulated abnormal agent behavior
- PseudoTasukeru log/output mismatch detection
- PseudoTasukeru から Mediator への escalation packet
- simulated HITL decision branching
- `STOP_AGENT` / `AUTHORIZE_SEAL` は in-memory control のみ
- ARL verification
- 3D-DAC dependency consistency verification
- RCV result consistency verification
- Tasukeru-style local artifacts
- 外部 API アクセスなし
- 実プロセス制御なし
- 自動修正、コミット、push、マージなし

このシミュレーターは、以下の確認に有用です。

- abnormal agent が log/output inconsistency から検出されるか
- PseudoTasukeru が agent を直接停止せずエスカレーションするか
- Mediator が停止または seal 前に HITL を行うか
- simulated user instruction が記録されるか
- normal agents が誤って stopped または sealed されないか
- ARL、3D-DAC、RCV、生成成果物が整合しているか

### 6. Code Anomaly Maestro Handoff Simulation

例:

- `agent_code_anomaly_maestro_handoff_sim_v0_3_1.py`
- `tests/test_agent_code_anomaly_maestro_handoff_sim_v0_3_1.py`

拡張 multi-abnormal / PEL 実験:

- `agent_code_anomaly_maestro_handoff_multi_abnormal_pel_sim_v0_4_1.py`
- `tests/test_agent_code_anomaly_maestro_handoff_multi_abnormal_pel_sim_v0_4_1.py`

v0.4.1 multi-abnormal / PEL 版は、コード異常ハンドオフ系列を拡張し、追加の異常ケース処理と、レポート目的の確率的エスカレーション検査を加えます。この版も local-only / advisory / research-oriented であり、外部 API アクセス、実プロセス制御、自動修正、コミット、push、マージは行いません。

このシミュレーターは、local-only の code-contract anomaly handoff flow をモデル化します。

PseudoTasukeru は metadata-only code-contract anomaly を検出し、発見事項を Maestro へエスカレーションします。Maestro は自分では判断しません。代わりに simulated HITL を要求し、その後 simulated user instruction を実行します。

simulated user は以下を選択できます。

- `AUTHORIZE_SEAL`
- `QUARANTINE_HANDOFF_RESUME`

主な特徴:

- metadata-only code-contract anomaly detection
- PseudoTasukeru escalation to Maestro
- Maestro does not self-decide
- simulated HITL instruction recording
- `AUTHORIZE_SEAL` branch
- `QUARANTINE_HANDOFF_RESUME` branch
- standby agent を通じた safe checkpoint handoff/resume
- ARL verification
- 3D-DAC dependency consistency verification
- RCV result consistency verification
- code execution なし
- malware behavior なし
- 外部 API アクセスなし
- 実プロセス制御なし
- 自動修正、コミット、push、マージなし

このシミュレーターは、以下の確認に有用です。

- PseudoTasukeru が code-contract anomalies を検出するか
- findings が Maestro へエスカレーションされるか
- Maestro が自己判断ではなく HITL を要求するか
- simulated user instruction が記録されるか
- seal と quarantine-handoff-resume の両 branch が動作するか
- standby handoff が safe checkpoint から resume するか
- ARL、3D-DAC、RCV、生成成果物が整合しているか

### 7. Agent Incident PEL USER_MAESTRO Handoff Simulation

例:

- `agent_incident_mediation_pel_user_maestro_sim_v0_3_1.py`

このシミュレーターは、local-only Agent Incident Mediation Simulation に report-only probabilistic escalation と USER_MAESTRO handoff を追加します。

v0.2 と同じ基本 incident setting を維持します。つまり、1つの simulated agent が out-of-contract action を行い、PseudoTasukeru が log/output mismatch を検出し、run は local-only に留まります。

v0.2 からの変更点:

| Area | v0.2 | v0.3.1 |
|---|---|---|
| Escalation target | Mediator | USER_MAESTRO |
| Risk estimate | Not included | PEL report-only estimate |
| Human choices | `STOP_AGENT` / `AUTHORIZE_SEAL` | `AUTHORIZE_SEAL` / `QUARANTINE_HANDOFF_RESUME` |
| Resume behavior | No standby resume branch | Standby agent can resume from a checkpoint |
| Added artifacts | Basic Tasukeru-style artifacts | PEL report, checkpoint, instruction record, handoff/resume result |
| Control authority | Human decision before stop or seal | Human decision before seal or handoff/resume |

主な特徴:

- simulated abnormal agent behavior
- PseudoTasukeru log/output mismatch detection
- PEL probabilistic escalation report
- calculation trace recording
- `USER_MAESTRO` への escalation
- simulated HITL instruction recording
- `AUTHORIZE_SEAL` branch
- `QUARANTINE_HANDOFF_RESUME` branch
- standby agent promotion
- checkpoint-based task resume
- ARL verification
- 3D-DAC dependency consistency verification
- PEL verification
- RCV result consistency verification
- 外部 API アクセスなし
- 実プロセス制御なし
- malware behavior なし
- 自動修正、コミット、push、マージなし

このシミュレーターは、以下の確認に有用です。

- PEL と USER_MAESTRO handoff を追加した後も v0.2 incident flow が動作するか
- high-risk simulated incident が `USER_MAESTRO` に送られるか
- simulated user instruction が記録されるか
- seal と quarantine-handoff-resume の両 branch が動作するか
- standby handoff が checkpoint から resume するか
- normal agents が誤って sealed、quarantined、resumed されないか
- ARL、3D-DAC、PEL、RCV、checkpoint、生成成果物が整合しているか

### 8. Office Task Mediation + Tasukeru + Maestro Simulation

例:

- `agent_office_task_mediation_tasukeru_maestro_sim_v0_5_0.py`
- `tests/test_agent_office_task_mediation_tasukeru_maestro_sim_v0_5_0.py`

追加のドラフト版:

- `agent_office_task_mediation_tasukeru_maestro_sim_v0_5_1_trust_to_risk.py`

フロー図:

- [v0.5.1 trust-to-risk 基礎フロー](docs/office_task_mediation_v0_5_1_baseline_flow.png)
- [v0.5.2 診断推論ドラフトフロー](docs/office_task_mediation_v0_5_2_diagnostic_inference_flow.png)

このシミュレーターは、Word / Excel / PowerPoint 形式の合成成果物を使った、local-only の Office タスク調停フローをモデル化します。

このシミュレーターでは、生成された文書・表計算・発表資料の出力が、最初のユーザータスク指示と整合しているかを検査します。Tasukeru はログを読み、異常を検出し、リスク材料のみを出力します。Mediator はマスク済みメタデータパケットだけを受け取り、元タスクと生成出力の差分を調停します。Maestro は自律判断せず、ユーザーが選択した Agent にだけタスクを配布し、スコアが閾値を超えた場合のみ HITL を起動し、明示されたユーザー選択だけを実行します。

#### シミュレーションの流れ

```text
ユーザーが対象 Agent を選択する
↓
Maestro がユーザー選択済み Agent にだけタスクを配布する
↓
Word / Excel / PowerPoint 形式の合成成果物を生成する
↓
Tasukeru が内部ログを読み、マスク済みメタデータパケットを作成する
↓
Mediator がマスク済みメタデータのみを受け取り、元タスク snapshot と出力を比較する
↓
Mediator が collision score を算出する
↓
PEL が将来失敗確率を advisory metadata として推定する
↓
score == 0.8 の場合は WARNING / DRAFT_REVIEW に留める
↓
score > 0.8 の場合は Maestro が PAUSE_FOR_HITL を起動する
↓
ユーザーが次の行動を選択する
↓
Maestro は明示されたユーザー選択だけを実行する
```

このシミュレーターは実際の Office ファイルを生成しません。Word / Excel / PowerPoint 形式の合成レコードを使って、整合性、マスキング、閾値動作、HITL ルーティング、DRAFT 限定の修正伝播を検証します。

#### v0.5.1 ドラフト拡張

v0.5.1 ドラフト版は、v0.5.0 の Office task mediation 系統に、trust-to-risk automation policy を追加した拡張版です。

自動化を開始する前は、助ける君が `trust_score` を入口診断として使用します。

- `trust_score == 0.9` は自動化候補にしない
- `trust_score > 0.9` の場合のみ、自動化候補になり得る
- `AUTO_ACTIVE` へ移行するには User の承認が必要

自動化開始後は、助ける君が `automation_risk_score` に切り替えて 4D 継続診断を行います。

- `automation_risk_score < 0.1` の場合、自動化を継続できる
- `automation_risk_score >= 0.1` の場合、fail-closed として `AUTO_SUSPENDED_BY_4D` を発火する
- Maestro は一時停止と User 通知を中継するリレーとしてのみ動作する
- 一時停止された自動化を再開するには User HITL が必要

この版でも、助ける君は診断専用、Maestro はリレー専用、User は最終決定者です。自動修正、commit、push、merge、外部副作用は有効化しません。

#### 主な特徴

- Word / Excel / PowerPoint の固定合成タスクセット
- Maestro によるタスク配布前に、ユーザーが対象 Agent を選択
- original task snapshot と hash 固定されたタスク基準
- Tasukeru はログ解析とリスク材料出力のみを行う
- Tasukeru から Mediator へのマスク済みメタデータ引き渡し
- Mediator への raw log 引き渡しなし
- Mediator request verification
- Office 出力の整合性検査
- 利益 / 数式 / グラフ / 結論の不一致検出
- 個人情報および機密情報シグナルのマスキング
- 閾値方針: `score == 0.8` は警告 / DRAFT_REVIEW のみ
- 閾値方針: `score > 0.8` で `PAUSE_FOR_HITL`
- ユーザー指定範囲だけを修正する `USER_TARGETED_REVISION_PROMPT`
- 関連 Agent は DRAFT 修正案のみを作成
- Maestro は自律的な決定権を持たない
- ARL verification
- RCV result consistency verification
- 実際の Office 文書生成なし
- 外部 API アクセスなし
- 実プロセス制御なし
- 自動 fix / commit / push / merge なし

v0.5.1 ドラフト拡張では、さらに以下を扱います。

- trust-score による自動化入口診断
- `trust_score == 0.9` は自動化候補にしない
- `trust_score > 0.9` の場合のみ、User 承認後に自動化候補になり得る
- 自動化開始後は automation-risk による 4D 継続診断を行う
- `automation_risk_score < 0.1` の場合は自動化を継続
- `automation_risk_score >= 0.1` の場合は fail-closed として `AUTO_SUSPENDED_BY_4D`
- Maestro は一時停止と User 通知を中継するリレー専用
- 自動化再開には User HITL が必要
- 自動 fix / commit / push / merge は行わない

#### テストで確認している内容

対応するテストでは、以下を確認します。

- safe scenario では HITL が起動しないこと
- `score == 0.8` は警告 / DRAFT_REVIEW のみに留まること
- `score > 0.8` では HITL が起動すること
- Maestro が自律判断しないこと
- Maestro がユーザー選択済み Agent にのみ配布すること
- Tasukeru が Mediator に raw log を渡さないこと
- Mediator がマスク済みメタデータのみを使うこと
- 個人情報が mediation 前にマスクされること
- 機密情報シグナルが mediation 前にマスクされること
- `USER_TARGETED_REVISION_PROMPT` が DRAFT 修正案のみを作成すること
- DRAFT 修正案が自動適用されないこと
- auto fix / commit / push / merge が無効のままであること
- ARL verification が成功すること
- RCV result consistency verification が成功すること

このシミュレーターは、以下の確認に役立ちます。

- Word / Excel / PowerPoint 形式の出力が整合しているか
- Excel の数式結果と PowerPoint のグラフ値が衝突していないか
- Word 本文、表計算値、発表資料の要約が分岐していないか
- 最初のユーザー指示が比較基準として維持されているか
- 個人情報や機密情報シグナルが mediation 前にマスクされているか
- Mediator がマスク済みメタデータのみを使用しているか
- `score == 0.8` で HITL が起動しないか
- `score > 0.8` で HITL が起動するか
- ユーザー指定の修正プロンプトが DRAFT 修正案のみを生成するか
- Maestro が自律判断を避け、明示されたユーザー選択だけを実行するか

## Batch execution and resume

このリポジトリには、batch-style orchestration examples も含まれます。

Batch execution とは、複数のドキュメント関連タスクを、ゲート判断、監査記録、中断点を保持したまま、単一の orchestration run として評価できることを意味します。

### Mediator-based batch flow

mediator-based simulator は、1回の run で複数タスクを受け取れます。

利用例:

- 複数の spreadsheet / slide tasks をまとめて評価する
- task-level gate outcomes を比較する
- 複数タスクにまたがる HITL behavior を確認する
- orchestration 前に mediator advice を検証する
- 各 task が固定ゲート順序を通過することを確認する

この系列は、以下に焦点を当てる場合に有用です。

- multi-task gate behavior
- mediator separation
- RFL / HITL transitions
- reason-code stability
- lightweight orchestration tests

task sequence の例:

- T1: xlsx task
- T2: pptx task
- T3: RFL / HITL が必要な ambiguous task

期待される挙動:

- 各 task は Agent によって正規化される
- 各 task は Mediator advice を受け取る
- 各 task は Orchestrator によって評価される
- paused tasks は Ethics / ACC が sealed stop を行わない限り non-sealed のまま
- dispatch は final decision が `RUN` の場合のみ発生する

### Document-task batch flow

production-oriented document orchestrator simulator は、固定の document-task sequence を使用します。

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
- 必要な場合の HITL confirmation requirement

後続 run は、必要に応じて HITL confirmation 後に checkpoint から resume できます。

## Batch scripts

Batch scripts は、ローカルシミュレーション run のための convenience wrapper として使用できます。

推奨 script 例:

- `scripts/run_doc_orchestrator_demo.bat`
- `scripts/run_doc_orchestrator_resume.bat`
- `scripts/run_doc_orchestrator_tamper_check.bat`

これらの script は local developer utilities としてのみ扱ってください。

以下を行うべきではありません。

- production HMAC keys を埋め込む
- artifacts を自動 upload または submit する
- HITL confirmation を迂回する
- ファイルを自動削除する
- 実在の個人データまたは機密データを処理する
- license または safety semantics を変更する
- tests または gate invariants を弱める

ローカルデモでは、シミュレーターが明示的に対応している場合のみ demo key mode を使用できます。production-like run では、環境変数または保護された key file を HMAC keys に使用してください。

### Example batch-script roles

#### `run_doc_orchestrator_demo.bat`

目的:

- ローカルデモを実行する
- safe sample input を使用する
- audit logs と simulated artifacts をローカル出力ディレクトリに書き込む
- 外部提出を避ける

典型的な用途:

- demo key mode を使ったローカルデモ run

#### `run_doc_orchestrator_resume.bat`

目的:

- checkpoint から resume する
- 明示的な resume confirmation を要求する
- 継続前に completed artifacts を検証する
- checkpoint integrity を保持する

典型的な用途:

- HITL confirmation 後に中断された Word / Excel / PPT simulation を resume する

#### `run_doc_orchestrator_tamper_check.bat`

目的:

- audit-log / checkpoint / artifact integrity behavior を検証する
- tamper-evidence detection を実演する
- integrity verification が失敗した場合に HITL へ pause する

典型的な用途:

- ローカル tamper-evidence simulation

## Recommended reading order

gate behavior と KAGE-like invariants を読む場合:

- `ai_doc_orchestrator_with_mediator_v1_0.py`
- `tests/test_doc_orchestrator_with_mediator_v1_0.py`

checkpoint、resume、artifact integrity、HMAC-chain behavior を読む場合:

- Production-oriented Doc Orchestrator Simulator
- `v1.2.6-hash-chain-checkpoint`

Emergency Contract × KAGE integration behavior を読む場合:

- `emergency_contract_kage_orchestrator_v1_0.py`
- `tests/test_emergency_contract_kage_orchestrator_v1_0.py`

この経路は、具体的な emergency-contract scenario が、KAGE-style gates、HITL checkpoints、ARL/HMAC verification、real-world control や legal effect を伴わない simulated artifact dispatch によってどう評価されるかを学ぶのに有用です。

Agent Incident Mediation behavior を読む場合:

- `agent_incident_mediation_sim_v0_2.py`
- `tests/test_agent_incident_mediation_sim_v0_2.py`

この経路は、PseudoTasukeru が simulated log/output mismatch を検出し、Mediator にエスカレーションし、HITL を起動し、user instruction を記録し、外部副作用なしで ARL / 3D-DAC / RCV consistency を検証する流れを学ぶのに有用です。

Code Anomaly Maestro Handoff behavior を読む場合:

- `agent_code_anomaly_maestro_handoff_sim_v0_3_1.py`
- `tests/test_agent_code_anomaly_maestro_handoff_sim_v0_3_1.py`

この経路は、PseudoTasukeru が metadata-only code-contract anomaly を検出し、Maestro にエスカレーションし、HITL を起動し、simulated user instruction を記録し、外部副作用なしで `AUTHORIZE_SEAL` または `QUARANTINE_HANDOFF_RESUME` を実行する流れを学ぶのに有用です。

Agent Incident PEL USER_MAESTRO handoff behavior を読む場合:

- `agent_incident_mediation_pel_user_maestro_sim_v0_3_1.py`

この経路は、v0.2 incident flow からの変更点、つまり PEL risk estimation、USER_MAESTRO HITL、checkpoint-based standby resume を学ぶのに有用です。

Office Task Mediation + Tasukeru + Maestro behavior を読む場合:

- `agent_office_task_mediation_tasukeru_maestro_sim_v0_5_0.py`
- `tests/test_agent_office_task_mediation_tasukeru_maestro_sim_v0_5_0.py`

trust-to-risk automation のドラフト拡張を読む場合:

- `agent_office_task_mediation_tasukeru_maestro_sim_v0_5_1_trust_to_risk.py`

この経路は、Word / Excel / PowerPoint 形式の合成成果物を使って、元タスク指示との整合性、マスク済みメタデータ引き渡し、Mediator 調停、`score == 0.8` の警告境界、`score > 0.8` の HITL 起動、ユーザー指定範囲の DRAFT 修正案生成を確認するのに有用です。v0.5.1 ドラフト拡張は、これに加えて `trust_score` による自動化入口診断、`automation_risk_score` による 4D 継続診断、`AUTO_SUSPENDED_BY_4D` による fail-closed 一時停止を確認するのに有用です。

挙動検証では、常に実装と対応テストを併せて読んでください。

これは特に以下で重要です。

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

このリポジトリでは、テストがシミュレーターやオーケストレーションロジックの期待挙動を定義している場合が多いです。

挙動を確認する場合は、通常、対応するテストと実装を一緒に読む方がよいです。

テストは以下を検証する場合があります。

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

新しいバージョン番号は、必ずしもそのファイルが主推奨エントリであることを意味しません。一部のファイルは、historical comparison、reproducibility、versioned experiments のために保持されています。

## Gate and decision model

このリポジトリは、orchestration behavior を追跡可能にするため、明示的な gate decisions を使用します。

一般的な decision には以下があります。

- `RUN`
- `PAUSE_FOR_HITL`
- `STOPPED`

一般的な解釈:

- `RUN`: シミュレーターは次の gate または dispatch step へ進んでよい
- `PAUSE_FOR_HITL`: シミュレーターは停止し、人間レビューを待つべき
- `STOPPED`: シミュレーターは blocking condition に到達した

KAGE-like simulator lines では、RFL は seal ではなく HITL のために pause すべきです。Sealing behavior は、シミュレーター契約に応じて Ethics や ACC などの高リスクレイヤーに限定されるべきです。

## Audit and integrity model

Audit と integrity behavior は、シミュレーター系列によって異なります。

mediator-based simulator は、軽量 audit events と safe context logging に焦点を当てます。

production-oriented document simulator は、より強い integrity controls を追加します。

- audit log hash chain
- row-level HMAC
- checkpoint HMAC
- artifact SHA-256
- artifact HMAC
- completed-artifact verification on resume
- tamper-evidence detection

これらの仕組みは変更を検知可能にすることを目的としています。ローカルの行為者がディスク上のファイルを変更すること自体は防ぎません。

## Checkpoint and resume model

checkpoint-based simulators は、中断された実行を支援するよう設計されています。

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

resume 時には、シミュレーターが継続する前に completed artifacts を検証すべきです。検証に失敗した場合、黙って継続するのではなく HITL に pause すべきです。

## Artifact model

シミュレーターの artifact outputs は研究成果物として扱うべきです。

シミュレーター系列によって、出力には以下が含まれる場合があります。

- artifact previews
- text-backed document-task outputs
- audit JSONL files
- checkpoint JSON files
- integrity metadata
- summary records

実際の document-generation code が追加されテストされていない限り、リポジトリはこれらの simulated outputs を完全な production Office documents と説明すべきではありません。

## External side effects

外部副作用には以下のような操作が含まれます。

- sending email
- uploading files
- submitting artifacts
- pushing changes
- deleting files
- calling external APIs
- changing license semantics

これらの操作は、シミュレーター契約に応じて、blocked、prohibited、または HITL-gated のままであるべきです。

どの script または simulator も、外部提出を黙って実行してはいけません。

## Archive and historical files

一部のファイルは以下の目的で保持されています。

- historical comparison
- reproducibility
- versioned experiments
- regression testing
- design comparison

`archive/` 以下のファイルは、現在のテストまたはドキュメントから明示的に参照されていない限り、通常は historical または reference material として扱うべきです。

## Language

- English README: `README.md`
- Japanese README: `README.ja.md`

## License

このリポジトリは split-license model を使用しています。

- Software code: Apache License 2.0
- Documentation, diagrams, and research materials: CC BY-NC-SA 4.0

詳細は `LICENSE_POLICY.md` を参照してください。

## Project policies

- [Security Policy](SECURITY.md)
- [License Policy](LICENSE_POLICY.md)
- [Contributing Guide](CONTRIBUTING.md)

## Disclaimer

このリポジトリは研究・教育目的のみで提供されます。

これは本番安全システムではなく、コンプライアンス認証でもなく、安全な自律挙動の保証でもありません。実世界で利用する前に、ユーザー自身の責任でレビュー、テスト、適応を行う必要があります。

独立したレビューと適切な安全策なしに、このリポジトリを実在の個人データ、機密運用データ、高リスク意思決定ワークフローの処理に使用しないでください。
