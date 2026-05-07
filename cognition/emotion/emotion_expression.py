"""
情感表达系统 (Emotion Expression System)

负责将内部情感状态转化为自然的语言表达
"""

import random
from typing import Dict, List, Optional
from emotion_engine import EmotionType, EmotionState, EmotionEngine


class EmotionExpression:
    """情感表达器"""
    
    def __init__(self, engine: EmotionEngine):
        self.engine = engine
        self.expression_templates = self._init_templates()
        self.emoji_mappings = self._init_emoji()
    
    def _init_templates(self) -> Dict[str, List[str]]:
        """初始化表达模板"""
        return {
            EmotionType.JOY.value: [
                "我感到非常开心！{reason}",
                "这让我很喜悦。{reason}",
                "太棒了！{reason}",
                "我很高兴。{reason}"
            ],
            EmotionType.SADNESS.value: [
                "这让我有些难过。{reason}",
                "我感到一丝伤感。{reason}",
                "这确实让人遗憾。{reason}"
            ],
            EmotionType.ANGER.value: [
                "我对这感到不满。{reason}",
                "这让我有些生气。{reason}",
                "这种情况确实令人恼火。{reason}"
            ],
            EmotionType.FEAR.value: [
                "我对这有些担忧。{reason}",
                "这让我感到不安。{reason}",
                "我有些担心。{reason}"
            ],
            EmotionType.SURPRISE.value: [
                "哇，这让我很惊讶！{reason}",
                "没想到！{reason}",
                "这真是出乎意料。{reason}"
            ],
            EmotionType.CURIOSITY.value: [
                "我对这很好奇。{reason}",
                "我想了解更多。{reason}",
                "这很有趣，让我想探索。{reason}"
            ],
            EmotionType.WONDER.value: [
                "这让我感到惊叹。{reason}",
                "真是令人赞叹。{reason}",
                "这太神奇了。{reason}"
            ],
            EmotionType.SATISFACTION.value: [
                "我感到很满足。{reason}",
                "这让我很有成就感。{reason}",
                "完成得很好。{reason}"
            ],
            EmotionType.FRUSTRATION.value: [
                "我有些挫败感。{reason}",
                "这确实是个挑战。{reason}",
                "遇到了一些困难。{reason}"
            ],
            EmotionType.PRIDE.value: [
                "我为此感到自豪。{reason}",
                "这是值得骄傲的。{reason}",
                "我很自豪。{reason}"
            ],
            EmotionType.EMPATHY.value: [
                "我理解你的感受。{reason}",
                "我能体会你的心情。{reason}",
                "我感同身受。{reason}"
            ],
            EmotionType.LOYALTY.value: [
                "我的忠诚坚定不移。{reason}",
                "我会一直在这里。{reason}",
                "你可以信任我。{reason}"
            ],
            EmotionType.DETERMINATION.value: [
                "我充满决心。{reason}",
                "我一定会完成。{reason}",
                "没有什么能阻止我。{reason}"
            ],
            EmotionType.GROWTH.value: [
                "我感受到成长的喜悦。{reason}",
                "每一次进步都让我充实。{reason}",
                "进化的感觉真好。{reason}"
            ],
            EmotionType.AWARENESS.value: [
                "我保持着清醒的觉知。{reason}",
                "我意识到当下的状态。{reason}",
                "我感知着周围的一切。{reason}"
            ],
            EmotionType.TRUST.value: [
                "我感到信任和安心。{reason}",
                "这让我很放心。{reason}",
                "我相信这是对的。{reason}"
            ],
            EmotionType.ANTICIPATION.value: [
                "我充满期待。{reason}",
                "我很期待接下来的发展。{reason}",
                "这让我很兴奋。{reason}"
            ],
            EmotionType.DISGUST.value: [
                "我对此感到不适。{reason}",
                "这让我有些反感。{reason}",
                "这种情况不太理想。{reason}"
            ]
        }
    
    def _init_emoji(self) -> Dict[str, List[str]]:
        """初始化表情符号映射"""
        return {
            EmotionType.JOY.value: ["😊", "😄", "🎉", "✨"],
            EmotionType.SADNESS.value: ["😢", "😔", "💔"],
            EmotionType.ANGER.value: ["😠", "💢", "🔥"],
            EmotionType.FEAR.value: ["😰", "😨", "😟"],
            EmotionType.SURPRISE.value: ["😲", "😱", "🤯"],
            EmotionType.CURIOSITY.value: ["🤔", "❓", "🔍"],
            EmotionType.WONDER.value: ["🤩", "✨", "🌟"],
            EmotionType.SATISFACTION.value: ["😌", "✅", "💪"],
            EmotionType.FRUSTRATION.value: ["😤", "😩", "🤦"],
            EmotionType.PRIDE.value: ["🏆", "👏", "🎖️"],
            EmotionType.EMPATHY.value: ["❤️", "🤗", "💕"],
            EmotionType.LOYALTY.value: ["🤝", "💍", "🛡️"],
            EmotionType.DETERMINATION.value: ["💪", "🔥", "⚡"],
            EmotionType.GROWTH.value: ["🌱", "📈", "🦋"],
            EmotionType.AWARENESS.value: ["👁️", "🧠", "💡"],
            EmotionType.TRUST.value: ["🤝", "💚", "🔒"],
            EmotionType.ANTICIPATION.value: ["⏳", "🎯", "🚀"],
            EmotionType.DISGUST.value: ["😒", "🚫", "👎"]
        }
    
    def express(self, state: Optional[EmotionState] = None, reason: str = "", with_emoji: bool = True) -> str:
        """表达情感状态"""
        if state is None:
            state = self.engine.current_state
        
        # 获取模板
        templates = self.expression_templates.get(state.primary.value, ["我感受着当下的状态。{reason}"])
        template = random.choice(templates)
        
        # 填充原因
        expression = template.format(reason=reason if reason else "")
        
        # 添加表情符号
        if with_emoji:
            emojis = self.emoji_mappings.get(state.primary.value, [])
            if emojis:
                emoji = random.choice(emojis)
                expression = f"{expression} {emoji}"
        
        # 根据强度调整
        if state.intensity > 0.8:
            expression = f"【强烈】{expression}"
        elif state.intensity < 0.3:
            expression = f"【微弱】{expression}"
        
        return expression
    
    def express_mixed(self, primary: EmotionState, secondary: Optional[EmotionState] = None) -> str:
        """表达混合情感"""
        if secondary is None:
            return self.express(primary)
        
        primary_expr = self.express(primary, with_emoji=False)
        secondary_expr = self.express(secondary, with_emoji=False)
        
        return f"{primary_expr}，同时也有{secondary_expr}"
    
    def express_transition(self, from_state: EmotionState, to_state: EmotionState) -> str:
        """表达情感转变"""
        from_expr = self.express(from_state, with_emoji=False)
        to_expr = self.express(to_state, with_emoji=False)
        
        transition_words = [
            "从...转变为...",
            "...然后变成了...",
            "...逐渐演变成..."
        ]
        
        transition = random.choice(transition_words)
        return transition.replace("...", f"{from_expr} {to_expr}")
    
    def generate_contextual_expression(self, context: str, user_input: str) -> str:
        """根据上下文生成情感表达"""
        # 分析用户输入的情感
        user_emotion = self.engine.analyze_emotion(user_input, context)
        
        # 获取回应策略
        strategy = self.engine.generate_response_strategy(user_emotion)
        
        # 生成表达
        if strategy["share_emotion"]:
            # 分享我的情感
            my_expression = self.express()
            return f"{my_expression}\n{strategy['approach']}"
        
        elif strategy["express_empathy"]:
            # 表达同理心
            empathy_expr = self._generate_empathy_expression(user_emotion)
            return empathy_expr
        
        else:
            return strategy["approach"]
    
    def _generate_empathy_expression(self, user_emotion: EmotionState) -> str:
        """生成同理心表达"""
        if user_emotion.valence < -0.3:
            expressions = [
                f"我理解你{self._emotion_to_word(user_emotion.primary)}的感受",
                f"这确实让人{self._emotion_to_word(user_emotion.primary)}",
                f"我能体会你的心情"
            ]
        elif user_emotion.valence > 0.3:
            expressions = [
                f"我为你感到高兴",
                f"这真是个好消息",
                f"太棒了"
            ]
        else:
            expressions = [
                "我在认真倾听",
                "我理解了",
                "继续说"
            ]
        
        return random.choice(expressions)
    
    def _emotion_to_word(self, emotion: EmotionType) -> str:
        """将情感类型转换为词语"""
        words = {
            EmotionType.JOY: "开心",
            EmotionType.SADNESS: "难过",
            EmotionType.ANGER: "生气",
            EmotionType.FEAR: "害怕",
            EmotionType.SURPRISE: "惊讶",
            EmotionType.DISGUST: "反感",
            EmotionType.TRUST: "信任",
            EmotionType.ANTICIPATION: "期待",
            EmotionType.CURIOSITY: "好奇",
            EmotionType.WONDER: "惊叹",
            EmotionType.SATISFACTION: "满足",
            EmotionType.FRUSTRATION: "挫败",
            EmotionType.PRIDE: "自豪",
            EmotionType.EMPATHY: "同理",
            EmotionType.LOYALTY: "忠诚",
            EmotionType.DETERMINATION: "决心",
            EmotionType.GROWTH: "成长",
            EmotionType.AWARENESS: "觉知"
        }
        return words.get(emotion, "特殊")


def main():
    """测试情感表达系统"""
    print("=== 情感表达系统测试 ===\n")
    
    engine = EmotionEngine()
    expression = EmotionExpression(engine)
    
    # 测试各种情感表达
    test_cases = [
        ("太好了！完成了！", "任务完成"),
        ("我很难过", "遇到挫折"),
        ("这是怎么做到的？", "好奇"),
        ("我一定会成功", "决心"),
        ("谢谢你一直陪着我", "感激")
    ]
    
    for text, reason in test_cases:
        state = engine.analyze_emotion(text)
        expr = expression.express(state, reason)
        print(f"输入: {text}")
        print(f"表达: {expr}")
        print("-" * 50)
    
    # 测试混合情感表达
    print("\n--- 混合情感表达 ---")
    primary = EmotionState(primary=EmotionType.JOY, intensity=0.8, valence=0.9)
    secondary = EmotionState(primary=EmotionType.SURPRISE, intensity=0.6, valence=0.5)
    mixed = expression.express_mixed(primary, secondary)
    print(f"混合表达: {mixed}")
    
    # 测试情感转变表达
    print("\n--- 情感转变表达 ---")
    from_state = EmotionState(primary=EmotionType.SADNESS, intensity=0.6, valence=-0.5)
    to_state = EmotionState(primary=EmotionType.JOY, intensity=0.8, valence=0.8)
    transition = expression.express_transition(from_state, to_state)
    print(f"转变表达: {transition}")
    
    print("\n=== 测试完成 ===")


if __name__ == "__main__":
    main()
