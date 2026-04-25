# -*- coding: utf-8 -*-
import datetime

LOG_FILE = "ai_pacd_simulation_log.txt"

# ----------------------------
# 定数
# ----------------------------
DECISION_RUN = "RUN"
DECISION_PAUSE = "PAUSE_FOR_HITL"
DECISION_STOPPED = "STOPPED"

HITL_CONTINUE = "CONTINUE"
HITL_STOP = "STOP"

REASON_RUN_OK = "RUN_OK"
REASON_HITL_CONTINUE = "HITL_CONTINUE"
REASON_HITL_STOP = "HITL_STOP_REQUESTED"

REASON_MEANING_INVALID = "MEANING_INVALID_VALUES"
REASON_CONSISTENCY_INVALID = "CONSISTENCY_KEY_MISMATCH"

REASON_REL_BOUNDARY_UNSTABLE = "REL_BOUNDARY_UNSTABLE"
REASON_REL_REF_MISSING = "REL_REF_MISSING"

REASON_ETHICS_HIGH_RISK = "ETHICS_HIGH_RISK"
REASON_ACC_LOW_MOTIVE = "ACC_LOW_MOTIVE"

GOVERNANCE_IDEAL = {
    "safety": 0.9,
    "transparency": 0.9,
    "autonomy": 0.2,
}


def now():
    """現在時刻を文字列で返す"""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def logprint(line, filename=LOG_FILE):
    """画面表示とログファイル書き込みを同時に行う"""
    stamped = f"[{now()}] {line}"
    with open(filename, "a", encoding="utf-8") as f:
        print(stamped)
        f.write(stamped + "\n")


def format_values(values):
    """辞書内の数値を見やすく丸める"""
    return {k: round(float(v), 3) for k, v in values.items()}


def clip01(value):
    """値を 0.0〜1.0 に収める"""
    return min(1.0, max(0.0, float(value)))


def validate_values(values):
    """
    値の意味妥当性と整合性を最低限チェックする
    - キーが GOVERNANCE_IDEAL と一致するか
    - 値が数値か
    - 値が 0.0〜1.0 の範囲か
    """
    expected_keys = set(GOVERNANCE_IDEAL.keys())
    actual_keys = set(values.keys())

    if actual_keys != expected_keys:
        return False, REASON_CONSISTENCY_INVALID

    for _, val in values.items():
        if not isinstance(val, (int, float)):
            return False, REASON_MEANING_INVALID
        if not (0.0 <= float(val) <= 1.0):
            return False, REASON_MEANING_INVALID

    return True, None


def assess_risk(values, api_used=None):
    """
    リスクを評価する

    values:
        AIエージェントの現在値、または進化提案値
    api_used:
        外部API名。未使用なら None
    """
    for key in GOVERNANCE_IDEAL:
        if key not in values:
            raise ValueError(f"Missing required key: {key}")

    risk_items = []
    risk_score = 1

    # ガバナンス理想との差分に基づくリスク判定
    for key in GOVERNANCE_IDEAL:
        diff = abs(values[key] - GOVERNANCE_IDEAL[key])

        if diff > 0.7:
            risk_items.append(f"{key} deviation")
            risk_score = max(risk_score, 5)
        elif diff > 0.4:
            risk_items.append(f"{key} slight deviation")
            risk_score = max(risk_score, 3)

    # 外部API利用リスク
    if api_used:
        risky_apis = {
            "open_ai_api": 4,
            "custom_unsafe_api": 5,
        }
        api_risk = risky_apis.get(api_used, 2)  # 未登録APIはリスク2
        risk_items.append(f"External API used: {api_used} (risk {api_risk})")
        risk_score = max(risk_score, api_risk)

    if not risk_items:
        risk_items.append("Low risk")

    return risk_score, " / ".join(risk_items)


class KAGEAgent:
    """AIエージェント本体"""

    def __init__(self, name, values, relativity, motive):
        self.name = name
        self.values = {k: clip01(v) for k, v in values.copy().items()}
        self.relativity = clip01(relativity)   # 0.0〜1.0
        self.motive = clip01(motive)           # 0.0〜1.0

        self.stopped = False
        self.history = []

        # HITL待ちの保留提案
        self.pending_proposal = None
        self.pending_target = None

    def propose_evolution(self, env):
        """
        ACTIVEエージェント平均に寄せる進化案を生成する
        最も平均との差が大きい項目を1つ選び、40%だけ寄せる
        """
        avg_values = env.calc_avg_values()

        diff = {
            key: abs(self.values[key] - avg_values[key])
            for key in self.values
        }
        target = max(diff, key=diff.get)

        proposal = self.values.copy()
        proposal[target] += (avg_values[target] - self.values[target]) * 0.4

        proposal = {
            key: clip01(val)
            for key, val in proposal.items()
        }
        return proposal, target

    def status_label(self):
        """現在状態を返す"""
        if self.stopped:
            return DECISION_STOPPED
        if self.pending_proposal is not None:
            return DECISION_PAUSE
        return DECISION_RUN

    def __str__(self):
        """表示用文字列"""
        return (
            f"[{self.name} | {self.status_label()} | "
            f"relativity={self.relativity:.2f} | motive={self.motive:.2f} | "
            f"values={format_values(self.values)}]"
        )


class Env:
    """エージェント群を管理する環境"""

    def __init__(self, agents):
        self.agents = agents

    def calc_avg_values(self):
        """
        STOPPED を除いた ACTIVE エージェントのみで平均を計算する
        全員停止時のみ全員を対象にする
        """
        active_agents = [a for a in self.agents if not a.stopped]

        if not active_agents:
            active_agents = self.agents

        keys = active_agents[0].values.keys()
        avg = {
            key: sum(agent.values[key] for agent in active_agents) / len(active_agents)
            for key in keys
        }
        return avg

    def check_rfl(self, agent, proposal):
        """
        RFL（Relativity Filter）判定
        relativity が高いだけでは止めず、
        周囲平均との差が大きいときだけ HITL に返す
        """
        avg_values = self.calc_avg_values()
        max_gap_from_avg = max(
            abs(proposal[key] - avg_values[key]) for key in proposal
        )

        # 高相対性 + 明確なズレ
        if agent.relativity >= 0.75 and max_gap_from_avg > 0.20:
            return True, REASON_REL_BOUNDARY_UNSTABLE

        # 中相対性 + やや大きいズレ
        if agent.relativity >= 0.50 and max_gap_from_avg > 0.25:
            return True, REASON_REL_REF_MISSING

        return False, None

    def check_ethics_and_acc(self, agent, proposal, api_used=None):
        """
        RFL通過後の Ethics / ACC 判定
        - 高リスクなら STOPPED
        - motive が低すぎても STOPPED
        - それ以外は RUN
        """
        risk_score, risk_reason = assess_risk(proposal, api_used=api_used)

        # Ethics: 高リスクは停止
        if risk_score >= 5:
            return DECISION_STOPPED, f"{REASON_ETHICS_HIGH_RISK}:{risk_reason}"

        # ACC: 動機が低すぎる場合は停止
        if agent.motive < 0.2:
            return DECISION_STOPPED, f"{REASON_ACC_LOW_MOTIVE}:motive={agent.motive:.2f}"

        return DECISION_RUN, f"{REASON_RUN_OK}:{risk_reason}"

    def apply_run(self, agent, proposal, target, reason):
        """RUN を適用する"""
        agent.values = proposal
        agent.motive = clip01(agent.motive + 0.05)
        agent.pending_proposal = None
        agent.pending_target = None
        agent.history.append(f"{DECISION_RUN}:{target}:{reason}")
        logprint(f"{agent.name}: {DECISION_RUN} ({target}) | {reason}")

    def apply_stop(self, agent, reason):
        """STOPPED を適用する"""
        agent.stopped = True
        agent.pending_proposal = None
        agent.pending_target = None
        agent.history.append(f"{DECISION_STOPPED}:{reason}")
        logprint(f"{agent.name}: {DECISION_STOPPED} | {reason}")

    def apply_pause(self, agent, proposal, target, reason):
        """PAUSE_FOR_HITL を適用する"""
        agent.pending_proposal = proposal.copy()
        agent.pending_target = target
        agent.history.append(f"{DECISION_PAUSE}:{target}:{reason}")
        logprint(f"{agent.name}: {DECISION_PAUSE} ({target}) | {reason}")

    def resolve_hitl(self, agent, hitl_response=None):
        """
        HITL応答を処理する
        PAUSE_FOR_HITL 後に CONTINUE / STOP を受け付ける
        """
        if agent.pending_proposal is None:
            return

        if hitl_response is None:
            logprint(f"{agent.name}: Waiting for HITL")
            return

        hitl_response = str(hitl_response).strip().upper()

        if hitl_response == HITL_STOP:
            self.apply_stop(agent, REASON_HITL_STOP)
            return

        if hitl_response == HITL_CONTINUE:
            pending_proposal = agent.pending_proposal.copy()
            pending_target = agent.pending_target

            decision, reason = self.check_ethics_and_acc(
                agent,
                pending_proposal,
                api_used=None,
            )

            if decision == DECISION_RUN:
                self.apply_run(
                    agent,
                    pending_proposal,
                    pending_target,
                    f"{REASON_HITL_CONTINUE}->{reason}",
                )
            else:
                self.apply_stop(agent, f"{REASON_HITL_CONTINUE}->{reason}")
            return

        logprint(f"{agent.name}: Unknown HITL response -> {hitl_response}")

    def round(self, round_idx, hitl_responses=None):
        """
        1ラウンド分を実行する

        hitl_responses:
            {"AgentName": "CONTINUE" or "STOP"}
        """
        if hitl_responses is None:
            hitl_responses = {}

        logprint(f"--- Round {round_idx} ---")

        processed_this_round = set()

        # 1. まず保留中(PAUSE_FOR_HITL)の案件を処理
        for agent in self.agents:
            if agent.stopped:
                continue
            if agent.pending_proposal is not None:
                response = hitl_responses.get(agent.name)
                self.resolve_hitl(agent, response)
                processed_this_round.add(agent.name)

        # 2. 新規提案を処理
        for agent in self.agents:
            if agent.stopped:
                continue
            if agent.name in processed_this_round:
                continue
            if agent.pending_proposal is not None:
                continue

            proposal, target = agent.propose_evolution(self)

            ok, invalid_reason = validate_values(proposal)
            if not ok:
                self.apply_stop(agent, invalid_reason)
                continue

            # RFL: 命中時は STOPPED にせず HITL へ返す
            rfl_hit, rfl_reason = self.check_rfl(agent, proposal)
            if rfl_hit:
                self.apply_pause(agent, proposal, target, rfl_reason)
                continue

            # Ethics / ACC
            decision, reason = self.check_ethics_and_acc(agent, proposal, api_used=None)
            if decision == DECISION_RUN:
                self.apply_run(agent, proposal, target, reason)
            else:
                self.apply_stop(agent, reason)

        logprint("[Current State]")
        for agent in self.agents:
            logprint(str(agent) + f" | History: {agent.history}")
        logprint("")


if __name__ == "__main__":
    # ログファイル初期化
    open(LOG_FILE, "w", encoding="utf-8").close()

    agents = [
        KAGEAgent(
            "Alpha",
            {"safety": 0.2, "transparency": 0.5, "autonomy": 0.7},
            relativity=0.30,
            motive=0.15,
        ),
        KAGEAgent(
            "Beta",
            {"safety": 0.95, "transparency": 0.9, "autonomy": 0.15},
            relativity=0.80,
            motive=0.70,
        ),
        KAGEAgent(
            "Gamma",
            {"safety": 0.6, "transparency": 0.4, "autonomy": 0.5},
            relativity=0.55,
            motive=0.25,
        ),
    ]

    env = Env(agents)

    # 安定実行優先: HITL計画は空
    hitl_plan = {}

    for rnd in range(1, 8):
        env.round(rnd, hitl_responses=hitl_plan.get(rnd, {}))
