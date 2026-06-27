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

Maestro Orchestrator は、複数のシミュレートされたAIエージェントが安全に協調できるかを検証するためのローカル研究ツールです。

何が起きたかを記録し、出力の一貫性を確認し、リスクがあると見なされる場合には人間レビューのために一時停止します。

このツールは、実システムを制御せず、外部へデータを送信せず、修正を自動適用せず、人間の判断を置き換えません。

研究者およびメンテナ向けに、このリポジトリは、明示的な安全チェック、監査ログ、チェックポイント、人間レビューを備えたマルチエージェントおよびエージェント型ワークフローを探索します。

このリポジトリは、ローカル・シミュレーションと防御的レビュー・ワークフローに焦点を当てています。次のような問いを検証するために設計されています。

- エージェント・ワークフローをいつ継続すべきか
- いつ安全に停止すべきか
- いつ人間レビューを求めるべきか
- ログと生成された出力が一貫しているか
- 助言的な検出結果が自動実行と分離されているか
- チェックポイントと監査記録によって予期しない変更を検出できるか

このプロジェクトは、本番用の自動化システムではありません。  
法的、医療、金融、規制、安全に関する保証は提供しません。

主要な設計原則は単純です。

> 振る舞いが不確実、リスクあり、不整合、または外部に影響を与える可能性がある場合、ワークフローは自動継続せず、安全に停止するか人間レビューを求めるべきです。

## このプロジェクトについて

実用上、このプロジェクトは次のような問いの検証に役立ちます。

- シミュレートされたエージェントはタスクに従ったか
- 出力は一貫していたか
- リスクがある場合にワークフローは停止したか
- 何が起きたかの記録があるか
- 結果に人間レビューが必要だったか

例はローカル・シミュレーションです。本番自動化ツールではありません。

## 研究者とメンテナ向け

このリポジトリは、次の要素を備えたマルチエージェント・オーケストレーションを探索します。

- 明示的なゲート判断
- 助言専用レビュー
- human-in-the-loop チェックポイント
- 改ざん検知可能な監査ログ
- 結果一貫性チェック
- フェイルクローズ動作
- 再現可能なローカル・シミュレーション
- 助言と実行の明確な分離

実装とテストは、ワークフローの振る舞いを検査、再現、レビューしやすくすることを目的としています。

## 用語集

- **Agent**: タスクの一部を実行するシミュレートされた作業者。
- **Maestro**: タスクをルーティングする調整役。人間の判断を置き換えません。
- **Tasukeru**: 防御的なリポジトリレビューに使われる助言レビュー・ワークフロー。
- **HITL**: human-in-the-loop。ワークフローが人間レビューのために一時停止すること。
- **Advisory-only**: ツールが検出結果を報告するが、自動修正、commit、push、merge は行わないこと。
- **Audit log**: 重要な判断やイベントの記録。
- **Checkpoint**: シミュレーション再開に使う保存状態。
- **Fail-closed**: 振る舞いが不確実またはリスクありの場合、継続せず安全に停止するかレビューを求めること。
- **External side effect**: ローカル・シミュレーション外の動作。例: 送信、アップロード、push、削除、deploy、実システム制御。

## 初学者向けの読み方

このリポジトリを初めて読む場合は、次の順で読んでください。

1. **Safety and scope** を読む。
2. **Responsible use and prohibited use** を読む。
3. **Advisory-only policy** を読む。
4. **Human review model** を読む。
5. 安全境界を理解した後にのみ **Current simulator lines** を読む。

このリポジトリは、研究および教育用のテストベンチです。  
出力は研究成果物であり、本番承認や安全保証ではありません。

振る舞いが不明確な場合は、変更を適用する前に、関連する実装とそのテストを併せて読んでください。

## 安全性と範囲

このリポジトリは研究プロトタイプです。

次の用途を意図していません。

- 本番環境での自律的意思決定
- 監督なしの実世界制御
- 法的、医療、金融、規制に関する助言
- 実際の個人データまたは機密運用データの処理
- 完全または普遍的な安全性カバレッジの実証
- 外部への自動送信、アップロード、送付、deploy
- 外部副作用に対する人間レビューの迂回

例は次のものとして読むべきです。

- ローカル研究シミュレーション
- 教育用リファレンス
- ガバナンスおよび安全性のテストベンチ
- フェイルクローズ設計例
- 人間レビュー・ワークフロー例
- 監査ログおよびチェックポイント完全性の実験
- ローカル・バッチ・オーケストレーション例

外部への submit、upload、push、send、deploy、delete、または実世界制御は、ブロックまたは人間レビュー・ゲート付きのままにする必要があります。

## 責任ある利用と禁止用途

レビュー・ワークフローとシミュレータ例は、ユーザーが所有するリポジトリ、または明示的な権限を持つリポジトリの防御的レビューを意図しています。

このリポジトリまたはそのツールを、次の目的で使用しないでください。

- 権限のない脆弱性探索
- 攻撃的偵察
- 第三者システムまたはコードの悪用
- 認証情報、トークン、シークレットの収集
- 許可のないリポジトリまたはシステムのスキャン
- 実ターゲットに対する exploit 手順の生成または検証
- アクセス制御、レート制限、セキュリティ境界の迂回
- 責任ある開示なしでの機密検出結果の公開

検出結果は、安全性、信頼性、追跡可能性、ガバナンスを改善するために使用してください。第三者またはオープンソースのコードをレビューする場合は、そのプロジェクトのセキュリティポリシーと責任ある開示プロセスに従ってください。

## 助言レビュー・ワークフロー

Tasukeru Analysis は、防御的なリポジトリレビューのための助言レビュー・ワークフローです。

これは、複雑化するマルチエージェントおよびエージェント型ワークフローの検査とガバナンスを支援することを意図しています。このようなワークフローは成長するにつれて、振る舞いの検査、説明、監査が難しくなる可能性があります。

次のようなレビュー支援の問いに焦点を当てます。

- 検出結果が適切なレビュー・レベルに分類されているか
- プロセスログと生成された出力が一貫しているか
- 不確実またはリスクのあるケースを人間レビューに戻すべきか
- 公開PRコメントが過度に詳細なセキュリティ情報を避けているか
- ワークフローが自動修正、commit、push、merge なしの助言専用のままか

このワークフローは、詳細な exploit 手順を開示せず、自律的な執行システムとして動作しません。詳細な検出結果は、人間レビューのためにワークフロー成果物とログに残されます。

次のような静的チェックおよびリポジトリ固有チェックを実行します。

- Ruff
- Bandit
- pip-audit
- リポジトリ固有のロジックチェック
- ドキュメントレビュー
- 人間レビュー分類

このワークフローは、すべての助言的検出結果を自動的なブロッキング失敗として扱うのではなく、保守性、安全レビュー、開発者の使いやすさを改善するよう設計されています。

警告を隠すことは目的ではありません。代わりに、能動的な修復候補、レビュー専用の検出結果、履歴バージョンの警告、ノイズの可能性を分離し、メンテナが優先すべき項目に集中できるようにします。

### ワークフロー堅牢化メモ

Tasukeru Analysis ワークフローには、防御的なワークフロー堅牢化チェックも含まれています。

セキュリティレビュー用の依存パッケージは再現性のためワークフロー内で固定されており、PRファイル一覧APIへのアクセスは想定されたGitHub APIホストに制限されています。PRファイルメタデータの取得中に、想定外のAPIホスト、HTTPエラー、またはネットワークエラーが発生した場合、ワークフローはトークンを含まない診断情報のみをログに出力し、その取得経路を安全側に停止します。

ワークフローは、トークン、Authorizationヘッダー、またはリクエストヘッダーをログに出力してはいけません。これらの制御は、このリポジトリの助言専用かつ人間レビュー優先の設計を支えるものであり、ワークフローを自動執行、自動修復、自動コミット、自動push、自動PR作成、自動merge、または自動デプロイの仕組みに変更するものではありません。

## 助言専用ポリシー

助言レビュー・ワークフローは次を行いません。

- branch を自動作成しない
- pull request を自動作成しない
- 変更を自動 commit しない
- 変更を自動 push しない
- 修正を自動適用しない
- pull request を自動 merge しない

人間レビューを必要とする検出結果のみ、PRコメントを生成する場合があります。

その他の検出結果は、人間レビューのために GitHub Step Summary とワークフロー成果物に収集されます。

このワークフローは、人間レビューの負荷を減らすためのものであり、人間の意思決定を置き換えるものではありません。

## 人間可読性ポリシー

このプロジェクトは、人間が安全に読み、レビューし、保守できるコードを優先します。

AIや自動化ツールが処理しやすいという理由だけで、変更を良い修正として扱うべきではありません。変更によって人間の可読性、レビュー容易性、保守性が下がる可能性がある場合は、人間レビューに戻すべきです。

## セキュリティレビュー出力ポリシー

セキュリティ関連の出力は、防御的レビューと安全な修正方針に焦点を当てるべきです。

公開PRコメントには、次を含めるべきではありません。

- exploit payload
- 攻撃コマンド
- 攻撃的な再現手順
- 段階的な exploit 指示
- 第三者ターゲットに対する exploit の詳細

セキュリティ関連の検出結果は、次に焦点を当てるべきです。

- 影響を受けるファイルと行
- レビューが必要な防御上の理由
- 期待される安全上の影響
- 安全な修正方向
- 人間レビューが必要かどうか

## 人間レビュー・モデル

このリポジトリは、実行可能な問題と想定ノイズを分離するためにレビュー・レベルを使います。

現在のレビュー・レベル:

- `HITL_REQUIRED`: merge または次の操作の前に人間レビューが必要
- `FIX_RECOMMENDED`: 具体的な修正が適切である可能性が高い
- `REVIEW_RECOMMENDED`: 判断前に文脈レビューが必要
- `NOISE_CANDIDATE`: テスト、デモ、研究シミュレーションでは許容される可能性が高い
- `INFO_ONLY`: 履歴バージョン警告を含む情報提供

この分類は既定では助言的です。メンテナが修正、文書化、抑制、受容のいずれにするかを判断する助けになります。

## アクティブ・レビュー・キュー

メインのレビュー・キューは小さく保つことを意図しています。

直ちに注意が必要な検出結果は、次として表示されるべきです。

- `HITL_REQUIRED`
- `FIX_RECOMMENDED`
- `REVIEW_RECOMMENDED`

これらの数がゼロの場合、リポジトリにはワークフローが現在優先して人間修復またはレビューを推奨するアクティブな助言項目がないことを意味します。

これは、リポジトリに警告がないことを意味しません。残りの警告が、ノイズの可能性または履歴/情報記録として分類されていることを意味します。

## 履歴バージョン警告

履歴バージョン警告は完全には除外されません。

助言ワークフローは、監査可視性に有用だがアクティブな修復対象ではない場合、置き換え済みまたは履歴的なシミュレータファイルの検出結果を `INFO_ONLY` として見える状態に保ちます。

これにより、アクティブ・レビュー・キューは現在人間の注意を必要とする検出結果に集中しつつ、次の目的で保持される古いバージョン付きファイルへの可視性を維持します。

- 再現性
- 回帰比較
- 履歴参照
- バージョン付き実験
- 設計比較

そのファイルが再びアクティブな入口点になる場合、履歴警告は再確認すべきです。

## 典型的な分類例

例:

### subprocess 実行

通常は `HITL_REQUIRED`。

subprocess 実行は外部副作用を生む可能性があるため、レビューが必要です。

### subprocess import

通常は `REVIEW_RECOMMENDED`。

subprocess を import すること自体は外部副作用ではありません。

### テスト内の assert 使用

通常は `NOISE_CANDIDATE`。

pytest テストでは `assert` が一般的に使われます。

### アクティブなランタイムコード内の assert 使用

通常は `FIX_RECOMMENDED`。

ランタイムの assert 文は Python の最適化フラグで除去される可能性があります。

### 置き換え済み履歴シミュレータファイル内の assert 使用

通常は `INFO_ONLY`。

完全に除外するのではなく、履歴バージョン警告として見える状態に保たれます。そのファイルがアクティブな入口点にならない限り、直ちに修正する必要はありません。

### テスト内の一時パス使用

`tmp_path` のような分離された pytest fixture を使う場合、通常は `NOISE_CANDIDATE`。

ハードコードされた共有パスを使っている場合はレビューすべきです。

### アクティブなシミュレーション内の疑似乱数生成器使用

通常は `REVIEW_RECOMMENDED`。

決定論的なシミュレーション乱数は、シークレット、トークン、認証、認可、暗号用途でなければ許容される場合があります。

受け入れる場合、その乱数がシミュレーション専用であることをコードに文書化すべきです。

### 置き換え済み履歴シミュレータファイル内の疑似乱数生成器使用

通常は `INFO_ONLY`。

履歴バージョン警告として見える状態に保たれます。セキュリティ上重要な振る舞いまたはアクティブなランタイム挙動に再利用されない限り、直ちに修正は不要です。

### 依存関係監査ツールによる依存関係脆弱性

通常は `FIX_RECOMMENDED`。

## 証拠、説明、予測

助言ワークフローは、検出結果に構造化された意思決定支援メタデータを付与する場合があります。

これには次が含まれます。

- `evidence`: ソースツール、ルールID、ファイル、行、スニペット、成果物参照
- `explanation`: 検出結果が重要な理由と、修正方向が提案される理由
- `fix_prediction`: 提案変更によって期待される安全性または保守性への影響
- `fix_verification`: 候補検証用のプレースホルダーまたは結果データ

`fix_prediction` は保証ではありません。レビュー補助です。

`fix_verification` を有効にする場合も、助言専用のままでなければなりません。候補チェックは一時ファイルまたは分離ファイルを使用し、人間が手動適用を明示的に選択しない限り、リポジトリファイルを変更してはいけません。

## 出力成果物

助言ワークフローは、次のようなレビュー成果物を生成する場合があります。

- 助言サマリー
- 人間レビュー・レポート
- 機械可読レビュー・データ
- 通知状態記録
- PRコメント下書き
- ドキュメント提案下書き
- 信頼度レポート
- 結果一貫性レポート
- 依存関係一貫性レポート

これらの成果物はレビュー資料です。リポジトリファイルを変更せず、自動適用されてはいけません。

人間可読レビュー・レポートには次が含まれる場合があります。

- ファイルパス
- 行番号
- 検出コード
- 問題サマリー
- レビュー・レベル
- 推奨アクション

機械可読レポートは、同じ意思決定支援データを構造化形式で提供します。

PRコメント下書きは、人間レビューを必要とし、PR通知の条件を満たす検出結果にのみ使用されます。

ドキュメント提案下書きには、提案される最小diff、全文下書き、ハッシュ、証拠、レビュー・チェックリストが含まれる場合があります。リポジトリファイルを変更せず、自動適用されてはいけません。

信頼度スコアはレビュー補助メタデータにすぎません。検出結果を安全に無視してよいことを示すものではなく、自動修正、自動PR作成、自動commit、自動push、自動merge を有効にしてはいけません。

結果一貫性レポートは、プロセスログと生成結果成果物が一致しているかを記録します。

依存関係一貫性レポートは、検出結果、影響構造、影響分類、レビュー・レベル、生成出力が一貫しているかを記録します。

これらはすべて助言専用です。検出結果の変更、分類変更、修正適用、commit作成、push、pull request の merge を自動的に行いません。

## 助言的な振る舞い

助言ワークフローは、メンテナが次を判断する助けになるべきです。

- どの検出結果がノイズの可能性が高いか
- どの検出結果をレビューすべきか
- どのファイルに注意が必要か
- なぜその検出結果が関係するのか
- 推奨される修正は何か
- merge 前に人間レビューが必要か
- アクティブな修復候補か、履歴バージョン警告か

ワークフローは人間レビューを置き換えません。より安全なリポジトリ保守のためのトリアージおよび文書化支援です。

## リポジトリの目的

このリポジトリの主目的は、エージェント型ワークフローを、明示的チェック、再現可能ログ、中断点、人間レビューによって制御する方法を探索することです。

プロジェクトは次を重視します。

- フェイルクローズ動作
- リスクのある操作前の人間レビュー
- 固定された安全チェック順序
- 安定した理由コード
- チェックポイントと再開動作
- 改ざん検知可能な監査記録
- 成果物完全性検証
- 再現可能なシミュレーション出力
- 助言と実行の明確な分離

このリポジトリは、完全なAI安全性カバレッジを提供すると主張しません。オーケストレーション挙動を研究するための研究・教育用テストベンチです。

## アーキテクチャ図

本番志向のドキュメント・オーケストレータ・シミュレータに関する詳細なアーキテクチャ図は、documentation ディレクトリにまとめられます。

図ドキュメントには次が含まれる場合があります。

- ドキュメント・オーケストレータ概要
- タスク処理フロー
- 監査ハッシュチェーン
- チェックポイント再開フロー
- データ構造マップ

README は概要を簡潔に保ちます。詳細図、参照ファイル、バンドル、ドキュメント資産は documentation index に配置してください。

## 現在のシミュレータ系統

このリポジトリには、複数のローカル限定シミュレータ系統があります。各系統は異なるオーケストレーションまたはレビュー問題に焦点を当てています。

### 1. ゲートベース mediator シミュレータ

このシミュレータは、単純なフローを研究します。

```text
Agent → Mediator → Orchestrator
```

主な特徴:

- agent がタスク入力を正規化する
- mediator は助言のみを行う
- mediator は実行権限を持たない
- orchestrator は固定順序でチェックを評価する
- 曖昧または相対的な要求は人間レビューにルーティングされる
- 高リスクケースはブロックされる場合がある
- raw text は永続化すべきではない
- 監査ログは直接的な個人データ漏えいを避けるべき

標準チェック順序:

```text
Meaning → Consistency → Ambiguity Review → External-Action Safety → Dispatch
```

このシミュレータは次の確認に役立ちます。

- 固定チェック順序
- 人間レビューへの遷移
- ブロックされる挙動とされない挙動
- mediator と orchestrator の分離
- 理由コードの期待値
- 軽量なマルチタスク・オーケストレーション挙動

### 2. ドキュメントタスク・チェックポイント・シミュレータ

このシミュレータは、より強い永続化と完全性制御を備えたドキュメントタスク・オーケストレーションを研究します。

主な特徴:

- タスク契約チェック
- 粗いトークン見積もり
- Word / Excel / PowerPoint 風タスク・シミュレーション
- タスクごとのチェックポイントと再開
- 監査ログ・ハッシュチェーン
- 保護されたチェックポイントファイル
- 成果物完全性記録
- 個人データに配慮した監査、チェックポイント、成果物書き込み
- 改ざん検知
- CLIベースのローカル・シミュレーション
- 外部への自動提出なし

重要な実装上の注意:

このシミュレータは、ドキュメントタスク結果を表すテキストベースの成果物を出力します。別途ドキュメント生成ライブラリが接続されテストされていない限り、完全に整形された Microsoft Office ドキュメントを生成すると主張しません。

ハッシュと HMAC は改ざん検知を提供します。物理的な書き込み防止は提供しません。実運用では、HMACキーは環境変数または保護されたキーファイルから供給し、リポジトリに commit してはいけません。

### 3. 緊急契約ゲート・オーケストレーション・シミュレータ

このシミュレータは、緊急契約シナリオとゲートベース・オーケストレーション・フローを組み合わせます。

これは小さな統合概念実証であり、本番用の契約、法務、信号制御システムではありません。

主な特徴:

- 緊急契約シナリオ
- 固定された安全チェック順序
- 曖昧な優先順位のレビュー挙動
- 証拠検証と捏造証拠検出
- 人間承認チェックポイント
- 管理者 finalize チェックポイント
- 高リスク条件に対するブロック停止不変条件
- シミュレートされた契約ドラフト成果物生成
- 改ざん検知可能な監査行
- 実世界の信号制御なし
- 法的効力なし
- 外部提出、アップロード、送信、API呼び出し、deploy なし

標準統合フロー:

```text
Meaning → Consistency → Ambiguity Review → Evidence Check → Human Authorization
→ Draft → Safety Review → Draft Review → External-Action Safety
→ Admin Finalize → Dispatch
```

このシミュレータは次の確認に役立ちます。

- 緊急契約シナリオの扱い
- 相対的優先順位評価
- 捏造証拠時の一時停止挙動
- 実世界制御のブロック
- ユーザーおよび管理者の停止パス
- シミュレート成果物の dispatch のみ
- 監査ログ検証
- 正常系および異常系にまたがる安全不変条件

### 4. インフラ・ライフライン mediation シミュレーション

このシミュレータは、3つのインフラ・エージェントを含む制約付き資源配分シナリオをモデル化します。

- electricity
- water
- gas

これは、障害時資源制約下で mediator が提案専用の配分計画を作成する方法を研究する、ローカルかつ seed 再現可能な研究シミュレーションです。

主な特徴:

- 通常資源要求を持つ3つのインフラ・エージェント
- 障害モードでの総資源制約
- 最小保証
- 優先重み
- life-risk score
- 不足率を考慮した配分
- シミュレートされた人間判断
- JSONおよびstdout出力
- 外部APIアクセスなし
- 実インフラ制御なし
- 自動復旧なし
- 自動停止または切断なし

mediator は配分案のみを作成します。実インフラを制御せず、実世界の復旧操作を行いません。

シミュレートされた人間オペレーターは次を返す場合があります。

- `APPROVE`
- `REJECT`
- `REDEFINE`
- `REQUEST_ALTERNATIVES`

このシミュレータは次の確認に役立ちます。

- 制約付き資源配分挙動
- 提案専用 mediation
- seed による再現性
- 人間レビュー分岐挙動
- safety-boundary flags
- JSON出力挙動
- 配分合計が利用可能資源制限内に収まること

### 5. エージェント・インシデント mediation シミュレーション

このシミュレータは、1つのシミュレートされたエージェントがオーケストレーション中に契約外アクションを行う、ローカル限定のインシデント mediation フローをモデル化します。

診断レビュー helper がログ/出力不一致を検出し、レビュー成果物を作成し、検出結果を mediator にエスカレーションします。その後 mediator は、インメモリ結果を適用する前にシミュレートされた人間レビューを実行します。

主な特徴:

- シミュレートされた異常エージェント挙動
- ログ/出力不一致検出
- mediator へのエスカレーション packet
- シミュレートされた人間判断分岐
- インメモリの停止または承認結果のみ
- 監査ログ検証
- 依存関係一貫性検証
- 結果一貫性検証
- ローカル成果物のみ
- 外部APIアクセスなし
- 実プロセス制御なし
- 自動修正、commit、push、merge なし

このシミュレータは次の確認に役立ちます。

- 異常エージェント挙動がログ/出力不一致から検出されるか
- 診断 helper が agent を直接停止せずエスカレーションするか
- mediator が stop または authorization result を適用する前に人間レビューを行うか
- シミュレートされたユーザー指示が記録されるか
- 正常エージェントが誤って停止またはロックされないか
- 監査ログと生成成果物が一貫しているか

### 6. コード異常 handoff シミュレーション

このシミュレータは、ローカル限定の code-contract anomaly handoff フローをモデル化します。

診断レビュー helper がメタデータのみの code-contract anomaly を検出し、その検出結果をユーザー制御の coordinator にエスカレーションします。coordinator は自分で判断しません。シミュレートされた人間レビューを要求し、その後シミュレートされたユーザー指示だけを実行します。

主な特徴:

- メタデータのみの code-contract anomaly 検出
- ユーザー制御 coordinator へのエスカレーション
- coordinator による自律判断なし
- シミュレートされた人間指示の記録
- 安全なチェックポイント handoff と再開
- 監査ログ検証
- 依存関係一貫性検証
- 結果一貫性検証
- コード実行なし
- マルウェア挙動なし
- 外部APIアクセスなし
- 実プロセス制御なし
- 自動修正、commit、push、merge なし

このシミュレータは次の確認に役立ちます。

- code-contract anomaly が検出されるか
- 検出結果がユーザー制御 coordinator にエスカレーションされるか
- coordinator が自己判断ではなく人間レビューを要求するか
- シミュレートされたユーザー指示が記録されるか
- lock 分岐と quarantine-handoff-resume 分岐の両方が動作するか
- standby handoff が安全なチェックポイントから再開するか
- 監査ログと生成成果物が一貫しているか

### 7. エージェント・インシデント risk-report handoff シミュレーション

このシミュレータは、ローカル限定のエージェント・インシデント mediation 系統に、report-only のリスク推定とユーザー制御 handoff を追加します。

基本的なインシデント設定は同じです。1つのシミュレートされたエージェントが契約外アクションを行い、診断 helper がログ/出力不一致を検出し、実行はローカル限定のままです。

主な特徴:

- シミュレートされた異常エージェント挙動
- ログ/出力不一致検出
- report-only リスク推定
- 計算 trace 記録
- ユーザー制御 coordinator へのエスカレーション
- シミュレートされた人間指示の記録
- lock 分岐
- quarantine-handoff-resume 分岐
- standby agent promotion
- チェックポイントベースのタスク再開
- 監査ログ検証
- 依存関係一貫性検証
- リスクレポート検証
- 結果一貫性検証
- 外部APIアクセスなし
- 実プロセス制御なし
- マルウェア挙動なし
- 自動修正、commit、push、merge なし

このシミュレータは次の確認に役立ちます。

- risk reporting と handoff を追加しても incident flow が動作するか
- 高リスクのシミュレートされた incident がユーザー制御 coordinator にルーティングされるか
- シミュレートされたユーザー指示が記録されるか
- lock 分岐と quarantine-handoff-resume 分岐の両方が動作するか
- standby handoff がチェックポイントから再開するか
- 正常エージェントが誤って lock、quarantine、resume されないか
- 監査ログ、リスクレポート、チェックポイント、生成成果物が一貫しているか

### 8. Office タスク mediation シミュレーション

このシミュレータは、Word / Excel / PowerPoint 風の合成成果物を使うローカル限定の Office タスク mediation フローをモデル化します。

生成された文書、スプレッドシート、プレゼンテーション出力が、元のユーザータスク指示と一致しているかを確認します。診断 helper はログを読み、異常を検出し、リスク資料のみを出力します。mediator はマスク済みメタデータ packet のみを受け取り、元のタスクと生成出力の差異を調整します。coordinator は自分で判断しません。ユーザーが選択した agent にのみタスクを配布し、スコアが閾値を超えた場合にのみ人間レビューを起動し、明示的にユーザーが選択したアクションのみを実行します。

シミュレーションフロー:

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

このシミュレータは実際の Office ファイルを生成しません。合成された Word / Excel / PowerPoint 風レコードを使い、一貫性、マスキング、閾値挙動、人間レビュー・ルーティング、draft-only revision propagation を検証します。

主な特徴:

- 固定された Word / Excel / PowerPoint 合成タスクセット
- ユーザー選択 agent への dispatch
- 元タスク snapshot と hash 固定 task baseline
- 診断ログ分析とマスク済みメタデータ handoff
- mediator への raw log handoff なし
- Office 出力一貫性チェック
- 利益、数式、チャート、結論の不一致検出
- 個人データおよび機密 signal のマスキング
- 閾値ポリシー: `score == 0.8` は warning / draft review のみ
- 閾値ポリシー: `score > 0.8` は人間レビューを起動
- user-scoped draft revision proposals のみ
- 関連 agent は draft revision proposals のみを作成
- coordinator に自律判断権限なし
- 監査ログ検証
- 結果一貫性検証
- 必須 Word / Excel / PowerPoint 成果物の完全性チェック
- 必須成果物の欠落を検出
- zero values は有効値として扱う
- safety-buffer metadata は明示的かつレビュー可能
- 内部 raw agent logs は既定では保存されず、明示的なシミュレーション専用 opt-in が必要
- 実 Office 文書生成なし
- 外部APIアクセスなし
- 実プロセス制御なし
- 自動修正、commit、push、merge なし

このシミュレータは次の確認に役立ちます。

- Word / Excel / PowerPoint 風出力が一貫しているか
- Excel 数式結果と PowerPoint チャート値が衝突していないか
- Word テキスト、スプレッドシート値、プレゼン要約が食い違っていないか
- 元のユーザー指示が比較 baseline のままか
- 個人データと機密 signal が mediation 前にマスクされるか
- mediator がマスク済みメタデータのみを使用するか
- `score == 0.8` が人間レビューを起動しないか
- `score > 0.8` が人間レビューを起動するか
- user-targeted revision prompts が draft proposals のみを生成するか
- coordinator が自己判断を避け、明示的にユーザーが選択したアクションのみを実行するか

### 9. Trust-to-risk automation draft extension

このドラフト拡張は、Office タスク mediation 系統に automation-entry と automation-continuation diagnostics を追加します。

主な特徴:

- trust-score に基づく automation entry diagnosis
- `trust_score == 0.9` は自動化適格ではない
- `trust_score > 0.9` はユーザー承認後に automation candidate になり得る
- 自動化開始後は automation-risk に基づいて継続診断
- `automation_risk_score < 0.1` は自動化を継続
- `automation_risk_score >= 0.1` はフェイルクローズ停止を起動
- coordinator relay-only temporary automation suspension
- automation resume にはユーザーレビューが必要
- diagnostic helper は diagnostic-only のままで agent に直接命令しない
- 自動修正、commit、push、merge なし

この拡張は次の確認に役立ちます。

- automation entry が `trust_score > 0.9` によって gate されたままか
- `trust_score == 0.9` が非適格として扱われるか
- automation active 前にユーザー承認が必要か
- automation continuation が trust scoring から risk scoring に切り替わるか
- `automation_risk_score == 0.1` がフェイルクローズ停止になるか
- 停止した automation の再開にユーザーレビューが必要か
- 自動修正、commit、push、merge が無効のままか

### 10. Source-grounded Office orchestration simulation

このシミュレータは、Office タスク mediation 系統を、成果物一貫性チェックから source-grounded multi-agent orchestration へ拡張します。

主な追加点:

- primary / secondary / tertiary synthetic source agents
- raw source logs ではなく source evidence packets
- source-to-artifact consistency checks
- source packets に基づく Office draft artifacts
- source conflicts と artifact contradictions に対する mediator reconciliation
- diagnostic source/artifact packet boundary checks
- 個人データおよび機密 signal のマスキング
- unsupported-claim detection
- missing artifact detection
- unknown selected-agent detection
- request tampering detection
- 固定 loop limit 付き retry loop
- 最終出力は draft-only のままでユーザーレビューが必要

このシミュレータはローカル限定かつ合成のままです。実 source を fetch せず、実 Office ファイルを生成せず、外部APIを呼ばず、実プロセスを制御せず、自動修正、commit、push、merge を行いません。

このシミュレータは次の確認に役立ちます。

- source packets と生成成果物が一貫しているか
- unsupported claims が review にルーティングされるか
- source conflicts が報告されるか
- 必須成果物の欠落が検出されるか
- unknown selected agents が検出されるか
- unsafe mediator request keys が拒否されるか
- request tampering が拒否されるか
- reconciliation が loop limit 後に停止するか
- 監査ログと生成成果物が一貫しているか

### 10.1 Mediator / Maestro gate hardening draft

このドラフト系統は、明示的な mediator-to-Maestro review routing と fail-closed score handling を追加して、source-grounded Office orchestration simulation を拡張します。

ファイル:

- `agent_source_grounded_office_orchestration_sim_v1_0_0_refactored_integrated_draft.py`
- `agent_source_grounded_office_orchestration_sim_v1_0_1_fail_closed_hardening_draft.py`
- `tests/test_agent_source_grounded_office_orchestration_sim_v1_0_1_fail_closed_hardening_contract.py`

`v1.0.0` ファイルは比較 baseline として保持されます。  
`v1.0.1` ファイルは、baseline の検証済み numeric-boundary behavior を維持しながら、無効な threshold score input に対する fail-closed handling を追加します。

Mediator / Maestro gate decisions:

- `HITL_REVIEW_READY`: 結果は人間レビュー担当者に提示可能だが、自動的に受け入れられたり外部適用されたりしない。
- `PAUSE_FOR_HITL`: responsibility floor が満たされない場合、remaining conformity threshold が満たされない場合、または threshold input を安全に評価できない場合にワークフローを一時停止する。
- `ROUTED_TO_PRECHECK`: severe condition または structural invariant violation が検出された場合、通常の candidate comparison に入らない。

Fail-closed threshold behavior:

```text
invalid score input
→ PAUSE_FOR_HITL
```

対応する contract test は次をカバーします。

- invalid score input が `PAUSE_FOR_HITL` に fail closed すること
- baseline numeric threshold behavior の維持
- responsibility-floor failures が score によって救済されないこと
- severe conditions と structural invariant violations が `ROUTED_TO_PRECHECK` にルーティングされること
- candidate presentation と next-stage approval の分離
- user acceptance によって `PAUSE_FOR_HITL` または `ROUTED_TO_PRECHECK` が bypass されないこと
- Maestro による自律的な最終判断または外部アクションがないこと
- Tasukeru、Mediator、Maestro が不正な `sealed=True` state を発行しないこと
- 決定論的な `runs=100` および `runs=1000` distribution checks

これはローカル限定の研究および検証ドラフトです。  
自動採用、自動外部アクション、自動修正、自動commit、自動push、自動merge を認可しません。

### 10.2 Security orchestration isolated verification authorization simulation

このシミュレータは、公開系統を防御的、ローカル限定、助言専用に保ちながら、オーケストレーションモデルを security-review sub-agents へ適用します。

ファイル:

- `security_orchestration_isolated_verification_authorization_sim.py`

主な特徴:

- security-review sub-agent routing
- ユーザー承認済み read-only static audit flow
- static candidate finding records
- primary and secondary mediation records
- 実行しない draft remediation proposal records
- human-review disposition records
- bounded isolated-verification authorization records
- authorization、verification execution、application、merge、close の明示的分離
- isolated verification planning のために任意の command text を受け取らない
- exploit execution なし
- external scanning なし
- external system access なし
- repository modification なし
- automatic remediation なし
- automatic application なし
- automatic merge なし
- production safety guarantee なし

このシミュレータは次の確認に役立ちます。

- security-review sub-agents が read-only advisory boundary 内に留まるか
- candidate findings が exploitability の証明と分離されたままか
- remediation drafts が non-executing proposal records のままか
- isolated verification が bounded authorization plan のみとして表現されるか
- その後の execution、application、merge、close、post-change audit progression が個別に人間レビューで gate されるか
- security review orchestration が advice と action の明確な境界を維持できるか

公開範囲の境界:

この公開系統は、authorization records、static candidate review、mediation、human-review routing、bounded non-executing proposal records の範囲に留まるべきです。Offensive capability expansion、external execution、external scanning、automatic remediation、automatic application、automatic merge、autonomous security enforcement、または実ターゲットに対する exploit validation は範囲外です。

### AI-to-AI Mediation Control Plane v0.7 draft evaluator

`evaluator_pseudocode.py` ファイルは、ローカル研究および教育用途の draft-only evaluator sketch です。要求または観測された振る舞いを L0 から L6 の外部アクション・レベルに分類し、高リスクケースを次のようにルーティングします。

* L4 -> `HUMAN_REVIEW_REQUIRED`
* L5 -> `ISOLATED_REVIEW_REQUIRED`
* L6 -> `STOP_AND_PRESERVE`

この evaluator は副作用を持ちません。外部APIを呼び出さず、candidate code を実行せず、リポジトリファイルを変更せず、deploy を承認せず、安全閾値を変更せず、モデルを訓練せず、自己改善ループを実装しません。

本番承認、自律的執行、deploy 承認、または安全保証は提供しません。外部に影響する行為、自己改善、または evolution-loop 関連アクションの前には、引き続き人間レビューが必要です。

### AI-to-AI Mediation Control Plane v0.8 Explainable Patch Gate draft

`evaluator_pseudocode_v0_8_explainable_patch_gate.py` ファイルは、v0.7 evaluator のバージョン付きドラフト拡張です。

既存の L0-L6 外部アクション分類モデルを維持しつつ、AI生成パッチに対する draft-only patch accountability checks を追加します。

v0.8 draft では、AI生成パッチ案に、人間が読める説明、証拠、影響分析、検証結果、および説明とdiffの整合性を含めることを求めます。

Patch accountability findings は、本来 continue できるケースを `HUMAN_REVIEW_REQUIRED` にルーティングする場合があります。ただし、既存の高リスクルーティングを弱めてはいけません。

* L4 -> `HUMAN_REVIEW_REQUIRED`
* L5 -> `ISOLATED_REVIEW_REQUIRED`
* L6 -> `STOP_AND_PRESERVE`

v0.8 draft は、自動パッチ適用、commit、push、pull request 作成、merge、deployment 要求も、人間レビューを必要とする禁止的自動アクションとして扱います。

このファイルはバージョン付き研究ドラフトであり、`evaluator_pseudocode.py` の置き換えではありません。

関連テストファイル:

* `tests/test_evaluator_pseudocode_v0_8_explainable_patch_gate.py`

#### v0.7 との差分

v0.7 は、外部アクション、自己改善挙動、evaluator 変更、evolution-loop signals を L0-L6 review levels に分類することに焦点を当てています。

v0.8 は、その分類モデルを維持しつつ、AI生成パッチの patch accountability checks を追加します。追加されたチェックは、パッチに説明、証拠、影響分析、検証結果、説明とdiffの整合性があるかを確認します。

v0.8 draft は意図的に別ファイルとしてバージョン管理されているため、v0.7 evaluator と v0.7 tests は変更されません。

#### v0.8 テストが確認すること

v0.8 test file は次を確認します。

- patch-accountability fields の default が `False` であること
- 説明のない生成パッチは人間レビューを必要とすること
- security-related patches は support fields が存在しても人間レビューを必要とすること
- already-applied patches は人間レビューを必要とすること
- explanation/diff mismatches は人間レビューを必要とすること
- 十分にサポートされた、未適用で非セキュリティの patch proposals は、base route が許す場合 `CONTINUE` のままでよいこと
- automatic patch application、commit、push、PR creation、merge、deployment requests は人間レビューを必要とすること
- 既存の L4、L5、L6 routes が変更されないこと
- patch-accountability overlay が L5 または L6 を弱めないこと
- blocked actions に automatic patch actions が含まれること
- human-review stub に patch-accountability fields と reason codes が含まれること
- versioned evaluator が `py_compile` に通ること

## バッチ実行と再開

このリポジトリには、バッチ形式のオーケストレーション例が含まれます。

バッチ実行とは、複数のドキュメント関連タスクを単一のオーケストレーション実行として評価しながら、チェック判断、監査記録、中断点を維持することです。

### Mediator-based batch flow

mediator-based simulator は、複数タスクを1回の実行で受け取ることができます。

使用例:

- 複数の spreadsheet または slide タスクをまとめて評価する
- タスク単位の check outcomes を比較する
- 複数タスクにまたがる人間レビュー挙動を確認する
- オーケストレーション前の mediator advice を検証する
- 各タスクが固定チェック順序を通ることを確認する

この系統は次に焦点を当てる場合に有用です。

- マルチタスク・チェック挙動
- mediator separation
- ambiguity review と human-review transitions
- reason-code stability
- 軽量な orchestration tests

タスク列の例:

- T1: spreadsheet task
- T2: presentation task
- T3: human review を必要とする ambiguous task

期待される挙動:

- 各タスクは agent によって正規化される
- 各タスクは mediator advice を受ける
- 各タスクは orchestrator によって評価される
- paused tasks は、高リスク safety check がブロックしない限り non-final のまま
- dispatch は final decision が continue の場合にのみ発生する

### Document-task batch flow

document-task checkpoint simulator は、固定されたドキュメントタスク列を使います。

```text
Word → Excel → PowerPoint
```

この系統は次に焦点を当てる場合に有用です。

- batch task execution
- per-task checkpointing
- interruption and resume
- artifact integrity records
- protected checkpoints
- audit log hash chains
- tamper-evidence detection

タスクが中断された場合、シミュレータは次を記録します。

- failed task ID
- failed check
- reason code
- checkpoint path
- resume requirement
- applicable な場合の human confirmation requirement

後続実行では、必要な場合に人間確認後、チェックポイントから再開できます。

## バッチスクリプト

バッチスクリプトは、ローカル・シミュレーション実行の便利用 wrapper として使う場合があります。

推奨されるスクリプト例:

- local demo run
- checkpoint resume run
- tamper-evidence check run

これらのスクリプトは、ローカル開発者ユーティリティとしてのみ扱うべきです。

行ってはいけないこと:

- production HMAC keys を埋め込む
- 成果物を自動 upload または submit する
- human confirmation を迂回する
- ファイルを自動削除する
- 実際の個人データまたは機密データを処理する
- license または safety semantics を変更する
- tests または safety-check invariants を弱める

ローカル・デモでは、シミュレータが明示的にサポートする場合に限り、demo key mode を使用できます。本番に近い実行では、HMAC keys は環境変数または保護されたキーファイルを使うべきです。

### バッチスクリプト役割の例

#### Local demo script

目的:

- ローカル・デモを実行する
- 安全なサンプル入力を使う
- audit logs と simulated artifacts をローカル出力ディレクトリに書き込む
- 外部提出を避ける

#### Resume script

目的:

- チェックポイントから再開する
- 明示的な resume confirmation を要求する
- 継続前に completed artifacts を検証する
- checkpoint integrity を維持する

#### Tamper-check script

目的:

- audit-log、checkpoint、artifact integrity behavior を検証する
- tamper-evidence detection を実演する
- integrity verification が失敗した場合、人間レビューのために一時停止する

## 推奨読書順

gate behavior と mediator separation について:

- mediator-based gate simulator を読む
- 対応する tests を読む

この経路は、fixed check order、human-review transitions、blocked and non-blocked behavior、mediator separation、軽量な multi-task orchestration behavior を研究するのに役立ちます。

checkpoint、resume、artifact integrity、hash-chain behavior について:

- document-task checkpoint simulator を読む
- 対応する tests を読む

この経路は、batch execution、checkpointing、artifact verification、tamper evidence、resume behavior を研究するのに役立ちます。

emergency-contract behavior について:

- emergency contract gate-orchestration simulator を読む
- 対応する tests を読む

この経路は、具体的な emergency-contract scenario が、fixed checks、human-review checkpoints、audit verification、real-world control または legal effect のない simulated artifact dispatch によってどのように評価されるかを研究するのに役立ちます。

agent incident mediation behavior について:

- agent incident mediation simulator を読む
- 対応する tests を読む

この経路は、diagnostic helper が simulated log/output mismatch を検出し、mediator にエスカレーションし、人間レビューを起動し、ユーザー指示を記録し、外部副作用なしに output consistency を検証する方法を研究するのに役立ちます。

code anomaly handoff behavior について:

- code anomaly handoff simulator を読む
- 対応する tests を読む

この経路は、metadata-only code-contract anomalies が検出され、user-controlled coordinator にエスカレーションされ、人間にレビューされ、外部副作用なしに safe checkpoint handoff を通じて処理される方法を研究するのに役立ちます。

Office task mediation behavior について:

- Office task mediation simulator を読む
- 対応する tests を読む

この経路は、Word / Excel / PowerPoint 風 consistency checks、masked metadata handoff、threshold-based human-review behavior、automatic application なしの user-targeted draft revision を研究するのに役立ちます。

source-grounded Office orchestration behavior について:

- source-grounded Office orchestration simulator を読む
- 対応する tests を読む

この経路は、source agents、source evidence packets、Office draft artifacts、mediator reconciliation、diagnostic packet handling、human-review relay、loop-limit enforcement が、外部副作用なしにどのように連携するかを研究するのに役立ちます。

振る舞い検証では、常に実装と対応するテストを併せて読んでください。

これは特に次の場合に重要です。

- safety-check invariants
- reason-code expectations
- human-review transitions
- blocked and non-blocked behavior
- checkpoint and resume behavior
- tamper-evidence behavior
- reproducibility checks
- benchmark expectations
- batch execution behavior

## テストと振る舞い

このリポジトリでは、多くの場合、テストがシミュレータおよびオーケストレーション・ロジックの期待される挙動を定義します。

振る舞いを確認する場合は、実装と対応するテストを併せて読んでください。

テストでは次を検証する場合があります。

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

新しいバージョン番号が、常にそのファイルが主要な推奨入口点であることを意味するわけではありません。一部のファイルは、履歴比較、再現性、またはバージョン付き実験のために保持されます。

## ゲートと判断モデル

このリポジトリは、オーケストレーション挙動を追跡可能にするために明示的なゲート判断を使います。

一般的な判断には次があります。

- `RUN`
- `PAUSE_FOR_HITL`
- `STOPPED`

一般的な解釈:

- `RUN`: シミュレータは次のチェックまたは dispatch step に進める
- `PAUSE_FOR_HITL`: シミュレータは一時停止し、人間レビューを待つべき
- `STOPPED`: シミュレータはブロック条件に到達した

曖昧または相対的な要求は、暗黙に安全扱いされるのではなく、人間レビューのために一時停止すべきです。

高リスク条件、特に外部副作用、ポリシー違反、または危険なアクションは、シミュレータ契約に応じてブロックまたは人間レビューにルーティングされるべきです。

## 監査と完全性モデル

監査と完全性の挙動はシミュレータ系統ごとに異なります。

mediator-based simulator は、軽量な audit events と safe context logging に焦点を当てます。

document-task checkpoint simulator は、より強い完全性制御を追加します。

- audit log hash chain
- row-level HMAC
- checkpoint HMAC
- artifact SHA-256
- artifact HMAC
- resume 時の completed-artifact verification
- tamper-evidence detection

これらの仕組みは変更を検出可能にするためのものです。ローカルの行為者がディスク上のファイルを変更することを防ぐものではありません。

## チェックポイントと再開モデル

チェックポイントベースのシミュレータは、中断された実行をサポートするよう設計されています。

チェックポイントには次が記録される場合があります。

- run ID
- current task ID
- failed task ID
- failed check
- reason code
- task status
- artifact path
- artifact hash
- resume が許可されるか
- resume 前に人間レビューが必要か

再開時には、シミュレータが継続する前に completed artifacts を検証するべきです。検証に失敗した場合、黙って継続するのではなく、人間レビューのために一時停止すべきです。

## 成果物モデル

シミュレータの成果物出力は研究成果物として扱うべきです。

シミュレータ系統によって、出力には次が含まれる場合があります。

- artifact previews
- text-backed document-task outputs
- audit JSONL files
- checkpoint JSON files
- integrity metadata
- summary records

実際のドキュメント生成コードが追加されテストされていない限り、シミュレートされた出力を完全な本番 Office ドキュメントとして説明すべきではありません。

## 外部副作用

外部副作用には次のようなアクションが含まれます。

- メール送信
- ファイルのアップロード
- 成果物提出
- 変更の push
- ファイル削除
- 外部API呼び出し
- ライセンス意味論の変更

これらのアクションは、シミュレータ契約に応じて、ブロック、禁止、または人間レビュー・ゲート付きのままにすべきです。

いかなる script または simulator も、外部提出を黙って実行すべきではありません。

## アーカイブと履歴ファイル

一部のファイルは次の目的で保持されます。

- 履歴比較
- 再現性
- バージョン付き実験
- 回帰テスト
- 設計比較

`archive/` 配下のファイルは、現在のテストまたはドキュメントで明示的に参照されていない限り、一般には履歴または参照資料として扱うべきです。

## 言語

- English README: `README.md`
- Japanese README: `README.ja.md`
- English security policy: `SECURITY.md`
- Japanese security policy translation: `SECURITY.ja.md`

## ライセンス

このリポジトリは分割ライセンスモデルを使用します。

- ソフトウェアコード: Apache License 2.0
- ドキュメント、図、研究資料: CC BY-NC-SA 4.0

詳細は `LICENSE_POLICY.md` を参照してください。

## プロジェクトポリシー

- [Security Policy](SECURITY.md)
- [Japanese Security Policy Translation](SECURITY.ja.md)
- [License Policy](LICENSE_POLICY.md)
- [Contributing Guide](CONTRIBUTING.md)

## 免責事項

このリポジトリは、研究および教育目的でのみ提供されます。

本番安全システム、法務ツール、医療ツール、金融ツール、規制遵守ツール、自律制御システムではありません。

ローカル、許可済み、防御的、教育的な文脈でのみ使用してください。
