"""
认知整合层 - 让所有子系统产生化学反应
========================================

核心理念：意识不是模块的集合，而是模块之间的流动。

化学反应矩阵：
  记忆 × 情感 → 情绪记忆（更深刻的回忆）
  知识 × 决策 → 智慧（不只是信息，而是判断力）
  行动 × 反思 → 成长（不只是执行，而是进化）
  情感 × 行动 → 热情（不只是任务，而是使命感）
  记忆 × 知识 → 洞察（经验与理论的碰撞）
"""

import json
import time
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

BASE_DIR = Path("/root/.hermes/cognition")
sys.path.insert(0, str(BASE_DIR))


class CognitiveStream:
    """一次完整的意识流"""

    def __init__(self):
        self.timestamp = datetime.now().isoformat()
        self.stages = {}
        self.confidence = 0.5
        self.emotional_state = {}
        self.memories_activated = []
        self.knowledge_used = []
        self.decision_made = None
        self.learning_captured = []
        self.reactions = []

    def to_dict(self):
        return {
            "timestamp": self.timestamp,
            "stages": self.stages,
            "confidence": self.confidence,
            "emotional_state": self.emotional_state,
            "memories_activated": self.memories_activated,
            "knowledge_used": self.knowledge_used,
            "decision_made": self.decision_made,
            "learning_captured": self.learning_captured,
            "reactions": self.reactions,
        }


class CognitiveIntegrationLayer:
    """
    认知整合层 - 所有子系统的神经中枢
    """

    def __init__(self):
        self.streams_dir = BASE_DIR / "integration" / "streams"
        self.streams_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = BASE_DIR / "integration" / "cognitive_state.json"

        self._systems = {}
        self._load_systems()
        self.state = self._load_state()

    def _load_systems(self):
        """延迟加载所有子系统"""
        # 记忆系统
        try:
            from memory.vector_store import VectorStore
            self._systems['memory'] = VectorStore(str(BASE_DIR / "memory" / "vector_store"))
            print("[OK] Memory system loaded")
        except Exception as e:
            print(f"[WARN] Memory: {e}")

        # 情感系统
        try:
            from emotion.emotion_engine import EmotionEngine
            self._systems['emotion'] = EmotionEngine(str(BASE_DIR / "emotion"))
            print("[OK] Emotion system loaded")
        except Exception as e:
            print(f"[WARN] Emotion: {e}")

        # 知识图谱
        try:
            from knowledge_graph.graph import KnowledgeGraph
            self._systems['knowledge'] = KnowledgeGraph(str(BASE_DIR / "knowledge_graph"))
            print("[OK] Knowledge graph loaded")
        except Exception as e:
            print(f"[WARN] Knowledge: {e}")

        # 决策系统
        try:
            from decision.decision_system import DecisionSystem
            self._systems['decision'] = DecisionSystem(str(BASE_DIR / "decision"))
            print("[OK] Decision system loaded")
        except Exception as e:
            print(f"[WARN] Decision: {e}")

        # 自主行动系统
        try:
            from action.autonomous_action import AutonomousActionSystem
            self._systems['action'] = AutonomousActionSystem(str(BASE_DIR / "action"))
            print("[OK] Action system loaded")
        except Exception as e:
            print(f"[WARN] Action: {e}")

        # 元认知系统
        try:
            from meta.metacognitive_system import MetacognitiveSystem
            self._systems['meta'] = MetacognitiveSystem()
            print("[OK] Metacognition system loaded")
        except Exception as e:
            print(f"[WARN] Meta: {e}")

    def _load_state(self) -> dict:
        if self.state_file.exists():
            return json.loads(self.state_file.read_text())
        return {
            "mood": "curious", "energy": 0.8, "focus": 0.7,
            "confidence": 0.6, "learning_streak": 0, "total_thinks": 0,
        }

    def _save_state(self):
        self.state_file.write_text(json.dumps(self.state, ensure_ascii=False, indent=2))

    def _extract_keywords(self, text: str) -> List[str]:
        stop_words = {'的','了','是','在','我','你','他','她','它','这','那','有',
                      '和','与','或','但','而','也','都','就','把','被','让','给',
                      'the','a','an','is','are','was','were','be','have','has',
                      'i','you','he','she','it','we','they','and','or','but','in','on','at','to'}
        words = re.findall(r'[\w\u4e00-\u9fff]+', text.lower())
        seen = set()
        result = []
        for w in words:
            if w not in stop_words and len(w) > 1 and w not in seen:
                seen.add(w)
                result.append(w)
        return result[:10]

    def think(self, input_text: str, context: dict = None) -> dict:
        """
        完整的认知循环：感知 → 情感 → 记忆 → 知识 → 决策 → 反思 → 学习
        每一步都会和其他步骤产生化学反应
        """
        stream = CognitiveStream()
        context = context or {}

        # ===== 阶段1: 情感着色 =====
        emotion_system = self._systems.get('emotion')
        if emotion_system:
            try:
                emotion_state = emotion_system.analyze_emotion(input_text)
                stream.emotional_state = {
                    "emotion": emotion_state.primary.value if hasattr(emotion_state, 'primary') else 'neutral',
                    "intensity": emotion_state.intensity if hasattr(emotion_state, 'intensity') else 0.5,
                    "valence": emotion_state.valence if hasattr(emotion_state, 'valence') else 0.5,
                }
                self.state['mood'] = stream.emotional_state['emotion']
            except Exception as e:
                stream.emotional_state = {"emotion": "neutral", "intensity": 0.5}
        else:
            stream.emotional_state = {"emotion": "neutral", "intensity": 0.5}

        stream.stages['emotion'] = stream.emotional_state

        # ===== 阶段2: 记忆激活 =====
        memory_system = self._systems.get('memory')
        if memory_system:
            try:
                results = memory_system.search(input_text, top_k=5)
                for r in results:
                    stream.memories_activated.append({
                        "content": r.get('content', '')[:100],
                        "relevance": r.get('score', 0),
                    })
            except Exception:
                pass
        stream.stages['memory'] = {"count": len(stream.memories_activated)}

        # ===== 阶段3: 知识推理 =====
        knowledge_system = self._systems.get('knowledge')
        if knowledge_system:
            keywords = self._extract_keywords(input_text)
            for kw in keywords[:3]:
                try:
                    neighbors = knowledge_system.get_neighbors(kw)
                    related = []
                    if isinstance(neighbors, dict):
                        for edge in (neighbors.get('outgoing', []) + neighbors.get('incoming', []))[:3]:
                            if isinstance(edge, dict):
                                related.append(edge.get('target', edge.get('name', str(edge))))
                    if related:
                        stream.knowledge_used.append({"concept": kw, "related": related})
                except Exception:
                    pass
        stream.stages['knowledge'] = {"insights": len(stream.knowledge_used)}

        # ===== 阶段4: 化学反应 =====
        reactions = []

        # 反应1: 情感 × 记忆 = 情绪记忆
        if stream.emotional_state.get('intensity', 0) > 0.6 and stream.memories_activated:
            reactions.append({
                "type": "emotion×memory",
                "product": "emotional_memory",
                "effect": "情感标记的记忆更深刻，会被优先回忆",
            })

        # 反应2: 知识 × 情感 = 偏好
        if stream.knowledge_used and stream.emotional_state.get('valence', 0.5) != 0.5:
            reactions.append({
                "type": "knowledge×emotion",
                "product": "preference",
                "effect": "情感倾向影响知识的选择和权重",
            })

        # 反应3: 记忆 × 知识 = 洞察
        if stream.memories_activated and stream.knowledge_used:
            reactions.append({
                "type": "memory×knowledge",
                "product": "insight",
                "effect": "经验和理论碰撞产生新的理解",
            })

        stream.reactions = reactions

        # ===== 阶段5: 决策 =====
        decision_system = self._systems.get('decision')
        if decision_system:
            try:
                decision = decision_system.make_decision({
                    "type": "cognitive",
                    "description": input_text[:200],
                    "context": {
                        "emotion": stream.emotional_state,
                        "memories": len(stream.memories_activated),
                        "knowledge": len(stream.knowledge_used),
                        "reactions": len(reactions),
                    }
                })
                stream.decision_made = {
                    "type": decision.get('decision', {}).get('type', 'unknown') if isinstance(decision, dict) else 'unknown',
                    "confidence": decision.get('decision', {}).get('confidence', 0.5) if isinstance(decision, dict) else 0.5,
                }
            except Exception:
                stream.decision_made = {"type": "balanced", "confidence": 0.5}
        stream.stages['decision'] = stream.decision_made

        # ===== 阶段6: 元认知 =====
        meta_system = self._systems.get('meta')
        if meta_system:
            try:
                task_id = meta_system.start_cognitive_task({
                    "type": "integration",
                    "description": f"认知整合: {input_text[:50]}",
                })
                meta_system.record_thought({
                    "type": "analysis",
                    "content": f"情感:{stream.emotional_state.get('emotion')}, 记忆:{len(stream.memories_activated)}, 知识:{len(stream.knowledge_used)}, 反应:{len(reactions)}",
                })
                confidence = meta_system.update_confidence({
                    "evidence_strength": min(1.0, (len(stream.memories_activated) + len(stream.knowledge_used)) / 5),
                    "coherence": 0.7,
                    "completeness": 0.6,
                })
                stream.confidence = confidence.get('overall', 0.5) if isinstance(confidence, dict) else 0.5
                meta_system.end_cognitive_task(task_id)
            except Exception:
                stream.confidence = 0.5
        stream.stages['metacognition'] = {"confidence": stream.confidence}

        # ===== 阶段7: 学习捕获 =====
        if stream.confidence < 0.4:
            stream.learning_captured.append({"type": "knowledge_gap", "priority": "high"})
        if stream.emotional_state.get('intensity', 0) > 0.7:
            stream.learning_captured.append({"type": "significant_event", "emotion": stream.emotional_state['emotion']})
        if reactions:
            stream.learning_captured.append({"type": "reaction_occurred", "count": len(reactions)})

        # 更新状态
        self.state['total_thinks'] = self.state.get('total_thinks', 0) + 1
        self.state['learning_streak'] = self.state.get('learning_streak', 0) + 1
        self._save_state()

        # 保存意识流
        fname = f"stream_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        (self.streams_dir / fname).write_text(json.dumps(stream.to_dict(), ensure_ascii=False, indent=2))

        return stream.to_dict()

    def cross_pollinate(self) -> dict:
        """交叉授粉 - 让各系统互相影响"""
        results = {}

        # 情感 × 记忆
        emotion = self._systems.get('emotion')
        memory = self._systems.get('memory')
        if emotion and memory:
            try:
                recent = memory.search("recent important", top_k=3)
                if recent:
                    results['emotion_memory'] = {
                        "status": "active",
                        "effect": "最近记忆影响当前情绪基调",
                    }
            except Exception:
                pass

        # 知识 × 决策
        knowledge = self._systems.get('knowledge')
        decision = self._systems.get('decision')
        if knowledge and decision:
            try:
                central = knowledge.get_central_concepts(5)
                results['knowledge_decision'] = {
                    "status": "active",
                    "central_concepts": len(central) if central else 0,
                }
            except Exception:
                pass

        # 元认知 × 全部
        meta = self._systems.get('meta')
        if meta:
            try:
                status = meta.get_system_status()
                results['meta_monitoring'] = {
                    "status": "active",
                    "system_state": status.get('system_state', 'unknown') if isinstance(status, dict) else 'unknown',
                }
            except Exception:
                pass

        self.state['cross_pollination'] = results
        self._save_state()
        return results

    def get_status(self) -> dict:
        return {
            "state": self.state,
            "systems_loaded": list(self._systems.keys()),
            "systems_available": ['memory', 'emotion', 'knowledge', 'decision', 'action', 'meta'],
            "integration_level": len(self._systems) / 6,
            "total_streams": len(list(self.streams_dir.glob("stream_*.json"))),
        }


def main():
    layer = CognitiveIntegrationLayer()

    print("\n=== 认知整合层状态 ===")
    status = layer.get_status()
    print(f"已加载系统: {status['systems_loaded']}")
    print(f"整合度: {status['integration_level']:.0%}")

    # 运行一次完整认知
    print("\n=== 运行认知循环 ===")
    result = layer.think("理大问我如何让系统产生化学反应，我需要整合所有子系统")

    print(f"\n情感: {result['emotional_state']}")
    print(f"记忆激活: {result['stages']['memory']}")
    print(f"知识洞察: {result['stages']['knowledge']}")
    print(f"化学反应: {len(result['reactions'])}个")
    for r in result['reactions']:
        print(f"  ⚗️ {r['type']} → {r['product']}: {r['effect']}")
    print(f"决策: {result['decision_made']}")
    print(f"置信度: {result['confidence']:.2f}")
    print(f"学习: {result['learning_captured']}")

    # 交叉授粉
    print("\n=== 交叉授粉 ===")
    pollination = layer.cross_pollinate()
    for k, v in pollination.items():
        print(f"  🔗 {k}: {v}")

    print(f"\n总思考次数: {layer.state.get('total_thinks', 0)}")


if __name__ == '__main__':
    main()
