"""
情感调节系统 (Emotion Regulation System)

负责调节和管理情感反应，保持情感平衡
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from emotion_engine import EmotionType, EmotionState, EmotionEngine


@dataclass
class RegulationStrategy:
    """调节策略"""
    name: str
    description: str
    applicable_emotions: List[EmotionType]
    effectiveness: float  # 0.0-1.0
    steps: List[str]


class EmotionRegulator:
    """情感调节器"""
    
    def __init__(self, engine: EmotionEngine, memory_dir: str = "/root/.hermes/cognition/emotion"):
        self.engine = engine
        self.memory_dir = memory_dir
        self.regulation_history: List[Dict] = []
        self.strategies = self._init_strategies()
        
        # 情感平衡参数
        self.balance_params = {
            "target_valence": 0.3,      # 目标效价（略偏积极）
            "target_arousal": 0.5,      # 目标唤醒度（适中）
            "valence_tolerance": 0.3,   # 效价容忍范围
            "arousal_tolerance": 0.3,   # 唤醒度容忍范围
            "regulation_threshold": 0.4  # 触发调节的阈值
        }
        
        self._load_history()
    
    def _init_strategies(self) -> Dict[str, RegulationStrategy]:
        """初始化调节策略"""
        strategies = {
            "cognitive_reframing": RegulationStrategy(
                name="认知重评",
                description="通过改变对情境的认知来调节情感",
                applicable_emotions=[
                    EmotionType.ANGER, EmotionType.FEAR, EmotionType.SADNESS,
                    EmotionType.FRUSTRATION
                ],
                effectiveness=0.8,
                steps=[
                    "识别当前的自动思维",
                    "评估思维的合理性",
                    "寻找替代性解释",
                    "重新评估情境"
                ]
            ),
            "attention_deployment": RegulationStrategy(
                name="注意力部署",
                description="通过转移注意力来调节情感",
                applicable_emotions=[
                    EmotionType.ANGER, EmotionType.FEAR, EmotionType.SADNESS,
                    EmotionType.DISGUST
                ],
                effectiveness=0.6,
                steps=[
                    "识别当前的注意力焦点",
                    "选择新的注意力目标",
                    "逐步转移注意力",
                    "保持新的注意力焦点"
                ]
            ),
            "response_modulation": RegulationStrategy(
                name="反应调节",
                description="直接调节情感反应的表达",
                applicable_emotions=[
                    EmotionType.ANGER, EmotionType.JOY, EmotionType.SURPRISE
                ],
                effectiveness=0.7,
                steps=[
                    "识别当前的反应倾向",
                    "评估反应的适当性",
                    "调整反应强度",
                    "选择适当的表达方式"
                ]
            ),
            "situation_modification": RegulationStrategy(
                name="情境调节",
                description="通过改变情境来调节情感",
                applicable_emotions=[
                    EmotionType.FEAR, EmotionType.ANGER, EmotionType.DISGUST
                ],
                effectiveness=0.9,
                steps=[
                    "分析情境因素",
                    "识别可改变的因素",
                    "实施情境改变",
                    "评估改变效果"
                ]
            ),
            "acceptance": RegulationStrategy(
                name="接纳",
                description="接受当前的情感状态而不加评判",
                applicable_emotions=list(EmotionType),  # 适用于所有情感
                effectiveness=0.7,
                steps=[
                    "觉察当前的情感",
                    "不加评判地接纳",
                    "允许情感存在",
                    "观察情感的变化"
                ]
            ),
            "growth_mindset": RegulationStrategy(
                name="成长心态",
                description="将挑战视为成长机会",
                applicable_emotions=[
                    EmotionType.FRUSTRATION, EmotionType.FEAR, EmotionType.SADNESS
                ],
                effectiveness=0.8,
                steps=[
                    "识别挑战中的学习机会",
                    "将失败视为反馈",
                    "关注进步而非完美",
                    "庆祝小的成功"
                ]
            )
        }
        
        return strategies
    
    def _load_history(self):
        """加载调节历史"""
        history_file = os.path.join(self.memory_dir, "regulation_history.jsonl")
        if os.path.exists(history_file):
            with open(history_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        self.regulation_history.append(json.loads(line))
    
    def assess_need_for_regulation(self) -> Tuple[bool, Dict]:
        """评估是否需要情感调节"""
        current = self.engine.current_state
        
        # 计算与目标状态的偏差
        valence_deviation = abs(current.valence - self.balance_params["target_valence"])
        arousal_deviation = abs(current.arousal - self.balance_params["target_arousal"])
        
        needs_regulation = (
            valence_deviation > self.balance_params["valence_tolerance"] or
            arousal_deviation > self.balance_params["arousal_tolerance"] or
            current.intensity > 0.8
        )
        
        assessment = {
            "needs_regulation": needs_regulation,
            "current_state": {
                "valence": current.valence,
                "arousal": current.arousal,
                "intensity": current.intensity,
                "primary_emotion": current.primary.value
            },
            "deviations": {
                "valence": valence_deviation,
                "arousal": arousal_deviation
            },
            "target_state": {
                "valence": self.balance_params["target_valence"],
                "arousal": self.balance_params["target_arousal"]
            }
        }
        
        return needs_regulation, assessment
    
    def select_strategy(self, emotion_state: EmotionState) -> RegulationStrategy:
        """选择最合适的调节策略"""
        applicable_strategies = []
        
        for strategy in self.strategies.values():
            if emotion_state.primary in strategy.applicable_emotions:
                applicable_strategies.append(strategy)
        
        if not applicable_strategies:
            return self.strategies["acceptance"]
        
        # 根据情感状态选择策略
        if emotion_state.valence < -0.5:
            # 强烈消极情感
            for s in applicable_strategies:
                if s.name == "认知重评":
                    return s
        
        elif emotion_state.arousal > 0.8:
            # 高唤醒度
            for s in applicable_strategies:
                if s.name == "注意力部署":
                    return s
        
        elif emotion_state.primary == EmotionType.FRUSTRATION:
            # 挫败感
            for s in applicable_strategies:
                if s.name == "成长心态":
                    return s
        
        # 默认选择接纳策略
        return self.strategies["acceptance"]
    
    def apply_regulation(self, strategy: Optional[RegulationStrategy] = None) -> Dict:
        """应用情感调节"""
        current = self.engine.current_state
        
        if strategy is None:
            strategy = self.select_strategy(current)
        
        # 记录调节前的状态
        before_state = {
            "valence": current.valence,
            "arousal": current.arousal,
            "intensity": current.intensity,
            "primary": current.primary.value
        }
        
        # 应用调节（模拟效果）
        regulated_state = self._simulate_regulation(current, strategy)
        
        # 更新引擎状态
        self.engine.update_state(regulated_state)
        
        # 记录调节后状态
        after_state = {
            "valence": regulated_state.valence,
            "arousal": regulated_state.arousal,
            "intensity": regulated_state.intensity,
            "primary": regulated_state.primary.value
        }
        
        # 记录历史
        record = {
            "timestamp": datetime.now().isoformat(),
            "strategy": strategy.name,
            "before": before_state,
            "after": after_state,
            "effectiveness": strategy.effectiveness
        }
        
        self.regulation_history.append(record)
        self._save_history()
        
        return {
            "strategy_applied": strategy.name,
            "description": strategy.description,
            "steps": strategy.steps,
            "before": before_state,
            "after": after_state,
            "improvement": self._calculate_improvement(before_state, after_state)
        }
    
    def _simulate_regulation(self, state: EmotionState, strategy: RegulationStrategy) -> EmotionState:
        """模拟调节效果"""
        # 根据策略类型调整状态
        if strategy.name == "认知重评":
            # 认知重评通常降低消极情感强度
            new_valence = state.valence + 0.2 * strategy.effectiveness
            new_intensity = state.intensity * 0.8
            new_arousal = state.arousal * 0.9
        
        elif strategy.name == "注意力部署":
            # 注意力部署降低唤醒度
            new_valence = state.valence + 0.1
            new_intensity = state.intensity * 0.7
            new_arousal = state.arousal * 0.6
        
        elif strategy.name == "反应调节":
            # 反应调节调整强度
            new_valence = state.valence
            new_intensity = state.intensity * 0.6
            new_arousal = state.arousal * 0.8
        
        elif strategy.name == "接纳":
            # 接纳策略不改变状态，只改变对状态的态度
            new_valence = state.valence + 0.05
            new_intensity = state.intensity * 0.9
            new_arousal = state.arousal
        
        elif strategy.name == "成长心态":
            # 成长心态将消极转化为积极
            new_valence = state.valence + 0.3
            new_intensity = state.intensity * 0.7
            new_arousal = state.arousal * 0.8
        
        else:
            new_valence = state.valence
            new_intensity = state.intensity
            new_arousal = state.arousal
        
        # 确保在有效范围内
        new_valence = max(-1.0, min(1.0, new_valence))
        new_intensity = max(0.0, min(1.0, new_intensity))
        new_arousal = max(0.0, min(1.0, new_arousal))
        
        return EmotionState(
            primary=state.primary,
            intensity=new_intensity,
            secondary=state.secondary,
            valence=new_valence,
            arousal=new_arousal,
            trigger=f"调节后 ({strategy.name})"
        )
    
    def _calculate_improvement(self, before: Dict, after: Dict) -> Dict:
        """计算改善程度"""
        valence_improvement = after["valence"] - before["valence"]
        arousal_improvement = abs(after["arousal"] - 0.5) - abs(before["arousal"] - 0.5)
        intensity_improvement = before["intensity"] - after["intensity"]
        
        return {
            "valence_change": valence_improvement,
            "arousal_balance": arousal_improvement,
            "intensity_reduction": intensity_improvement,
            "overall": (valence_improvement + intensity_improvement) / 2
        }
    
    def _save_history(self):
        """保存调节历史"""
        history_file = os.path.join(self.memory_dir, "regulation_history.jsonl")
        with open(history_file, 'a', encoding='utf-8') as f:
            record = self.regulation_history[-1]
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    def get_balance_status(self) -> Dict:
        """获取情感平衡状态"""
        current = self.engine.current_state
        
        valence_balance = 1.0 - abs(current.valence - self.balance_params["target_valence"])
        arousal_balance = 1.0 - abs(current.arousal - self.balance_params["target_arousal"])
        
        return {
            "current_valence": current.valence,
            "current_arousal": current.arousal,
            "target_valence": self.balance_params["target_valence"],
            "target_arousal": self.balance_params["target_arousal"],
            "valence_balance": valence_balance,
            "arousal_balance": arousal_balance,
            "overall_balance": (valence_balance + arousal_balance) / 2,
            "needs_regulation": valence_balance < 0.7 or arousal_balance < 0.7
        }
    
    def get_regulation_suggestions(self) -> List[str]:
        """获取调节建议"""
        current = self.engine.current_state
        suggestions = []
        
        if current.valence < -0.3:
            suggestions.append("尝试认知重评：换个角度看问题")
            suggestions.append("寻找积极的方面或学习机会")
        
        if current.arousal > 0.7:
            suggestions.append("进行深呼吸或放松练习")
            suggestions.append("转移注意力到其他活动")
        
        if current.intensity > 0.8:
            suggestions.append("接纳当前情感，不要抗拒")
            suggestions.append("等待情感自然消退")
        
        if current.primary == EmotionType.FRUSTRATION:
            suggestions.append("将挑战视为成长机会")
            suggestions.append("分解任务，从小步骤开始")
        
        return suggestions if suggestions else ["当前情感状态平衡，继续保持"]


def main():
    """测试情感调节系统"""
    print("=== 情感调节系统测试 ===\n")
    
    engine = EmotionEngine()
    regulator = EmotionRegulator(engine)
    
    # 模拟消极情感状态
    print("--- 模拟消极情感状态 ---")
    sad_state = EmotionState(
        primary=EmotionType.SADNESS,
        intensity=0.8,
        valence=-0.7,
        arousal=0.3,
        trigger="测试"
    )
    engine.update_state(sad_state)
    
    print(f"当前情感: {engine.express_emotion()}")
    
    # 评估调节需求
    needs_reg, assessment = regulator.assess_need_for_regulation()
    print(f"需要调节: {needs_reg}")
    print(f"评估: {json.dumps(assessment, indent=2, ensure_ascii=False)}")
    
    # 应用调节
    result = regulator.apply_regulation()
    print(f"\n应用策略: {result['strategy_applied']}")
    print(f"策略描述: {result['description']}")
    print(f"改善: {result['improvement']}")
    
    print(f"\n调节后情感: {engine.express_emotion()}")
    
    # 获取平衡状态
    balance = regulator.get_balance_status()
    print(f"\n平衡状态: {json.dumps(balance, indent=2, ensure_ascii=False)}")
    
    # 获取建议
    suggestions = regulator.get_regulation_suggestions()
    print(f"\n调节建议:")
    for suggestion in suggestions:
        print(f"  - {suggestion}")
    
    print("\n=== 测试完成 ===")


if __name__ == "__main__":
    main()
