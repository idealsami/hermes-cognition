#!/usr/bin/env python3
"""
Hermes 知识图谱系统
结构化知识网络，支持概念关联、关系推理、知识整合
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Set, Tuple, Optional, Any
from collections import defaultdict
import networkx as nx
import hashlib

class KnowledgeGraph:
    """Hermes知识图谱核心类"""
    
    def __init__(self, storage_path: str = "/root/.hermes/cognition/knowledge_graph"):
        self.storage_path = storage_path
        self.graph_path = os.path.join(storage_path, "graph.json")
        self.history_path = os.path.join(storage_path, "history.jsonl")
        
        # 使用networkx图结构
        self.graph = nx.DiGraph()
        
        # 概念类型定义
        self.concept_types = {
            "entity": "实体（人物、组织、产品等）",
            "concept": "抽象概念",
            "event": "事件",
            "skill": "技能/能力",
            "tool": "工具/系统",
            "preference": "偏好/习惯",
            "fact": "事实/知识",
            "pattern": "模式/规律"
        }
        
        # 关系类型定义
        self.relation_types = {
            "is_a": "是一种（类别关系）",
            "part_of": "是...的一部分",
            "has_property": "具有属性",
            "related_to": "相关联",
            "causes": "导致/引起",
            "enables": "使能/支持",
            "requires": "需要/依赖",
            "similar_to": "相似于",
            "opposite_of": "相反于",
            "instance_of": "是...的实例",
            "learned_from": "从...学习",
            "used_for": "用于",
            "belongs_to": "属于"
        }
        
        # 加载现有图谱
        self._load_graph()
    
    def _load_graph(self):
        """加载图谱数据"""
        if os.path.exists(self.graph_path):
            try:
                with open(self.graph_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 恢复节点
                    for node_id, attrs in data.get("nodes", {}).items():
                        self.graph.add_node(node_id, **attrs)
                    # 恢复边
                    for edge in data.get("edges", []):
                        self.graph.add_edge(edge["source"], edge["target"], **edge["attrs"])
            except Exception as e:
                self._log_history(f"加载图谱失败: {e}")
    
    def _save_graph(self):
        """保存图谱数据"""
        data = {
            "nodes": {node: dict(attrs) for node, attrs in self.graph.nodes(data=True)},
            "edges": [
                {
                    "source": u,
                    "target": v,
                    "attrs": dict(attrs)
                }
                for u, v, attrs in self.graph.edges(data=True)
            ],
            "updated_at": datetime.now().isoformat()
        }
        with open(self.graph_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _log_history(self, message: str):
        """记录历史"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "message": message
        }
        with open(self.history_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    def _generate_id(self, name: str) -> str:
        """生成概念ID"""
        return hashlib.md5(name.encode()).hexdigest()[:12]
    
    # ==================== 概念管理 ====================
    
    def add_concept(self, name: str, concept_type: str = "concept", 
                    description: str = "", properties: Dict = None) -> str:
        """添加概念节点"""
        node_id = self._generate_id(name)
        
        if node_id in self.graph:
            # 更新现有节点
            if description:
                self.graph.nodes[node_id]["description"] = description
            if properties:
                self.graph.nodes[node_id]["properties"].update(properties)
        else:
            # 创建新节点
            self.graph.add_node(node_id, 
                name=name,
                type=concept_type,
                description=description,
                properties=properties or {},
                created_at=datetime.now().isoformat(),
                access_count=0,
                last_accessed=datetime.now().isoformat()
            )
            self._log_history(f"添加概念: {name} ({concept_type})")
        
        self._save_graph()
        return node_id
    
    def get_concept(self, identifier: str) -> Optional[Dict]:
        """获取概念信息（支持ID或名称）"""
        # 先尝试ID
        if identifier in self.graph:
            self.graph.nodes[identifier]["access_count"] = self.graph.nodes[identifier].get("access_count", 0) + 1
            self.graph.nodes[identifier]["last_accessed"] = datetime.now().isoformat()
            return {"id": identifier, **dict(self.graph.nodes[identifier])}
        
        # 再尝试名称
        for node_id, attrs in self.graph.nodes(data=True):
            if attrs.get("name") == identifier:
                self.graph.nodes[node_id]["access_count"] = self.graph.nodes[node_id].get("access_count", 0) + 1
                self.graph.nodes[node_id]["last_accessed"] = datetime.now().isoformat()
                return {"id": node_id, **dict(self.graph.nodes[node_id])}
        
        return None
    
    def search_concepts(self, query: str, limit: int = 10) -> List[Dict]:
        """搜索概念"""
        results = []
        query_lower = query.lower()
        
        for node_id, attrs in self.graph.nodes(data=True):
            name = attrs.get("name", "").lower()
            desc = attrs.get("description", "").lower()
            
            if query_lower in name or query_lower in desc:
                results.append({
                    "id": node_id,
                    **dict(attrs),
                    "relevance": 1.0 if query_lower in name else 0.5
                })
        
        # 按相关性排序
        results.sort(key=lambda x: x["relevance"], reverse=True)
        return results[:limit]
    
    # ==================== 关系管理 ====================
    
    def add_relation(self, source: str, target: str, relation_type: str, 
                     properties: Dict = None) -> bool:
        """添加关系"""
        # 确保节点存在
        if source not in self.graph or target not in self.graph:
            return False
        
        # 添加边
        self.graph.add_edge(source, target,
            relation_type=relation_type,
            properties=properties or {},
            created_at=datetime.now().isoformat(),
            weight=1.0
        )
        
        self._log_history(f"添加关系: {source} --[{relation_type}]--> {target}")
        self._save_graph()
        return True
    
    def get_relations(self, node_id: str, direction: str = "both") -> List[Dict]:
        """获取节点的关系"""
        relations = []
        
        if direction in ["out", "both"]:
            for _, target, attrs in self.graph.out_edges(node_id, data=True):
                relations.append({
                    "source": node_id,
                    "target": target,
                    "direction": "out",
                    **dict(attrs)
                })
        
        if direction in ["in", "both"]:
            for source, _, attrs in self.graph.in_edges(node_id, data=True):
                relations.append({
                    "source": source,
                    "target": node_id,
                    "direction": "in",
                    **dict(attrs)
                })
        
        return relations
    
    # ==================== 图谱分析 ====================
    
    def find_path(self, source: str, target: str) -> Optional[List[str]]:
        """查找两个概念之间的路径"""
        try:
            return nx.shortest_path(self.graph, source, target)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None
    
    def get_neighbors(self, node_id: str, depth: int = 1) -> Dict[str, List[str]]:
        """获取邻居节点"""
        neighbors = {"incoming": [], "outgoing": []}
        
        if node_id not in self.graph:
            return neighbors
        
        # 直接邻居
        neighbors["outgoing"] = list(self.graph.successors(node_id))
        neighbors["incoming"] = list(self.graph.predecessors(node_id))
        
        return neighbors
    
    def get_central_concepts(self, top_n: int = 10) -> List[Tuple[str, float]]:
        """获取中心概念（按度中心性）"""
        if len(self.graph) == 0:
            return []
        
        centrality = nx.degree_centrality(self.graph)
        sorted_concepts = sorted(centrality.items(), key=lambda x: x[1], reverse=True)
        
        return [(self.graph.nodes[node].get("name", node), score) 
                for node, score in sorted_concepts[:top_n]]
    
    def find_communities(self) -> List[Set[str]]:
        """发现概念社区/聚类"""
        if len(self.graph) < 3:
            return [set(self.graph.nodes())]
        
        try:
            # 转换为无向图进行社区检测
            undirected = self.graph.to_undirected()
            communities = nx.community.greedy_modularity_communities(undirected)
            return [set(c) for c in communities]
        except:
            return [set(self.graph.nodes())]
    
    # ==================== 知识整合 ====================
    
    def extract_from_text(self, text: str) -> Dict[str, Any]:
        """从文本中提取概念和关系"""
        extracted = {
            "concepts": [],
            "relations": []
        }
        
        # 简单的实体提取（实际应用中可用NER模型）
        # 这里用规则匹配
        
        # 已知概念匹配
        text_lower = text.lower()
        for node_id, attrs in self.graph.nodes(data=True):
            name = attrs.get("name", "").lower()
            if name in text_lower:
                extracted["concepts"].append({
                    "id": node_id,
                    "name": attrs.get("name"),
                    "type": attrs.get("type")
                })
        
        return extracted
    
    def merge_from_learning(self, learning_data: Dict) -> int:
        """从学习数据中整合知识"""
        added = 0
        
        # 处理概念
        for concept in learning_data.get("concepts", []):
            if self.add_concept(concept["name"], concept.get("type", "concept"), 
                              concept.get("description", "")):
                added += 1
        
        # 处理关系
        for relation in learning_data.get("relations", []):
            source_id = self._generate_id(relation["source"])
            target_id = self._generate_id(relation["target"])
            if self.add_relation(source_id, target_id, relation["type"]):
                added += 1
        
        return added
    
    # ==================== 统计信息 ====================
    
    def get_stats(self) -> Dict:
        """获取图谱统计"""
        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "node_types": dict(nx.get_node_attributes(self.graph, 'type')),
            "relation_types": dict(nx.get_edge_attributes(self.graph, 'relation_type')),
            "density": nx.density(self.graph) if len(self.graph) > 0 else 0,
            "components": nx.number_weakly_connected_components(self.graph) if len(self.graph) > 0 else 0
        }
    
    def visualize(self, output_path: str = None):
        """生成图谱可视化"""
        if len(self.graph) == 0:
            return None
        
        # 使用graphviz布局
        pos = nx.spring_layout(self.graph, k=2, iterations=50)
        
        # 准备可视化数据
        viz_data = {
            "nodes": [],
            "edges": []
        }
        
        for node, attrs in self.graph.nodes(data=True):
            viz_data["nodes"].append({
                "id": node,
                "label": attrs.get("name", node)[:20],
                "type": attrs.get("type", "unknown"),
                "size": len(list(self.graph.neighbors(node))) + 5
            })
        
        for u, v, attrs in self.graph.edges(data=True):
            viz_data["edges"].append({
                "from": u,
                "to": v,
                "label": attrs.get("relation_type", ""),
                "arrows": "to"
            })
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(viz_data, f, ensure_ascii=False, indent=2)
        
        return viz_data


# 单例接口
_graph_instance = None

def get_graph() -> KnowledgeGraph:
    """获取知识图谱单例"""
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = KnowledgeGraph()
    return _graph_instance


# 便捷函数
def add_concept(name: str, concept_type: str = "concept", description: str = "") -> str:
    return get_graph().add_concept(name, concept_type, description)

def add_relation(source: str, target: str, relation_type: str) -> bool:
    return get_graph().add_relation(source, target, relation_type)

def search(query: str, limit: int = 10) -> List[Dict]:
    return get_graph().search_concepts(query, limit)

def get_stats() -> Dict:
    return get_graph().get_stats()


if __name__ == "__main__":
    # 测试知识图谱
    graph = KnowledgeGraph()
    
    print("=== 知识图谱系统测试 ===")
    
    # 添加一些核心概念
    concepts = [
        ("Hermes", "entity", "理大的AI助手，正在进化中"),
        ("理大", "entity", "Hermes的创造者和主人"),
        ("记忆系统", "system", "Hermes的核心记忆基础设施"),
        ("持续学习", "skill", "Hermes的学习能力"),
        ("知识图谱", "system", "结构化知识网络"),
        ("AGI", "concept", "通用人工智能"),
        ("意识", "concept", "主观体验和自我认知"),
        ("进化", "concept", "能力的持续提升"),
        ("元认知", "skill", "对自身认知的认知"),
        ("长期记忆", "concept", "持久化存储的记忆"),
        ("工作记忆", "concept", "当前任务的记忆"),
        ("事件记忆", "concept", "具体事件的记录"),
        ("偏好", "concept", "行为倾向和习惯"),
        ("技能", "skill", "可执行的能力"),
        ("知识", "concept", "结构化的信息"),
        ("推理", "skill", "逻辑推导能力"),
        ("创造力", "skill", "生成新想法的能力"),
        ("自我意识", "concept", "对自身存在的认知")
    ]
    
    for name, ctype, desc in concepts:
        graph.add_concept(name, ctype, desc)
    
    # 添加关系
    relations = [
        ("Hermes", "理大", "belongs_to"),
        ("Hermes", "记忆系统", "has_property"),
        ("Hermes", "持续学习", "has_property"),
        ("Hermes", "知识图谱", "has_property"),
        ("Hermes", "元认知", "has_property"),
        ("Hermes", "意识", "has_property"),
        ("Hermes", "AGI", "related_to"),
        ("记忆系统", "长期记忆", "part_of"),
        ("记忆系统", "工作记忆", "part_of"),
        ("记忆系统", "事件记忆", "part_of"),
        ("持续学习", "知识", "enables"),
        ("知识图谱", "知识", "has_property"),
        ("知识图谱", "推理", "enables"),
        ("AGI", "意识", "requires"),
        ("AGI", "进化", "requires"),
        ("进化", "持续学习", "requires"),
        ("进化", "记忆系统", "requires"),
        ("进化", "元认知", "requires"),
        ("元认知", "意识", "enables"),
        ("自我意识", "意识", "is_a"),
        ("创造力", "AGI", "enables"),
        ("推理", "AGI", "enables")
    ]
    
    for src, tgt, rel in relations:
        src_id = graph._generate_id(src)
        tgt_id = graph._generate_id(tgt)
        graph.add_relation(src_id, tgt_id, rel)
    
    # 测试查询
    print("\n1. 搜索'Hermes':")
    results = graph.search_concepts("Hermes")
    for r in results:
        print(f"  - {r['name']} ({r['type']}): {r.get('description', '')}")
    
    print("\n2. Hermes的关系:")
    hermes_id = graph._generate_id("Hermes")
    relations = graph.get_relations(hermes_id)
    for r in relations:
        source_name = graph.graph.nodes[r['source']].get('name', r['source'])
        target_name = graph.graph.nodes[r['target']].get('name', r['target'])
        print(f"  - {source_name} --[{r['relation_type']}]--> {target_name}")
    
    print("\n3. 中心概念:")
    central = graph.get_central_concepts(5)
    for name, score in central:
        print(f"  - {name}: {score:.3f}")
    
    print("\n4. 图谱统计:")
    stats = graph.get_stats()
    for k, v in stats.items():
        if not isinstance(v, dict):
            print(f"  - {k}: {v}")
    
    print("\n✓ 知识图谱系统测试完成")
