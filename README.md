## Quickstart


py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
python -m pytest -q


### Recommended entrypoint

# Doc orchestrator (KAGE3-style, implementation reference for post-HITL semantics)
python ai_doc_orchestrator_kage3_v1_2_4.py


## Environment Setup

### Prerequisites

* Python **3.10+** (recommended: 3.11)
* Latest `pip`

### 1) Create and activate a virtual environment (Windows / PowerShell)


py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip


If PowerShell blocks activation:


Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1


### 2) Install dependencies

* Runtime only:

pip install -r requirements.txt


* Development / tests:


pip install -r requirements-dev.txt


### 3) Run tests


python -m pytest -q


### Optional: lock dependencies (pip-tools)


pip install pip-tools
pip-compile requirements.txt -o requirements.lock.txt
pip-compile requirements-dev.txt -o requirements-dev.lock.txt
pip-sync requirements-dev.lock.txt


### Notes

* **matplotlib**: use `plt.savefig(...)` in headless environments (CI, servers). Avoid `plt.show()` unless a GUI backend is available.
* **Linux / macOS** (equivalent):


python3 -m venv .venv
source .venv/bin/activate



