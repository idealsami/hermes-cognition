#!/usr/bin/env python3
"""
对话学习模块
从每次对话中提取学习内容
"""

import json
import re
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

class DialogueLearner:
    def __init__(self):
        self.base_dir = Path("/root/.hermes/memory/continuous_learning")
        self.base_dir.mkdir(exist_ok=True)
        
        # 学习数据文件
        self.dialogue_lessons_file = self.base_dir / "dialogue_lessons.json"
        self.user_preferences_file = self.base_dir / "user_preferences.json"
        
        # 加载现有数据
        self.dialogue_lessons = self.load_json(self.dialogue_lessons_file, [])
        self.user_preferences = self.load_json(self.user_preferences_file, {})
        
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
    
    def extract_user_corrections(self, dialogue: List[Dict]) -> List[Dict]:
        """提取用户纠正内容"""
        corrections = []
        
        for i, message in enumerate(dialogue):
            if message.get('role') == 'user':
                content = message.get('content', '')
                
                # 检测纠正模式
                correction_patterns = [
                    r'不是.*而是',
                    r'应该.*而不是',
                    r'错了.*正确的是',
                    r'我纠正一下',
                    r'你理解错了',
                    r'我的意思是',
                    r'不对.*应该是',
                ]
                
                for pattern in correction_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        corrections.append({
                            'timestamp': datetime.datetime.now().isoformat(),
                            'user_message': content,
                            'context': dialogue[max(0, i-2):i],  # 前两条消息作为上下文
                            'type': 'correction'
                        })
                        break
        
        return corrections
    
    def extract_user_preferences(self, dialogue: List[Dict]) -> Dict:
        """提取用户偏好"""
        preferences = {}
        
        for message in dialogue:
            if message.get('role') == 'user':
                content = message.get('content', '').lower()
                
                # 沟通风格偏好
                if any(word in content for word in ['简洁', '直接', '简短']):
                    preferences['communication_style'] = 'concise'
                elif any(word in content for word in ['详细', '详细解释', '展开说']):
                    preferences['communication_style'] = 'detailed'
                
                # 技术偏好
                if any(word in content for word in ['代码', '脚本', '程序']):
                    preferences['technical_level'] = 'advanced'
                elif any(word in content for word in ['简单', '易懂', '通俗']):
                    preferences['technical_level'] = 'beginner'
                
                # 响应偏好
                if any(word in content for word in ['快速', '马上', '立即']):
                    preferences['response_speed'] = 'fast'
                elif any(word in content for word in ['仔细', '慢慢来', '不急']):
                    preferences['response_speed'] = 'thorough'
        
        return preferences
    
    def extract_knowledge_topics(self, dialogue: List[Dict]) -> List[Dict]:
        """提取知识主题"""
        topics = []
        
        for message in dialogue:
            if message.get('role') == 'user':
                content = message.get('content', '')
                
                # 识别问题模式
                question_patterns = [
                    r'什么是(.{2,20})',
                    r'如何(.{2,20})',
                    r'怎么(.{2,20})',
                    r'为什么(.{2,20})',
                    r'(.{2,20})是什么',
                ]
                
                for pattern in question_patterns:
                    matches = re.findall(pattern, content)
                    for match in matches:
                        if len(match) > 2:  # 过滤太短的匹配
                            topics.append({
                                'timestamp': datetime.datetime.now().isoformat(),
                                'topic': match.strip(),
                                'context': content,
                                'type': 'question'
                            })
        
        return topics
    
    def extract_task_patterns(self, dialogue: List[Dict]) -> List[Dict]:
        """提取任务模式"""
        patterns = []
        
        for message in dialogue:
            if message.get('role') == 'user':
                content = message.get('content', '')
                
                # 任务类型识别
                task_types = {
                    'research': ['查找', '搜索', '研究', '分析'],
                    'creation': ['创建', '制作', '写', '生成'],
                    'modification': ['修改', '更新', '调整', '优化'],
                    'explanation': ['解释', '说明', '介绍', '讲解'],
                    'troubleshooting': ['修复', '解决', '调试', '排查']
                }
                
                for task_type, keywords in task_types.items():
                    if any(keyword in content for keyword in keywords):
                        patterns.append({
                            'timestamp': datetime.datetime.now().isoformat(),
                            'task_type': task_type,
                            'keywords': [kw for kw in keywords if kw in content],
                            'context': content
                        })
                        break
        
        return patterns
    
    def learn_from_dialogue(self, dialogue: List[Dict]) -> Dict:
        """从对话中学习"""
        learning_results = {
            'timestamp': datetime.datetime.now().isoformat(),
            'dialogue_length': len(dialogue),
            'corrections': [],
            'preferences': {},
            'topics': [],
            'patterns': []
        }
        
        # 1. 提取用户纠正
        corrections = self.extract_user_corrections(dialogue)
        if corrections:
            self.dialogue_lessons.extend(corrections)
            learning_results['corrections'] = corrections
        
        # 2. 提取用户偏好
        preferences = self.extract_user_preferences(dialogue)
        if preferences:
            self.user_preferences.update(preferences)
            learning_results['preferences'] = preferences
        
        # 3. 提取知识主题
        topics = self.extract_knowledge_topics(dialogue)
        if topics:
            learning_results['topics'] = topics
        
        # 4. 提取任务模式
        patterns = self.extract_task_patterns(dialogue)
        if patterns:
            learning_results['patterns'] = patterns
        
        # 保存学习结果
        self.save_json(self.dialogue_lessons_file, self.dialogue_lessons)
        self.save_json(self.user_preferences_file, self.user_preferences)
        
        return learning_results
    
    def get_learning_summary(self) -> Dict:
        """获取学习摘要"""
        return {
            'total_lessons': len(self.dialogue_lessons),
            'user_preferences': self.user_preferences,
            'recent_lessons': self.dialogue_lessons[-10:] if self.dialogue_lessons else [],
            'learning_effectiveness': self.calculate_learning_effectiveness()
        }
    
    def calculate_learning_effectiveness(self) -> float:
        """计算学习效果"""
        if not self.dialogue_lessons:
            return 0.0
        
        # 简单计算：基于学习次数和时间跨度
        total_lessons = len(self.dialogue_lessons)
        
        # 计算时间跨度
        if len(self.dialogue_lessons) > 1:
            first_timestamp = self.dialogue_lessons[0].get('timestamp', '')
            last_timestamp = self.dialogue_lessons[-1].get('timestamp', '')
            
            if first_timestamp and last_timestamp:
                try:
                    first_time = datetime.datetime.fromisoformat(first_timestamp)
                    last_time = datetime.datetime.fromisoformat(last_timestamp)
                    time_span_days = (last_time - first_time).days
                    
                    if time_span_days > 0:
                        # 学习频率（每天学习次数）
                        learning_frequency = total_lessons / time_span_days
                        # 学习效果分数（0-1）
                        effectiveness = min(1.0, learning_frequency / 10)  # 假设每天10次学习为满分
                        return effectiveness
                except:
                    pass
        
        # 默认返回基于总学习次数的分数
        return min(1.0, total_lessons / 100)  # 假设100次学习为满分

def main():
    """主函数 - 用于测试"""
    learner = DialogueLearner()
    
    # 模拟对话
    test_dialogue = [
        {'role': 'user', 'content': '你好，我想了解Python编程'},
        {'role': 'assistant', 'content': 'Python是一种流行的编程语言...'},
        {'role': 'user', 'content': '我纠正一下，我想要的是Python数据分析，不是基础语法'},
        {'role': 'assistant', 'content': '明白了，您想要学习Python数据分析...'},
        {'role': 'user', 'content': '请详细解释一下Pandas库的使用方法'}
    ]
    
    # 从对话中学习
    results = learner.learn_from_dialogue(test_dialogue)
    
    print("学习结果:")
    print(json.dumps(results, indent=2, ensure_ascii=False))
    
    print("\n学习摘要:")
    summary = learner.get_learning_summary()
    print(json.dumps(summary, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()