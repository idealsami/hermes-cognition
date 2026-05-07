#!/usr/bin/env python3
"""
查询引擎 - 提供图谱查询能力
"""

import json
from collections import deque
from knowledge_manager import KnowledgeManager


class QueryEngine:
    """知识图谱查询引擎"""
    
    def __init__(self, km=None):
        self.km = km or KnowledgeManager()
    
    def find_path(self, start_name, end_name, max_depth=3):
        """查找两个概念之间的最短路径 (BFS)"""
        start = self.km.get_concept_by_name(start_name)
        end = self.km.get_concept_by_name(end_name)
        
        if not start or not end:
            return None
        
        # BFS
        queue = deque([(start["id"], [start["id"]])])
        visited = {start["id"]}
        
        while queue:
            current_id, path = queue.popleft()
            
            if len(path) > max_depth + 1:
                continue
            
            if current_id == end["id"]:
                # 构建路径详情
                result_path = []
                for i in range(len(path) - 1):
                    source = self.km.get_concept_by_id(path[i])
                    target = self.km.get_concept_by_id(path[i+1])
                    relations = self.km.get_relations_from(path[i])
                    rel = next((r for r in relations if r["target_id"] == path[i+1]), None)
                    result_path.append({
                        "source": source["name"],
                        "relation": rel["type"] if rel else "unknown",
                        "target": target["name"]
                    })
                return result_path
            
            # 向前搜索
            for rel in self.km.get_relations_from(current_id):
                if rel["target_id"] not in visited:
                    visited.add(rel["target_id"])
                    queue.append((rel["target_id"], path + [rel["target_id"]]))
            
            # 向后搜索
            for rel in self.km.get_relations_to(current_id):
                if rel["source_id"] not in visited:
                    visited.add(rel["source_id"])
                    queue.append((rel["source_id"], path + [rel["source_id"]]))
        
        return None
    
    def get_neighbors(self, concept_name, depth=1):
        """获取概念的邻居（N跳内）"""
        concept = self.km.get_concept_by_name(concept_name)
        if not concept:
            return []
        
        visited = set()
        result = []
        
        def dfs(cid, current_depth):
            if current_depth > depth or cid in visited:
                return
            visited.add(cid)
            
            c = self.km.get_concept_by_id(cid)
            if c and cid != concept["id"]:
                result.append(c)
            
            for rel in self.km.get_relations_from(cid):
                dfs(rel["target_id"], current_depth + 1)
            for rel in self.km.get_relations_to(cid):
                dfs(rel["source_id"], current_depth + 1)
        
        dfs(concept["id"], 0)
        return result
    
    def get_context(self, concept_name):
        """获取概念的完整上下文"""
        concept = self.km.get_concept_by_name(concept_name)
        if not concept:
            return None
        
        outgoing = self.km.get_relations_from(concept["id"])
        incoming = self.km.get_relations_to(concept["id"])
        
        return {
            "concept": concept,
            "outgoing_relations": outgoing,
            "incoming_relations": incoming,
            "total_connections": len(outgoing) + len(incoming)
        }
    
    def find_by_type(self, type_name):
        """按类型查找概念"""
        return self.km.get_all_concepts(type_filter=type_name)
    
    def find_related(self, concept_name, relation_type=None):
        """查找相关概念"""
        concept = self.km.get_concept_by_name(concept_name)
        if not concept:
            return []
        
        relations = self.km.get_relations_from(concept["id"])
        if relation_type:
            relations = [r for r in relations if r["type"] == relation_type]
        
        results = []
        for rel in relations:
            target = self.km.get_concept_by_id(rel["target_id"])
            if target:
                results.append({
                    "concept": target,
                    "relation": rel["type"],
                    "confidence": rel["confidence"]
                })
        
        return results
    
    def query(self, question):
        """自然语言查询（简化版）"""
        # 提取关键概念
        concepts = self.km.search_concepts(question)
        
        if not concepts:
            return {"answer": "未找到相关概念", "concepts": []}
        
        # 获取上下文
        contexts = []
        for c in concepts[:3]:
            ctx = self.get_context(c["name"])
            if ctx:
                contexts.append(ctx)
        
        return {
            "concepts": concepts,
            "contexts": contexts
        }


# 测试
if __name__ == "__main__":
    qe = QueryEngine()
    
    print("=== 查询Hermes的上下文 ===")
    ctx = qe.get_context("Hermes")
    print(json.dumps(ctx, indent=2, ensure_ascii=False))
    
    print("\n=== 查找路径: 理大 -> 记忆系统 ===")
    path = qe.find_path("理大", "记忆系统")
    if path:
        for step in path:
            print(f"  {step['source']} --[{step['relation']}]--> {step['target']}")
    else:
        print("  未找到路径")
    
    print("\n=== Hermes的邻居 ===")
    neighbors = qe.get_neighbors("Hermes", depth=2)
    for n in neighbors:
        print(f"  - {n['name']} ({n['type']})")
