#!/usr/bin/env python3
"""
Hermes 决策系统 (Decision System)
整合决策引擎、风险评估、多目标优化、决策树生成。
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# 导入决策系统组件
import sys
sys.path.insert(0, '/root/.hermes/cognition/decision')

from decision_engine import DecisionEngine, DecisionType, decision_engine
from risk_assessor import RiskAssessor, RiskCategory, risk_assessor
from multi_objective_optimizer import MultiObjectiveOptimizer, OptimizationMethod, multi_objective_optimizer
from decision_tree_generator import DecisionTreeGenerator, decision_tree_generator

@dataclass
class DecisionSystemConfig:
    """决策系统配置"""
    enable_risk_assessment: bool = True
    enable_multi_objective_optimization: bool = True
    enable_decision_tree: bool = True
    default_optimization_method: OptimizationMethod = OptimizationMethod.WEIGHTED_SUM
    risk_threshold: float = 0.7  # 风险阈值
    confidence_threshold: float = 0.6  # 信心阈值
    log_decisions: bool = True
    auto_review_days: int = 30  # 自动回顾天数

class DecisionSystem:
    """决策系统主类"""
    
    def __init__(self, config: DecisionSystemConfig = None):
        self.config = config or DecisionSystemConfig()
        
        # 初始化组件
        self.decision_engine = decision_engine
        self.risk_assessor = risk_assessor
        self.optimizer = multi_objective_optimizer
        self.tree_generator = decision_tree_generator
        
        # 系统状态
        self.system_state = {
            "initialized_at": datetime.now().isoformat(),
            "total_decisions": 0,
            "successful_decisions": 0,
            "average_confidence": 0.0,
            "risk_assessments": 0,
            "optimizations": 0,
            "decision_trees": 0
        }
        
        # 决策历史
        self.decision_history = []
        
        # 系统日志目录
        self.log_dir = Path("/root/.hermes/cognition/decision/system_logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        print("[决策系统] 初始化完成")
    
    def make_decision(self,
                     description: str,
                     decision_type: DecisionType,
                     options: List[Dict[str, Any]],
                     constraints: List[str] = None,
                     objectives: List[str] = None,
                     stakeholders: List[str] = None,
                     time_pressure: float = 0.5,
                     available_resources: Dict[str, float] = None,
                     risk_analysis: bool = True,
                     optimization_method: OptimizationMethod = None,
                     generate_tree: bool = True) -> Dict[str, Any]:
        """综合决策过程"""
        
        decision_id = f"decision_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        print("\n" + "="*60)
        print("🧠 综合决策过程开始")
        print("="*60)
        print(f"决策ID: {decision_id}")
        print(f"描述: {description[:80]}...")
        
        results = {
            "decision_id": decision_id,
            "description": description,
            "timestamp": datetime.now().isoformat(),
            "components": {}
        }
        
        # 1. 启动决策引擎
        print("\n📊 步骤1: 启动决策引擎")
        engine_result = self.decision_engine.start_decision(
            description=description,
            decision_type=decision_type,
            options=options,
            constraints=constraints,
            objectives=objectives,
            stakeholders=stakeholders,
            time_pressure=time_pressure,
            available_resources=available_resources
        )
        results["components"]["decision_engine"] = engine_result
        
        # 2. 风险评估（如果启用）
        if risk_analysis and self.config.enable_risk_assessment:
            print("\n⚠️  步骤2: 风险评估")
            risk_result = self._perform_risk_analysis(options, description)
            results["components"]["risk_assessment"] = risk_result
        
        # 3. 多目标优化（如果有多个目标）
        if objectives and len(objectives) > 1 and self.config.enable_multi_objective_optimization:
            print("\n🎯 步骤3: 多目标优化")
            opt_method = optimization_method or self.config.default_optimization_method
            optimization_result = self._perform_optimization(
                options, objectives, opt_method
            )
            results["components"]["optimization"] = optimization_result
        
        # 4. 生成决策树（如果启用）
        if generate_tree and self.config.enable_decision_tree:
            print("\n🌳 步骤4: 生成决策树")
            tree_result = self._generate_decision_tree(
                description, options
            )
            results["components"]["decision_tree"] = tree_result
        
        # 5. 分析选项
        print("\n📈 步骤5: 分析选项")
        analysis = self.decision_engine.analyze_options()
        results["components"]["analysis"] = analysis
        
        # 6. 综合推荐
        print("\n💡 步骤6: 综合推荐")
        recommendation = self._generate_recommendation(results)
        results["recommendation"] = recommendation
        
        # 更新系统状态
        self._update_system_state(results)
        
        # 保存决策日志
        if self.config.log_decisions:
            self._save_decision_log(results)
        
        print("\n" + "="*60)
        print("✅ 综合决策过程完成")
        print("="*60)
        
        return results
    
    def _perform_risk_analysis(self, 
                              options: List[Dict[str, Any]], 
                              context: str) -> Dict[str, Any]:
        """执行风险分析"""
        
        # 从选项中提取风险信息
        risk_descriptions = []
        
        for i, option in enumerate(options):
            # 基于选项特征推断风险
            risk_level = option.get("risk_level", 3)
            
            # 为每个选项创建风险描述
            risk_desc = {
                "category": "technical",
                "description": f"选项 '{option.get('name', f'选项{i+1}')}' 的技术实现风险",
                "probability": min(risk_level, 5),
                "impact": min(risk_level, 5),
                "mitigation_strategies": option.get("mitigation_strategies", [
                    "增加技术验证",
                    "准备备选方案"
                ]),
                "contingency_plans": option.get("contingency_plans", [
                    "回退到旧版本",
                    "寻求外部支持"
                ]),
                "owner": "技术团队"
            }
            risk_descriptions.append(risk_desc)
            
            # 如果有明确的风险描述，添加额外风险
            if "risks" in option:
                for risk in option["risks"]:
                    risk_descriptions.append(risk)
        
        # 执行风险评估
        assessment = self.risk_assessor.assess_risks(
            context=context,
            risk_descriptions=risk_descriptions
        )
        
        return {
            "assessment_id": assessment.assessment_id,
            "overall_risk_score": assessment.overall_risk_score,
            "risk_level": assessment.risk_level,
            "risk_count": len(assessment.risks),
            "recommendations": assessment.recommendations
        }
    
    def _perform_optimization(self,
                             options: List[Dict[str, Any]],
                             objectives: List[str],
                             method: OptimizationMethod) -> Dict[str, Any]:
        """执行多目标优化"""
        
        # 转换目标格式
        obj_list = []
        for i, obj_name in enumerate(objectives):
            obj_list.append({
                "objective_id": f"obj_{i+1}",
                "name": obj_name,
                "description": f"目标: {obj_name}",
                "weight": 1.0 / len(objectives),  # 平均权重
                "target_value": 100,  # 默认目标值
                "current_value": 50,  # 默认当前值
                "is_benefit": True,  # 默认越大越好
                "priority": i + 1
            })
        
        # 转换选项格式
        alt_list = []
        for i, option in enumerate(options):
            # 为每个选项生成目标值
            objective_values = {}
            for j, obj_name in enumerate(objectives):
                # 使用选项中的值或生成随机值
                value_key = f"obj_{j+1}_value"
                if value_key in option:
                    objective_values[f"obj_{j+1}"] = option[value_key]
                else:
                    # 基于选项特征生成值
                    base_value = option.get("estimated_outcome", 0.5) * 100
                    variation = (i * 10 + j * 5) % 30 - 15  # 添加一些变化
                    objective_values[f"obj_{j+1}"] = max(0, min(100, base_value + variation))
            
            alt_list.append({
                "alternative_id": f"alt_{i+1}",
                "name": option.get("name", f"选项{i+1}"),
                "description": option.get("description", ""),
                "objective_values": objective_values
            })
        
        # 执行优化
        result = self.optimizer.optimize(
            objectives=obj_list,
            alternatives=alt_list,
            method=method
        )
        
        return {
            "optimization_id": result.optimization_id,
            "method": result.method.value,
            "best_alternative": {
                "id": result.best_alternative.alternative_id,
                "name": result.best_alternative.name
            } if result.best_alternative else None,
            "ranking": result.ranking[:5],  # 前5名
            "pareto_front_count": len(result.pareto_front),
            "robustness_score": result.sensitivity_analysis.get("robustness_score", 0)
        }
    
    def _generate_decision_tree(self,
                               description: str,
                               options: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成决策树"""
        
        # 为每个选项创建情景分析
        chance_scenarios = [
            {
                "name": "成功",
                "description": "项目成功完成",
                "probability": 0.7,
                "value": 10000
            },
            {
                "name": "部分成功",
                "description": "部分功能实现",
                "probability": 0.2,
                "value": 6000
            },
            {
                "name": "失败",
                "description": "项目失败",
                "probability": 0.1,
                "value": 2000
            }
        ]
        
        # 生成决策树
        tree = self.tree_generator.generate_tree(
            name=f"决策树: {description[:50]}...",
            description=description,
            decision_options=options,
            chance_scenarios=chance_scenarios
        )
        
        # 获取统计信息
        stats = self.tree_generator.get_tree_statistics(tree.tree_id)
        
        # 比较备选方案
        comparison = self.tree_generator.compare_alternatives(tree.tree_id)
        
        return {
            "tree_id": tree.tree_id,
            "node_count": stats["total_nodes"],
            "max_depth": stats["max_depth"],
            "expected_value": stats["expected_value"],
            "optimal_path_length": stats["optimal_path_length"],
            "optimal_alternative": comparison.get("optimal_alternative")
        }
    
    def _generate_recommendation(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """生成综合推荐"""
        
        recommendation = {
            "primary_recommendation": None,
            "confidence": 0.0,
            "reasoning": [],
            "alternatives": [],
            "risk_mitigation": [],
            "next_steps": []
        }
        
        # 从各个组件收集推荐
        component_recommendations = []
        
        # 从决策引擎获取推荐
        if "analysis" in results["components"]:
            analysis = results["components"]["analysis"]
            if "best_option" in analysis and analysis["best_option"]:
                component_recommendations.append({
                    "source": "decision_engine",
                    "option": analysis["best_option"]["name"],
                    "score": analysis["best_option"]["overall_score"],
                    "confidence": analysis["best_option"]["confidence"]
                })
        
        # 从优化结果获取推荐
        if "optimization" in results["components"]:
            optimization = results["components"]["optimization"]
            if "best_alternative" in optimization and optimization["best_alternative"]:
                component_recommendations.append({
                    "source": "optimizer",
                    "option": optimization["best_alternative"]["name"],
                    "score": optimization.get("robustness_score", 0.5),
                    "confidence": 0.8  # 优化器的默认信心
                })
        
        # 从决策树获取推荐
        if "decision_tree" in results["components"]:
            tree = results["components"]["decision_tree"]
            if "optimal_alternative" in tree and tree["optimal_alternative"]:
                component_recommendations.append({
                    "source": "decision_tree",
                    "option": tree["optimal_alternative"]["name"],
                    "score": tree["optimal_alternative"].get("expected_value", 0) / 10000,
                    "confidence": 0.7  # 决策树的默认信心
                })
        
        # 综合推荐
        if component_recommendations:
            # 按得分排序
            component_recommendations.sort(key=lambda x: x["score"], reverse=True)
            
            best_rec = component_recommendations[0]
            recommendation["primary_recommendation"] = best_rec["option"]
            recommendation["confidence"] = best_rec["confidence"]
            
            # 生成推理
            recommendation["reasoning"] = [
                f"基于{best_rec['source']}的分析，推荐选择 '{best_rec['option']}'",
                f"综合得分: {best_rec['score']:.3f}",
                f"信心程度: {best_rec['confidence']:.0%}"
            ]
            
            # 添加其他推荐作为备选
            for rec in component_recommendations[1:3]:  # 最多3个备选
                recommendation["alternatives"].append({
                    "option": rec["option"],
                    "source": rec["source"],
                    "score": rec["score"]
                })
        
        # 添加风险缓解建议
        if "risk_assessment" in results["components"]:
            risk = results["components"]["risk_assessment"]
            if "recommendations" in risk:
                recommendation["risk_mitigation"] = risk["recommendations"][:3]
        
        # 添加下一步建议
        recommendation["next_steps"] = [
            "详细评估推荐方案",
            "制定实施计划",
            "分配资源和责任",
            "设置监控指标"
        ]
        
        return recommendation
    
    def _update_system_state(self, results: Dict[str, Any]):
        """更新系统状态"""
        
        self.system_state["total_decisions"] += 1
        
        # 更新组件使用统计
        if "risk_assessment" in results["components"]:
            self.system_state["risk_assessments"] += 1
        
        if "optimization" in results["components"]:
            self.system_state["optimizations"] += 1
        
        if "decision_tree" in results["components"]:
            self.system_state["decision_trees"] += 1
        
        # 更新平均信心
        if "recommendation" in results:
            confidence = results["recommendation"].get("confidence", 0)
            total = self.system_state["total_decisions"]
            current_avg = self.system_state["average_confidence"]
            
            # 计算新的平均值
            new_avg = (current_avg * (total - 1) + confidence) / total
            self.system_state["average_confidence"] = round(new_avg, 3)
        
        # 保存到历史
        self.decision_history.append({
            "decision_id": results["decision_id"],
            "timestamp": results["timestamp"],
            "description": results["description"][:100],
            "recommendation": results.get("recommendation", {}).get("primary_recommendation")
        })
    
    def _save_decision_log(self, results: Dict[str, Any]):
        """保存决策日志"""
        
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"{results['decision_id']}.json"
        filepath = self.log_dir / date_str / filename
        
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # 转换为可序列化格式
        log_data = {
            "decision_id": results["decision_id"],
            "description": results["description"],
            "timestamp": results["timestamp"],
            "components": {},
            "recommendation": results.get("recommendation"),
            "system_state": self.system_state
        }
        
        # 简化组件数据
        for component_name, component_data in results["components"].items():
            if isinstance(component_data, dict):
                # 只保存关键信息
                simplified = {}
                for key, value in component_data.items():
                    if isinstance(value, (str, int, float, bool, list)):
                        simplified[key] = value
                    elif isinstance(value, dict):
                        # 只保存字典的第一层
                        simplified[key] = {
                            k: v for k, v in value.items()
                            if isinstance(v, (str, int, float, bool))
                        }
                log_data["components"][component_name] = simplified
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)
        
        print(f"[决策系统] 决策日志已保存: {filepath}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        
        return {
            "system_state": self.system_state,
            "component_status": {
                "decision_engine": "active",
                "risk_assessor": "active",
                "optimizer": "active",
                "tree_generator": "active"
            },
            "recent_decisions": self.decision_history[-5:],
            "config": {
                "enable_risk_assessment": self.config.enable_risk_assessment,
                "enable_multi_objective_optimization": self.config.enable_multi_objective_optimization,
                "enable_decision_tree": self.config.enable_decision_tree,
                "default_optimization_method": self.config.default_optimization_method.value,
                "risk_threshold": self.config.risk_threshold,
                "confidence_threshold": self.config.confidence_threshold
            }
        }
    
    def review_decision(self, decision_id: str) -> Dict[str, Any]:
        """回顾决策"""
        
        # 从历史中查找决策
        decision_record = None
        for record in self.decision_history:
            if record["decision_id"] == decision_id:
                decision_record = record
                break
        
        if not decision_record:
            return {"error": "未找到指定决策"}
        
        # 生成回顾报告
        review = {
            "decision_id": decision_id,
            "original_description": decision_record["description"],
            "original_timestamp": decision_record["timestamp"],
            "original_recommendation": decision_record["recommendation"],
            "review_timestamp": datetime.now().isoformat(),
            "days_since_decision": (
                datetime.now() - datetime.fromisoformat(decision_record["timestamp"])
            ).days,
            "questions": [
                "决策是否按预期执行？",
                "实际结果与预期有何差异？",
                "哪些因素被低估或高估？",
                "从这次决策中学到了什么？",
                "如果重来，会做出什么不同的选择？"
            ]
        }
        
        return review
    
    def get_decision_statistics(self) -> Dict[str, Any]:
        """获取决策统计"""
        
        if not self.decision_history:
            return {"message": "暂无决策历史"}
        
        # 计算决策频率
        if len(self.decision_history) >= 2:
            first_decision = datetime.fromisoformat(self.decision_history[0]["timestamp"])
            last_decision = datetime.fromisoformat(self.decision_history[-1]["timestamp"])
            days_between = (last_decision - first_decision).days
            
            if days_between > 0:
                decision_frequency = len(self.decision_history) / days_between
            else:
                decision_frequency = len(self.decision_history)
        else:
            decision_frequency = 0
        
        return {
            "total_decisions": len(self.decision_history),
            "decision_frequency": round(decision_frequency, 2),  # 每天决策数
            "system_state": self.system_state,
            "recent_decisions": [
                {
                    "decision_id": record["decision_id"],
                    "description": record["description"][:50],
                    "recommendation": record["recommendation"],
                    "timestamp": record["timestamp"]
                }
                for record in self.decision_history[-10:]
            ]
        }

# 全局实例
decision_system = DecisionSystem()

def demo():
    """演示决策系统"""
    
    print("="*60)
    print("🧠 决策系统演示")
    print("="*60)
    
    # 执行综合决策
    result = decision_system.make_decision(
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
    
    # 打印结果摘要
    print("\n📋 决策结果摘要:")
    print(f"决策ID: {result['decision_id']}")
    print(f"描述: {result['description'][:80]}...")
    
    if "recommendation" in result:
        rec = result["recommendation"]
        print(f"\n💡 综合推荐:")
        print(f"主要推荐: {rec.get('primary_recommendation', '无')}")
        print(f"信心程度: {rec.get('confidence', 0):.0%}")
        
        print(f"\n推理:")
        for reason in rec.get("reasoning", []):
            print(f"  • {reason}")
        
        print(f"\n备选方案:")
        for alt in rec.get("alternatives", [])[:3]:
            print(f"  • {alt['option']} (来源: {alt['source']})")
    
    # 获取系统状态
    status = decision_system.get_system_status()
    print(f"\n📊 系统状态:")
    print(f"总决策数: {status['system_state']['total_decisions']}")
    print(f"平均信心: {status['system_state']['average_confidence']:.0%}")
    
    # 获取决策统计
    stats = decision_system.get_decision_statistics()
    print(f"\n📈 决策统计:")
    print(f"决策频率: {stats.get('decision_frequency', 0):.2f} 次/天")

if __name__ == "__main__":
    demo()