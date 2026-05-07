#!/usr/bin/env python3
"""
推理引擎 v2.0 - 高级推理能力
============================

新增能力:
1. 因果推理 - 推断因果链
2. 矛盾检测 - 发现知识冲突
3. 模式识别 - 发现知识图谱中的模式
4. 溯因推理 - 为观察找到最佳解释
5. 组合推理 - 组合多种推理方式
"""

import sys
sys.path.insert(0, '/root/.hermes/cognition/knowledge_graph')

from knowledge_manager import KnowledgeManager
from query_engine import QueryEngine
from collections import defaultdict
from typing import List, Dict, Set, Tuple, Optional
import json


class ReasoningEngine:
    """知识图谱推理引擎 v2.0"""
    
    def __init__(self, km=None):
        self.km = km or KnowledgeManager()
        self.qe = QueryEngine(self.km)
        self._reasoning_cache = {}
    
    # ========== 传递推理 ==========
    
    def infer_transitive(self, concept_name: str, relation_type: str, max_depth: int = 3) -> List[dict]:
        """传递推理: A -rel-> B, B -rel-> C => A -rel-> C (支持多层)"""
        concept = self.km.get_concept_by_name(concept_name)
        if not concept:
            return []
        
        visited = set()
        results = []
        self._transitive_dfs(concept, relation_type, 0, max_depth, [concept_name], visited, results)
        return results
    
    def _transitive_dfs(self, concept, rel_type, depth, max_depth, path, visited, results):
        if depth >= max_depth or concept["id"] in visited:
            return
        
        visited.add(concept["id"])
        outgoing = [r for r in self.km.get_relations_from(concept["id"]) if r["type"] == rel_type]
        
        for rel in outgoing:
            target = self.km.get_concept_by_id(rel["target_id"])
            if not target:
                continue
            
            new_path = path + [target["name"]]
            
            if depth > 0:  # 跳过直接关系
                confidence = 1.0
                for _ in range(depth + 1):
                    confidence *= rel.get("confidence", 0.9) * 0.85
                results.append({
                    "from": path[0],
                    "through": new_path[1:-1],
                    "to": target["name"],
                    "relation": rel_type,
                    "confidence": round(confidence, 4),
                    "depth": depth + 1,
                    "path": new_path
                })
            
            self._transitive_dfs(target, rel_type, depth + 1, max_depth, new_path, visited, results)
    
    # ========== 因果推理 ==========
    
    def infer_causal_chain(self, concept_name: str) -> List[dict]:
        """推断因果链: A causes B causes C"""
        concept = self.km.get_concept_by_name(concept_name)
        if not concept:
            return []
        
        causal_relations = ["causes", "leads_to", "enables", "produces", "results_in"]
        chains = []
        visited = set()
        
        self._causal_dfs(concept, causal_relations, [concept_name], chains, visited)
        return chains
    
    def _causal_dfs(self, concept, rel_types, path, chains, visited):
        if concept["id"] in visited or len(path) > 5:
            return
        visited.add(concept["id"])
        
        outgoing = self.km.get_relations_from(concept["id"])
        for rel in outgoing:
            if rel["type"] in rel_types:
                target = self.km.get_concept_by_id(rel["target_id"])
                if target:
                    new_path = path + [target["name"]]
                    chains.append({
                        "chain": new_path,
                        "length": len(new_path) - 1,
                        "relation": rel["type"]
                    })
                    self._causal_dfs(target, rel_types, new_path, chains, visited)
    
    # ========== 矛盾检测 ==========
    
    def detect_contradictions(self) -> List[dict]:
        """检测知识图谱中的矛盾"""
        contradictions = []
        all_concepts = self.km.get_all_concepts()
        
        for concept in all_concepts:
            outgoing = self.km.get_relations_from(concept["id"])
            
            # 检查互斥关系
            for r1 in outgoing:
                for r2 in outgoing:
                    if r1["id"] == r2["id"]:
                        continue
                    if self._are_contradictory(r1["type"], r2["type"]):
                        if r1["target_id"] == r2["target_id"]:
                            contradictions.append({
                                "type": "direct_contradiction",
                                "concept": concept["name"],
                                "relation1": r1["type"],
                                "relation2": r2["type"],
                                "target_id": r1["target_id"]
                            })
            
            # 检查循环因果
            for rel in outgoing:
                if rel["type"] in ["causes", "leads_to"]:
                    target = self.km.get_concept_by_id(rel["target_id"])
                    if target:
                        target_rels = self.km.get_relations_from(target["id"])
                        for tr in target_rels:
                            if tr["type"] in ["causes", "leads_to"] and tr["target_id"] == concept["id"]:
                                contradictions.append({
                                    "type": "circular_causality",
                                    "concept1": concept["name"],
                                    "concept2": target["name"],
                                    "relation": rel["type"]
                                })
        
        return contradictions
    
    def _are_contradictory(self, rel1: str, rel2: str) -> bool:
        """判断两个关系是否矛盾"""
        contradiction_pairs = [
            ("enables", "prevents"),
            ("causes", "prevents"),
            ("increases", "decreases"),
            ("is_a", "is_not_a"),
            ("supports", "opposes"),
        ]
        for a, b in contradiction_pairs:
            if (rel1 == a and rel2 == b) or (rel1 == b and rel2 == a):
                return True
        return False
    
    # ========== 模式识别 ==========
    
    def find_patterns(self) -> List[dict]:
        """发现知识图谱中的结构模式"""
        patterns = []
        all_concepts = self.km.get_all_concepts()
        
        # 模式1: 集线节点（大量入边或出边）
        for concept in all_concepts:
            out_count = len(self.km.get_relations_from(concept["id"]))
            in_count = len(self.km.get_relations_to(concept["id"]))
            
            if out_count >= 5:
                patterns.append({
                    "type": "hub_outgoing",
                    "concept": concept["name"],
                    "count": out_count,
                    "description": f"{concept['name']} 是一个辐射中心，有 {out_count} 条出边"
                })
            if in_count >= 5:
                patterns.append({
                    "type": "hub_incoming",
                    "concept": concept["name"],
                    "count": in_count,
                    "description": f"{concept['name']} 是一个汇聚中心，有 {in_count} 条入边"
                })
        
        # 模式2: 三角形关系 (A->B->C->A)
        triangles = self._find_triangles()
        for t in triangles:
            patterns.append({
                "type": "triangle",
                "concepts": t,
                "description": f"三角关系: {' -> '.join(t)}"
            })
        
        # 模式3: 共享关系模式
        relation_groups = defaultdict(list)
        for concept in all_concepts:
            outgoing = tuple(sorted(r["type"] for r in self.km.get_relations_from(concept["id"])))
            if len(outgoing) >= 2:
                relation_groups[outgoing].append(concept["name"])
        
        for rel_pattern, concepts in relation_groups.items():
            if len(concepts) >= 2:
                patterns.append({
                    "type": "shared_pattern",
                    "concepts": concepts,
                    "pattern": list(rel_pattern),
                    "description": f"共享模式: {', '.join(concepts)} 都有关系 {list(rel_pattern)}"
                })
        
        return patterns
    
    def _find_triangles(self) -> List[List[str]]:
        """找到三角形关系"""
        triangles = []
        all_concepts = self.km.get_all_concepts()
        
        for c1 in all_concepts:
            out1 = self.km.get_relations_from(c1["id"])
            for r1 in out1:
                c2 = self.km.get_concept_by_id(r1["target_id"])
                if not c2 or c2["id"] <= c1["id"]:
                    continue
                out2 = self.km.get_relations_from(c2["id"])
                for r2 in out2:
                    c3 = self.km.get_concept_by_id(r2["target_id"])
                    if not c3 or c3["id"] <= c2["id"]:
                        continue
                    # 检查 C3 -> C1
                    out3 = self.km.get_relations_from(c3["id"])
                    for r3 in out3:
                        if r3["target_id"] == c1["id"]:
                            triangles.append([c1["name"], c2["name"], c3["name"]])
        
        return triangles
    
    # ========== 溯因推理 ==========
    
    def abductive_reasoning(self, observation: str) -> List[dict]:
        """为观察找到最佳解释"""
        concept = self.km.get_concept_by_name(observation)
        if not concept:
            return []
        
        explanations = []
        
        # 查找所有指向该概念的关系
        incoming = self.km.get_relations_to(concept["id"])
        
        for rel in incoming:
            source = self.km.get_concept_by_id(rel["source_id"])
            if source:
                explanations.append({
                    "explanation": f"{source['name']} {rel['type']} {observation}",
                    "cause": source["name"],
                    "relation": rel["type"],
                    "confidence": rel.get("confidence", 0.5),
                    "type": "direct_cause"
                })
        
        # 间接原因 (通过传递)
        for rel in incoming:
            source = self.km.get_concept_by_id(rel["source_id"])
            if source:
                deeper = self.km.get_relations_to(source["id"])
                for drel in deeper:
                    dsource = self.km.get_concept_by_id(drel["source_id"])
                    if dsource:
                        explanations.append({
                            "explanation": f"{dsource['name']} -> {source['name']} -> {observation}",
                            "cause": dsource["name"],
                            "relation": f"{drel['type']}->{rel['type']}",
                            "confidence": drel.get("confidence", 0.5) * rel.get("confidence", 0.5) * 0.7,
                            "type": "indirect_cause"
                        })
        
        return sorted(explanations, key=lambda x: x["confidence"], reverse=True)
    
    # ========== 组合推理 ==========
    
    def comprehensive_analysis(self, concept_name: str) -> dict:
        """对一个概念进行全面推理分析"""
        result = {
            "concept": concept_name,
            "transitive": {},
            "causal_chains": [],
            "analogies": [],
            "explanations": [],
            "suggestions": []
        }
        
        # 传递推理 (对所有关系类型)
        concept = self.km.get_concept_by_name(concept_name)
        if concept:
            rel_types = set()
            for r in self.km.get_relations_from(concept["id"]):
                rel_types.add(r["type"])
            for rt in rel_types:
                inferred = self.infer_transitive(concept_name, rt)
                if inferred:
                    result["transitive"][rt] = inferred
        
        # 因果链
        result["causal_chains"] = self.infer_causal_chain(concept_name)
        
        # 类比
        result["analogies"] = self.find_analogies(concept_name)
        
        # 溯因
        result["explanations"] = self.abductive_reasoning(concept_name)
        
        # 建议
        result["suggestions"] = self.get_suggestions(concept_name)
        
        return result
    
    # ========== 原有能力(增强) ==========
    
    def find_analogies(self, concept_name: str) -> List[dict]:
        """类比推理: 找到与给定概念结构相似的概念"""
        concept = self.km.get_concept_by_name(concept_name)
        if not concept:
            return []
        
        outgoing = self.km.get_relations_from(concept["id"])
        incoming = self.km.get_relations_to(concept["id"])
        
        outgoing_types = set(r["type"] for r in outgoing)
        incoming_types = set(r["type"] for r in incoming)
        
        all_concepts = self.km.get_all_concepts()
        similar = []
        
        for c in all_concepts:
            if c["id"] == concept["id"]:
                continue
            
            c_out = set(r["type"] for r in self.km.get_relations_from(c["id"]))
            c_in = set(r["type"] for r in self.km.get_relations_to(c["id"]))
            
            out_overlap = len(outgoing_types & c_out)
            in_overlap = len(incoming_types & c_in)
            total = len(outgoing_types | c_out) + len(incoming_types | c_in)
            
            if total > 0:
                similarity = (out_overlap + in_overlap) / total
                if similarity > 0.3:
                    similar.append({
                        "concept": c["name"],
                        "similarity": round(similarity, 3),
                        "shared_outgoing": list(outgoing_types & c_out),
                        "shared_incoming": list(incoming_types & c_in)
                    })
        
        return sorted(similar, key=lambda x: x["similarity"], reverse=True)
    
    def get_suggestions(self, concept_name: str) -> List[dict]:
        """基于现有知识建议可能的关系"""
        concept = self.km.get_concept_by_name(concept_name)
        if not concept:
            return []
        
        suggestions = []
        
        # 基于类比
        analogies = self.find_analogies(concept_name)
        for a in analogies[:3]:
            other = self.km.get_concept_by_name(a["concept"])
            if other:
                for rel_type in a["shared_outgoing"]:
                    existing = self.km.get_relations_from(concept["id"])
                    if not any(r["type"] == rel_type for r in existing):
                        suggestions.append({
                            "type": "add_relation",
                            "source": concept_name,
                            "relation": rel_type,
                            "reason": f"类比: {a['concept']} 也有 {rel_type} 关系"
                        })
        
        # 基于传递性
        for rel in self.km.get_relations_from(concept["id"]):
            inferred = self.infer_transitive(concept_name, rel["type"])
            for inf in inferred:
                target = self.km.get_concept_by_name(inf["to"])
                if target:
                    existing = self.km.get_relation(concept["id"], target["id"], rel["type"])
                    if not existing:
                        suggestions.append({
                            "type": "add_relation",
                            "source": concept_name,
                            "relation": rel["type"],
                            "target": inf["to"],
                            "reason": f"传递推理: {' -> '.join(inf['path'])}",
                            "confidence": inf["confidence"]
                        })
        
        return suggestions
    
    # ========== 推理统计 ==========
    
    def reasoning_stats(self) -> dict:
        """推理引擎统计"""
        all_concepts = self.km.get_all_concepts()
        all_relations = []
        for c in all_concepts:
            all_relations.extend(self.km.get_relations_from(c["id"]))
        
        rel_type_counts = defaultdict(int)
        for r in all_relations:
            rel_type_counts[r["type"]] += 1
        
        return {
            "total_concepts": len(all_concepts),
            "total_relations": len(all_relations),
            "relation_types": dict(rel_type_counts),
            "avg_relations_per_concept": round(len(all_relations) / max(len(all_concepts), 1), 2)
        }


# 测试
if __name__ == "__main__":
    re = ReasoningEngine()
    
    print("=== 推理引擎 v2.0 测试 ===\n")
    
    # 统计
    stats = re.reasoning_stats()
    print(f"知识图谱: {stats['total_concepts']} 概念, {stats['total_relations']} 关系")
    print(f"关系类型: {stats['relation_types']}")
    
    # 传递推理
    print("\n=== 传递推理: Hermes has ===")
    inferred = re.infer_transitive("Hermes", "has")
    for inf in inferred[:5]:
        print(f"  {' -> '.join(inf['path'])} (置信度: {inf['confidence']:.2f})")
    
    # 模式识别
    print("\n=== 模式识别 ===")
    patterns = re.find_patterns()
    for p in patterns[:5]:
        print(f"  [{p['type']}] {p['description']}")
    
    # 矛盾检测
    print("\n=== 矛盾检测 ===")
    contradictions = re.detect_contradictions()
    if contradictions:
        for c in contradictions[:3]:
            print(f"  [{c['type']}] {c}")
    else:
        print("  未发现矛盾")
    
    # 全面分析
    print("\n=== 全面分析: Hermes ===")
    analysis = re.comprehensive_analysis("Hermes")
    print(f"  传递推理: {len(analysis['transitive'])} 种关系")
    print(f"  因果链: {len(analysis['causal_chains'])} 条")
    print(f"  类比: {len(analysis['analogies'])} 个")
    print(f"  解释: {len(analysis['explanations'])} 个")
    print(f"  建议: {len(analysis['suggestions'])} 条")
