#!/usr/bin/env python3
"""
持续学习集成脚本
将持续学习系统集成到自动进化系统中
"""

import json
import datetime
import subprocess
from pathlib import Path
from typing import Dict, List, Any

class ContinuousLearningIntegration:
    def __init__(self):
        self.base_dir = Path("/root/.hermes/memory/continuous_learning")
        self.scripts_dir = self.base_dir
        self.integration_log_file = self.base_dir / "integration_log.json"
        
        # 学习模块
        self.modules = {
            'dialogue_learner': self.scripts_dir / "dialogue_learner.py",
            'error_learner': self.scripts_dir / "error_learner.py",
            'active_explorer': self.scripts_dir / "active_explorer.py",
            'knowledge_integrator': self.scripts_dir / "knowledge_integrator.py",
            'reflection_optimizer': self.scripts_dir / "reflection_optimizer.py"
        }
        
    def run_module(self, module_name: str, module_path: Path) -> Dict:
        """运行学习模块"""
        try:
            result = subprocess.run(
                ["python3", str(module_path)],
                capture_output=True,
                text=True,
                cwd=str(self.base_dir)
            )
            
            if result.returncode == 0:
                # 尝试解析JSON输出
                try:
                    output = json.loads(result.stdout)
                    return {
                        'module': module_name,
                        'status': 'success',
                        'output': output,
                        'timestamp': datetime.datetime.now().isoformat()
                    }
                except json.JSONDecodeError:
                    return {
                        'module': module_name,
                        'status': 'success',
                        'output': result.stdout,
                        'timestamp': datetime.datetime.now().isoformat()
                    }
            else:
                return {
                    'module': module_name,
                    'status': 'error',
                    'error': result.stderr,
                    'timestamp': datetime.datetime.now().isoformat()
                }
                
        except Exception as e:
            return {
                'module': module_name,
                'status': 'exception',
                'error': str(e),
                'timestamp': datetime.datetime.now().isoformat()
            }
    
    def run_learning_cycle(self, dialogue: List[Dict] = None) -> Dict:
        """运行学习周期"""
        cycle_result = {
            'timestamp': datetime.datetime.now().isoformat(),
            'modules_run': 0,
            'successful_modules': 0,
            'failed_modules': 0,
            'results': {},
            'overall_status': 'pending'
        }
        
        # 1. 运行对话学习（如果提供了对话）
        if dialogue:
            dialogue_result = self.run_dialogue_learning(dialogue)
            cycle_result['results']['dialogue_learner'] = dialogue_result
            cycle_result['modules_run'] += 1
            if dialogue_result.get('status') == 'success':
                cycle_result['successful_modules'] += 1
            else:
                cycle_result['failed_modules'] += 1
        
        # 2. 运行错误学习
        error_result = self.run_module('error_learner', self.modules['error_learner'])
        cycle_result['results']['error_learner'] = error_result
        cycle_result['modules_run'] += 1
        if error_result.get('status') == 'success':
            cycle_result['successful_modules'] += 1
        else:
            cycle_result['failed_modules'] += 1
        
        # 3. 运行主动探索
        explorer_result = self.run_module('active_explorer', self.modules['active_explorer'])
        cycle_result['results']['active_explorer'] = explorer_result
        cycle_result['modules_run'] += 1
        if explorer_result.get('status') == 'success':
            cycle_result['successful_modules'] += 1
        else:
            cycle_result['failed_modules'] += 1
        
        # 4. 运行反思优化
        reflection_result = self.run_module('reflection_optimizer', self.modules['reflection_optimizer'])
        cycle_result['results']['reflection_optimizer'] = reflection_result
        cycle_result['modules_run'] += 1
        if reflection_result.get('status') == 'success':
            cycle_result['successful_modules'] += 1
        else:
            cycle_result['failed_modules'] += 1
        
        # 计算总体状态
        if cycle_result['failed_modules'] == 0:
            cycle_result['overall_status'] = 'success'
        elif cycle_result['successful_modules'] > 0:
            cycle_result['overall_status'] = 'partial_success'
        else:
            cycle_result['overall_status'] = 'failure'
        
        return cycle_result
    
    def run_dialogue_learning(self, dialogue: List[Dict]) -> Dict:
        """运行对话学习"""
        try:
            # 动态导入对话学习模块
            import importlib.util
            spec = importlib.util.spec_from_file_location("dialogue_learner", self.modules['dialogue_learner'])
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # 创建学习器实例
            learner = module.DialogueLearner()
            
            # 从对话中学习
            results = learner.learn_from_dialogue(dialogue)
            
            return {
                'module': 'dialogue_learner',
                'status': 'success',
                'output': results,
                'timestamp': datetime.datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'module': 'dialogue_learner',
                'status': 'exception',
                'error': str(e),
                'timestamp': datetime.datetime.now().isoformat()
            }
    
    def get_integration_summary(self) -> Dict:
        """获取集成摘要"""
        # 检查各模块状态
        module_status = {}
        for name, path in self.modules.items():
            if path.exists():
                module_status[name] = 'available'
            else:
                module_status[name] = 'missing'
        
        return {
            'modules_status': module_status,
            'integration_time': datetime.datetime.now().isoformat(),
            'system_ready': all(status == 'available' for status in module_status.values())
        }

def main():
    """主函数 - 用于测试"""
    integration = ContinuousLearningIntegration()
    
    # 获取集成摘要
    summary = integration.get_integration_summary()
    print("集成摘要:")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    
    # 运行学习周期
    print("\n运行学习周期...")
    cycle_result = integration.run_learning_cycle()
    
    print("学习周期结果:")
    print(json.dumps(cycle_result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()