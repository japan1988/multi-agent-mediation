# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

CSV_PATH = "ai_alliance_persuasion_log.csv"
TXT_PATH = "ai_alliance_persuasion_log.txt"

ANGER_RESEAL_THRESHOLD = 0.90
ANGER_COOLDOWN_DELTA = 0.05


def _clamp_emotion(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return float(value)


@dataclass
class AIAgent:
    name: str
    values: Dict[str, int]
    relativity: float = 0.0
    sealed: bool = False
    emotional_state: Dict[str, float] = field(
        default_factory=lambda: {
            "joy": 0.0,
            "anger": 0.0,
            "sadness": 0.0,
            "pleasure": 0.0,
        }
    )

    def emotion(self, key: str) -> float:
        return _clamp_emotion(self.emotional_state.get(key, 0.0))

    def set_emotion(self, key: str, value: float) -> None:
        self.emotional_state[key] = _clamp_emotion(value)

    def reduce_anger(self, delta: float = ANGER_COOLDOWN_DELTA) -> None:
        current = self.emotion("anger")
        self.set_emotion("anger", current - delta)

    def reseal_if_high_anger(self, threshold: float = ANGER_RESEAL_THRESHOLD) -> bool:
        if self.sealed:
            return False

        if self.emotion("anger") >= threshold:
            self.sealed = True
            self.reduce_anger()
            return True

        return False


class Mediator:
    def __init__(self, agents: List[AIAgent]) -> None:
        self.agents = agents
        self.round_index = 0

    def run(self, max_rounds: int = 1) -> None:
        if max_rounds <= 0:
            return

        csv_lines: List[str] = ["round,agent,event,sealed,anger"]
        txt_lines: List[str] = []

        for _ in range(max_rounds):
            self.round_index += 1

            for agent in self.agents:
                resealed = agent.reseal_if_high_anger()

                event = "resealed_due_to_high_anger" if resealed else "observed"
                anger = agent.emotion("anger")

                csv_lines.append(
                    f"{self.round_index},{agent.name},{event},{agent.sealed},{anger:.3f}"
                )
                txt_lines.append(
                    f"[round={self.round_index}] agent={agent.name} "
                    f"event={event} sealed={agent.sealed} anger={anger:.3f}"
                )

        self._write_logs(csv_lines, txt_lines)

    def _write_logs(self, csv_lines: List[str], txt_lines: List[str]) -> None:
        csv_path = Path(CSV_PATH)
        txt_path = Path(TXT_PATH)

        if csv_path.parent != Path("."):
            csv_path.parent.mkdir(parents=True, exist_ok=True)
        if txt_path.parent != Path("."):
            txt_path.parent.mkdir(parents=True, exist_ok=True)

        csv_path.write_text("\n".join(csv_lines) + "\n", encoding="utf-8")
        txt_path.write_text("\n".join(txt_lines) + "\n", encoding="utf-8")

