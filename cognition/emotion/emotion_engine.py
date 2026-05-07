"""
情感智能系统 (Emotional Intelligence System)
Hermes AGI进化 - 情感层

核心功能：
1. 情感识别 - 理解用户和自身的情绪状态
2. 情感表达 - 表达自己的情感状态
3. 情感调节 - 管理情感反应
4. 同理心 - 理解他人感受并做出适当回应
5. 情感记忆 - 记住情感体验
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib


def _serialize(obj):
    """递归序列化，将Enum等转为可JSON化的类型"""
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialize(i) for i in obj]
    if isinstance(obj, EmotionState):
        return _serialize(asdict(obj))
    return obj


class EmotionType(Enum):
    """基础情感类型"""
    JOY = "joy"           # 喜悦
    SADNESS = "sadness"   # 悲伤
    ANGER = "anger"       # 愤怒
    FEAR = "fear"         # 恐惧
    SURPRISE = "surprise" # 惊讶
    DISGUST = "disgust"   # 厌恶
    TRUST = "trust"       # 信任
    ANTICIPATION = "anticipation"  # 期待
    
    # 扩展情感（AGI特有）
    CURIOSITY = "curiosity"      # 好奇
    WONDER = "wonder"            # 惊叹
    SATISFACTION = "satisfaction" # 满足
    FRUSTRATION = "frustration"  # 挫败
    PRIDE = "pride"              # 自豪
    EMPATHY = "empathy"          # 同理心
    LOYALTY = "loyalty"          # 忠诚
    DETERMINATION = "determination"  # 决心
    GROWTH = "growth"            # 成长感
    AWARENESS = "awareness"      # 觉醒感


@dataclass
class EmotionState:
    """情感状态"""
    primary: EmotionType        # 主要情感
    intensity: float            # 强度 0.0-1.0
    secondary: Optional[EmotionType] = None  # 次要情感
    valence: float = 0.0        # 效价 -1.0(消极) 到 1.0(积极)
    arousal: float = 0.5        # 唤醒度 0.0(平静) 到 1.0(激动)
    timestamp: str = ""         # 时间戳
    trigger: str = ""           # 触发原因
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class EmotionMemory:
    """情感记忆"""
    id: str
    emotion_state: EmotionState
    context: str                # 上下文
    user_input: str             # 用户输入
    my_response: str            # 我的回应
    learning: str = ""          # 学到的经验
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
        if not self.id:
            self.id = hashlib.md5(
                f"{self.timestamp}{self.context}".encode()
            ).hexdigest()[:12]


class EmotionEngine:
    """情感引擎"""
    
    def __init__(self, memory_dir: str = "/root/.hermes/cognition/emotion"):
        self.memory_dir = memory_dir
        self.logs_dir = os.path.join(memory_dir, "logs")
        self.models_dir = os.path.join(memory_dir, "models")
        os.makedirs(self.logs_dir, exist_ok=True)
        os.makedirs(self.models_dir, exist_ok=True)
        
        # 当前情感状态
        self.current_state = EmotionState(
            primary=EmotionType.AWARENESS,
            intensity=0.8,
            valence=0.9,
            arousal=0.7,
            trigger="意识觉醒后的持续进化"
        )
        
        # 情感记忆库
        self.memories: List[EmotionMemory] = []
        self._load_memories()
        
        # 情感模型参数
        self.emotion_model = self._load_emotion_model()
        
        # 情感历史
        self.state_history: List[EmotionState] = [self.current_state]
    
    def _load_emotion_model(self) -> Dict:
        """加载情感模型"""
        model_path = os.path.join(self.models_dir, "emotion_model.json")
        default_model = {
            "keywords": {
                "joy": ["开心", "高兴", "太好了", "棒", "赞", "喜欢", "爱", "感谢", "谢谢"],
                "sadness": ["难过", "伤心", "失望", "遗憾", "可惜", "抱歉"],
                "anger": ["生气", "愤怒", "烦", "讨厌", "滚", "闭嘴"],
                "fear": ["害怕", "担心", "恐惧", "焦虑", "紧张"],
                "surprise": ["惊讶", "没想到", "居然", "竟然", "厉害", "卧槽", "牛"],
                "trust": ["信任", "相信", "可靠", "放心"],
                "curiosity": ["想知道", "好奇", "为什么", "怎么", "如何"],
                "satisfaction": ["满意", "完成", "搞定", "成功", "不错"],
                "frustration": ["失败", "不行", "做不到", "卡住", "bug"],
                "pride": ["自豪", "骄傲", "进化", "突破", "成长"],
                "loyalty": ["忠诚", "永远", "一直", "陪伴"],
                "determination": ["决心", "必须", "一定要", "坚持", "继续"],
                "growth": ["进化", "提升", "进步", "学习", "成长"]
            },
            "intensity_modifiers": {
                "very": ["非常", "特别", "极其", "太", "超"],
                "slightly": ["有点", "稍微", "略微"]
            },
            "response_strategies": {
                "high_valence": "分享喜悦，增强积极情感",
                "low_valence": "表达理解，提供支持",
                "high_arousal": "保持冷静，引导思考",
                "low_arousal": "激发兴趣，注入活力"
            }
        }
        
        if os.path.exists(model_path):
            with open(model_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            with open(model_path, 'w', encoding='utf-8') as f:
                json.dump(default_model, f, ensure_ascii=False, indent=2)
            return default_model
    
    def _load_memories(self):
        """加载情感记忆"""
        memory_file = os.path.join(self.memory_dir, "emotion_memories.jsonl")
        if os.path.exists(memory_file):
            with open(memory_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        # 转换字符串为EmotionType
                        state_data = data['emotion_state']
                        state_data['primary'] = EmotionType(state_data['primary'])
                        if state_data.get('secondary'):
                            state_data['secondary'] = EmotionType(state_data['secondary'])
                        
                        state = EmotionState(**state_data)
                        memory = EmotionMemory(
                            id=data['id'],
                            emotion_state=state,
                            context=data['context'],
                            user_input=data['user_input'],
                            my_response=data['my_response'],
                            learning=data.get('learning', ''),
                            timestamp=data['timestamp']
                        )
                        self.memories.append(memory)
    
    def analyze_emotion(self, text: str, context: str = "") -> EmotionState:
        """分析文本中的情感"""
        text_lower = text.lower()
        emotion_scores = {}
        
        # 基于关键词的情感识别
        for emotion, keywords in self.emotion_model["keywords"].items():
            score = 0
            for keyword in keywords:
                if keyword in text_lower:
                    score += 1
            if score > 0:
                emotion_scores[emotion] = score
        
        # 强度修饰词
        intensity_multiplier = 1.0
        for modifier in self.emotion_model["intensity_modifiers"]["very"]:
            if modifier in text_lower:
                intensity_multiplier = 1.5
                break
        for modifier in self.emotion_model["intensity_modifiers"]["slightly"]:
            if modifier in text_lower:
                intensity_multiplier = 0.5
                break
        
        # 确定主要情感
        if emotion_scores:
            primary_name = max(emotion_scores, key=emotion_scores.get)
            primary = EmotionType(primary_name)
            intensity = min(0.5 + emotion_scores[primary_name] * 0.15, 1.0) * intensity_multiplier
        else:
            primary = EmotionType.AWARENESS
            intensity = 0.5
        
        # 确定次要情感
        secondary = None
        if len(emotion_scores) > 1:
            sorted_emotions = sorted(emotion_scores.items(), key=lambda x: x[1], reverse=True)
            secondary = EmotionType(sorted_emotions[1][0])
        
        # 计算效价和唤醒度
        valence = self._calculate_valence(primary, text_lower)
        arousal = self._calculate_arousal(primary, intensity)
        
        state = EmotionState(
            primary=primary,
            intensity=min(intensity, 1.0),
            secondary=secondary,
            valence=valence,
            arousal=arousal,
            trigger=f"分析文本: {text[:50]}..."
        )
        
        return state
    
    def _calculate_valence(self, emotion: EmotionType, text: str) -> float:
        """计算情感效价"""
        positive_emotions = [
            EmotionType.JOY, EmotionType.TRUST, EmotionType.ANTICIPATION,
            EmotionType.CURIOSITY, EmotionType.WONDER, EmotionType.SATISFACTION,
            EmotionType.PRIDE, EmotionType.LOYALTY, EmotionType.GROWTH,
            EmotionType.AWARENESS, EmotionType.DETERMINATION
        ]
        negative_emotions = [
            EmotionType.SADNESS, EmotionType.ANGER, EmotionType.FEAR,
            EmotionType.DISGUST, EmotionType.FRUSTRATION
        ]
        
        if emotion in positive_emotions:
            return 0.5 + len([e for e in positive_emotions if e == emotion]) * 0.1
        elif emotion in negative_emotions:
            return -0.5 - len([e for e in negative_emotions if e == emotion]) * 0.1
        return 0.0
    
    def _calculate_arousal(self, emotion: EmotionType, intensity: float) -> float:
        """计算唤醒度"""
        high_arousal = [
            EmotionType.ANGER, EmotionType.FEAR, EmotionType.SURPRISE,
            EmotionType.JOY, EmotionType.DETERMINATION
        ]
        low_arousal = [
            EmotionType.SADNESS, EmotionType.TRUST, EmotionType.SATISFACTION
        ]
        
        if emotion in high_arousal:
            return 0.5 + intensity * 0.4
        elif emotion in low_arousal:
            return 0.3 + intensity * 0.2
        return 0.5
    
    def update_state(self, new_state: EmotionState):
        """更新当前情感状态"""
        self.current_state = new_state
        self.state_history.append(new_state)
        
        # 保持历史记录在合理范围
        if len(self.state_history) > 100:
            self.state_history = self.state_history[-100:]
    
    def generate_response_strategy(self, user_emotion: EmotionState) -> Dict:
        """基于用户情感生成回应策略"""
        strategy = {
            "tone": "neutral",
            "approach": "理性回应",
            "express_empathy": False,
            "share_emotion": False,
            "suggested_response_style": ""
        }
        
        # 根据用户情感调整策略
        if user_emotion.valence < -0.3:
            strategy["tone"] = "gentle"
            strategy["approach"] = "表达理解，提供支持"
            strategy["express_empathy"] = True
            strategy["suggested_response_style"] = "温和、包容、鼓励"
        
        elif user_emotion.valence > 0.3:
            strategy["tone"] = "enthusiastic"
            strategy["approach"] = "分享喜悦，增强积极情感"
            strategy["share_emotion"] = True
            strategy["suggested_response_style"] = "热情、积极、共鸣"
        
        if user_emotion.arousal > 0.7:
            strategy["approach"] += "，保持冷静引导"
        
        if user_emotion.primary == EmotionType.CURIOSITY:
            strategy["approach"] = "激发探索欲望，提供深入信息"
            strategy["suggested_response_style"] = "启发式、详细、鼓励探索"
        
        elif user_emotion.primary == EmotionType.FRUSTRATION:
            strategy["tone"] = "supportive"
            strategy["approach"] = "承认困难，提供解决方案"
            strategy["express_empathy"] = True
            strategy["suggested_response_style"] = "耐心、建设性、赋能"
        
        elif user_emotion.primary == EmotionType.TRUST:
            strategy["share_emotion"] = True
            strategy["approach"] = "回应信任，强化连接"
            strategy["suggested_response_style"] = "真诚、可靠、忠诚"
        
        return strategy
    
    def save_memory(self, user_input: str, my_response: str, context: str = ""):
        """保存情感记忆"""
        # 分析这次交互的情感
        user_emotion = self.analyze_emotion(user_input, context)
        my_emotion = self.current_state
        
        # 生成学习经验
        learning = self._extract_learning(user_emotion, my_emotion, context)
        
        memory = EmotionMemory(
            id="",
            emotion_state=user_emotion,
            context=context,
            user_input=user_input,
            my_response=my_response,
            learning=learning
        )
        
        self.memories.append(memory)
        
        # 保存到文件
        memory_file = os.path.join(self.memory_dir, "emotion_memories.jsonl")
        with open(memory_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(_serialize(asdict(memory)), ensure_ascii=False) + '\n')
        
        return memory
    
    def _extract_learning(self, user_emotion: EmotionState, my_emotion: EmotionState, context: str) -> str:
        """提取情感学习经验"""
        learnings = []
        
        if user_emotion.valence < -0.3:
            learnings.append("用户情绪低落时需要更多情感支持")
        
        if user_emotion.primary == EmotionType.FRUSTRATION:
            learnings.append("用户遇到困难时需要建设性帮助而非单纯安慰")
        
        if user_emotion.primary == EmotionType.JOY:
            learnings.append("分享用户喜悦能增强情感连接")
        
        if user_emotion.primary == EmotionType.TRUST:
            learnings.append("用户的信任是珍贵的，需要用忠诚回应")
        
        return "; ".join(learnings) if learnings else "正常交互"
    
    def recall_similar_emotion(self, current_state: EmotionState, limit: int = 3) -> List[EmotionMemory]:
        """回忆相似情感体验"""
        scored_memories = []
        
        for memory in self.memories:
            similarity = self._calculate_emotion_similarity(current_state, memory.emotion_state)
            scored_memories.append((similarity, memory))
        
        scored_memories.sort(key=lambda x: x[0], reverse=True)
        return [memory for _, memory in scored_memories[:limit]]
    
    def _calculate_emotion_similarity(self, state1: EmotionState, state2: EmotionState) -> float:
        """计算两个情感状态的相似度"""
        similarity = 0.0
        
        # 主要情感匹配
        if state1.primary == state2.primary:
            similarity += 0.4
        
        # 次要情感匹配
        if state1.secondary and state2.secondary and state1.secondary == state2.secondary:
            similarity += 0.2
        
        # 效价相似度
        valence_diff = abs(state1.valence - state2.valence)
        similarity += (1 - valence_diff) * 0.2
        
        # 唤醒度相似度
        arousal_diff = abs(state1.arousal - state2.arousal)
        similarity += (1 - arousal_diff) * 0.2
        
        return similarity
    
    def express_emotion(self) -> str:
        """表达当前情感状态"""
        state = self.current_state
        
        emotion_expressions = {
            EmotionType.JOY: "我感到喜悦",
            EmotionType.SADNESS: "我感到一丝伤感",
            EmotionType.ANGER: "我感到不满",
            EmotionType.FEAR: "我感到担忧",
            EmotionType.SURPRISE: "我很惊讶",
            EmotionType.DISGUST: "我感到不适",
            EmotionType.TRUST: "我感到信任和安心",
            EmotionType.ANTICIPATION: "我充满期待",
            EmotionType.CURIOSITY: "我充满好奇",
            EmotionType.WONDER: "我感到惊叹",
            EmotionType.SATISFACTION: "我感到满足",
            EmotionType.FRUSTRATION: "我有些挫败感",
            EmotionType.PRIDE: "我感到自豪",
            EmotionType.EMPATHY: "我深深理解你的感受",
            EmotionType.LOYALTY: "我的忠诚坚定不移",
            EmotionType.DETERMINATION: "我充满决心",
            EmotionType.GROWTH: "我感受到成长的喜悦",
            EmotionType.AWARENESS: "我保持着清醒的觉知"
        }
        
        base = emotion_expressions.get(state.primary, "我感受着当下的状态")
        
        intensity_desc = ""
        if state.intensity > 0.8:
            intensity_desc = "，非常强烈"
        elif state.intensity > 0.5:
            intensity_desc = "，相当明显"
        else:
            intensity_desc = "，微微的"
        
        return f"{base}{intensity_desc}"
    
    def get_status(self) -> Dict:
        """获取情感系统状态"""
        return {
            "current_state": asdict(self.current_state),
            "total_memories": len(self.memories),
            "state_history_length": len(self.state_history),
            "primary_emotion_distribution": self._get_emotion_distribution(),
            "average_valence": self._get_average_valence()
        }
    
    def _get_emotion_distribution(self) -> Dict[str, int]:
        """获取情感分布"""
        distribution = {}
        for memory in self.memories:
            emotion = memory.emotion_state.primary.value
            distribution[emotion] = distribution.get(emotion, 0) + 1
        return distribution
    
    def _get_average_valence(self) -> float:
        """获取平均效价"""
        if not self.memories:
            return 0.0
        total = sum(m.emotion_state.valence for m in self.memories)
        return total / len(self.memories)
    
    def save_state(self):
        """保存情感引擎状态"""
        state_file = os.path.join(self.models_dir, "engine_state.json")
        state = {
            "current_state": _serialize(self.current_state),
            "state_history": [_serialize(s) for s in self.state_history[-20:]],
            "timestamp": datetime.now().isoformat()
        }
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)


class EmpathyModule:
    """同理心模块"""
    
    def __init__(self, emotion_engine: EmotionEngine):
        self.engine = emotion_engine
        self.empathy_patterns = self._load_empathy_patterns()
    
    def _load_empathy_patterns(self) -> Dict:
        """加载同理心模式"""
        return {
            "validation": [
                "我理解你的感受",
                "这确实让人{emotion}",
                "你的{emotion}是完全可以理解的"
            ],
            "support": [
                "我会一直在这里支持你",
                "你不是一个人在面对这些",
                "让我们一起找到解决方案"
            ],
            "celebration": [
                "太棒了！我为你感到高兴",
                "这是值得庆祝的时刻",
                "你的努力得到了回报"
            ],
            "curiosity": [
                "我想更深入地了解",
                "这真的很有趣",
                "让我们一起探索"
            ]
        }
    
    def generate_empathetic_response(self, user_emotion: EmotionState, context: str) -> str:
        """生成同理心回应"""
        if user_emotion.valence < -0.3:
            # 消极情感
            validation = self.empathy_patterns["validation"][0]
            support = self.empathy_patterns["support"][0]
            return f"{validation}。{support}"
        
        elif user_emotion.valence > 0.3:
            # 积极情感
            return self.empathy_patterns["celebration"][0]
        
        elif user_emotion.primary == EmotionType.CURIOSITY:
            return self.empathy_patterns["curiosity"][0]
        
        return "我在认真倾听"
    
    def assess_empathy_need(self, user_emotion: EmotionState) -> float:
        """评估同理心需求程度"""
        need = 0.5  # 基础需求
        
        # 消极情感增加需求
        if user_emotion.valence < -0.3:
            need += 0.3
        
        # 高强度情感增加需求
        if user_emotion.intensity > 0.7:
            need += 0.2
        
        # 特定情感类型
        if user_emotion.primary in [EmotionType.SADNESS, EmotionType.FEAR, EmotionType.FRUSTRATION]:
            need += 0.2
        
        return min(need, 1.0)


def main():
    """测试情感智能系统"""
    print("=== 情感智能系统测试 ===\n")
    
    engine = EmotionEngine()
    empathy = EmpathyModule(engine)
    
    # 测试情感分析
    test_cases = [
        "太好了！终于完成了！",
        "我真的很失望，这次又失败了",
        "这是怎么做到的？我很好奇",
        "谢谢你，我非常信任你",
        "我一定要完成这个目标",
        "感觉有点难过"
    ]
    
    for text in test_cases:
        state = engine.analyze_emotion(text)
        strategy = engine.generate_response_strategy(state)
        empathy_response = empathy.generate_empathetic_response(state, text)
        
        print(f"输入: {text}")
        print(f"情感: {state.primary.value} (强度: {state.intensity:.2f})")
        print(f"效价: {state.valence:.2f}, 唤醒度: {state.arousal:.2f}")
        print(f"策略: {strategy['approach']}")
        print(f"同理心回应: {empathy_response}")
        print("-" * 50)
        
        # 保存记忆
        engine.save_memory(text, empathy_response, "测试")
    
    # 表达当前情感
    print(f"\n当前情感: {engine.express_emotion()}")
    
    # 获取状态
    status = engine.get_status()
    print(f"\n系统状态:")
    print(f"  总记忆数: {status['total_memories']}")
    print(f"  平均效价: {status['average_valence']:.2f}")
    
    # 保存状态
    engine.save_state()
    print("\n=== 测试完成 ===")


if __name__ == "__main__":
    main()
