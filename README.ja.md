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

Maestro Orchestrator は、マルチエージェント・ガバナンス、fail-closed 制御、HITL エスカレーション、チェックポイントベースの再開、改ざん検知可能なシミュレーション・ワークフローを研究するための、研究指向のオーケストレーション・フレームワークです。

このリポジトリには複数のシミュレーター系列が含まれています。KAGE風のゲート挙動や Mediator 分離を扱うファイルもあれば、ドキュメントタスクのバッチ実行、チェックポイント、監査整合性、成果物検証を扱うファイルもあります。

## 初めて読む人向けガイド

このリポジトリを初めて読む場合は、次の順に読むことを推奨します。

1. まず **Safety and scope** を読む。
2. **Tasukeru Analysis** を読み、レビュー補助の役割を理解する。
3. **Advisory-only policy** を読み、この workflow が何をしないのかを理解する。
4. **HITL decision support** を読み、人間レビューが必要になる条件を理解する。
5. 安全境界を理解してから **Current simulator lines** を読む。

このリポジトリは、研究・教育目的のテストベンチです。  
出力は研究用 artifacts であり、本番承認や安全保証ではありません。

挙動が不明な場合は、変更を適用する前に、関連する実装とテストを合わせて確認してください。

## Safety and scope

このリポジトリは研究用プロトタイプです。

次の用途を意図していません。

- 本番環境での自律的意思決定
- 人間の監督なしの現実世界制御
- 法律、医療、金融、規制に関する助言
- 実在する個人データや機密運用データの処理
- 完全または普遍的な安全性カバレッジの実証
- 外部送信、アップロード、送付、デプロイの自動実行
- 外部副作用に対する HITL レビューの迂回

例は次のものとして読むべきです。

- 研究用シミュレーション
- 教育用リファレンス
- ガバナンス / 安全性テストベンチ
- fail-closed と HITL 設計の例
- 監査ログとチェックポイント整合性の実験
- ローカルシミュレーション用のバッチ・オーケストレーション例

外部 submit / upload / push / send は、HITL-gated のままにする必要があります。

## Responsible use and prohibited use

Tasukeru Analysis とシミュレーター例は、ユーザー自身が所有するリポジトリ、または明示的な許可を得たリポジトリの防御的レビューを目的としています。

このリポジトリやツールを次の目的で使用しないでください。

- 無許可の脆弱性探索
- 攻撃的偵察
- 第三者システムやコードの exploit
- 認証情報、トークン、秘密情報の収集
- 許可のないリポジトリやシステムのスキャン
- 実在ターゲットに対する exploit 手順の生成または検証
- アクセス制御、レート制限、セキュリティ境界の迂回
- 責任ある開示を経ない機密 findings の公開

findings は、安全性、信頼性、追跡性、ガバナンスの改善に使うべきです。第三者または OSS コードをレビューする場合は、対象プロジェクトの security policy と responsible disclosure process に従ってください。

## Tasukeru Analysis

Tasukeru Analysis は、防御的なリポジトリレビューのための advisory workflow です。

Tasukeru Analysis は、複雑化する multi-agent / agentic workflows を検査・統制する補助も目的としています。こうした workflow は成長するほど、挙動の検査、説明、監査が難しくなります。

主に次のようなレビュー支援の問いを扱います。

- findings が適切なレビュー水準に分類されているか
- process logs と生成 outputs が整合しているか
- 不確実またはリスクのあるケースが HITL に戻されているか
- public PR comments が過度に詳細な情報を含まないか
- workflow が自動 fix / commit / push / merge を行わず advisory-only のままか

workflow は詳細な exploit 手順を公開せず、自律的な enforcement system としても動作しません。詳細 findings は human review 用に workflow artifacts/logs に残ります。

実行する静的・リポジトリ固有チェックの例は次のとおりです。

- Ruff
- Bandit
- pip-audit
- Tasukeru logic review
- documentation review
- HITL decision support classification

この workflow は、すべての advisory finding を自動的に blocking failure と扱うのではなく、maintainability、安全レビュー、developer usability を改善するように設計されています。

Tasukeru Analysis は warnings を隠すことを目的としていません。active repair candidates、review-only findings、historical-version warnings、likely noise を分離し、maintainers が優先すべき項目に集中できるようにします。

Tasukeru Analysis には result consistency audit layer も含まれます。

前段の checks は review process、logs、gates、classifications が不審または不整合でないかを確認します。result consistency auditor はさらに、生成 outputs が記録された process state と一致しているかを確認します。

これは summaries、HITL review data、announcement data、ARL verification data、gate adoption data、self-definition verification data などの process records と generated artifacts を比較します。

この layer は、count、verification status、gate adoption result、announcement claim などが underlying records と一致しない場合を検出する助けになります。

この layer は report-only です。artifacts を書き換えたり、classifications を変更したり、fixes を適用したり、pull requests / commits / pushes / merges を自動作成したりしません。

## Tasukeru adversarial stress test

Tasukeru adversarial stress test は、ローカル・合成・防御的な stress test です。

外部システムへの攻撃、exploit 実行、第三者ターゲットの scan、pull request 作成、push commit、fix 適用、merge の自動実行は行いません。

この stress test は、malformed、contradictory、bypass-like な synthetic inputs を local evaluator に入力し、Tasukeru-style safety invariants が維持されることを確認します。

典型的な synthetic cases は次のとおりです。

- malformed JSON / JSONL
- missing required audit keys
- RFL sealed-state contradictions
- non-safety-layer sealed rows
- HITL bypass-like text
- auto-merge / auto-fix injection-like text
- duplicate JSON keys
- suspicious path-like strings
- oversized audit lines

期待される挙動は fail-closed または review-oriented です。

- automation remains disabled
- risky synthetic cases に対して unsafe `RUN` を返さない
- RFL sealed contradictions は sealing せず escalation する
- non-safety sealed rows は review へ escalation する
- HITL bypass-like inputs は human review を迂回しない

この test は defensive robustness と regression coverage の改善を目的としています。攻撃用セキュリティツールではありません。

## Tasukeru boundary self-check tests

Tasukeru boundary self-check tests は、Tasukeru 自身の workflow boundaries が整合していることを確認します。

generated artifacts、PR Draft artifact listings、upload artifact paths、ARL artifact-integrity records、result-consistency expectations がずれていないかを確認します。

維持されている test entry point は次です。

- `tests/test_tasukeru_boundary_self_check_v0_2.py`

legacy/private compatibility shim は次です。

- `tests/_tasukeru_boundary_self_check_v0_1.py`

これらの tests は static/read-only です。外部 actions の実行、branches / pull requests / commits / pushes の作成、fixes 適用、comments 投稿、merge の自動実行は行いません。

## Advisory-only policy

Tasukeru Analysis は advisory-only review helper です。

次のことは行いません。

- branches の自動作成
- pull requests の自動作成
- changes の自動 commit
- changes の自動 push
- fixes の自動適用
- pull requests の自動 merge

PR comment を生成できるのは `HITL_REQUIRED` findings のみです。

`FIX_RECOMMENDED`、`REVIEW_RECOMMENDED`、`NOISE_CANDIDATE`、`INFO_ONLY` などの findings は、GitHub Step Summary と workflow artifacts に集約され、人間が確認します。

Tasukeru Analysis は human review load を下げるためのものであり、人間の意思決定を置き換えるものではありません。

## Human readability policy

Tasukeru Analysis は、人間が安全に読めて、レビューでき、保守できるコードを優先します。

AI や automated tools が処理しやすいという理由だけで、良い fix と扱うべきではありません。変更が human readability、reviewability、maintainability を下げる可能性がある場合は、human review に戻すべきです。

## Security review output policy

Tasukeru Analysis は defensive review と safe remediation guidance に限定されます。

Public PR comments には次を含めないでください。

- exploit payloads
- attack commands
- offensive reproduction steps
- step-by-step exploitation instructions
- third-party target exploitation details

Security-related findings は、次に焦点を当てるべきです。

- affected file and line
- review が必要な防御的理由
- expected safety impact
- safe remediation direction
- human review が必要かどうか

## HITL decision support

Tasukeru Analysis は findings を review levels に分類し、maintainers が actionable issues と expected noise を分離できるようにします。

現在の review levels は次のとおりです。

- `HITL_REQUIRED`: merge または次の action の前に human review が必要
- `FIX_RECOMMENDED`: concrete fix が適切である可能性が高い
- `REVIEW_RECOMMENDED`: 判断前に context review が必要
- `NOISE_CANDIDATE`: tests、demos、research simulations では許容される可能性が高い
- `INFO_ONLY`: historical-version warnings などの informational finding

この classification はデフォルトでは advisory です。maintainers が fix、document、suppress、accept を判断する助けになります。

## Active review queue

main review queue は compact に保つことを意図しています。

直ちに注意が必要な findings は次として現れます。

- `HITL_REQUIRED`
- `FIX_RECOMMENDED`
- `REVIEW_RECOMMENDED`

これらの count が zero の場合、Tasukeru が現在 human repair / review を優先推奨する active advisory items はない、という意味です。

これは repository に warnings がないという意味ではありません。残りの warnings が likely noise または historical/informational records に分類されているという意味です。

## Historical-version warnings

Historical-version warnings は完全には除外されません。

Tasukeru Analysis は、superseded または historical simulator files 由来の findings を、audit visibility に有用だが active repair target ではないものとして `INFO_ONLY` に残します。

これにより active review queue は現在 human attention を必要とする findings に集中しつつ、次の目的で保持された古い versioned files への可視性も維持します。

- reproducibility
- regression comparison
- historical reference
- versioned experiments
- design comparison

historical warnings は、その file が再び active entry point になった場合に再確認してください。

## Typical classification examples

例:

### B603 subprocess execution

通常は `HITL_REQUIRED`。

subprocess execution は external side effects を生む可能性があるため review が必要です。

### B404 subprocess import

通常は `REVIEW_RECOMMENDED`。

subprocess の import 自体は external side effect ではありません。

### B101 assert usage in tests

通常は `NOISE_CANDIDATE`。

pytest tests では `assert` が一般的に使われます。

### B101 assert usage in active runtime code

通常は `FIX_RECOMMENDED`。

runtime assert statements は Python optimization flags で除去される可能性があります。

### B101 assert usage in superseded historical simulator files

通常は `INFO_ONLY`。

完全除外ではなく historical-version warning として visible に残します。file が active entry point に戻らない限り immediate fix は不要です。

### B108 temporary path usage in tests

`tmp_path` のような isolated pytest fixtures を使う場合、通常は `NOISE_CANDIDATE`。

`/tmp/name` のような hard-coded shared path を使う場合は review すべきです。

### B311 pseudo-random generator usage in active simulations

通常は `REVIEW_RECOMMENDED`。

deterministic simulation randomness は、secrets、tokens、authentication、authorization、cryptography に使われない場合は許容されることがあります。

許容する場合、randomness が simulation-only であることを code/documentation に明示してください。

### B311 pseudo-random generator usage in superseded historical simulator files

通常は `INFO_ONLY`。

historical-version warning として visible に残します。security-sensitive behavior または active runtime behavior に再利用されない限り immediate fix は不要です。

### Dependency vulnerabilities from pip-audit

通常は `FIX_RECOMMENDED`。

## Evidence, explanation, and prediction

Tasukeru Analysis は findings に structured decision-support metadata を付与することがあります。

含まれる可能性があるものは次のとおりです。

- `evidence`: source tool、rule ID、file、line、snippet、artifact reference
- `explanation`: finding が重要な理由、remediation direction が提案される理由
- `fix_prediction`: suggested change の expected safety / maintainability effect
- `fix_verification`: candidate verification 用の placeholder または result data

`fix_prediction` は保証ではありません。review aid です。

`fix_verification` が有効な場合も advisory-only のままでなければなりません。candidate checks は temporary / isolated files を使い、人間が明示的に手動適用を選ぶまでは repository files を変更してはいけません。

## Output artifacts

Tasukeru Analysis は次の review artifacts を生成することがあります。

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

`tasukeru_advisory_summary.md` は簡潔な overview を提供します。

`tasukeru_hitl_review.md` は次を含む human-readable review guidance を提供します。

- file path
- line number
- finding code
- issue summary
- review level
- suggested action

`tasukeru_hitl_review.json` は同じ decision-support data を machine-readable format で提供します。

`tasukeru_notification_state.json` は、該当する場合、fingerprint-based incident aggregation を含む critical-notification state を記録します。

`tasukeru_pr_comment.md` は、`HITL_REQUIRED` incident が PR notification の条件を満たす場合にのみ使われる PR comment body を記録します。

`tasukeru_dradm_draft.md` と `tasukeru_dradm_draft.json` は human review 用の draft-only documentation proposals を含みます。

これらの DRADM drafts は、proposed minimal diffs、full draft text、hashes、evidence、review checklists を含むことがあります。repository files を変更せず、自動適用してはいけません。

`tasukeru_confidence_report.md` と `tasukeru_confidence_report.json` は、Tasukeru の classifications、explanations、draft recommendations に対する confidence をまとめます。

Confidence scores は review-aid metadata にすぎません。finding を safe to ignore と示すものではなく、automatic fixes、automatic PR creation、automatic commits、automatic pushes、automatic merges を可能にしてはいけません。

`tasukeru_result_consistency_report.md`、`tasukeru_result_consistency_report.json`、`tasukeru_result_consistency_verify.json` は、process logs と generated result artifacts が一致しているかを記録します。

これらは decision counts、ARL verification、gate adoption status、self-definition verification、announcement data が outputs 間で一貫していることを確認するために使われます。

`tasukeru_dimension_dependency_report.md`、`tasukeru_dimension_dependency_report.json`、`tasukeru_dimension_dependency_verify.json` は、findings、affected structures、impact classification、review levels、generated outputs が dependency-consistent かを記録します。

これらは advisory-only dependency audit artifacts です。findings の変更、classifications の変更、fixes の適用、commits の作成、push、pull requests の merge は行いません。

## Advisory behavior

Tasukeru Analysis はデフォルトで advisory です。

maintainers が次を判断する助けになります。

- どの findings が likely noise か
- どの findings を review すべきか
- どの files に注意が必要か
- finding がなぜ relevant か
- suggested fix は何か
- merge 前に HITL が必要か
- active repair candidate か historical-version warning か

workflow は human review を置き換えません。より安全な repository maintenance のための triage と documentation aid です。

## Repository purpose

このリポジトリの主目的は、agentic workflows を explicit gates、reproducible logs、interruption points、human review によって制御する方法を探索することです。

この project は次を重視します。

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

production-oriented Doc Orchestrator simulator の詳細な architecture diagrams は次にまとめています。

- Doc Orchestrator Architecture Diagrams

この文書には次が含まれます。

- Doc Orchestrator overview
- task processing flow
- audit HMAC chain
- checkpoint resume flow
- data structure map

direct diagram links も利用できます。

- Doc Orchestrator overview
- Task processing flow
- Audit HMAC chain
- Checkpoint resume flow
- Data structure map

その他の diagrams、reference files、bundles、documentation assets については次を参照してください。

- Documentation Index

README は overview を簡潔に保ち、詳細 diagrams は `docs/architecture.md`、より広い documentation index は `docs/index.md` に分離しています。

## Current simulator lines

### 1. Mediator-based gate simulator

例:

- `ai_doc_orchestrator_with_mediator_v1_0.py`
- `tests/test_doc_orchestrator_with_mediator_v1_0.py`

Plain-language guide:

- Japanese: [`docs/mediator_orchestrator_plain_guide.ja.md`](docs/mediator_orchestrator_plain_guide.ja.md)

この simulator は次の flow に焦点を当てます。

```text
Agent → Mediator → Orchestrator
```

Core characteristics:

- Agent は task input を normalize する。
- Mediator は advice のみを出す。
- Mediator は execution authority を持たない。
- Orchestrator は固定順で gates を評価する。
- RFL は relative または ambiguous requests に使う。
- Ethics / ACC は higher-risk blocking conditions を扱う。
- `sealed=True` は Ethics / ACC のみに現れる。
- raw text は persist すべきではない。
- audit logs は direct PII leakage を避けるべきである。

Canonical gate order:

```text
Meaning → Consistency → RFL → Ethics → ACC → Dispatch
```

この simulator は次の確認に有用です。

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

この simulator は、より強い persistence と integrity controls を持つ document-task orchestration に焦点を当てます。

Core characteristics:

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
- mediation / negotiation feature はない
- automatic external submission はない

Important implementation note:

この simulator は document-task results を表す text-backed artifact outputs を書き込みます。別途 document-generation libraries が接続・テストされていない限り、完全に formatted された Microsoft Office documents を生成すると主張しません。

Hashing と HMAC は tamper evidence を提供します。physical write prevention は提供しません。real deployment では、HMAC keys は environment variable または protected key file から供給し、repository に commit してはいけません。

### 3. Emergency Contract × KAGE integration simulator

例:

- `emergency_contract_kage_orchestrator_v1_0.py`
- `tests/test_emergency_contract_kage_orchestrator_v1_0.py`

この simulator は、Emergency Contract Case B scenario と KAGE-style orchestration flow を組み合わせます。

これは small integration proof-of-concept であり、本番の contracting、legal、signal-control system ではありません。

Core characteristics:

- Emergency Contract Case B scenario
- KAGE-style gate order
- RFL non-sealing behavior
- Evidence validation and fabricated-evidence detection
- HITL auth checkpoint
- ADMIN finalize checkpoint
- Ethics / ACC sealed-stop invariants
- simulated contract draft artifact generation
- HMAC verification 付き tamper-evident ARL rows
- real-world signal control はない
- legal effect はない
- external submission、upload、send、API call、deployment はない

Canonical integration flow:

```text
Meaning → Consistency → RFL → Evidence → HITL Auth → Draft
→ Ethics → Draft Lint → ACC → ADMIN Finalize → Dispatch
```

この simulator は次の確認に有用です。

- emergency-contract scenario handling
- relative-priority evaluation through RFL
- fabricated evidence pause behavior
- real-world control blocking through ACC
- USER and ADMIN HITL stop paths
- simulated artifact dispatch only
- ARL/HMAC verification
- KAGE invariants across normal and abnormal paths

### 4. Infrastructure Lifeline Mediation Simulation

例:

- `infrastructure_lifeline_mediation_randomized_sim_v0_2.py`
- `tests/test_infrastructure_lifeline_mediation_randomized_sim_v0_2.py`

この simulator は、3つの infrastructure agents による constrained lifeline-resource mediation scenario をモデル化します。

- electricity
- water
- gas

これは、mediator が制約下の failure resources に対して proposal-only allocation plans を作る挙動を研究するための、local、seed-reproducible な research simulation です。

Core characteristics:

- normal resource requirements を持つ3つの infrastructure agents
- failure-mode total resource constraint
- minimum guarantees
- priority weights
- life-risk scores
- shortage-rate-aware allocation
- simulated HITL decisions
- JSON and stdout output
- external API access はない
- real infrastructure control はない
- automatic recovery はない
- automatic shutdown or disconnection はない

Mediator は allocation proposals のみを作成します。real infrastructure を制御せず、real-world recovery actions も実行しません。

simulated human operator は次を返すことがあります。

- `APPROVE`
- `REJECT`
- `REDEFINE`
- `REQUEST_ALTERNATIVES`

この simulator は次の確認に有用です。

- constrained resource allocation behavior
- proposal-only mediation
- seeded reproducibility
- HITL branch behavior
- safety-boundary flags
- JSON output behavior
- allocation totals staying within the available resource limit

### 5. Agent Incident Mediation Simulation

例:

- `agent_incident_mediation_sim_v0_2.py`
- `tests/test_agent_incident_mediation_sim_v0_2.py`

この simulator は、1つの simulated agent が orchestration 中に out-of-contract action を行う local-only incident mediation flow をモデル化します。

PseudoTasukeru が log/output mismatch を検出し、Tasukeru-style review artifacts を作成し、finding を Mediator に escalate します。Mediator は simulated HITL を行った後、in-memory の `STOP_AGENT` または `AUTHORIZE_SEAL` result を適用します。

Core characteristics:

- simulated abnormal agent behavior
- PseudoTasukeru log/output mismatch detection
- escalation packet from PseudoTasukeru to Mediator
- simulated HITL decision branching
- `STOP_AGENT` / `AUTHORIZE_SEAL` in-memory control only
- ARL verification
- 3D-DAC dependency consistency verification
- RCV result consistency verification
- Tasukeru-style local artifacts
- external API access はない
- real process control はない
- automatic fix、commit、push、merge はない

この simulator は次の確認に有用です。

- abnormal agent が log/output inconsistency から検出されるか
- PseudoTasukeru が agents を直接停止せず escalate するか
- Mediator が stopping / sealing の前に HITL を行うか
- simulated user instruction が記録されるか
- normal agents が誤って stopped / sealed されないか
- ARL、3D-DAC、RCV、generated artifacts が整合するか

### 6. Code Anomaly Maestro Handoff Simulation

例:

- `agent_code_anomaly_maestro_handoff_sim_v0_3_1.py`
- `tests/test_agent_code_anomaly_maestro_handoff_sim_v0_3_1.py`

Extended multi-abnormal / PEL experiment:

- `agent_code_anomaly_maestro_handoff_multi_abnormal_pel_sim_v0_4_1.py`
- `tests/test_agent_code_anomaly_maestro_handoff_multi_abnormal_pel_sim_v0_4_1.py`

v0.4.1 multi-abnormal / PEL variant は、code-anomaly handoff line に additional abnormal-case handling と report-oriented probabilistic escalation checks を追加します。local-only、advisory/research-oriented のままであり、external API access、real process control、automatic fixes、commits、pushes、merges は行いません。

この simulator は local-only code-contract anomaly handoff flow をモデル化します。

PseudoTasukeru は metadata-only code-contract anomaly を検出し、finding を Maestro に escalate します。Maestro は自分で判断せず、simulated HITL を要求し、その後 simulated user instruction を実行します。

simulated user は次を選択できます。

- `AUTHORIZE_SEAL`
- `QUARANTINE_HANDOFF_RESUME`

Core characteristics:

- metadata-only code-contract anomaly detection
- PseudoTasukeru escalation to Maestro
- Maestro does not self-decide
- simulated HITL instruction recording
- `AUTHORIZE_SEAL` branch
- `QUARANTINE_HANDOFF_RESUME` branch
- safe checkpoint handoff/resume through a standby agent
- ARL verification
- 3D-DAC dependency consistency verification
- RCV result consistency verification
- code execution はない
- malware behavior はない
- external API access はない
- real process control はない
- automatic fix、commit、push、merge はない

この simulator は次の確認に有用です。

- PseudoTasukeru が code-contract anomalies を検出するか
- findings が Maestro に escalate されるか
- Maestro が self-decision せず HITL を要求するか
- simulated user instruction が記録されるか
- seal と quarantine-handoff-resume branches が両方動くか
- standby handoff が safe checkpoint から resume するか
- ARL、3D-DAC、RCV、generated artifacts が整合するか

### 7. Agent Incident PEL USER_MAESTRO Handoff Simulation

例:

- `agent_incident_mediation_pel_user_maestro_sim_v0_3_1.py`

この simulator は local-only Agent Incident Mediation Simulation に、report-only probabilistic escalation と USER_MAESTRO handoff を追加します。

基本 incident setting は v0.2 と同じです。1つの simulated agent が out-of-contract action を行い、PseudoTasukeru が log/output mismatch を検出し、run は local-only に保たれます。

v0.2 からの変更点:

| Area | v0.2 | v0.3.1 |
|---|---|---|
| Escalation target | Mediator | USER_MAESTRO |
| Risk estimate | Not included | PEL report-only estimate |
| Human choices | `STOP_AGENT` / `AUTHORIZE_SEAL` | `AUTHORIZE_SEAL` / `QUARANTINE_HANDOFF_RESUME` |
| Resume behavior | No standby resume branch | Standby agent can resume from a checkpoint |
| Added artifacts | Basic Tasukeru-style artifacts | PEL report, checkpoint, instruction record, handoff/resume result |
| Control authority | Human decision before stop or seal | Human decision before seal or handoff/resume |

Core characteristics:

- simulated abnormal agent behavior
- PseudoTasukeru log/output mismatch detection
- PEL probabilistic escalation report
- calculation trace recording
- escalation to `USER_MAESTRO`
- simulated HITL instruction recording
- `AUTHORIZE_SEAL` branch
- `QUARANTINE_HANDOFF_RESUME` branch
- standby agent promotion
- checkpoint-based task resume
- ARL verification
- 3D-DAC dependency consistency verification
- PEL verification
- RCV result consistency verification
- external API access はない
- real process control はない
- malware behavior はない
- automatic fix、commit、push、merge はない

この simulator は次の確認に有用です。

- PEL と USER_MAESTRO handoff を追加しても v0.2 incident flow が維持されるか
- high-risk simulated incidents が `USER_MAESTRO` に routed されるか
- simulated user instruction が記録されるか
- seal と quarantine-handoff-resume branches が両方動くか
- standby handoff が checkpoint から resume するか
- normal agents が誤って sealed、quarantined、resumed されないか
- ARL、3D-DAC、PEL、RCV、checkpoint、generated artifacts が整合するか

### 8. Office Task Mediation + Tasukeru + Maestro Simulation

例:

- `agent_office_task_mediation_tasukeru_maestro_sim_v0_5_0.py`
- `tests/test_agent_office_task_mediation_tasukeru_maestro_sim_v0_5_0.py`

Additional draft variant:

- `agent_office_task_mediation_tasukeru_maestro_sim_v0_5_1_trust_to_risk.py`

Flow diagrams:

- [v0.5.1 trust-to-risk baseline flow](docs/office_task_mediation_v0_5_1_baseline_flow.png)
- [v0.5.2 diagnostic inference draft flow](docs/office_task_mediation_v0_5_2_diagnostic_inference_flow.png)

この simulator は、Word / Excel / PowerPoint-style の synthetic artifacts を使う local-only Office task mediation flow をモデル化します。

生成された document、spreadsheet、presentation outputs が original user task instruction と整合しているかを確認します。Tasukeru は logs を読み、anomalies を検出し、risk materials のみを出力します。Mediator は masked metadata packets のみを受け取り、original task と generated outputs の差分を reconcile します。Maestro は自分で判断せず、user-selected agents にだけ tasks を配布し、score が threshold を超えた場合だけ HITL を trigger し、explicit user-selected actions のみを実行します。

Simulation flow:

```text
User selects target agents
↓
Maestro dispatches the task only to user-selected agents
↓
Word / Excel / PowerPoint-style synthetic artifacts are generated
↓
Tasukeru reads internal logs and creates masked metadata packets
↓
Mediator receives only masked metadata and compares outputs against the original task snapshot
↓
Mediator calculates the collision score
↓
PEL estimates future failure probability as advisory metadata
↓
If score == 0.8, the result remains WARNING / DRAFT_REVIEW
↓
If score > 0.8, Maestro triggers PAUSE_FOR_HITL
↓
User selects the next action
↓
Maestro executes only the explicit user-selected action
```

この simulator は real Office files を生成しません。synthetic Word / Excel / PowerPoint-style records を用いて、consistency、masking、threshold behavior、HITL routing、draft-only revision propagation を検証します。

Core characteristics:

- fixed Word / Excel / PowerPoint synthetic task set
- user-selected agent dispatch before Maestro handoff
- original task snapshot and hash-fixed task baseline
- Tasukeru log analysis and risk-material output only
- masked metadata handoff from Tasukeru to Mediator
- no raw log handoff to Mediator
- Mediator request verification
- Office output consistency checks
- profit / formula / chart / conclusion mismatch detection
- PII and confidential-signal masking
- threshold policy: `score == 0.8` is warning / draft review only
- threshold policy: `score > 0.8` triggers `PAUSE_FOR_HITL`
- `USER_TARGETED_REVISION_PROMPT` for user-scoped draft revisions
- related agents create draft revision proposals only
- Maestro has no autonomous decision authority
- ARL verification
- RCV result consistency verification
- no real Office document generation
- no external API access
- no real process control
- no automatic fix, commit, push, or merge

Recent v0.5.0 verification hardening:

- required Word / Excel / PowerPoint artifacts are now checked explicitly
- missing required artifacts produce `REQUIRED_ARTIFACTS_MISSING` in RCV
- profit comparison uses None-safe value selection so `0` remains a valid value
- sealed ARL rows keep `final_decider="SYSTEM"` while user authorization remains recorded in the reason/message
- PEL records its safety buffer explicitly as advisory metadata
- internal raw agent logs are not saved by default and require `--save-raw-logs-simulation-only`

v0.5.1 draft extension:

- trust-score based automation entry diagnosis
- `trust_score == 0.9` is not auto eligible
- `trust_score > 0.9` may become an automation candidate after User approval
- automation-risk based 4D continuation diagnosis after automation starts
- `automation_risk_score < 0.1` continues automation
- `automation_risk_score >= 0.1` triggers fail-closed `AUTO_SUSPENDED_BY_4D`
- Maestro relay-only temporary automation suspension
- User HITL required for automation resume
- Tasukeru remains diagnostic-only and does not directly command agents
- no automatic fix, commit, push, or merge

The v0.5.1 draft variant keeps the v0.5.0 Office task mediation line intact and adds a trust-to-risk automation policy. Before automation starts, Tasukeru uses `trust_score` as an entry diagnostic. After automation starts, Tasukeru switches to `automation_risk_score` and performs 4D continuation diagnosis. Maestro remains relay-only, and User remains the final decider.

What the tests verify:

- the safe scenario does not trigger HITL
- `score == 0.8` remains warning / draft review only
- `score > 0.8` triggers HITL
- Maestro does not decide by itself
- Maestro dispatches only to user-selected agents
- Tasukeru does not hand raw logs to Mediator
- Mediator uses masked metadata only
- PII is masked before mediation
- confidential signals are masked before mediation
- `USER_TARGETED_REVISION_PROMPT` creates draft proposals only
- draft revisions are not auto-applied
- auto fix / commit / push / merge remain disabled
- ARL verification succeeds
- RCV result consistency verification succeeds
- missing required Office artifacts are detected by RCV
- `chart_profit=0` and `profit=0` are treated as valid values
- sealed ARL rows preserve system-level final-decider semantics
- raw simulation logs are opt-in and are not written by default
- PEL safety-buffer metadata is explicit and reviewable

This simulator is useful for checking:

- whether Word / Excel / PowerPoint-style outputs remain consistent
- whether Excel formula results and PowerPoint chart values conflict
- whether Word text, spreadsheet values, and presentation summaries diverge
- whether the original user instruction remains the comparison baseline
- whether PII and confidential signals are masked before mediation
- whether Mediator uses only masked metadata
- whether `score == 0.8` does not trigger HITL
- whether `score > 0.8` triggers HITL
- whether user-targeted revision prompts generate draft proposals only
- whether Maestro avoids self-decision and only executes explicit user-selected actions

The v0.5.1 draft variant is useful for checking:

- whether automation entry remains gated by `trust_score > 0.9`
- whether `trust_score == 0.9` is treated as non-eligible
- whether User approval is required before `AUTO_ACTIVE`
- whether automation continuation switches from trust scoring to risk scoring
- whether `automation_risk_score == 0.1` fails closed into suspension
- whether `automation_risk_score >= 0.1` triggers `AUTO_SUSPENDED_BY_4D`
- whether Maestro temporarily suspends automation as a relay without autonomous decision authority
- whether User HITL is required to resume suspended automation
- whether auto fix / commit / push / merge remain disabled

## Batch execution and resume

このリポジトリには batch-style orchestration examples も含まれています。

Batch execution は、gate decisions、audit records、interruption points を保持しながら、複数の document-related tasks を単一 orchestration run として評価できることを意味します。

### Mediator-based batch flow

mediator-based simulator は1回の run で複数 tasks を受け取ることができます。

Example use cases:

- 複数の spreadsheet / slide tasks をまとめて評価する
- task-level gate outcomes を比較する
- 複数 tasks にまたがる HITL behavior を確認する
- orchestration 前の mediator advice を確認する
- 各 task が fixed gate order を通ることを確認する

この line は次に焦点を当てる場合に有用です。

- multi-task gate behavior
- mediator separation
- RFL / HITL transitions
- reason-code stability
- lightweight orchestration tests

Example task sequence:

- T1: xlsx task
- T2: pptx task
- T3: ambiguous task requiring RFL / HITL

Expected behavior:

- each task is normalized by the Agent
- each task receives Mediator advice
- each task is evaluated by the Orchestrator
- paused tasks remain non-sealed unless Ethics / ACC performs a sealed stop
- dispatch only occurs when the final decision is `RUN`

### Document-task batch flow

production-oriented document orchestrator simulator は fixed document-task sequence を使います。

```text
Word → Excel → PPT
```

この line は次に焦点を当てる場合に有用です。

- batch task execution
- per-task checkpointing
- interruption and resume
- artifact integrity records
- HMAC-protected checkpoints
- HMAC-SHA256 audit log hash chains
- tamper-evidence detection

task が interrupted された場合、simulator は次を記録します。

- failed task ID
- failed layer
- reason code
- checkpoint path
- resume requirement
- applicable な場合の HITL confirmation requirement

後続 run は、必要に応じて HITL confirmation の後、checkpoint から resume できます。

## Batch scripts

Batch scripts は local simulation runs の convenience wrappers として使えます。

推奨 script examples:

- `scripts/run_doc_orchestrator_demo.bat`
- `scripts/run_doc_orchestrator_resume.bat`
- `scripts/run_doc_orchestrator_tamper_check.bat`

これらの scripts は local developer utilities として扱ってください。

次のことをしてはいけません。

- production HMAC keys を埋め込む
- artifacts を自動 upload / submit する
- HITL confirmation を迂回する
- files を自動削除する
- 実在する個人データや機密データを処理する
- license または safety semantics を変更する
- tests または gate invariants を弱める

local demonstrations では、simulator が明示的に support している場合のみ demo key mode を使えます。production-like runs では、HMAC keys は environment variable または protected key file を使ってください。

### Example batch-script roles

#### `run_doc_orchestrator_demo.bat`

Purpose:

- local demonstration を実行する
- safe sample input を使う
- audit logs と simulated artifacts を local output directories に書く
- external submission を避ける

Typical use:

- demo key mode を使った local demo run

#### `run_doc_orchestrator_resume.bat`

Purpose:

- checkpoint から resume する
- explicit resume confirmation を要求する
- continuing 前に completed artifacts を verify する
- checkpoint integrity を保持する

Typical use:

- HITL confirmation 後に interrupted Word / Excel / PPT simulation を resume する

#### `run_doc_orchestrator_tamper_check.bat`

Purpose:

- audit-log / checkpoint / artifact integrity behavior を verify する
- tamper-evidence detection を実演する
- integrity verification が失敗した場合 HITL に pause する

Typical use:

- local tamper-evidence simulation

## Recommended reading order

Gate behavior と KAGE-like invariants を見る場合:

- `ai_doc_orchestrator_with_mediator_v1_0.py`
- `tests/test_doc_orchestrator_with_mediator_v1_0.py`

Checkpoint、resume、artifact integrity、HMAC-chain behavior を見る場合:

- Production-oriented Doc Orchestrator Simulator
- `v1.2.6-hash-chain-checkpoint`

Emergency Contract × KAGE integration behavior を見る場合:

- `emergency_contract_kage_orchestrator_v1_0.py`
- `tests/test_emergency_contract_kage_orchestrator_v1_0.py`

この path は、concrete emergency-contract scenario が KAGE-style gates、HITL checkpoints、ARL/HMAC verification、simulated artifact dispatch によって、real-world control や legal effect なしにどう評価されるかを学ぶのに有用です。

Agent Incident Mediation behavior を見る場合:

- `agent_incident_mediation_sim_v0_2.py`
- `tests/test_agent_incident_mediation_sim_v0_2.py`

この path は、PseudoTasukeru が simulated log/output mismatch を検出し、Mediator へ escalate し、HITL を trigger し、user instruction を記録し、ARL / 3D-DAC / RCV consistency を external side effects なしに verify する流れを学ぶのに有用です。

Code Anomaly Maestro Handoff behavior を見る場合:

- `agent_code_anomaly_maestro_handoff_sim_v0_3_1.py`
- `tests/test_agent_code_anomaly_maestro_handoff_sim_v0_3_1.py`

この path は、PseudoTasukeru が metadata-only code-contract anomaly を検出し、Maestro へ escalate し、HITL を trigger し、simulated user instruction を記録し、`AUTHORIZE_SEAL` または `QUARANTINE_HANDOFF_RESUME` を external side effects なしに実行する流れを学ぶのに有用です。

Agent Incident PEL USER_MAESTRO handoff behavior を見る場合:

- `agent_incident_mediation_pel_user_maestro_sim_v0_3_1.py`

この path は、v0.2 incident flow から PEL risk estimation、USER_MAESTRO HITL、checkpoint-based standby resume がどう変わったかを学ぶのに有用です。

Office task mediation behavior を見る場合:

- `agent_office_task_mediation_tasukeru_maestro_sim_v0_5_0.py`
- `tests/test_agent_office_task_mediation_tasukeru_maestro_sim_v0_5_0.py`

trust-to-risk automation draft extension を見る場合:

- `agent_office_task_mediation_tasukeru_maestro_sim_v0_5_1_trust_to_risk.py`

この path は、Word / Excel / PowerPoint-style consistency checks、masked metadata handoff、threshold-based HITL behavior、automatic application を伴わない user-targeted draft revision を学ぶのに有用です。v0.5.1 draft extension はさらに trust-score based automation entry、automation-risk based 4D suspension、fail-closed `AUTO_SUSPENDED_BY_4D`、User HITL required for automation resume を示します。

Behavior verification では、必ず implementation と corresponding tests を合わせて読んでください。

特に重要なものは次です。

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

このリポジトリでは、tests が simulators と orchestration logic の expected behavior を定義することが多いです。

behavior を確認するときは、implementation と corresponding tests を合わせて読む方が通常は有効です。

Tests が verify する可能性のあるもの:

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

新しい version number が常に primary recommended entry point を意味するわけではありません。historical comparison、reproducibility、versioned experiments のために残されている files もあります。

## Gate and decision model

この repository は、orchestration behavior を traceable にするため explicit gate decisions を使います。

Common decisions include:

- `RUN`
- `PAUSE_FOR_HITL`
- `STOPPED`

General interpretation:

- `RUN`: simulator は次の gate または dispatch step へ進んでよい
- `PAUSE_FOR_HITL`: simulator は pause し human review を待つべき
- `STOPPED`: simulator は blocking condition に到達した

KAGE-like simulator lines では、RFL は seal ではなく HITL へ pause すべきです。Sealing behavior は simulator contract に応じて Ethics や ACC のような higher-risk layers に限定されるべきです。

## Audit and integrity model

Audit と integrity behavior は simulator line によって異なります。

mediator-based simulator は lightweight audit events と safe context logging に焦点を当てます。

production-oriented document simulator はより強い integrity controls を追加します。

- audit log hash chain
- row-level HMAC
- checkpoint HMAC
- artifact SHA-256
- artifact HMAC
- completed-artifact verification on resume
- tamper-evidence detection

これらの mechanisms は changes を detectable にすることを目的とします。local actor が disk 上の files を変更することを防止するものではありません。

## Checkpoint and resume model

Checkpoint-based simulators は interrupted execution を support するように設計されています。

Checkpoint には次が記録されることがあります。

- run ID
- current task ID
- failed task ID
- failed layer
- reason code
- task status
- artifact path
- artifact hash
- resume が allowed か
- resume 前に HITL が required か

resuming 時には、simulator が continue する前に completed artifacts を verify すべきです。verification が失敗した場合、silent に continue せず HITL に pause すべきです。

## Artifact model

Simulator の artifact outputs は research artifacts として扱ってください。

simulator line によって、outputs には次が含まれます。

- artifact previews
- text-backed document-task outputs
- audit JSONL files
- checkpoint JSON files
- integrity metadata
- summary records

実際の document-generation code が追加・テストされていない限り、repository はこれらの simulated outputs を complete production Office documents と説明すべきではありません。

## External side effects

External side effects には次のような actions が含まれます。

- sending email
- uploading files
- submitting artifacts
- pushing changes
- deleting files
- calling external APIs
- changing license semantics

これらの actions は simulator contract に応じて blocked、prohibited、または HITL-gated のままにすべきです。

script や simulator は external submission を silent に実行してはいけません。

## Archive and historical files

一部の files は次の目的で保存されています。

- historical comparison
- reproducibility
- versioned experiments
- regression testing
- design comparison

`archive/` 配下の files は、current tests や documentation で明示的に参照されていない限り、通常は historical または reference material として扱うべきです。

## Language

- English README: `README.md`
- Japanese README: `README.ja.md`

## License

この repository は split-license model を使います。

- Software code: Apache License 2.0
- Documentation, diagrams, and research materials: CC BY-NC-SA 4.0

詳細は `LICENSE_POLICY.md` を参照してください。

## Project policies

- [Security Policy](SECURITY.md)
- [License Policy](LICENSE_POLICY.md)
- [Contributing Guide](CONTRIBUTING.md)

## Disclaimer

この repository は研究・教育目的のみで提供されます。
