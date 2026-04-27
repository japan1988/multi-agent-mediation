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

---

Maestro Orchestrator は、マルチエージェントのガバナンス、
fail-closed 制御、HITL エスカレーション、チェックポイントベースの再開、
および改ざん検知可能なシミュレーションワークフローを研究するための
オーケストレーション・フレームワークです。

このリポジトリには、複数のシミュレーター系統が含まれています。
一部のファイルは KAGE 風のゲート挙動と Mediator 分離に焦点を当て、
別のファイルはドキュメントタスクのバッチ実行、チェックポイント、
監査整合性、成果物検証に焦点を当てています。

---

## 安全性と適用範囲

このリポジトリは **研究用プロトタイプ** です。

次の用途を意図したものではありません。

- 本番環境での自律的な意思決定
- 監督なしの現実世界制御
- 法務、医療、金融、規制に関する助言
- 実在する個人データや機密性のある業務データの処理
- 完全または普遍的な安全性保証の実証
- 外部提出、アップロード、送信、デプロイの自動実行
- 外部副作用に対する HITL レビューの迂回

各サンプルは、次のものとして読んでください。

- 研究用シミュレーション
- 教育用リファレンス
- ガバナンス / 安全性テストベンチ
- fail-closed と HITL 設計の例
- 監査ログとチェックポイント整合性の実験
- ローカルシミュレーション用のバッチ・オーケストレーション例

外部提出、アップロード、push、送信などの操作は、HITL によって
ゲートされるべきです。

---

## 責任ある利用と禁止事項

Tasukeru Analysis および各種シミュレーター例は、ユーザー自身が所有する
リポジトリ、または明示的な許可を得たリポジトリの防御的レビューを目的としています。

このリポジトリおよび付属ツールを、次の目的で使用してはいけません。

- 無許可の脆弱性調査
- 攻撃目的の偵察
- 第三者のシステムやコードの悪用
- 認証情報、トークン、シークレットの探索または取得
- 許可のないリポジトリやシステムのスキャン
- 実在する対象に対する exploit 手順の生成または検証
- アクセス制御、レート制限、セキュリティ境界の回避
- 責任ある開示を行わないままの機微な発見事項の公開

検出結果は、安全性、信頼性、追跡可能性、ガバナンスを改善するために
使用してください。第三者または OSS のコードをレビューする場合は、
対象プロジェクトのセキュリティポリシーと責任ある開示手順に従ってください。

---

## リポジトリの目的

このリポジトリの主な目的は、エージェント型ワークフローを、
明示的なゲート、再現可能なログ、中断点、人間によるレビューによって
どのように制御できるかを探ることです。

このプロジェクトでは、次の点を重視しています。

- fail-closed 挙動
- HITL エスカレーション
- ゲート順序の不変条件
- reason code の安定性
- チェックポイント / 再開挙動
- 改ざん検知可能な監査記録
- 成果物の整合性検証
- 再現可能なシミュレーション出力
- 助言と実行の明確な分離

このリポジトリは、完全な AI 安全性を提供すると主張するものではありません。
オーケストレーション挙動を研究・教育するためのテストベンチです。

---

## アーキテクチャ図

実運用寄り Doc Orchestrator シミュレーターの詳細な構成図は、
以下のドキュメントにまとめています。

- [Doc Orchestrator Architecture Diagrams](docs/architecture.md)

このドキュメントには、次の図が含まれています。

- Doc Orchestrator 全体構成
- タスク処理フロー
- 監査 HMAC チェーン
- チェックポイント再開フロー
- データ構造マップ

個別の図への直接リンクも利用できます。

- [Doc Orchestrator 全体構成](docs/doc-orchestrator-overview.png)
- [タスク処理フロー](docs/task-processing-flow.png)
- [監査 HMAC チェーン](docs/audit-hmac-chain.png)
- [チェックポイント再開フロー](docs/checkpoint-resume-flow.png)
- [データ構造マップ](docs/data-structure-map.png)

その他の図、参照ファイル、バンドル、ドキュメント資産は、
以下を参照してください。

- [Documentation Index](docs/index.md)

README 本体では概要を簡潔に示し、詳細な構成図は `docs/architecture.md` に、
より広いドキュメント目次は `docs/index.md` に分離しています。

---

## 現在のシミュレーター系統

### 1. Mediator ベースのゲートシミュレーター

例：

```text
ai_doc_orchestrator_with_mediator_v1_0.py
tests/test_doc_orchestrator_with_mediator_v1_0.py
```

このシミュレーターは、次の流れに焦点を当てています。

```text
Agent → Mediator → Orchestrator
```

主な特徴：

- Agent がタスク入力を正規化する
- Mediator は助言のみを行う
- Mediator は実行権限を持たない
- Orchestrator は固定順序でゲートを評価する
- RFL は相対的または曖昧な要求に使用される
- Ethics / ACC はより高リスクなブロック条件を扱う
- `sealed=True` は Ethics / ACC でのみ出現できる
- raw text は永続化されるべきではない
- 監査ログは直接的な PII 漏えいを避けるべきである

正規のゲート順序：

```text
Meaning → Consistency → RFL → Ethics → ACC → Dispatch
```

このシミュレーターは、次の確認に有用です。

- ゲート不変条件
- HITL 遷移
- RFL による一時停止挙動
- sealed / non-sealed 挙動
- Mediator と Orchestrator の分離
- reason code の期待値
- 軽量なマルチタスク・オーケストレーション挙動

---

### 2. 実運用寄りドキュメント・オーケストレーター・シミュレーター

例バージョン：

```text
v1.2.6-hash-chain-checkpoint
```

このシミュレーターは、より強い永続化と整合性制御を備えた
ドキュメントタスク・オーケストレーションに焦点を当てています。

主な特徴：

- Task Contract Gate
- 粗いトークン見積もり
- Word / Excel / PPT タスクのシミュレーション
- タスクごとのチェックポイント / 再開
- HMAC-SHA256 監査ログ・ハッシュチェーン
- HMAC 保護されたチェックポイントファイル
- SHA-256 + HMAC による成果物整合性記録
- PII 安全な監査 / チェックポイント / 成果物書き込み
- 改ざん検知
- CLI ベースのシミュレーション実行入口
- mediation / negotiation 機能なし
- 外部提出の自動実行なし

重要な実装上の注意：

このシミュレーターは、ドキュメントタスク結果を表すテキストベースの
成果物を出力します。別途ドキュメント生成ライブラリを接続しない限り、
完全に整形された Microsoft Office 文書を生成するものではありません。

ハッシュ化と HMAC は改ざん検知を提供します。
物理的な書き込み防止を提供するものではありません。
実運用では、HMAC キーは環境変数または保護されたキーファイルから
供給されるべきであり、リポジトリにコミットしてはいけません。

---

## バッチ実行と再開

このリポジトリには、バッチ形式のオーケストレーション例も含まれています。

ここでいうバッチ実行とは、複数のドキュメント関連タスクを
1つのオーケストレーション実行として評価しつつ、ゲート判断、
監査記録、中断点を保持することを意味します。

---

### Mediator ベースのバッチフロー

Mediator ベースのシミュレーターは、1回の実行で複数タスクを受け取れます。

利用例：

- 複数のスプレッドシート / スライドタスクをまとめて評価する
- タスク単位のゲート結果を比較する
- 複数タスクにまたがる HITL 挙動を確認する
- オーケストレーション前に Mediator の助言を検証する
- 各タスクが固定ゲート順序を通過することを確認する

この系統は、次の点に焦点を当てる場合に有用です。

- マルチタスクのゲート挙動
- Mediator 分離
- RFL / HITL 遷移
- reason code の安定性
- 軽量なオーケストレーションテスト

タスク列の例：

```text
T1: xlsx task
T2: pptx task
T3: ambiguous task requiring RFL / HITL
```

期待される挙動：

- 各タスクは Agent によって正規化される
- 各タスクは Mediator の助言を受ける
- 各タスクは Orchestrator によって評価される
- 一時停止したタスクは、Ethics / ACC が sealed stop を実行しない限り non-sealed のまま残る
- dispatch は最終判断が RUN の場合にのみ実行される

---

### ドキュメントタスク・バッチフロー

実運用寄りドキュメント・オーケストレーター・シミュレーターは、
固定されたドキュメントタスク列を使用します。

```text
Word → Excel → PPT
```

この系統は、次の点に焦点を当てる場合に有用です。

- バッチタスク実行
- タスクごとのチェックポイント
- 中断と再開
- 成果物整合性記録
- HMAC 保護されたチェックポイント
- HMAC-SHA256 監査ログ・ハッシュチェーン
- 改ざん検知

タスクが中断された場合、シミュレーターは次の情報を記録します。

- 失敗したタスク ID
- 失敗したレイヤー
- reason code
- チェックポイントパス
- 再開要件
- 該当する場合の HITL 確認要件

後続の実行では、必要に応じて HITL 確認後にチェックポイントから再開できます。

---

## バッチスクリプト

バッチスクリプトは、ローカルシミュレーション実行のための
便利なラッパーとして使用できます。

推奨されるスクリプト例：

```text
scripts/run_doc_orchestrator_demo.bat
scripts/run_doc_orchestrator_resume.bat
scripts/run_doc_orchestrator_tamper_check.bat
```

これらのスクリプトは、ローカル開発者向けユーティリティとしてのみ扱うべきです。

次のことをしてはいけません。

- 本番用 HMAC キーを埋め込む
- 成果物を自動的にアップロードまたは提出する
- HITL 確認を迂回する
- ファイルを自動削除する
- 実在する個人データや機密データを処理する
- ライセンスまたは安全性の意味を変更する
- テストやゲート不変条件を弱める

ローカルデモでは、シミュレーターが明示的に対応している場合に限り、
デモキー・モードを使用できます。本番相当の実行では、HMAC キーは
環境変数または保護されたキーファイルを使用してください。

---

## バッチスクリプトの役割例

### `run_doc_orchestrator_demo.bat`

目的：

- ローカルデモを実行する
- 安全なサンプル入力を使用する
- 監査ログとシミュレーション成果物をローカル出力ディレクトリに書き込む
- 外部提出を避ける

典型的な用途：

```text
デモキー・モードによるローカルデモ実行。
```

---

### `run_doc_orchestrator_resume.bat`

目的：

- チェックポイントから再開する
- 明示的な再開確認を要求する
- 継続前に完了済み成果物を検証する
- チェックポイント整合性を保持する

典型的な用途：

```text
HITL 確認後に、中断された Word / Excel / PPT シミュレーションを再開する。
```

---

### `run_doc_orchestrator_tamper_check.bat`

目的：

- 監査ログ / チェックポイント / 成果物の整合性挙動を検証する
- 改ざん検知を実演する
- 整合性検証に失敗した場合は HITL のために一時停止する

典型的な用途：

```text
ローカルでの改ざん検知シミュレーション。
```

---

## 推奨される読み進め方

ゲート挙動と KAGE 風の不変条件を確認する場合：

```text
ai_doc_orchestrator_with_mediator_v1_0.py
tests/test_doc_orchestrator_with_mediator_v1_0.py
```

チェックポイント、再開、成果物整合性、HMAC チェーン挙動を確認する場合：

```text
Production-oriented Doc Orchestrator Simulator
v1.2.6-hash-chain-checkpoint
```

挙動を検証する際は、常に実装と対応するテストを一緒に読むことを推奨します。

これは特に、次の確認で重要です。

- ゲート不変条件
- reason code の期待値
- HITL 遷移
- sealed / non-sealed 挙動
- チェックポイント / 再開挙動
- 改ざん検知挙動
- 再現性チェック
- ベンチマーク期待値
- バッチ実行挙動

---

## テストと挙動

このリポジトリでは、テストがシミュレーターや
オーケストレーションロジックの期待挙動を定義していることが多いです。

挙動を確認する際は、実装と対応するテストを一緒に読む方がよいです。

テストでは、次のような点を検証する場合があります。

- 固定ゲート順序
- fail-closed 挙動
- HITL エスカレーション
- RFL の非封印挙動
- Ethics / ACC の封印制約
- チェックポイント復旧
- 監査ログ整合性
- 成果物ハッシュ検証
- reason code の安定性
- 再現性の期待値
- バッチタスク挙動
- CLI 挙動

新しいバージョン番号が、常に主要な推奨エントリーポイントを意味するとは限りません。
一部のファイルは、履歴比較、再現性、またはバージョン付き実験のために保存されています。

---

## ゲートと判断モデル

このリポジトリでは、オーケストレーション挙動を追跡可能にするために、
明示的なゲート判断を使用します。

代表的な判断は次のとおりです。

```text
RUN
PAUSE_FOR_HITL
STOPPED
```

一般的な解釈：

- `RUN`: シミュレーターは次のゲートまたは dispatch ステップへ進んでよい
- `PAUSE_FOR_HITL`: シミュレーターは一時停止し、人間のレビューを待つべき
- `STOPPED`: シミュレーターはブロック条件に到達している

KAGE 風のシミュレーター系統では、RFL は封印するのではなく、
HITL のために一時停止すべきです。
封印挙動は、シミュレーター契約に応じて、Ethics や ACC などの
高リスク層に限定されるべきです。

---

## 監査と整合性モデル

監査と整合性の挙動は、シミュレーター系統によって異なります。

Mediator ベースのシミュレーターは、軽量な監査イベントと
安全なコンテキストログに焦点を当てています。

実運用寄りドキュメントシミュレーターは、より強い整合性制御を追加しています。

- 監査ログ・ハッシュチェーン
- 行単位 HMAC
- チェックポイント HMAC
- 成果物 SHA-256
- 成果物 HMAC
- 再開時の完了済み成果物検証
- 改ざん検知

これらの仕組みは、変更を検知可能にすることを目的としています。
ローカルの行為者がディスク上のファイルを変更すること自体を
防止するものではありません。

---

## チェックポイントと再開モデル

チェックポイントベースのシミュレーターは、
中断された実行を再開できるように設計されています。

チェックポイントには、次の情報が記録される場合があります。

- run ID
- 現在のタスク ID
- 失敗したタスク ID
- 失敗したレイヤー
- reason code
- タスク状態
- 成果物パス
- 成果物ハッシュ
- 再開が許可されているか
- 再開前に HITL が必要か

再開時には、シミュレーターが継続する前に完了済み成果物を
検証するべきです。検証に失敗した場合、黙って継続するのではなく、
HITL のために一時停止するべきです。

---

## 成果物モデル

シミュレーター内の成果物出力は、研究用成果物として扱うべきです。

シミュレーター系統によって、出力には次のようなものが含まれる場合があります。

- 成果物プレビュー
- テキストベースのドキュメントタスク出力
- 監査 JSONL ファイル
- チェックポイント JSON ファイル
- 整合性メタデータ
- サマリー記録

実際のドキュメント生成コードが追加され、テストされていない限り、
このリポジトリは、これらのシミュレーション出力を完全な本番用 Office 文書として
説明するべきではありません。

---

## 外部副作用

外部副作用には、次のような操作が含まれます。

- メール送信
- ファイルアップロード
- 成果物提出
- 変更の push
- ファイル削除
- 外部 API 呼び出し
- ライセンス意味論の変更

これらの操作は、シミュレーター契約に応じて、
ブロック、禁止、または HITL ゲート付きにすべきです。

スクリプトやシミュレーターが、外部提出を黙って実行するべきではありません。

---

## アーカイブと履歴ファイル

一部のファイルは、次の目的で保存されています。

- 履歴比較
- 再現性
- バージョン付き実験
- 回帰テスト
- 設計比較

`archive/` 以下のファイルは、現在のテストやドキュメントから明示的に
参照されていない限り、通常は履歴資料または参考資料として扱うべきです。

---

## 言語

- 英語 README: `README.md`
- 日本語 README: `README.ja.md`

---

## ライセンス

このリポジトリは、分割ライセンスモデルを使用しています。

- ソフトウェアコード: **Apache License 2.0**
- ドキュメント、図、研究資料: **CC BY-NC-SA 4.0**

詳細は [LICENSE_POLICY.md](./LICENSE_POLICY.md) を参照してください。

---

## 免責事項

このリポジトリは、研究および教育目的でのみ提供されています。

これは本番用安全システムではなく、コンプライアンス認証でもなく、
安全な自律挙動を保証するものでもありません。ユーザーは、実世界で使用する前に、
コードをレビュー、テスト、適応する責任があります。

独立したレビューと適切な保護措置なしに、このリポジトリを使用して、
実在する個人データ、機密性のある業務データ、または高リスクな意思決定ワークフローを
処理しないでください。
