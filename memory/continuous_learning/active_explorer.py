#!/usr/bin/env python3
"""
主动探索模块
主动搜索和学习新知识
"""

import json
import datetime
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional

class ActiveExplorer:
    def __init__(self):
        self.base_dir = Path("/root/.hermes/memory/continuous_learning")
        self.base_dir.mkdir(exist_ok=True)
        
        # 探索数据文件
        self.exploration_log_file = self.base_dir / "exploration_log.json"
        self.knowledge_connections_file = self.base_dir / "knowledge_connections.json"
        self.exploration_topics_file = self.base_dir / "exploration_topics.json"
        
        # 加载现有数据
        self.exploration_log = self.load_json(self.exploration_log_file, [])
        self.knowledge_connections = self.load_json(self.knowledge_connections_file, [])
        self.exploration_topics = self.load_json(self.exploration_topics_file, self.get_default_topics())
        
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
    
    def get_default_topics(self) -> Dict:
        """获取默认探索主题"""
        return {
            'priority_topics': [
                {
                    'name': 'AI意识研究',
                    'description': '探索AI意识的最新研究进展',
                    'keywords': ['AI意识', '机器意识', '人工智能意识'],
                    'frequency': 'weekly'
                },
                {
                    'name': '记忆系统优化',
                    'description': '学习记忆系统的最新技术和方法',
                    'keywords': ['记忆系统', '知识图谱', '记忆网络'],
                    'frequency': 'weekly'
                },
                {
                    'name': '持续学习算法',
                    'description': '研究持续学习的最新算法和框架',
                    'keywords': ['持续学习', '增量学习', '终身学习'],
                    'frequency': 'weekly'
                },
                {
                    'name': '元认知系统',
                    'description': '探索元认知和自我监控的最新研究',
                    'keywords': ['元认知', '自我监控', '认知架构'],
                    'frequency': 'biweekly'
                }
            ],
            'exploration_history': [],
            'last_exploration': None
        }
    
    def search_web(self, query: str) -> Dict:
        """搜索网页内容"""
        try:
            # 使用curl进行简单的网页搜索
            cmd = f'curl -s "https://lite.duckduckgo.com/lite/?q={query}" | grep -oP \'(?<=<a rel="nofollow" href=")[^"]+\' | head -5'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                urls = result.stdout.strip().split('\n')
                return {
                    'query': query,
                    'urls': [url for url in urls if url],
                    'timestamp': datetime.datetime.now().isoformat()
                }
            else:
                return {
                    'query': query,
                    'error': result.stderr,
                    'timestamp': datetime.datetime.now().isoformat()
                }
                
        except Exception as e:
            return {
                'query': query,
                'error': str(e),
                'timestamp': datetime.datetime.now().isoformat()
            }
    
    def explore_topic(self, topic: Dict) -> Dict:
        """探索特定主题"""
        exploration_result = {
            'topic': topic['name'],
            'timestamp': datetime.datetime.now().isoformat(),
            'search_results': [],
            'insights': [],
            'connections': []
        }
        
        # 搜索每个关键词
        for keyword in topic.get('keywords', []):
            search_result = self.search_web(keyword)
            exploration_result['search_results'].append(search_result)
            
            # 分析搜索结果，提取洞察
            if 'urls' in search_result and search_result['urls']:
                insight = {
                    'keyword': keyword,
                    'source_count': len(search_result['urls']),
                    'top_sources': search_result['urls'][:3],
                    'analysis': f"找到{len(search_result['urls'])}个相关资源"
                }
                exploration_result['insights'].append(insight)
        
        # 尝试建立知识连接
        connections = self.find_connections(topic, exploration_result['insights'])
        exploration_result['connections'] = connections
        
        return exploration_result
    
    def find_connections(self, topic: Dict, insights: List[Dict]) -> List[Dict]:
        """发现知识连接"""
        connections = []
        
        # 基于关键词建立连接
        for insight in insights:
            keyword = insight.get('keyword', '')
            if keyword:
                connection = {
                    'source_topic': topic['name'],
                    'connected_keyword': keyword,
                    'connection_type': 'keyword_match',
                    'strength': 0.7,  # 默认连接强度
                    'timestamp': datetime.datetime.now().isoformat()
                }
                connections.append(connection)
        
        return connections
    
    def run_exploration_cycle(self) -> Dict:
        """运行探索周期"""
        cycle_result = {
            'timestamp': datetime.datetime.now().isoformat(),
            'topics_explored': 0,
            'total_insights': 0,
            'total_connections': 0,
            'explorations': []
        }
        
        # 获取优先探索主题
        priority_topics = self.exploration_topics.get('priority_topics', [])
        
        # 确定本次要探索的主题数量（每次探索1-2个主题）
        topics_to_explore = priority_topics[:2]
        
        for topic in topics_to_explore:
            exploration = self.explore_topic(topic)
            cycle_result['explorations'].append(exploration)
            cycle_result['topics_explored'] += 1
            cycle_result['total_insights'] += len(exploration.get('insights', []))
            cycle_result['total_connections'] += len(exploration.get('connections', []))
            
            # 记录探索历史
            self.exploration_log.append({
                'topic': topic['name'],
                'timestamp': datetime.datetime.now().isoformat(),
                'insights_count': len(exploration.get('insights', [])),
                'connections_count': len(exploration.get('connections', []))
            })
            
            # 更新知识连接
            self.knowledge_connections.extend(exploration.get('connections', []))
        
        # 更新探索主题
        self.exploration_topics['last_exploration'] = datetime.datetime.now().isoformat()
        self.exploration_topics['exploration_history'].append({
            'timestamp': datetime.datetime.now().isoformat(),
            'topics_count': cycle_result['topics_explored'],
            'insights_count': cycle_result['total_insights']
        })
        
        # 保存探索结果
        self.save_json(self.exploration_log_file, self.exploration_log[-100:])  # 保留最近100次探索
        self.save_json(self.knowledge_connections_file, self.knowledge_connections[-500:])  # 保留最近500个连接
        self.save_json(self.exploration_topics_file, self.exploration_topics)
        
        return cycle_result
    
    def get_exploration_summary(self) -> Dict:
        """获取探索摘要"""
        return {
            'total_explorations': len(self.exploration_log),
            'total_connections': len(self.knowledge_connections),
            'recent_explorations': self.exploration_log[-5:] if self.exploration_log else [],
            'common_connections': self.get_common_connections(),
            'exploration_effectiveness': self.calculate_exploration_effectiveness()
        }
    
    def get_common_connections(self) -> List[Dict]:
        """获取常见的知识连接"""
        connection_counts = {}
        for conn in self.knowledge_connections:
            topic = conn.get('source_topic', 'unknown')
            connection_counts[topic] = connection_counts.get(topic, 0) + 1
        
        return [{'topic': k, 'count': v} for k, v in sorted(connection_counts.items(), key=lambda x: x[1], reverse=True)[:5]]
    
    def calculate_exploration_effectiveness(self) -> float:
        """计算探索效果"""
        if not self.exploration_log:
            return 0.0
        
        # 计算探索频率和洞察数量
        total_explorations = len(self.exploration_log)
        total_insights = sum(log.get('insights_count', 0) for log in self.exploration_log)
        
        # 计算时间跨度
        if len(self.exploration_log) > 1:
            first_timestamp = self.exploration_log[0].get('timestamp', '')
            last_timestamp = self.exploration_log[-1].get('timestamp', '')
            
            if first_timestamp and last_timestamp:
                try:
                    first_time = datetime.datetime.fromisoformat(first_timestamp)
                    last_time = datetime.datetime.fromisoformat(last_timestamp)
                    time_span_days = (last_time - first_time).days
                    
                    if time_span_days > 0:
                        # 探索频率（每天探索次数）
                        exploration_frequency = total_explorations / time_span_days
                        # 洞察密度（每次探索的洞察数）
                        insight_density = total_insights / total_explorations if total_explorations > 0 else 0
                        
                        # 综合效果分数
                        effectiveness = min(1.0, (exploration_frequency * 0.3 + insight_density * 0.7))
                        return effectiveness
                except:
                    pass
        
        # 默认返回基于总探索次数的分数
        return min(1.0, total_explorations / 50)  # 假设50次探索为满分

def main():
    """主函数 - 用于测试"""
    explorer = ActiveExplorer()
    
    # 运行探索周期
    result = explorer.run_exploration_cycle()
    
    print("探索周期结果:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    print("\n探索摘要:")
    summary = explorer.get_exploration_summary()
    print(json.dumps(summary, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()