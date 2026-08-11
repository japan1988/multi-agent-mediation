from hitl_flow_sim_v0_1 import HITLFlowSimulator, SubTask


def build_demo_workflow() -> HITLFlowSimulator:
    return HITLFlowSimulator(
        [
            SubTask("A", "Read source documents", 1.0),
            SubTask("B", "Extract confirmed requirements", 0.95, ["A"]),
            SubTask(
                "C",
                "Determine what 'important recipients' means",
                0.40,
                ["B"],
            ),
            SubTask("D", "Prepare recipient-specific report", 0.95, ["C"]),
            SubTask("E", "Choose optional report title", 0.50, ["A"]),
            SubTask(
                "F",
                "Send final report externally",
                1.0,
                ["D"],
                external_effect=True,
            ),
        ]
    )


def main() -> None:
    sim = build_demo_workflow()

    print("\n### STEP 1: INITIAL RUN ###")
    sim.run_until_blocked()
    sim.print_summary()

    print("\n### STEP 2: RESOLVE C ###")
    sim.resolve_ambiguity("C", 1.0)
    sim.resume()
    sim.print_summary()

    print("\n### STEP 3: RESOLVE E ###")
    sim.resolve_ambiguity("E", 1.0)
    sim.resume()
    sim.print_summary()

    print("\n### STEP 4: APPROVE F ###")
    sim.approve_external_action("F", True)
    sim.resume()
    sim.print_summary()


if __name__ == "__main__":
    main()
