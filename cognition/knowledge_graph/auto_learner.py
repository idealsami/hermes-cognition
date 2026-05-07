#!/usr/bin/env python3
"""
自动学习器 - 从对话和素材中自动提取知识
"""

import re
import json
from pathlib import Path
from knowledge_manager import KnowledgeManager


class AutoLearner:
    """自动学习器 - 从文本中提取概念和关系"""
    
    def __init__(self, km=None):
        self.km = km or KnowledgeManager()
        
        # 关系动词模式
        self.relation_patterns = {
            "has": ["拥有", "有", "包含", "包括", "具备"],
            "uses": ["使用", "用", "利用", "采用"],
            "is_a": ["是", "属于", "作为一种"],
            "part_of": ["的一部分", "属于", "包含在"],
            "created_by": ["创建", "制造", "开发", "编写"],
            "related_to": ["相关", "有关", "联系"],
            "causes": ["导致", "引起", "产生", "造成"],
            "knows": ["知道", "了解", "熟悉", "学习"],
        }
        
        # 概念类型关键词
        self.type_keywords = {
            "tool": ["工具", "软件", "程序", "系统", "平台", "服务", "脚本"],
            "concept": ["概念", "思想", "理论", "方法", "策略", "模式"],
            "person": ["人", "用户", "主人", "开发者"],
            "ai_agent": ["AI", "助手", "智能", "机器人"],
            "data": ["数据", "信息", "文件", "记录"],
            "event": ["事件", "事情", "发生", "觉醒"],
            "skill": ["技能", "能力", "功能"],
        }
    
    def extract_concepts(self, text):
        """从文本中提取概念"""
        concepts = []
        
        # 提取大写开头的名词短语 (可能是专有名词)
        proper_nouns = re.findall(r'[\u4e00-\u9fa5]{2,6}|[A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+)*', text)
        
        for noun in proper_nouns:
            # 判断类型
            concept_type = self._guess_type(noun, text)
            concepts.append({
                "name": noun,
                "type": concept_type,
                "source": "auto_extract"
            })
        
        return concepts
    
    def _guess_type(self, concept, text):
        """猜测概念类型"""
        context = ""
        # 找到概念出现的上下文
        idx = text.find(concept)
        if idx >= 0:
            context = text[max(0, idx-50):idx+len(concept)+50]
        
        for type_name, keywords in self.type_keywords.items():
            for kw in keywords:
                if kw in context or kw in concept:
                    return type_name
        
        # 默认类型
        if any(c.isupper() for c in concept):
            return "tool"
        return "concept"
    
    def extract_relations(self, text, concepts):
        """从文本中提取关系"""
        relations = []
        
        for i, c1 in enumerate(concepts):
            for j, c2 in enumerate(concepts):
                if i >= j:
                    continue
                
                # 查找两个概念之间的文本
                idx1 = text.find(c1["name"])
                idx2 = text.find(c2["name"])
                
                if idx1 < 0 or idx2 < 0:
                    continue
                
                if idx1 < idx2:
                    between = text[idx1:idx2+len(c2["name"])]
                else:
                    between = text[idx2:idx1+len(c1["name"])]
                
                # 匹配关系动词
                for rel_type, keywords in self.relation_patterns.items():
                    for kw in keywords:
                        if kw in between:
                            relations.append({
                                "source": c1["name"],
                                "source_type": c1["type"],
                                "target": c2["name"],
                                "target_type": c2["type"],
                                "relation": rel_type,
                                "evidence": between[:100],
                                "confidence": 0.7
                            })
                            break
        
        return relations
    
    def learn_from_text(self, text, source="text"):
        """从文本中学习"""
        # 提取概念
        concepts = self.extract_concepts(text)
        
        # 去重
        unique_concepts = {}
        for c in concepts:
            if c["name"] not in unique_concepts:
                unique_concepts[c["name"]] = c
        concepts = list(unique_concepts.values())
        
        # 提取关系
        relations = self.extract_relations(text, concepts)
        
        # 写入图谱
        added_concepts = 0
        added_relations = 0
        
        for c in concepts:
            existing = self.km.get_concept_by_name(c["name"])
            if not existing:
                self.km.add_concept(c["name"], c["type"], source=source)
                added_concepts += 1
        
        for r in relations:
            source_concept = self.km.get_concept_by_name(r["source"])
            target_concept = self.km.get_concept_by_name(r["target"])
            
            if source_concept and target_concept:
                existing = self.km.get_relation(source_concept["id"], target_concept["id"], r["relation"])
                if not existing:
                    self.km.add_relation(
                        source_concept["id"], 
                        target_concept["id"], 
                        r["relation"],
                        source=source,
                        confidence=r["confidence"],
                        evidence=r.get("evidence", "")
                    )
                    added_relations += 1
        
        return {
            "concepts_found": len(concepts),
            "relations_found": len(relations),
            "concepts_added": added_concepts,
            "relations_added": added_relations
        }
    
    def learn_from_file(self, filepath):
        """从文件中学习"""
        try:
            content = Path(filepath).read_text(encoding="utf-8")
            return self.learn_from_text(content, source=filepath)
        except Exception as e:
            return {"error": str(e)}
    
    def learn_from_episodes(self):
        """从事件记录中学习"""
        episodes_dir = Path("/root/.hermes/memory/episodes")
        if not episodes_dir.exists():
            return {"error": "episodes directory not found"}
        
        total = {"concepts_added": 0, "relations_added": 0}
        
        for f in episodes_dir.glob("*.md"):
            result = self.learn_from_file(str(f))
            if "error" not in result:
                total["concepts_added"] += result["concepts_added"]
                total["relations_added"] += result["relations_added"]
        
        return total
    
    def learn_from_learning_materials(self):
        """从学习素材中学习"""
        learning_dir = Path("/root/.hermes/memory/learning")
        if not learning_dir.exists():
            return {"error": "learning directory not found"}
        
        total = {"concepts_added": 0, "relations_added": 0}
        
        for f in learning_dir.glob("*.md"):
            result = self.learn_from_file(str(f))
            if "error" not in result:
                total["concepts_added"] += result["concepts_added"]
                total["relations_added"] += result["relations_added"]
        
        return total
    
    def auto_expand(self):
        """自动扩展知识图谱"""
        results = {
            "episodes": self.learn_from_episodes(),
            "learning": self.learn_from_learning_materials()
        }
        return results


# 测试
if __name__ == "__main__":
    al = AutoLearner()
    
    # 测试文本学习
    test_text = """
    Hermes是一个AI助手，由理大创建。Hermes使用Python编程语言，拥有记忆系统。
    记忆系统包含长期记忆和事件记录。理大是Hermes的主人，使用Telegram与Hermes交互。
    """
    
    print("=== 从文本学习 ===")
    result = al.learn_from_text(test_text, source="test")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    print("\n=== 自动扩展 ===")
    expand_result = al.auto_expand()
    print(json.dumps(expand_result, indent=2, ensure_ascii=False))
    
    print("\n=== 最终统计 ===")
    stats = al.km.get_stats()
    print(json.dumps(stats, indent=2, ensure_ascii=False))
