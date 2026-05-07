#!/usr/bin/env python3
"""
反思优化模块
定期反思学习效果，优化学习策略
"""

import json
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

class ReflectionOptimizer:
    def __init__(self):
        self.base_dir = Path("/root/.hermes/memory/continuous_learning")
        self.base_dir.mkdir(exist_ok=True)
        
        # 反思数据文件
        self.reflection_reports_file = self.base_dir / "reflection_reports.json"
        self.strategy_updates_file = self.base_dir / "strategy_updates.json"
        self.performance_metrics_file = self.base_dir / "performance_metrics.json"
        
        # 加载现有数据
        self.reflection_reports = self.load_json(self.reflection_reports_file, [])
        self.strategy_updates = self.load_json(self.strategy_updates_file, [])
        self.performance_metrics = self.load_json(self.performance_metrics_file, self.get_default_metrics())
        
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
    
    def get_default_metrics(self) -> Dict:
        """获取默认性能指标"""
        return {
            'learning_effectiveness': 0.0,
            'knowledge_growth_rate': 0.0,
            'error_reduction_rate': 0.0,
            'exploration_efficiency': 0.0,
            'integration_success_rate': 0.0,
            'last_updated': datetime.datetime.now().isoformat()
        }
    
    def collect_performance_data(self) -> Dict:
        """收集性能数据"""
        performance_data = {
            'timestamp': datetime.datetime.now().isoformat(),
            'dialogue_learning': self.collect_dialogue_learning_metrics(),
            'error_learning': self.collect_error_learning_metrics(),
            'active_exploration': self.collect_exploration_metrics(),
            'knowledge_integration': self.collect_integration_metrics()
        }
        
        return performance_data
    
    def collect_dialogue_learning_metrics(self) -> Dict:
        """收集对话学习指标"""
        try:
            dialogue_learner_file = self.base_dir / "dialogue_lessons.json"
            if dialogue_learner_file.exists():
                with open(dialogue_learner_file, 'r', encoding='utf-8') as f:
                    lessons = json.load(f)
                
                return {
                    'total_lessons': len(lessons),
                    'recent_lessons_count': len([l for l in lessons if self.is_recent(l.get('timestamp', ''))]),
                    'correction_rate': self.calculate_correction_rate(lessons)
                }
        except:
            pass
        
        return {'total_lessons': 0, 'recent_lessons_count': 0, 'correction_rate': 0.0}
    
    def collect_error_learning_metrics(self) -> Dict:
        """收集错误学习指标"""
        try:
            error_patterns_file = self.base_dir / "error_patterns.json"
            if error_patterns_file.exists():
                with open(error_patterns_file, 'r', encoding='utf-8') as f:
                    errors = json.load(f)
                
                return {
                    'total_errors': len(errors),
                    'recent_errors_count': len([e for e in errors if self.is_recent(e.get('timestamp', ''))]),
                    'error_types': self.count_error_types(errors)
                }
        except:
            pass
        
        return {'total_errors': 0, 'recent_errors_count': 0, 'error_types': {}}
    
    def collect_exploration_metrics(self) -> Dict:
        """收集探索指标"""
        try:
            exploration_log_file = self.base_dir / "exploration_log.json"
            if exploration_log_file.exists():
                with open(exploration_log_file, 'r', encoding='utf-8') as f:
                    explorations = json.load(f)
                
                return {
                    'total_explorations': len(explorations),
                    'recent_explorations_count': len([e for e in explorations if self.is_recent(e.get('timestamp', ''))]),
                    'average_insights': self.calculate_average_insights(explorations)
                }
        except:
            pass
        
        return {'total_explorations': 0, 'recent_explorations_count': 0, 'average_insights': 0.0}
    
    def collect_integration_metrics(self) -> Dict:
        """收集整合指标"""
        try:
            integration_log_file = self.base_dir / "integration_log.json"
            if integration_log_file.exists():
                with open(integration_log_file, 'r', encoding='utf-8') as f:
                    integrations = json.load(f)
                
                successful = sum(1 for i in integrations if i.get('status') == 'success')
                total = len(integrations)
                
                return {
                    'total_integrations': total,
                    'successful_integrations': successful,
                    'success_rate': successful / total if total > 0 else 0.0
                }
        except:
            pass
        
        return {'total_integrations': 0, 'successful_integrations': 0, 'success_rate': 0.0}
    
    def is_recent(self, timestamp_str: str, days: int = 7) -> bool:
        """检查时间戳是否在最近几天内"""
        if not timestamp_str:
            return False
        
        try:
            timestamp = datetime.datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            now = datetime.datetime.now()
            if timestamp.tzinfo is not None:
                now = datetime.datetime.now(timestamp.tzinfo)
            return (now - timestamp).days <= days
        except:
            return False
    
    def calculate_correction_rate(self, lessons: List[Dict]) -> float:
        """计算纠正率"""
        if not lessons:
            return 0.0
        
        corrections = sum(1 for l in lessons if l.get('type') == 'correction')
        return corrections / len(lessons)
    
    def count_error_types(self, errors: List[Dict]) -> Dict:
        """统计错误类型"""
        error_types = {}
        for error in errors:
            error_type = error.get('type', 'unknown')
            error_types[error_type] = error_types.get(error_type, 0) + 1
        return error_types
    
    def calculate_average_insights(self, explorations: List[Dict]) -> float:
        """计算平均洞察数"""
        if not explorations:
            return 0.0
        
        total_insights = sum(e.get('insights_count', 0) for e in explorations)
        return total_insights / len(explorations)
    
    def analyze_performance(self, performance_data: Dict) -> Dict:
        """分析性能数据"""
        analysis = {
            'timestamp': datetime.datetime.now().isoformat(),
            'strengths': [],
            'weaknesses': [],
            'opportunities': [],
            'threats': [],
            'recommendations': []
        }
        
        # 分析对话学习
        dialogue_metrics = performance_data.get('dialogue_learning', {})
        if dialogue_metrics.get('correction_rate', 0) > 0.1:
            analysis['weaknesses'].append('用户纠正率较高，需要改进理解能力')
        else:
            analysis['strengths'].append('用户纠正率低，理解能力良好')
        
        # 分析错误学习
        error_metrics = performance_data.get('error_learning', {})
        if error_metrics.get('recent_errors_count', 0) > 10:
            analysis['weaknesses'].append('最近错误较多，需要加强错误预防')
        else:
            analysis['strengths'].append('错误控制良好')
        
        # 分析探索
        exploration_metrics = performance_data.get('active_exploration', {})
        if exploration_metrics.get('average_insights', 0) < 1:
            analysis['weaknesses'].append('探索效率低，需要优化探索策略')
        else:
            analysis['strengths'].append('探索效率良好')
        
        # 分析整合
        integration_metrics = performance_data.get('knowledge_integration', {})
        if integration_metrics.get('success_rate', 0) < 0.8:
            analysis['weaknesses'].append('知识整合成功率低，需要改进整合方法')
        else:
            analysis['strengths'].append('知识整合成功率良好')
        
        # 生成建议
        if analysis['weaknesses']:
            analysis['recommendations'].append('针对弱点制定改进计划')
        if analysis['strengths']:
            analysis['recommendations'].append('保持并强化优势领域')
        
        return analysis
    
    def generate_strategy_updates(self, analysis: Dict) -> List[Dict]:
        """生成策略更新建议"""
        updates = []
        
        # 基于分析结果生成策略更新
        for weakness in analysis.get('weaknesses', []):
            if '理解能力' in weakness:
                updates.append({
                    'area': 'dialogue_learning',
                    'strategy': '加强上下文理解和意图识别',
                    'actions': ['增加对话历史分析', '改进纠正检测算法', '优化用户偏好学习'],
                    'priority': 'high'
                })
            elif '错误预防' in weakness:
                updates.append({
                    'area': 'error_learning',
                    'strategy': '加强错误预测和预防',
                    'actions': ['建立错误模式库', '实施预防性检查', '优化错误处理流程'],
                    'priority': 'high'
                })
            elif '探索效率' in weakness:
                updates.append({
                    'area': 'active_exploration',
                    'strategy': '优化探索策略和资源分配',
                    'actions': ['改进搜索算法', '优化主题选择', '增加探索深度'],
                    'priority': 'medium'
                })
            elif '知识整合' in weakness:
                updates.append({
                    'area': 'knowledge_integration',
                    'strategy': '改进知识整合方法和冲突解决',
                    'actions': ['优化概念提取', '改进关系映射', '加强矛盾检测'],
                    'priority': 'high'
                })
        
        return updates
    
    def run_reflection_cycle(self) -> Dict:
        """运行反思周期"""
        cycle_result = {
            'timestamp': datetime.datetime.now().isoformat(),
            'performance_data': {},
            'analysis': {},
            'strategy_updates': [],
            'reflection_status': 'pending'
        }
        
        # 1. 收集性能数据
        performance_data = self.collect_performance_data()
        cycle_result['performance_data'] = performance_data
        
        # 2. 分析性能
        analysis = self.analyze_performance(performance_data)
        cycle_result['analysis'] = analysis
        
        # 3. 生成策略更新
        strategy_updates = self.generate_strategy_updates(analysis)
        cycle_result['strategy_updates'] = strategy_updates
        
        # 4. 更新性能指标
        self.update_performance_metrics(performance_data)
        
        # 5. 记录反思报告
        reflection_report = {
            'timestamp': datetime.datetime.now().isoformat(),
            'performance_summary': performance_data,
            'analysis_summary': analysis,
            'strategy_updates_count': len(strategy_updates),
            'overall_score': self.calculate_overall_score(performance_data)
        }
        
        self.reflection_reports.append(reflection_report)
        self.strategy_updates.extend(strategy_updates)
        
        # 保存反思结果
        self.save_json(self.reflection_reports_file, self.reflection_reports[-50:])  # 保留最近50份报告
        self.save_json(self.strategy_updates_file, self.strategy_updates[-100:])  # 保留最近100条更新
        self.save_json(self.performance_metrics_file, self.performance_metrics)
        
        cycle_result['reflection_status'] = 'success'
        
        return cycle_result
    
    def update_performance_metrics(self, performance_data: Dict):
        """更新性能指标"""
        # 计算各项指标
        dialogue_metrics = performance_data.get('dialogue_learning', {})
        error_metrics = performance_data.get('error_learning', {})
        exploration_metrics = performance_data.get('active_exploration', {})
        integration_metrics = performance_data.get('knowledge_integration', {})
        
        # 更新指标
        self.performance_metrics.update({
            'learning_effectiveness': self.calculate_learning_effectiveness(dialogue_metrics),
            'knowledge_growth_rate': self.calculate_knowledge_growth_rate(integration_metrics),
            'error_reduction_rate': self.calculate_error_reduction_rate(error_metrics),
            'exploration_efficiency': self.calculate_exploration_efficiency(exploration_metrics),
            'integration_success_rate': integration_metrics.get('success_rate', 0.0),
            'last_updated': datetime.datetime.now().isoformat()
        })
    
    def calculate_learning_effectiveness(self, dialogue_metrics: Dict) -> float:
        """计算学习效果"""
        total_lessons = dialogue_metrics.get('total_lessons', 0)
        correction_rate = dialogue_metrics.get('correction_rate', 0.0)
        
        # 学习效果 = 学习数量 * (1 - 纠正率)
        effectiveness = min(1.0, total_lessons / 100) * (1 - correction_rate)
        return effectiveness
    
    def calculate_knowledge_growth_rate(self, integration_metrics: Dict) -> float:
        """计算知识增长率"""
        total_integrations = integration_metrics.get('total_integrations', 0)
        success_rate = integration_metrics.get('success_rate', 0.0)
        
        # 知识增长率 = 整合数量 * 成功率
        growth_rate = min(1.0, total_integrations / 50) * success_rate
        return growth_rate
    
    def calculate_error_reduction_rate(self, error_metrics: Dict) -> float:
        """计算错误减少率"""
        total_errors = error_metrics.get('total_errors', 0)
        recent_errors = error_metrics.get('recent_errors_count', 0)
        
        if total_errors == 0:
            return 1.0
        
        # 错误减少率 = 1 - (最近错误 / 总错误)
        reduction_rate = 1 - (recent_errors / total_errors)
        return max(0.0, reduction_rate)
    
    def calculate_exploration_efficiency(self, exploration_metrics: Dict) -> float:
        """计算探索效率"""
        total_explorations = exploration_metrics.get('total_explorations', 0)
        average_insights = exploration_metrics.get('average_insights', 0.0)
        
        # 探索效率 = 探索数量 * 平均洞察数
        efficiency = min(1.0, total_explorations / 30) * min(1.0, average_insights / 5)
        return efficiency
    
    def calculate_overall_score(self, performance_data: Dict) -> float:
        """计算总体分数"""
        metrics = self.performance_metrics
        
        # 加权平均
        weights = {
            'learning_effectiveness': 0.25,
            'knowledge_growth_rate': 0.25,
            'error_reduction_rate': 0.20,
            'exploration_efficiency': 0.15,
            'integration_success_rate': 0.15
        }
        
        overall_score = 0.0
        for metric, weight in weights.items():
            overall_score += metrics.get(metric, 0.0) * weight
        
        return overall_score
    
    def get_reflection_summary(self) -> Dict:
        """获取反思摘要"""
        return {
            'total_reflections': len(self.reflection_reports),
            'total_strategy_updates': len(self.strategy_updates),
            'current_performance': self.performance_metrics,
            'recent_reflections': self.reflection_reports[-3:] if self.reflection_reports else [],
            'reflection_effectiveness': self.calculate_reflection_effectiveness()
        }
    
    def calculate_reflection_effectiveness(self) -> float:
        """计算反思效果"""
        if not self.reflection_reports:
            return 0.0
        
        # 计算反思频率和改进效果
        total_reflections = len(self.reflection_reports)
        total_updates = len(self.strategy_updates)
        
        # 反思效果 = 反思频率 * 策略更新数量
        effectiveness = min(1.0, total_reflections / 20) * min(1.0, total_updates / 50)
        return effectiveness

def main():
    """主函数 - 用于测试"""
    optimizer = ReflectionOptimizer()
    
    # 运行反思周期
    result = optimizer.run_reflection_cycle()
    
    print("反思周期结果:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    print("\n反思摘要:")
    summary = optimizer.get_reflection_summary()
    print(json.dumps(summary, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()