#!/usr/bin/env python3
"""
知识图谱系统主入口
"""

import sys
import json
from knowledge_manager import KnowledgeManager
from query_engine import QueryEngine
from reasoning_engine import ReasoningEngine
from auto_learner import AutoLearner


class KnowledgeGraphSystem:
    """知识图谱系统"""
    
    def __init__(self):
        self.km = KnowledgeManager()
        self.qe = QueryEngine(self.km)
        self.re = ReasoningEngine(self.km)
        self.al = AutoLearner(self.km)
    
    def status(self):
        """获取系统状态"""
        stats = self.km.get_stats()
        return {
            "system": "Knowledge Graph",
            "status": "active",
            "stats": stats
        }
    
    def learn(self, text, source="conversation"):
        """学习新知识"""
        return self.al.learn_from_text(text, source)
    
    def query(self, concept_name):
        """查询概念"""
        return self.qe.get_context(concept_name)
    
    def search(self, query):
        """搜索概念"""
        return self.qe.query(query)
    
    def find_path(self, start, end):
        """查找路径"""
        return self.qe.find_path(start, end)
    
    def infer(self, concept, relation_type):
        """推理"""
        return self.re.infer_transitive(concept, relation_type)
    
    def suggest(self, concept):
        """获取建议"""
        return self.re.get_suggestions(concept)
    
    def auto_expand(self):
        """自动扩展"""
        return self.al.auto_expand()
    
    def add_triple(self, s_name, s_type, predicate, o_name, o_type, evidence=None):
        """添加三元组"""
        return self.km.add_triple(s_name, s_type, predicate, o_name, o_type, evidence=evidence)


def main():
    """CLI入口"""
    if len(sys.argv) < 2:
        print("用法: python main.py <command> [args]")
        print("命令:")
        print("  status        - 系统状态")
        print("  learn <text>  - 学习文本")
        print("  query <name>  - 查询概念")
        print("  search <q>    - 搜索")
        print("  path <a> <b>  - 查找路径")
        print("  expand        - 自动扩展")
        return
    
    kgs = KnowledgeGraphSystem()
    cmd = sys.argv[1]
    
    if cmd == "status":
        print(json.dumps(kgs.status(), indent=2, ensure_ascii=False))
    
    elif cmd == "learn" and len(sys.argv) > 2:
        text = " ".join(sys.argv[2:])
        result = kgs.learn(text)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif cmd == "query" and len(sys.argv) > 2:
        name = sys.argv[2]
        result = kgs.query(name)
        if result:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"未找到概念: {name}")
    
    elif cmd == "search" and len(sys.argv) > 2:
        q = " ".join(sys.argv[2:])
        result = kgs.search(q)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif cmd == "path" and len(sys.argv) > 3:
        result = kgs.find_path(sys.argv[2], sys.argv[3])
        if result:
            for step in result:
                print(f"  {step['source']} --[{step['relation']}]--> {step['target']}")
        else:
            print("未找到路径")
    
    elif cmd == "expand":
        result = kgs.auto_expand()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    else:
        print(f"未知命令: {cmd}")


if __name__ == "__main__":
    main()
