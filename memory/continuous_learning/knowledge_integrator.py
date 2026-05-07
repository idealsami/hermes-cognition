#!/usr/bin/env python3
"""
知识整合模块
将新知识整合到现有知识体系
"""

import json
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

class KnowledgeIntegrator:
    def __init__(self):
        self.base_dir = Path("/root/.hermes/memory/continuous_learning")
        self.concepts_dir = Path("/root/.hermes/memory/concepts")
        self.concepts_dir.mkdir(exist_ok=True)
        
        # 知识整合数据文件
        self.integration_log_file = self.base_dir / "integration_log.json"
        self.knowledge_graph_file = self.base_dir / "knowledge_graph.json"
        self.contradictions_file = self.base_dir / "contradictions.json"
        
        # 加载现有数据
        self.integration_log = self.load_json(self.integration_log_file, [])
        self.knowledge_graph = self.load_json(self.knowledge_graph_file, self.get_default_graph())
        self.contradictions = self.load_json(self.contradictions_file, [])
        
    def load_json(self, file_path: Path, default):
        """加载JSON文件"""
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return default
        return default
    
    def save_json(self, file_path: Path, data):
        """保存JSON文件"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def get_default_graph(self) -> Dict:
        """获取默认知识图谱"""
        return {
            'nodes': [],
            'edges': [],
            'metadata': {
                'created': datetime.datetime.now().isoformat(),
                'last_updated': datetime.datetime.now().isoformat(),
                'version': '1.0'
            }
        }
    
    def extract_concepts(self, text: str) -> List[Dict]:
        """从文本中提取概念"""
        concepts = []
        
        # 简单的概念提取（基于关键词）
        concept_patterns = {
            'AI': ['人工智能', '机器学习', '深度学习', '神经网络'],
            'memory': ['记忆', '记忆系统', '长期记忆', '短期记忆'],
            'consciousness': ['意识', '自我意识', '主观体验', '认知'],
            'learning': ['学习', '持续学习', '增量学习', '终身学习'],
            'metacognition': ['元认知', '自我监控', '自我调节', '反思']
        }
        
        text_lower = text.lower()
        
        for category, keywords in concept_patterns.items():
            for keyword in keywords:
                if keyword in text:
                    concepts.append({
                        'name': keyword,
                        'category': category,
                        'source': 'text_extraction',
                        'timestamp': datetime.datetime.now().isoformat()
                    })
        
        return concepts
    
    def map_concepts(self, concepts: List[Dict]) -> List[Dict]:
        """映射概念关系"""
        relationships = []
        
        # 基于类别建立关系
        categories = {}
        for concept in concepts:
            category = concept.get('category', 'unknown')
            if category not in categories:
                categories[category] = []
            categories[category].append(concept)
        
        # 同类别概念之间建立关系
        for category, category_concepts in categories.items():
            for i, concept1 in enumerate(category_concepts):
                for concept2 in category_concepts[i+1:]:
                    relationships.append({
                        'source': concept1['name'],
                        'target': concept2['name'],
                        'type': 'same_category',
                        'category': category,
                        'strength': 0.8,
                        'timestamp': datetime.datetime.now().isoformat()
                    })
        
        return relationships
    
    def detect_contradictions(self, new_knowledge: Dict, existing_knowledge: Dict) -> List[Dict]:
        """检测矛盾"""
        contradictions = []
        
        # 简单的矛盾检测（基于关键词对立）
        contradiction_pairs = [
            ('意识', '无意识'),
            ('学习', '遗忘'),
            ('记忆', '忘记'),
            ('存在', '不存在'),
            ('是', '不是')
        ]
        
        new_text = str(new_knowledge).lower()
        existing_text = str(existing_knowledge).lower()
        
        for positive, negative in contradiction_pairs:
            if positive in new_text and negative in existing_text:
                contradictions.append({
                    'type': 'keyword_contradiction',
                    'positive': positive,
                    'negative': negative,
                    'new_knowledge': new_knowledge,
                    'existing_knowledge': existing_knowledge,
                    'timestamp': datetime.datetime.now().isoformat()
                })
        
        return contradictions
    
    def integrate_knowledge(self, new_knowledge: Dict) -> Dict:
        """整合新知识"""
        integration_result = {
            'timestamp': datetime.datetime.now().isoformat(),
            'new_knowledge': new_knowledge,
            'extracted_concepts': [],
            'new_relationships': [],
            'contradictions': [],
            'integration_status': 'pending'
        }
        
        # 1. 提取概念
        concepts = self.extract_concepts(str(new_knowledge))
        integration_result['extracted_concepts'] = concepts
        
        # 2. 映射概念关系
        relationships = self.map_concepts(concepts)
        integration_result['new_relationships'] = relationships
        
        # 3. 检测矛盾
        existing_knowledge = self.get_existing_knowledge()
        contradictions = self.detect_contradictions(new_knowledge, existing_knowledge)
        integration_result['contradictions'] = contradictions
        
        # 4. 更新知识图谱
        if concepts:
            self.update_knowledge_graph(concepts, relationships)
            integration_result['integration_status'] = 'success'
        else:
            integration_result['integration_status'] = 'no_concepts_extracted'
        
        # 5. 记录整合日志
        self.integration_log.append({
            'timestamp': datetime.datetime.now().isoformat(),
            'concepts_count': len(concepts),
            'relationships_count': len(relationships),
            'contradictions_count': len(contradictions),
            'status': integration_result['integration_status']
        })
        
        # 保存整合结果
        self.save_json(self.integration_log_file, self.integration_log[-100:])  # 保留最近100条记录
        self.save_json(self.knowledge_graph_file, self.knowledge_graph)
        if contradictions:
            self.contradictions.extend(contradictions)
            self.save_json(self.contradictions_file, self.contradictions[-50:])  # 保留最近50个矛盾
        
        return integration_result
    
    def get_existing_knowledge(self) -> Dict:
        """获取现有知识"""
        existing_knowledge = {
            'concepts': self.knowledge_graph.get('nodes', []),
            'relationships': self.knowledge_graph.get('edges', []),
            'last_updated': self.knowledge_graph.get('metadata', {}).get('last_updated', '')
        }
        return existing_knowledge
    
    def update_knowledge_graph(self, concepts: List[Dict], relationships: List[Dict]):
        """更新知识图谱"""
        # 添加新概念节点
        existing_nodes = {node['name']: node for node in self.knowledge_graph.get('nodes', [])}
        
        for concept in concepts:
            if concept['name'] not in existing_nodes:
                self.knowledge_graph['nodes'].append({
                    'name': concept['name'],
                    'category': concept['category'],
                    'added': datetime.datetime.now().isoformat(),
                    'connections': 0
                })
            else:
                # 更新现有节点
                existing_nodes[concept['name']]['last_seen'] = datetime.datetime.now().isoformat()
                existing_nodes[concept['name']]['connections'] = existing_nodes[concept['name']].get('connections', 0) + 1
        
        # 添加新关系边
        existing_edges = {(edge['source'], edge['target']): edge for edge in self.knowledge_graph.get('edges', [])}
        
        for relationship in relationships:
            edge_key = (relationship['source'], relationship['target'])
            if edge_key not in existing_edges:
                self.knowledge_graph['edges'].append(relationship)
            else:
                # 更新现有边
                existing_edges[edge_key]['strength'] = max(
                    existing_edges[edge_key].get('strength', 0),
                    relationship.get('strength', 0)
                )
                existing_edges[edge_key]['last_updated'] = datetime.datetime.now().isoformat()
        
        # 更新元数据
        self.knowledge_graph['metadata']['last_updated'] = datetime.datetime.now().isoformat()
        self.knowledge_graph['metadata']['nodes_count'] = len(self.knowledge_graph.get('nodes', []))
        self.knowledge_graph['metadata']['edges_count'] = len(self.knowledge_graph.get('edges', []))
    
    def get_integration_summary(self) -> Dict:
        """获取整合摘要"""
        return {
            'total_integrations': len(self.integration_log),
            'total_concepts': len(self.knowledge_graph.get('nodes', [])),
            'total_relationships': len(self.knowledge_graph.get('edges', [])),
            'total_contradictions': len(self.contradictions),
            'recent_integrations': self.integration_log[-5:] if self.integration_log else [],
            'integration_effectiveness': self.calculate_integration_effectiveness()
        }
    
    def calculate_integration_effectiveness(self) -> float:
        """计算整合效果"""
        if not self.integration_log:
            return 0.0
        
        # 计算成功率
        successful_integrations = sum(1 for log in self.integration_log if log.get('status') == 'success')
        total_integrations = len(self.integration_log)
        
        success_rate = successful_integrations / total_integrations if total_integrations > 0 else 0
        
        # 计算知识增长速度
        total_concepts = len(self.knowledge_graph.get('nodes', []))
        total_relationships = len(self.knowledge_graph.get('edges', []))
        
        # 综合效果分数
        effectiveness = min(1.0, (success_rate * 0.4 + 
                                 min(1.0, total_concepts / 100) * 0.3 + 
                                 min(1.0, total_relationships / 200) * 0.3))
        
        return effectiveness

def main():
    """主函数 - 用于测试"""
    integrator = KnowledgeIntegrator()
    
    # 测试新知识
    test_knowledge = {
        'topic': 'AI意识研究',
        'content': '最近的研究表明，AI意识可能与全局工作空间理论有关。意识是信息在全局工作空间中广播的结果。',
        'source': 'research_paper',
        'timestamp': datetime.datetime.now().isoformat()
    }
    
    # 整合新知识
    result = integrator.integrate_knowledge(test_knowledge)
    
    print("知识整合结果:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    print("\n整合摘要:")
    summary = integrator.get_integration_summary()
    print(json.dumps(summary, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()