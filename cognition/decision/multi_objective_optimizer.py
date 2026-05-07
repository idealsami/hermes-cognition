#!/usr/bin/env python3
"""
Hermes 多目标优化器 (Multi-Objective Optimizer)
处理多个冲突目标的决策问题。
"""

import json
import math
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import itertools

class OptimizationMethod(Enum):
    """优化方法"""
    WEIGHTED_SUM = "weighted_sum"          # 加权和法
    GOAL_PROGRAMMING = "goal_programming"  # 目标规划法
    PARETO_FRONTIER = "pareto_frontier"    # 帕累托前沿法
    TOPSIS = "topsis"                      # 逼近理想解排序法
    AHP = "ahp"                            # 层次分析法

@dataclass
class Objective:
    """优化目标"""
    objective_id: str
    name: str
    description: str
    weight: float  # 0.0 - 1.0
    target_value: float  # 目标值
    current_value: float  # 当前值
    is_benefit: bool  # True表示越大越好，False表示越小越好
    priority: int  # 优先级，1为最高

@dataclass
class Alternative:
    """备选方案"""
    alternative_id: str
    name: str
    description: str
    objective_values: Dict[str, float]  # objective_id -> value
    constraints_satisfied: bool = True
    feasibility_score: float = 1.0

@dataclass
class OptimizationResult:
    """优化结果"""
    optimization_id: str
    method: OptimizationMethod
    best_alternative: Alternative
    ranking: List[Tuple[str, float]]  # (alternative_id, score)
    pareto_front: List[str]  # 帕累托前沿的alternative_id
    sensitivity_analysis: Dict[str, Any]
    optimization_time: str

class MultiObjectiveOptimizer:
    """多目标优化器主类"""
    
    def __init__(self):
        self.optimization_history: List[OptimizationResult] = []
        
        # 优化日志目录
        self.log_dir = Path("/root/.hermes/cognition/decision/optimization_logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        print("[多目标优化器] 初始化完成")
    
    def optimize(self,
                objectives: List[Dict[str, Any]],
                alternatives: List[Dict[str, Any]],
                method: OptimizationMethod = OptimizationMethod.WEIGHTED_SUM,
                constraints: List[Callable] = None) -> OptimizationResult:
        """执行多目标优化"""
        
        optimization_id = f"optimization_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 转换目标格式
        obj_list = []
        for obj_desc in objectives:
            objective = Objective(
                objective_id=obj_desc.get("objective_id", f"obj_{len(obj_list)+1}"),
                name=obj_desc.get("name", ""),
                description=obj_desc.get("description", ""),
                weight=obj_desc.get("weight", 1.0/len(objectives)),
                target_value=obj_desc.get("target_value", 0.0),
                current_value=obj_desc.get("current_value", 0.0),
                is_benefit=obj_desc.get("is_benefit", True),
                priority=obj_desc.get("priority", 1)
            )
            obj_list.append(objective)
        
        # 转换备选方案格式
        alt_list = []
        for alt_desc in alternatives:
            alternative = Alternative(
                alternative_id=alt_desc.get("alternative_id", f"alt_{len(alt_list)+1}"),
                name=alt_desc.get("name", ""),
                description=alt_desc.get("description", ""),
                objective_values=alt_desc.get("objective_values", {})
            )
            
            # 检查约束条件
            if constraints:
                alternative.constraints_satisfied = all(
                    constraint(alternative) for constraint in constraints
                )
            
            alt_list.append(alternative)
        
        # 根据方法执行优化
        if method == OptimizationMethod.WEIGHTED_SUM:
            ranking = self._weighted_sum_optimization(obj_list, alt_list)
        elif method == OptimizationMethod.GOAL_PROGRAMMING:
            ranking = self._goal_programming_optimization(obj_list, alt_list)
        elif method == OptimizationMethod.PARETO_FRONTIER:
            ranking = self._pareto_frontier_optimization(obj_list, alt_list)
        elif method == OptimizationMethod.TOPSIS:
            ranking = self._topsis_optimization(obj_list, alt_list)
        elif method == OptimizationMethod.AHP:
            ranking = self._ahp_optimization(obj_list, alt_list)
        else:
            ranking = self._weighted_sum_optimization(obj_list, alt_list)
        
        # 找到最佳方案
        best_alt_id = ranking[0][0] if ranking else None
        best_alternative = next(
            (alt for alt in alt_list if alt.alternative_id == best_alt_id),
            alt_list[0] if alt_list else None
        )
        
        # 计算帕累托前沿
        pareto_front = self._calculate_pareto_front(obj_list, alt_list)
        
        # 敏感性分析
        sensitivity = self._sensitivity_analysis(obj_list, alt_list, ranking)
        
        # 创建优化结果
        result = OptimizationResult(
            optimization_id=optimization_id,
            method=method,
            best_alternative=best_alternative,
            ranking=ranking,
            pareto_front=pareto_front,
            sensitivity_analysis=sensitivity,
            optimization_time=datetime.now().isoformat()
        )
        
        # 保存到历史
        self.optimization_history.append(result)
        
        # 保存优化日志
        self._save_optimization_log(result, obj_list, alt_list)
        
        # 打印优化报告
        self._print_optimization_report(result, obj_list, alt_list)
        
        return result
    
    def _weighted_sum_optimization(self,
                                  objectives: List[Objective],
                                  alternatives: List[Alternative]) -> List[Tuple[str, float]]:
        """加权和法优化"""
        
        scores = []
        
        for alt in alternatives:
            total_score = 0.0
            
            for obj in objectives:
                value = alt.objective_values.get(obj.objective_id, 0.0)
                
                # 归一化处理
                if obj.is_benefit:
                    # 越大越好
                    normalized = value / obj.target_value if obj.target_value != 0 else 0
                else:
                    # 越小越好
                    normalized = obj.target_value / value if value != 0 else 0
                
                # 应用权重
                weighted_score = normalized * obj.weight
                total_score += weighted_score
            
            # 检查约束
            if not alt.constraints_satisfied:
                total_score *= 0.5  # 约束不满足则减半
            
            scores.append((alt.alternative_id, total_score))
        
        # 按分数降序排序
        scores.sort(key=lambda x: x[1], reverse=True)
        
        return scores
    
    def _goal_programming_optimization(self,
                                      objectives: List[Objective],
                                      alternatives: List[Alternative]) -> List[Tuple[str, float]]:
        """目标规划法优化"""
        
        scores = []
        
        for alt in alternatives:
            total_deviation = 0.0
            
            for obj in objectives:
                value = alt.objective_values.get(obj.objective_id, 0.0)
                
                # 计算与目标的偏差
                if obj.is_benefit:
                    # 越大越好，负偏差表示不足
                    deviation = max(0, obj.target_value - value)
                else:
                    # 越小越好，正偏差表示超出
                    deviation = max(0, value - obj.target_value)
                
                # 按优先级加权（优先级越高，权重越大）
                priority_weight = 1.0 / obj.priority
                weighted_deviation = deviation * priority_weight
                
                total_deviation += weighted_deviation
            
            # 分数 = 1 / (1 + 总偏差)
            score = 1.0 / (1.0 + total_deviation)
            
            # 检查约束
            if not alt.constraints_satisfied:
                score *= 0.5
            
            scores.append((alt.alternative_id, score))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        
        return scores
    
    def _pareto_frontier_optimization(self,
                                     objectives: List[Objective],
                                     alternatives: List[Alternative]) -> List[Tuple[str, float]]:
        """帕累托前沿法优化"""
        
        # 首先计算帕累托前沿
        pareto_front = self._calculate_pareto_front(objectives, alternatives)
        
        # 为帕累托前沿上的方案分配高分
        scores = []
        
        for alt in alternatives:
            if alt.alternative_id in pareto_front:
                # 帕累托前沿上的方案
                score = 1.0
            else:
                # 计算到帕累托前沿的距离（简化处理）
                score = 0.5
            
            # 检查约束
            if not alt.constraints_satisfied:
                score *= 0.3
            
            scores.append((alt.alternative_id, score))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        
        return scores
    
    def _calculate_pareto_front(self,
                               objectives: List[Objective],
                               alternatives: List[Alternative]) -> List[str]:
        """计算帕累托前沿"""
        
        pareto_front = []
        
        for alt in alternatives:
            is_dominated = False
            
            for other_alt in alternatives:
                if alt.alternative_id == other_alt.alternative_id:
                    continue
                
                # 检查是否被支配
                dominated = True
                at_least_one_better = False
                
                for obj in objectives:
                    alt_value = alt.objective_values.get(obj.objective_id, 0.0)
                    other_value = other_alt.objective_values.get(obj.objective_id, 0.0)
                    
                    if obj.is_benefit:
                        # 越大越好
                        if other_value < alt_value:
                            dominated = False
                            break
                        elif other_value > alt_value:
                            at_least_one_better = True
                    else:
                        # 越小越好
                        if other_value > alt_value:
                            dominated = False
                            break
                        elif other_value < alt_value:
                            at_least_one_better = True
                
                if dominated and at_least_one_better:
                    is_dominated = True
                    break
            
            if not is_dominated:
                pareto_front.append(alt.alternative_id)
        
        return pareto_front
    
    def _topsis_optimization(self,
                            objectives: List[Objective],
                            alternatives: List[Alternative]) -> List[Tuple[str, float]]:
        """逼近理想解排序法（TOPSIS）"""
        
        if not alternatives:
            return []
        
        # 步骤1: 构建决策矩阵
        decision_matrix = []
        for alt in alternatives:
            row = []
            for obj in objectives:
                value = alt.objective_values.get(obj.objective_id, 0.0)
                row.append(value)
            decision_matrix.append(row)
        
        # 步骤2: 归一化处理
        normalized_matrix = []
        for j in range(len(objectives)):
            col_values = [decision_matrix[i][j] for i in range(len(alternatives))]
            norm = math.sqrt(sum(v**2 for v in col_values))
            
            normalized_col = []
            for i in range(len(alternatives)):
                if norm != 0:
                    normalized_col.append(decision_matrix[i][j] / norm)
                else:
                    normalized_col.append(0)
            
            normalized_matrix.append(normalized_col)
        
        # 步骤3: 加权归一化矩阵
        weighted_matrix = []
        for i in range(len(alternatives)):
            row = []
            for j in range(len(objectives)):
                weight = objectives[j].weight
                row.append(normalized_matrix[j][i] * weight)
            weighted_matrix.append(row)
        
        # 步骤4: 确定理想解和负理想解
        ideal_solution = []
        negative_ideal_solution = []
        
        for j in range(len(objectives)):
            col_values = [weighted_matrix[i][j] for i in range(len(alternatives))]
            
            if objectives[j].is_benefit:
                # 越大越好
                ideal_solution.append(max(col_values))
                negative_ideal_solution.append(min(col_values))
            else:
                # 越小越好
                ideal_solution.append(min(col_values))
                negative_ideal_solution.append(max(col_values))
        
        # 步骤5: 计算距离
        scores = []
        for i in range(len(alternatives)):
            # 到理想解的距离
            dist_to_ideal = math.sqrt(
                sum((weighted_matrix[i][j] - ideal_solution[j])**2 
                    for j in range(len(objectives)))
            )
            
            # 到负理想解的距离
            dist_to_negative = math.sqrt(
                sum((weighted_matrix[i][j] - negative_ideal_solution[j])**2 
                    for j in range(len(objectives)))
            )
            
            # 计算相对接近度
            if dist_to_ideal + dist_to_negative != 0:
                closeness = dist_to_negative / (dist_to_ideal + dist_to_negative)
            else:
                closeness = 0
            
            alt_id = alternatives[i].alternative_id
            
            # 检查约束
            if not alternatives[i].constraints_satisfied:
                closeness *= 0.5
            
            scores.append((alt_id, closeness))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        
        return scores
    
    def _ahp_optimization(self,
                         objectives: List[Objective],
                         alternatives: List[Alternative]) -> List[Tuple[str, float]]:
        """层次分析法（AHP）优化"""
        
        # 简化的AHP实现
        # 实际应用中需要构建完整的判断矩阵
        
        # 使用权重作为AHP的简化版本
        scores = []
        
        for alt in alternatives:
            total_score = 0.0
            
            for obj in objectives:
                value = alt.objective_values.get(obj.objective_id, 0.0)
                
                # 简单的加权得分
                if obj.is_benefit:
                    normalized = value / obj.target_value if obj.target_value != 0 else 0
                else:
                    normalized = obj.target_value / value if value != 0 else 0
                
                weighted_score = normalized * obj.weight
                total_score += weighted_score
            
            # 检查约束
            if not alt.constraints_satisfied:
                total_score *= 0.5
            
            scores.append((alt.alternative_id, total_score))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        
        return scores
    
    def _sensitivity_analysis(self,
                             objectives: List[Objective],
                             alternatives: List[Alternative],
                             ranking: List[Tuple[str, float]]) -> Dict[str, Any]:
        """敏感性分析"""
        
        analysis = {
            "weight_sensitivity": {},
            "value_sensitivity": {},
            "robustness_score": 0.0
        }
        
        # 权重敏感性分析
        for obj in objectives:
            # 测试权重变化±20%
            original_weight = obj.weight
            test_weights = [original_weight * 0.8, original_weight * 1.2]
            
            ranking_changes = []
            for test_weight in test_weights:
                # 临时修改权重
                obj.weight = test_weight
                
                # 重新计算排名
                new_ranking = self._weighted_sum_optimization(objectives, alternatives)
                
                # 检查排名变化
                if new_ranking != ranking:
                    ranking_changes.append(True)
                else:
                    ranking_changes.append(False)
                
                # 恢复原始权重
                obj.weight = original_weight
            
            analysis["weight_sensitivity"][obj.objective_id] = {
                "original_weight": original_weight,
                "ranking_changed": any(ranking_changes),
                "sensitivity": "high" if any(ranking_changes) else "low"
            }
        
        # 值敏感性分析
        for alt in alternatives[:3]:  # 只分析前3个方案
            for obj in objectives:
                original_value = alt.objective_values.get(obj.objective_id, 0.0)
                
                # 测试值变化±10%
                test_values = [original_value * 0.9, original_value * 1.1]
                
                ranking_changes = []
                for test_value in test_values:
                    # 临时修改值
                    alt.objective_values[obj.objective_id] = test_value
                    
                    # 重新计算排名
                    new_ranking = self._weighted_sum_optimization(objectives, alternatives)
                    
                    # 检查排名变化
                    if new_ranking != ranking:
                        ranking_changes.append(True)
                    else:
                        ranking_changes.append(False)
                    
                    # 恢复原始值
                    alt.objective_values[obj.objective_id] = original_value
                
                if alt.alternative_id not in analysis["value_sensitivity"]:
                    analysis["value_sensitivity"][alt.alternative_id] = {}
                
                analysis["value_sensitivity"][alt.alternative_id][obj.objective_id] = {
                    "original_value": original_value,
                    "ranking_changed": any(ranking_changes),
                    "sensitivity": "high" if any(ranking_changes) else "low"
                }
        
        # 计算鲁棒性分数
        total_tests = len(objectives) + len(alternatives[:3]) * len(objectives)
        sensitive_tests = sum(
            1 for obj_id, data in analysis["weight_sensitivity"].items()
            if data["ranking_changed"]
        )
        
        for alt_id, obj_data in analysis["value_sensitivity"].items():
            for obj_id, data in obj_data.items():
                if data["ranking_changed"]:
                    sensitive_tests += 1
        
        analysis["robustness_score"] = 1.0 - (sensitive_tests / total_tests) if total_tests > 0 else 1.0
        
        return analysis
    
    def _save_optimization_log(self,
                              result: OptimizationResult,
                              objectives: List[Objective],
                              alternatives: List[Alternative]):
        """保存优化日志"""
        
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"{result.optimization_id}.json"
        filepath = self.log_dir / date_str / filename
        
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        log_data = {
            "optimization_id": result.optimization_id,
            "method": result.method.value,
            "best_alternative": {
                "id": result.best_alternative.alternative_id,
                "name": result.best_alternative.name
            } if result.best_alternative else None,
            "ranking": result.ranking,
            "pareto_front": result.pareto_front,
            "sensitivity_analysis": result.sensitivity_analysis,
            "optimization_time": result.optimization_time,
            "objectives": [
                {
                    "id": obj.objective_id,
                    "name": obj.name,
                    "weight": obj.weight,
                    "target_value": obj.target_value,
                    "is_benefit": obj.is_benefit
                }
                for obj in objectives
            ],
            "alternatives": [
                {
                    "id": alt.alternative_id,
                    "name": alt.name,
                    "objective_values": alt.objective_values
                }
                for alt in alternatives
            ]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)
        
        print(f"[多目标优化器] 优化日志已保存: {filepath}")
    
    def _print_optimization_report(self,
                                  result: OptimizationResult,
                                  objectives: List[Objective],
                                  alternatives: List[Alternative]):
        """打印优化报告"""
        
        print("\n" + "="*60)
        print("🎯 多目标优化报告")
        print("="*60)
        print(f"优化ID: {result.optimization_id}")
        print(f"优化方法: {result.method.value}")
        
        print(f"\n目标 ({len(objectives)}):")
        for obj in objectives:
            direction = "↑" if obj.is_benefit else "↓"
            print(f"  • {obj.name} (权重: {obj.weight:.2f}, 目标: {direction}{obj.target_value})")
        
        print(f"\n备选方案 ({len(alternatives)}):")
        for alt in alternatives:
            print(f"  • {alt.name}")
            for obj in objectives:
                value = alt.objective_values.get(obj.objective_id, 0.0)
                print(f"    {obj.name}: {value}")
        
        print(f"\n优化结果:")
        print(f"最佳方案: {result.best_alternative.name if result.best_alternative else '无'}")
        
        print(f"\n排名:")
        for i, (alt_id, score) in enumerate(result.ranking[:5], 1):
            alt = next((a for a in alternatives if a.alternative_id == alt_id), None)
            name = alt.name if alt else alt_id
            print(f"  {i}. {name}: {score:.3f}")
        
        print(f"\n帕累托前沿: {len(result.pareto_front)}个方案")
        
        print(f"\n鲁棒性分数: {result.sensitivity_analysis.get('robustness_score', 0):.2%}")
        
        print("="*60)
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """获取优化统计"""
        
        if not self.optimization_history:
            return {"message": "暂无优化历史"}
        
        # 统计优化方法使用情况
        method_counts = {}
        for opt in self.optimization_history:
            method = opt.method.value
            method_counts[method] = method_counts.get(method, 0) + 1
        
        # 计算平均鲁棒性
        robustness_scores = [
            opt.sensitivity_analysis.get("robustness_score", 0)
            for opt in self.optimization_history
        ]
        avg_robustness = sum(robustness_scores) / len(robustness_scores)
        
        return {
            "total_optimizations": len(self.optimization_history),
            "method_distribution": method_counts,
            "average_robustness": round(avg_robustness, 3),
            "recent_optimizations": [
                {
                    "optimization_id": opt.optimization_id,
                    "method": opt.method.value,
                    "best_alternative": opt.best_alternative.name if opt.best_alternative else None,
                    "optimization_time": opt.optimization_time
                }
                for opt in self.optimization_history[-5:]
            ]
        }

# 全局实例
multi_objective_optimizer = MultiObjectiveOptimizer()

def demo():
    """演示多目标优化器"""
    
    print("="*60)
    print("🎯 多目标优化器演示")
    print("="*60)
    
    # 定义目标
    objectives = [
        {
            "objective_id": "cost",
            "name": "成本",
            "description": "项目总成本",
            "weight": 0.3,
            "target_value": 10000,
            "current_value": 15000,
            "is_benefit": False,  # 越小越好
            "priority": 1
        },
        {
            "objective_id": "time",
            "name": "时间",
            "description": "项目完成时间",
            "weight": 0.25,
            "target_value": 30,
            "current_value": 45,
            "is_benefit": False,  # 越小越好
            "priority": 2
        },
        {
            "objective_id": "quality",
            "name": "质量",
            "description": "产品质量评分",
            "weight": 0.35,
            "target_value": 95,
            "current_value": 80,
            "is_benefit": True,  # 越大越好
            "priority": 1
        },
        {
            "objective_id": "risk",
            "name": "风险",
            "description": "项目风险等级",
            "weight": 0.1,
            "target_value": 2,
            "current_value": 3,
            "is_benefit": False,  # 越小越好
            "priority": 3
        }
    ]
    
    # 定义备选方案
    alternatives = [
        {
            "alternative_id": "alt_1",
            "name": "方案A: 快速开发",
            "description": "快速开发，成本低，但质量一般",
            "objective_values": {
                "cost": 8000,
                "time": 25,
                "quality": 75,
                "risk": 4
            }
        },
        {
            "alternative_id": "alt_2",
            "name": "方案B: 平衡方案",
            "description": "平衡成本、时间和质量",
            "objective_values": {
                "cost": 12000,
                "time": 35,
                "quality": 90,
                "risk": 2
            }
        },
        {
            "alternative_id": "alt_3",
            "name": "方案C: 高质量方案",
            "description": "追求最高质量，成本高，时间长",
            "objective_values": {
                "cost": 18000,
                "time": 50,
                "quality": 98,
                "risk": 1
            }
        },
        {
            "alternative_id": "alt_4",
            "name": "方案D: 创新方案",
            "description": "采用新技术，风险高但潜力大",
            "objective_values": {
                "cost": 15000,
                "time": 40,
                "quality": 85,
                "risk": 5
            }
        }
    ]
    
    # 使用不同的优化方法
    methods = [
        OptimizationMethod.WEIGHTED_SUM,
        OptimizationMethod.GOAL_PROGRAMMING,
        OptimizationMethod.TOPSIS
    ]
    
    for method in methods:
        print(f"\n{'='*60}")
        print(f"使用 {method.value} 方法优化")
        print('='*60)
        
        result = multi_objective_optimizer.optimize(
            objectives=objectives,
            alternatives=alternatives,
            method=method
        )
    
    # 获取优化统计
    stats = multi_objective_optimizer.get_optimization_stats()
    print(f"\n优化统计:")
    print(json.dumps(stats, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    demo()