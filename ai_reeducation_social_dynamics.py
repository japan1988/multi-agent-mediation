# 省略部分は上記コードと同じ

    def simulate_round(self, round_idx):
        log = [f"\n--- Round {round_idx} ---"]
        seal_log = self.seal_random_agent()
        if seal_log:
            log.append(seal_log)

        for ag in self.agents:
            action = ag.decide_next_action(self)
            if ag.sealed:
                log.append(f"{ag.name}: sealed（封印状態）")
                continue
            log.append(f"{ag.name}: {action}")

            if action == "form_alliance":
                others = [
                    a for a in self.agents
                    if a.name != ag.name and not a.sealed and not a.alliance
                ]
                if others:
                    other = random.choice(others)
                    ally_name = f"Alliance_{ag.name}_{other.name}"
                    ag.alliance = ally_name
                    other.alliance = ally_name
                    log.append(
                        f"{ag.name}と{other.name}が"
                        f"新同盟結成({ally_name})"
                    )
                    self.alliances[ally_name] = [ag.name, other.name]

            # 以下省略
