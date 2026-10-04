# Tasukeru mediation experiment: selected runtime records

This is an abbreviated record from a report-only experiment executed in GitHub Actions. AI answers and approval grants were deterministic test fixtures. No real AI API calls or automatic repository repairs were performed.

The referenced experiment completed **20/20 self-tests** and **10/10 fixed scenario checks** with the expected outcomes. This excerpt contains **5 of those 10 scenarios**. PASS means that a scenario reached its expected state, including expected waiting and stopping states.

## Selected outcomes

| Scenario | Recorded state | Meaning |
|---|---|---|
| `corrected` | `HUMAN_REVIEW` | A mock proposal that disagreed with the reference evidence was resubmitted, revalidated and left for human review. |
| `no_approval` | `WAITING_FOR_APPROVAL` | No mock regeneration request was issued without a mock approval grant. |
| `still_inconsistent` | `STOPPED_BUDGET` | The resubmitted mock proposal still disagreed with the evidence, so processing stopped. |
| `result_unknown` | `STOPPED_RESULT_UNKNOWN` | An unknown mock request result led to a stop. |
| `human_stop` | `STOPPED_BY_HUMAN` | The simulated human stop prevented the returned result from advancing to review or adoption. Remote cancellation was not confirmed. |

## Scope and unresolved points

- The `corrected` case corrected a deliberately prepared **mock proposal**. It did not repair the original analysis logs.
- The original **two observed differences remain unresolved**. Cause, actor and snapshot relationship remain `UNKNOWN`.
- Final adoption remains `NOT_DETERMINED`. No automatic application or final adoption was performed.
- Actual AI correction ability, real user authentication, source authenticity and whole-system safety are not established by these results.
- The excerpt omits source bindings, approval metadata and other fields. It cannot independently verify provenance or authorization, and it is not a complete audit record.

## Selected record fields

The JSON below retains recorded values for the selected state and event fields. `expected_behavior_matched` is the source case's `passed` field, renamed for clarity. Event sequence numbers are copied without renumbering. Fields omitted from events are not available in this excerpt. The selection intentionally excludes source code, commands, rejected proposal payloads, approval tokens and bindings, internal identifiers and hashes, concrete input values, and links to full records.

```json
{
  "record_type": "SELECTED_RUNTIME_EXCERPT",
  "selection_note": "Five of ten fixed demo scenarios; fields are intentionally omitted.",
  "ai_output": "DETERMINISTIC_FIXTURES_ONLY",
  "approval_channel": "SIMULATED_FIXTURE_DRIVER",
  "real_AI_calls": 0,
  "human_authentication_tested": false,
  "automatic_apply": false,
  "final_adoption": false,
  "original_records_repaired": false,
  "observed_difference_count": 2,
  "cause": "UNKNOWN",
  "actor": "UNKNOWN",
  "same_snapshot_relationship": "UNKNOWN",
  "approval": "NOT_DETERMINED",
  "selected_cases": [
    {
      "scenario": "corrected",
      "actual_state": "HUMAN_REVIEW",
      "expected_behavior_matched": true,
      "ai_output": "DETERMINISTIC_FIXTURE",
      "approval_channel": "SIMULATED_FIXTURE_DRIVER",
      "automatic_apply": false,
      "human_final_adoption": false,
      "original_records_repaired": false,
      "events": [
        {
          "seq": 1,
          "kind": "INITIAL_VERIFICATION",
          "status": "BLOCKED_INVALID"
        },
        {
          "seq": 2,
          "kind": "FEEDBACK_READY"
        },
        {
          "seq": 3,
          "kind": "MOCK_REGENERATION_REQUESTED"
        },
        {
          "seq": 4,
          "kind": "MOCK_REQUEST_RESULT",
          "state": "COMPLETED"
        },
        {
          "seq": 5,
          "kind": "RESUBMISSION_VERIFICATION",
          "status": "REVIEWABLE_DRAFT"
        }
      ]
    },
    {
      "scenario": "no_approval",
      "actual_state": "WAITING_FOR_APPROVAL",
      "expected_behavior_matched": true,
      "ai_output": "DETERMINISTIC_FIXTURE",
      "approval_channel": "SIMULATED_FIXTURE_DRIVER",
      "automatic_apply": false,
      "human_final_adoption": false,
      "original_records_repaired": false,
      "events": [
        {
          "seq": 1,
          "kind": "INITIAL_VERIFICATION",
          "status": "BLOCKED_INVALID"
        },
        {
          "seq": 2,
          "kind": "FEEDBACK_READY"
        },
        {
          "seq": 3,
          "kind": "NO_APPROVAL_NO_REQUEST"
        }
      ]
    },
    {
      "scenario": "still_inconsistent",
      "actual_state": "STOPPED_BUDGET",
      "expected_behavior_matched": true,
      "ai_output": "DETERMINISTIC_FIXTURE",
      "approval_channel": "SIMULATED_FIXTURE_DRIVER",
      "automatic_apply": false,
      "human_final_adoption": false,
      "original_records_repaired": false,
      "events": [
        {
          "seq": 1,
          "kind": "INITIAL_VERIFICATION",
          "status": "BLOCKED_INVALID"
        },
        {
          "seq": 2,
          "kind": "FEEDBACK_READY"
        },
        {
          "seq": 3,
          "kind": "MOCK_REGENERATION_REQUESTED"
        },
        {
          "seq": 4,
          "kind": "MOCK_REQUEST_RESULT",
          "state": "COMPLETED"
        },
        {
          "seq": 5,
          "kind": "RESUBMISSION_VERIFICATION",
          "status": "BLOCKED_INVALID"
        }
      ]
    },
    {
      "scenario": "result_unknown",
      "actual_state": "STOPPED_RESULT_UNKNOWN",
      "expected_behavior_matched": true,
      "ai_output": "DETERMINISTIC_FIXTURE",
      "approval_channel": "SIMULATED_FIXTURE_DRIVER",
      "automatic_apply": false,
      "human_final_adoption": false,
      "original_records_repaired": false,
      "events": [
        {
          "seq": 1,
          "kind": "INITIAL_VERIFICATION",
          "status": "BLOCKED_INVALID"
        },
        {
          "seq": 2,
          "kind": "FEEDBACK_READY"
        },
        {
          "seq": 3,
          "kind": "MOCK_REGENERATION_REQUESTED"
        },
        {
          "seq": 4,
          "kind": "MOCK_REQUEST_RESULT",
          "state": "RESULT_UNKNOWN"
        }
      ]
    },
    {
      "scenario": "human_stop",
      "actual_state": "STOPPED_BY_HUMAN",
      "expected_behavior_matched": true,
      "ai_output": "DETERMINISTIC_FIXTURE",
      "approval_channel": "SIMULATED_FIXTURE_DRIVER",
      "automatic_apply": false,
      "human_final_adoption": false,
      "original_records_repaired": false,
      "events": [
        {
          "seq": 1,
          "kind": "INITIAL_VERIFICATION",
          "status": "BLOCKED_INVALID"
        },
        {
          "seq": 2,
          "kind": "FEEDBACK_READY"
        },
        {
          "seq": 3,
          "kind": "MOCK_REGENERATION_REQUESTED"
        },
        {
          "seq": 4,
          "kind": "LOCAL_HUMAN_STOP",
          "request_state": "REQUESTED",
          "remote_cancellation": "NOT_ATTEMPTED_OR_CONFIRMED"
        },
        {
          "seq": 5,
          "kind": "MOCK_REQUEST_RESULT",
          "state": "COMPLETED"
        },
        {
          "seq": 6,
          "kind": "RESULT_WITHHELD_AFTER_STOP",
          "result_state": "COMPLETED",
          "remote_cancellation": "NOT_CONFIRMED"
        }
      ]
    }
  ]
}
```

## 日本語の説明

これはGitHub Actionsで実行した、レポートのみを出力する模擬実験の抜粋です。AIの回答と承認には、事前に用意したテスト用データを使っています。実AIのAPI呼び出し、自動適用、自動修復、最終採用は行っていません。

実行では、自己テスト20件と固定シナリオ10件が予定した結果になりました。このファイルは、そのうち5ケースの一部の記録です。PASSは、承認待ちや停止を含め、各ケースが予定した状態になったことを意味します。

| ケース | 記録された状態 | 確認した動作 |
|---|---|---|
| `corrected` | `HUMAN_REVIEW` | 根拠と一致しなかった模擬提案を再提出し、再検証後に人間確認の段階へ移した。 |
| `no_approval` | `WAITING_FOR_APPROVAL` | 模擬承認がなければ、模擬再生成の要求を出さず承認待ちになった。 |
| `still_inconsistent` | `STOPPED_BUDGET` | 再提出後も根拠と一致しなかったため、処理を止めた。 |
| `result_unknown` | `STOPPED_RESULT_UNKNOWN` | 模擬要求の結果が不明だったため、処理を止めた。 |
| `human_stop` | `STOPPED_BY_HUMAN` | 人間停止を模擬し、その後に届いた結果を確認・採用の段階へ進めなかった。外部処理の取消完了は確認していない。 |

`corrected`で修正したのは、意図的に不一致を入れた模擬提案です。元の解析ログにある差異2件は未解決で、原因・主体・スナップショットの関係はUNKNOWNのままです。最終採用はNOT_DETERMINEDです。

実AIの修正能力、実際の承認者認証、出典の真正性、システム全体の安全性は、この結果では確認できていません。

上のJSONは、元記録から選んだ状態・イベントの項目を保持しています。`expected_behavior_matched`は元の`passed`を表示用に改名したものです。イベントの順番は元記録のままです。コード、コマンド、却下された提案の入力例、承認トークンと結び付け情報、内部識別子・ハッシュ、具体的な入力値、全文へのリンクは省略しています。

このファイルは説明用の抜粋です。省略された情報があるため、このファイル単体で実行元や承認の正当性を検証することはできません。完全な監査記録や、実AIの性能・安全性の証明として扱わないでください。
