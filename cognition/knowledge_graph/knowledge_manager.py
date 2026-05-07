#!/usr/bin/env python3
"""
知识管理器 - 管理知识图谱中的概念和关系
"""

import sqlite3
import json
import uuid
from datetime import datetime
from pathlib import Path


class KnowledgeManager:
    """知识图谱管理器"""
    
    def __init__(self, db_path="/root/.hermes/cognition/knowledge_graph/graph.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.init_db()
    
    def get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self):
        """初始化数据库"""
        conn = self.get_conn()
        cursor = conn.cursor()
        
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS concepts (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                description TEXT,
                properties TEXT,
                source TEXT,
                confidence REAL DEFAULT 1.0,
                access_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS relations (
                id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                type TEXT NOT NULL,
                weight REAL DEFAULT 1.0,
                properties TEXT,
                source TEXT,
                confidence REAL DEFAULT 1.0,
                evidence TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_id) REFERENCES concepts(id),
                FOREIGN KEY (target_id) REFERENCES concepts(id)
            );
            
            CREATE INDEX IF NOT EXISTS idx_concepts_name ON concepts(name);
            CREATE INDEX IF NOT EXISTS idx_concepts_type ON concepts(type);
            CREATE INDEX IF NOT EXISTS idx_relations_source ON relations(source_id);
            CREATE INDEX IF NOT EXISTS idx_relations_target ON relations(target_id);
            CREATE INDEX IF NOT EXISTS idx_relations_type ON relations(type);
        """)
        
        conn.commit()
        conn.close()
    
    def add_concept(self, name, type, description=None, properties=None, source=None, confidence=1.0):
        """添加概念"""
        # 先检查是否已存在
        existing = self.get_concept_by_name(name)
        if existing:
            return existing["id"]
        
        concept_id = str(uuid.uuid4())[:8]
        conn = self.get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO concepts (id, name, type, description, properties, source, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (concept_id, name, type, description, json.dumps(properties or {}), source, confidence))
        
        conn.commit()
        conn.close()
        return concept_id
    
    def add_relation(self, source_id, target_id, type, weight=1.0, properties=None, source=None, confidence=1.0, evidence=None):
        """添加关系"""
        # 检查是否已存在
        existing = self.get_relation(source_id, target_id, type)
        if existing:
            return existing["id"]
        
        relation_id = str(uuid.uuid4())[:8]
        conn = self.get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO relations (id, source_id, target_id, type, weight, properties, source, confidence, evidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (relation_id, source_id, target_id, type, weight, json.dumps(properties or {}), source, confidence, evidence))
        
        conn.commit()
        conn.close()
        return relation_id
    
    def get_concept_by_name(self, name):
        """按名称获取概念"""
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM concepts WHERE name = ?", (name,))
        result = cursor.fetchone()
        conn.close()
        return dict(result) if result else None
    
    def get_concept_by_id(self, concept_id):
        """按ID获取概念"""
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM concepts WHERE id = ?", (concept_id,))
        result = cursor.fetchone()
        if result:
            # 更新访问次数
            cursor.execute("UPDATE concepts SET access_count = access_count + 1 WHERE id = ?", (concept_id,))
            conn.commit()
        conn.close()
        return dict(result) if result else None
    
    def get_relation(self, source_id, target_id, type):
        """获取特定关系"""
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM relations 
            WHERE source_id = ? AND target_id = ? AND type = ?
        """, (source_id, target_id, type))
        result = cursor.fetchone()
        conn.close()
        return dict(result) if result else None
    
    def get_relations_from(self, concept_id):
        """获取从某概念出发的所有关系"""
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.*, c.name as target_name 
            FROM relations r
            JOIN concepts c ON r.target_id = c.id
            WHERE r.source_id = ?
        """, (concept_id,))
        results = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return results
    
    def get_relations_to(self, concept_id):
        """获取指向某概念的所有关系"""
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.*, c.name as source_name 
            FROM relations r
            JOIN concepts c ON r.source_id = c.id
            WHERE r.target_id = ?
        """, (concept_id,))
        results = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return results
    
    def search_concepts(self, query, limit=10):
        """搜索概念"""
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM concepts 
            WHERE name LIKE ? OR description LIKE ?
            ORDER BY access_count DESC
            LIMIT ?
        """, (f"%{query}%", f"%{query}%", limit))
        results = [dict(c) for c in cursor.fetchall()]
        conn.close()
        return results
    
    def get_all_concepts(self, type_filter=None):
        """获取所有概念"""
        conn = self.get_conn()
        cursor = conn.cursor()
        if type_filter:
            cursor.execute("SELECT * FROM concepts WHERE type = ?", (type_filter,))
        else:
            cursor.execute("SELECT * FROM concepts")
        results = [dict(c) for c in cursor.fetchall()]
        conn.close()
        return results
    
    def get_all_relations(self, type_filter=None):
        """获取所有关系"""
        conn = self.get_conn()
        cursor = conn.cursor()
        if type_filter:
            cursor.execute("SELECT * FROM relations WHERE type = ?", (type_filter,))
        else:
            cursor.execute("SELECT * FROM relations")
        results = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return results
    
    def get_stats(self):
        """获取统计信息"""
        conn = self.get_conn()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as count FROM concepts")
        concept_count = cursor.fetchone()["count"]
        
        cursor.execute("SELECT COUNT(*) as count FROM relations")
        relation_count = cursor.fetchone()["count"]
        
        cursor.execute("SELECT type, COUNT(*) as count FROM concepts GROUP BY type")
        concept_types = {r["type"]: r["count"] for r in cursor.fetchall()}
        
        cursor.execute("SELECT type, COUNT(*) as count FROM relations GROUP BY type")
        relation_types = {r["type"]: r["count"] for r in cursor.fetchall()}
        
        conn.close()
        
        return {
            "total_concepts": concept_count,
            "total_relations": relation_count,
            "concept_types": concept_types,
            "relation_types": relation_types
        }
    
    def add_triple(self, subject_name, subject_type, predicate, object_name, object_type, 
                   evidence=None, source="auto", confidence=0.8):
        """便捷方法：添加三元组 (subject - predicate - object)"""
        subject_id = self.add_concept(subject_name, subject_type, source=source)
        object_id = self.add_concept(object_name, object_type, source=source)
        relation_id = self.add_relation(subject_id, object_id, predicate, 
                                       source=source, confidence=confidence, evidence=evidence)
        return {"subject_id": subject_id, "relation_id": relation_id, "object_id": object_id}


# 测试
if __name__ == "__main__":
    km = KnowledgeManager()
    
    # 测试添加概念
    id1 = km.add_concept("Hermes", "ai_agent", "AI助手，正在进化中", source="memory")
    id2 = km.add_concept("理大", "person", "Hermes的主人", source="memory")
    id3 = km.add_concept("记忆系统", "system", "长期记忆系统", source="memory")
    
    # 测试添加关系
    km.add_relation(id2, id1, "created_by", evidence="理大创造了Hermes")
    km.add_relation(id1, id3, "has", evidence="Hermes拥有记忆系统")
    
    # 测试三元组
    km.add_triple("知识图谱", "system", "part_of", "认知系统", "system", 
                  evidence="知识图谱是认知系统的一部分")
    
    # 测试查询
    print("=== 知识图谱统计 ===")
    stats = km.get_stats()
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    
    print("\n=== 搜索'Hermes' ===")
    results = km.search_concepts("Hermes")
    for r in results:
        print(f"  {r['name']} ({r['type']}): {r['description']}")
    
    print("\n=== Hermes的关系 ===")
    relations = km.get_relations_from(id1)
    for r in relations:
        print(f"  -> {r['type']} -> {r['target_name']}")
