#!/usr/bin/env python3
"""
错误学习模块
从错误和失败中学习
"""

import json
import re
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

class ErrorLearner:
    def __init__(self):
        self.base_dir = Path("/root/.hermes/memory/continuous_learning")
        self.base_dir.mkdir(exist_ok=True)
        
        # 错误学习数据文件
        self.error_patterns_file = self.base_dir / "error_patterns.json"
        self.knowledge_gaps_file = self.base_dir / "knowledge_gaps.json"
        self.error_solutions_file = self.base_dir / "error_solutions.json"
        
        # 加载现有数据
        self.error_patterns = self.load_json(self.error_patterns_file, [])
        self.knowledge_gaps = self.load_json(self.knowledge_gaps_file, [])
        self.error_solutions = self.load_json(self.error_solutions_file, {})
        
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
    
    def parse_error_log(self, log_file: Path) -> List[Dict]:
        """解析错误日志文件"""
        errors = []
        
        if not log_file.exists():
            return errors
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 分割不同的错误条目
            error_blocks = re.split(r'\n\d{4}-\d{2}-\d{2}', content)
            
            for block in error_blocks:
                if not block.strip():
                    continue
                
                # 提取时间戳
                timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', block)
                timestamp = timestamp_match.group(1) if timestamp_match else ""
                
                # 提取错误类型
                error_type = "unknown"
                if "ERROR" in block:
                    error_type = "error"
                elif "WARNING" in block:
                    error_type = "warning"
                elif "Traceback" in block:
                    error_type = "exception"
                
                # 提取错误信息
                error_message = ""
                if "Traceback" in block:
                    # 提取异常信息
                    lines = block.split('\n')
                    for i, line in enumerate(lines):
                        if line.strip().startswith('File ') or line.strip().startswith('Exception') or line.strip().startswith('Error'):
                            error_message = line.strip()
                            break
                else:
                    # 提取一般错误信息
                    lines = block.split('\n')
                    for line in lines:
                        if line.strip() and not line.startswith(' '):
                            error_message = line.strip()
                            break
                
                # 提取模块信息
                module_match = re.search(r'([\w.]+):', block)
                module = module_match.group(1) if module_match else "unknown"
                
                if error_message:
                    errors.append({
                        'timestamp': timestamp,
                        'type': error_type,
                        'module': module,
                        'message': error_message,
                        'full_block': block[:500]  # 限制长度
                    })
        
        except Exception as e:
            print(f"解析错误日志失败: {e}")
        
        return errors
    
    def analyze_error_patterns(self, errors: List[Dict]) -> Dict:
        """分析错误模式"""
        patterns = {
            'by_type': {},
            'by_module': {},
            'frequency': {},
            'time_distribution': {}
        }
        
        for error in errors:
            # 按类型统计
            error_type = error.get('type', 'unknown')
            patterns['by_type'][error_type] = patterns['by_type'].get(error_type, 0) + 1
            
            # 按模块统计
            module = error.get('module', 'unknown')
            patterns['by_module'][module] = patterns['by_module'].get(module, 0) + 1
            
            # 频率统计
            message = error.get('message', '')
            if message:
                # 简化消息用于统计
                simplified = re.sub(r'[\d]+', 'N', message)  # 将数字替换为N
                patterns['frequency'][simplified] = patterns['frequency'].get(simplified, 0) + 1
            
            # 时间分布
            timestamp = error.get('timestamp', '')
            if timestamp:
                try:
                    dt = datetime.datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                    hour = dt.hour
                    patterns['time_distribution'][hour] = patterns['time_distribution'].get(hour, 0) + 1
                except:
                    pass
        
        return patterns
    
    def identify_knowledge_gaps(self, errors: List[Dict]) -> List[Dict]:
        """识别知识盲点"""
        gaps = []
        
        # 常见错误模式及其对应的知识盲点
        gap_indicators = {
            'ModuleNotFoundError': '缺少必要的Python模块',
            'ImportError': '导入错误，可能是模块不存在或路径问题',
            'FileNotFoundError': '文件路径错误或文件不存在',
            'PermissionError': '权限不足',
            'ConnectionError': '网络连接问题',
            'TimeoutError': '操作超时',
            'ValueError': '参数值错误',
            'TypeError': '类型错误',
            'KeyError': '键不存在',
            'AttributeError': '属性不存在',
            'IndexError': '索引越界',
            'SyntaxError': '语法错误',
            'NameError': '名称未定义',
            'ZeroDivisionError': '除零错误',
            'MemoryError': '内存不足',
            'RecursionError': '递归过深'
        }
        
        for error in errors:
            message = error.get('message', '')
            
            # 检查是否匹配已知错误模式
            for pattern, description in gap_indicators.items():
                if pattern in message:
                    gaps.append({
                        'error_pattern': pattern,
                        'description': description,
                        'example': message,
                        'timestamp': error.get('timestamp', ''),
                        'module': error.get('module', 'unknown')
                    })
                    break
        
        return gaps
    
    def learn_from_errors(self, log_files: List[Path]) -> Dict:
        """从错误中学习"""
        learning_results = {
            'timestamp': datetime.datetime.now().isoformat(),
            'files_analyzed': len(log_files),
            'total_errors': 0,
            'patterns': {},
            'knowledge_gaps': [],
            'solutions': []
        }
        
        all_errors = []
        
        # 分析所有错误日志
        for log_file in log_files:
            errors = self.parse_error_log(log_file)
            all_errors.extend(errors)
        
        learning_results['total_errors'] = len(all_errors)
        
        if all_errors:
            # 分析错误模式
            patterns = self.analyze_error_patterns(all_errors)
            learning_results['patterns'] = patterns
            
            # 识别知识盲点
            gaps = self.identify_knowledge_gaps(all_errors)
            learning_results['knowledge_gaps'] = gaps
            
            # 更新错误模式库
            self.error_patterns.extend([{
                'timestamp': error.get('timestamp', ''),
                'type': error.get('type', 'unknown'),
                'module': error.get('module', 'unknown'),
                'message': error.get('message', '')
            } for error in all_errors])
            
            # 更新知识盲点库
            self.knowledge_gaps.extend(gaps)
            
            # 生成解决方案建议
            solutions = self.generate_solutions(all_errors, gaps)
            learning_results['solutions'] = solutions
            
            # 保存学习结果
            self.save_json(self.error_patterns_file, self.error_patterns[-1000:])  # 保留最近1000条
            self.save_json(self.knowledge_gaps_file, self.knowledge_gaps[-500:])  # 保留最近500条
        
        return learning_results
    
    def generate_solutions(self, errors: List[Dict], gaps: List[Dict]) -> List[Dict]:
        """生成解决方案建议"""
        solutions = []
        
        # 基于错误模式生成解决方案
        error_counts = {}
        for error in errors:
            message = error.get('message', '')
            if message:
                simplified = re.sub(r'[\d]+', 'N', message)
                error_counts[simplified] = error_counts.get(simplified, 0) + 1
        
        # 为最常见的错误生成解决方案
        for pattern, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            solution = {
                'error_pattern': pattern,
                'frequency': count,
                'suggested_actions': []
            }
            
            # 根据错误类型生成建议
            if 'ModuleNotFoundError' in pattern:
                solution['suggested_actions'] = [
                    '检查Python环境',
                    '安装缺少的模块: pip install <module_name>',
                    '检查虚拟环境是否正确激活'
                ]
            elif 'FileNotFoundError' in pattern:
                solution['suggested_actions'] = [
                    '检查文件路径是否正确',
                    '确认文件是否存在',
                    '检查文件权限'
                ]
            elif 'ConnectionError' in pattern:
                solution['suggested_actions'] = [
                    '检查网络连接',
                    '确认服务是否可用',
                    '检查防火墙设置'
                ]
            elif 'PermissionError' in pattern:
                solution['suggested_actions'] = [
                    '检查文件权限',
                    '使用sudo运行（如果需要）',
                    '检查用户权限'
                ]
            else:
                solution['suggested_actions'] = [
                    '查看完整错误日志',
                    '搜索相关文档',
                    '检查代码逻辑'
                ]
            
            solutions.append(solution)
        
        return solutions
    
    def get_learning_summary(self) -> Dict:
        """获取学习摘要"""
        return {
            'total_error_patterns': len(self.error_patterns),
            'total_knowledge_gaps': len(self.knowledge_gaps),
            'recent_errors': self.error_patterns[-10:] if self.error_patterns else [],
            'common_gaps': self.get_common_gaps(),
            'learning_effectiveness': self.calculate_learning_effectiveness()
        }
    
    def get_common_gaps(self) -> List[Dict]:
        """获取常见的知识盲点"""
        gap_counts = {}
        for gap in self.knowledge_gaps:
            pattern = gap.get('error_pattern', 'unknown')
            gap_counts[pattern] = gap_counts.get(pattern, 0) + 1
        
        return [{'pattern': k, 'count': v} for k, v in sorted(gap_counts.items(), key=lambda x: x[1], reverse=True)[:5]]
    
    def calculate_learning_effectiveness(self) -> float:
        """计算学习效果"""
        if not self.error_patterns:
            return 0.0
        
        # 计算错误减少率（简化计算）
        total_errors = len(self.error_patterns)
        
        # 计算时间跨度
        if len(self.error_patterns) > 1:
            first_timestamp = self.error_patterns[0].get('timestamp', '')
            last_timestamp = self.error_patterns[-1].get('timestamp', '')
            
            if first_timestamp and last_timestamp:
                try:
                    first_time = datetime.datetime.strptime(first_timestamp, '%Y-%m-%d %H:%M:%S')
                    last_time = datetime.datetime.strptime(last_timestamp, '%Y-%m-%d %H:%M:%S')
                    time_span_days = (last_time - first_time).days
                    
                    if time_span_days > 0:
                        # 错误频率（每天错误次数）
                        error_frequency = total_errors / time_span_days
                        # 学习效果分数（错误越少，效果越好）
                        effectiveness = max(0.0, 1.0 - (error_frequency / 100))  # 假设每天100个错误为最差
                        return effectiveness
                except:
                    pass
        
        # 默认返回基于总错误数的分数
        return max(0.0, 1.0 - (total_errors / 1000))  # 假设1000个错误为最差

def main():
    """主函数 - 用于测试"""
    learner = ErrorLearner()
    
    # 测试错误日志文件
    log_files = [
        Path("/root/.hermes/logs/errors.log"),
        Path("/root/.hermes/cache/binance-volume-monitor/monitor.log"),
        Path("/root/.hermes/cache/okx-signal-auto-buy/events.log")
    ]
    
    # 从错误中学习
    results = learner.learn_from_errors(log_files)
    
    print("错误学习结果:")
    print(json.dumps(results, indent=2, ensure_ascii=False))
    
    print("\n学习摘要:")
    summary = learner.get_learning_summary()
    print(json.dumps(summary, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()