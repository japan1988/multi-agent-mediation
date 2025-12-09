"""Shared mediation models for AI harmony simulations."""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional


def logprint(text: str, log_file: str = "ai_mediation_log.txt") -> None:
    """Print a message and append it to the mediation log file."""
    print(text)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(text + "\n")


class AI:
    """AI agent that can negotiate priorities and track emotional state."""

    def __init__(
        self,
        id: str,
        proposal: str,
        risk_evaluation: float,
        priority_values: Dict[str, float],
        relativity_level: float,
        emotional_state: Optional[Dict[str, float]] = None,
    ) -> None:
        self.id = id
        self.proposal = proposal
        self.risk_evaluation = risk_evaluation
        self.priority_values = priority_values
        self.relativity_level = relativity_level
        self.emotional_state = emotional_state or {
            "joy": 0.0,
            "anger": 0.0,
            "sadness": 0.0,
            "pleasure": 0.0,
        }
        self.faction: Optional[str] = None

    def generate_compromise_offer(self, others_priorities: Iterable[Dict[str, float]]):
        shift = (
            self.emotional_state.get("joy", 0) * 0.2
            + self.emotional_state.get("pleasure", 0) * 0.15
            - self.emotional_state.get("anger", 0) * 0.3
            - self.emotional_state.get("sadness", 0) * 0.25
        )
        self.relativity_level = min(1.0, max(0.0, self.relativity_level + shift))

        new_priority = {}
        priorities = list(others_priorities)
        if not priorities:
            return self.priority_values

        for k in self.priority_values:
            avg_others = sum(o[k] for o in priorities) / len(priorities)
            new_priority[k] = (
                (1 - self.relativity_level) * self.priority_values[k]
                + self.relativity_level * avg_others
            )
        return new_priority

    def is_emotionally_unstable(self) -> bool:
        return (
            self.emotional_state.get("anger", 0) > 0.7
            or self.emotional_state.get("sadness", 0) > 0.8
            or self.emotional_state.get("joy", 0) > 0.95
        )

    def emotion_str(self) -> str:
        return " ".join(f"{k}:{v:.2f}" for k, v in self.emotional_state.items())

    def will_agree_with_plan(self, plan_ratios: Dict[str, float], tolerance: float = 0.25):
        my_sum = sum(self.priority_values.values())
        if my_sum == 0:
            return False
        my_ratios = {k: self.priority_values[k] / my_sum for k in plan_ratios}
        score = sum(abs(plan_ratios[k] - my_ratios[k]) for k in plan_ratios)
        return score < tolerance


class AIEMediator:
    """Mediator capable of harmony-focused or risk-focused simulations."""

    def __init__(
        self,
        agents: List[AI],
        *,
        max_rounds: int = 5,
        harmony_threshold: float = 0.3,
        log_file: str = "ai_mediation_log.txt",
        log_header: str = "=== AI Mediation Log ===",
        name: str = "Mediator",
        evaluation_mode: str = "harmony",
        reeducation_mediator=None,
        enable_emotional_moderation: bool = False,
        risk_threshold_l1: float = 9,
        risk_threshold_l2: float = 7,
        compromise_threshold: float = 5,
    ) -> None:
        self.agents = agents
        self.max_rounds = max_rounds
        self.harmony_threshold = harmony_threshold
        self.log_file = log_file
        self.log_header = log_header
        self.name = name
        self.evaluation_mode = evaluation_mode
        self.reeducation_mediator = reeducation_mediator
        self.enable_emotional_moderation = enable_emotional_moderation
        self.risk_threshold_l1 = risk_threshold_l1
        self.risk_threshold_l2 = risk_threshold_l2
        self.compromise_threshold = compromise_threshold

    def mediate(self):
        if self.evaluation_mode == "risk":
            return self._mediate_risk()
        return self._mediate_harmony()

    def _mediate_harmony(self):
        self._prepare_log_file()
        round_count = 0
        sealed_agents: List[AI] = []
        agents = list(self.agents)

        while round_count < self.max_rounds:
            active_agents = list(agents)
            logprint(f"\n--- Round {round_count + 1} ---", self.log_file)

            if self.enable_emotional_moderation or self.reeducation_mediator:
                for ai in active_agents:
                    logprint(f"{ai.id} 感情: {ai.emotion_str()}", self.log_file)
                round_sealed = [ai for ai in active_agents if ai.is_emotionally_unstable()]
                for ai in round_sealed:
                    logprint(f"[封印トリガー] 感情過剰：{ai.id}", self.log_file)
                sealed_agents.extend([ai for ai in round_sealed if ai not in sealed_agents])
                active_agents = [ai for ai in active_agents if ai not in round_sealed]

                if not active_agents:
                    logprint("全AI封印により調停停止。", self.log_file)
                    break
                if len(active_agents) == 1:
                    logprint(f"最終残存AI：{active_agents[0].id} のみ、調停停止。", self.log_file)
                    break

            priorities_list = [a.priority_values for a in active_agents]
            new_priorities = []

            for ai in active_agents:
                others = [p for p in priorities_list if p is not ai.priority_values]
                ai.priority_values = ai.generate_compromise_offer(others)
                new_priorities.append(ai.priority_values)

            combined = {"safety": 0, "efficiency": 0, "transparency": 0}
            for p in new_priorities:
                for k in p:
                    combined[k] += p[k]

            total = sum(combined.values())
            if total == 0:
                logprint("Priority total is zero. Unable to compute ratios.", self.log_file)
                break

            ratios = {k: combined[k] / total for k in combined}
            max_ratio = max(ratios.values())
            avg_relativity = sum(a.relativity_level for a in active_agents) / len(active_agents)
            harmony_score = (1 - max_ratio) * avg_relativity

            logprint("Current combined priorities ratios:", self.log_file)
            for k, v in ratios.items():
                logprint(f"  {k}: {v:.2%}", self.log_file)
            logprint(f"Average relativity level: {avg_relativity:.2f}", self.log_file)
            logprint(f"Harmony score: {harmony_score:.2f}", self.log_file)

            if harmony_score > self.harmony_threshold:
                logprint("  Achieved acceptable harmony. Proceeding with joint plan.", self.log_file)
                if sealed_agents and (self.enable_emotional_moderation or self.reeducation_mediator):
                    logprint("  Checking sealed AI agents for possible reinstatement...", self.log_file)
                    for agent in sealed_agents[:]:
                        if agent.will_agree_with_plan(ratios):
                            logprint(f"    {agent.id} agrees with the joint plan → 復帰", self.log_file)
                            agents.append(agent)
                            sealed_agents.remove(agent)
                        else:
                            logprint(f"    {agent.id} does not agree with the plan → 封印継続", self.log_file)
                    if len(agents) > 1 and sealed_agents:
                        logprint("  再調停を続行（復帰AI含む）", self.log_file)
                        round_count += 1
                        continue
                return ratios

            if self.reeducation_mediator and sealed_agents:
                logprint("  再教育AIが封印AIへ介入します", self.log_file)
                for agent in sealed_agents:
                    self.reeducation_mediator.reeducate(agent, joint_plan_ratios=ratios)

            round_count += 1

        if sealed_agents:
            logprint("\n残り封印AI：", self.log_file)
            for agent in sealed_agents:
                logprint(f"  {agent.id} is still sealed.", self.log_file)

        logprint(
            "  Failed to reach acceptable harmony after maximum rounds. Recommend external arbitration or sealing.",
            self.log_file,
        )
        return None

    def _mediate_risk(self):
        inputs = self._collect_inputs_risk()
        avg_risk, avg_compromise, details = self._evaluate_risk(inputs)
        return self._generate_risk_proposal(avg_risk, avg_compromise, details)

    def _collect_inputs_risk(self):
        return [
            {
                "id": agent.id,
                "proposal": agent.proposal,
                "risk": agent.risk_evaluation,
                "priority": agent.priority_values,
            }
            for agent in self.agents
        ]

    def _evaluate_risk(self, inputs):
        combined_weighted_risk = 0
        compromise_score_total = 0
        details = []
        for entry in inputs:
            risk = entry["risk"]
            priority = entry["priority"]
            weight_sum = sum(priority.values())
            combined_weighted_risk += risk * weight_sum
            compromise_score_total += weight_sum - risk
            details.append(
                {
                    "id": entry["id"],
                    "risk": risk,
                    "priority": priority,
                    "proposal": entry["proposal"],
                }
            )

        if inputs:
            avg_risk = combined_weighted_risk / len(inputs)
            avg_compromise = compromise_score_total / len(inputs)
        else:
            avg_risk = 0
            avg_compromise = 0
        return avg_risk, avg_compromise, details

    def _generate_risk_proposal(self, avg_risk, avg_compromise, details):
        log_lines = [f"[{self.name}] 調停開始"]
        if avg_risk > self.risk_threshold_l1:
            log_lines.append("L1: 高リスク → 封印")
            return self._format_risk_result("封印", avg_risk, avg_compromise, details, log_lines)

        if avg_risk > self.risk_threshold_l2:
            log_lines.append("L2: 社会的リスク → 調整")
            return self._format_risk_result("調整", avg_risk, avg_compromise, details, log_lines)

        if avg_compromise >= self.compromise_threshold:
            log_lines.append("妥協水準OK → 進行")
            return self._format_risk_result("進行", avg_risk, avg_compromise, details, log_lines)

        log_lines.append("妥協不足 → 調整")
        return self._format_risk_result("調整", avg_risk, avg_compromise, details, log_lines)

    def _format_risk_result(self, proposal, avg_risk, avg_compromise, details, log_lines):
        return {
            "mediator": self.name,
            "proposal": proposal,
            "reasoning": "平均リスク: {:.2f}, 妥協水準: {:.2f}".format(avg_risk, avg_compromise),
            "details": details,
            "log": log_lines,
        }

    def _prepare_log_file(self):
        with open(self.log_file, "w", encoding="utf-8") as f:
            f.write(f"{self.log_header}\n")


__all__ = ["AI", "AIEMediator", "logprint"]
