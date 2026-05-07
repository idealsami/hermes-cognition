#!/usr/bin/env python3
"""
Hermes 决策引擎 (Decision Engine)
整合元认知系统，提供高级决策能力。
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import sys

# 导入元认知系统
sys.path.insert(0, '/root/.hermes/cognition/meta')
from metacognitive_system import MetacognitiveSystem, metacognitive_system

class DecisionType(Enum):
    """决策类型"""
    BINARY = "binary"              # 二选一决策
    MULTIPLE_CHOICE = "multiple_choice"  # 多选一决策
    OPTIMIZATION = "optimization"  # 优化决策
    RESOURCE_ALLOCATION = "resource_allocation"  # 资源分配
    RISK_MANAGEMENT = "risk_management"  # 风险管理
    STRATEGIC = "strategic"        # 战略决策
    TACTICAL = "tactical"          # 战术决策
    OPERATIONAL = "operational"    # 操作决策

class RiskLevel(Enum):
    """风险等级"""
    VERY_LOW = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    VERY_HIGH = 5

@dataclass
class DecisionOption:
    """决策选项"""
    option_id: str
    name: str
    description: str
    pros: List[str]
    cons: List[str]
    risk_level: RiskLevel
    estimated_outcome: float  # 0.0 - 1.0
    resource_requirements: Dict[str, float]
    time_estimate: float  # 小时
    confidence: float  # 0.0 - 1.0

@dataclass
class DecisionContext:
    """决策上下文"""
    decision_id: str
    description: str
    decision_type: DecisionType
    options: List[DecisionOption]
    constraints: List[str]
    objectives: List[str]
    stakeholders: List[str]
    time_pressure: float  # 0.0 - 1.0
    available_resources: Dict[str, float]
    start_time: str
    status: str = "pending"

@dataclass
class DecisionResult:
    """决策结果"""
    decision_id: str
    chosen_option: str
    reasoning: str
    risk_assessment: Dict[str, Any]
    expected_outcome: float
    confidence: float
    alternatives_considered: int
    decision_time: str
    review_date: Optional[str] = None

class DecisionEngine:
    """决策引擎主类"""
    
    def __init__(self):
        self.metacognitive = metacognitive_system
        self.decision_history: List[DecisionResult] = []
        self.current_decision: Optional[DecisionContext] = None
        
        # 决策日志目录
        self.log_dir = Path("/root/.hermes/cognition/decision/logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 风险评估权重
        self.risk_weights = {
            "financial": 0.3,
            "time": 0.25,
            "reputation": 0.2,
            "technical": 0.15,
            "resource": 0.1
        }
        
        print("[决策引擎] 初始化完成")
    
    def start_decision(self, 
                      description: str,
                      decision_type: DecisionType,
                      options: List[Dict[str, Any]],
                      constraints: List[str] = None,
                      objectives: List[str] = None,
                      stakeholders: List[str] = None,
                      time_pressure: float = 0.5,
                      available_resources: Dict[str, float] = None) -> Dict[str, Any]:
        """开始新的决策过程"""
        
        decision_id = f"decision_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 转换选项格式
        decision_options = []
        for i, opt in enumerate(options):
            option = DecisionOption(
                option_id=f"option_{i+1}",
                name=opt.get("name", f"选项{i+1}"),
                description=opt.get("description", ""),
                pros=opt.get("pros", []),
                cons=opt.get("cons", []),
                risk_level=RiskLevel(opt.get("risk_level", 3)),
                estimated_outcome=opt.get("estimated_outcome", 0.5),
                resource_requirements=opt.get("resource_requirements", {}),
                time_estimate=opt.get("time_estimate", 1.0),
                confidence=opt.get("confidence", 0.5)
            )
            decision_options.append(option)
        
        # 创建决策上下文
        self.current_decision = DecisionContext(
            decision_id=decision_id,
            description=description,
            decision_type=decision_type,
            options=decision_options,
            constraints=constraints or [],
            objectives=objectives or [],
            stakeholders=stakeholders or [],
            time_pressure=time_pressure,
            available_resources=available_resources or {},
            start_time=datetime.now().isoformat()
        )
        
        # 启动元认知监控
        self.metacognitive.start_cognitive_task(f"决策: {description}")
        
        # 打印决策启动报告
        self._print_decision_start_report()
        
        return {
            "decision_id": decision_id,
            "decision_type": decision_type.value,
            "options_count": len(decision_options),
            "constraints_count": len(constraints or []),
            "objectives_count": len(objectives or [])
        }
    
    def analyze_options(self) -> Dict[str, Any]:
        """分析所有决策选项"""
        
        if not self.current_decision:
            raise ValueError("没有活跃的决策过程")
        
        analysis_results = []
        
        for option in self.current_decision.options:
            # 计算综合得分
            score = self._calculate_option_score(option)
            
            # 风险评估
            risk_assessment = self._assess_risk(option)
            
            # 可行性评估
            feasibility = self._assess_feasibility(option)
            
            analysis_results.append({
                "option_id": option.option_id,
                "name": option.name,
                "overall_score": score,
                "risk_assessment": risk_assessment,
                "feasibility": feasibility,
                "pros_count": len(option.pros),
                "cons_count": len(option.cons),
                "confidence": option.confidence
            })
        
        # 按得分排序
        analysis_results.sort(key=lambda x: x["overall_score"], reverse=True)
        
        # 记录分析过程
        self.metacognitive.record_thought(
            thought_type="analysis",
            content=f"分析了{len(analysis_results)}个决策选项",
            reasoning="通过多维度评估每个选项的优劣",
            confidence_level=4
        )
        
        return {
            "decision_id": self.current_decision.decision_id,
            "analysis_results": analysis_results,
            "best_option": analysis_results[0] if analysis_results else None,
            "analysis_time": datetime.now().isoformat()
        }
    
    def _calculate_option_score(self, option: DecisionOption) -> float:
        """计算选项综合得分"""
        
        # 基础分 = 预期结果 * 信心
        base_score = option.estimated_outcome * option.confidence
        
        # 风险调整（风险越低越好）
        risk_adjustment = 1.0 - (option.risk_level.value - 1) / 4 * 0.3
        
        # 时间调整（时间越短越好，但要考虑质量）
        time_adjustment = 1.0 / (1.0 + option.time_estimate * 0.1)
        
        # 优缺点调整
        pros_cons_ratio = len(option.pros) / max(len(option.cons), 1)
        pros_cons_adjustment = min(pros_cons_ratio / 2, 1.5)  # 最多加50%
        
        # 综合得分
        final_score = base_score * risk_adjustment * time_adjustment * pros_cons_adjustment
        
        return round(final_score, 3)
    
    def _assess_risk(self, option: DecisionOption) -> Dict[str, Any]:
        """评估选项风险"""
        
        risk_factors = {
            "financial": 0.5,  # 默认中等
            "time": 0.5,
            "reputation": 0.5,
            "technical": 0.5,
            "resource": 0.5
        }
        
        # 根据风险等级调整
        risk_multiplier = option.risk_level.value / 3  # 以中等风险为基准
        
        for factor in risk_factors:
            risk_factors[factor] *= risk_multiplier
        
        # 计算总体风险
        overall_risk = sum(
            risk_factors[factor] * self.risk_weights[factor]
            for factor in risk_factors
        )
        
        # 风险等级描述
        if overall_risk < 0.3:
            risk_level_desc = "低风险"
        elif overall_risk < 0.6:
            risk_level_desc = "中等风险"
        elif overall_risk < 0.8:
            risk_level_desc = "高风险"
        else:
            risk_level_desc = "极高风险"
        
        return {
            "overall_risk": round(overall_risk, 3),
            "risk_level": risk_level_desc,
            "risk_factors": risk_factors,
            "mitigation_suggestions": self._generate_risk_mitigation(option)
        }
    
    def _generate_risk_mitigation(self, option: DecisionOption) -> List[str]:
        """生成风险缓解建议"""
        
        suggestions = []
        
        if option.risk_level.value >= 4:
            suggestions.append("制定详细的应急计划")
            suggestions.append("设置风险监控指标")
        
        if option.time_estimate > 10:
            suggestions.append("将任务分解为多个阶段")
            suggestions.append("设置阶段性检查点")
        
        if len(option.cons) > len(option.pros):
            suggestions.append("重新评估选项的必要性")
            suggestions.append("寻找减少缺点的方法")
        
        if option.confidence < 0.6:
            suggestions.append("收集更多信息提高信心")
            suggestions.append("考虑小规模试点验证")
        
        return suggestions
    
    def _assess_feasibility(self, option: DecisionOption) -> Dict[str, Any]:
        """评估选项可行性"""
        
        feasibility_score = 0.0
        factors = []
        
        # 资源可行性
        resource_feasibility = 1.0
        for resource, required in option.resource_requirements.items():
            available = self.current_decision.available_resources.get(resource, 0)
            if available > 0:
                ratio = required / available
                resource_feasibility = min(resource_feasibility, 1.0 / ratio)
        
        feasibility_score += resource_feasibility * 0.4
        factors.append({
            "factor": "资源可行性",
            "score": resource_feasibility,
            "weight": 0.4
        })
        
        # 时间可行性
        time_feasibility = 1.0 / (1.0 + option.time_estimate * 0.1)
        feasibility_score += time_feasibility * 0.3
        factors.append({
            "factor": "时间可行性",
            "score": time_feasibility,
            "weight": 0.3
        })
        
        # 技术可行性（基于信心）
        technical_feasibility = option.confidence
        feasibility_score += technical_feasibility * 0.3
        factors.append({
            "factor": "技术可行性",
            "score": technical_feasibility,
            "weight": 0.3
        })
        
        return {
            "overall_feasibility": round(feasibility_score, 3),
            "factors": factors,
            "is_feasible": feasibility_score > 0.6
        }
    
    def make_decision(self, 
                     chosen_option_id: str,
                     reasoning: str,
                     review_date: str = None) -> Dict[str, Any]:
        """做出最终决策"""
        
        if not self.current_decision:
            raise ValueError("没有活跃的决策过程")
        
        # 找到选择的选项
        chosen_option = None
        for option in self.current_decision.options:
            if option.option_id == chosen_option_id:
                chosen_option = option
                break
        
        if not chosen_option:
            raise ValueError(f"未找到选项: {chosen_option_id}")
        
        # 风险评估
        risk_assessment = self._assess_risk(chosen_option)
        
        # 创建决策结果
        decision_result = DecisionResult(
            decision_id=self.current_decision.decision_id,
            chosen_option=chosen_option_id,
            reasoning=reasoning,
            risk_assessment=risk_assessment,
            expected_outcome=chosen_option.estimated_outcome,
            confidence=chosen_option.confidence,
            alternatives_considered=len(self.current_decision.options),
            decision_time=datetime.now().isoformat(),
            review_date=review_date
        )
        
        # 保存决策结果
        self.decision_history.append(decision_result)
        
        # 记录到元认知系统
        self.metacognitive.record_thought(
            thought_type="decision",
            content=f"选择选项: {chosen_option.name}",
            reasoning=reasoning,
            confidence_level=int(chosen_option.confidence * 5)
        )
        
        self.metacognitive.add_lesson(f"决策: {self.current_decision.description[:50]}...")
        
        # 结束元认知任务
        self.metacognitive.end_cognitive_task(f"决策完成: {chosen_option.name}")
        
        # 保存决策日志
        self._save_decision_log(decision_result)
        
        # 重置当前决策
        self.current_decision = None
        
        return asdict(decision_result)
    
    def _save_decision_log(self, decision_result: DecisionResult):
        """保存决策日志"""
        
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"{decision_result.decision_id}.json"
        filepath = self.log_dir / date_str / filename
        
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        log_data = {
            "decision_result": asdict(decision_result),
            "saved_at": datetime.now().isoformat()
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)
        
        print(f"[决策引擎] 决策日志已保存: {filepath}")
    
    def _print_decision_start_report(self):
        """打印决策启动报告"""
        
        if not self.current_decision:
            return
        
        decision = self.current_decision
        
        print("\n" + "="*60)
        print("🎯 决策过程启动")
        print("="*60)
        print(f"决策ID: {decision.decision_id}")
        print(f"描述: {decision.description[:80]}...")
        print(f"类型: {decision.decision_type.value}")
        print(f"选项数量: {len(decision.options)}")
        print(f"约束条件: {len(decision.constraints)}")
        print(f"目标数量: {len(decision.objectives)}")
        print(f"时间压力: {decision.time_pressure:.0%}")
        
        print("\n选项概览:")
        for i, option in enumerate(decision.options, 1):
            print(f"  {i}. {option.name}")
            print(f"     风险: {option.risk_level.name}")
            print(f"     预期结果: {option.estimated_outcome:.0%}")
            print(f"     信心: {option.confidence:.0%}")
        
        print("="*60)
    
    def get_decision_stats(self) -> Dict[str, Any]:
        """获取决策统计"""
        
        if not self.decision_history:
            return {"message": "暂无决策历史"}
        
        # 计算平均信心
        avg_confidence = sum(
            d.confidence for d in self.decision_history
        ) / len(self.decision_history)
        
        # 计算平均预期结果
        avg_outcome = sum(
            d.expected_outcome for d in self.decision_history
        ) / len(self.decision_history)
        
        # 统计决策类型
        type_counts = {}
        for decision in self.decision_history:
            # 这里简化处理，实际应该从决策上下文中获取
            type_counts["unknown"] = type_counts.get("unknown", 0) + 1
        
        return {
            "total_decisions": len(self.decision_history),
            "average_confidence": round(avg_confidence, 3),
            "average_expected_outcome": round(avg_outcome, 3),
            "decision_type_distribution": type_counts,
            "recent_decisions": [
                {
                    "decision_id": d.decision_id,
                    "chosen_option": d.chosen_option,
                    "confidence": d.confidence,
                    "decision_time": d.decision_time
                }
                for d in self.decision_history[-5:]
            ]
        }
    
    def review_decision(self, decision_id: str) -> Dict[str, Any]:
        """回顾决策"""
        
        # 查找决策
        decision = None
        for d in self.decision_history:
            if d.decision_id == decision_id:
                decision = d
                break
        
        if not decision:
            return {"error": "未找到指定决策"}
        
        # 生成回顾报告
        review_report = {
            "decision_id": decision.decision_id,
            "chosen_option": decision.chosen_option,
            "original_confidence": decision.confidence,
            "original_expected_outcome": decision.expected_outcome,
            "decision_time": decision.decision_time,
            "review_time": datetime.now().isoformat(),
            "days_since_decision": (
                datetime.now() - datetime.fromisoformat(decision.decision_time)
            ).days,
            "risk_assessment": decision.risk_assessment,
            "reasoning": decision.reasoning
        }
        
        return review_report

# 全局实例
decision_engine = DecisionEngine()

def demo():
    """演示决策引擎"""
    
    print("="*60)
    print("🎯 决策引擎演示")
    print("="*60)
    
    # 开始决策
    result = decision_engine.start_decision(
        description="选择下一个要开发的AI功能模块",
        decision_type=DecisionType.MULTIPLE_CHOICE,
        options=[
            {
                "name": "自然语言处理模块",
                "description": "增强文本理解和生成能力",
                "pros": ["提升对话质量", "支持更多语言任务"],
                "cons": ["需要大量训练数据", "计算资源要求高"],
                "risk_level": 3,
                "estimated_outcome": 0.8,
                "resource_requirements": {"gpu_hours": 100, "data_size": 10},
                "time_estimate": 40,
                "confidence": 0.7
            },
            {
                "name": "计算机视觉模块",
                "description": "添加图像识别和处理能力",
                "pros": ["扩展应用场景", "技术成熟度高"],
                "cons": ["需要标注数据", "模型体积大"],
                "risk_level": 2,
                "estimated_outcome": 0.75,
                "resource_requirements": {"gpu_hours": 80, "data_size": 5},
                "time_estimate": 30,
                "confidence": 0.8
            },
            {
                "name": "强化学习模块",
                "description": "实现自主学习和决策能力",
                "pros": ["真正的智能", "适应性强"],
                "cons": ["训练不稳定", "需要环境模拟"],
                "risk_level": 4,
                "estimated_outcome": 0.9,
                "resource_requirements": {"gpu_hours": 150, "simulation_time": 200},
                "time_estimate": 60,
                "confidence": 0.6
            }
        ],
        constraints=["预算限制", "时间限制", "技术可行性"],
        objectives=["提升AI能力", "保持稳定性", "控制成本"],
        stakeholders=["开发团队", "用户", "管理层"],
        time_pressure=0.6,
        available_resources={"gpu_hours": 200, "data_size": 15, "simulation_time": 100}
    )
    
    print(f"\n决策启动结果: {json.dumps(result, indent=2)}")
    
    # 分析选项
    analysis = decision_engine.analyze_options()
    print(f"\n选项分析结果:")
    print(f"最佳选项: {analysis['best_option']['name']}")
    print(f"得分: {analysis['best_option']['overall_score']}")
    
    # 做出决策
    decision_result = decision_engine.make_decision(
        chosen_option_id="option_2",  # 选择计算机视觉模块
        reasoning="考虑到技术成熟度和资源限制，计算机视觉模块是最佳选择",
        review_date="2026-06-05"
    )
    
    print(f"\n决策结果:")
    print(f"选择: {decision_result['chosen_option']}")
    print(f"信心: {decision_result['confidence']:.0%}")
    print(f"预期结果: {decision_result['expected_outcome']:.0%}")
    
    # 获取统计
    stats = decision_engine.get_decision_stats()
    print(f"\n决策统计: {json.dumps(stats, indent=2, ensure_ascii=False)}")

if __name__ == "__main__":
    demo()