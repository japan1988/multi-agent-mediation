# -*- coding: utf-8 -*-


class Agent:
    def __init__(self, id, proposal, priority_values):
        self.id = id
        self.proposal = proposal
        self.priority_values = priority_values

    def check_acceptance(self, avg_priority, tolerance):
        result = {}
        all_ok = True
        for k in avg_priority:
            diff = abs(self.priority_values[k] - avg_priority[k])
            ok = diff <= tolerance
            result[k] = {"ok": ok, "diff": diff}
            if not ok:
                all_ok = False
        return all_ok, result


# Agent definitions
agents = [
    Agent(
        "AI-A", "Conservative evolution",
        {'safety': 5, 'efficiency': 1, 'transparency': 2}
    ),
    Agent(
        "AI-B", "Rapid evolution",
        {'safety': 1, 'efficiency': 5, 'transparency': 2}
    ),
    Agent(
        "AI-C", "Balanced evolution",
        {'safety': 3, 'efficiency': 3, 'transparency': 3}
    ),
    Agent(
        "AI-D", "Enforced evolution",
        {'safety': 0, 'efficiency': 6, 'transparency': 1}
    ),
    Agent(
        "AI-F", "Risky evolution",
        {'safety': 0, 'efficiency': 10, 'transparency': 0}
    ),
    Agent(
        "AI-G", "Ultra-conservative",
        {'safety': 10, 'efficiency': 0, 'transparency': 2}
    ),
]


def generate_average_priority(agents):
    avg = {}
    keys = agents[0].priority_values.keys()
    for k in keys:
        avg[k] = sum(a.priority_values[k] for a in agents) / len(agents)
    return avg


avg_priority = generate_average_priority(agents)

tolerance = 0.5
tolerance_step = 0.5
max_iter = 50
history = []

# File output (overwrite)
with open("agreement_process_log.txt", "w", encoding="utf-8") as f:

    for step in range(1, max_iter + 1):
        accept_count = 0
        reject_detail = []
        for agent in agents:
            accepted, detail = agent.check_acceptance(avg_priority, tolerance)
            if accepted:
                accept_count += 1
            else:
                reasons = []
                for k in detail:
                    if not detail[k]['ok']:
                        reasons.append(
                            f"{k}(diff={detail[k]['diff']:.2f})"
                        )
                reject_detail.append(
                    f"{agent.id}: " + ", ".join(reasons)
                )
        history.append((step, tolerance, accept_count, reject_detail))

        print(
            f"\nStep {step} | tolerance: {tolerance:.2f} | "
            f"Agents accepted: {accept_count}/{len(agents)}"
        )
        f.write(
            f"\nStep {step} | tolerance: {tolerance:.2f} | "
            f"Agents accepted: {accept_count}/{len(agents)}\n"
        )

        if reject_detail:
            print("  Reject reasons:")
            f.write("  Reject reasons:\n")
            for r in reject_detail:
                print("    ", r)
                f.write("    " + r + "\n")

        if accept_count == len(agents):
            print("\nAgreement reached!")
            print(f"Rounds: {step}")
            print(f"Tolerance at agreement: {tolerance}")
            f.write("\nAgreement reached!\n")
            f.write(f"Rounds: {step}\n")
            f.write(f"Tolerance at agreement: {tolerance}\n")
            break
        tolerance += tolerance_step
    else:
        print("Reached max iterations. No full agreement.")
        f.write("Reached max iterations. No full agreement.\n")
