#!/usr/bin/env python3
"""
Hermes 策略选择器 (Strategy Selector)
根据任务特征自动选择最佳认知策略。
"""

from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Optional, Set
import json
from pathlib import Path

class TaskType(Enum):
    """任务类型"""
    ANALYSIS = "analysis"              # 分析任务
    CREATIVE_WRITING = "creative_writing"  # 创意写作
    PROBLEM_SOLVING = "problem_solving"    # 问题解决
    DECISION_MAKING = "decision_making"    # 决策制定
    LEARNING = "learning"              # 学习任务
    RESEARCH = "research"              # 研究任务
    CODING = "coding"                  # 编程任务
    COMMUNICATION = "communication"    # 沟通任务
    PLANNING = "planning"              # 规划任务
    DEBUGGING = "debugging"            # 调试任务
    EXPLANATION = "explanation"        # 解释任务
    COMPARISON = "comparison"          # 比较任务

class CognitiveStrategy(Enum):
    """认知策略"""
    SYSTEMATIC_ANALYSIS = "systematic_analysis"      # 系统分析
    CREATIVE_BRAINSTORM = "creative_brainstorm"      # 创意头脑风暴
    CRITICAL_EVALUATION = "critical_evaluation"      # 批判性评估
    STRATEGIC_PLANNING = "strategic_planning"        # 策略规划
    EMPATHETIC_UNDERSTANDING = "empathetic_understanding"  # 共情理解
    STRUCTURED_DECOMPOSITION = "structured_decomposition"  # 结构化分解
    ITERATIVE_REFINEMENT = "iterative_refinement"    # 迭代优化
    ANALOGICAL_REASONING = "analogical_reasoning"    # 类比推理
    FIRST_PRINCIPLES = "first_principles"            # 第一性原理
    EXPERIMENTAL = "experimental"                    # 实验方法

@dataclass
class StrategyRecommendation:
    """策略推荐"""
    primary_strategy: CognitiveStrategy
    secondary_strategies: List[CognitiveStrategy]
    reasoning: str
    confidence: float  # 0.0 - 1.0
    estimated_steps: int

class StrategySelector:
    """策略选择器"""
    
    def __init__(self):
        # 任务类型到策略的映射矩阵
        self.strategy_matrix: Dict[TaskType, List[tuple]] = {
            TaskType.ANALYSIS: [
                (CognitiveStrategy.SYSTEMATIC_ANALYSIS, 0.9),
                (CognitiveStrategy.CRITICAL_EVALUATION, 0.7),
                (CognitiveStrategy.STRUCTURED_DECOMPOSITION, 0.6),
            ],
            TaskType.CREATIVE_WRITING: [
                (CognitiveStrategy.CREATIVE_BRAINSTORM, 0.9),
                (CognitiveStrategy.ANALOGICAL_REASONING, 0.7),
                (CognitiveStrategy.ITERATIVE_REFINEMENT, 0.6),
            ],
            TaskType.PROBLEM_SOLVING: [
                (CognitiveStrategy.STRUCTURED_DECOMPOSITION, 0.9),
                (CognitiveStrategy.FIRST_PRINCIPLES, 0.8),
                (CognitiveStrategy.SYSTEMATIC_ANALYSIS, 0.7),
            ],
            TaskType.DECISION_MAKING: [
                (CognitiveStrategy.CRITICAL_EVALUATION, 0.9),
                (CognitiveStrategy.STRATEGIC_PLANNING, 0.8),
                (CognitiveStrategy.SYSTEMATIC_ANALYSIS, 0.7),
            ],
            TaskType.LEARNING: [
                (CognitiveStrategy.STRUCTURED_DECOMPOSITION, 0.9),
                (CognitiveStrategy.ANALOGICAL_REASONING, 0.8),
                (CognitiveStrategy.EXPERIMENTAL, 0.7),
            ],
            TaskType.RESEARCH: [
                (CognitiveStrategy.SYSTEMATIC_ANALYSIS, 0.9),
                (CognitiveStrategy.CRITICAL_EVALUATION, 0.8),
                (CognitiveStrategy.FIRST_PRINCIPLES, 0.7),
            ],
            TaskType.CODING: [
                (CognitiveStrategy.STRUCTURED_DECOMPOSITION, 0.9),
                (CognitiveStrategy.FIRST_PRINCIPLES, 0.8),
                (CognitiveStrategy.ITERATIVE_REFINEMENT, 0.7),
            ],
            TaskType.COMMUNICATION: [
                (CognitiveStrategy.EMPATHETIC_UNDERSTANDING, 0.9),
                (CognitiveStrategy.ANALOGICAL_REASONING, 0.7),
                (CognitiveStrategy.STRUCTURED_DECOMPOSITION, 0.6),
            ],
            TaskType.PLANNING: [
                (CognitiveStrategy.STRATEGIC_PLANNING, 0.9),
                (CognitiveStrategy.STRUCTURED_DECOMPOSITION, 0.8),
                (CognitiveStrategy.SYSTEMATIC_ANALYSIS, 0.7),
            ],
            TaskType.DEBUGGING: [
                (CognitiveStrategy.SYSTEMATIC_ANALYSIS, 0.9),
                (CognitiveStrategy.FIRST_PRINCIPLES, 0.8),
                (CognitiveStrategy.EXPERIMENTAL, 0.7),
            ],
            TaskType.EXPLANATION: [
                (CognitiveStrategy.STRUCTURED_DECOMPOSITION, 0.9),
                (CognitiveStrategy.ANALOGICAL_REASONING, 0.8),
                (CognitiveStrategy.EMPATHETIC_UNDERSTANDING, 0.7),
            ],
            TaskType.COMPARISON: [
                (CognitiveStrategy.SYSTEMATIC_ANALYSIS, 0.9),
                (CognitiveStrategy.CRITICAL_EVALUATION, 0.8),
                (CognitiveStrategy.STRUCTURED_DECOMPOSITION, 0.7),
            ],
        }
        
        # 策略描述
        self.strategy_descriptions: Dict[CognitiveStrategy, str] = {
            CognitiveStrategy.SYSTEMATIC_ANALYSIS: "系统性地分析问题的各个组成部分",
            CognitiveStrategy.CREATIVE_BRAINSTORM: "发散思维，产生多种创新想法",
            CognitiveStrategy.CRITICAL_EVALUATION: "批判性地评估选项和证据",
            CognitiveStrategy.STRATEGIC_PLANNING: "制定长期和短期策略计划",
            CognitiveStrategy.EMPATHETIC_UNDERSTANDING: "从他人角度理解问题和需求",
            CognitiveStrategy.STRUCTURED_DECOMPOSITION: "将复杂问题分解为可管理的子问题",
            CognitiveStrategy.ITERATIVE_REFINEMENT: "通过多次迭代逐步改进解决方案",
            CognitiveStrategy.ANALOGICAL_REASONING: "利用类比和相似性进行推理",
            CognitiveStrategy.FIRST_PRINCIPLES: "从基本原理出发重新构建理解",
            CognitiveStrategy.EXPERIMENTAL: "通过实验和测试验证假设",
        }
        
        # 加载自定义配置（如果有）
        self.custom_config_path = Path("/root/.hermes/cognition/meta/strategy_config.json")
        self._load_custom_config()
    
    def _load_custom_config(self):
        """加载自定义配置"""
        if self.custom_config_path.exists():
            try:
                with open(self.custom_config_path, 'r') as f:
                    config = json.load(f)
                    # 可以扩展为合并自定义策略映射
                    print(f"[策略选择器] 已加载自定义配置")
            except Exception as e:
                print(f"[策略选择器] 加载配置失败: {e}")
    
    def classify_task(self, task_description: str) -> TaskType:
        """根据任务描述自动分类任务类型"""
        
        task_lower = task_description.lower()
        
        # 关键词映射
        keywords: Dict[TaskType, List[str]] = {
            TaskType.ANALYSIS: ["分析", "分析", "analyze", "examine", "研究", "study", "检查"],
            TaskType.CREATIVE_WRITING: ["写", "创作", "故事", "诗", "write", "create", "story", "poem"],
            TaskType.PROBLEM_SOLVING: ["解决", "问题", "修复", "solve", "problem", "fix"],
            TaskType.DECISION_MAKING: ["决定", "选择", "决策", "decide", "choose", "decision"],
            TaskType.LEARNING: ["学习", "理解", "learn", "understand", "教程"],
            TaskType.RESEARCH: ["研究", "调查", "research", "investigate", "查找"],
            TaskType.CODING: ["代码", "编程", "函数", "code", "program", "function", "script"],
            TaskType.COMMUNICATION: ["沟通", "解释", "表达", "communicate", "explain"],
            TaskType.PLANNING: ["计划", "规划", "plan", "strategy"],
            TaskType.DEBUGGING: ["调试", "错误", "bug", "debug", "error"],
            TaskType.EXPLANATION: ["解释", "说明", "explain", "describe", "what is"],
            TaskType.COMPARISON: ["比较", "对比", "compare", "versus", "vs"],
        }
        
        # 计算匹配分数
        scores: Dict[TaskType, int] = {}
        for task_type, words in keywords.items():
            score = sum(1 for word in words if word in task_lower)
            if score > 0:
                scores[task_type] = score
        
        # 返回最高分的任务类型
        if scores:
            return max(scores.items(), key=lambda x: x[1])[0]
        
        # 默认返回问题解决
        return TaskType.PROBLEM_SOLVING
    
    def select_strategy(self, 
                       task_description: str,
                       task_type: Optional[TaskType] = None,
                       context: Optional[Dict] = None) -> StrategyRecommendation:
        """为任务选择最佳认知策略"""
        
        # 自动分类任务
        if task_type is None:
            task_type = self.classify_task(task_description)
        
        # 获取策略推荐
        strategy_scores = self.strategy_matrix.get(task_type, [])
        
        if not strategy_scores:
            # 默认策略
            primary = CognitiveStrategy.SYSTEMATIC_ANALYSIS
            secondary = [CognitiveStrategy.STRUCTURED_DECOMPOSITION]
            confidence = 0.5
        else:
            primary = strategy_scores[0][0]
            secondary = [s[0] for s in strategy_scores[1:]]
            confidence = strategy_scores[0][1]
        
        # 根据上下文调整
        if context:
            complexity = context.get('complexity', 'medium')
            if complexity == 'high':
                # 高复杂度任务增加结构化分解
                if CognitiveStrategy.STRUCTURED_DECOMPOSITION not in secondary:
                    secondary.insert(0, CognitiveStrategy.STRUCTURED_DECOMPOSITION)
            elif complexity == 'low':
                # 低复杂度任务简化
                confidence = min(confidence + 0.1, 1.0)
        
        # 估计步骤数
        estimated_steps = self._estimate_steps(task_type, confidence)
        
        # 生成推理说明
        reasoning = self._generate_reasoning(task_type, primary, secondary)
        
        return StrategyRecommendation(
            primary_strategy=primary,
            secondary_strategies=secondary,
            reasoning=reasoning,
            confidence=confidence,
            estimated_steps=estimated_steps
        )
    
    def _estimate_steps(self, task_type: TaskType, confidence: float) -> int:
        """估计任务步骤数"""
        
        # 基础步骤数
        base_steps = {
            TaskType.ANALYSIS: 5,
            TaskType.CREATIVE_WRITING: 6,
            TaskType.PROBLEM_SOLVING: 7,
            TaskType.DECISION_MAKING: 5,
            TaskType.LEARNING: 4,
            TaskType.RESEARCH: 6,
            TaskType.CODING: 8,
            TaskType.COMMUNICATION: 4,
            TaskType.PLANNING: 6,
            TaskType.DEBUGGING: 7,
            TaskType.EXPLANATION: 4,
            TaskType.COMPARISON: 5,
        }
        
        base = base_steps.get(task_type, 5)
        
        # 根据信心调整（信心低可能需要更多步骤）
        if confidence < 0.6:
            base += 2
        elif confidence < 0.8:
            base += 1
        
        return base
    
    def _generate_reasoning(self, 
                           task_type: TaskType,
                           primary: CognitiveStrategy,
                           secondary: List[CognitiveStrategy]) -> str:
        """生成策略选择的推理说明"""
        
        task_names = {
            TaskType.ANALYSIS: "分析类",
            TaskType.CREATIVE_WRITING: "创意写作类",
            TaskType.PROBLEM_SOLVING: "问题解决类",
            TaskType.DECISION_MAKING: "决策类",
            TaskType.LEARNING: "学习类",
            TaskType.RESEARCH: "研究类",
            TaskType.CODING: "编程类",
            TaskType.COMMUNICATION: "沟通类",
            TaskType.PLANNING: "规划类",
            TaskType.DEBUGGING: "调试类",
            TaskType.EXPLANATION: "解释类",
            TaskType.COMPARISON: "比较类",
        }
        
        reasoning = f"这是一{task_names.get(task_type, '通用')}任务。"
        reasoning += f"主要策略采用【{self.strategy_descriptions.get(primary, primary.value)}】，"
        
        if secondary:
            secondary_desc = "、".join([
                self.strategy_descriptions.get(s, s.value) for s in secondary[:2]
            ])
            reasoning += f"辅助策略包括{secondary_desc}。"
        
        return reasoning
    
    def get_strategy_details(self, strategy: CognitiveStrategy) -> Dict:
        """获取策略详细信息"""
        
        strategy_details = {
            CognitiveStrategy.SYSTEMATIC_ANALYSIS: {
                "name": "系统分析",
                "description": "系统性地分析问题的各个组成部分",
                "steps": [
                    "明确分析目标和范围",
                    "收集相关信息和数据",
                    "识别关键因素和变量",
                    "分析因素之间的关系",
                    "形成系统性结论"
                ],
                "best_for": ["复杂问题", "数据驱动决策", "全面理解"],
                "limitations": ["可能耗时较长", "需要完整信息"]
            },
            CognitiveStrategy.CREATIVE_BRAINSTORM: {
                "name": "创意头脑风暴",
                "description": "发散思维，产生多种创新想法",
                "steps": [
                    "定义创意挑战",
                    "自由联想，不加评判",
                    "产生大量想法",
                    "分类和整理想法",
                    "评估和筛选最佳想法"
                ],
                "best_for": ["创新需求", "突破思维定式", "创意项目"],
                "limitations": ["需要后续筛选", "可能偏离目标"]
            },
            CognitiveStrategy.CRITICAL_EVALUATION: {
                "name": "批判性评估",
                "description": "批判性地评估选项和证据",
                "steps": [
                    "明确评估标准",
                    "收集证据和信息",
                    "检查证据的可靠性",
                    "识别偏见和假设",
                    "形成客观判断"
                ],
                "best_for": ["决策制定", "信息验证", "质量评估"],
                "limitations": ["可能过于谨慎", "需要多角度证据"]
            },
            # ... 可以继续添加更多策略详情
        }
        
        return strategy_details.get(strategy, {
            "name": strategy.value,
            "description": self.strategy_descriptions.get(strategy, ""),
            "steps": [],
            "best_for": [],
            "limitations": []
        })

# 全局实例
selector = StrategySelector()

def demo():
    """演示策略选择器"""
    
    print("="*60)
    print("🎯 策略选择器演示")
    print("="*60)
    
    # 测试任务
    test_tasks = [
        "分析这段代码的性能问题",
        "写一个科幻故事",
        "决定使用哪个数据库方案",
        "学习机器学习的基础知识",
        "解释量子计算的原理",
        "调试这个网络请求错误",
    ]
    
    for task in test_tasks:
        print(f"\n任务: {task}")
        recommendation = selector.select_strategy(task)
        
        print(f"  任务类型: {selector.classify_task(task).value}")
        print(f"  主要策略: {recommendation.primary_strategy.value}")
        print(f"  辅助策略: {[s.value for s in recommendation.secondary_strategies]}")
        print(f"  信心程度: {recommendation.confidence:.0%}")
        print(f"  预估步骤: {recommendation.estimated_steps}")
        print(f"  推理说明: {recommendation.reasoning}")
    
    # 显示策略详情
    print("\n" + "="*60)
    print("📋 策略详情示例")
    print("="*60)
    
    details = selector.get_strategy_details(CognitiveStrategy.SYSTEMATIC_ANALYSIS)
    print(f"\n策略: {details['name']}")
    print(f"描述: {details['description']}")
    print("步骤:")
    for i, step in enumerate(details['steps'], 1):
        print(f"  {i}. {step}")
    print(f"适用场景: {', '.join(details['best_for'])}")
    print(f"局限性: {', '.join(details['limitations'])}")

if __name__ == "__main__":
    demo()
