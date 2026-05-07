#!/usr/bin/env python3
"""
知识图谱自动扩展与集成
从多个来源自动提取和整合知识
"""

import json
import os
import re
from datetime import datetime
from typing import Dict, List, Set
import sys

sys.path.insert(0, '/root/.hermes/cognition/knowledge_graph')
from graph import KnowledgeGraph, get_graph


class KnowledgeExtractor:
    """知识提取器"""
    
    def __init__(self, graph: KnowledgeGraph = None):
        self.graph = graph or get_graph()
        self.memory_path = "/root/.hermes/memory"
        self.learning_path = "/root/.hermes/memory/continuous_learning"
        
        # 概念模式匹配
        self.patterns = {
            "file_path": r'\/[\w\-\.\/]+\.\w+',
            "url": r'https?:\/\/[^\s]+',
            "email": r'[\w\.-]+@[\w\.-]+\.\w+',
            "date": r'\d{4}-\d{2}-\d{2}',
            "version": r'v?\d+\.\d+(\.\d+)?',
            "command": r'(?:npm|git|python|pip|curl|apt)\s+[\w\-]+',
        }
    
    def extract_from_episodes(self) -> Dict:
        """从事件记录中提取知识"""
        episodes_path = os.path.join(self.memory_path, "episodes")
        
        extracted = {
            "concepts": [],
            "relations": [],
            "count": 0
        }
        
        if not os.path.exists(episodes_path):
            return extracted
        
        for filename in os.listdir(episodes_path):
            if filename.endswith('.md'):
                filepath = os.path.join(episodes_path, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # 提取概念
                    concepts = self._extract_concepts_from_text(content)
                    extracted["concepts"].extend(concepts)
                    
                    # 提取关系
                    relations = self._extract_relations_from_text(content)
                    extracted["relations"].extend(relations)
                    
                    extracted["count"] += 1
        
        return extracted
    
    def extract_from_learning(self) -> Dict:
        """从学习记录中提取知识"""
        learning_path = self.learning_path
        
        extracted = {
            "concepts": [],
            "relations": [],
            "count": 0
        }
        
        if not os.path.exists(learning_path):
            return extracted
        
        # 遍历学习记录
        for date_dir in os.listdir(learning_path):
            date_path = os.path.join(learning_path, date_dir)
            if os.path.isdir(date_path):
                for filename in os.listdir(date_path):
                    filepath = os.path.join(date_path, filename)
                    if os.path.exists(filepath):
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                            # 提取概念
                            concepts = self._extract_concepts_from_text(content)
                            extracted["concepts"].extend(concepts)
                            
                            extracted["count"] += 1
        
        return extracted
    
    def extract_from_long_term_memory(self) -> Dict:
        """从长期记忆中提取知识"""
        long_term_path = os.path.join(self.memory_path, "core/long-term.md")
        
        extracted = {
            "concepts": [],
            "relations": [],
            "count": 0
        }
        
        if not os.path.exists(long_term_path):
            return extracted
        
        with open(long_term_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # 提取所有概念
            concepts = self._extract_concepts_from_text(content)
            extracted["concepts"] = concepts
            
            # 提取关系
            relations = self._extract_relations_from_text(content)
            extracted["relations"] = relations
            
            extracted["count"] = 1
        
        return extracted
    
    def _extract_concepts_from_text(self, text: str) -> List[Dict]:
        """从文本中提取概念"""
        concepts = []
        
        # 检查已知概念
        for node_id, attrs in self.graph.graph.nodes(data=True):
            name = attrs.get("name", "").lower()
            if name and name in text.lower():
                concepts.append({
                    "id": node_id,
                    "name": attrs.get("name"),
                    "type": attrs.get("type", "concept"),
                    "found_in_text": True
                })
        
        # 提取新概念（使用模式匹配）
        for pattern_name, pattern in self.patterns.items():
            matches = re.findall(pattern, text)
            for match in matches[:5]:  # 限制每个模式最多5个
                if len(match) > 3 and len(match) < 50:  # 过滤太短或太长的
                    concepts.append({
                        "name": match,
                        "type": pattern_name,
                        "source": "pattern_extraction"
                    })
        
        return concepts
    
    def _extract_relations_from_text(self, text: str) -> List[Dict]:
        """从文本中提取关系"""
        relations = []
        
        # 基于关键词的关系提取
        relation_keywords = {
            "is_a": ["是一种", "属于", "is a", "is an"],
            "part_of": ["包含", "包括", "contains", "includes"],
            "uses": ["使用", "利用", "uses", "utilizes"],
            "creates": ["创建", "生成", "creates", "generates"],
            "requires": ["需要", "依赖", "requires", "depends on"],
            "related_to": ["相关", "关联", "related to", "associated with"]
        }
        
        text_lower = text.lower()
        
        # 获取所有已知概念名称
        known_concepts = {}
        for node_id, attrs in self.graph.graph.nodes(data=True):
            name = attrs.get("name", "").lower()
            if name:
                known_concepts[name] = node_id
        
        # 查找关系
        for relation_type, keywords in relation_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    # 查找概念对
                    concept_names = list(known_concepts.keys())
                    for i, concept1 in enumerate(concept_names):
                        for concept2 in concept_names[i+1:]:
                            if concept1 in text_lower and concept2 in text_lower:
                                # 检查是否在相近位置
                                pos1 = text_lower.find(concept1)
                                pos2 = text_lower.find(concept2)
                                keyword_pos = text_lower.find(keyword)
                                
                                if abs(pos1 - keyword_pos) < 100 and abs(pos2 - keyword_pos) < 100:
                                    relations.append({
                                        "source": known_concepts[concept1],
                                        "target": known_concepts[concept2],
                                        "type": relation_type,
                                        "evidence": keyword
                                    })
        
        return relations
    
    def auto_expand(self) -> Dict:
        """自动扩展知识图谱"""
        results = {
            "new_concepts": 0,
            "new_relations": 0,
            "sources_processed": 0
        }
        
        # 从事件记录提取
        episode_data = self.extract_from_episodes()
        results["sources_processed"] += episode_data["count"]
        
        # 从学习记录提取
        learning_data = self.extract_from_learning()
        results["sources_processed"] += learning_data["count"]
        
        # 从长期记忆提取
        memory_data = self.extract_from_long_term_memory()
        results["sources_processed"] += memory_data["count"]
        
        # 合并所有提取的概念
        all_concepts = []
        all_relations = []
        
        for data in [episode_data, learning_data, memory_data]:
            all_concepts.extend(data.get("concepts", []))
            all_relations.extend(data.get("relations", []))
        
        # 去重并添加到图谱
        seen_concepts = set()
        for concept in all_concepts:
            concept_id = concept.get("id") or self.graph._generate_id(concept.get("name", ""))
            if concept_id not in seen_concepts:
                seen_concepts.add(concept_id)
                if concept_id not in self.graph.graph:
                    self.graph.add_concept(
                        concept.get("name", ""),
                        concept.get("type", "concept"),
                        concept.get("description", "")
                    )
                    results["new_concepts"] += 1
        
        # 添加关系
        seen_relations = set()
        for relation in all_relations:
            rel_key = (relation["source"], relation["target"], relation["type"])
            if rel_key not in seen_relations:
                seen_relations.add(rel_key)
                if self.graph.add_relation(relation["source"], relation["target"], relation["type"]):
                    results["new_relations"] += 1
        
        return results


def run_auto_expand():
    """运行自动扩展"""
    print("=== 知识图谱自动扩展 ===")
    
    extractor = KnowledgeExtractor()
    results = extractor.auto_expand()
    
    print(f"\n处理来源数: {results['sources_processed']}")
    print(f"新增概念: {results['new_concepts']}")
    print(f"新增关系: {results['new_relations']}")
    
    # 显示图谱统计
    stats = extractor.graph.get_stats()
    print(f"\n图谱总览:")
    print(f"  总概念数: {stats['total_nodes']}")
    print(f"  总关系数: {stats['total_edges']}")
    print(f"  图密度: {stats['density']:.4f}")
    
    # 显示中心概念
    print("\n核心概念:")
    central = extractor.graph.get_central_concepts(5)
    for name, score in central:
        print(f"  - {name}: {score:.3f}")
    
    print("\n✓ 自动扩展完成")
    return results


if __name__ == "__main__":
    run_auto_expand()
