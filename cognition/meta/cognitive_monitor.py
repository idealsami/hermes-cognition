#!/usr/bin/env python3
"""
Hermes 认知监控器 (Cognitive Monitor)
跟踪和记录思维过程，支持元认知分析。
"""

import json
import time
from datetime import datetime
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any

class ThoughtType(Enum):
    """思维类型"""
    ANALYSIS = "analysis"           # 分析性思维
    CREATIVE = "creative"           # 创造性思维
    CRITICAL = "critical"           # 批判性思维
    STRATEGIC = "strategic"         # 策略性思维
    EMPATHETIC = "empathetic"       # 共情性思维
    SYSTEMATIC = "systematic"       # 系统性思维
    REFLECTION = "reflection"       # 反思性思维
    DECISION = "decision"           # 决策性思维
    PROBLEM_SOLVING = "problem_solving"  # 问题解决
    LEARNING = "learning"           # 学习性思维

class ConfidenceLevel(Enum):
    """信心程度"""
    VERY_LOW = 1      # 非常不确定
    LOW = 2           # 不确定
    MODERATE = 3      # 中等
    HIGH = 4          # 较确定
    VERY_HIGH = 5     # 非常确定

@dataclass
class ThoughtStep:
    """思维步骤"""
    id: str
    timestamp: str
    thought_type: str
    content: str
    reasoning: str
    confidence: int
    duration_ms: int
    parent_id: Optional[str] = None
    outcome: Optional[str] = None
    tags: List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []

@dataclass
class CognitiveSession:
    """认知会话"""
    session_id: str
    start_time: str
    task_description: str
    thought_steps: List[ThoughtStep]
    strategies_used: List[str]
    total_duration_ms: int
    final_outcome: Optional[str] = None
    lessons_learned: List[str] = None

    def __post_init__(self):
        if self.lessons_learned is None:
            self.lessons_learned = []

class CognitiveMonitor:
    """认知监控器"""
    
    def __init__(self, log_dir: str = "/root/.hermes/cognition/meta/journal"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.current_session: Optional[CognitiveSession] = None
        self.current_step_start: Optional[float] = None
        self.step_counter = 0
        
    def start_session(self, task_description: str) -> str:
        """开始新的认知会话"""
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.current_session = CognitiveSession(
            session_id=session_id,
            start_time=datetime.now().isoformat(),
            task_description=task_description,
            thought_steps=[],
            strategies_used=[],
            total_duration_ms=0
        )
        
        self.step_counter = 0
        print(f"[元认知] 开始监控认知会话: {session_id}")
        print(f"[元认知] 任务: {task_description}")
        
        return session_id
    
    def record_thought(self, 
                      thought_type: ThoughtType,
                      content: str,
                      reasoning: str,
                      confidence: ConfidenceLevel,
                      parent_id: Optional[str] = None,
                      tags: Optional[List[str]] = None) -> str:
        """记录思维步骤"""
        
        if not self.current_session:
            raise ValueError("没有活跃的认知会话")
        
        # 计算持续时间
        duration_ms = 0
        if self.current_step_start:
            duration_ms = int((time.time() - self.current_step_start) * 1000)
        
        self.step_counter += 1
        step_id = f"step_{self.step_counter}"
        
        step = ThoughtStep(
            id=step_id,
            timestamp=datetime.now().isoformat(),
            thought_type=thought_type.value,
            content=content,
            reasoning=reasoning,
            confidence=confidence.value,
            duration_ms=duration_ms,
            parent_id=parent_id,
            tags=tags or []
        )
        
        self.current_session.thought_steps.append(step)
        self.current_step_start = time.time()
        
        # 打印监控信息
        confidence_desc = {
            1: "❓ 非常不确定",
            2: "🤔 不确定",
            3: "😐 中等",
            4: "😊 较确定",
            5: "💪 非常确定"
        }
        
        print(f"\n[元认知] 步骤 {step_id}")
        print(f"  类型: {thought_type.value}")
        print(f"  信心: {confidence_desc[confidence.value]}")
        print(f"  内容: {content[:100]}...")
        
        return step_id
    
    def update_step_outcome(self, step_id: str, outcome: str):
        """更新步骤结果"""
        if not self.current_session:
            return
        
        for step in self.current_session.thought_steps:
            if step.id == step_id:
                step.outcome = outcome
                print(f"[元认知] 步骤 {step_id} 结果: {outcome}")
                break
    
    def add_strategy(self, strategy_name: str):
        """记录使用的策略"""
        if self.current_session:
            if strategy_name not in self.current_session.strategies_used:
                self.current_session.strategies_used.append(strategy_name)
                print(f"[元认知] 使用策略: {strategy_name}")
    
    def add_lesson(self, lesson: str):
        """记录学习到的经验"""
        if self.current_session:
            self.current_session.lessons_learned.append(lesson)
            print(f"[元认知] 学到经验: {lesson}")
    
    def end_session(self, final_outcome: str = "completed") -> Dict[str, Any]:
        """结束认知会话并生成报告"""
        
        if not self.current_session:
            return {}
        
        # 计算总时长
        self.current_session.total_duration_ms = int(
            (time.time() - time.mktime(
                datetime.fromisoformat(self.current_session.start_time).timetuple()
            )) * 1000
        )
        self.current_session.final_outcome = final_outcome
        
        # 生成会话报告
        report = self._generate_session_report()
        
        # 保存会话日志
        self._save_session_log()
        
        # 打印摘要
        print("\n" + "="*60)
        print("📊 认知会话报告")
        print("="*60)
        print(f"任务: {self.current_session.task_description}")
        print(f"时长: {self.current_session.total_duration_ms / 1000:.1f}秒")
        print(f"思维步骤: {len(self.current_session.thought_steps)}")
        print(f"使用策略: {', '.join(self.current_session.strategies_used)}")
        print(f"结果: {final_outcome}")
        
        if self.current_session.lessons_learned:
            print("\n学习到的经验:")
            for lesson in self.current_session.lessons_learned:
                print(f"  • {lesson}")
        
        print("="*60)
        
        # 重置会话
        session_data = asdict(self.current_session)
        self.current_session = None
        self.current_step_start = None
        
        return session_data
    
    def _generate_session_report(self) -> Dict[str, Any]:
        """生成会话分析报告"""
        
        if not self.current_session:
            return {}
        
        steps = self.current_session.thought_steps
        
        # 统计思维类型
        type_counts = {}
        for step in steps:
            t = step.thought_type
            type_counts[t] = type_counts.get(t, 0) + 1
        
        # 计算平均信心
        if steps:
            avg_confidence = sum(s.confidence for s in steps) / len(steps)
        else:
            avg_confidence = 0
        
        # 识别低信心步骤
        low_confidence_steps = [
            s for s in steps if s.confidence <= 2
        ]
        
        return {
            "session_id": self.current_session.session_id,
            "task": self.current_session.task_description,
            "duration_seconds": self.current_session.total_duration_ms / 1000,
            "total_steps": len(steps),
            "thought_type_distribution": type_counts,
            "average_confidence": round(avg_confidence, 2),
            "low_confidence_count": len(low_confidence_steps),
            "strategies_used": self.current_session.strategies_used,
            "lessons_count": len(self.current_session.lessons_learned)
        }
    
    def _save_session_log(self):
        """保存会话日志到文件"""
        
        if not self.current_session:
            return
        
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"{self.current_session.session_id}.json"
        filepath = self.log_dir / date_str / filename
        
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(asdict(self.current_session), f, ensure_ascii=False, indent=2)
        
        print(f"[元认知] 会话日志已保存: {filepath}")
    
    def get_cognitive_stats(self, days: int = 7) -> Dict[str, Any]:
        """获取认知统计"""
        
        stats = {
            "total_sessions": 0,
            "total_steps": 0,
            "thought_type_totals": {},
            "average_confidence_trend": [],
            "common_strategies": {},
            "frequent_lessons": []
        }
        
        # 扫描日志文件
        cutoff_date = datetime.now().timestamp() - (days * 86400)
        
        for date_dir in self.log_dir.iterdir():
            if not date_dir.is_dir():
                continue
            
            for log_file in date_dir.glob("*.json"):
                try:
                    with open(log_file, 'r') as f:
                        session_data = json.load(f)
                    
                    # 检查时间范围
                    session_time = datetime.fromisoformat(session_data['start_time']).timestamp()
                    if session_time < cutoff_date:
                        continue
                    
                    stats["total_sessions"] += 1
                    stats["total_steps"] += len(session_data.get('thought_steps', []))
                    
                    # 统计思维类型
                    for step in session_data.get('thought_steps', []):
                        t = step['thought_type']
                        stats["thought_type_totals"][t] = stats["thought_type_totals"].get(t, 0) + 1
                    
                    # 统计策略
                    for strategy in session_data.get('strategies_used', []):
                        stats["common_strategies"][strategy] = stats["common_strategies"].get(strategy, 0) + 1
                    
                    # 收集经验
                    stats["frequent_lessons"].extend(session_data.get('lessons_learned', []))
                    
                except Exception as e:
                    print(f"[元认知] 读取日志失败: {e}")
        
        # 去重经验
        stats["frequent_lessons"] = list(set(stats["frequent_lessons"]))[:10]
        
        return stats

# 全局实例
monitor = CognitiveMonitor()

def demo():
    """演示认知监控器"""
    
    print("="*60)
    print("🧠 认知监控器演示")
    print("="*60)
    
    # 开始会话
    monitor.start_session("分析并解决一个技术问题")
    
    # 记录思维步骤
    step1 = monitor.record_thought(
        thought_type=ThoughtType.ANALYSIS,
        content="首先需要理解问题的本质和范围",
        reasoning="系统性分析问题有助于找到根本原因",
        confidence=ConfidenceLevel.HIGH,
        tags=["问题分析", "初始阶段"]
    )
    
    monitor.add_strategy("系统性思维")
    
    step2 = monitor.record_thought(
        thought_type=ThoughtType.CRITICAL,
        content="检查现有解决方案是否适用",
        reasoning="避免重复造轮子，评估现有资源",
        confidence=ConfidenceLevel.MODERATE,
        tags=["评估", "资源检查"]
    )
    
    monitor.add_strategy("批判性思维")
    
    step3 = monitor.record_thought(
        thought_type=ThoughtType.CREATIVE,
        content="提出一个新的解决思路",
        reasoning="现有方案不足，需要创新方法",
        confidence=ConfidenceLevel.LOW,
        tags=["创新", "新方案"]
    )
    
    # 更新步骤结果
    monitor.update_step_outcome(step1, "问题已明确定义")
    monitor.update_step_outcome(step2, "现有方案部分适用")
    monitor.update_step_outcome(step3, "新方案可行")
    
    # 记录学习
    monitor.add_lesson("在解决技术问题前，先充分理解问题范围")
    monitor.add_lesson("创新方案需要更多验证")
    
    # 结束会话
    monitor.end_session("问题已解决")
    
    # 获取统计
    stats = monitor.get_cognitive_stats(days=30)
    print("\n📊 认知统计:")
    print(json.dumps(stats, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    demo()
