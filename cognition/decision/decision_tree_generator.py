#!/usr/bin/env python3
"""
Hermes 决策树生成器 (Decision Tree Generator)
生成决策树，帮助可视化决策过程。
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import random

class NodeType(Enum):
    """节点类型"""
    DECISION = "decision"      # 决策节点
    CHANCE = "chance"          # 机会节点
    OUTCOME = "outcome"        # 结果节点
    ROOT = "root"              # 根节点

@dataclass
class TreeNode:
    """决策树节点"""
    node_id: str
    node_type: NodeType
    name: str
    description: str
    probability: float  # 对于机会节点
    value: float  # 对于结果节点
    children: List[str]  # 子节点ID列表
    parent: Optional[str] = None
    depth: int = 0
    is_leaf: bool = False

@dataclass
class DecisionTree:
    """决策树"""
    tree_id: str
    name: str
    description: str
    root_node_id: str
    nodes: Dict[str, TreeNode]
    created_time: str
    decision_path: List[str]  # 最优决策路径
    expected_value: float

class DecisionTreeGenerator:
    """决策树生成器主类"""
    
    def __init__(self):
        self.trees: Dict[str, DecisionTree] = {}
        
        # 决策树日志目录
        self.log_dir = Path("/root/.hermes/cognition/decision/tree_logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        print("[决策树生成器] 初始化完成")
    
    def generate_tree(self,
                     name: str,
                     description: str,
                     decision_options: List[Dict[str, Any]],
                     chance_scenarios: List[Dict[str, Any]] = None) -> DecisionTree:
        """生成决策树"""
        
        tree_id = f"tree_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 创建节点字典
        nodes = {}
        
        # 创建根节点
        root_node = TreeNode(
            node_id="root",
            node_type=NodeType.ROOT,
            name="决策起点",
            description="开始决策分析",
            probability=1.0,
            value=0.0,
            children=[],
            depth=0
        )
        nodes["root"] = root_node
        
        # 创建决策选项节点
        for i, option in enumerate(decision_options):
            option_id = f"decision_{i+1}"
            option_node = TreeNode(
                node_id=option_id,
                node_type=NodeType.DECISION,
                name=option.get("name", f"选项{i+1}"),
                description=option.get("description", ""),
                probability=1.0,
                value=0.0,
                children=[],
                parent="root",
                depth=1
            )
            nodes[option_id] = option_node
            root_node.children.append(option_id)
            
            # 如果有情景分析，为每个决策创建机会节点
            if chance_scenarios:
                for j, scenario in enumerate(chance_scenarios):
                    scenario_id = f"chance_{i+1}_{j+1}"
                    scenario_node = TreeNode(
                        node_id=scenario_id,
                        node_type=NodeType.CHANCE,
                        name=scenario.get("name", f"情景{j+1}"),
                        description=scenario.get("description", ""),
                        probability=scenario.get("probability", 0.5),
                        value=scenario.get("value", 0.0),
                        children=[],
                        parent=option_id,
                        depth=2
                    )
                    nodes[scenario_id] = scenario_node
                    option_node.children.append(scenario_id)
                    
                    # 创建结果节点
                    outcome_id = f"outcome_{i+1}_{j+1}"
                    outcome_value = scenario.get("value", 0.0)
                    outcome_node = TreeNode(
                        node_id=outcome_id,
                        node_type=NodeType.OUTCOME,
                        name=f"结果: {outcome_value}",
                        description=f"预期价值: {outcome_value}",
                        probability=1.0,
                        value=outcome_value,
                        children=[],
                        parent=scenario_id,
                        depth=3,
                        is_leaf=True
                    )
                    nodes[outcome_id] = outcome_node
                    scenario_node.children.append(outcome_id)
            else:
                # 如果没有情景分析，直接创建结果节点
                outcome_id = f"outcome_{i+1}"
                outcome_value = option.get("expected_value", 0.0)
                outcome_node = TreeNode(
                    node_id=outcome_id,
                    node_type=NodeType.OUTCOME,
                    name=f"预期结果: {outcome_value}",
                    description=f"预期价值: {outcome_value}",
                    probability=1.0,
                    value=outcome_value,
                    children=[],
                    parent=option_id,
                    depth=2,
                    is_leaf=True
                )
                nodes[outcome_id] = outcome_node
                option_node.children.append(outcome_id)
        
        # 计算最优路径
        decision_path, expected_value = self._calculate_optimal_path(nodes)
        
        # 创建决策树
        tree = DecisionTree(
            tree_id=tree_id,
            name=name,
            description=description,
            root_node_id="root",
            nodes=nodes,
            created_time=datetime.now().isoformat(),
            decision_path=decision_path,
            expected_value=expected_value
        )
        
        # 保存决策树
        self.trees[tree_id] = tree
        
        # 保存到文件
        self._save_tree(tree)
        
        # 打印决策树
        self._print_tree(tree)
        
        return tree
    
    def _calculate_optimal_path(self, nodes: Dict[str, TreeNode]) -> Tuple[List[str], float]:
        """计算最优决策路径"""
        
        # 找到所有结果节点
        outcome_nodes = [
            node for node in nodes.values()
            if node.node_type == NodeType.OUTCOME
        ]
        
        if not outcome_nodes:
            return [], 0.0
        
        # 计算每个决策选项的期望值
        decision_values = {}
        
        for node in nodes.values():
            if node.node_type == NodeType.DECISION:
                expected_value = self._calculate_expected_value(node, nodes)
                decision_values[node.node_id] = expected_value
        
        # 找到最优决策
        if not decision_values:
            return [], 0.0
        
        best_decision_id = max(decision_values.items(), key=lambda x: x[1])[0]
        best_value = decision_values[best_decision_id]
        
        # 构建最优路径
        path = ["root", best_decision_id]
        
        # 找到最优路径上的机会节点和结果节点
        best_decision_node = nodes[best_decision_id]
        if best_decision_node.children:
            # 找到价值最高的子节点
            best_child_id = None
            best_child_value = float('-inf')
            
            for child_id in best_decision_node.children:
                child_node = nodes[child_id]
                if child_node.node_type == NodeType.CHANCE:
                    # 对于机会节点，计算期望值
                    child_expected = self._calculate_expected_value(child_node, nodes)
                    if child_expected > best_child_value:
                        best_child_value = child_expected
                        best_child_id = child_id
                elif child_node.node_type == NodeType.OUTCOME:
                    # 对于结果节点，直接使用价值
                    if child_node.value > best_child_value:
                        best_child_value = child_node.value
                        best_child_id = child_id
            
            if best_child_id:
                path.append(best_child_id)
                
                # 如果是机会节点，继续找结果节点
                best_child_node = nodes[best_child_id]
                if best_child_node.children:
                    best_outcome_id = max(
                        best_child_node.children,
                        key=lambda x: nodes[x].value
                    )
                    path.append(best_outcome_id)
        
        return path, best_value
    
    def _calculate_expected_value(self, node: TreeNode, nodes: Dict[str, TreeNode]) -> float:
        """计算节点的期望值"""
        
        if node.node_type == NodeType.OUTCOME:
            return node.value
        
        if not node.children:
            return 0.0
        
        expected_value = 0.0
        
        for child_id in node.children:
            child_node = nodes[child_id]
            child_value = self._calculate_expected_value(child_node, nodes)
            expected_value += child_value * child_node.probability
        
        return expected_value
    
    def _save_tree(self, tree: DecisionTree):
        """保存决策树到文件"""
        
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"{tree.tree_id}.json"
        filepath = self.log_dir / date_str / filename
        
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # 转换为可序列化格式
        tree_data = {
            "tree_id": tree.tree_id,
            "name": tree.name,
            "description": tree.description,
            "root_node_id": tree.root_node_id,
            "created_time": tree.created_time,
            "decision_path": tree.decision_path,
            "expected_value": tree.expected_value,
            "nodes": {
                node_id: {
                    "node_id": node.node_id,
                    "node_type": node.node_type.value,
                    "name": node.name,
                    "description": node.description,
                    "probability": node.probability,
                    "value": node.value,
                    "children": node.children,
                    "parent": node.parent,
                    "depth": node.depth,
                    "is_leaf": node.is_leaf
                }
                for node_id, node in tree.nodes.items()
            }
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(tree_data, f, ensure_ascii=False, indent=2)
        
        print(f"[决策树生成器] 决策树已保存: {filepath}")
    
    def _print_tree(self, tree: DecisionTree):
        """打印决策树"""
        
        print("\n" + "="*60)
        print("🌳 决策树分析")
        print("="*60)
        print(f"树ID: {tree.tree_id}")
        print(f"名称: {tree.name}")
        print(f"描述: {tree.description}")
        print(f"创建时间: {tree.created_time}")
        
        print(f"\n节点统计:")
        node_types = {}
        for node in tree.nodes.values():
            node_type = node.node_type.value
            node_types[node_type] = node_types.get(node_type, 0) + 1
        
        for node_type, count in node_types.items():
            print(f"  • {node_type}: {count}")
        
        print(f"\n最优决策路径:")
        for i, node_id in enumerate(tree.decision_path):
            node = tree.nodes[node_id]
            indent = "  " * i
            print(f"{indent}→ {node.name}")
            if node.description:
                print(f"{indent}  {node.description}")
        
        print(f"\n预期价值: {tree.expected_value:.2f}")
        
        # 打印树结构
        print(f"\n树结构:")
        self._print_node(tree.nodes["root"], tree.nodes, indent=0)
        
        print("="*60)
    
    def _print_node(self, node: TreeNode, nodes: Dict[str, TreeNode], indent: int):
        """递归打印节点"""
        
        prefix = "  " * indent
        
        # 节点类型图标
        type_icons = {
            NodeType.ROOT: "🔴",
            NodeType.DECISION: "🟡",
            NodeType.CHANCE: "🟢",
            NodeType.OUTCOME: "🔵"
        }
        
        icon = type_icons.get(node.node_type, "⚪")
        
        print(f"{prefix}{icon} {node.name}")
        
        if node.description:
            print(f"{prefix}   {node.description}")
        
        if node.node_type == NodeType.CHANCE:
            print(f"{prefix}   概率: {node.probability:.2%}")
        
        if node.node_type == NodeType.OUTCOME:
            print(f"{prefix}   价值: {node.value:.2f}")
        
        # 递归打印子节点
        for child_id in node.children:
            child_node = nodes[child_id]
            self._print_node(child_node, nodes, indent + 1)
    
    def visualize_tree_mermaid(self, tree_id: str) -> str:
        """生成Mermaid格式的决策树可视化"""
        
        if tree_id not in self.trees:
            return "决策树不存在"
        
        tree = self.trees[tree_id]
        
        mermaid_lines = ["graph TD"]
        
        # 添加节点
        for node_id, node in tree.nodes.items():
            # 节点形状
            if node.node_type == NodeType.ROOT:
                shape = f'{node_id}[/{node.name}/]'
            elif node.node_type == NodeType.DECISION:
                shape = f'{node_id}[{node.name}]'
            elif node.node_type == NodeType.CHANCE:
                shape = f'{node_id}({node.name})'
            elif node.node_type == NodeType.OUTCOME:
                shape = f'{node_id}(({node.name}))'
            else:
                shape = f'{node_id}[{node.name}]'
            
            mermaid_lines.append(f"    {shape}")
        
        # 添加边
        for node_id, node in tree.nodes.items():
            for child_id in node.children:
                child_node = tree.nodes[child_id]
                
                # 边标签
                if child_node.node_type == NodeType.CHANCE:
                    label = f"|{child_node.probability:.0%}|"
                elif child_node.node_type == NodeType.OUTCOME:
                    label = f"|{child_node.value:.0f}|"
                else:
                    label = ""
                
                mermaid_lines.append(f"    {node_id} -->{label} {child_id}")
        
        # 高亮最优路径
        if tree.decision_path:
            path_edges = []
            for i in range(len(tree.decision_path) - 1):
                from_node = tree.decision_path[i]
                to_node = tree.decision_path[i+1]
                path_edges.append(f"{from_node} --> {to_node}")
            
            if path_edges:
                mermaid_lines.append("\n    %% 最优路径高亮")
                for edge in path_edges:
                    mermaid_lines.append(f"    linkStyle {len(mermaid_lines)-4} stroke:#ff0000,stroke-width:2px")
        
        return "\n".join(mermaid_lines)
    
    def get_tree_statistics(self, tree_id: str) -> Dict[str, Any]:
        """获取决策树统计信息"""
        
        if tree_id not in self.trees:
            return {"error": "决策树不存在"}
        
        tree = self.trees[tree_id]
        
        # 节点类型统计
        node_type_counts = {}
        for node in tree.nodes.values():
            node_type = node.node_type.value
            node_type_counts[node_type] = node_type_counts.get(node_type, 0) + 1
        
        # 深度统计
        max_depth = max(node.depth for node in tree.nodes.values())
        
        # 叶子节点统计
        leaf_nodes = [node for node in tree.nodes.values() if node.is_leaf]
        leaf_values = [node.value for node in leaf_nodes]
        
        return {
            "tree_id": tree.tree_id,
            "name": tree.name,
            "total_nodes": len(tree.nodes),
            "node_type_distribution": node_type_counts,
            "max_depth": max_depth,
            "leaf_node_count": len(leaf_nodes),
            "leaf_value_range": {
                "min": min(leaf_values) if leaf_values else 0,
                "max": max(leaf_values) if leaf_values else 0,
                "average": sum(leaf_values) / len(leaf_values) if leaf_values else 0
            },
            "optimal_path_length": len(tree.decision_path),
            "expected_value": tree.expected_value
        }
    
    def compare_alternatives(self, tree_id: str) -> Dict[str, Any]:
        """比较决策树中的备选方案"""
        
        if tree_id not in self.trees:
            return {"error": "决策树不存在"}
        
        tree = self.trees[tree_id]
        
        # 找到所有决策节点
        decision_nodes = [
            node for node in tree.nodes.values()
            if node.node_type == NodeType.DECISION
        ]
        
        alternatives = []
        
        for decision_node in decision_nodes:
            # 计算每个决策的期望值
            expected_value = self._calculate_expected_value(decision_node, tree.nodes)
            
            # 计算风险（价值的标准差）
            outcome_values = []
            self._collect_outcome_values(decision_node, tree.nodes, outcome_values)
            
            risk = 0.0
            if len(outcome_values) > 1:
                mean_value = sum(outcome_values) / len(outcome_values)
                variance = sum((v - mean_value) ** 2 for v in outcome_values) / len(outcome_values)
                risk = variance ** 0.5
            
            alternatives.append({
                "decision_id": decision_node.node_id,
                "name": decision_node.name,
                "description": decision_node.description,
                "expected_value": expected_value,
                "risk": risk,
                "is_optimal": decision_node.node_id in tree.decision_path
            })
        
        # 按期望值排序
        alternatives.sort(key=lambda x: x["expected_value"], reverse=True)
        
        return {
            "tree_id": tree.tree_id,
            "alternatives": alternatives,
            "optimal_alternative": next(
                (alt for alt in alternatives if alt["is_optimal"]),
                alternatives[0] if alternatives else None
            )
        }
    
    def _collect_outcome_values(self, 
                               node: TreeNode, 
                               nodes: Dict[str, TreeNode], 
                               values: List[float]):
        """递归收集结果节点的价值"""
        
        if node.node_type == NodeType.OUTCOME:
            values.append(node.value)
            return
        
        for child_id in node.children:
            child_node = nodes[child_id]
            self._collect_outcome_values(child_node, nodes, values)

# 全局实例
decision_tree_generator = DecisionTreeGenerator()

def demo():
    """演示决策树生成器"""
    
    print("="*60)
    print("🌳 决策树生成器演示")
    print("="*60)
    
    # 生成决策树
    tree = decision_tree_generator.generate_tree(
        name="AI功能开发决策",
        description="选择下一个要开发的AI功能模块",
        decision_options=[
            {
                "name": "自然语言处理",
                "description": "增强文本理解和生成能力",
                "expected_value": 8000
            },
            {
                "name": "计算机视觉",
                "description": "添加图像识别和处理能力",
                "expected_value": 7500
            },
            {
                "name": "强化学习",
                "description": "实现自主学习和决策能力",
                "expected_value": 9000
            }
        ],
        chance_scenarios=[
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
    )
    
    # 获取统计信息
    stats = decision_tree_generator.get_tree_statistics(tree.tree_id)
    print(f"\n决策树统计:")
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    
    # 比较备选方案
    comparison = decision_tree_generator.compare_alternatives(tree.tree_id)
    print(f"\n备选方案比较:")
    print(json.dumps(comparison, indent=2, ensure_ascii=False))
    
    # 生成Mermaid可视化
    mermaid_code = decision_tree_generator.visualize_tree_mermaid(tree.tree_id)
    print(f"\nMermaid可视化代码:")
    print(mermaid_code)
    
    # 保存Mermaid代码到文件
    mermaid_file = Path("/root/.hermes/cognition/decision/tree_logs") / f"{tree.tree_id}.mmd"
    with open(mermaid_file, 'w') as f:
        f.write(mermaid_code)
    
    print(f"\nMermaid代码已保存到: {mermaid_file}")

if __name__ == "__main__":
    demo()