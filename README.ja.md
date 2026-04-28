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

Maestro Orchestrator は、マルチエージェント・ガバナンス、fail-closed 制御、HITL エスカレーション、チェックポイントによる再開、改ざん検知可能なシミュレーションワークフローを扱う研究向けオーケストレーション・フレームワークです。

このリポジトリには複数のシミュレーター系列が含まれます。  
一部のファイルは KAGE 的なゲート挙動やメディエーター分離に焦点を当て、別のファイルは文書タスクのバッチ実行、チェックポイント、監査整合性、成果物検証に焦点を当てています。

---

## 安全性と適用範囲

このリポジトリは **研究用プロトタイプ** です。

以下を目的としていません。

- 本番環境での自律的意思決定
- 人間の監督なしの現実世界制御
- 法務・医療・金融・規制上の助言
- 実在する個人情報や機密運用データの処理
- 完全または普遍的な安全性保証の実証
- 外部への自動送信・アップロード・提出・デプロイ
- 外部副作用に対する HITL レビューの回避

このリポジトリの例は、以下として読むべきものです。

- 研究用シミュレーション
- 教育用リファレンス
- ガバナンス / 安全性テストベンチ
- fail-closed と HITL 設計の例
- 監査ログとチェックポイント整合性の実験
- ローカルシミュレーション用のバッチ・オーケストレーション例

外部への submit / upload / push / send などの操作は、HITL によってゲートされるべきです。

---

## 責任ある利用と禁止用途

Tasukeru Analysis とシミュレーター例は、ユーザー自身が所有するリポジトリ、または明示的な許可を得たリポジトリに対する防御的レビューを目的としています。

このリポジトリまたはそのツールを、以下の目的で使用しないでください。

- 許可のない脆弱性探索
- 攻撃的偵察
- 第三者システムまたはコードの悪用
- 認証情報・トークン・秘密情報の収集
- 許可のないリポジトリまたはシステムのスキャン
- 実在する対象に対する悪用手順の生成または検証
- アクセス制御・レート制限・セキュリティ境界の回避
- 責任ある開示なしでの機密性の高い発見事項の公開

検出結果は、安全性、信頼性、追跡可能性、ガバナンスを改善するために使用してください。  
第三者またはオープンソースのコードをレビューする場合は、そのプロジェクトのセキュリティポリシーおよび責任ある開示プロセスに従ってください。

---

## Tasukeru Analysis

Tasukeru Analysis は、防御的なリポジトリレビューのための advisory workflow です。

以下のような静的チェックおよびリポジトリ固有のチェックを実行します。

- Ruff
- Bandit
- pip-audit
- Tasukeru logic review
- HITL decision support classification

この workflow は、すべての advisory finding を自動的に blocking failure として扱うのではなく、保守性、安全性レビュー、開発者の使いやすさを改善するために設計されています。

Tasukeru Analysis は警告を隠すことを目的としていません。  
代わりに、active な修正候補、レビューのみ必要な finding、旧版・履歴ファイルの警告、ノイズ候補を分離し、保守者が優先順位を判断しやすくします。

### HITL decision support

Tasukeru Analysis は、保守者が actionable issue と想定ノイズを分離できるように、finding をレビュー水準に分類します。

現在のレビュー水準は以下です。

- `HITL_REQUIRED`: マージ前の人間レビューを推奨
- `FIX_RECOMMENDED`: 具体的な修正が妥当である可能性が高い
- `REVIEW_RECOMMENDED`: 文脈を確認して判断するべき finding
- `NOISE_CANDIDATE`: テスト、デモ、研究用シミュレーションでは許容される可能性が高い finding
- `INFO_ONLY`: 旧版・履歴ファイルの警告を含む情報目的の finding

この分類はデフォルトで advisory です。  
保守者が、修正するか、文書化するか、抑制するか、許容するかを判断するための補助として使います。

### Active review queue

メインのレビューキューは、コンパクトに保つことを意図しています。

すぐに注意が必要な finding は、以下として表示されます。

- `HITL_REQUIRED`
- `FIX_RECOMMENDED`
- `REVIEW_RECOMMENDED`

これらの件数が 0 の場合、Tasukeru が現在、人間による修正またはレビューを優先すべき active advisory item はない、という意味です。

これは、リポジトリに警告が一切ないという意味ではありません。  
残っている警告が、likely noise または historical / informational record として分類されている、という意味です。

### Historical-version warnings

旧版・履歴ファイルの警告は完全除外しません。

Tasukeru Analysis は、置き換え済みまたは履歴目的のシミュレーターファイルに含まれる finding を、監査上の可視性として有用だが active な修正対象ではない場合、`INFO_ONLY` として表示し続けます。

これにより、現在人間の注意を必要とする finding に active review queue を集中させつつ、以下の目的で保持されている古いバージョンのファイルに対する可視性を維持します。

- 再現性
- 回帰比較
- 履歴参照
- バージョン付き実験
- 設計比較

旧版警告は、そのファイルが再び active entry point になった場合に再確認するべきです。

### 典型的な分類例

例：

- `B603` subprocess execution:
  - 通常は `HITL_REQUIRED`
  - subprocess 実行は外部副作用を発生させる可能性があるため、レビューが必要

- `B404` subprocess import:
  - 通常は `REVIEW_RECOMMENDED`
  - `subprocess` の import 自体は外部副作用ではない

- `B101` tests 内の assert 使用:
  - 通常は `NOISE_CANDIDATE`
  - pytest のテストでは `assert` 使用が一般的

- `B101` active runtime code 内の assert 使用:
  - 通常は `FIX_RECOMMENDED`
  - runtime の `assert` は Python の最適化フラグで除去される可能性がある

- `B101` 置き換え済み historical simulator files 内の assert 使用:
  - 通常は `INFO_ONLY`
  - 完全除外せず、historical-version warning として表示する
  - そのファイルが再び active entry point にならない限り、即時修正は不要

- `B108` tests 内の temporary path 使用:
  - `tmp_path` などの分離された pytest fixture を使っている場合、通常は `NOISE_CANDIDATE`
  - `/tmp/name` のような共有固定パスを使っている場合はレビュー対象

- `B311` active simulations 内の pseudo-random generator 使用:
  - 通常は `REVIEW_RECOMMENDED`
  - secrets、tokens、authentication、authorization、cryptography に使っていない決定論的シミュレーション乱数であれば許容される場合がある
  - 許容する場合は、その乱数が simulation-only であることをコード上で文書化するべき

- `B311` 置き換え済み historical simulator files 内の pseudo-random generator 使用:
  - 通常は `INFO_ONLY`
  - historical-version warning として表示する
  - security-sensitive behavior または active runtime behavior に再利用されない限り、即時修正は不要

- `pip-audit` による dependency vulnerabilities:
  - 通常は `FIX_RECOMMENDED`

### 出力 artifacts

Tasukeru Analysis は、以下のレビュー artifacts を生成する場合があります。

```text
tasukeru_advisory_summary.md
tasukeru_hitl_review.md
tasukeru_hitl_review.json
```

`tasukeru_advisory_summary.md` は簡潔な概要を提供します。

`tasukeru_hitl_review.md` は、人間が読めるレビューガイダンスを提供します。内容には以下が含まれます。

- ファイルパス
- 行番号
- finding code
- issue summary
- review level
- suggested action

`tasukeru_hitl_review.json` は、同じ decision-support data を機械可読形式で提供します。

### Advisory behavior

Tasukeru Analysis はデフォルトで advisory です。

保守者が以下を判断するための補助として機能します。

- どの finding がノイズ候補か
- どの finding をレビューすべきか
- どのファイルに注意が必要か
- なぜその finding が重要なのか
- 推奨される修正は何か
- マージ前に HITL が必要か
- active repair candidate なのか、historical-version warning なのか

この workflow は人間レビューを置き換えるものではありません。  
より安全なリポジトリ保守のためのトリアージおよび文書化支援です。

---

## リポジトリの目的

このリポジトリの主な目的は、エージェント型ワークフローを、明示的なゲート、再現可能なログ、中断点、人間レビューによってどのように制御できるかを探ることです。

このプロジェクトが重視するものは以下です。

- fail-closed behavior
- HITL escalation
- gate-order invariants
- reason-code stability
- checkpoint / resume behavior
- tamper-evident audit records
- artifact integrity verification
- reproducible simulation outputs
- advice と execution の明確な分離

このリポジトリは、完全な AI 安全性カバレッジを提供すると主張するものではありません。  
オーケストレーション挙動を研究・教育するためのテストベンチです。

---

## アーキテクチャ図

production-oriented Doc Orchestrator simulator の詳細なアーキテクチャ図は以下にまとめています。

- [Doc Orchestrator Architecture Diagrams](docs/architecture.md)

このドキュメントには以下が含まれます。

- Doc Orchestrator overview
- task processing flow
- audit HMAC chain
- checkpoint resume flow
- data structure map

直接リンク：

- [Doc Orchestrator overview](docs/doc-orchestrator-overview.png)
- [Task processing flow](docs/task-processing-flow.png)
- [Audit HMAC chain](docs/audit-hmac-chain.png)
- [Checkpoint resume flow](docs/checkpoint-resume-flow.png)
- [Data structure map](docs/data-structure-map.png)

その他の図、参照ファイル、バンドル、ドキュメント資産については以下を参照してください。

- [Documentation Index](docs/index.md)

README は概要を簡潔に保ち、詳細図は `docs/architecture.md` に、広いドキュメント索引は `docs/index.md` に分離しています。

---

## 現在のシミュレーター系列

### 1. Mediator-based gate simulator

例：

```text
ai_doc_orchestrator_with_mediator_v1_0.py
tests/test_doc_orchestrator_with_mediator_v1_0.py
```

このシミュレーターは以下の流れに焦点を当てます。

```text
Agent → Mediator → Orchestrator
```

主な特徴：

- Agent がタスク入力を正規化する
- Mediator は advice のみを提供する
- Mediator は実行権限を持たない
- Orchestrator が固定順序で gate を評価する
- 相対的または曖昧な要求に RFL を使用する
- Ethics / ACC が高リスクの blocking condition を扱う
- `sealed=True` は Ethics / ACC にのみ現れるべき
- raw text は永続化しない
- audit logs は直接的な PII leakage を避けるべき

標準ゲート順序：

```text
Meaning → Consistency → RFL → Ethics → ACC → Dispatch
```

このシミュレーターは以下の確認に有用です。

- gate invariants
- HITL transitions
- RFL pause behavior
- sealed / non-sealed behavior
- mediator-to-orchestrator separation
- reason-code expectations
- lightweight multi-task orchestration behavior

---

### 2. Production-oriented document orchestrator simulator

例バージョン：

```text
v1.2.6-hash-chain-checkpoint
```

このシミュレーターは、より強い永続化と整合性制御を備えた文書タスク・オーケストレーションに焦点を当てます。

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

このシミュレーターは、document-task results を表現する text-backed artifact outputs を書き出します。  
別途 document-generation libraries が接続・テストされていない限り、完全に整形された Microsoft Office 文書を生成すると主張するものではありません。

Hashing と HMAC は改ざん検知を提供します。  
物理的な書き込み防止を提供するものではありません。  
実運用では、HMAC keys は environment variable または protected key file から供給し、リポジトリにコミットしてはいけません。

---

## Batch execution and resume

このリポジトリには、batch-style orchestration examples も含まれます。

Batch execution とは、複数の document-related tasks を単一の orchestration run として評価しつつ、gate decisions、audit records、interruption points を保持することを意味します。

---

### Mediator-based batch flow

mediator-based simulator は、一回の run で複数タスクを受け付けることができます。

利用例：

- 複数の spreadsheet / slide tasks をまとめて評価する
- task-level gate outcomes を比較する
- 複数タスクにまたがる HITL behavior を確認する
- orchestration 前に mediator advice を検証する
- 各タスクが固定 gate order を通ることを確認する

この系列は、以下に焦点を当てる場合に有用です。

- multi-task gate behavior
- mediator separation
- RFL / HITL transitions
- reason-code stability
- lightweight orchestration tests

タスク列の例：

```text
T1: xlsx task
T2: pptx task
T3: ambiguous task requiring RFL / HITL
```

期待される挙動：

- 各タスクは Agent によって正規化される
- 各タスクは Mediator advice を受ける
- 各タスクは Orchestrator によって評価される
- paused tasks は Ethics / ACC が sealed stop を行わない限り non-sealed のまま
- dispatch は final decision が RUN の場合のみ実行される

---

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

タスクが中断された場合、シミュレーターは以下を記録します。

- failed task ID
- failed layer
- reason code
- checkpoint path
- resume requirement
- HITL confirmation requirement when applicable

後続の run は、必要な場合に HITL confirmation の後、checkpoint から再開できます。

---

## Batch scripts

Batch scripts は、ローカルシミュレーション run の convenience wrappers として使用できます。

推奨スクリプト例：

```text
scripts/run_doc_orchestrator_demo.bat
scripts/run_doc_orchestrator_resume.bat
scripts/run_doc_orchestrator_tamper_check.bat
```

これらのスクリプトは、ローカル開発者用ユーティリティとして扱うべきです。

以下をしてはいけません。

- production HMAC keys を埋め込む
- artifacts を自動 upload / submit する
- HITL confirmation を回避する
- ファイルを自動削除する
- 実在する個人情報や機密データを処理する
- license や safety semantics を変更する
- tests や gate invariants を弱める

ローカルデモでは、シミュレーターが明示的に対応している場合のみ demo key mode を使用できます。  
production-like runs では、HMAC keys は environment variable または protected key file を使用するべきです。

---

## Example batch-script roles

### `run_doc_orchestrator_demo.bat`

目的：

- ローカルデモを実行する
- 安全なサンプル入力を使う
- audit logs と simulated artifacts をローカル出力ディレクトリに書く
- 外部送信を避ける

典型的な用途：

```text
Local demo run with demo key mode.
```

---

### `run_doc_orchestrator_resume.bat`

目的：

- checkpoint から再開する
- 明示的な resume confirmation を要求する
- 続行前に completed artifacts を検証する
- checkpoint integrity を保持する

典型的な用途：

```text
Resume interrupted Word / Excel / PPT simulation after HITL confirmation.
```

---

### `run_doc_orchestrator_tamper_check.bat`

目的：

- audit-log / checkpoint / artifact integrity behavior を検証する
- tamper-evidence detection を実演する
- integrity verification に失敗した場合は HITL に pause する

典型的な用途：

```text
Local tamper-evidence simulation.
```

---

## 推奨される読み順

gate behavior と KAGE-like invariants を見る場合：

```text
ai_doc_orchestrator_with_mediator_v1_0.py
tests/test_doc_orchestrator_with_mediator_v1_0.py
```

checkpoint、resume、artifact integrity、HMAC-chain behavior を見る場合：

```text
Production-oriented Doc Orchestrator Simulator
v1.2.6-hash-chain-checkpoint
```

挙動検証では、常に実装と対応する tests を合わせて読むことを推奨します。

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

---

## Testing and behavior

このリポジトリでは、tests がシミュレーターおよび orchestration logic の期待挙動を定義している場合があります。

挙動を確認するときは、実装と対応する tests を一緒に読む方が適切です。

tests は以下を検証することがあります。

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

新しいバージョン番号が、常に primary recommended entry point を意味するとは限りません。  
一部のファイルは、historical comparison、reproducibility、versioned experiments のために保持されています。

---

## Gate and decision model

このリポジトリでは、orchestration behavior を追跡可能にするため、明示的な gate decisions を使用します。

一般的な decisions は以下です。

```text
RUN
PAUSE_FOR_HITL
STOPPED
```

一般的な解釈：

- `RUN`: シミュレーターは次の gate または dispatch step に進める
- `PAUSE_FOR_HITL`: シミュレーターは pause し、人間レビューを待つべき
- `STOPPED`: シミュレーターは blocking condition に到達した

KAGE-like simulator lines では、RFL は seal ではなく HITL に pause するべきです。  
Sealing behavior は、シミュレーター契約に応じて Ethics や ACC などの高リスク層に限定されるべきです。

---

## Audit and integrity model

Audit and integrity behavior は simulator line によって異なります。

mediator-based simulator は、軽量な audit events と安全な context logging に焦点を当てます。

production-oriented document simulator は、より強い integrity controls を追加します。

- audit log hash chain
- row-level HMAC
- checkpoint HMAC
- artifact SHA-256
- artifact HMAC
- completed-artifact verification on resume
- tamper-evidence detection

これらの仕組みは、変更を検出可能にすることを目的としています。  
ローカルの行為者がディスク上のファイルを変更することを防ぐものではありません。

---

## Checkpoint and resume model

Checkpoint-based simulators は、中断された実行を再開できるように設計されています。

checkpoint は以下を記録することがあります。

- run ID
- current task ID
- failed task ID
- failed layer
- reason code
- task status
- artifact path
- artifact hash
- resume is allowed かどうか
- resume 前に HITL が必要かどうか

再開時には、シミュレーターが続行する前に completed artifacts を検証するべきです。  
検証に失敗した場合、silent に続行するのではなく HITL に pause するべきです。

---

## Artifact model

Artifact outputs は research artifacts として扱うべきです。

simulator line によって、出力には以下が含まれる場合があります。

- artifact previews
- text-backed document-task outputs
- audit JSONL files
- checkpoint JSON files
- integrity metadata
- summary records

実際の document-generation code が追加・テストされていない限り、このリポジトリは simulated outputs を完全な production Office documents として説明するべきではありません。

---

## External side effects

External side effects には以下のような操作が含まれます。

- email sending
- file upload
- artifact submission
- pushing changes
- file deletion
- calling external APIs
- changing license semantics

これらの操作は、シミュレーター契約に応じて blocked、prohibited、または HITL-gated のままであるべきです。

どの script や simulator も、外部送信を silent に実行するべきではありません。

---

## Archive and historical files

一部のファイルは以下のために保持されています。

- historical comparison
- reproducibility
- versioned experiments
- regression testing
- design comparison

`archive/` 配下のファイルは、現在の tests または documentation で明示的に参照されていない限り、一般に historical または reference material として扱うべきです。

---

## Language

- English README: `README.md`
- Japanese README: `README.ja.md`

---

## License

このリポジトリは split-license model を採用しています。

- Software code: **Apache License 2.0**
- Documentation, diagrams, and research materials: **CC BY-NC-SA 4.0**

詳細は [LICENSE_POLICY.md](./LICENSE_POLICY.md) を参照してください。

---

## Disclaimer

このリポジトリは、研究および教育目的で提供されています。

これは production safety system ではなく、compliance certification でもなく、安全な自律挙動を保証するものでもありません。  
実世界で使用する前に、ユーザー自身がレビュー、テスト、適応を行う責任があります。

独立したレビューと適切な safeguards なしに、実在する個人情報、機密運用データ、または high-stakes decision workflows を処理するためにこのリポジトリを使用しないでください。
