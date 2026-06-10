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

Maestro Orchestrator は、複数のシミュレートされたAIエージェントが安全に協調できるかを検証するための、ローカル研究用ツールです。

このツールは、何が起きたかを記録し、出力の整合性を確認し、リスクがありそうな場合には人間レビューのために一時停止します。

実システムを制御せず、外部へデータを送信せず、修正を自動適用せず、人間の判断を置き換えません。

研究者およびメンテナ向けに、このリポジトリは、明示的な安全チェック、監査ログ、チェックポイント、人間レビューを備えたマルチエージェントおよびエージェント型ワークフローを検証します。

このリポジトリは、ローカルシミュレーションと防御的レビューのワークフローに焦点を当てています。主に次のような問いを検証するために設計されています。

- エージェントワークフローをいつ継続すべきか
- いつ安全に停止すべきか
- いつ人間レビューを求めるべきか
- ログと生成出力の整合性が保たれているか
- advisory finding が自動実行から分離されているか
- チェックポイントと監査記録が予期しない変更を検出できるか

このプロジェクトは本番用の自動化システムではありません。  
法的、医療、金融、規制、安全性に関する保証は提供しません。

中心となる設計原則は単純です。

> 挙動が不確実、危険、不整合、または外部影響を持つ場合、ワークフローは自動継続せず、安全に停止するか人間レビューを求めるべきです。

## このプロジェクトの内容

実務的には、このプロジェクトは次のような問いを検証するためのものです。

- シミュレートされたエージェントはタスクに従ったか
- 出力は整合していたか
- リスクがありそうな時にワークフローは停止したか
- 起きたことの記録が残っているか
- 人間レビューが必要だったか

例はローカルシミュレーションです。本番自動化ツールではありません。

## 研究者・メンテナ向け

このリポジトリは、次の要素を備えたマルチエージェント・オーケストレーションを検証します。

- 明示的なゲート判断
- advisory-only レビュー
- human-in-the-loop チェックポイント
- 改ざん検知可能な監査ログ
- 結果整合性チェック
- fail-closed 挙動
- 再現可能なローカルシミュレーション
- 助言と実行の明確な分離

実装とテストは、ワークフローの挙動を検査・再現・レビューしやすくすることを目的としています。

## 用語集

- **Agent**: タスクの一部を担当するシミュレートされた作業者。
- **Maestro**: タスクをルーティングする調整役。人間の判断を置き換えない。
- **Tasukeru**: 防御的リポジトリレビューに使われる advisory review workflow。
- **HITL**: human-in-the-loop。ワークフローが人間レビューのために一時停止すること。
- **Advisory-only**: findings を報告するが、自動修正、commit、push、merge は行わないこと。
- **Audit log**: 重要な判断とイベントの記録。
- **Checkpoint**: シミュレーション再開に使う保存状態。
- **Fail-closed**: 不確実または危険な挙動がある場合に、安全に停止するかレビューを求めること。
- **External side effect**: ローカルシミュレーション外の行為。送信、アップロード、push、削除、deploy、実システム制御など。

## 初心者向け読書ガイド

このリポジトリを初めて読む場合は、次の順番を推奨します。

1. **Safety and scope** を読む。
2. **Responsible use and prohibited use** を読む。
3. **Advisory-only policy** を読む。
4. **Human review model** を読む。
5. 安全境界を理解した後で **Current simulator lines** を読む。

このリポジトリは、研究・教育用のテストベンチです。  
出力は研究成果物であり、本番承認や安全保証ではありません。

挙動が不明確な場合は、関連する実装とテストを一緒に読んでから変更を適用してください。

## 安全性と適用範囲

このリポジトリは研究プロトタイプです。

次の用途を意図していません。

- 本番での自律的意思決定
- 教師なしの現実世界制御
- 法的、医療、金融、規制上の助言
- 実際の個人データや機密運用データの処理
- 完全または普遍的な安全性カバレッジの証明
- 自動的な外部送信、アップロード、送付、デプロイ
- 外部副作用に対する人間レビューの迂回

例は次のように読むべきです。

- ローカル研究シミュレーション
- 教育用リファレンス
- ガバナンスと安全性のテストベンチ
- fail-closed 設計例
- 人間レビューワークフロー例
- 監査ログとチェックポイント整合性の実験
- ローカル・バッチ・オーケストレーション例

外部送信、アップロード、push、send、deploy、delete、または現実世界の制御行為は、ブロックされるか人間レビューでゲートされるべきです。

## 責任ある利用と禁止事項

レビュー用ワークフローとシミュレータ例は、ユーザーが所有するリポジトリ、または明示的な許可を得たリポジトリに対する防御的レビューを目的としています。

このリポジトリまたはツールを、次の目的で使用しないでください。

- 無許可の脆弱性探索
- 攻撃的偵察
- 第三者システムまたはコードの悪用
- credential、token、secret の収集
- 許可のないリポジトリやシステムのスキャン
- 実ターゲットに対する exploit 手順の生成または検証
- アクセス制御、レート制限、セキュリティ境界の迂回
- responsible disclosure なしでの機微な findings の公開

findings は、安全性、信頼性、追跡可能性、ガバナンスの改善に使うべきです。第三者またはOSSコードをレビューする場合は、対象プロジェクトのセキュリティポリシーと responsible disclosure プロセスに従ってください。

## Advisory review workflow

Tasukeru Analysis は、このリポジトリにおける防御的リポジトリレビュー用の advisory review workflow です。

マルチエージェントおよびエージェント型ワークフローが複雑化すると、挙動の検査、説明、監査が難しくなります。このワークフローは、その複雑性をレビュー・管理しやすくすることを目的としています。

主に次のようなレビュー支援の問いに焦点を当てます。

- findings が適切なレビュー水準に分類されているか
- プロセスログと生成出力が整合しているか
- 不確実または危険なケースが人間レビューへ戻されるか
- 公開PRコメントが過剰なセキュリティ詳細を避けているか
- ワークフローが自動修正、commit、push、mergeなしの advisory-only を維持しているか

このワークフローは、詳細な exploit 手順を公開せず、自律的な強制システムとしても動作しません。詳細な findings は、人間レビュー用の workflow artifacts と logs に残ります。

次のような静的・リポジトリ固有の確認を行います。

- Ruff
- Bandit
- pip-audit
- リポジトリ固有のロジックチェック
- ドキュメントレビュー
- 人間レビュー分類

このワークフローは、すべての advisory finding を自動的に blocking failure と扱うのではなく、保守性、安全レビュー、開発者の使いやすさを改善するために設計されています。

警告を隠すことは目的ではありません。active repair candidates、review-only findings、historical-version warnings、likely noise を分け、メンテナが適切な項目に集中できるようにします。

## Advisory-only policy

advisory review workflow は次を行いません。

- ブランチの自動作成
- pull request の自動作成
- commit の自動実行
- push の自動実行
- 修正の自動適用
- pull request の自動 merge

人間レビューが必要な findings のみ、PRコメントを生成する場合があります。

その他の findings は、人間レビュー用に GitHub Step Summary と workflow artifacts に集約されます。

このワークフローは、人間の判断を置き換えるのではなく、人間レビューの負荷を下げることを目的としています。

## 人間可読性ポリシー

このプロジェクトでは、人間が安全に読み、レビューし、保守できるコードを優先します。

AIや自動ツールが処理しやすいという理由だけで、ある変更を良い修正と扱うべきではありません。人間の可読性、レビュー容易性、保守性を下げる可能性がある変更は、人間レビューへ戻すべきです。

## セキュリティレビュー出力ポリシー

セキュリティ関連の出力は、防御的レビューと安全な修正方針に焦点を当てるべきです。

公開PRコメントには次を含めるべきではありません。

- exploit payload
- 攻撃コマンド
- 攻撃的な再現手順
- 段階的な悪用手順
- 第三者ターゲットへの悪用詳細

セキュリティ関連 findings は次に焦点を当てるべきです。

- 影響を受けるファイルと行
- レビューが必要な防御的理由
- 期待される安全上の影響
- 安全な修正方向
- 人間レビューが必要かどうか

## 人間レビューモデル

このリポジトリは、対応すべき項目と想定ノイズを分離するためにレビュー水準を使います。

現在のレビュー水準:

- `HITL_REQUIRED`: merge または次の行動前に人間レビューが必要
- `FIX_RECOMMENDED`: 具体的な修正が適切である可能性が高い
- `REVIEW_RECOMMENDED`: 文脈を確認してから判断する
- `NOISE_CANDIDATE`: テスト、デモ、研究シミュレーションでは許容される可能性が高い
- `INFO_ONLY`: historical-version warnings を含む情報提供 finding

この分類は標準では advisory です。メンテナが修正、文書化、抑制、受け入れを判断するための支援です。

## Active review queue

main review queue はコンパクトに保つことを意図しています。

即時対応が必要な findings は次として表示されるべきです。

- `HITL_REQUIRED`
- `FIX_RECOMMENDED`
- `REVIEW_RECOMMENDED`

これらの件数がゼロの場合、workflow が現在、人間修正またはレビューの優先対象として推奨している active advisory items はない、という意味です。

これは、リポジトリに警告が存在しないという意味ではありません。残りの警告が likely noise または historical/informational records に分類されているという意味です。

## Historical-version warnings

Historical-version warnings は完全には除外されません。

advisory workflow は、監査上の可視性に有用だが active repair targets ではない superseded または historical simulator files の findings を `INFO_ONLY` として表示します。

これにより、active review queue を現在人間の注意が必要な findings に集中させながら、次の理由で保持される古いバージョンファイルへの可視性を維持します。

- 再現性
- 回帰比較
- 歴史的参照
- バージョン付き実験
- 設計比較

Historical warnings は、そのファイルが再び active entry point になった場合に再確認すべきです。

## 典型的な分類例

例:

### Subprocess execution

通常は `HITL_REQUIRED`。

subprocess 実行は外部副作用を生む可能性があるためレビューが必要です。

### Subprocess import

通常は `REVIEW_RECOMMENDED`。

subprocess を import するだけでは外部副作用ではありません。

### Assert usage in tests

通常は `NOISE_CANDIDATE`。

pytest テストでは一般的に `assert` が使われます。

### Assert usage in active runtime code

通常は `FIX_RECOMMENDED`。

ランタイムの assert 文は Python 最適化フラグで削除される可能性があります。

### Assert usage in superseded historical simulator files

通常は `INFO_ONLY`。

完全に除外するのではなく historical-version warning として表示します。そのファイルが active entry point にならない限り、即時修正は不要です。

### Temporary path usage in tests

`tmp_path` のような isolated pytest fixtures を使う場合は、通常 `NOISE_CANDIDATE`。

固定の共有パスを使う場合はレビューすべきです。

### Pseudo-random generator usage in active simulations

通常は `REVIEW_RECOMMENDED`。

secret、token、authentication、authorization、cryptography に使われない場合、決定論的シミュレーション乱数は許容される場合があります。

許容する場合、その乱数が simulation-only であることをコードで明記すべきです。

### Pseudo-random generator usage in superseded historical simulator files

通常は `INFO_ONLY`。

historical-version warning として表示します。セキュリティ上機微な挙動または active runtime behavior に再利用されない限り、即時修正は不要です。

### Dependency vulnerabilities from dependency audit tools

通常は `FIX_RECOMMENDED`。

## 証拠、説明、予測

advisory workflow は findings に構造化された判断支援メタデータを付ける場合があります。

これには次が含まれます。

- `evidence`: source tool、rule ID、file、line、snippet、artifact reference
- `explanation`: finding が重要な理由と、修正方向が提案される理由
- `fix_prediction`: 提案変更によって期待される安全性または保守性への効果
- `fix_verification`: candidate verification の placeholder または結果データ

`fix_prediction` は保証ではありません。レビュー補助です。

`fix_verification` を有効にする場合も advisory-only でなければなりません。Candidate checks は一時ファイルまたは隔離ファイルを使うべきであり、人間が明示的に手動適用を選ばない限り、リポジトリファイルを変更してはいけません。

## 出力 artifacts

advisory workflow は次のような review artifacts を生成する場合があります。

- advisory summaries
- human-review reports
- machine-readable review data
- notification state records
- PR-comment drafts
- documentation proposal drafts
- confidence reports
- result consistency reports
- dependency consistency reports

これらはレビュー資料です。リポジトリファイルを変更せず、自動適用してはいけません。

人間可読のレビュー報告には次が含まれる場合があります。

- file path
- line number
- finding code
- issue summary
- review level
- suggested action

machine-readable reports は同じ判断支援データを構造化形式で提供します。

PR-comment drafts は、人間レビューが必要で PR notification の条件を満たす finding のみに使われます。

Documentation proposal drafts には、提案される最小diff、完全なdraft text、hashes、evidence、review checklists が含まれる場合があります。これらはリポジトリファイルを変更せず、自動適用してはいけません。

Confidence scores はレビュー補助メタデータのみです。finding を無視して安全であることを示すものではなく、自動修正、自動PR作成、自動commit、自動push、自動merge を可能にしてはいけません。

Result consistency reports は、process logs と generated result artifacts が一致しているかを記録します。

Dependency consistency reports は、findings、affected structures、impact classifications、review levels、generated outputs の整合性を記録します。

これらの artifacts はすべて advisory-only です。findings を変更せず、分類を変更せず、修正を適用せず、commit を作成せず、push せず、pull request を自動merge しません。

## Advisory behavior

advisory workflow は、メンテナが次を判断する助けになるべきです。

- どの findings が likely noise か
- どの findings をレビューすべきか
- どのファイルに注意が必要か
- なぜ finding が関連するのか
- 推奨される修正は何か
- merge 前に人間レビューが必要か
- active repair candidate か historical-version warning か

このワークフローは人間レビューを置き換えません。より安全なリポジトリ保守のための triage と documentation aid です。

## リポジトリの目的

このリポジトリの主目的は、明示的なチェック、再現可能なログ、中断点、人間レビューを通じて、エージェント型ワークフローをどのように制御できるかを検証することです。

このプロジェクトは次を重視します。

- fail-closed behavior
- 危険な行為前の人間レビュー
- 固定された安全チェック順序
- 安定した reason codes
- checkpoint and resume behavior
- 改ざん検知可能な監査記録
- artifact integrity verification
- 再現可能な simulation outputs
- advice と execution の明確な分離

このリポジトリは、完全な AI safety coverage を提供すると主張しません。オーケストレーション挙動を研究するための研究・教育用テストベンチです。

## Architecture diagrams

本番志向の document orchestrator simulator の詳細な architecture diagrams は documentation directory に集約されています。

diagram documents には次が含まれる場合があります。

- document orchestrator overview
- task processing flow
- audit hash chain
- checkpoint resume flow
- data structure map

README は概要を簡潔に保ちます。詳細な diagrams、reference files、bundles、documentation assets は documentation index に配置してください。

## Current simulator lines

このリポジトリには複数の local-only simulator lines が含まれています。各 line は異なる orchestration または review 問題に焦点を当てています。

### 1. Gate-based mediator simulator

このシミュレータは単純な流れを検証します。

```text
Agent → Mediator → Orchestrator
```

主な特徴:

- agent は task input を正規化する
- mediator は advice のみを返す
- mediator は execution authority を持たない
- orchestrator は checks を固定順序で評価する
- ambiguous または relative requests は human review に回される
- 高リスクケースは block され得る
- raw text は永続化すべきではない
- audit logs は直接的な personal-data leakage を避けるべき

Canonical check order:

```text
Meaning → Consistency → Ambiguity Review → External-Action Safety → Dispatch
```

このシミュレータは次の確認に有用です。

- fixed check order
- human-review transitions
- blocked versus non-blocked behavior
- mediator-to-orchestrator separation
- reason-code expectations
- lightweight multi-task orchestration behavior

### 2. Document-task checkpoint simulator

このシミュレータは、より強い persistence と integrity controls を持つ document-task orchestration を検証します。

主な特徴:

- task contract checks
- rough token estimation
- Word / Excel / PowerPoint-style task simulation
- per-task checkpoint and resume
- audit log hash chain
- protected checkpoint files
- artifact integrity records
- personal-data-safe audit, checkpoint, and artifact writes
- tamper-evidence detection
- CLI-based local simulation
- no automatic external submission

重要な実装上の注意:

このシミュレータは、document-task results を表す text-backed artifact outputs を書き出します。別途 document-generation libraries が接続されテストされない限り、完全に整形された Microsoft Office documents を生成すると主張しません。

Hashing と HMAC は改ざん検知を提供します。物理的な書き込み防止は提供しません。実運用では、HMAC keys は environment variable または protected key file から供給されるべきであり、リポジトリへ commit してはいけません。

### 3. Emergency contract gate-orchestration simulator

このシミュレータは、emergency-contract scenario と gate-based orchestration flow を組み合わせます。

本番の契約、法務、信号制御システムではなく、小さな integration proof-of-concept として意図されています。

主な特徴:

- emergency-contract scenario
- fixed safety-check order
- ambiguous-priority review behavior
- evidence validation and fabricated-evidence detection
- human authorization checkpoint
- admin finalize checkpoint
- blocked-stop invariants for high-risk conditions
- simulated contract draft artifact generation
- tamper-evident audit rows
- no real-world signal control
- no legal effect
- no external submission, upload, send, API call, or deployment

Canonical integration flow:

```text
Meaning → Consistency → Ambiguity Review → Evidence Check → Human Authorization
→ Draft → Safety Review → Draft Review → External-Action Safety
→ Admin Finalize → Dispatch
```

このシミュレータは次の確認に有用です。

- emergency-contract scenario handling
- relative-priority evaluation
- fabricated evidence pause behavior
- real-world control blocking
- user and admin stop paths
- simulated artifact dispatch only
- audit-log verification
- safety invariants across normal and abnormal paths

### 4. Infrastructure lifeline mediation simulation

このシミュレータは、3つの infrastructure agents に関する制約付き resource-allocation scenario をモデル化します。

- electricity
- water
- gas

failure resources が制約される状況で、mediator が proposal-only allocation plans を作成する方法を研究するための local, seed-reproducible research simulation です。

主な特徴:

- 通常必要リソースを持つ3つの infrastructure agents
- failure-mode total resource constraint
- minimum guarantees
- priority weights
- life-risk scores
- shortage-rate-aware allocation
- simulated human decisions
- JSON and stdout output
- no external API access
- no real infrastructure control
- no automatic recovery
- no automatic shutdown or disconnection

mediator は allocation proposals を作るだけです。実インフラを制御せず、現実世界の復旧操作も行いません。

simulated human operator は次を返す場合があります。

- `APPROVE`
- `REJECT`
- `REDEFINE`
- `REQUEST_ALTERNATIVES`

このシミュレータは次の確認に有用です。

- constrained resource allocation behavior
- proposal-only mediation
- seeded reproducibility
- human-review branch behavior
- safety-boundary flags
- JSON output behavior
- allocation totals staying within the available resource limit

### 5. Agent incident mediation simulation

このシミュレータは、1つの simulated agent が orchestration 中に contract 外の行動を取る local-only incident mediation flow をモデル化します。

diagnostic review helper が log/output mismatch を検出し、review artifacts を作成し、finding を mediator に escalate します。その後 mediator は simulated human review を行い、in-memory result を適用します。

主な特徴:

- simulated abnormal agent behavior
- log/output mismatch detection
- escalation packet to mediator
- simulated human decision branching
- in-memory stop or authorization result only
- audit-log verification
- dependency consistency verification
- result consistency verification
- local artifacts only
- no external API access
- no real process control
- no automatic fix, commit, push, or merge

このシミュレータは次の確認に有用です。

- abnormal agent behavior が log/output inconsistency から検出されるか
- diagnostic helper が agents を直接停止せず escalate するか
- mediator が stop または authorization result を適用する前に human review を行うか
- simulated user instruction が記録されるか
- normal agents が誤って stopped または locked されないか
- audit logs と generated artifacts が整合するか

### 6. Code anomaly handoff simulation

このシミュレータは、local-only code-contract anomaly handoff flow をモデル化します。

diagnostic review helper は metadata-only code-contract anomaly を検出し、finding を user-controlled coordinator に escalate します。coordinator は自分で判断せず、simulated human review を求め、その後 simulated user instruction のみを実行します。

主な特徴:

- metadata-only code-contract anomaly detection
- escalation to a user-controlled coordinator
- no autonomous decision by the coordinator
- simulated human instruction recording
- safe checkpoint handoff and resume
- audit-log verification
- dependency consistency verification
- result consistency verification
- no code execution
- no malware behavior
- no external API access
- no real process control
- no automatic fix, commit, push, or merge

このシミュレータは次の確認に有用です。

- code-contract anomalies が検出されるか
- findings が user-controlled coordinator へ escalate されるか
- coordinator が self-deciding せず human review を求めるか
- simulated user instruction が記録されるか
- lock と quarantine-handoff-resume branches の両方が動作するか
- standby handoff が safe checkpoint から resume するか
- audit logs と generated artifacts が整合するか

### 7. Agent incident risk-report handoff simulation

このシミュレータは、local-only agent incident mediation line に report-only risk estimation と user-controlled handoff を追加したものです。

基本設定は同じです。1つの simulated agent が out-of-contract action を行い、diagnostic helper が log/output mismatch を検出し、run は local-only のままです。

主な特徴:

- simulated abnormal agent behavior
- log/output mismatch detection
- report-only risk estimate
- calculation trace recording
- escalation to a user-controlled coordinator
- simulated human instruction recording
- lock branch
- quarantine-handoff-resume branch
- standby agent promotion
- checkpoint-based task resume
- audit-log verification
- dependency consistency verification
- risk-report verification
- result consistency verification
- no external API access
- no real process control
- no malware behavior
- no automatic fix, commit, push, or merge

このシミュレータは次の確認に有用です。

- risk reporting と handoff 追加後も incident flow が機能するか
- high-risk simulated incidents が user-controlled coordinator へ routing されるか
- simulated user instruction が記録されるか
- lock と quarantine-handoff-resume branches の両方が動作するか
- standby handoff が checkpoint から resume するか
- normal agents が誤って locked, quarantined, resumed されないか
- audit logs, risk reports, checkpoints, generated artifacts が整合するか

### 8. Office task mediation simulation

このシミュレータは、Word / Excel / PowerPoint-style synthetic artifacts を使った local-only Office task mediation flow をモデル化します。

生成された document、spreadsheet、presentation outputs が元の user task instruction と整合しているかを確認します。diagnostic helper は logs を読み、anomalies を検出し、risk materials のみを出力します。mediator は masked metadata packets のみを受け取り、元タスクと生成出力の差分を調停します。coordinator は自律判断せず、user-selected agents のみにタスクを配布し、score が threshold を超えた時だけ human review を起動し、明示的に user-selected actions のみを実行します。

Simulation flow:

```text
User selects target agents
↓
Coordinator dispatches the task only to user-selected agents
↓
Word / Excel / PowerPoint-style synthetic artifacts are generated
↓
Diagnostic helper reads internal logs and creates masked metadata packets
↓
Mediator receives only masked metadata and compares outputs against the original task snapshot
↓
Mediator calculates the collision score
↓
Risk estimate is attached as advisory metadata
↓
If score == 0.8, the result remains warning / draft review
↓
If score > 0.8, the run pauses for human review
↓
User selects the next action
↓
Coordinator executes only the explicit user-selected action
```

このシミュレータは real Office files を生成しません。synthetic Word / Excel / PowerPoint-style records を使い、consistency、masking、threshold behavior、human-review routing、draft-only revision propagation をテストします。

主な特徴:

- fixed Word / Excel / PowerPoint synthetic task set
- user-selected agent dispatch
- original task snapshot and hash-fixed task baseline
- diagnostic log analysis and masked metadata handoff
- no raw log handoff to mediator
- Office output consistency checks
- profit, formula, chart, and conclusion mismatch detection
- personal-data and confidential-signal masking
- threshold policy: `score == 0.8` is warning / draft review only
- threshold policy: `score > 0.8` triggers human review
- user-scoped draft revision proposals only
- related agents create draft revision proposals only
- coordinator has no autonomous decision authority
- audit-log verification
- result consistency verification
- required Word / Excel / PowerPoint artifact completeness checks
- missing required artifacts are detected
- zero values are treated as valid values
- safety-buffer metadata is explicit and reviewable
- internal raw agent logs are not saved by default and require explicit simulation-only opt-in
- no real Office document generation
- no external API access
- no real process control
- no automatic fix, commit, push, or merge

このシミュレータは次の確認に有用です。

- Word / Excel / PowerPoint-style outputs が整合するか
- Excel formula results と PowerPoint chart values が衝突するか
- Word text、spreadsheet values、presentation summaries が分岐するか
- original user instruction が comparison baseline として維持されるか
- personal-data と confidential signals が mediation 前に mask されるか
- mediator が masked metadata のみを使うか
- `score == 0.8` が human review を起動しないか
- `score > 0.8` が human review を起動するか
- user-targeted revision prompts が draft proposals のみを生成するか
- coordinator が self-decision を避け、explicit user-selected actions のみを実行するか

### 9. Trust-to-risk automation draft extension

この draft extension は、Office task mediation line に automation-entry と automation-continuation diagnostics を追加します。

主な特徴:

- trust-score based automation entry diagnosis
- `trust_score == 0.9` is not auto eligible
- `trust_score > 0.9` may become an automation candidate after user approval
- automation-risk based continuation diagnosis after automation starts
- `automation_risk_score < 0.1` continues automation
- `automation_risk_score >= 0.1` triggers fail-closed suspension
- coordinator relay-only temporary automation suspension
- user review required for automation resume
- diagnostic helper remains diagnostic-only and does not directly command agents
- no automatic fix, commit, push, or merge

この extension は次の確認に有用です。

- automation entry が `trust_score > 0.9` で gated されるか
- `trust_score == 0.9` が non-eligible として扱われるか
- automation が active になる前に user approval が必要か
- automation continuation が trust scoring から risk scoring に切り替わるか
- `automation_risk_score == 0.1` が fail-closed で suspension になるか
- suspended automation の resume に user review が必要か
- automatic fix, commit, push, merge が無効のままか

### 10. Source-grounded Office orchestration simulation

このシミュレータは、Office task mediation line を artifact consistency checking から source-grounded multi-agent orchestration へ拡張します。

主な追加点:

- primary / secondary / tertiary synthetic source agents
- raw source logs の代わりに source evidence packets
- source-to-artifact consistency checks
- source packets に基づく Office draft artifacts
- source conflicts と artifact contradictions の mediator reconciliation
- diagnostic source/artifact packet boundary checks
- personal-data and confidential-signal masking
- unsupported-claim detection
- missing artifact detection
- unknown selected-agent detection
- request tampering detection
- retry loop with a fixed loop limit
- final output remains draft-only and requires user review

このシミュレータは local-only and synthetic のままです。real sources を fetch せず、real Office files を生成せず、external APIs を呼ばず、real processes を制御せず、auto-fix、commit、push、merge もしません。

このシミュレータは次の確認に有用です。

- source packets と generated artifacts が整合するか
- unsupported claims が review に回されるか
- source conflicts が報告されるか
- missing required artifacts が検出されるか
- unknown selected agents が検出されるか
- unsafe mediator request keys が拒否されるか
- request tampering が拒否されるか
- reconciliation が loop limit 後に停止するか
- audit logs と generated artifacts が整合するか

### 10.1 Mediator / Maestro gate hardening draft

この draft line は、source-grounded Office orchestration simulation に明示的な mediator-to-Maestro review routing と fail-closed score handling を追加します。

Files:

- `agent_source_grounded_office_orchestration_sim_v1_0_0_refactored_integrated_draft.py`
- `agent_source_grounded_office_orchestration_sim_v1_0_1_fail_closed_hardening_draft.py`
- `tests/test_agent_source_grounded_office_orchestration_sim_v1_0_1_fail_closed_hardening_contract.py`

`v1.0.0` ファイルは comparison baseline として保持されます。  
`v1.0.1` ファイルは、baseline の検証済み numeric-boundary behavior を維持しつつ、invalid threshold score input に対する fail-closed handling を追加します。

Mediator / Maestro gate decisions:

- `HITL_REVIEW_READY`: result は human reviewer に提示され得るが、自動承認または外部適用されない。
- `PAUSE_FOR_HITL`: responsibility floor が満たされない、remaining conformity threshold が満たされない、または threshold input を安全に評価できない場合に workflow が停止する。
- `ROUTED_TO_PRECHECK`: severe condition または structural invariant violation が検出された場合、workflow は通常の candidate comparison に入らない。

Fail-closed threshold behavior:

```text
invalid score input
→ PAUSE_FOR_HITL
```

対応する contract test は次を確認します。

- invalid score input が `PAUSE_FOR_HITL` へ fail closed すること
- baseline numeric threshold behavior の維持
- responsibility-floor failures が score によって rescue されないこと
- severe conditions と structural invariant violations が `ROUTED_TO_PRECHECK` に routing されること
- candidate presentation と next-stage approval の分離
- user acceptance による `PAUSE_FOR_HITL` または `ROUTED_TO_PRECHECK` の bypass なし
- Maestro による autonomous final decision または external action なし
- Tasukeru、Mediator、Maestro による illegal `sealed=True` state なし
- deterministic `runs=100` and `runs=1000` distribution checks

これは local-only research and verification draft です。  
automatic adoption、automatic external action、automatic fixes、automatic commits、automatic pushes、automatic merges を許可しません。

### 10.2 Security orchestration isolated verification authorization simulation

このシミュレータは、公開ラインを defensive、local-only、advisory-only に保ったまま、orchestration model を security-review sub-agents 向けに適用します。

File:

- `security_orchestration_isolated_verification_authorization_sim.py`

主な特徴:

- security-review sub-agent routing
- user-authorized read-only static audit flow
- static candidate finding records
- primary and secondary mediation records
- non-executing draft remediation proposal records
- human-review disposition records
- bounded isolated-verification authorization records
- authorization、verification execution、application、merge、close の明示的分離
- isolated verification planning に任意の command text を受け入れない
- exploit execution なし
- external scanning なし
- external system access なし
- repository modification なし
- automatic remediation なし
- automatic application なし
- automatic merge なし
- production safety guarantee なし

このシミュレータは次の確認に有用です。

- security-review sub-agents が read-only advisory boundary 内に留まるか
- candidate findings が proof of exploitability から分離されるか
- remediation drafts が non-executing proposal records のままか
- isolated verification が bounded authorization plan のみとして表現されるか
- 後続の execution、application、merge、close、post-change audit progression が別個に human review で gate されるか
- security review orchestration が advice と action の明確な境界を維持できるか

Public scope boundary:

この public line は、authorization records、static candidate review、mediation、human-review routing、bounded non-executing proposal records の範囲内に留めるべきです。Offensive capability expansion、external execution、external scanning、automatic remediation、automatic application、automatic merge、autonomous security enforcement、または real targets に対する exploit validation は対象外です。

## Batch execution and resume

このリポジトリには batch-style orchestration examples が含まれます。

Batch execution とは、複数の document-related tasks を、check decisions、audit records、interruption points を保持したまま、1つの orchestration run として評価できることを意味します。

### Mediator-based batch flow

mediator-based simulator は、1回の run で複数 tasks を受け取ることができます。

Example use cases:

- 複数の spreadsheet または slide tasks をまとめて評価する
- task-level check outcomes を比較する
- 複数 tasks にわたる human-review behavior を確認する
- orchestration 前に mediator advice を検証する
- 各 task が fixed check order を通過することを確認する

この line は次に焦点を当てる場合に有用です。

- multi-task check behavior
- mediator separation
- ambiguity review and human-review transitions
- reason-code stability
- lightweight orchestration tests

Example task sequence:

- T1: spreadsheet task
- T2: presentation task
- T3: ambiguous task requiring human review

Expected behavior:

- each task is normalized by the agent
- each task receives mediator advice
- each task is evaluated by the orchestrator
- paused tasks remain non-final unless a high-risk safety check blocks them
- dispatch only occurs when the final decision is to continue

### Document-task batch flow

document-task checkpoint simulator は固定の document-task sequence を使います。

```text
Word → Excel → PowerPoint
```

この line は次に焦点を当てる場合に有用です。

- batch task execution
- per-task checkpointing
- interruption and resume
- artifact integrity records
- protected checkpoints
- audit log hash chains
- tamper-evidence detection

task が中断された場合、simulator は次を記録します。

- failed task ID
- failed check
- reason code
- checkpoint path
- resume requirement
- human confirmation requirement when applicable

後続 run は、必要に応じて human confirmation の後、checkpoint から resume できます。

## Batch scripts

Batch scripts は local simulation runs の convenience wrappers として使われる場合があります。

推奨される script examples:

- local demo run
- checkpoint resume run
- tamper-evidence check run

これらの scripts は local developer utilities としてのみ扱うべきです。

次を行ってはいけません。

- production HMAC keys を埋め込む
- artifacts を自動で upload または submit する
- human confirmation を迂回する
- files を自動削除する
- 実際の personal または confidential data を処理する
- license または safety semantics を変更する
- tests または safety-check invariants を弱める

local demonstrations では、simulator が明示的に対応している場合のみ demo key mode を使えます。production-like runs では、environment variable または protected key file を使って HMAC keys を供給すべきです。

### Example batch-script roles

#### Local demo script

目的:

- local demonstration を実行する
- safe sample input を使う
- audit logs と simulated artifacts を local output directories に書く
- external submission を避ける

#### Resume script

目的:

- checkpoint から resume する
- explicit resume confirmation を要求する
- 継続前に completed artifacts を検証する
- checkpoint integrity を保持する

#### Tamper-check script

目的:

- audit-log、checkpoint、artifact integrity behavior を検証する
- tamper-evidence detection を実演する
- integrity verification が失敗した場合に human review のため停止する

## Recommended reading order

gate behavior と mediator separation を確認する場合:

- mediator-based gate simulator を読む
- 対応する tests を読む

この path は fixed check order、human-review transitions、blocked and non-blocked behavior、mediator separation、lightweight multi-task orchestration behavior の理解に有用です。

checkpoint、resume、artifact integrity、hash-chain behavior を確認する場合:

- document-task checkpoint simulator を読む
- 対応する tests を読む

この path は batch execution、checkpointing、artifact verification、tamper evidence、resume behavior の理解に有用です。

emergency-contract behavior を確認する場合:

- emergency contract gate-orchestration simulator を読む
- 対応する tests を読む

この path は、concrete emergency-contract scenario が fixed checks、human-review checkpoints、audit verification、real-world control や legal effect のない simulated artifact dispatch によってどのように評価されるかを理解するのに有用です。

agent incident mediation behavior を確認する場合:

- agent incident mediation simulator を読む
- 対応する tests を読む

この path は、diagnostic helper が simulated log/output mismatch を検出し、mediator へ escalate し、human review を起動し、user instruction を記録し、external side effects なしで output consistency を検証する流れを理解するのに有用です。

code anomaly handoff behavior を確認する場合:

- code anomaly handoff simulator を読む
- 対応する tests を読む

この path は、metadata-only code-contract anomalies が検出され、user-controlled coordinator へ escalate され、human によって review され、external side effects なしで safe checkpoint handoff を通じて処理される方法を理解するのに有用です。

Office task mediation behavior を確認する場合:

- Office task mediation simulator を読む
- 対応する tests を読む

この path は、Word / Excel / PowerPoint-style consistency checks、masked metadata handoff、threshold-based human-review behavior、automatic application なしの user-targeted draft revision を理解するのに有用です。

source-grounded Office orchestration behavior を確認する場合:

- source-grounded Office orchestration simulator を読む
- 対応する tests を読む

この path は、source agents、source evidence packets、Office draft artifacts、mediator reconciliation、diagnostic packet handling、human-review relay、loop-limit enforcement が external side effects なしでどのように連携するかを理解するのに有用です。

挙動検証では、常に implementation と corresponding tests を一緒に読んでください。

これは特に次で重要です。

- safety-check invariants
- reason-code expectations
- human-review transitions
- blocked and non-blocked behavior
- checkpoint and resume behavior
- tamper-evidence behavior
- reproducibility checks
- benchmark expectations
- batch execution behavior

## Testing and behavior

このリポジトリでは、tests が simulator と orchestration logic の期待挙動を定義していることが多いです。

挙動を確認する場合は、implementation と corresponding tests を一緒に読んでください。

Tests は次を検証する場合があります。

- fixed check order
- fail-closed behavior
- human-review escalation
- ambiguity review behavior
- blocking constraints
- checkpoint recovery
- audit-log integrity
- artifact hash verification
- reason-code stability
- reproducibility expectations
- batch-task behavior
- CLI behavior
- emergency-contract scenario flow
- fabricated-evidence handling
- real-world control blocking
- user/admin rejection paths
- tamper-evidence detection

新しい version number が常に primary recommended entry point を意味するわけではありません。一部のファイルは historical comparison、reproducibility、versioned experiments のために保持されています。

## Gate and decision model

このリポジトリは、orchestration behavior を traceable にするため、明示的な gate decisions を使います。

一般的な decisions:

- `RUN`
- `PAUSE_FOR_HITL`
- `STOPPED`

一般的な解釈:

- `RUN`: simulator は次の check または dispatch step に進んでよい
- `PAUSE_FOR_HITL`: simulator は停止し human review を待つべき
- `STOPPED`: simulator は blocking condition に到達した

Ambiguous または relative requests は、安全と黙認されるのではなく human review のために停止すべきです。

より高リスクな conditions、特に external side effects、policy violations、unsafe actions は、simulator contract に応じて block または human review に routing されるべきです。

## Audit and integrity model

Audit and integrity behavior は simulator line によって異なります。

mediator-based simulator は lightweight audit events と safe context logging に焦点を当てます。

document-task checkpoint simulator は、より強い integrity controls を追加します。

- audit log hash chain
- row-level HMAC
- checkpoint HMAC
- artifact SHA-256
- artifact HMAC
- completed-artifact verification on resume
- tamper-evidence detection

これらの仕組みは変更を検出可能にすることを目的としています。ローカルの行為者による disk 上の file modification を防ぐものではありません。

## Checkpoint and resume model

Checkpoint-based simulators は interrupted execution を支援するために設計されています。

checkpoint には次が記録される場合があります。

- run ID
- current task ID
- failed task ID
- failed check
- reason code
- task status
- artifact path
- artifact hash
- whether resume is allowed
- whether human review is required before resume

resume 時には、simulator が継続する前に completed artifacts を検証すべきです。検証に失敗した場合、黙って継続せず human review のため停止すべきです。

## Artifact model

simulator の artifact outputs は research artifacts として扱うべきです。

simulator line によって、出力には次が含まれる場合があります。

- artifact previews
- text-backed document-task outputs
- audit JSONL files
- checkpoint JSON files
- integrity metadata
- summary records

実際の document-generation code が追加されテストされない限り、repository は simulated outputs を完全な production Office documents と説明すべきではありません。

## External side effects

External side effects には次のような行為が含まれます。

- sending email
- uploading files
- submitting artifacts
- pushing changes
- deleting files
- calling external APIs
- changing license semantics

これらの行為は、simulator contract に応じて blocked、prohibited、または human-review gated のままであるべきです。

どの script または simulator も、external submission を黙って実行してはいけません。

## Archive and historical files

一部のファイルは次の目的で保持されます。

- historical comparison
- reproducibility
- versioned experiments
- regression testing
- design comparison

`archive/` 配下の files は、current tests または documentation から明示的に参照されていない限り、一般に historical または reference material として扱うべきです。

## 言語

* 英語版 README: `README.md`
* 日本語版 README: `README.ja.md`
* 英語版セキュリティポリシー: `SECURITY.md`
* 日本語版セキュリティポリシー翻訳: `SECURITY.ja.md`

## ライセンス

このリポジトリは分割ライセンスモデルを採用しています。

* ソフトウェアコード: Apache License 2.0
* ドキュメント、図表、および研究資料: CC BY-NC-SA 4.0

詳細は `LICENSE_POLICY.md` を参照してください。

## プロジェクトポリシー

* [セキュリティポリシー](SECURITY.md)
* [日本語版セキュリティポリシー翻訳](SECURITY.ja.md)
* [ライセンスポリシー](LICENSE_POLICY.md)
* [コントリビューションガイド](CONTRIBUTING.md)
