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
    <img src="https://img.shields.io/badge/license-Educational%20%2F%20Research-brightgreen?style=flat-square" alt="License (Policy Intent)">
  </a>
  <a href="https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml">
    <img src="https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml/badge.svg?branch=main" alt="CI Status">
  </a>
  <br/>
  <img src="https://img.shields.io/badge/python-3.9%2B-blue.svg?style=flat-square" alt="Python Version">
  <img src="https://img.shields.io/badge/lint-Ruff-000000.svg?style=flat-square" alt="Ruff">
  <a href="https://github.com/japan1988/multi-agent-mediation/commits/main">
    <img src="https://img.shields.io/github/last-commit/japan1988/multi-agent-mediation?style=flat-square" alt="Last Commit">
  </a>
</p>

## 🎯 目的（Purpose）

Maestro Orchestrator は、複数エージェント（または複数手法）を監督するための **研究向けオーケストレーション・フレームワーク**です。  
特徴は **fail-closed（安全側に倒す）** を前提にしている点です。

- **STOPPED**: エラー／危険／未定義仕様を検知したら停止
- **REROUTE**: 明示的に安全と判断できる場合のみ再ルーティング（fail-open reroute を避ける）
- **HITL**: 曖昧・高リスクは人間判断へエスカレーション（`PAUSE_FOR_HITL`）

### 位置づけ（安全優先）
Maestro Orchestrator は、タスク完遂率を最大化するよりも、**不安全／未定義の実行を防ぐこと**を優先します。  
リスクや曖昧さが検知された場合、`PAUSE_FOR_HITL` または `STOPPED` に **fail-closed** し、監査ログに「なぜそうなったか」を残します。

**トレードオフ:** 安全とトレーサビリティを優先するため、デフォルトでは *止まりやすい（over-stop）* 設計になり得ます。

---

## 🚀 Quickstart（30秒）

```bash
pip install -r requirements.txt
python ai_doc_orchestrator_kage3_v1_2_4.py
pytest -q
