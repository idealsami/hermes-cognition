#!/usr/bin/env python3
"""
Hermes 风险评估器 (Risk Assessor)
专门用于评估决策和行动的风险。
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import math

class RiskCategory(Enum):
    """风险类别"""
    FINANCIAL = "financial"          # 财务风险
    TIME = "time"                    # 时间风险
    REPUTATION = "reputation"        # 声誉风险
    TECHNICAL = "technical"          # 技术风险
    RESOURCE = "resource"            # 资源风险
    LEGAL = "legal"                  # 法律风险
    SAFETY = "safety"                # 安全风险
    STRATEGIC = "strategic"          # 战略风险

class RiskImpact(Enum):
    """风险影响"""
    NEGLIGIBLE = 1      # 可忽略
    MINOR = 2           # 轻微
    MODERATE = 3        # 中等
    MAJOR = 4           # 重大
    CATASTROPHIC = 5    # 灾难性

class RiskProbability(Enum):
    """风险概率"""
    RARE = 1            # 罕见
    UNLIKELY = 2        # 不太可能
    POSSIBLE = 3        # 可能
    LIKELY = 4          # 很可能
    ALMOST_CERTAIN = 5  # 几乎确定

@dataclass
class Risk:
    """风险定义"""
    risk_id: str
    category: RiskCategory
    description: str
    probability: RiskProbability
    impact: RiskImpact
    risk_score: float  # probability * impact
    mitigation_strategies: List[str]
    contingency_plans: List[str]
    owner: str
    status: str = "identified"  # identified, mitigated, accepted, transferred
    identified_date: str = None
    review_date: str = None

    def __post_init__(self):
        if self.identified_date is None:
            self.identified_date = datetime.now().isoformat()

@dataclass
class RiskAssessment:
    """风险评估结果"""
    assessment_id: str
    context: str
    risks: List[Risk]
    overall_risk_score: float
    risk_level: str  # low, medium, high, critical
    recommendations: List[str]
    assessment_time: str
    assessor: str = "Hermes"

class RiskAssessor:
    """风险评估器主类"""
    
    def __init__(self):
        self.risk_history: List[RiskAssessment] = []
        self.risk_registry: Dict[str, Risk] = {}
        
        # 风险评估日志目录
        self.log_dir = Path("/root/.hermes/cognition/decision/risk_logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 风险矩阵配置
        self.risk_matrix = self._initialize_risk_matrix()
        
        print("[风险评估器] 初始化完成")
    
    def _initialize_risk_matrix(self) -> Dict[Tuple[int, int], str]:
        """初始化风险矩阵"""
        
        matrix = {}
        
        # 概率: 1-5, 影响: 1-5
        for prob in range(1, 6):
            for impact in range(1, 6):
                score = prob * impact
                
                if score <= 4:
                    level = "low"
                elif score <= 9:
                    level = "medium"
                elif score <= 16:
                    level = "high"
                else:
                    level = "critical"
                
                matrix[(prob, impact)] = level
        
        return matrix
    
    def assess_risks(self,
                    context: str,
                    risk_descriptions: List[Dict[str, Any]],
                    assessor: str = "Hermes") -> RiskAssessment:
        """评估一组风险"""
        
        assessment_id = f"risk_assessment_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        risks = []
        total_risk_score = 0.0
        
        for i, risk_desc in enumerate(risk_descriptions):
            # 创建风险对象
            risk = Risk(
                risk_id=f"risk_{i+1}",
                category=RiskCategory(risk_desc.get("category", "technical")),
                description=risk_desc.get("description", ""),
                probability=RiskProbability(risk_desc.get("probability", 3)),
                impact=RiskImpact(risk_desc.get("impact", 3)),
                risk_score=0.0,  # 将计算
                mitigation_strategies=risk_desc.get("mitigation_strategies", []),
                contingency_plans=risk_desc.get("contingency_plans", []),
                owner=risk_desc.get("owner", "未指定"),
                status="identified"
            )
            
            # 计算风险分数
            risk.risk_score = risk.probability.value * risk.impact.value
            total_risk_score += risk.risk_score
            
            risks.append(risk)
            
            # 注册到风险登记册
            self.risk_registry[risk.risk_id] = risk
        
        # 计算总体风险分数
        overall_risk_score = total_risk_score / len(risks) if risks else 0
        
        # 确定风险等级
        risk_level = self._determine_risk_level(overall_risk_score)
        
        # 生成建议
        recommendations = self._generate_recommendations(risks, risk_level)
        
        # 创建评估结果
        assessment = RiskAssessment(
            assessment_id=assessment_id,
            context=context,
            risks=risks,
            overall_risk_score=overall_risk_score,
            risk_level=risk_level,
            recommendations=recommendations,
            assessment_time=datetime.now().isoformat(),
            assessor=assessor
        )
        
        # 保存到历史
        self.risk_history.append(assessment)
        
        # 保存评估日志
        self._save_assessment_log(assessment)
        
        # 打印评估报告
        self._print_assessment_report(assessment)
        
        return assessment
    
    def _determine_risk_level(self, score: float) -> str:
        """确定风险等级"""
        
        if score <= 4:
            return "low"
        elif score <= 9:
            return "medium"
        elif score <= 16:
            return "high"
        else:
            return "critical"
    
    def _generate_recommendations(self, risks: List[Risk], risk_level: str) -> List[str]:
        """生成风险缓解建议"""
        
        recommendations = []
        
        # 根据风险等级生成一般建议
        if risk_level == "critical":
            recommendations.append("立即暂停相关活动，进行全面风险评估")
            recommendations.append("建立专门的风险管理团队")
            recommendations.append("制定详细的风险缓解计划")
        elif risk_level == "high":
            recommendations.append("优先处理高风险项目")
            recommendations.append("增加风险监控频率")
            recommendations.append("准备应急响应计划")
        elif risk_level == "medium":
            recommendations.append("定期审查风险状况")
            recommendations.append("实施标准风险缓解措施")
        else:
            recommendations.append("维持常规风险监控")
        
        # 针对特定风险类别的建议
        categories = set(risk.category for risk in risks)
        
        for category in categories:
            if category == RiskCategory.FINANCIAL:
                recommendations.append("建立财务风险准备金")
                recommendations.append("实施严格的预算控制")
            elif category == RiskCategory.TECHNICAL:
                recommendations.append("增加技术验证和测试")
                recommendations.append("建立技术储备方案")
            elif category == RiskCategory.TIME:
                recommendations.append("设置时间缓冲")
                recommendations.append("建立关键路径监控")
            elif category == RiskCategory.RESOURCE:
                recommendations.append("建立资源储备")
                recommendations.append("实施资源优化计划")
        
        # 去重
        recommendations = list(set(recommendations))
        
        return recommendations
    
    def _save_assessment_log(self, assessment: RiskAssessment):
        """保存评估日志"""
        
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"{assessment.assessment_id}.json"
        filepath = self.log_dir / date_str / filename
        
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # 转换为可序列化格式
        log_data = {
            "assessment_id": assessment.assessment_id,
            "context": assessment.context,
            "overall_risk_score": assessment.overall_risk_score,
            "risk_level": assessment.risk_level,
            "recommendations": assessment.recommendations,
            "assessment_time": assessment.assessment_time,
            "assessor": assessment.assessor,
            "risks": [
                {
                    "risk_id": risk.risk_id,
                    "category": risk.category.value,
                    "description": risk.description,
                    "probability": risk.probability.value,
                    "impact": risk.impact.value,
                    "risk_score": risk.risk_score,
                    "mitigation_strategies": risk.mitigation_strategies,
                    "contingency_plans": risk.contingency_plans,
                    "owner": risk.owner,
                    "status": risk.status
                }
                for risk in assessment.risks
            ]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)
        
        print(f"[风险评估器] 评估日志已保存: {filepath}")
    
    def _print_assessment_report(self, assessment: RiskAssessment):
        """打印评估报告"""
        
        print("\n" + "="*60)
        print("⚠️  风险评估报告")
        print("="*60)
        print(f"评估ID: {assessment.assessment_id}")
        print(f"上下文: {assessment.context[:80]}...")
        print(f"总体风险分数: {assessment.overall_risk_score:.2f}")
        print(f"风险等级: {assessment.risk_level.upper()}")
        
        # 风险等级图标
        level_icons = {
            "low": "🟢",
            "medium": "🟡",
            "high": "🟠",
            "critical": "🔴"
        }
        print(f"状态: {level_icons.get(assessment.risk_level, '⚪')} {assessment.risk_level}")
        
        print(f"\n识别到的风险 ({len(assessment.risks)}):")
        for risk in assessment.risks:
            print(f"  • {risk.description[:50]}...")
            print(f"    类别: {risk.category.value}")
            print(f"    概率: {risk.probability.name}, 影响: {risk.impact.name}")
            print(f"    风险分数: {risk.risk_score}")
        
        print(f"\n建议措施:")
        for i, rec in enumerate(assessment.recommendations[:5], 1):
            print(f"  {i}. {rec}")
        
        print("="*60)
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """获取风险摘要"""
        
        if not self.risk_history:
            return {"message": "暂无风险评估历史"}
        
        latest = self.risk_history[-1]
        
        # 统计风险类别
        category_counts = {}
        for risk in latest.risks:
            cat = risk.category.value
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        # 统计风险等级
        level_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        for risk in latest.risks:
            level = self._determine_risk_level(risk.risk_score)
            level_counts[level] += 1
        
        return {
            "total_assessments": len(self.risk_history),
            "latest_assessment": {
                "assessment_id": latest.assessment_id,
                "context": latest.context[:100],
                "overall_risk_score": latest.overall_risk_score,
                "risk_level": latest.risk_level,
                "risk_count": len(latest.risks)
            },
            "risk_distribution": {
                "by_category": category_counts,
                "by_level": level_counts
            },
            "recent_assessments": [
                {
                    "assessment_id": a.assessment_id,
                    "risk_level": a.risk_level,
                    "assessment_time": a.assessment_time
                }
                for a in self.risk_history[-5:]
            ]
        }
    
    def update_risk_status(self, risk_id: str, new_status: str, notes: str = ""):
        """更新风险状态"""
        
        if risk_id not in self.risk_registry:
            raise ValueError(f"未找到风险: {risk_id}")
        
        risk = self.risk_registry[risk_id]
        old_status = risk.status
        risk.status = new_status
        
        print(f"[风险评估器] 风险 {risk_id} 状态更新: {old_status} -> {new_status}")
        
        if notes:
            print(f"  备注: {notes}")
    
    def get_risks_by_category(self, category: RiskCategory) -> List[Risk]:
        """按类别获取风险"""
        
        return [
            risk for risk in self.risk_registry.values()
            if risk.category == category
        ]
    
    def get_high_risks(self, threshold: float = 10.0) -> List[Risk]:
        """获取高风险项目"""
        
        return [
            risk for risk in self.risk_registry.values()
            if risk.risk_score >= threshold
        ]

# 全局实例
risk_assessor = RiskAssessor()

def demo():
    """演示风险评估器"""
    
    print("="*60)
    print("⚠️  风险评估器演示")
    print("="*60)
    
    # 评估一组风险
    assessment = risk_assessor.assess_risks(
        context="开发新的AI功能模块",
        risk_descriptions=[
            {
                "category": "technical",
                "description": "技术实现难度超出预期",
                "probability": 4,
                "impact": 4,
                "mitigation_strategies": ["增加技术验证", "准备备选方案"],
                "contingency_plans": ["回退到旧版本", "寻求外部技术支持"],
                "owner": "技术团队"
            },
            {
                "category": "time",
                "description": "项目进度延迟",
                "probability": 3,
                "impact": 3,
                "mitigation_strategies": ["设置时间缓冲", "并行开发"],
                "contingency_plans": ["调整项目范围", "增加资源"],
                "owner": "项目经理"
            },
            {
                "category": "financial",
                "description": "预算超支",
                "probability": 2,
                "impact": 4,
                "mitigation_strategies": ["严格预算控制", "分阶段投入"],
                "contingency_plans": ["寻求额外资金", "缩减功能范围"],
                "owner": "财务部门"
            },
            {
                "category": "resource",
                "description": "关键人员离职",
                "probability": 2,
                "impact": 5,
                "mitigation_strategies": ["知识共享", "交叉培训"],
                "contingency_plans": ["招聘替代人员", "外包部分工作"],
                "owner": "人力资源"
            }
        ]
    )
    
    # 获取风险摘要
    summary = risk_assessor.get_risk_summary()
    print(f"\n风险摘要:")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    
    # 获取高风险项目
    high_risks = risk_assessor.get_high_risks(threshold=10.0)
    print(f"\n高风险项目 ({len(high_risks)}):")
    for risk in high_risks:
        print(f"  • {risk.description}")
        print(f"    风险分数: {risk.risk_score}")

if __name__ == "__main__":
    demo()