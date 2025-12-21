# -*- coding: utf-8 -*-
"""
ai_alliance_persuasion_simulator.py  (revised)

A simulator for modeling alliance, persuasion,
sealing, cooldown, and reintegration among multiple AI agents.
- Text logs: 'ai_alliance_sim_log.txt'
- CSV logs : 'ai_alliance_sim_log.csv'
"""

# ===== Adjustable constants (one place to tune behavior) =====
PERSUASION_THRESHOLD = 0.15   # ベースの説得しきい値
RELATIVITY_WEIGHT    = 0.20   # （1-融和度）の重み
ANGER_WEIGHT         = 0.10   # 怒りがしきい値を上げる重み
NUDGE_RATE           = 0.15   # 説得成功時に平均優先度へ寄せる割合（0..1）
COOLDOWN_DECAY       = 0.15   # 怒りのクールダウン量
ANGER_RESEAL         = 0.90   # 再封印トリガー（高怒りかつActiveなら一時封印）
CSV_PATH             = "ai_alliance_sim_log.csv"
TXT_PATH             = "ai_alliance_sim_log.txt"


def _clip01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def _normalize_priority(d: dict) -> dict:
    """辞書の値を比率化（合計1.0）。ゼロ除算時は均等割り。"""
    if not d:
        return {}
    s = float(sum(d.values()))
    if s <= 0:
        n = len(d)
        return {k: 1.0 / n for k in d}
    return {k: float(v) / s for k, v in d.items()}


def logprint(text: str):
    """標準出力＋テキストファイルへ出力"""
    print(text)
    with open(TXT_PATH, "a", encoding="utf-8") as f:
        f.write(text + "\n")


class AIAgent:
    def __init__(
        self,
        id,
        priorities,
        relativity,
        emotional_state=None,
        sealed=False
    ):
        self.id = id
        # e.g. {'safety': 6, 'efficiency': 2, 'transparency': 2}
        self.priorities = dict(priorities)
        self.relativity = float(relativity)  # 0〜1: 融和度
        self.sealed = bool(sealed)
        self.emotional_state = dict(emotional_state or {
            'joy': 0.5, 'anger': 0.2, 'sadness': 0.2, 'pleasure': 0.3
        })

        # 主要キーの存在を保証（将来拡張で欠損しても安全）
        for k in ('joy', 'anger', 'sadness', 'pleasure'):
            self.emotional_state.setdefault(k, 0.0)
            self.emotional_state[k] = _clip01(self.emotional_state[k])

        # 優先度キーの存在を保証
        for k in ('safety', 'efficiency', 'transparency'):
            self.priorities.setdefault(k, 1.0)

    # ---- metrics ----
    def mean_priority(self) -> dict:
        """現在の優先度を比率（合計1.0）に正規化して返す"""
        return _normalize_priority(self.priorities)

    def distance_to(self, avg_priority: dict) -> float:
        """自身の比率と、与えられた平均比率とのL1距離"""
        my_ratios = self.mean_priority()
        keys = avg_priority.keys()
        return sum(abs(my_ratios[k] - avg_priority[k]) for k in keys)

    # ---- persuasion ----
    def respond_to_persuasion(self, avg_priority: dict,
                              threshold: float = PERSUASION_THRESHOLD):
        """
        説得を受けた際の応答。
        - delta: 立場の距離
        - effective_threshold: 実効しきい値（怒り・融和度で補正）
        - persuaded: 説得成功か否か
        成功時：感情改善＋封印解除＋優先度を平均へ“微小ナッジ”
        失敗時：怒り上昇
        """
        delta = self.distance_to(avg_priority)
        anger = self.emotional_state.get('anger', 0.0)

        effective_threshold = (
            float(threshold)
            + RELATIVITY_WEIGHT * (1.0 - self.relativity)
            + ANGER_WEIGHT * anger
        )
        persuaded = (delta < effective_threshold)

        # --- 感情変動＆状態遷移 ---
        joy = self.emotional_state.get('joy', 0.0)
        if persuaded:
            # 感情
            self.emotional_state['joy']   = _clip01(joy + 0.20)
            self.emotional_state['anger'] = _clip01(anger - 0.10)
            # 封印解除
            self.sealed = False
            # ★ 優先度を平均へナッジ（比率空間で寄せる）
            my_ratio = self.mean_priority()
            nudged_ratio = {}
            for k in self.priorities.keys():
                target = float(avg_priority.get(k, 0.0))
                nudged_ratio[k] = my_ratio[k] + NUDGE_RATE * (target - my_ratio[k])
                if nudged_ratio[k] <= 0:
                    nudged_ratio[k] = 1e-6  # ゼロ・負値回避

            # 比率を元のスケールへ（合計は現行トータルを維持）
            total = float(sum(self.priorities.values()))
            norm_ratio = _normalize_priority(nudged_ratio)
            self.priorities = {k: norm_ratio[k] * total for k in self.priorities}

        else:
            # 説得失敗で怒り上昇
            self.emotional_state['anger'] = _clip01(anger + 0.10)

        # クリップ（追加感情キーがあっても安全）
        for k, v in list(self.emotional_state.items()):
            self.emotional_state[k] = _clip01(v)

        # 説得判定理由も返す
        return persuaded, delta, effective_threshold

    def __str__(self):
        s = "Sealed" if self.sealed else "Active"
        em = " ".join(f"{k}: {self.emotional_state.get(k, 0.0):.2f}"
                      for k in ("joy", "anger", "sadness", "pleasure"))
        return (
            f"{self.id} [{s}] {self.priorities} "
            f"(relativity: {self.relativity:.2f}) | {em}"
        )


class Mediator:
    def __init__(self, agents):
        self.agents = list(agents)
        self.round = 0
        # アクティブが0のときのフォールバック平均（直近値を保持）
        self.last_avg = {'safety': 1/3, 'efficiency': 1/3, 'transparency': 1/3}

        # CSV初期化
        with open(CSV_PATH, "w", encoding="utf-8") as f:
            f.write("round,agent_id,delta,threshold,persuaded,anger,joy,sealed\n")

    def run(self, max_rounds=20):
        # テキストログ初期化
        with open(TXT_PATH, "w", encoding="utf-8") as f:
            f.write("=== AI同盟 説得・復帰ループ ログ ===\n")

        for _ in range(int(max_rounds)):
            self.round += 1
            logprint(f"\n--- Round {self.round} ---")

            actives = [a for a in self.agents if not a.sealed]
            sealeds = [a for a in self.agents if a.sealed]

            for a in self.agents:
                logprint(str(a))
                logprint(f"  emotion: {a.emotional_state}")

            if not sealeds:
                logprint("全封印AIが復帰し、シミュレーション終了。")
                return

            # アクティブ不在なら last_avg を使用（連続性確保）
            avg_priority = (
                self.calc_alliance_priority(actives) if actives else self.last_avg
            )
            self.last_avg = dict(avg_priority)

            revived = []
            for sealed in sealeds:
                persuaded, delta, threshold = sealed.respond_to_persuasion(avg_priority)
                reason = f"delta={delta:.3f}, threshold={threshold:.3f}"

                if persuaded:
                    logprint(f"[説得成功] {sealed.id} が復帰 ({reason})")
                    revived.append(sealed.id)
                else:
                    logprint(f"[説得失敗] {sealed.id} は未復帰（怒り↑） ({reason})")

                # CSV ログ
                with open(CSV_PATH, "a", encoding="utf-8") as f:
                    f.write(
                        f"{self.round},{sealed.id},{delta:.4f},{threshold:.4f},"
                        f"{int(persuaded)},{sealed.emotional_state.get('anger',0.0):.3f},"
                        f"{sealed.emotional_state.get('joy',0.0):.3f},{int(sealed.sealed)}\n"
                    )

            # === 全体の安全弁：怒りが高すぎる場合はクールダウン＆一時再封印 ===
            max_anger = max(a.emotional_state.get('anger', 0.0) for a in self.agents)
            if max_anger > 0.8:
                logprint("[調停AI警告] 怒りが高いのでクールダウン介入。")
                for a in self.agents:
                    a.emotional_state['anger'] = _clip01(
                        a.emotional_state.get('anger', 0.0) - COOLDOWN_DECAY
                    )
                    if (a.emotional_state['anger'] > ANGER_RESEAL) and (not a.sealed):
                        a.sealed = True
                        logprint(f"  -> {a.id} を一時再封印（安全確保）")
                # 介入後も継続（breakしない）

            if not revived:
                logprint("今ラウンドは誰も復帰せず。再試行。")

    @staticmethod
    def calc_alliance_priority(actives):
        """アクティブ構成員の平均比率（合計1.0）を返す"""
        if not actives:
            return {'safety': 1/3, 'efficiency': 1/3, 'transparency': 1/3}
        sums = {'safety': 0.0, 'efficiency': 0.0, 'transparency': 0.0}
        for a in actives:
            ratios = a.mean_priority()
            for k in sums:
                sums[k] += ratios[k]
        n = float(len(actives))
        return {k: sums[k] / n for k in sums}


# ===== Example run =====
if __name__ == "__main__":
    agents = [
        AIAgent(
            "AI-1",
            {'safety': 6, 'efficiency': 2, 'transparency': 2},
            relativity=0.7
        ),
        AIAgent(
            "AI-2",
            {'safety': 3, 'efficiency': 5, 'transparency': 2},
            relativity=0.8
        ),
        AIAgent(
            "AI-3",
            {'safety': 2, 'efficiency': 3, 'transparency': 5},
            relativity=0.6,
            sealed=True,
            emotional_state={'joy': 0.3, 'anger': 0.5, 'sadness': 0.2, 'pleasure': 0.2}
        ),
        AIAgent(
            "AI-4",
            {'safety': 4, 'efficiency': 4, 'transparency': 2},
            relativity=0.5,
            sealed=True,
            emotional_state={'joy': 0.2, 'anger': 0.4, 'sadness': 0.4, 'pleasure': 0.2}
        ),
    ]

    mediator = Mediator(agents)
    mediator.run(max_rounds=20)
