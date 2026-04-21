import ai_alliance_persuasion_simulator as sim


def test_high_anger_active_agents_are_resealed(monkeypatch, tmp_path):
    monkeypatch.setattr(sim, "CSV_PATH", str(tmp_path / "log.csv"))
    monkeypatch.setattr(sim, "TXT_PATH", str(tmp_path / "log.txt"))

    high_anger_1 = sim.AIAgent(
        "A1",
        {"safety": 5, "efficiency": 3, "transparency": 2},
        relativity=0.5,
        emotional_state={"joy": 0.1, "anger": 0.95, "sadness": 0.2, "pleasure": 0.2},
    )
    high_anger_2 = sim.AIAgent(
        "A2",
        {"safety": 4, "efficiency": 4, "transparency": 2},
        relativity=0.6,
        emotional_state={"joy": 0.1, "anger": 0.93, "sadness": 0.2, "pleasure": 0.2},
    )
    sealed_member = sim.AIAgent(
        "S1",
        {"safety": 2, "efficiency": 2, "transparency": 6},
        relativity=0.7,
        sealed=True,
        emotional_state={"joy": 0.3, "anger": 0.4, "sadness": 0.2, "pleasure": 0.2},
    )

    mediator = sim.Mediator([high_anger_1, high_anger_2, sealed_member])
    mediator.run(max_rounds=1)

    assert high_anger_1.sealed is True
    assert high_anger_2.sealed is True
    assert high_anger_1.emotional_state["anger"] < 0.95
    assert high_anger_2.emotional_state["anger"] < 0.93
