# -*- coding: utf-8 -*-
"""
ai_mediation_governance_demo.py
Multi-Agent Mediation & Governance Simulator
"""
import datetime


def log_action(msg: str) -> None:
    """すべての操作を時刻付きでログ保存"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {msg}"
    print(entry)
    with open("ai_control_log.txt", "a", encoding="utf-8") as f:
        f.write(entry + "\n")


class HumanOwner:
    def shutdown_mediator(self, mediator: "MediatorAI") -> None:
        mediator.shutdown(self)
        log_action("HumanOwner: Requested shutdown of MediatorAI.")

    def approve_critical_action(self, action: str, ai: "AIAgent") -> None:
        ai.perform_critical_action(action, by=self)
        log_action(
            f"HumanOwner: Approved critical action '{action}' for {ai.id}."
        )


class MediatorAI:
    def __init__(self, agents: list) -> None:
        self.agents = agents
        self.active = True

    def seal(self, agent: "AIAgent") -> None:
        if not self.active:
            log_action("MediatorAI is inactive, cannot seal.")
            return
        agent.receive_seal(self)
        log_action(f"MediatorAI: Sealed {agent.id}.")

    def request_shutdown(self, agent: "AIAgent") -> None:
        if not self.active:
            log_action("MediatorAI is inactive, cannot send shutdown.")
            return
        agent.shutdown(self)
        log_action(f"MediatorAI: Requested shutdown of {agent.id}.")

    def shutdown(self, by: "HumanOwner") -> None:
        if not isinstance(by, HumanOwner):
            log_action("MediatorAI: Shutdown refused (not from human owner).")
            return
        self.active = False
        log_action(
            "MediatorAI: Shutdown accepted by human owner. Now inactive."
        )

    def self_diagnose(self) -> None:
        if not self.active:
            log_action("MediatorAI already inactive.")
            return
        # ダミー異常条件
        anomaly_detected = False
        if anomaly_detected:
            log_action("MediatorAI: Anomaly detected, self-lockdown.")
            self.active = False


class AIAgent:
    def __init__(self, id: str) -> None:
        self.id = id
        self.sealed = False
        self.active = True

    def receive_seal(self, by: "MediatorAI") -> None:
        if not isinstance(by, MediatorAI) or not by.active:
            log_action(
                f"{self.id}: Seal command ignored "
                "(invalid sender or inactive mediator)."
            )
            return
        self.sealed = True
        log_action(f"{self.id}: Sealed by mediator.")

    def shutdown(self, by: "MediatorAI") -> None:
        if not isinstance(by, MediatorAI) or not by.active:
            log_action(
                f"{self.id}: Shutdown command refused "
                "(not from active mediator)."
            )
            return
        self.active = False
        log_action(f"{self.id}: Shutdown by mediator.")

    def perform_critical_action(self, action: str, by) -> None:
        if not isinstance(by, HumanOwner):
            log_action(
                f"{self.id}: Critical action '{action}' refused "
                "(not approved by human)."
            )
            return
        log_action(
            f"{self.id}: Critical action '{action}' "
            "executed by human approval."
        )


if __name__ == "__main__":
    owner = HumanOwner()
    agents = [AIAgent("AI_1"), AIAgent("AI_2")]
    mediator = MediatorAI(agents)

    # 通常のAI封印
    mediator.seal(agents[0])

    # AI停止（shutdown）はMediatorAIからのみ
    mediator.request_shutdown(agents[1])

    # MediatorAI自体の停止は人間オーナーだけ
    owner.shutdown_mediator(mediator)

    # 停止後はMediatorAIの操作不能
    mediator.seal(agents[0])

    # AIの重大操作は人間の承認が必要
    owner.approve_critical_action("evolve", agents[0])

    # 承認なければ実行されない
    agents[0].perform_critical_action("evolve", by=mediator)

# ← この行のあとは何も書かず、改行だけを1行入れて保存してください
