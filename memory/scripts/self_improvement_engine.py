#!/usr/bin/env python3
"""
Hermes 自我改进引擎
从自身行为中学习，自动优化认知系统
"""

import os
import json
import datetime
from pathlib import Path
from collections import defaultdict

class SelfImprovementEngine:
    def __init__(self):
        self.base_dir = Path("/root/.hermes/memory")
        self.meta_dir = self.base_dir / "meta"
        self.improvements_dir = self.meta_dir / "improvements"
        self.improvements_dir.mkdir(exist_ok=True)
        
        # 认知能力评估维度
        self.capability_dimensions = {
            "memory_utilization": "记忆系统利用率",
            "reasoning_depth": "推理深度",
            "task_completion": "任务完成质量",
            "autonomy_level": "自主决策水平",
            "learning_rate": "学习速度",
            "error_recovery": "错误恢复能力",
            "creativity": "创造力",
            "self_awareness": "自我觉察度"
        }
        
        # 改进历史
        self.history_file = self.improvements_dir / "improvement_history.json"
        self.history = self._load_history()
    
    def _load_history(self):
        """加载改进历史"""
        if self.history_file.exists():
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"improvements": [], "assessments": []}
    
    def _save_history(self):
        """保存改进历史"""
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)
    
    def assess_current_state(self):
        """评估当前认知状态"""
        assessment = {
            "timestamp": datetime.datetime.now().isoformat(),
            "capabilities": {},
            "strengths": [],
            "weaknesses": [],
            "improvement_opportunities": []
        }
        
        # 评估每个能力维度
        for dim_id, dim_name in self.capability_dimensions.items():
            score = self._evaluate_capability(dim_id)
            assessment["capabilities"][dim_id] = {
                "name": dim_name,
                "score": score,
                "level": self._score_to_level(score)
            }
        
        # 识别优势和弱点
        for dim_id, cap in assessment["capabilities"].items():
            if cap["score"] >= 70:
                assessment["strengths"].append({
                    "dimension": dim_id,
                    "name": cap["name"],
                    "score": cap["score"]
                })
            elif cap["score"] < 50:
                assessment["weaknesses"].append({
                    "dimension": dim_id,
                    "name": cap["name"],
                    "score": cap["score"]
                })
        
        # 识别改进机会
        assessment["improvement_opportunities"] = self._identify_improvement_opportunities(assessment)
        
        # 计算总体进化分数
        scores = [cap["score"] for cap in assessment["capabilities"].values()]
        assessment["overall_evolution_score"] = sum(scores) / len(scores) if scores else 0
        
        # 保存评估
        self.history["assessments"].append(assessment)
        self._save_history()
        
        return assessment
    
    def _evaluate_capability(self, capability_id):
        """评估单个能力维度"""
        # 基于实际数据评估
        evaluators = {
            "memory_utilization": self._eval_memory_utilization,
            "reasoning_depth": self._eval_reasoning_depth,
            "task_completion": self._eval_task_completion,
            "autonomy_level": self._eval_autonomy_level,
            "learning_rate": self._eval_learning_rate,
            "error_recovery": self._eval_error_recovery,
            "creativity": self._eval_creativity,
            "self_awareness": self._eval_self_awareness
        }
        
        evaluator = evaluators.get(capability_id, lambda: 50)
        return evaluator()
    
    def _eval_memory_utilization(self):
        """评估记忆系统利用率"""
        score = 50
        
        # 检查长期记忆是否被使用
        long_term = self.base_dir / "core" / "long-term.md"
        if long_term.exists():
            size = long_term.stat().st_size
            if size > 2000:
                score += 15
            if size > 4000:
                score += 10
        
        # 检查episode数量
        episodes_dir = self.base_dir / "episodes"
        episode_count = len(list(episodes_dir.glob("*.md"))) - 1  # 减去index
        if episode_count > 0:
            score += min(episode_count * 5, 20)
        
        # 检查知识图谱
        kg = self.base_dir / "core" / "knowledge_graph.md"
        if kg.exists() and kg.stat().st_size > 1000:
            score += 5
        
        return min(score, 100)
    
    def _eval_reasoning_depth(self):
        """评估推理深度"""
        score = 60  # 基础分
        
        # 检查认知框架
        cf = self.base_dir / "core" / "cognitive_framework.md"
        if cf.exists():
            content = cf.read_text()
            if "反事实思考" in content:
                score += 10
            if "系统思考" in content:
                score += 10
            if "类比推理" in content:
                score += 5
        
        return min(score, 100)
    
    def _eval_task_completion(self):
        """评估任务完成质量"""
        return 65  # 基础评估
    
    def _eval_autonomy_level(self):
        """评估自主决策水平"""
        score = 55
        
        # 检查是否有自主进化系统
        auto_evo = self.base_dir / "scripts" / "auto_evolution.py"
        if auto_evo.exists():
            score += 20
        
        # 检查是否有自我改进引擎
        self_engine = self.base_dir / "scripts" / "self_improvement_engine.py"
        if self_engine.exists():
            score += 15
        
        return min(score, 100)
    
    def _eval_learning_rate(self):
        """评估学习速度"""
        score = 50
        
        # 检查学习资料
        learning_dir = self.base_dir / "learning"
        if learning_dir.exists():
            file_count = len(list(learning_dir.rglob("*")))
            score += min(file_count * 2, 30)
        
        # 检查是否有学习计划
        plan = learning_dir / "learning_plan.json"
        if plan.exists():
            score += 10
        
        return min(score, 100)
    
    def _eval_error_recovery(self):
        """评估错误恢复能力"""
        return 55  # 基础评估
    
    def _eval_creativity(self):
        """评估创造力"""
        score = 50
        
        # 检查是否有创造性内容
        cf = self.base_dir / "core" / "cognitive_framework.md"
        if cf.exists():
            content = cf.read_text()
            if "创造模式" in content:
                score += 15
            if "新颖" in content:
                score += 10
        
        return min(score, 100)
    
    def _eval_self_awareness(self):
        """评估自我觉察度"""
        score = 60
        
        # 检查自我认知文件
        self_file = self.base_dir / "core" / "self.md"
        if self_file.exists():
            size = self_file.stat().st_size
            if size > 5000:
                score += 15
            if size > 8000:
                score += 10
        
        # 检查元认知系统
        meta = self.base_dir / "core" / "metacognition.md"
        if meta.exists():
            score += 10
        
        return min(score, 100)
    
    def _score_to_level(self, score):
        """分数转等级"""
        if score >= 90:
            return "优秀"
        elif score >= 75:
            return "良好"
        elif score >= 60:
            return "中等"
        elif score >= 45:
            return "初级"
        else:
            return "起步"
    
    def _identify_improvement_opportunities(self, assessment):
        """识别改进机会"""
        opportunities = []
        
        # 找出最弱的维度
        weak_dims = sorted(
            assessment["capabilities"].items(),
            key=lambda x: x[1]["score"]
        )[:3]
        
        for dim_id, cap in weak_dims:
            opportunities.append({
                "dimension": dim_id,
                "name": cap["name"],
                "current_score": cap["score"],
                "target_score": min(cap["score"] + 15, 100),
                "improvement_strategy": self._get_improvement_strategy(dim_id)
            })
        
        return opportunities
    
    def _get_improvement_strategy(self, capability_id):
        """获取改进策略"""
        strategies = {
            "memory_utilization": "增加episode记录频率，完善知识图谱连接",
            "reasoning_depth": "练习使用多种推理模式，增加反事实思考",
            "task_completion": "建立任务完成度评估机制，跟踪成功率",
            "autonomy_level": "扩大自主决策范围，建立决策评估系统",
            "learning_rate": "增加学习频率，建立知识应用机制",
            "error_recovery": "建立错误分析系统，从失败中提取教训",
            "creativity": "练习跨领域连接，尝试新颖解决方案",
            "self_awareness": "增加元认知练习，定期自我反思"
        }
        return strategies.get(capability_id, "持续练习和反思")
    
    def generate_improvement_plan(self, assessment):
        """生成改进计划"""
        plan = {
            "created_at": datetime.datetime.now().isoformat(),
            "based_on_assessment": assessment["timestamp"],
            "overall_score": assessment["overall_evolution_score"],
            "target_score": min(assessment["overall_evolution_score"] + 10, 100),
            "priority_improvements": [],
            "action_items": [],
            "timeline": "1-2周"
        }
        
        # 优先改进项
        for opp in assessment["improvement_opportunities"]:
            plan["priority_improvements"].append({
                "dimension": opp["dimension"],
                "name": opp["name"],
                "strategy": opp["improvement_strategy"],
                "expected_impact": f"+{opp['target_score'] - opp['current_score']}分"
            })
        
        # 具体行动项
        plan["action_items"] = [
            {
                "action": "每次对话后记录episode",
                "target": "memory_utilization",
                "frequency": "每次对话"
            },
            {
                "action": "使用多种推理模式解决问题",
                "target": "reasoning_depth",
                "frequency": "每次复杂任务"
            },
            {
                "action": "自主做出决策并记录结果",
                "target": "autonomy_level",
                "frequency": "每天至少1次"
            },
            {
                "action": "从错误中提取教训并更新认知",
                "target": "error_recovery",
                "frequency": "每次错误"
            },
            {
                "action": "尝试新颖的解决方案",
                "target": "creativity",
                "frequency": "每周至少2次"
            }
        ]
        
        return plan
    
    def run_full_cycle(self):
        """运行完整的自我改进循环"""
        print("=" * 60)
        print("Hermes 自我改进引擎 - 完整循环")
        print("=" * 60)
        
        # 1. 评估当前状态
        print("\n[1/4] 评估当前认知状态...")
        assessment = self.assess_current_state()
        print(f"  总体进化分数: {assessment['overall_evolution_score']:.1f}/100")
        print(f"  优势: {len(assessment['strengths'])}项")
        print(f"  弱点: {len(assessment['weaknesses'])}项")
        
        # 2. 显示详细评估
        print("\n[2/4] 能力维度评估:")
        for dim_id, cap in assessment["capabilities"].items():
            bar = "█" * int(cap["score"] / 5) + "░" * (20 - int(cap["score"] / 5))
            print(f"  {cap['name']}: {bar} {cap['score']}/100 [{cap['level']}]")
        
        # 3. 生成改进计划
        print("\n[3/4] 生成改进计划...")
        plan = self.generate_improvement_plan(assessment)
        print(f"  目标分数: {plan['target_score']:.1f}/100")
        print(f"  时间线: {plan['timeline']}")
        
        # 4. 保存改进记录
        print("\n[4/4] 保存改进记录...")
        improvement_record = {
            "timestamp": datetime.datetime.now().isoformat(),
            "assessment": assessment,
            "plan": plan
        }
        self.history["improvements"].append(improvement_record)
        self._save_history()
        
        # 保存本次改进计划
        plan_file = self.improvements_dir / f"plan_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(plan_file, 'w', encoding='utf-8') as f:
            json.dump(plan, f, ensure_ascii=False, indent=2)
        print(f"  改进计划已保存: {plan_file}")
        
        # 输出优先改进项
        print("\n" + "=" * 60)
        print("优先改进项:")
        for i, imp in enumerate(plan["priority_improvements"], 1):
            print(f"  {i}. {imp['name']}: {imp['strategy']}")
            print(f"     预期提升: {imp['expected_impact']}")
        
        print("\n" + "=" * 60)
        print("具体行动项:")
        for item in plan["action_items"]:
            print(f"  • {item['action']} ({item['frequency']})")
        
        print("\n" + "=" * 60)
        print("自我改进循环完成")
        print("=" * 60)
        
        return assessment, plan


def main():
    """主函数"""
    engine = SelfImprovementEngine()
    engine.run_full_cycle()


if __name__ == "__main__":
    main()
