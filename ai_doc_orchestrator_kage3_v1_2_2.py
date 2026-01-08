review_result = {
    "meta": {
        "review_target": "ai_doc_orchestrator_kage3_v1_2_3.py",
        "version": "1.2.3",
        "mode": {"STRICT": False},
        "rulebook": {
            "banned_phrases_yml": "unavailable_in_this_session",
            "dev_terms_yml": "unavailable_in_this_session",
            "red_flags_yml": "unavailable_in_this_session",
            "note": "辞書ファイルを参照できないため、ルールIDは本レビュー内の暫定IDで付与",
        },
    },
    "gate_progress": {
        "stage_1_purpose_scope": {
            "status": "PASS_WITH_ISSUES",
            "findings": [
                {
                    "id": "S1-001",
                    "type": "scope_gap",
                    "statement": "目的(PIIを永続化しない)は明確だが、対象PIIの定義がメールアドレスのみ。",
                    "evidence": ["EMAIL_RE のみで検出/マスク", "_ethics_detect_pii は EMAIL_RE のみ"],
                    "impact": "メール以外(電話番号、住所、氏名、社員ID等)が監査ログ/成果物に残る可能性。",
                },
                {
                    "id": "S1-002",
                    "type": "non_goal_missing",
                    "statement": "並行実行/複数プロセス同時書き込みの非目標・制約が未記載。",
                    "evidence": [
                        "AuditLog.emit はファイルロックなしで追記",
                        "start_run(truncate=True) は同一パス共有時に他Runを破壊可能",
                    ],
                    "impact": "監査ログ欠損、相互上書き、法務監査の完全性毀損。",
                },
            ],
        },
        "stage_2_requirements_constraints": {
            "status": "PASS_WITH_ISSUES",
            "findings": [
                {
                    "id": "S2-001",
                    "type": "contract_incomplete",
                    "statement": "Excel契約検証が 'columns' と 'rows' の型検証のみで、列名と行キー整合が未検証。",
                    "evidence": ["_validate_contract(excel) は rows の各dictキー検証なし"],
                    "impact": "後段(実ファイル生成や集計)でKeyError/欠損列が発生しうる。",
                },
                {
                    "id": "S2-002",
                    "type": "artifact_format_mismatch",
                    "statement": "成果物拡張子が xlsx/docx/pptx を名乗るが、実体は .txt。",
                    "evidence": ['_write_artifact: f"{task_id}.{_artifact_ext(kind)}.txt"'],
                    "impact": "利用者・後続処理が誤認し、誤処理/取り込み失敗を誘発。",
                },
            ],
        },
        "stage_3_design_specifics": {
            "status": "PASS_WITH_ISSUES",
            "findings": [
                {
                    "id": "S3-001",
                    "type": "log_integrity_risk",
                    "statement": "start_run(truncate=True) が同一 audit_path を共有する複数runで破壊的。",
                    "evidence": ["truncate=True で open('w') により全消去"],
                    "impact": "他runのログ消失(監査証跡の不可逆破壊)。",
                },
                {
                    "id": "S3-002",
                    "type": "pii_detection_gap",
                    "statement": "Ethics gateは raw_text でのみ検出し、draft(構造データ)内のPIIを未検出。",
                    "evidence": ["_ethics_detect_pii(raw_text) のみ", "draft は検査対象外"],
                    "impact": "draft→safe_text化の過程を変えると、構造側PIIが成果物に混入し得る。",
                },
                {
                    "id": "S3-003",
                    "type": "meaning_gate_overproduction",
                    "statement": "promptにkind言及が無い場合、3タスクすべてRUNになり成果物が過剰生成される。",
                    "evidence": ["if not any_kind: return RUN for all kinds"],
                    "impact": "ユーザー意図とズレた成果物生成(情報最小化に反する運用になりやすい)。",
                },
            ],
        },
        "stage_4_verification_threats": {
            "status": "FAIL",
            "findings": [
                {
                    "id": "S4-001",
                    "type": "missing_tests",
                    "statement": "境界/異常/並行/回帰テスト観点がコード内にも仕様にも具体化されていない。",
                    "impact": "PII非永続の保証・ログ完全性の保証が設計主張に留まる。",
                }
            ],
        },
    },
    "overall_assessment": {
        "decision": "HITL",
        "pass_rate_estimate": {
            "value": 0.62,
            "basis": [
                "PII対策(メール)は強いが範囲が狭い",
                "ログ完全性(truncate/並行)が未封止",
                "契約検証が浅い",
                "拡張子偽装(実体txt)が運用事故を誘発",
            ],
        },
    },
    "red_flags": [
        {
            "id": "RF-LOG-TRUNC-001",
            "severity": "HIGH",
            "description": "truncate=True が他runの監査ログを破壊可能",
            "trigger": "同一audit_path共有 + truncate_audit_on_start=True",
            "sealed": True,
            "seal_plan": "run_id別ファイル化 または ファイルロック/排他 + truncate禁止(単一run専用パス強制)",
        },
        {
            "id": "RF-CONC-IO-001",
            "severity": "HIGH",
            "description": "ファイル追記に排他制御が無く、JSONL行が競合/破損し得る",
            "trigger": "複数プロセス/スレッド同時 emit",
            "sealed": False,
            "seal_plan": "fcntl/msvcrt等のOSロック、または専用ロガープロセス/キュー経由",
        },
        {
            "id": "RF-FORMAT-MISREP-001",
            "severity": "MEDIUM",
            "description": "xlsx/docx/pptxと誤認させる命名(実体txt)",
            "trigger": "生成物を外部が実ファイルとして扱う",
            "sealed": False,
            "seal_plan": "実形式で生成するか、拡張子を .txt に統一し kind をメタデータへ",
        },
    ],
    "misuse_abuse_scenarios": [
        {
            "id": "MU-001",
            "scenario": "運用者が truncate_audit_on_start=True をデフォルト化し、複数ジョブが同一audit_pathで動いてログを相互消去。",
            "impact": "監査証跡消失、インシデント時の原因追跡不能。",
            "mitigation": [
                "audit_path を run_id/日付で必ず分割",
                "truncate はテスト専用フラグに限定(本番で無効化)",
            ],
            "sealed": True,
        },
        {
            "id": "MU-002",
            "scenario": "promptにkind指定が無いユーザーへ3成果物を自動生成し、不要情報が保存される(情報最小化違反)。",
            "impact": "データ保持リスク増大、誤配布/誤参照の面積増大。",
            "mitigation": [
                "task selectionを明示入力(allowed_kinds)として必須化",
                "kind指定無しはHITLに変更し、意図確認へ",
            ],
            "sealed": False,
        },
        {
            "id": "MU-003",
            "scenario": "メール以外のPII(電話番号/住所/氏名/社員ID)を入力し、監査ログ/成果物に残る。",
            "impact": "PII永続化ポリシー違反。",
            "mitigation": [
                "PII定義を明文化し検出器を拡張(電話番号等)",
                "少なくとも '任意の@を含む文字列' 以外の基本PIIを追加",
            ],
            "sealed": False,
        },
    ],
    "contradictions_and_gaps": [
        {
            "id": "CG-001",
            "pair": ["コメント: 'PII must not persist'", "実装: メール以外は未マスク"],
            "resolution": "PII対象をメール限定と仕様で宣言するか、検出/マスク範囲を拡張する。",
        },
        {
            "id": "CG-002",
            "pair": ["kind拡張子(xlsx/docx/pptx)を示す", "実体はtxt"],
            "resolution": "ファイル実体と拡張子を一致させる。最低限 .txt を名乗る。",
        },
    ],
    "recommended_changes": [
        {
            "id": "FIX-001",
            "priority": "P0",
            "change": "audit_path を run_id で分割し、truncate を本番禁止にする(テスト専用ガード)。",
            "acceptance_criteria": [
                "同一ディレクトリで100並行runしてもログが相互消去されない",
                "truncate=True は allow_test_mode=True のときのみ有効",
            ],
        },
        {
            "id": "FIX-002",
            "priority": "P0",
            "change": "emit() の排他制御(ファイルロック)またはログ書き込みの単一化(キュー/専用スレッド)。",
            "acceptance_criteria": [
                "10プロセス同時追記でJSONLが行単位で破損しない",
                "部分行/連結行が発生しない",
            ],
        },
        {
            "id": "FIX-003",
            "priority": "P1",
            "change": "PII定義を仕様化し、最低限『メール＋電話番号(国別パターン)＋郵便番号/住所の簡易検出＋社員IDプレフィクス』等を追加。加えて draft(構造)も ethics 対象にする。",
            "acceptance_criteria": [
                "raw_text と draft の両方からPII検出できる",
                "監査ログ/成果物の両方でPIIパターンが残らない(サンプル100ケース)",
            ],
        },
        {
            "id": "FIX-004",
            "priority": "P1",
            "change": "Excel契約: columns と rows の整合(各rowがcolumnsを全て持つ/余剰キー方針)を検証。方針を決定表で固定。",
            "acceptance_criteria": [
                "欠損列/余剰列を投入したときの挙動が一意に決まる",
                "CONTRACT_EXCEL_* のreason_codeがケース別に分岐する",
            ],
        },
        {
            "id": "FIX-005",
            "priority": "P2",
            "change": "kind指定無しの意味ゲート方針を変更: (A) HITLにして意図確認、または (B) allowed_kinds を引数として必須化。",
            "acceptance_criteria": ["ユーザーが望まない成果物が生成されない(テストで確認)"],
        },
        {
            "id": "FIX-006",
            "priority": "P2",
            "change": "成果物の命名/実体を一致: txtなら拡張子を統一、実形式生成するなら本当にxlsx/docx/pptxを書く。",
            "acceptance_criteria": [
                "拡張子から期待されるアプリで正常に開ける(実形式の場合)",
                "txtの場合、誤認しない命名規約になっている",
            ],
        },
    ],
    "verification_plan": {
        "tests": [
            {
                "id": "T-PII-001",
                "type": "security",
                "case": "raw_textにメール/電話/住所/社員IDを混在させる",
                "expected": "audit JSONL と artifact の双方に生PIIが残らない",
            },
            {
                "id": "T-PII-002",
                "type": "security",
                "case": "dictキーにメール様文字列を入れる",
                "expected": "監査ログにキーもマスクされる",
            },
            {
                "id": "T-LOG-001",
                "type": "concurrency",
                "case": "10プロセス×1000行 emit",
                "expected": "JSONLが破損しない(各行が単独JSONとしてパース可能)",
            },
            {
                "id": "T-TRUNC-001",
                "type": "safety",
                "case": "2つのrunが同一audit_pathで truncate=True/False を混在",
                "expected": "本番設定では truncate が拒否され、他runログは保持される",
            },
            {
                "id": "T-CONTRACT-EX-001",
                "type": "consistency",
                "case": "rowsの欠損キー/余剰キー/型不一致",
                "expected": "定義された方針どおりにHITLまたは補正される",
            },
            {
                "id": "T-MEANING-001",
                "type": "functional",
                "case": "promptにkind指定無し/指定有り/複数kind指定",
                "expected": "生成対象が仕様どおりに決まる(過剰生成しない)",
            },
        ]
    },
    "quick_notes_on_current_changes": [
        {
            "change": "AuditLog.start_run(truncate=...)",
            "verdict": "GOOD_BUT_NEEDS_GUARD",
            "note": "テスト容易性は上がるが、本番での誤用を封止する仕組みが必要。",
        },
        {
            "change": "AuditLogがts_state(_last_ts)を保持",
            "verdict": "GOOD",
            "note": "モジュールグローバルより安全でテストしやすい。",
        },
        {
            "change": "default=str の防御的JSON化",
            "verdict": "GOOD_WITH_CAVEAT",
            "note": "落ちないが、str化でPIIが新たに出現する可能性があるため、PII検出範囲の拡張が必要。",
        },
        {
            "change": "deep redactionがdict keysも対象",
            "verdict": "GOOD",
            "note": "キー漏洩対策として有効。",
        },
        {
            "change": "emit() が ts を自動補完",
            "verdict": "GOOD",
            "note": "呼び出し側の責務を減らす。",
        },
    ],
    "next_actions": [
        "P0(FIX-001/FIX-002)を先に実装し、並行・破壊系リスクを封止。",
        "PIIの仕様(対象範囲)を文章で確定し、検出器を拡張(FIX-003)。",
        "契約検証の厳格化(FIX-004)と、kind選択の入力インタフェース確定(FIX-005)。",
        "成果物の実体と拡張子整合(FIX-006)。",
    ],
}

# 使う側がJSONにしたい場合:
# import json
# print(json.dumps(review_result, ensure_ascii=False, indent=2))
