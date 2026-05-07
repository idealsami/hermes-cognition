#!/usr/bin/env python3
"""
Hermes 元认知系统 (Metacognitive System)
整合认知监控、策略选择、信心评估。
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# 导入子系统
import sys
sys.path.insert(0, '/root/.hermes/cognition/meta')
from cognitive_monitor import (
    CognitiveMonitor, ThoughtType, ConfidenceLevel,
    monitor as cognitive_monitor
)
from strategy_selector import (
    StrategySelector, TaskType, CognitiveStrategy,
    selector as strategy_selector
)
from confidence_assessor import (
    ConfidenceAssessor, ConfidenceAssessment,
    assessor as confidence_assessor
)

@dataclass
class CognitiveTask:
    """认知任务"""
    task_id: str
    description: str
    task_type: TaskType
    strategy_recommendation: Any
    confidence_assessment: ConfidenceAssessment
    start_time: str
    status: str = "in_progress"
    end_time: Optional[str] = None
    outcome: Optional[str] = None

class MetacognitiveSystem:
    """元认知系统主类"""
    
    def __init__(self):
        self.monitor = cognitive_monitor
        self.selector = strategy_selector
        self.assessor = confidence_assessor
        
        self.current_task: Optional[CognitiveTask] = None
        self.task_history: List[CognitiveTask] = []
        
        # 系统状态
        self.system_state = {
            "initialized_at": datetime.now().isoformat(),
            "total_tasks": 0,
            "average_confidence": 0.0,
            "common_strategies": {},
            "learning_progress": []
        }
        
        print("[元认知系统] 初始化完成")
    
    def start_cognitive_task(self, task_description: str) -> Dict[str, Any]:
        """开始新的认知任务"""
        
        task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 1. 分类任务
        task_type = self.selector.classify_task(task_description)
        
        # 2. 获取策略推荐
        strategy_rec = self.selector.select_strategy(task_description, task_type)
        
        # 3. 初始信心评估
        # 使用默认值，后续会根据实际情况调整
        confidence = self.assessor.assess_confidence(
            task_description=task_description,
            knowledge_level=0.5,  # 默认中等
            evidence_quality=0.5,
            reasoning_clarity=0.5,
            consistency=0.5,
            complexity=0.5,
            familiarity=0.5,
            time_pressure=0.5
        )
        
        # 4. 创建任务
        self.current_task = CognitiveTask(
            task_id=task_id,
            description=task_description,
            task_type=task_type,
            strategy_recommendation=strategy_rec,
            confidence_assessment=confidence,
            start_time=datetime.now().isoformat()
        )
        
        # 5. 开始认知监控
        self.monitor.start_session(task_description)
        
        # 打印任务启动报告
        self._print_task_start_report()
        
        return {
            "task_id": task_id,
            "task_type": task_type.value,
            "strategy": strategy_rec.primary_strategy.value,
            "confidence": confidence.overall_confidence,
            "estimated_steps": strategy_rec.estimated_steps
        }
    
    def record_thought(self,
                      thought_type: str,
                      content: str,
                      reasoning: str,
                      confidence_level: int) -> str:
        """记录思维步骤"""
        
        if not self.current_task:
            raise ValueError("没有活跃的认知任务")
        
        # 转换类型
        thought_enum = ThoughtType(thought_type)
        confidence_enum = ConfidenceLevel(confidence_level)
        
        # 记录到监控器
        step_id = self.monitor.record_thought(
            thought_type=thought_enum,
            content=content,
            reasoning=reasoning,
            confidence=confidence_enum,
            tags=[self.current_task.task_type.value]
        )
        
        return step_id
    
    def update_confidence(self, **kwargs):
        """动态更新信心评估"""
        
        if not self.current_task:
            return
        
        # 重新评估信心
        new_assessment = self.assessor.assess_confidence(
            task_description=self.current_task.description,
            **kwargs
        )
        
        self.current_task.confidence_assessment = new_assessment
        
        print(f"[元认知] 信心更新: {new_assessment.overall_confidence:.0%}")
    
    def add_strategy(self, strategy_name: str):
        """记录使用的策略"""
        self.monitor.add_strategy(strategy_name)
    
    def add_lesson(self, lesson: str):
        """记录学习到的经验"""
        self.monitor.add_lesson(lesson)
    
    def end_cognitive_task(self, outcome: str = "completed") -> Dict[str, Any]:
        """结束认知任务"""
        
        if not self.current_task:
            return {}
        
        # 结束监控会话
        session_data = self.monitor.end_session(outcome)
        
        # 更新任务状态
        self.current_task.end_time = datetime.now().isoformat()
        self.current_task.outcome = outcome
        self.current_task.status = "completed"
        
        # 保存到历史
        self.task_history.append(self.current_task)
        
        # 更新系统状态
        self._update_system_state()
        
        # 生成任务总结
        summary = self._generate_task_summary()
        
        # 重置当前任务
        self.current_task = None
        
        return summary
    
    def _print_task_start_report(self):
        """打印任务启动报告"""
        
        if not self.current_task:
            return
        
        task = self.current_task
        strategy = task.strategy_recommendation
        confidence = task.confidence_assessment
        
        print("\n" + "="*60)
        print("🚀 认知任务启动")
        print("="*60)
        print(f"任务ID: {task.task_id}")
        print(f"描述: {task.description[:80]}...")
        print(f"类型: {task.task_type.value}")
        print(f"\n策略推荐:")
        print(f"  主要: {strategy.primary_strategy.value}")
        print(f"  辅助: {[s.value for s in strategy.secondary_strategies]}")
        print(f"  预估步骤: {strategy.estimated_steps}")
        print(f"  推理: {strategy.reasoning}")
        print(f"\n初始信心: {confidence.overall_confidence:.0%}")
        print(f"建议:")
        for s in confidence.suggestions[:3]:
            print(f"  • {s}")
        print("="*60)
    
    def _generate_task_summary(self) -> Dict[str, Any]:
        """生成任务总结"""
        
        if not self.current_task:
            return {}
        
        task = self.current_task
        
        # 计算持续时间
        start = datetime.fromisoformat(task.start_time)
        end = datetime.fromisoformat(task.end_time)
        duration = (end - start).total_seconds()
        
        return {
            "task_id": task.task_id,
            "description": task.description[:200],
            "task_type": task.task_type.value,
            "duration_seconds": duration,
            "outcome": task.outcome,
            "final_confidence": task.confidence_assessment.overall_confidence,
            "strategies_used": self.monitor.current_session.strategies_used if self.monitor.current_session else [],
            "lessons_learned": self.monitor.current_session.lessons_learned if self.monitor.current_session else []
        }
    
    def _update_system_state(self):
        """更新系统状态"""
        
        self.system_state["total_tasks"] = len(self.task_history)
        
        # 计算平均信心
        if self.task_history:
            avg_conf = sum(
                t.confidence_assessment.overall_confidence 
                for t in self.task_history
            ) / len(self.task_history)
            self.system_state["average_confidence"] = round(avg_conf, 3)
        
        # 统计常用策略
        for task in self.task_history:
            strategy = task.strategy_recommendation.primary_strategy.value
            self.system_state["common_strategies"][strategy] = \
                self.system_state["common_strategies"].get(strategy, 0) + 1
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        
        status = {
            "system_state": self.system_state,
            "current_task": None,
            "cognitive_stats": self.monitor.get_cognitive_stats(days=30),
            "confidence_trend": self.assessor.get_confidence_trend()
        }
        
        if self.current_task:
            status["current_task"] = {
                "task_id": self.current_task.task_id,
                "description": self.current_task.description[:100],
                "type": self.current_task.task_type.value,
                "confidence": self.current_task.confidence_assessment.overall_confidence
            }
        
        return status
    
    def save_system_state(self):
        """保存系统状态到文件"""
        
        state_file = Path("/root/.hermes/cognition/meta/system_state.json")
        
        state_data = {
            "saved_at": datetime.now().isoformat(),
            "system_state": self.system_state,
            "task_count": len(self.task_history),
            "recent_tasks": [
                {
                    "task_id": t.task_id,
                    "description": t.description[:100],
                    "outcome": t.outcome,
                    "confidence": t.confidence_assessment.overall_confidence
                }
                for t in self.task_history[-10:]
            ]
        }
        
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state_data, f, ensure_ascii=False, indent=2)
        
        print(f"[元认知] 系统状态已保存: {state_file}")

# 全局实例
metacognitive_system = MetacognitiveSystem()

def demo():
    """演示元认知系统"""
    
    print("="*60)
    print("🧠 元认知系统演示")
    print("="*60)
    
    # 开始任务
    result = metacognitive_system.start_cognitive_task(
        "分析并优化这段代码的性能"
    )
    print(f"\n任务启动结果: {json.dumps(result, indent=2)}")
    
    # 模拟思维过程
    metacognitive_system.record_thought(
        thought_type="analysis",
        content="首先识别性能瓶颈",
        reasoning="需要找到最耗时的部分才能有效优化",
        confidence_level=4
    )
    
    metacognitive_system.add_strategy("系统性分析")
    
    metacognitive_system.record_thought(
        thought_type="analysis",
        content="发现数据库查询是主要瓶颈",
        reasoning="通过性能分析工具确认",
        confidence_level=5
    )
    
    # 更新信心
    metacognitive_system.update_confidence(
        knowledge_level=0.7,
        evidence_quality=0.8,
        reasoning_clarity=0.7,
        familiarity=0.6
    )
    
    metacognitive_system.add_lesson("优化前先做性能分析，避免盲目优化")
    
    # 结束任务
    summary = metacognitive_system.end_cognitive_task("成功优化，性能提升50%")
    print(f"\n任务总结: {json.dumps(summary, indent=2, ensure_ascii=False)}")
    
    # 获取系统状态
    status = metacognitive_system.get_system_status()
    print(f"\n系统状态: {json.dumps(status, indent=2, ensure_ascii=False)}")
    
    # 保存状态
    metacognitive_system.save_system_state()

if __name__ == "__main__":
    demo()
