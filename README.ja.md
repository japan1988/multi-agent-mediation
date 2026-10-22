# Maestro Orchestrator — Multi-Agent Orchestration Framework

[English](README.md) / 日本語

## 何をするものか

複数の模擬エージェントが協調する際の、継続・保留・停止、人間レビューへの引き継ぎ、出力とログの整合性を調べる研究・教育用リポジトリです。

- **Maestro**：エージェントの協調、判定の順序、監査記録、チェックポイントなどを扱うシミュレーション。
- **Tasukeru**：静的解析とリポジトリ固有の検査結果を整理し、人間のレビューを支援する助言型ワークフロー。

## 現在の開発状況と未検証点

Phase 1Fは、基本的なシミュレーションテストを通過しましたが、その後の詳細な検証で複数の修正点が見つかりました。

現在はV04として修正を進めています。修正後の再検証とレビューが完了するまで、最終凍結は保留しています。

公開デモや個別テストの成功は、Phase 1F全体の完成や安全性を示すものではありません。模擬実験では、実AIの判断性能、実ユーザーの本人確認・承認、GitHub Actionsの別実行をまたぐ永続的な停止・二重実行防止は検証できていません。対象と検証範囲は、各実験の資料を参照してください。

## 最初の実行方法

まずは、**入門用HITLデモ v0.1**で保留・模擬承認・再開の流れを確認できます。GitとPythonを用意してください。リポジトリのPython CI対象は3.10と3.11です。このデモには追加パッケージやAI APIキーは不要です。

```bash
git clone https://github.com/japan1988/multi-agent-mediation.git
cd multi-agent-mediation
python -B demo_hitl_flow_v0_1.py
```

環境によっては、`python`を`python3`に読み替えてください。

画面に`WAITING_HITL`、`LOCAL_HOLD`、模擬的な確認・承認後の完了状態が順に表示されます。確認内容と承認はスクリプト内に固定されており、ユーザーの入力待ちは行いません。「外部送信」タスクも状態と文字列の記録だけで、実際の送信は行いません。

実装：[デモ](demo_hitl_flow_v0_1.py) / [HITLシミュレーター](hitl_flow_sim_v0_1.py)

## 重要な制約

- 研究用の試作です。テストの`PASS`やCI成功は、実行許可・最終採用・本番環境での安全性保証を意味しません。
- 調停役の提案、安全性の検証、実行権限を分離し、最終判断を人間に残す設計を検証しています。模擬承認を実承認として扱わないでください。
- Tasukeru Analysisは、サマリーとArtifactにレビュー資料・コメント案を保存します。PRコメントの自動投稿、ソースの自動修正、ブランチ・PR・コミットの自動作成、Push・マージは行いません。
- GitHub Actions版は、GitHub APIの読み取り、依存関係の取得・監査、Artifact保存などの通信を伴います。上のローカルデモと通信範囲を区別してください。
- 所有または明示的に許可された対象を、防御・研究目的で扱ってください。実在する秘密情報・個人情報・機密データを例題に含めないでください。[セキュリティポリシー](SECURITY.ja.md)（内容に差異がある場合は[英語版](SECURITY.md)を優先）。
- ハッシュや監査記録は整合性の確認を支援しますが、発行者の本人確認、変更の防止、システム全体の安全性を保証しません。

ソフトウェアコードは[Apache License 2.0](LICENSE)、文書・図・研究資料はCC BY-NC-SA 4.0です。

## 詳細資料へのリンク

| 読みたい内容 | 資料 |
| --- | --- |
| 資料・図・参考ファイルの一覧 | [ドキュメント索引](docs/index.md) |
| 文書処理シミュレーターの構成・監査・再開 | [アーキテクチャ資料](docs/architecture.md) |
| Tasukeru Analysisの実際の設定 | [解析ワークフロー](.github/workflows/tasukeru-analysis.yml) |
| 調停役と独立した検証境界の模擬実験 | [Mediator Boundaryデモ](docs/tasukeru-mediator-boundary-demo.md) |
| Mediator・Gate・Framework・Observerの比較実験 | [MGF比較デモ](docs/tasukeru-mgf-comparison-demo.md) |
| 過去のシミュレーター一覧・詳細説明 | [従来READMEの固定スナップショット](https://github.com/japan1988/multi-agent-mediation/blob/6e2f157cdfa56a5010a9ce5bb274e2eae685538c/README.ja.md) |

過去・バージョン別の資料は参考記録です。現在のPhase 1Fの実装・検証状況とは区別してください。
