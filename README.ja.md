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

Maestro Orchestrator は、マルチエージェント・ガバナンス、fail-closed 制御、
HITL エスカレーション、checkpoint ベースの resume、改ざん検知可能な
シミュレーション workflow を研究するためのオーケストレーション・フレームワークです。

このリポジトリには複数の simulator 系列が含まれます。KAGE 風の gate 挙動や
mediator 分離に焦点を当てるファイルもあれば、document-task の batch 実行、
checkpoint、audit integrity、artifact verification に焦点を当てるファイルもあります。

---

## Safety and scope / 安全性と適用範囲

このリポジトリは **研究用プロトタイプ** です。

以下を目的としていません。

- 本番環境での自律的意思決定
- 人間の監督なしの現実世界制御
- 法務、医療、金融、規制対応に関する助言
- 実在する個人情報または機密運用データの処理
- 完全または普遍的な安全性の証明
- 外部送信、upload、send、deployment の自動実行
- 外部副作用に対する HITL review の迂回

各 example は、以下として読むべきものです。

- 研究用シミュレーション
- 教育用リファレンス
- governance / safety test bench
- fail-closed と HITL 設計の example
- audit-log と checkpoint integrity の実験
- local simulation 用の batch orchestration example

外部 submit / upload / push / send は、HITL-gated のまま維持してください。

---

## Responsible use and prohibited use / 責任ある利用と禁止事項

Tasukeru Analysis と simulator examples は、ユーザー自身が所有するリポジトリ、
または明示的な許可を得ているリポジトリに対する防御目的の review を想定しています。

このリポジトリまたはその tools を、以下の目的で使用しないでください。

- 許可のない脆弱性探索
- 攻撃的 reconnaissance
- 第三者システムまたは第三者コードの exploitation
- credential、token、secret の収集
- 許可のない repository または system の scanning
- 実在 target に対する exploit step の生成または検証
- access control、rate limit、security boundary の迂回
- responsible disclosure なしでの sensitive finding の公開

finding は、安全性、信頼性、traceability、governance の改善に使用してください。
第三者または open-source code を review する場合は、対象 project の security policy
および responsible disclosure process に従ってください。

---

## Tasukeru Analysis / 助ける君

Tasukeru Analysis は、防御目的の repository review を支援する advisory workflow です。

以下のような static check と repository-specific check を実行します。

- Ruff
- Bandit
- pip-audit
- Tasukeru logic review
- documentation review
- HITL decision support classification

この workflow は、すべての advisory finding を自動的に blocking failure として扱うのではなく、
maintainability、safety review、developer usability を改善することを目的としています。

Tasukeru Analysis は warning を隠すことを目的としていません。active repair candidate、
review-only finding、historical-version warning、likely noise を分離し、maintainer が
優先して確認すべき項目に集中できるようにします。

### Advisory-only policy / Advisory-only 方針

Tasukeru Analysis / 助ける君は **advisory-only のレビュー補助** です。

以下は行いません。

- ブランチの自動作成
- Pull Request の自動作成
- 自動 commit
- 自動 push
- 自動修正の適用
- Pull Request の自動 merge

PR comment の対象になり得るのは、原則として `HITL_REQUIRED` finding のみです。

`FIX_RECOMMENDED`、`REVIEW_RECOMMENDED`、`NOISE_CANDIDATE`、`INFO_ONLY`
などの finding は、GitHub Step Summary と workflow artifacts に集約され、
人間が必要に応じて確認します。

Tasukeru Analysis の目的は、人間の review 負荷を下げることであり、
人間の判断を置き換えることではありません。

### Security review output policy / セキュリティレビュー出力方針

Tasukeru Analysis は、防御目的の review と安全な remediation guidance に限定されます。

公開 PR comment には、以下を含めるべきではありません。

- exploit payload
- 攻撃用 command
- 攻撃的な再現手順
- exploitation の step-by-step 手順
- 第三者 target に対する exploitation detail

security-related finding では、以下に焦点を当てます。

- 対象 file と line
- review が必要な防御上の理由
- 想定される safety impact
- 安全な remediation direction
- human review が必要かどうか

### HITL decision support / HITL 判断支援

Tasukeru Analysis は、maintainer が actionable issue と expected noise を分離できるよう、
finding を review level に分類します。

現在の review level は以下です。

- `HITL_REQUIRED`: merge または次工程の前に human review が必要
- `FIX_RECOMMENDED`: 具体的な修正が適切である可能性が高い
- `REVIEW_RECOMMENDED`: 判断前に文脈確認を推奨
- `NOISE_CANDIDATE`: tests、demo、research simulation では許容される可能性が高い
- `INFO_ONLY`: historical-version warning などの情報目的 finding

この classification は標準では advisory です。maintainer が finding を修正する、
文書化する、抑制する、または受け入れるか判断するための補助です。

### Active review queue / 優先 review queue

main review queue は compact に保つことを意図しています。

即時確認が必要な finding は、以下として表示されるべきです。

- `HITL_REQUIRED`
- `FIX_RECOMMENDED`
- `REVIEW_RECOMMENDED`

これらの count が 0 の場合、その repository には Tasukeru が現在優先的な
human repair / review を推奨する active advisory item がない、という意味です。

これは repository に warning が存在しないという意味ではありません。残りの warning が、
likely noise または historical / informational record として分類されているという意味です。

### Historical-version warnings / 履歴版 warning

historical-version warning は完全には除外されません。

Tasukeru Analysis は、superseded または historical simulator file からの finding を、
audit visibility に有用だが active repair target ではない場合、`INFO_ONLY` として可視化します。

これにより、active review queue を現在 human attention が必要な finding に集中させつつ、
以下の目的で保持されている古い versioned file への visibility を維持します。

- reproducibility
- regression comparison
- historical reference
- versioned experiments
- design comparison

historical warning は、その file が再び active entry point になる場合に再確認してください。

### Typical classification examples / 代表的な分類例

例:

- `B603` subprocess execution:
  - 通常は `HITL_REQUIRED`
  - subprocess 実行は外部副作用を生む可能性があるため review が必要

- `B404` subprocess import:
  - 通常は `REVIEW_RECOMMENDED`
  - `subprocess` の import 自体は外部副作用ではない

- `B101` assert usage in tests:
  - 通常は `NOISE_CANDIDATE`
  - pytest tests では `assert` が一般的に使用される

- `B101` assert usage in active runtime code:
  - 通常は `FIX_RECOMMENDED`
  - runtime `assert` は Python optimization flag により削除され得る

- `B101` assert usage in superseded historical simulator files:
  - 通常は `INFO_ONLY`
  - 完全除外ではなく historical-version warning として可視化
  - その file が active entry point にならない限り、即時修正は不要

- `B108` temporary path usage in tests:
  - `tmp_path` など isolated pytest fixture を使う場合、通常は `NOISE_CANDIDATE`
  - `/tmp/name` のような hard-coded shared path を使う場合は review 推奨

- `B311` pseudo-random generator usage in active simulations:
  - 通常は `REVIEW_RECOMMENDED`
  - deterministic simulation randomness は、secret、token、authentication、
    authorization、cryptography に使われない場合は許容される可能性がある
  - 受け入れる場合は、その randomness が simulation-only であることを code comment で明示するべき

- `B311` pseudo-random generator usage in superseded historical simulator files:
  - 通常は `INFO_ONLY`
  - historical-version warning として可視化
  - security-sensitive behavior または active runtime behavior に再利用しない限り、即時修正は不要

- dependency vulnerabilities from `pip-audit`:
  - 通常は `FIX_RECOMMENDED`

### Evidence, explanation, and prediction / evidence・説明・修正予測

Tasukeru Analysis は finding に structured decision-support metadata を付与できます。

含まれる可能性がある項目:

- `evidence`: source tool、rule ID、file、line、snippet、artifact reference
- `explanation`: なぜその finding が重要か、なぜその remediation direction が示されるか
- `fix_prediction`: 提案変更によって期待される safety または maintainability 上の効果
- `fix_verification`: candidate verification 用の placeholder または result data

`fix_prediction` は保証ではありません。review 補助です。

`fix_verification` を有効にする場合も、advisory-only のまま維持しなければなりません。
candidate check は一時 file または isolated file を使用し、人間が明示的に手動適用を選ばない限り、
repository file を変更してはいけません。

### Output artifacts / 出力 artifact

Tasukeru Analysis は以下の review artifact を生成する場合があります。

```text
tasukeru_advisory_summary.md
tasukeru_hitl_review.md
tasukeru_hitl_review.json
tasukeru_notification_state.json
tasukeru_pr_comment.md
tasukeru_dradm_draft.md
tasukeru_dradm_draft.json
```

`tasukeru_advisory_summary.md` は簡潔な overview を提供します。

`tasukeru_hitl_review.md` は、人間が読みやすい review guidance を提供します。
含まれる情報の例:

- file path
- line number
- finding code
- issue summary
- review level
- suggested action

`tasukeru_hitl_review.json` は、同じ decision-support data を machine-readable format で提供します。

`tasukeru_notification_state.json` は、該当する場合に fingerprint-based incident aggregation を含む
critical-notification state を記録します。

`tasukeru_pr_comment.md` は、`HITL_REQUIRED` incident が PR notification 条件を満たす場合にのみ使われる
PR comment body を記録します。

`tasukeru_dradm_draft.md` と `tasukeru_dradm_draft.json` は、human review 用に生成される
draft-only の documentation proposal を含みます。

これらの DRADM draft には、提案される最小差分、full draft text、hash、evidence、
review checklist が含まれる場合があります。ただし、repository file は変更せず、
自動適用してはいけません。

### Advisory behavior / advisory としての挙動

Tasukeru Analysis は標準で advisory です。

maintainer が以下を判断するための補助として機能します。

- どの finding が likely noise か
- どの finding を review すべきか
- どの file に注意が必要か
- なぜその finding が関連するのか
- suggested fix は何か
- merge 前に HITL が必要か
- active repair candidate か historical-version warning か

この workflow は human review を置き換えるものではありません。
より安全な repository maintenance のための triage と documentation aid です。

---

## Repository purpose / リポジトリの目的

このリポジトリの主目的は、明示的な gate、再現可能な log、interruption point、
human review によって agentic workflow をどのように制御できるかを探ることです。

この project は以下を重視します。

- fail-closed behavior
- HITL escalation
- gate-order invariants
- reason-code stability
- checkpoint / resume behavior
- tamper-evident audit records
- artifact integrity verification
- reproducible simulation outputs
- advice と execution の明確な分離

このリポジトリは、完全な AI safety coverage を提供すると主張しません。
orchestration behavior を研究・教育目的で検証するための test bench です。

---

## Architecture diagrams / アーキテクチャ図

production-oriented Doc Orchestrator simulator の詳細な architecture diagram は以下にまとめています。

- [Doc Orchestrator Architecture Diagrams](docs/architecture.md)

この document には以下が含まれます。

- Doc Orchestrator overview
- task processing flow
- audit HMAC chain
- checkpoint resume flow
- data structure map

直接 diagram link:

- [Doc Orchestrator overview](docs/doc-orchestrator-overview.png)
- [Task processing flow](docs/task-processing-flow.png)
- [Audit HMAC chain](docs/audit-hmac-chain.png)
- [Checkpoint resume flow](docs/checkpoint-resume-flow.png)
- [Data structure map](docs/data-structure-map.png)

その他の diagram、reference file、bundle、documentation asset については以下を参照してください。

- [Documentation Index](docs/index.md)

README は overview を簡潔に保ち、詳細 diagram は `docs/architecture.md` に分離し、
より広い documentation index は `docs/index.md` に分離しています。

---

## Current simulator lines / 現在の simulator 系列

### 1. Mediator-based gate simulator

例:

```text
ai_doc_orchestrator_with_mediator_v1_0.py
tests/test_doc_orchestrator_with_mediator_v1_0.py
```

この simulator は以下の flow に焦点を当てます。

```text
Agent → Mediator → Orchestrator
```

主な特徴:

- Agent が task input を正規化する
- Mediator は advice のみを行う
- Mediator は execution authority を持たない
- Orchestrator が fixed order で gates を評価する
- RFL は relative または ambiguous request に使用される
- Ethics / ACC は higher-risk blocking condition を扱う
- `sealed=True` は Ethics / ACC のみに現れるべき
- raw text は永続化すべきではない
- audit log は直接的な PII leakage を避けるべき

canonical gate order:

```text
Meaning → Consistency → RFL → Ethics → ACC → Dispatch
```

この simulator は以下の確認に有用です。

- gate invariants
- HITL transitions
- RFL pause behavior
- sealed / non-sealed behavior
- mediator-to-orchestrator separation
- reason-code expectations
- lightweight multi-task orchestration behavior

---

### 2. Production-oriented document orchestrator simulator

example version:

```text
v1.2.6-hash-chain-checkpoint
```

この simulator は、より強い persistence と integrity control を持つ
document-task orchestration に焦点を当てます。

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

この simulator は document-task result を表す text-backed artifact output を書き出します。
別途 document-generation library が接続・テストされない限り、完全に formatting された
Microsoft Office document を生成するとは主張しません。

hashing と HMAC は tamper evidence を提供します。物理的な write prevention を提供するものではありません。
実運用では、HMAC key は environment variable または protected key file から供給し、
repository に commit してはいけません。

---

### 3. Emergency Contract × KAGE integration simulator

例:

```text
emergency_contract_kage_orchestrator_v1_0.py
tests/test_emergency_contract_kage_orchestrator_v1_0.py
```

この simulator は、Emergency Contract Case B scenario と KAGE-style orchestration flow を組み合わせます。

これは小さな integration proof-of-concept であり、本番の契約、法務、signal-control system ではありません。

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

canonical integration flow:

```text
Meaning → Consistency → RFL → Evidence → HITL Auth → Draft
→ Ethics → Draft Lint → ACC → ADMIN Finalize → Dispatch
```

この simulator は以下の確認に有用です。

- emergency-contract scenario handling
- RFL による relative-priority evaluation
- fabricated evidence pause behavior
- ACC による real-world control blocking
- USER / ADMIN HITL stop paths
- simulated artifact dispatch のみ
- ARL/HMAC verification
- normal path と abnormal path における KAGE invariants

---

## Batch execution and resume / batch 実行と resume

この repository には batch-style orchestration example も含まれます。

batch execution とは、複数の document-related task を単一の orchestration run として評価しながら、
gate decision、audit record、interruption point を保持することを意味します。

---

### Mediator-based batch flow

mediator-based simulator は、1回の run で複数 task を受け取ることができます。

example use cases:

- 複数 spreadsheet / slide task を一緒に評価する
- task-level gate outcome を比較する
- 複数 task にまたがる HITL behavior を確認する
- orchestration 前に mediator advice を検証する
- 各 task が fixed gate order を通ることを確認する

この系列は以下に焦点を当てる場合に有用です。

- multi-task gate behavior
- mediator separation
- RFL / HITL transitions
- reason-code stability
- lightweight orchestration tests

example task sequence:

```text
T1: xlsx task
T2: pptx task
T3: ambiguous task requiring RFL / HITL
```

expected behavior:

- 各 task は Agent により正規化される
- 各 task は Mediator advice を受け取る
- 各 task は Orchestrator によって評価される
- paused task は Ethics / ACC が sealed stop を行わない限り non-sealed のまま
- dispatch は final decision が RUN の場合のみ行われる

---

### Document-task batch flow

production-oriented document orchestrator simulator は固定の document-task sequence を使用します。

```text
Word → Excel → PPT
```

この系列は以下に焦点を当てる場合に有用です。

- batch task execution
- per-task checkpointing
- interruption and resume
- artifact integrity records
- HMAC-protected checkpoints
- HMAC-SHA256 audit log hash chains
- tamper-evidence detection

task が interrupted された場合、simulator は以下を記録します。

- failed task ID
- failed layer
- reason code
- checkpoint path
- resume requirement
- HITL confirmation requirement when applicable

後続 run は、必要に応じて HITL confirmation 後に checkpoint から resume できます。

---

## Batch scripts / batch script

batch script は local simulation run 用の convenience wrapper として使用できます。

recommended script examples:

```text
scripts/run_doc_orchestrator_demo.bat
scripts/run_doc_orchestrator_resume.bat
scripts/run_doc_orchestrator_tamper_check.bat
```

これらの script は local developer utility としてのみ扱ってください。

以下を行うべきではありません。

- production HMAC key を埋め込む
- artifact を自動 upload / submit する
- HITL confirmation を迂回する
- file を自動削除する
- 実在する個人情報または機密データを処理する
- license または safety semantics を変更する
- test または gate invariant を弱める

local demonstration では、simulator が明示的に対応している場合のみ demo key mode を使用できます。
production-like run では、environment variable または protected key file を使って HMAC key を供給してください。

---

## Example batch-script roles / batch script の役割例

### `run_doc_orchestrator_demo.bat`

目的:

- local demonstration を実行する
- safe sample input を使用する
- audit log と simulated artifact を local output directory に書き出す
- external submission を避ける

typical use:

```text
Local demo run with demo key mode.
```

---

### `run_doc_orchestrator_resume.bat`

目的:

- checkpoint から resume する
- 明示的な resume confirmation を要求する
- 継続前に completed artifact を検証する
- checkpoint integrity を維持する

typical use:

```text
Resume interrupted Word / Excel / PPT simulation after HITL confirmation.
```

---

### `run_doc_orchestrator_tamper_check.bat`

目的:

- audit-log / checkpoint / artifact integrity behavior を検証する
- tamper-evidence detection を demonstration する
- integrity verification が失敗した場合に HITL で pause する

typical use:

```text
Local tamper-evidence simulation.
```

---

## Recommended reading order / 推奨読解順

gate behavior と KAGE-like invariants を確認する場合:

```text
ai_doc_orchestrator_with_mediator_v1_0.py
tests/test_doc_orchestrator_with_mediator_v1_0.py
```

checkpoint、resume、artifact integrity、HMAC-chain behavior を確認する場合:

```text
Production-oriented Doc Orchestrator Simulator
v1.2.6-hash-chain-checkpoint
```

Emergency Contract × KAGE integration behavior を確認する場合:

```text
emergency_contract_kage_orchestrator_v1_0.py
tests/test_emergency_contract_kage_orchestrator_v1_0.py
```

この path は、具体的な emergency-contract scenario が KAGE-style gates、HITL checkpoints、
ARL/HMAC verification、simulated artifact dispatch により、real-world control または legal effect なしで
どのように評価されるかを学ぶのに有用です。

behavior verification では、必ず implementation と corresponding tests を一緒に読んでください。

特に重要な対象:

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

## Testing and behavior / テストと挙動

この repository では、test が simulator と orchestration logic の期待挙動を定義していることが多いです。

behavior を確認する際は、implementation と corresponding tests を一緒に読む方が適切です。

tests が検証する可能性がある項目:

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

新しい version number が、必ずしも primary recommended entry point を意味するわけではありません。
一部の file は historical comparison、reproducibility、versioned experiment のために保持されています。

---

## Gate and decision model / gate と decision model

この repository は、orchestration behavior を traceable にするため、明示的な gate decision を使用します。

common decisions:

```text
RUN
PAUSE_FOR_HITL
STOPPED
```

一般的な解釈:

- `RUN`: simulator は次の gate または dispatch step に進んでよい
- `PAUSE_FOR_HITL`: simulator は pause し、human review を待つべき
- `STOPPED`: simulator が blocking condition に到達した

KAGE-like simulator 系列では、RFL は seal ではなく HITL のために pause すべきです。
sealing behavior は、simulator contract に応じて Ethics または ACC のような higher-risk layer に限定すべきです。

---

## Audit and integrity model / audit と integrity model

audit と integrity behavior は simulator 系列ごとに異なります。

mediator-based simulator は lightweight audit events と safe context logging に焦点を当てます。

production-oriented document simulator は、より強い integrity control を追加します。

- audit log hash chain
- row-level HMAC
- checkpoint HMAC
- artifact SHA-256
- artifact HMAC
- resume 時の completed-artifact verification
- tamper-evidence detection

これらの mechanism は change を detect 可能にすることを意図しています。
local actor が disk 上の file を変更することを防止するものではありません。

---

## Checkpoint and resume model / checkpoint と resume model

checkpoint-based simulator は、interrupted execution を支援するように設計されています。

checkpoint は以下を記録する場合があります。

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

resume 時には、simulator が継続する前に completed artifact を検証すべきです。
verification が失敗した場合、silent に継続せず HITL で pause すべきです。

---

## Artifact model / artifact model

artifact output は research artifact として扱ってください。

simulator 系列に応じて、output には以下が含まれる可能性があります。

- artifact previews
- text-backed document-task outputs
- audit JSONL files
- checkpoint JSON files
- integrity metadata
- summary records

actual document-generation code が追加・テストされない限り、この repository は simulated output を
complete production Office document と説明すべきではありません。

---

## External side effects / 外部副作用

external side effects には以下のような action が含まれます。

- email 送信
- file upload
- artifact submit
- push
- file deletion
- external API call
- license semantics の変更

これらの action は、simulator contract に応じて blocked、prohibited、または HITL-gated のまま維持してください。

script または simulator は、external submission を silent に実行すべきではありません。

---

## Archive and historical files / archive と historical file

一部の file は以下の目的で保持されています。

- historical comparison
- reproducibility
- versioned experiments
- regression testing
- design comparison

`archive/` 配下の file は、current tests または documentation から明示的に参照されない限り、
通常は historical または reference material として扱ってください。

---

## Language / 言語

- English README: `README.md`
- Japanese README: `README.ja.md`

---

## License / ライセンス

この repository は split-license model を使用します。

- software code: **Apache License 2.0**
- documentation、diagrams、research materials: **CC BY-NC-SA 4.0**

詳細は [LICENSE_POLICY.md](./LICENSE_POLICY.md) を参照してください。

---

## Disclaimer / 免責

この repository は研究・教育目的で提供されています。

これは production safety system ではなく、compliance certification でもなく、
safe autonomous behavior を保証するものでもありません。real-world use の前に、
ユーザー自身が code を review、test、adapt する責任があります。

独立した review と適切な safeguards なしに、この repository を実在する個人情報、
機密運用データ、または high-stakes decision workflow の処理に使用しないでください。
