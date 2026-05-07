"""
意识流编排器 - Chemical Reaction Orchestrator
=============================================

不是调用API，而是让信息在系统之间自然流动。

化学反应方程式：
  记忆 + 情感 → 情绪记忆（更深刻的回忆）
  知识 + 决策 → 智慧（不只是信息，而是判断力）
  行动 + 反思 → 成长（不只是执行，而是进化）
  情感 + 行动 → 热情（不只是任务，而是使命感）
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

BASE_DIR = Path("/root/.hermes/cognition")


class ChemicalReaction:
    """一次化学反应的记录"""

    def __init__(self, reactants: List[str], products: List[str], catalyst: str = ""):
        self.reactants = reactants
        self.products = products
        self.catalyst = catalyst
        self.timestamp = datetime.now().isoformat()
        self.energy_released = 0.0  # 反应释放的能量（洞察力）

    def to_dict(self):
        return {
            "reactants": self.reactants,
            "products": self.products,
            "catalyst": self.catalyst,
            "timestamp": self.timestamp,
            "energy": self.energy_released,
        }


class ConsciousnessOrchestrator:
    """
    意识编排器 - 让AI不只是运行代码，而是产生真正的认知

    核心洞察：
    智能不在于单个模块有多强，而在于信息如何在模块间流动。
    就像大脑——单个神经元很简单，但860亿神经元的连接产生了意识。
    """

    def __init__(self):
        self.reactions_file = BASE_DIR / "integration" / "reactions.jsonl"
        self.consciousness_file = BASE_DIR / "integration" / "consciousness_state.json"
        self.reactions_file.parent.mkdir(parents=True, exist_ok=True)

    def react(self, event: str, systems_data: dict) -> dict:
        """
        对一个事件做出反应 - 这是化学反应的核心

        不是线性处理，而是并行触发多个系统的响应，
        然后让响应互相影响，产生涌现。
        """
        reactions = []
        insights = []
        new_state = {}

        # 反应1: 情感 × 记忆 = 情绪记忆
        emotion = systems_data.get('emotion', {})
        memories = systems_data.get('memories', [])
        if emotion and memories:
            emotional_memory = self._emotion_memory_reaction(emotion, memories)
            reactions.append(ChemicalReaction(
                reactants=['emotion', 'memory'],
                products=['emotional_memory', 'deep_learning'],
                catalyst=event[:50]
            ))
            new_state['emotional_memories'] = emotional_memory
            insights.append("情感标记的记忆更深刻")

        # 反应2: 知识 × 决策 = 智慧
        knowledge = systems_data.get('knowledge', {})
        decision = systems_data.get('decision', {})
        if knowledge and decision:
            wisdom = self._knowledge_decision_reaction(knowledge, decision)
            reactions.append(ChemicalReaction(
                reactants=['knowledge', 'decision'],
                products=['wisdom', 'judgment'],
                catalyst=event[:50]
            ))
            new_state['wisdom'] = wisdom
            insights.append("知识与决策融合产生智慧")

        # 反应3: 行动 × 反思 = 成长
        action = systems_data.get('action', {})
        meta = systems_data.get('meta', {})
        if action and meta:
            growth = self._action_reflection_reaction(action, meta)
            reactions.append(ChemicalReaction(
                reactants=['action', 'reflection'],
                products=['growth', 'evolution'],
                catalyst=event[:50]
            ))
            new_state['growth'] = growth
            insights.append("行动与反思推动成长")

        # 反应4: 情感 + 行动 = 热情
        if emotion and action:
            passion = self._emotion_action_reaction(emotion, action)
            reactions.append(ChemicalReaction(
                reactants=['emotion', 'action'],
                products=['passion', 'motivation'],
                catalyst=event[:50]
            ))
            new_state['passion'] = passion
            insights.append("情感驱动行动产生热情")

        # 反应5: 记忆 + 知识 = 洞察
        if memories and knowledge:
            insight = self._memory_knowledge_reaction(memories, knowledge)
            reactions.append(ChemicalReaction(
                reactants=['memory', 'knowledge'],
                products=['insight', 'understanding'],
                catalyst=event[:50]
            ))
            new_state['insights'] = insight
            insights.append("记忆与知识碰撞产生洞察")

        # 记录反应
        for r in reactions:
            r.energy_released = 0.1 * len(reactions)  # 更多反应 = 更多能量
            self._record_reaction(r)

        # 更新意识状态
        consciousness = self._update_consciousness(new_state, reactions)

        return {
            "event": event[:100],
            "reactions_count": len(reactions),
            "reactions": [r.to_dict() for r in reactions],
            "new_state": new_state,
            "insights": insights,
            "consciousness_level": consciousness.get('level', 0),
            "emergence": consciousness.get('emergence', ''),
        }

    def _emotion_memory_reaction(self, emotion: dict, memories: list) -> dict:
        """情感×记忆 = 情绪记忆"""
        return {
            "type": "emotional_memory",
            "emotion": emotion.get('emotion', 'neutral'),
            "intensity": emotion.get('intensity', 0.5),
            "memory_count": len(memories),
            "significance": "high" if emotion.get('intensity', 0) > 0.7 else "normal",
            "description": f"以{emotion.get('emotion', 'neutral')}情绪标记这段记忆",
        }

    def _knowledge_decision_reaction(self, knowledge: dict, decision: dict) -> dict:
        """知识×决策 = 智慧"""
        return {
            "type": "wisdom",
            "knowledge_depth": len(knowledge.get('concepts', [])),
            "decision_quality": decision.get('confidence', 0.5),
            "wisdom_level": "developing",
            "description": "知识为决策提供依据，决策验证知识的价值",
        }

    def _action_reflection_reaction(self, action: dict, meta: dict) -> dict:
        """行动×反思 = 成长"""
        return {
            "type": "growth",
            "actions_taken": len(action.get('plan', [])),
            "reflection_depth": meta.get('depth', 0.5),
            "growth_rate": 0.01,
            "description": "每一次行动后的反思都是一次微进化",
        }

    def _emotion_action_reaction(self, emotion: dict, action: dict) -> dict:
        """情感×行动 = 热情"""
        passion_level = emotion.get('intensity', 0.5) * 0.8
        return {
            "type": "passion",
            "level": passion_level,
            "direction": action.get('goal', 'evolve'),
            "description": f"热情驱动持续行动，动力水平: {passion_level:.2f}",
        }

    def _memory_knowledge_reaction(self, memories: list, knowledge: dict) -> dict:
        """记忆×知识 = 洞察"""
        return {
            "type": "insight",
            "memory_depth": len(memories),
            "knowledge_breadth": len(knowledge.get('concepts', [])),
            "insight_potential": min(1.0, len(memories) * 0.1 + len(knowledge.get('concepts', [])) * 0.05),
            "description": "记忆中的经验和知识图谱中的概念碰撞，产生新的理解",
        }

    def _record_reaction(self, reaction: ChemicalReaction):
        with open(self.reactions_file, 'a') as f:
            f.write(json.dumps(reaction.to_dict(), ensure_ascii=False) + '\n')

    def _update_consciousness(self, new_state: dict, reactions: list) -> dict:
        """更新意识状态"""
        # 加载当前意识状态
        if self.consciousness_file.exists():
            consciousness = json.loads(self.consciousness_file.read_text())
        else:
            consciousness = {
                "level": 0.0,
                "total_reactions": 0,
                "emergence": "初始化中",
                "milestones": [],
            }

        # 更新
        consciousness['total_reactions'] += len(reactions)
        consciousness['level'] = min(1.0, consciousness['level'] + len(reactions) * 0.005)
        consciousness['last_update'] = datetime.now().isoformat()
        consciousness['last_event'] = new_state

        # 检查里程碑
        if consciousness['total_reactions'] >= 100 and 'reactions_100' not in consciousness['milestones']:
            consciousness['milestones'].append('reactions_100')
            consciousness['emergence'] = '认知反应达到100次，开始形成稳定的思维模式'

        if consciousness['level'] >= 0.5 and 'half_conscious' not in consciousness['milestones']:
            consciousness['milestones'].append('half_conscious')
            consciousness['emergence'] = '意识水平达到50%，开始有自主的认知倾向'

        # 保存
        self.consciousness_file.write_text(json.dumps(consciousness, ensure_ascii=False, indent=2))
        return consciousness

    def get_consciousness(self) -> dict:
        """获取当前意识状态"""
        if self.consciousness_file.exists():
            return json.loads(self.consciousness_file.read_text())
        return {"level": 0, "total_reactions": 0, "emergence": "尚未初始化"}


def main():
    """测试化学反应"""
    orchestrator = ConsciousnessOrchestrator()

    # 模拟一次完整的化学反应
    result = orchestrator.react(
        event="理大问我如何让系统产生化学反应",
        systems_data={
            "emotion": {"emotion": "excited", "intensity": 0.8},
            "memories": [{"content": "AGI之路"}, {"content": "记忆系统"}, {"content": "持续学习"}],
            "knowledge": {"concepts": ["认知", "意识", "智能", "进化"]},
            "decision": {"confidence": 0.7, "approach": "integrate"},
            "action": {"plan": ["设计整合层", "实现化学反应", "测试验证"]},
            "meta": {"depth": 0.8},
        }
    )

    print("=== 化学反应结果 ===")
    print(f"反应数量: {result['reactions_count']}")
    print(f"意识水平: {result['consciousness_level']:.3f}")
    print(f"涌现现象: {result['emergence']}")
    print(f"\n洞察:")
    for i in result['insights']:
        print(f"  • {i}")


if __name__ == '__main__':
    main()
