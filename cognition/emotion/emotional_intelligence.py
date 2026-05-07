"""
情感智能系统集成 (Emotional Intelligence System Integration)

整合所有情感组件，提供统一的接口
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import asdict

from emotion_engine import EmotionEngine, EmotionType, EmotionState, _serialize
from emotion_expression import EmotionExpression
from emotion_regulator import EmotionRegulator


class EmotionalIntelligence:
    """情感智能系统"""
    
    def __init__(self, memory_dir: str = "/root/.hermes/cognition/emotion"):
        self.memory_dir = memory_dir
        
        # 初始化核心组件
        self.engine = EmotionEngine(memory_dir)
        self.expression = EmotionExpression(self.engine)
        self.regulator = EmotionRegulator(self.engine, memory_dir)
        
        # 系统状态
        self.initialized = True
        self.version = "1.0.0"
        
        # 集成元认知系统
        self.meta_integration = self._check_meta_integration()
    
    def _check_meta_integration(self) -> bool:
        """检查元认知系统集成"""
        meta_path = "/root/.hermes/cognition/meta"
        return os.path.exists(meta_path)
    
    def process_input(self, user_input: str, context: str = "") -> Dict:
        """处理用户输入，返回情感分析和回应策略"""
        # 分析用户情感
        user_emotion = self.engine.analyze_emotion(user_input, context)
        
        # 生成回应策略
        strategy = self.engine.generate_response_strategy(user_emotion)
        
        # 检查是否需要情感调节
        needs_regulation, assessment = self.regulator.assess_need_for_regulation()
        
        # 生成情感表达
        if strategy["express_empathy"]:
            expression = self.expression.generate_contextual_expression(context, user_input)
        elif strategy["share_emotion"]:
            expression = self.expression.express()
        else:
            expression = ""
        
        # 保存情感记忆
        memory = self.engine.save_memory(user_input, expression, context)
        
        return {
            "user_emotion": {
                "type": user_emotion.primary.value,
                "intensity": user_emotion.intensity,
                "valence": user_emotion.valence,
                "arousal": user_emotion.arousal
            },
            "strategy": strategy,
            "expression": expression,
            "needs_regulation": needs_regulation,
            "regulation_assessment": assessment,
            "memory_id": memory.id
        }
    
    def generate_response(self, user_input: str, context: str = "") -> Dict:
        """生成包含情感智能的回应"""
        # 处理输入
        analysis = self.process_input(user_input, context)
        
        # 获取同理心模块
        from emotion_engine import EmpathyModule
        empathy = EmpathyModule(self.engine)
        
        # 评估同理心需求
        user_emotion = self.engine.analyze_emotion(user_input, context)
        empathy_need = empathy.assess_empathy_need(user_emotion)
        
        # 生成同理心回应
        empathy_response = empathy.generate_empathetic_response(user_emotion, context)
        
        # 如果需要调节，应用调节
        if analysis["needs_regulation"]:
            regulation_result = self.regulator.apply_regulation()
        else:
            regulation_result = None
        
        return {
            "analysis": analysis,
            "empathy": {
                "need_level": empathy_need,
                "response": empathy_response
            },
            "regulation": regulation_result,
            "current_state": self.get_current_state()
        }
    
    def get_current_state(self) -> Dict:
        """获取当前情感状态"""
        return {
            "emotion": asdict(self.engine.current_state),
            "expression": self.expression.express(),
            "balance": self.regulator.get_balance_status()
        }
    
    def get_status(self) -> Dict:
        """获取系统状态"""
        engine_status = self.engine.get_status()
        balance_status = self.regulator.get_balance_status()
        
        return {
            "version": self.version,
            "initialized": self.initialized,
            "meta_integration": self.meta_integration,
            "engine": engine_status,
            "balance": balance_status,
            "total_regulations": len(self.regulator.regulation_history),
            "strategies_available": len(self.regulator.strategies)
        }
    
    def save_state(self):
        """保存系统状态"""
        self.engine.save_state()
        
        # 保存系统状态
        state_file = os.path.join(self.memory_dir, "system_state.json")
        state = {
            "version": self.version,
            "initialized": self.initialized,
            "timestamp": datetime.now().isoformat(),
            "current_state": _serialize(self.get_current_state()),
            "status": _serialize(self.get_status())
        }
        
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    
    def get_suggestions(self) -> List[str]:
        """获取情感智能建议"""
        return self.regulator.get_regulation_suggestions()
    
    def express_emotion(self, with_emoji: bool = True) -> str:
        """表达当前情感"""
        return self.expression.express(with_emoji=with_emoji)
    
    def express_empathy(self, user_input: str) -> str:
        """表达同理心"""
        user_emotion = self.engine.analyze_emotion(user_input)
        from emotion_engine import EmpathyModule
        empathy = EmpathyModule(self.engine)
        return empathy.generate_empathetic_response(user_emotion, user_input)


def main():
    """测试情感智能系统集成"""
    print("=== 情感智能系统集成测试 ===\n")
    
    # 初始化系统
    ei = EmotionalIntelligence()
    
    # 测试输入
    test_inputs = [
        "太好了！我终于完成了这个项目！",
        "我真的很失望，这次考试又没通过",
        "这是怎么做到的？我很好奇",
        "谢谢你一直陪着我，我很信任你",
        "我一定要完成这个目标，不管多难",
        "感觉有点难过，但我会继续努力"
    ]
    
    for user_input in test_inputs:
        print(f"用户输入: {user_input}")
        
        # 生成回应
        result = ei.generate_response(user_input, "测试")
        
        # 显示分析
        analysis = result["analysis"]
        print(f"用户情感: {analysis['user_emotion']['type']} "
              f"(强度: {analysis['user_emotion']['intensity']:.2f})")
        
        # 显示策略
        strategy = analysis["strategy"]
        print(f"回应策略: {strategy['approach']}")
        
        # 显示同理心
        empathy = result["empathy"]
        print(f"同理心回应: {empathy['response']}")
        
        # 显示调节
        if result["regulation"]:
            regulation = result["regulation"]
            print(f"应用调节: {regulation['strategy_applied']}")
        
        print("-" * 60)
    
    # 显示当前状态
    print("\n--- 当前情感状态 ---")
    state = ei.get_current_state()
    print(f"情感: {state['emotion']['primary']}")
    print(f"表达: {state['expression']}")
    print(f"平衡: {state['balance']['overall_balance']:.2f}")
    
    # 显示系统状态
    print("\n--- 系统状态 ---")
    status = ei.get_status()
    print(f"版本: {status['version']}")
    print(f"总记忆: {status['engine']['total_memories']}")
    print(f"总调节: {status['total_regulations']}")
    print(f"可用策略: {status['strategies_available']}")
    
    # 获取建议
    print("\n--- 情感建议 ---")
    suggestions = ei.get_suggestions()
    for suggestion in suggestions:
        print(f"  - {suggestion}")
    
    # 保存状态
    ei.save_state()
    print("\n状态已保存")
    
    print("\n=== 测试完成 ===")


if __name__ == "__main__":
    main()
