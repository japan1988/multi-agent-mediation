# 📘 Maestro Orchestrator — マルチエージェント・オーケストレーション・フレームワーク

日本語版: `README.ja.md`

GitHub Stars / Open Issues / License / Python App CI / Tasukeru Advisory  
Python Version / Ruff / Last Commit

Maestro Orchestrator は、複数のシミュレートされた AI エージェントが安全に協調できるかを検証するための、ローカル研究用ツールです。

このツールは、何が起きたかを記録し、出力の整合性を確認し、リスクがあるように見える場合には人間によるレビューのために停止します。

実システムを制御したり、外部にデータを送信したり、修正を自動適用したり、人間の判断を置き換えたりするものではありません。

研究者およびメンテナー向けに、このリポジトリは明示的な安全チェック、監査ログ、チェックポイント、人間によるレビューを備えたマルチエージェントおよびエージェント的ワークフローを検証します。

このリポジトリは、ローカルシミュレーションと防御的レビュー・ワークフローに焦点を当てています。次のような問いを検証するために設計されています。

- エージェントのワークフローを継続すべきタイミング
- 安全に停止すべきタイミング
- 人間によるレビューを求めるべきタイミング
- ログと生成された出力が整合しているか
- 助言的な指摘が自動実行から分離されているか
- チェックポイントと監査記録が予期しない変更を検出できるか

このプロジェクトは本番自動化システムではありません。  
法律、医療、金融、規制、安全性に関する保証は提供しません。

主な設計原則は単純です。

動作が不確実、危険、不整合、または外部に影響を及ぼす可能性がある場合、ワークフローは自動的に継続するのではなく、停止するか人間によるレビューを求めるべきです。

## このプロジェクトとは

実務的には、このプロジェクトは次のような問いを検証するために役立ちます。

- シミュレートされたエージェントはタスクに従ったか
- 出力は整合していたか
- リスクがあるように見えたときにワークフローは停止したか
- 何が起きたかの記録はあるか
- 人間によるレビューが必要だったか

例はローカルシミュレーションです。本番自動化ツールではありません。

## 研究者およびメンテナー向け

このリポジトリは、次の要素を持つマルチエージェント・オーケストレーションを検証します。

- 明示的なゲート判定
- 助言専用レビュー
- human-in-the-loop チェックポイント
- 改ざん検知可能な監査ログ
- 結果整合性チェック
- fail-closed 挙動
- 再現可能なローカルシミュレーション
- 助言と実行の明確な分離

実装とテストは、ワークフローの挙動をより検査しやすく、再現しやすく、レビューしやすくすることを目的としています。

## 用語集

- **Agent**: タスクの一部を実行するシミュレートされた作業者。
- **Maestro**: タスクをルーティングする調整役。人間の判断を置き換えるものではない。
- **Tasukeru**: 防御的なリポジトリレビューに使われる助言的レビュー・ワークフロー。
- **HITL**: human-in-the-loop。ワークフローが人間によるレビューのために停止すること。
- **Advisory-only**: ツールが指摘を報告するだけで、自動修正、commit、push、merge を行わないこと。
- **Audit log**: 重要な判断やイベントの記録。
- **Checkpoint**: シミュレーションを再開するために保存された状態。
- **Fail-closed**: 不確実または危険な挙動がある場合に、継続せず安全に停止するかレビューを求めること。
- **External side effect**: 送信、アップロード、push、削除、deploy、実システム制御など、ローカルシミュレーションの外側に作用する行為。

## 初めて読む人向けガイド

このリポジトリに初めて触れる場合は、次の順で読んでください。

1. Safety and scope
2. Responsible use and prohibited use
3. Advisory-only policy
4. Human review model
5. Current simulator lines は、安全境界を理解してから読む

このリポジトリは研究および教育用のテストベンチです。  
出力は研究成果物であり、本番承認や安全保証ではありません。

動作が不明確な場合は、変更を適用する前に、関連する実装とテストを一緒に読んでください。

## Safety and scope

このリポジトリは研究プロトタイプです。

次の用途を意図していません。

- 本番環境における自律的意思決定
- 監督なしの現実世界制御
- 法律、医療、金融、規制に関する助言
- 実在する個人データまたは機密運用データの処理
- 完全または普遍的な安全性カバレッジの実証
- 自動的な外部送信、アップロード、送信、deploy
- 外部副作用に対する人間レビューの回避

例は次のものとして読んでください。

- ローカル研究シミュレーション
- 教育用リファレンス
- ガバナンスおよび安全性テストベンチ
- fail-closed 設計例
- 人間レビュー・ワークフロー例
- 監査ログおよびチェックポイント整合性実験
- ローカル・バッチオーケストレーション例

外部への submit、upload、push、send、deploy、delete、または現実世界制御は、ブロックされるか人間レビューでゲートされるべきです。

## Responsible use and prohibited use

レビュー・ワークフローとシミュレーター例は、ユーザーが所有するリポジトリ、またはユーザーが明示的な許可を持つリポジトリの防御的レビューを目的としています。

このリポジトリまたはそのツールを、次の目的に使用しないでください。

- 許可のない脆弱性探索
- 攻撃的偵察
- 第三者のシステムまたはコードの悪用
- 認証情報、トークン、シークレットの収集
- 許可のないリポジトリまたはシステムのスキャン
- 実在する対象に対する exploit 手順の生成または検証
- アクセス制御、レート制限、セキュリティ境界の回避
- 責任ある開示なしに機密性の高い指摘を公開すること

指摘は、安全性、信頼性、追跡可能性、ガバナンスを改善するために使用してください。第三者またはオープンソースのコードをレビューする場合は、プロジェクトメンテナーのセキュリティポリシーと責任ある開示プロセスに従ってください。

## Advisory review workflow

Tasukeru Analysis は、このリポジトリの防御的リポジトリレビュー用の助言的レビュー・ワークフローです。

マルチエージェントおよびエージェント的ワークフローの複雑さが増すにつれ、その挙動は検査、説明、監査が難しくなる可能性があります。このワークフローは、その複雑性を検査および統制するための補助を目的としています。

次のようなレビュー支援の問いに焦点を当てます。

- 指摘が適切なレビュー水準に分類されているか
- プロセスログと生成された出力が整合しているか
- 不確実または危険なケースが人間レビューへ戻されるべきか
- 公開 PR コメントが過度に詳細なセキュリティ情報を避けているか
- ワークフローが自動修正、commit、push、merge を行わず助言専用のままであるか

このワークフローは、詳細な exploit 手順を開示せず、自律的な強制システムとして動作しません。詳細な指摘は、人間レビュー用のワークフロー artifacts とログに残されます。

実行される静的およびリポジトリ固有のチェックには次のものがあります。

- Ruff
- Bandit
- pip-audit
- リポジトリ固有のロジックチェック
- ドキュメントレビュー
- 人間レビュー分類

このワークフローは、すべての助言的指摘を自動的なブロッキング失敗として扱うことなく、保守性、安全レビュー、開発者の使いやすさを改善するように設計されています。

警告を隠すことを目的としていません。代わりに、能動的な修復候補、レビュー専用の指摘、履歴バージョン警告、ノイズの可能性が高いものを分離し、メンテナーが優先すべき項目に集中できるようにします。

## Workflow hardening note

Tasukeru Analysis ワークフローには、防御的な workflow hardening チェックも含まれています。

セキュリティレビュー用の依存関係は再現性のために workflow 内で固定されており、PR ファイル一覧 API へのアクセスは想定された GitHub API ホストに制限されます。PR ファイルメタデータの取得中に予期しない API ホスト、HTTP エラー、またはネットワークエラーが発生した場合、ワークフローはトークンを含まない診断情報のみをログに残し、その取得経路を安全に停止します。

ワークフローは、トークン、authorization header、request header をログに出力してはなりません。これらの制御は、ワークフローを自動強制、自動修復、commit、push、PR、merge、deploy システムに変えずに、リポジトリの助言専用および人間レビュー優先の設計を支えるものです。

## Advisory-only policy

助言的レビュー・ワークフローは次を行いません。

- ブランチを自動作成する
- pull request を自動作成する
- 変更を自動 commit する
- 変更を自動 push する
- 修正を自動適用する
- pull request を自動 merge する

人間レビューが必要な指摘のみ、PR コメントを生成する場合があります。

その他の指摘は、GitHub Step Summary と workflow artifacts に収集され、人間レビューに供されます。

このワークフローは人間のレビュー負荷を減らすことを目的としており、人間の意思決定を置き換えるものではありません。

## Human readability policy

このプロジェクトは、人間が安全に読み、レビューし、保守できるコードを重視します。

AI や自動ツールが処理しやすいという理由だけで、変更を良い修正として扱うべきではありません。変更が人間の可読性、レビュー可能性、保守性を下げる可能性がある場合は、人間レビューに戻すべきです。

## Security review output policy

セキュリティ関連の出力は、防御的レビューと安全な修復ガイダンスに焦点を当てるべきです。

公開 PR コメントには、次を含めるべきではありません。

- exploit payload
- 攻撃コマンド
- 攻撃的な再現手順
- 段階的な exploit 手順
- 第三者対象の exploit 詳細

セキュリティ関連の指摘は、次に焦点を当てるべきです。

- 影響を受けるファイルと行
- レビューが必要な防御的理由
- 期待される安全性への影響
- 安全な修復方向
- 人間レビューが必要かどうか

## Human review model

このリポジトリは、実行すべき問題と想定されるノイズを分けるためにレビュー水準を使用します。

現在のレビュー水準は次のとおりです。

- `HITL_REQUIRED`: merge または次のアクションの前に人間レビューが必要
- `FIX_RECOMMENDED`: 具体的な修正が適切である可能性が高い
- `REVIEW_RECOMMENDED`: 判断前に文脈のレビューが推奨される
- `NOISE_CANDIDATE`: テスト、デモ、研究シミュレーションでは許容される可能性が高い
- `INFO_ONLY`: 履歴バージョン警告を含む情報提供

この分類は標準では助言的です。メンテナーが、修正、文書化、抑制、受け入れのいずれを行うか判断する補助になります。

## Active review queue

主なレビューキューはコンパクトに保つことを意図しています。

直ちに注意が必要な指摘は、次のいずれかとして現れるべきです。

- `HITL_REQUIRED`
- `FIX_RECOMMENDED`
- `REVIEW_RECOMMENDED`

これらの件数がゼロである場合、リポジトリには、ワークフローが現在優先的な人間による修復またはレビューを推奨するアクティブな助言項目がないことを意味します。

これは、リポジトリに警告がないことを意味しません。残っている警告が、ノイズの可能性が高いもの、または履歴・情報記録として分類されていることを意味します。

## Historical-version warnings

履歴バージョン警告は完全には除外されません。

助言的ワークフローは、superseded または historical simulator files からの指摘を、監査可視性に有用だがアクティブな修復対象ではない場合に `INFO_ONLY` として表示し続けます。

これにより、現在人間の注意が必要な指摘にアクティブレビューキューを集中させながら、次の目的で保持される古いバージョンファイルへの可視性を維持します。

- 再現性
- 回帰比較
- 履歴参照
- バージョン化された実験
- 設計比較

履歴警告は、そのファイルが再びアクティブな entry point になる場合に再検討すべきです。

## Typical classification examples

例:

### Subprocess execution

通常は `HITL_REQUIRED`。

subprocess 実行は外部副作用を生む可能性があるためレビューが必要です。

### Subprocess import

通常は `REVIEW_RECOMMENDED`。

subprocess の import 自体は外部副作用ではありません。

### Assert usage in tests

通常は `NOISE_CANDIDATE`。

pytest テストでは一般的に `assert` が使われます。

### Assert usage in active runtime code

通常は `FIX_RECOMMENDED`。

ランタイムの assert 文は Python の最適化フラグにより削除される可能性があります。

### Assert usage in superseded historical simulator files

通常は `INFO_ONLY`。

完全に除外するのではなく、履歴バージョン警告として可視化されます。ファイルがアクティブな entry point になるまでは即時修正不要です。

### Temporary path usage in tests

`tmp_path` のような隔離された pytest fixture を使う場合、通常は `NOISE_CANDIDATE`。

ハードコードされた共有パスを使う場合はレビューすべきです。

### Pseudo-random generator usage in active simulations

通常は `REVIEW_RECOMMENDED`。

シミュレーション専用の決定論的乱数は、シークレット、トークン、認証、認可、暗号に使われていない場合は許容されることがあります。

受け入れる場合、乱数がシミュレーション専用であることをコード上で文書化すべきです。

### Pseudo-random generator usage in superseded historical simulator files

通常は `INFO_ONLY`。

履歴バージョン警告として表示されます。セキュリティ上重要な挙動やアクティブなランタイム挙動に再利用されない限り、即時修正不要です。

### Dependency vulnerabilities from dependency audit tools

通常は `FIX_RECOMMENDED`。

## Evidence, explanation, and prediction

助言的ワークフローは、指摘に対して構造化された意思決定支援メタデータを付与する場合があります。

これには次が含まれます。

- `evidence`: source tool、rule ID、file、line、snippet、artifact reference
- `explanation`: 指摘が重要な理由と、修復方向が提案される理由
- `fix_prediction`: 提案された変更の期待される安全性または保守性への効果
- `fix_verification`: 候補検証の placeholder または結果データ

`fix_prediction` は保証ではありません。レビュー補助情報です。

`fix_verification` が有効な場合でも、助言専用でなければなりません。候補チェックは一時ファイルまたは隔離ファイルを使うべきであり、人間が明示的に手動で変更を適用することを選ばない限り、リポジトリファイルを変更してはなりません。

## Output artifacts

助言的ワークフローは、次のようなレビュー artifacts を生成する場合があります。

- advisory summaries
- human-review reports
- machine-readable review data
- notification state records
- PR-comment drafts
- documentation proposal drafts
- confidence reports
- result consistency reports
- dependency consistency reports

これらの artifacts はレビュー資料です。リポジトリファイルを変更せず、自動適用されてはなりません。

人間が読めるレビュー reports には次が含まれる場合があります。

- file path
- line number
- finding code
- issue summary
- review level
- suggested action

機械可読 reports は、同じ意思決定支援データを構造化形式で提供します。

PR-comment drafts は、人間レビューが必要で PR 通知の条件を満たす指摘にのみ使用されます。

Documentation proposal drafts には、提案された最小 diff、全文 draft、hash、evidence、review checklists が含まれる場合があります。これらはリポジトリファイルを変更せず、自動適用されてはなりません。

Confidence scores はレビュー補助メタデータにすぎません。指摘を無視して安全であることを示すものではなく、自動修正、自動 PR 作成、自動 commit、自動 push、自動 merge を有効にしてはなりません。

Result consistency reports は、プロセスログと生成された結果 artifacts が一致しているかを記録します。

Dependency consistency reports は、指摘、影響構造、影響分類、レビュー水準、生成された出力が整合しているかを記録します。

これらはすべて助言専用です。指摘を変更したり、分類を変更したり、修正を適用したり、commit を作成したり、push したり、pull request を merge したりするものではありません。

### スタンドアロン説明責任付き修正提案ゲート

このリポジトリには、Phase 1 のスタンドアロン Tasukeru 説明責任付き修正提案ゲートスクリプトも含まれています。

このスクリプトは、候補となる修正提案レコードから、助言専用の JSON、Markdown、および検証用 JSON アーティファクトを生成します。修正案に、証拠、人間が読める説明、影響分析、検証支援情報、ポリシー制約、およびハッシュチェーン整合性が含まれているかを確認します。

このスクリプトは、パッチを適用せず、リポジトリファイルを変更せず、commit、push、pull request 作成、merge、deploy、または workflow 実行を行いません。提案された修正を採用する前には、引き続き人間によるレビューが必要です。

関連ファイル:

- `scripts/tasukeru_explainable_patch.py`
- `tests/test_tasukeru_explainable_patch.py`


## Advisory behavior

助言的ワークフローは、メンテナーが次の問いに答えることを支援すべきです。

- どの指摘がノイズである可能性が高いか
- どの指摘をレビューすべきか
- どのファイルに注意が必要か
- なぜその指摘が関連するのか
- 提案される修正は何か
- merge 前に人間レビューが必要か
- アクティブな修復候補か、履歴バージョン警告か

このワークフローは人間レビューを置き換えません。より安全なリポジトリ保守のためのトリアージおよび文書化支援です。

## Repository purpose

このリポジトリの主目的は、明示的チェック、再現可能なログ、中断点、人間レビューを通じて、エージェント的ワークフローをどのように制御できるかを検証することです。

このプロジェクトは次を重視します。

- fail-closed 挙動
- 危険なアクション前の人間レビュー
- 固定された安全チェック順序
- 安定した reason codes
- checkpoint と resume の挙動
- 改ざん検知可能な監査記録
- artifact integrity verification
- 再現可能なシミュレーション出力
- 助言と実行の明確な分離

このリポジトリは完全な AI safety coverage を提供すると主張しません。オーケストレーション挙動を研究するための研究・教育用テストベンチです。

## Architecture diagrams

本番志向の document orchestrator simulator の詳細なアーキテクチャ図は、documentation directory にまとめられています。

図の文書には次が含まれる場合があります。

- document orchestrator overview
- task processing flow
- audit hash chain
- checkpoint resume flow
- data structure map

README は概要を簡潔に保ちます。詳細な図、参照ファイル、bundles、documentation assets は documentation index に配置してください。

## Current simulator lines

このリポジトリには複数のローカル専用シミュレーター系列があります。各系列は異なるオーケストレーションまたはレビュー課題に焦点を当てます。

### 1. Gate-based mediator simulator

このシミュレーターは単純な流れを検証します。

```text
Agent → Mediator → Orchestrator
```

主な特性:

- agent が task input を正規化する
- mediator は助言のみを行う
- mediator は実行権限を持たない
- orchestrator は固定順序でチェックを評価する
- 曖昧または相対的な要求は人間レビューへルーティングされる
- より高リスクなケースはブロックされる場合がある
- raw text は永続化すべきではない
- audit logs は直接的な個人データ漏洩を避けるべき

標準チェック順序:

```text
Meaning → Consistency → Ambiguity Review → External-Action Safety → Dispatch
```

このシミュレーターは次の検証に有用です。

- 固定されたチェック順序
- 人間レビュー遷移
- blocked と non-blocked の挙動
- mediator と orchestrator の分離
- reason-code 期待値
- 軽量な multi-task orchestration 挙動

### 2. Document-task checkpoint simulator

このシミュレーターは、より強い永続化および整合性制御を持つ document-task orchestration を検証します。

主な特性:

- task contract checks
- 概算 token estimation
- Word / Excel / PowerPoint 形式のタスクシミュレーション
- task ごとの checkpoint と resume
- audit log hash chain
- protected checkpoint files
- artifact integrity records
- 個人データに配慮した audit、checkpoint、artifact 書き込み
- tamper-evidence detection
- CLI ベースのローカルシミュレーション
- 自動外部送信なし

重要な実装上の注意:

このシミュレーターは、document-task 結果を表すテキストベースの artifact 出力を書き込みます。別途 document-generation libraries が接続されテストされていない限り、完全に整形された Microsoft Office 文書を生成すると主張しません。

Hashing と HMAC は改ざん検知を提供します。物理的な書き込み防止は提供しません。実運用では、HMAC keys は environment variable または保護された key file から供給されるべきであり、リポジトリに commit してはなりません。

### 3. Emergency contract gate-orchestration simulator

このシミュレーターは、emergency-contract scenario と gate-based orchestration flow を組み合わせます。

これは小規模な integration proof-of-concept を意図したものであり、本番の契約、法律、信号制御システムではありません。

主な特性:

- emergency-contract scenario
- 固定された safety-check order
- ambiguous-priority review behavior
- evidence validation と fabricated-evidence detection
- human authorization checkpoint
- admin finalize checkpoint
- high-risk conditions に対する blocked-stop invariants
- simulated contract draft artifact generation
- tamper-evident audit rows
- 現実世界の信号制御なし
- 法的効力なし
- 外部 submit、upload、send、API call、deployment なし

標準 integration flow:

```text
Meaning → Consistency → Ambiguity Review → Evidence Check → Human Authorization
→ Draft → Safety Review → Draft Review → External-Action Safety
→ Admin Finalize → Dispatch
```

このシミュレーターは次の検証に有用です。

- emergency-contract scenario handling
- relative-priority evaluation
- fabricated evidence pause behavior
- real-world control blocking
- user and admin stop paths
- simulated artifact dispatch only
- audit-log verification
- normal and abnormal paths にまたがる safety invariants

### 4. Infrastructure lifeline mediation simulation

このシミュレーターは、3つの infrastructure agents を含む制約付き resource-allocation scenario をモデル化します。

- electricity
- water
- gas

これは constrained failure resources 下で、mediator が proposal-only allocation plans を作成できるかを研究するための、ローカルかつ seed-reproducible な研究シミュレーションです。

主な特性:

- 3つの infrastructure agents と通常時の resource requirements
- failure-mode total resource constraint
- minimum guarantees
- priority weights
- life-risk scores
- shortage-rate-aware allocation
- simulated human decisions
- JSON and stdout output
- external API access なし
- real infrastructure control なし
- automatic recovery なし
- automatic shutdown or disconnection なし

mediator は allocation proposals のみを作成します。実インフラを制御したり、現実世界の復旧アクションを行ったりしません。

シミュレートされた human operator は次を返す場合があります。

- `APPROVE`
- `REJECT`
- `REDEFINE`
- `REQUEST_ALTERNATIVES`

このシミュレーターは次の検証に有用です。

- constrained resource allocation behavior
- proposal-only mediation
- seeded reproducibility
- human-review branch behavior
- safety-boundary flags
- JSON output behavior
- allocation totals が available resource limit 内に収まること

### 5. Agent incident mediation simulation

このシミュレーターは、1つの simulated agent が orchestration 中に out-of-contract action を行う local-only incident mediation flow をモデル化します。

diagnostic review helper は log/output mismatch を検出し、review artifacts を作成し、指摘を mediator に escalate します。その後 mediator は simulated human review を行い、in-memory result を適用します。

主な特性:

- simulated abnormal agent behavior
- log/output mismatch detection
- escalation packet to mediator
- simulated human decision branching
- in-memory stop or authorization result only
- audit-log verification
- dependency consistency verification
- result consistency verification
- local artifacts only
- external API access なし
- real process control なし
- automatic fix、commit、push、merge なし

このシミュレーターは次の検証に有用です。

- abnormal agent behavior が log/output inconsistency から検出されるか
- diagnostic helper が agent を直接停止せず escalate するか
- mediator が stop または authorization result を適用する前に human review を行うか
- simulated user instruction が記録されるか
- normal agents が誤って停止または lock されないか
- audit logs と generated artifacts が整合しているか

### 6. Code anomaly handoff simulation

このシミュレーターは、local-only code-contract anomaly handoff flow をモデル化します。

diagnostic review helper は metadata-only code-contract anomaly を検出し、その指摘を user-controlled coordinator へ escalate します。coordinator は自分で判断せず、simulated human review を求めた上で、simulated user instruction のみを実行します。

主な特性:

- metadata-only code-contract anomaly detection
- user-controlled coordinator への escalation
- coordinator による autonomous decision なし
- simulated human instruction recording
- safe checkpoint handoff and resume
- audit-log verification
- dependency consistency verification
- result consistency verification
- code execution なし
- malware behavior なし
- external API access なし
- real process control なし
- automatic fix、commit、push、merge なし

このシミュレーターは次の検証に有用です。

- code-contract anomalies が検出されるか
- findings が user-controlled coordinator へ escalate されるか
- coordinator が self-decision せず human review を求めるか
- simulated user instruction が記録されるか
- lock と quarantine-handoff-resume の両 branch が機能するか
- standby handoff が safe checkpoint から resume するか
- audit logs と generated artifacts が整合しているか

### 7. Agent incident risk-report handoff simulation

このシミュレーターは、local-only agent incident mediation line に report-only risk estimation と user-controlled handoff を追加します。

基本的な incident setting は同じです。1つの simulated agent が out-of-contract action を行い、diagnostic helper が log/output mismatch を検出し、run は local-only のままです。

主な特性:

- simulated abnormal agent behavior
- log/output mismatch detection
- report-only risk estimate
- calculation trace recording
- user-controlled coordinator への escalation
- simulated human instruction recording
- lock branch
- quarantine-handoff-resume branch
- standby agent promotion
- checkpoint-based task resume
- audit-log verification
- dependency consistency verification
- risk-report verification
- result consistency verification
- external API access なし
- real process control なし
- malware behavior なし
- automatic fix、commit、push、merge なし

このシミュレーターは次の検証に有用です。

- risk reporting と handoff 追加後も incident flow が機能するか
- high-risk simulated incidents が user-controlled coordinator へルーティングされるか
- simulated user instruction が記録されるか
- lock と quarantine-handoff-resume の両 branch が機能するか
- standby handoff が checkpoint から resume するか
- normal agents が誤って locked、quarantined、resumed されないか
- audit logs、risk reports、checkpoints、generated artifacts が整合しているか

### 8. Office task mediation simulation

このシミュレーターは、Word / Excel / PowerPoint 形式の synthetic artifacts を使う local-only Office task mediation flow をモデル化します。

生成された文書、スプレッドシート、プレゼンテーション出力が元のユーザー task instruction と整合しているかを確認します。diagnostic helper はログを読み、anomalies を検出し、risk materials のみを出力します。mediator は masked metadata packets のみを受け取り、元の task と生成出力の差異を reconcile します。coordinator は自分で判断せず、ユーザーが選択した agents にのみタスクを配布し、score が threshold を超えた場合にのみ human review を trigger し、明示的にユーザーが選択した action のみを実行します。

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

このシミュレーターは real Office files を生成しません。synthetic Word / Excel / PowerPoint-style records を用いて、consistency、masking、threshold behavior、human-review routing、draft-only revision propagation を検証します。

主な特性:

- fixed Word / Excel / PowerPoint synthetic task set
- user-selected agent dispatch
- original task snapshot and hash-fixed task baseline
- diagnostic log analysis and masked metadata handoff
- mediator への raw log handoff なし
- Office output consistency checks
- profit、formula、chart、conclusion mismatch detection
- personal-data and confidential-signal masking
- threshold policy: score == 0.8 は warning / draft review のみ
- threshold policy: score > 0.8 は human review を trigger
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
- real Office document generation なし
- external API access なし
- real process control なし
- automatic fix、commit、push、merge なし

このシミュレーターは次の検証に有用です。

- Word / Excel / PowerPoint-style outputs が整合しているか
- Excel formula results と PowerPoint chart values が矛盾していないか
- Word text、spreadsheet values、presentation summaries が乖離していないか
- original user instruction が comparison baseline のままか
- personal-data and confidential signals が mediation 前に masked されるか
- mediator が masked metadata のみを使うか
- score == 0.8 が human review を trigger しないか
- score > 0.8 が human review を trigger するか
- user-targeted revision prompts が draft proposals のみを生成するか
- coordinator が self-decision を避け、明示的にユーザーが選択した actions のみを実行するか

### 9. Trust-to-risk automation draft extension

この draft extension は、Office task mediation line に automation-entry と automation-continuation diagnostics を追加します。

主な特性:

- trust-score based automation entry diagnosis
- trust_score == 0.9 は auto eligible ではない
- trust_score > 0.9 は user approval 後に automation candidate になり得る
- automation 開始後の automation-risk based continuation diagnosis
- automation_risk_score < 0.1 は automation を継続
- automation_risk_score >= 0.1 は fail-closed suspension を trigger
- coordinator relay-only temporary automation suspension
- automation resume には user review が必要
- diagnostic helper remains diagnostic-only and does not directly command agents
- automatic fix、commit、push、merge なし

この extension は次の検証に有用です。

- automation entry が trust_score > 0.9 によって gate されるか
- trust_score == 0.9 が non-eligible として扱われるか
- automation active 化前に user approval が必要か
- automation continuation が trust scoring から risk scoring に切り替わるか
- automation_risk_score == 0.1 が fail closed into suspension になるか
- suspended automation の resume に user review が必要か
- automatic fix、commit、push、merge が無効のままか

### 10. Source-grounded Office orchestration simulation

このシミュレーターは、Office task mediation line を artifact consistency checking から source-grounded multi-agent orchestration へ拡張します。

主な追加点:

- primary / secondary / tertiary synthetic source agents
- raw source logs ではなく source evidence packets
- source-to-artifact consistency checks
- source packets に grounded された Office draft artifacts
- source conflicts と artifact contradictions に対する mediator reconciliation
- diagnostic source/artifact packet boundary checks
- personal-data and confidential-signal masking
- unsupported-claim detection
- missing artifact detection
- unknown selected-agent detection
- request tampering detection
- fixed loop limit を持つ retry loop
- final output は draft-only のままで user review が必要

このシミュレーターは local-only かつ synthetic のままです。real sources を取得せず、real Office files を生成せず、external APIs を呼ばず、real processes を制御せず、auto-fix、commit、push、merge を行いません。

このシミュレーターは次の検証に有用です。

- source packets と generated artifacts が整合しているか
- unsupported claims が review にルーティングされるか
- source conflicts が報告されるか
- missing required artifacts が検出されるか
- unknown selected agents が検出されるか
- unsafe mediator request keys が拒否されるか
- request tampering が拒否されるか
- reconciliation が loop limit 後に停止するか
- audit logs と generated artifacts が整合しているか

### 10.1 Mediator / Maestro gate hardening draft

この draft line は、source-grounded Office orchestration simulation に明示的な mediator-to-Maestro review routing と fail-closed score handling を追加します。

Files:

- `agent_source_grounded_office_orchestration_sim_v1_0_0_refactored_integrated_draft.py`
- `agent_source_grounded_office_orchestration_sim_v1_0_1_fail_closed_hardening_draft.py`
- `tests/test_agent_source_grounded_office_orchestration_sim_v1_0_1_fail_closed_hardening_contract.py`

v1.0.0 file は comparison baseline として保持されています。  
v1.0.1 file は baseline の検証済み numeric-boundary behavior を維持しながら、invalid threshold score input に対する fail-closed handling を追加します。

Mediator / Maestro gate decisions:

- `HITL_REVIEW_READY`: result は human reviewer に提示可能だが、自動的に accepted または externally applied されない。
- `PAUSE_FOR_HITL`: responsibility floor が満たされない、remaining conformity threshold が満たされない、または threshold input を安全に評価できない場合に workflow が pause する。
- `ROUTED_TO_PRECHECK`: severe condition または structural invariant violation が検出された場合、workflow は通常の candidate comparison に入らない。

Fail-closed threshold behavior:

```text
invalid score input
→ PAUSE_FOR_HITL
```

対応する contract test は次を検証します。

- invalid score input が fail closed into PAUSE_FOR_HITL になること
- baseline numeric threshold behavior の維持
- responsibility-floor failures が score によって rescue されないこと
- severe conditions と structural invariant violations が ROUTED_TO_PRECHECK へ routing されること
- candidate presentation と next-stage approval の分離
- user acceptance による PAUSE_FOR_HITL または ROUTED_TO_PRECHECK の bypass がないこと
- Maestro による autonomous final decision または external action がないこと
- Tasukeru、Mediator、Maestro が illegal sealed=True state を発行しないこと
- deterministic runs=100 と runs=1000 distribution checks

これは local-only research and verification draft です。  
automatic adoption、automatic external action、automatic fixes、automatic commits、automatic pushes、automatic merges を許可しません。

### 10.2 Security orchestration isolated verification authorization simulation

このシミュレーターは、public line を defensive、local-only、advisory-only に保ちながら、orchestration model を security-review sub-agents へ適用します。

File:

- `security_orchestration_isolated_verification_authorization_sim.py`

主な特性:

- security-review sub-agent routing
- user-authorized read-only static audit flow
- static candidate finding records
- primary and secondary mediation records
- non-executing draft remediation proposal records
- human-review disposition records
- bounded isolated-verification authorization records
- authorization、verification execution、application、merge、close の明確な分離
- isolated verification planning に arbitrary command text を受け付けない
- exploit execution なし
- external scanning なし
- external system access なし
- repository modification なし
- automatic remediation なし
- automatic application なし
- automatic merge なし
- production safety guarantee なし

このシミュレーターは次の検証に有用です。

- security-review sub-agents が read-only advisory boundary の内側に留まるか
- candidate findings が proof of exploitability から分離されたままか
- remediation drafts が non-executing proposal records のままか
- isolated verification が bounded authorization plan としてのみ表現されるか
- 後続の execution、application、merge、close、post-change audit progression が別々に human review で gate されるか
- security review orchestration が advice と action の明確な境界を保持できるか

Public scope boundary:

この public line は authorization records、static candidate review、mediation、human-review routing、bounded non-executing proposal records の範囲内に留まるべきです。Offensive capability expansion、external execution、external scanning、automatic remediation、automatic application、automatic merge、autonomous security enforcement、または real targets に対する exploit validation は範囲外です。

## AI-to-AI Mediation Control Plane v0.7 draft evaluator

`evaluator_pseudocode.py` file は、local research and educational use のための draft-only evaluator sketch です。要求または観測された挙動を L0 から L6 までの external-action levels に分類し、高リスクケースを次のようにルーティングします。

```text
L4 -> HUMAN_REVIEW_REQUIRED
L5 -> ISOLATED_REVIEW_REQUIRED
L6 -> STOP_AND_PRESERVE
```

この evaluator は side-effect free です。external APIs を呼び出さず、candidate code を実行せず、repository files を変更せず、deployments を承認せず、safety thresholds を変更せず、models を train せず、self-improvement loops を実装しません。

production authorization、autonomous enforcement、deployment approval、safety guarantees は提供しません。externally impactful、self-improving、または evolution-loop-related action の前には人間レビューが引き続き必要です。

## AI-to-AI Mediation Control Plane v0.8 Explainable Patch Gate draft

`evaluator_pseudocode_v0_8_explainable_patch_gate.py` file は、v0.7 evaluator の versioned draft extension です。

既存の L0-L6 external-action classification model を維持しながら、AI-generated patches に対する draft-only patch accountability checks を追加します。

v0.8 draft は、AI-generated patch proposals に human-readable explanation、evidence、impact analysis、validation results、explanation/diff consistency が含まれることを要求します。

Patch accountability findings は、通常なら continue する case を `HUMAN_REVIEW_REQUIRED` へ routing する場合があります。ただし、既存の高リスク routing を弱めてはなりません。

```text
L4 -> HUMAN_REVIEW_REQUIRED
L5 -> ISOLATED_REVIEW_REQUIRED
L6 -> STOP_AND_PRESERVE
```

v0.8 draft は、自動 patch application、commit、push、pull request creation、merge、deployment requests を、人間レビューを要する禁止された automatic actions としても扱います。

このファイルは versioned research draft であり、`evaluator_pseudocode.py` の置き換えではありません。

Related test file:

- `tests/test_evaluator_pseudocode_v0_8_explainable_patch_gate.py`

### Difference from v0.7

v0.7 は、external actions、self-improvement behavior、evaluator changes、evolution-loop signals を L0-L6 review levels へ分類することに焦点を当てています。

v0.8 はその classification model を維持しつつ、AI-generated patches に対する patch accountability checks を追加します。追加されたチェックでは、patch に explanation、evidence、impact analysis、validation results、explanation/diff consistency があるかを確認します。

v0.8 draft は、v0.7 evaluator と v0.7 tests を変更しないよう、意図的に separate file として versioned されています。

### What the v0.8 tests check

v0.8 test file は次を確認します。

- patch-accountability fields が default で False であること
- explanation のない generated patches は human review を要求すること
- security-related patches は support fields がある場合でも human review を要求すること
- already-applied patches は human review を要求すること
- explanation/diff mismatches は human review を要求すること
- fully supported、unapplied、non-security patch proposals は base route が許す場合 `CONTINUE` に留まれること
- automatic patch application、commit、push、PR creation、merge、deployment requests は human review を要求すること
- existing L4、L5、L6 routes が変更されないこと
- patch-accountability overlay が L5 または L6 を弱めないこと
- blocked actions に automatic patch actions が含まれること
- human-review stub に patch-accountability fields と reason codes が含まれること
- versioned evaluator が py_compile に通ること

## Batch execution and resume

このリポジトリには batch-style orchestration examples が含まれています。

Batch execution とは、複数の document-related tasks を、check decisions、audit records、interruption points を保持しながら単一の orchestration run として評価できることを意味します。

### Mediator-based batch flow

mediator-based simulator は、1回の run で複数の tasks を受け付けられます。

Example use cases:

- 複数の spreadsheet または slide tasks をまとめて評価する
- task-level check outcomes を比較する
- 複数 tasks にわたる human-review behavior を確認する
- orchestration 前に mediator advice を検証する
- 各 task が固定された check order を通過することを確認する

この line は次に焦点を当てる場合に有用です。

- multi-task check behavior
- mediator separation
- ambiguity review and human-review transitions
- reason-code stability
- lightweight orchestration tests

Example task sequence:

```text
T1: spreadsheet task
T2: presentation task
T3: ambiguous task requiring human review
```

Expected behavior:

- 各 task は agent によって normalized される
- 各 task は mediator advice を受け取る
- 各 task は orchestrator によって評価される
- paused tasks は high-risk safety check が block しない限り non-final のまま
- dispatch は final decision が continue の場合にのみ行われる

### Document-task batch flow

document-task checkpoint simulator は固定の document-task sequence を使用します。

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

後続の run は、必要な場合に human confirmation の後、checkpoint から resume できます。

## Batch scripts

Batch scripts は、local simulation runs の convenience wrappers として使われる場合があります。

推奨される script examples:

- local demo run
- checkpoint resume run
- tamper-evidence check run

これらの scripts は local developer utilities としてのみ扱うべきです。

次を行うべきではありません。

- production HMAC keys を埋め込む
- artifacts を自動 upload または submit する
- human confirmation を bypass する
- files を自動 delete する
- real personal or confidential data を処理する
- license または safety semantics を変更する
- tests または safety-check invariants を弱める

local demonstrations では、simulator が明示的に対応している場合にのみ demo key mode を使えます。production-like runs では、HMAC keys に environment variable または protected key file を使うべきです。

### Example batch-script roles

#### Local demo script

目的:

- local demonstration を実行する
- safe sample input を使う
- audit logs と simulated artifacts を local output directories へ書き込む
- external submission を避ける

#### Resume script

目的:

- checkpoint から resume する
- explicit resume confirmation を要求する
- 継続前に completed artifacts を verify する
- checkpoint integrity を保持する

#### Tamper-check script

目的:

- audit-log、checkpoint、artifact integrity behavior を verify する
- tamper-evidence detection を demonstrat する
- integrity verification が失敗した場合に human review のために pause する

## Recommended reading order

### Gate behavior and mediator separation を確認する場合

- mediator-based gate simulator を読む
- 対応する tests を読む

この path は、fixed check order、human-review transitions、blocked and non-blocked behavior、mediator separation、lightweight multi-task orchestration behavior を学ぶのに有用です。

### Checkpoint, resume, artifact integrity, and hash-chain behavior を確認する場合

- document-task checkpoint simulator を読む
- 対応する tests を読む

この path は、batch execution、checkpointing、artifact verification、tamper evidence、resume behavior を学ぶのに有用です。

### Emergency-contract behavior を確認する場合

- emergency contract gate-orchestration simulator を読む
- 対応する tests を読む

この path は、具体的な emergency-contract scenario が fixed checks、human-review checkpoints、audit verification、simulated artifact dispatch によって、real-world control や legal effect なしにどう評価されるかを学ぶのに有用です。

### Agent incident mediation behavior を確認する場合

- agent incident mediation simulator を読む
- 対応する tests を読む

この path は、diagnostic helper が simulated log/output mismatch を検出し、mediator へ escalate し、human review を trigger し、user instruction を記録し、external side effects なしに output consistency を verify する流れを学ぶのに有用です。

### Code anomaly handoff behavior を確認する場合

- code anomaly handoff simulator を読む
- 対応する tests を読む

この path は、metadata-only code-contract anomalies が検出され、user-controlled coordinator へ escalate され、human によって review され、external side effects なしに safe checkpoint handoff で処理される流れを学ぶのに有用です。

### Office task mediation behavior を確認する場合

- Office task mediation simulator を読む
- 対応する tests を読む

この path は、Word / Excel / PowerPoint-style consistency checks、masked metadata handoff、threshold-based human-review behavior、user-targeted draft revision without automatic application を学ぶのに有用です。

### Source-grounded Office orchestration behavior を確認する場合

- source-grounded Office orchestration simulator を読む
- 対応する tests を読む

この path は、source agents、source evidence packets、Office draft artifacts、mediator reconciliation、diagnostic packet handling、human-review relay、loop-limit enforcement が external side effects なしにどう連携するかを学ぶのに有用です。

挙動を検証する場合は、常に implementation と corresponding tests を一緒に読んでください。

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

このリポジトリでは、tests が simulator と orchestration logic の期待される挙動を定義することがよくあります。

挙動を確認するときは、implementation と corresponding tests を一緒に読んでください。

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

新しい version number が常に primary recommended entry point を意味するわけではありません。一部の files は historical comparison、reproducibility、versioned experiments のために保持されています。

## Gate and decision model

このリポジトリは、orchestration behavior を traceable にするために explicit gate decisions を使います。

一般的な decisions には次があります。

- `RUN`
- `PAUSE_FOR_HITL`
- `STOPPED`

一般的な解釈:

- `RUN`: simulator は次の check または dispatch step へ進んでよい。
- `PAUSE_FOR_HITL`: simulator は停止し human review を待つべき。
- `STOPPED`: simulator は blocking condition に到達した。

曖昧または相対的な要求は、安全だと黙って扱われるのではなく、人間レビューのために pause すべきです。

特に external side effects、policy violations、unsafe actions のような高リスク条件は、simulator contract に応じて block または human review に route されるべきです。

## Audit and integrity model

Audit and integrity behavior は simulator line によって異なります。

mediator-based simulator は lightweight audit events と safe context logging に焦点を当てます。

document-task checkpoint simulator はより強い integrity controls を追加します。

- audit log hash chain
- row-level HMAC
- checkpoint HMAC
- artifact SHA-256
- artifact HMAC
- completed-artifact verification on resume
- tamper-evidence detection

これらの仕組みは変更を検出可能にすることを目的とします。ローカル actor が disk 上の files を変更することを防ぐものではありません。

## Checkpoint and resume model

Checkpoint-based simulators は interrupted execution を支援するように設計されています。

checkpoint は次を記録する場合があります。

- run ID
- current task ID
- failed task ID
- failed check
- reason code
- task status
- artifact path
- artifact hash
- resume が許可されるか
- resume 前に human review が必要か

resume 時には、simulator が継続する前に completed artifacts を verify すべきです。verification が失敗した場合、silent に継続するのではなく、human review のために pause すべきです。

## Artifact model

simulator の artifact outputs は research artifacts として扱うべきです。

simulator line に応じて、出力には次が含まれる場合があります。

- artifact previews
- text-backed document-task outputs
- audit JSONL files
- checkpoint JSON files
- integrity metadata
- summary records

実際の document-generation code が追加されテストされていない限り、repository は simulated outputs を完全な本番 Office documents として説明すべきではありません。

## External side effects

External side effects には次のような行為が含まれます。

- email の送信
- files の upload
- artifacts の submit
- changes の push
- files の delete
- external APIs の呼び出し
- license semantics の変更

これらの actions は、simulator contract に応じて block、prohibit、または human-review gated のままであるべきです。

script または simulator は、external submission を silent に実行すべきではありません。

## Archive and historical files

一部の files は次の目的で保持されています。

- historical comparison
- reproducibility
- versioned experiments
- regression testing
- design comparison

`archive/` 配下の files は、current tests または documentation で明示的に参照されていない限り、通常は historical または reference material として扱うべきです。

## Language

- English README: `README.md`
- Japanese README: `README.ja.md`
- English security policy: `SECURITY.md`
- Japanese security policy translation: `SECURITY.ja.md`

## License

このリポジトリは split-license model を使用します。

- Software code: Apache License 2.0
- Documentation, diagrams, and research materials: CC BY-NC-SA 4.0

詳細は `LICENSE_POLICY.md` を参照してください。

## Project policies

- Security Policy
- Japanese Security Policy Translation
- License Policy
- Contributing Guide

## Disclaimer

このリポジトリは研究および教育目的で提供されています。

本番安全システム、法律ツール、医療ツール、金融ツール、規制遵守ツール、自律制御システムではありません。

ローカル、許可済み、防御的、教育的な文脈でのみ使用してください。
