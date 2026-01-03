# 📘 Maestro Orchestrator — Orchestration Framework (fail-closed + HITL)

日本語版: [README.ja.md](README.ja.md)

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

## Quickstart

~~~powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
python -m pytest -q
~~~


### Recommended entrypoint

Doc orchestrator (KAGE3-style, implementation reference for post-HITL semantics):

~~~powershell
python ai_doc_orchestrator_kage3_v1_2_4.py
~~~

## Environment Setup

### Prerequisites
- Python **3.10+** (recommended: 3.11)
- Latest `pip`

### 1) Create and activate a virtual environment (Windows / PowerShell)
~~~powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
~~~

If PowerShell blocks activation:
~~~powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
~~~

### 2) Install dependencies

Runtime only:
~~~powershell
pip install -r requirements.txt
~~~

Development / tests:
~~~powershell
pip install -r requirements-dev.txt
~~~

### 3) Run tests
~~~powershell
python -m pytest -q
~~~

### Optional: lock dependencies (pip-tools)
~~~powershell
pip install pip-tools
pip-compile requirements.txt -o requirements.lock.txt
pip-compile requirements-dev.txt -o requirements-dev.lock.txt
pip-sync requirements-dev.lock.txt
~~~

### Notes
- **matplotlib**: use `plt.savefig(...)` in headless environments (CI, servers). Avoid `plt.show()` unless a GUI backend is available.

Linux / macOS (equivalent):
~~~bash
python3 -m venv .venv
source .venv/bin/activate
~~~

