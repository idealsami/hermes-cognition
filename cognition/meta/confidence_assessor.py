#!/usr/bin/env python3
"""
Hermes 信心评估器 (Confidence Assessor)
评估对回答和决策的信心程度。
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

class ConfidenceFactor(Enum):
    """影响信心的因素"""
    KNOWLEDGE_LEVEL = "knowledge_level"        # 知识水平
    EVIDENCE_QUALITY = "evidence_quality"      # 证据质量
    REASONING_CLARITY = "reasoning_clarity"    # 推理清晰度
    CONSISTENCY = "consistency"                # 一致性
    COMPLEXITY = "complexity"                  # 问题复杂度
    FAMILIARITY = "familiarity"                # 熟悉程度
    TIME_PRESSURE = "time_pressure"            # 时间压力

@dataclass
class ConfidenceAssessment:
    """信心评估结果"""
    overall_confidence: float      # 总体信心 (0.0 - 1.0)
    factor_scores: Dict[str, float]  # 各因素得分
    reasoning: str                 # 评估推理
    suggestions: List[str]         # 改进建议
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

class ConfidenceAssessor:
    """信心评估器"""
    
    def __init__(self, log_dir: str = "/root/.hermes/cognition/meta/confidence_logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 因素权重（可根据使用反馈调整）
        self.factor_weights: Dict[ConfidenceFactor, float] = {
            ConfidenceFactor.KNOWLEDGE_LEVEL: 0.25,
            ConfidenceFactor.EVIDENCE_QUALITY: 0.20,
            ConfidenceFactor.REASONING_CLARITY: 0.20,
            ConfidenceFactor.CONSISTENCY: 0.15,
            ConfidenceFactor.COMPLEXITY: 0.10,
            ConfidenceFactor.FAMILIARITY: 0.05,
            ConfidenceFactor.TIME_PRESSURE: 0.05,
        }
        
        # 评估历史
        self.assessment_history: List[ConfidenceAssessment] = []
    
    def assess_confidence(self,
                         task_description: str,
                         knowledge_level: float = 0.5,
                         evidence_quality: float = 0.5,
                         reasoning_clarity: float = 0.5,
                         consistency: float = 0.5,
                         complexity: float = 0.5,
                         familiarity: float = 0.5,
                         time_pressure: float = 0.5) -> ConfidenceAssessment:
        """评估信心程度"""
        
        # 计算各因素得分
        factor_scores = {
            ConfidenceFactor.KNOWLEDGE_LEVEL.value: knowledge_level,
            ConfidenceFactor.EVIDENCE_QUALITY.value: evidence_quality,
            ConfidenceFactor.REASONING_CLARITY.value: reasoning_clarity,
            ConfidenceFactor.CONSISTENCY.value: consistency,
            ConfidenceFactor.COMPLEXITY.value: complexity,
            ConfidenceFactor.FAMILIARITY.value: familiarity,
            ConfidenceFactor.TIME_PRESSURE.value: time_pressure,
        }
        
        # 计算加权总分
        overall_confidence = 0.0
        for factor, weight in self.factor_weights.items():
            score = factor_scores[factor.value]
            overall_confidence += score * weight
        
        # 确保在0-1范围内
        overall_confidence = max(0.0, min(1.0, overall_confidence))
        
        # 生成推理说明
        reasoning = self._generate_reasoning(
            overall_confidence, factor_scores, task_description
        )
        
        # 生成改进建议
        suggestions = self._generate_suggestions(factor_scores)
        
        # 创建评估结果
        assessment = ConfidenceAssessment(
            overall_confidence=overall_confidence,
            factor_scores=factor_scores,
            reasoning=reasoning,
            suggestions=suggestions
        )
        
        # 记录到历史
        self.assessment_history.append(assessment)
        
        # 保存到文件
        self._save_assessment(assessment, task_description)
        
        return assessment
    
    def _generate_reasoning(self,
                           overall: float,
                           factor_scores: Dict[str, float],
                           task_description: str) -> str:
        """生成评估推理"""
        
        # 信心等级描述
        if overall >= 0.8:
            level = "非常有信心"
        elif overall >= 0.6:
            level = "比较有信心"
        elif overall >= 0.4:
            level = "信心一般"
        elif overall >= 0.2:
            level = "信心较低"
        else:
            level = "信心很低"
        
        # 找出最高和最低因素
        sorted_factors = sorted(
            factor_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        highest = sorted_factors[0]
        lowest = sorted_factors[-1]
        
        reasoning = f"对任务「{task_description[:50]}...」的评估结果：\n"
        reasoning += f"总体信心: {level} ({overall:.0%})\n\n"
        reasoning += f"优势因素: {self._get_factor_name(highest[0])} ({highest[1]:.0%})\n"
        reasoning += f"劣势因素: {self._get_factor_name(lowest[0])} ({lowest[1]:.0%})\n"
        
        # 添加具体分析
        if factor_scores['knowledge_level'] < 0.5:
            reasoning += "\n⚠️ 知识储备不足，可能需要进一步学习\n"
        
        if factor_scores['evidence_quality'] < 0.5:
            reasoning += "⚠️ 证据质量较低，建议收集更多信息\n"
        
        if factor_scores['reasoning_clarity'] < 0.5:
            reasoning += "⚠️ 推理不够清晰，需要更系统的分析\n"
        
        return reasoning
    
    def _get_factor_name(self, factor_key: str) -> str:
        """获取因素的中文名称"""
        names = {
            'knowledge_level': '知识水平',
            'evidence_quality': '证据质量',
            'reasoning_clarity': '推理清晰度',
            'consistency': '一致性',
            'complexity': '复杂度',
            'familiarity': '熟悉度',
            'time_pressure': '时间压力'
        }
        return names.get(factor_key, factor_key)
    
    def _generate_suggestions(self, factor_scores: Dict[str, float]) -> List[str]:
        """生成改进建议"""
        
        suggestions = []
        
        if factor_scores['knowledge_level'] < 0.6:
            suggestions.append("建议先学习相关知识，提升知识储备")
        
        if factor_scores['evidence_quality'] < 0.6:
            suggestions.append("收集更多高质量的证据和数据支持")
        
        if factor_scores['reasoning_clarity'] < 0.6:
            suggestions.append("理清推理逻辑，采用更系统的分析方法")
        
        if factor_scores['consistency'] < 0.6:
            suggestions.append("检查答案的一致性，避免自相矛盾")
        
        if factor_scores['complexity'] > 0.7:
            suggestions.append("问题复杂度高，建议分解为子问题逐步解决")
        
        if factor_scores['familiarity'] < 0.5:
            suggestions.append("对任务不太熟悉，可以参考类似案例")
        
        if factor_scores['time_pressure'] > 0.7:
            suggestions.append("时间压力大，优先处理核心问题")
        
        if not suggestions:
            suggestions.append("各方面表现良好，可以自信地给出答案")
        
        return suggestions
    
    def _save_assessment(self, assessment: ConfidenceAssessment, task_description: str):
        """保存评估记录"""
        
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"assessment_{datetime.now().strftime('%H%M%S')}.json"
        filepath = self.log_dir / date_str / filename
        
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'task_description': task_description[:200],
            'assessment': asdict(assessment)
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def get_confidence_trend(self, days: int = 7) -> Dict[str, Any]:
        """获取信心趋势分析"""
        
        if not self.assessment_history:
            return {"message": "暂无评估历史"}
        
        recent = self.assessment_history[-50:]  # 最近50次
        
        # 计算平均信心
        avg_confidence = sum(a.overall_confidence for a in recent) / len(recent)
        
        # 找出常见低分因素
        low_factor_counts: Dict[str, int] = {}
        for assessment in recent:
            for factor, score in assessment.factor_scores.items():
                if score < 0.5:
                    low_factor_counts[factor] = low_factor_counts.get(factor, 0) + 1
        
        # 识别趋势
        if len(recent) >= 10:
            first_half = recent[:len(recent)//2]
            second_half = recent[len(recent)//2:]
            
            first_avg = sum(a.overall_confidence for a in first_half) / len(first_half)
            second_avg = sum(a.overall_confidence for a in second_half) / len(second_half)
            
            if second_avg > first_avg + 0.05:
                trend = "上升"
            elif second_avg < first_avg - 0.05:
                trend = "下降"
            else:
                trend = "稳定"
        else:
            trend = "数据不足"
        
        return {
            "total_assessments": len(self.assessment_history),
            "recent_count": len(recent),
            "average_confidence": round(avg_confidence, 3),
            "trend": trend,
            "common_weak_factors": sorted(
                low_factor_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:3],
            "confidence_distribution": {
                "high (>0.8)": sum(1 for a in recent if a.overall_confidence > 0.8),
                "medium (0.4-0.8)": sum(1 for a in recent if 0.4 <= a.overall_confidence <= 0.8),
                "low (<0.4)": sum(1 for a in recent if a.overall_confidence < 0.4)
            }
        }
    
    def print_assessment_report(self, assessment: ConfidenceAssessment):
        """打印评估报告"""
        
        print("\n" + "="*60)
        print("📊 信心评估报告")
        print("="*60)
        
        # 信心等级图标
        if assessment.overall_confidence >= 0.8:
            icon = "🟢"
        elif assessment.overall_confidence >= 0.6:
            icon = "🔵"
        elif assessment.overall_confidence >= 0.4:
            icon = "🟡"
        else:
            icon = "🔴"
        
        print(f"\n{icon} 总体信心: {assessment.overall_confidence:.0%}")
        
        print("\n各因素得分:")
        for factor, score in assessment.factor_scores.items():
            bar = "█" * int(score * 20) + "░" * (20 - int(score * 20))
            name = self._get_factor_name(factor)
            print(f"  {name:10} [{bar}] {score:.0%}")
        
        print(f"\n评估推理:\n{assessment.reasoning}")
        
        print("\n改进建议:")
        for i, suggestion in enumerate(assessment.suggestions, 1):
            print(f"  {i}. {suggestion}")
        
        print("="*60)

# 全局实例
assessor = ConfidenceAssessor()

def demo():
    """演示信心评估器"""
    
    print("="*60)
    print("📊 信心评估器演示")
    print("="*60)
    
    # 场景1: 高信心
    print("\n场景1: 熟悉领域的简单问题")
    assessment1 = assessor.assess_confidence(
        task_description="Python中如何读取文件",
        knowledge_level=0.9,
        evidence_quality=0.8,
        reasoning_clarity=0.85,
        consistency=0.9,
        complexity=0.2,
        familiarity=0.95,
        time_pressure=0.1
    )
    assessor.print_assessment_report(assessment1)
    
    # 场景2: 中等信心
    print("\n场景2: 需要研究的复杂问题")
    assessment2 = assessor.assess_confidence(
        task_description="设计一个分布式缓存系统",
        knowledge_level=0.6,
        evidence_quality=0.5,
        reasoning_clarity=0.7,
        consistency=0.7,
        complexity=0.8,
        familiarity=0.5,
        time_pressure=0.3
    )
    assessor.print_assessment_report(assessment2)
    
    # 场景3: 低信心
    print("\n场景3: 不熟悉的前沿领域")
    assessment3 = assessor.assess_confidence(
        task_description="解释量子纠缠的最新实验进展",
        knowledge_level=0.3,
        evidence_quality=0.4,
        reasoning_clarity=0.5,
        consistency=0.6,
        complexity=0.9,
        familiarity=0.2,
        time_pressure=0.2
    )
    assessor.print_assessment_report(assessment3)
    
    # 显示趋势
    print("\n" + "="*60)
    print("📈 信心趋势分析")
    print("="*60)
    trend = assessor.get_confidence_trend()
    print(json.dumps(trend, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    demo()
