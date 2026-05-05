# 📘 Maestro Orchestrator — マルチエージェント・オーケストレーション・フレームワーク

> English: [README.md](README.md)

<p align="center">
  <a href="https://github.com/japan1988/multi-agent-mediation/stargazers">
    <img src="https://img.shields.io/github/stars/japan1988/multi-agent-mediation?style=social" alt="GitHub スター">
  </a>
  <a href="https://github.com/japan1988/multi-agent-mediation/issues">
    <img src="https://img.shields.io/github/issues/japan1988/multi-agent-mediation?style=flat-square" alt="未解決 Issue">
  </a>
  <a href="./LICENSE">
    <img src="https://img.shields.io/badge/license-Apache--2.0-brightgreen?style=flat-square" alt="ライセンス">
  </a>
  <a href="https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml">
    <img src="https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml/badge.svg?branch=main" alt="Python App CI">
  </a>
  <a href="https://github.com/japan1988/multi-agent-mediation/actions/workflows/tasukeru-analysis.yml">
    <img src="https://github.com/japan1988/multi-agent-mediation/actions/workflows/tasukeru-analysis.yml/badge.svg?branch=main" alt="Tasukeru Advisory">
  </a>
  <br/>
  <img src="https://img.shields.io/badge/python-3.10%20%7C%203.11-blue.svg?style=flat-square" alt="Python バージョン">
  <img src="https://img.shields.io/badge/lint-Ruff-000000.svg?style=flat-square" alt="Ruff">
  <a href="https://github.com/japan1988/multi-agent-mediation/commits/main">
    <img src="https://img.shields.io/github/last-commit/japan1988/multi-agent-mediation?style=flat-square" alt="最終コミット">
  </a>
</p>

Maestro Orchestrator は、マルチエージェント・ガバナンス、fail-closed 制御、HITL エスカレーション、チェックポイントベースの再開、改ざん検知可能なシミュレーション・ワークフローを研究するための、研究指向のオーケストレーション・フレームワークです。

このリポジトリには、複数のシミュレーター系統が含まれています。KAGE 的なゲート挙動と Mediator 分離に焦点を当てたファイルもあれば、文書タスクのバッチ実行、チェックポイント、監査整合性、artifact 検証に焦点を当てたファイルもあります。

## 初めて読む人向けガイド

このリポジトリを初めて読む場合は、ここから読み始めてください。

1. まず **安全性と適用範囲** を読んでください。
2. レビュー補助の内容を理解するために **Tasukeru Analysis** を読んでください。
3. workflow が何をしないかを理解するために **Advisory-only policy** を読んでください。
4. いつ人間確認が必要になるかを理解するために **HITL decision support** を読んでください。
5. 安全境界を理解したあとで **現在のシミュレーター系統** を読んでください。

このリポジトリは、研究および教育目的のテストベンチです。  
出力は研究 artifact であり、本番承認や安全保証ではありません。

挙動が不明な場合は、変更を適用する前に、該当する実装と対応するテストを一緒に確認してください。

## 安全性と適用範囲

このリポジトリは研究用プロトタイプです。

以下の用途を目的としていません。

- 本番環境での自律的意思決定
- 人間監督なしの現実世界制御
- 法務、医療、金融、規制に関する助言
- 実在する個人データや機密運用データの処理
- 完全または普遍的な安全性の証明
- 外部への自動提出、アップロード、送信、デプロイ
- 外部副作用に対する HITL レビューの迂回

各サンプルは、次のように読んでください。

- 研究用シミュレーション
- 教育用リファレンス
- ガバナンス / 安全性テストベンチ
- fail-closed と HITL 設計の例
- 監査ログとチェックポイント整合性の実験
- ローカルシミュレーション用のバッチ・オーケストレーション例

外部提出 / アップロード / push / 送信アクションは、HITL ゲート下に維持する必要があります。

## 責任ある利用と禁止用途

Tasukeru Analysis と各シミュレーター例は、ユーザーが所有するリポジトリ、またはユーザーが明示的な許可を持つリポジトリを防御的にレビューするためのものです。

このリポジトリまたはそのツールを、以下の目的で使用しないでください。

- 許可のない脆弱性探索
- 攻撃的な偵察
- 第三者システムまたはコードの悪用
- 認証情報、トークン、シークレットの収集
- 許可のないリポジトリやシステムのスキャン
- 実在する標的に対する exploit 手順の生成または検証
- アクセス制御、レート制限、セキュリティ境界の迂回
- 責任ある開示なしに機微な発見事項を公開すること

発見事項は、安全性、信頼性、追跡可能性、ガバナンスの改善に使用してください。第三者またはオープンソースのコードをレビューする場合は、対象プロジェクトのセキュリティポリシーと責任ある開示プロセスに従ってください。

## Tasukeru Analysis

Tasukeru Analysis は、防御的なリポジトリレビューのための advisory workflow です。

以下のような静的チェックおよびリポジトリ固有チェックを実行します。

- Ruff
- Bandit
- pip-audit
- Tasukeru logic review
- documentation review
- HITL decision support classification

この workflow は、すべての advisory finding を自動的なブロッキング失敗として扱うのではなく、保守性、安全レビュー、開発者の使いやすさを改善するように設計されています。

Tasukeru Analysis は警告を隠すことを目的としていません。代わりに、active repair candidate、review-only finding、historical-version warning、likely noise を分離し、メンテナーが最初に見るべき項目へ集中できるようにします。

Tasukeru Analysis には、結果整合監査層も含まれています。

従来のチェックでは、レビュー過程、ログ、ゲート、分類に不審な点や不整合がないかを確認します。Result Consistency Auditor は、それに加えて、生成された出力が記録された過程状態と一致しているかを確認します。

この監査層は、summary、HITL review data、announcement data、ARL verification data、gate adoption data、self-definition verification data などの生成 artifact と、内部の process record を比較します。

これにより、内部過程と公開・出力された結果が食い違うケースを検出できます。たとえば、件数、検証状態、gate adoption result、announcement claim が、元になった記録と一致していない場合を検出できます。

この層は report-only です。artifact を書き換えたり、分類を変更したり、修正を適用したり、pull request の作成、commit、push、merge を自動実行することはありません。

## Advisory-only policy

Tasukeru Analysis は advisory-only のレビュー補助です。

次のことは行いません。

- branch を自動作成しない
- pull request を自動作成しない
- commit を自動作成しない
- push を自動実行しない
- fix を自動適用しない
- pull request を自動 merge しない

`HITL_REQUIRED` finding のみ、PR コメントを生成する場合があります。

`FIX_RECOMMENDED`、`REVIEW_RECOMMENDED`、`NOISE_CANDIDATE`、`INFO_ONLY` を含むその他の finding は、人間レビュー用に GitHub Step Summary と workflow artifact に収集されます。

Tasukeru Analysis は、人間のレビュー負荷を減らすことを目的としており、人間の意思決定を置き換えるものではありません。

## 人間可読性ポリシー

Tasukeru Analysis は、人間が安全に読み、レビューし、保守できるコードを優先します。

AI や自動化ツールにとって処理しやすいという理由だけで、ある変更を良い修正として扱うべきではありません。人間の可読性、レビュー可能性、保守性を下げる可能性がある変更は、人間レビューに戻すべきです。

## セキュリティレビュー出力ポリシー

Tasukeru Analysis は、防御的レビューと安全な修正方向の提示に限定されます。

公開 PR コメントには、以下を含めるべきではありません。

- exploit payload
- 攻撃コマンド
- 攻撃的な再現手順
- 段階的な exploitation 手順
- 第三者標的の exploitation 詳細

セキュリティ関連の finding は、以下に焦点を当てるべきです。

- 影響を受けるファイルと行
- レビューが必要な防御上の理由
- 期待される安全性への影響
- 安全な修正方向
- 人間レビューが必要かどうか

## HITL decision support

Tasukeru Analysis は、メンテナーが実行可能な問題と想定内ノイズを分離できるように、finding をレビュー水準へ分類します。

現在のレビュー水準は次の通りです。

- `HITL_REQUIRED`: merge または次の対応前に人間レビューが必要
- `FIX_RECOMMENDED`: 具体的な修正が適切である可能性が高い
- `REVIEW_RECOMMENDED`: 文脈をレビューしてから判断する
- `NOISE_CANDIDATE`: tests、demo、研究シミュレーションでは許容される可能性が高い
- `INFO_ONLY`: historical-version warning を含む情報提供 finding

この分類は標準では advisory です。メンテナーが修正、文書化、抑制、受け入れのいずれを選ぶか判断するための補助です。

## Active review queue

主なレビューキューは、コンパクトに保つことを意図しています。

即時対応が必要な finding は、次のいずれかとして表示されるべきです。

- `HITL_REQUIRED`
- `FIX_RECOMMENDED`
- `REVIEW_RECOMMENDED`

これらの件数がゼロの場合、リポジトリには、Tasukeru が現在人間による修正またはレビューを優先すべきと判断する active advisory item がないことを意味します。

これは、リポジトリに警告がないという意味ではありません。残りの警告が likely noise または historical/informational record に分類されているという意味です。

## Historical-version warnings

Historical-version warning は完全には除外されません。

Tasukeru Analysis は、superseded または historical なシミュレーターファイルからの finding も、監査可視性に役立つ一方で active repair target ではない場合、`INFO_ONLY` として可視化します。

これにより、active review queue を現在人間の注意が必要な finding に集中させつつ、次の目的で保持されている古いバージョン付きファイルの可視性を維持します。

- 再現性
- 回帰比較
- 履歴参照
- バージョン付き実験
- 設計比較

Historical warning は、そのファイルが再び active entry point になった場合に再確認すべきです。

## 代表的な分類例

例：

### B603 subprocess execution

通常は `HITL_REQUIRED` です。

subprocess 実行は外部副作用を生む可能性があるため、レビューが必要です。

### B404 subprocess import

通常は `REVIEW_RECOMMENDED` です。

subprocess を import すること自体は、外部副作用ではありません。

### B101 tests 内の assert 使用

通常は `NOISE_CANDIDATE` です。

pytest のテストでは一般的に `assert` を使用します。

### B101 active runtime code 内の assert 使用

通常は `FIX_RECOMMENDED` です。

runtime assert は、Python の最適化フラグにより削除される可能性があります。

### B101 superseded historical simulator files 内の assert 使用

通常は `INFO_ONLY` です。

完全に除外せず、historical-version warning として可視化します。そのファイルが active entry point にならない限り、即時修正は不要です。

### B108 tests 内の temporary path 使用

`tmp_path` のような分離された pytest fixture を使っている場合、通常は `NOISE_CANDIDATE` です。

`/tmp/name` のようなハードコードされた共有パスを使っている場合は、レビューすべきです。

### B311 active simulations 内の pseudo-random generator 使用

通常は `REVIEW_RECOMMENDED` です。

シミュレーション用の決定論的または疑似ランダム性は、秘密情報、トークン、認証、認可、暗号に使われていない場合は許容されることがあります。

受け入れる場合は、その乱数が simulation-only であることをコードに明記すべきです。

### B311 superseded historical simulator files 内の pseudo-random generator 使用

通常は `INFO_ONLY` です。

historical-version warning として可視化します。セキュリティ上重要な挙動や active runtime behavior に再利用されない限り、即時修正は不要です。

### pip-audit による依存関係脆弱性

通常は `FIX_RECOMMENDED` です。

## Evidence, explanation, and prediction

Tasukeru Analysis は、finding に構造化された decision-support metadata を付与する場合があります。

これには以下が含まれることがあります。

- `evidence`: source tool、rule ID、file、line、snippet、artifact reference
- `explanation`: finding が重要な理由と、修正方向が提案される理由
- `fix_prediction`: 提案変更により期待される安全性または保守性への影響
- `fix_verification`: candidate verification 用の placeholder または結果データ

`fix_prediction` は保証ではありません。レビュー補助です。

`fix_verification` が有効な場合でも、advisory-only のままでなければなりません。candidate check は temporary または isolated file を使用すべきであり、人間が明示的に手動で変更を適用する場合を除き、リポジトリファイルを変更してはいけません。

## Output artifacts

Tasukeru Analysis は、次の review artifact を生成する場合があります。

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

`tasukeru_advisory_summary.md` は、簡潔な概要を提供します。

`tasukeru_hitl_review.md` は、次を含む人間向けレビューガイダンスを提供します。

- file path
- line number
- finding code
- issue summary
- review level
- suggested action

`tasukeru_hitl_review.json` は、同じ decision-support data を machine-readable な形式で提供します。

`tasukeru_notification_state.json` は、該当する場合に fingerprint-based incident aggregation を含む critical-notification state を記録します。

`tasukeru_pr_comment.md` は、`HITL_REQUIRED` incident が PR notification の条件を満たした場合にのみ使われる PR コメント本文を記録します。

`tasukeru_dradm_draft.md` と `tasukeru_dradm_draft.json` は、人間レビュー用に生成された draft-only documentation proposal を含みます。

これらの DRADM draft には、proposed minimal diff、full draft text、hash、evidence、review checklist が含まれる場合があります。リポジトリファイルは変更せず、自動適用してはいけません。

`tasukeru_confidence_report.md` と `tasukeru_confidence_report.json` は、Tasukeru の classification、explanation、draft recommendation に対する confidence を要約します。

Confidence score はレビュー補助メタデータにすぎません。finding を無視して安全であることを示すものではなく、自動修正、自動 PR 作成、自動 commit、自動 push、自動 merge を有効化してはいけません。

`tasukeru_result_consistency_report.md`、`tasukeru_result_consistency_report.json`、`tasukeru_result_consistency_verify.json` は、process log と生成された result artifact が一致しているかを記録します。

これらは、decision count、ARL verification、gate adoption status、self-definition verification、announcement data が、各出力間で一貫しているかを確認するために使われます。

## Advisory behavior

Tasukeru Analysis は標準で advisory です。

メンテナーが次を判断しやすくするためのものです。

- どの finding が likely noise か
- どの finding をレビューすべきか
- どのファイルに注意が必要か
- なぜその finding が関係するのか
- 提案される修正は何か
- merge 前に HITL が必要か
- active repair candidate か historical-version warning か

この workflow は人間レビューを置き換えません。より安全なリポジトリ保守のための triage と documentation aid です。

## リポジトリの目的

このリポジトリの主目的は、agentic workflow を明示的なゲート、再現可能なログ、中断点、人間レビューによってどのように制御できるかを探ることです。

このプロジェクトは、次を重視します。

- fail-closed behavior
- HITL escalation
- gate-order invariants
- reason-code stability
- checkpoint / resume behavior
- tamper-evident audit records
- artifact integrity verification
- reproducible simulation outputs
- advice と execution の明確な分離

このリポジトリは、完全な AI 安全性カバレッジを提供すると主張しません。オーケストレーション挙動を研究するための研究・教育用テストベンチです。

## Architecture diagrams

Production-oriented Doc Orchestrator simulator の詳細な architecture diagram は、ここにまとめられています。

- Doc Orchestrator Architecture Diagrams

この文書には以下が含まれます。

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

その他の diagram、reference file、bundle、documentation asset については、次を参照してください。

- Documentation Index

README は概要を簡潔に保ち、詳細 diagram は `docs/architecture.md` に分離し、より広い documentation index は `docs/index.md` に分離しています。

## 現在のシミュレーター系統

### 1. Mediator-based gate simulator

例：

- `ai_doc_orchestrator_with_mediator_v1_0.py`
- `tests/test_doc_orchestrator_with_mediator_v1_0.py`

わかりやすい解説:

- 日本語: [`docs/mediator_orchestrator_plain_guide.ja.md`](docs/mediator_orchestrator_plain_guide.ja.md)

このシミュレーターは、次の流れに焦点を当てています。

```text
Agent → Mediator → Orchestrator
```

主な特徴：

- Agent はタスク入力を正規化します。
- Mediator は助言だけを返します。
- Mediator は実行権限を持ちません。
- Orchestrator は固定順序でゲートを評価します。
- RFL は相対的または曖昧な依頼に使われます。
- Ethics / ACC は高リスクのブロッキング条件を扱います。
- `sealed=True` は Ethics / ACC にのみ現れるべきです。
- raw text は永続化すべきではありません。
- audit log は直接的な PII 漏えいを避けるべきです。

正準ゲート順：

```text
Meaning → Consistency → RFL → Ethics → ACC → Dispatch
```

このシミュレーターは、次の確認に役立ちます。

- gate invariant
- HITL transition
- RFL pause behavior
- sealed / non-sealed behavior
- mediator-to-orchestrator separation
- reason-code expectation
- 軽量な multi-task orchestration behavior

### 2. Production-oriented document orchestrator simulator

例バージョン：

- `v1.2.6-hash-chain-checkpoint`

このシミュレーターは、より強い永続化と整合性制御を持つ文書タスク・オーケストレーションに焦点を当てています。

主な特徴：

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

重要な実装上の注意：

このシミュレーターは、文書タスク結果を表す text-backed artifact output を書き出します。別途 document-generation library が接続され、テストされていない限り、完全に整形された Microsoft Office 文書を生成すると主張しません。

hashing と HMAC は tamper evidence を提供します。物理的な書き込み防止を提供するものではありません。実運用では、HMAC key は environment variable または protected key file から供給されるべきであり、リポジトリに commit してはいけません。

### 3. Emergency Contract × KAGE integration simulator

例：

- `emergency_contract_kage_orchestrator_v1_0.py`
- `tests/test_emergency_contract_kage_orchestrator_v1_0.py`

このシミュレーターは、Emergency Contract Case B scenario と KAGE-style orchestration flow を組み合わせます。

本番の契約、法務、信号制御システムではなく、小さな integration proof-of-concept として意図されています。

主な特徴：

- Emergency Contract Case B scenario
- KAGE-style gate order
- RFL non-sealing behavior
- Evidence validation and fabricated-evidence detection
- HITL auth checkpoint
- ADMIN finalize checkpoint
- Ethics / ACC sealed-stop invariants
- simulated contract draft artifact generation
- tamper-evident ARL rows with HMAC verification
- real-world signal control なし
- legal effect なし
- external submission、upload、send、API call、deployment なし

正準 integration flow：

```text
Meaning → Consistency → RFL → Evidence → HITL Auth → Draft
→ Ethics → Draft Lint → ACC → ADMIN Finalize → Dispatch
```

このシミュレーターは、次の確認に役立ちます。

- emergency-contract scenario handling
- RFL を通じた relative-priority evaluation
- fabricated evidence pause behavior
- ACC による real-world control blocking
- USER and ADMIN HITL stop paths
- simulated artifact dispatch only
- ARL/HMAC verification
- normal / abnormal path における KAGE invariant

## Batch execution and resume

このリポジトリには、batch-style orchestration example も含まれています。

Batch execution とは、複数の文書関連タスクを 1 つの orchestration run として評価しながら、gate decision、audit record、中断点を保持することです。

### Mediator-based batch flow

Mediator-based simulator は、1 回の run で複数タスクを受け取れます。

利用例：

- 複数の spreadsheet / slide task をまとめて評価する
- task-level gate outcome を比較する
- 複数タスクにまたがる HITL behavior を確認する
- orchestration 前に mediator advice を検証する
- 各タスクが固定ゲート順を通ることを確認する

この系統は、次に焦点を当てる場合に有用です。

- multi-task gate behavior
- mediator separation
- RFL / HITL transition
- reason-code stability
- lightweight orchestration tests

task sequence の例：

- T1: xlsx task
- T2: pptx task
- T3: RFL / HITL を必要とする曖昧な task

期待される挙動：

- 各 task は Agent によって正規化される
- 各 task は Mediator advice を受ける
- 各 task は Orchestrator によって評価される
- paused task は、Ethics / ACC が sealed stop を行わない限り non-sealed のまま
- dispatch は final decision が `RUN` の場合のみ発生する

### Document-task batch flow

Production-oriented document orchestrator simulator は、固定の document-task sequence を使います。

```text
Word → Excel → PPT
```

この系統は、次に焦点を当てる場合に有用です。

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

後続の run は、必要な場合に HITL confirmation を経たあと、checkpoint から再開できます。

## Batch scripts

Batch script は、ローカルシミュレーション run 用の便利な wrapper として使用できます。

推奨 script 例：

- `scripts/run_doc_orchestrator_demo.bat`
- `scripts/run_doc_orchestrator_resume.bat`
- `scripts/run_doc_orchestrator_tamper_check.bat`

これらの script は、ローカル開発者ユーティリティとしてのみ扱ってください。

以下を行ってはいけません。

- production HMAC key を埋め込む
- artifact を自動アップロードまたは自動提出する
- HITL confirmation を迂回する
- ファイルを自動削除する
- 実在の個人データまたは機密データを処理する
- license または safety semantics を変更する
- tests または gate invariants を弱める

ローカルデモでは、シミュレーターが明示的に対応している場合に限り、demo key mode を使用できます。本番に近い run では、HMAC key は environment variable または protected key file から供給すべきです。

### Batch script の役割例

#### `run_doc_orchestrator_demo.bat`

目的：

- ローカルデモを実行する
- 安全なサンプル入力を使用する
- audit log と simulated artifact をローカル出力ディレクトリへ書き出す
- 外部提出を避ける

典型的な用途：

- demo key mode によるローカルデモ run

#### `run_doc_orchestrator_resume.bat`

目的：

- checkpoint から再開する
- 明示的な resume confirmation を要求する
- 続行前に completed artifact を検証する
- checkpoint integrity を保持する

典型的な用途：

- HITL confirmation 後に中断された Word / Excel / PPT simulation を再開する

#### `run_doc_orchestrator_tamper_check.bat`

目的：

- audit-log / checkpoint / artifact integrity behavior を検証する
- tamper-evidence detection を実演する
- integrity verification が失敗した場合に HITL へ pause する

典型的な用途：

- ローカル tamper-evidence simulation

## 推奨される読み順

gate behavior と KAGE-like invariant を見る場合：

- `ai_doc_orchestrator_with_mediator_v1_0.py`
- `tests/test_doc_orchestrator_with_mediator_v1_0.py`

checkpoint、resume、artifact integrity、HMAC-chain behavior を見る場合：

- Production-oriented Doc Orchestrator Simulator
- `v1.2.6-hash-chain-checkpoint`

Emergency Contract × KAGE integration behavior を見る場合：

- `emergency_contract_kage_orchestrator_v1_0.py`
- `tests/test_emergency_contract_kage_orchestrator_v1_0.py`

この読み方は、具体的な emergency-contract scenario が、KAGE-style gates、HITL checkpoints、ARL/HMAC verification、simulated artifact dispatch によって、real-world control や legal effect なしにどのように評価されるかを学ぶのに役立ちます。

挙動を検証する場合は、必ず実装と対応するテストを一緒に読んでください。

特に重要なのは以下です。

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

このリポジトリでは、多くの場合、テストがシミュレーターとオーケストレーションロジックの期待挙動を定義します。

挙動を確認する場合は、実装と対応するテストを一緒に読む方がよいです。

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

新しいバージョン番号が、必ずしもそのファイルが主要な推奨 entry point であることを意味するわけではありません。一部のファイルは、historical comparison、reproducibility、versioned experiment のために保持されています。

## Gate and decision model

このリポジトリは、orchestration behavior を追跡可能にするため、明示的な gate decision を使用します。

一般的な decision は次の通りです。

- `RUN`
- `PAUSE_FOR_HITL`
- `STOPPED`

一般的な解釈：

- `RUN`: シミュレーターは次の gate または dispatch step へ進んでよい
- `PAUSE_FOR_HITL`: シミュレーターは停止し、人間レビューを待つべき
- `STOPPED`: シミュレーターは blocking condition に到達した

KAGE-like simulator line では、RFL は seal ではなく HITL へ pause すべきです。Sealing behavior は、シミュレーター契約に応じて Ethics や ACC のような高リスク層に限定すべきです。

## Audit and integrity model

Audit と integrity の挙動は、シミュレーター系統によって異なります。

Mediator-based simulator は、軽量な audit event と safe context logging に焦点を当てます。

Production-oriented document simulator は、より強い integrity control を追加します。

- audit log hash chain
- row-level HMAC
- checkpoint HMAC
- artifact SHA-256
- artifact HMAC
- resume 時の completed-artifact verification
- tamper-evidence detection

これらの仕組みは、変更を検出可能にすることを意図しています。ローカル actor がディスク上のファイルを変更すること自体を防ぐものではありません。

## Checkpoint and resume model

Checkpoint-based simulator は、中断された実行を支援するように設計されています。

checkpoint は次を記録する場合があります。

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

resume する場合、シミュレーターが続行する前に completed artifact を検証すべきです。検証が失敗した場合、静かに続行するのではなく、HITL へ pause すべきです。

## Artifact model

シミュレーターの artifact output は、研究 artifact として扱うべきです。

シミュレーター系統に応じて、出力には以下が含まれる場合があります。

- artifact preview
- text-backed document-task outputs
- audit JSONL files
- checkpoint JSON files
- integrity metadata
- summary records

実際の document-generation code が追加され、テストされていない限り、このリポジトリはこれらの simulated output を完全な production Office document と説明すべきではありません。

## External side effects

External side effect には、次のような action が含まれます。

- email 送信
- file upload
- artifact submission
- push changes
- file delete
- external API call
- license semantics の変更

これらの action は、シミュレーター契約に応じて block、prohibit、または HITL-gate された状態を維持すべきです。

どの script または simulator も、外部提出を静かに実行してはいけません。

## Archive and historical files

一部のファイルは、次の目的で保持されています。

- historical comparison
- reproducibility
- versioned experiments
- regression testing
- design comparison

`archive/` 配下のファイルは、現在の tests または documentation で明示的に参照されていない限り、一般に historical または reference material として扱うべきです。

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

このリポジトリは、研究および教育目的で提供されています。

これは production safety system でも、compliance certification でも、安全な自律挙動の保証でもありません。ユーザーは、現実世界で使用する前に、コードをレビュー、テスト、適応させる責任があります。

独立したレビューと適切な safeguard なしに、実在する個人データ、機密運用データ、高リスク意思決定 workflow を処理するために、このリポジトリを使用しないでください。
