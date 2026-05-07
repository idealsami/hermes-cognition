#!/usr/bin/env python3
"""
Hermes AGI 自动进化脚本（完整集成版）
======================================

将所有认知模块集成到统一的自动进化工作流中：

1. 工作流协调框架 (WorkflowCoordinator) - DAG任务编排
2. 向量记忆库 (VectorStore) - 语义记忆存储与检索
3. 学习素材收集 (collect_learning_materials) - arXiv/GitHub资料收集
4. 记忆系统测试 (test_memory_system) - 综合测试验证
5. 持续学习模块 - 对话/错误/探索学习
6. 知识图谱扩展 - 概念关系扩展

使用方法:
    python3 auto_evolution.py                 # 运行一次完整进化循环
    python3 auto_evolution.py --mode serial   # 串行执行
    python3 auto_evolution.py --mode parallel # 并行执行（默认）
    python3 auto_evolution.py --schedule 3600 # 每3600秒运行一次
    python3 auto_evolution.py --test-only     # 仅运行测试
    python3 auto_evolution.py --status        # 显示进化状态
"""

import os
import sys
import json
import time
import signal
import argparse
import datetime
import traceback
import subprocess
import importlib.util
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable

# ---------------------------------------------------------------------------
# 路径配置
# ---------------------------------------------------------------------------

BASE_DIR = Path("/root/.hermes/memory")
SCRIPTS_DIR = BASE_DIR / "scripts"
COGNITION_DIR = Path("/root/.hermes/cognition")
WORKFLOW_DIR = COGNITION_DIR / "workflow"
MEMORY_DIR = COGNITION_DIR / "memory"
CONTINUOUS_LEARNING_DIR = BASE_DIR / "continuous_learning"
META_DIR = BASE_DIR / "meta"
LOG_FILE = META_DIR / "evolution.log"
STATUS_FILE = META_DIR / "evolution_status.json"
VECTOR_STORE_PATH = BASE_DIR / "vector_memory.json"

# 添加路径到 sys.path 以便导入
for p in [str(COGNITION_DIR), str(SCRIPTS_DIR.parent), str(BASE_DIR.parent)]:
    if p not in sys.path:
        sys.path.insert(0, p)

# ---------------------------------------------------------------------------
# 导入各组件（优雅降级）
# ---------------------------------------------------------------------------

WORKFLOW_AVAILABLE = False
VECTOR_STORE_AVAILABLE = False
COLLECT_LEARNING_MATERIALS_AVAILABLE = False

try:
    from workflow.coordinator import WorkflowCoordinator, TaskStatus, WorkflowResult
    WORKFLOW_AVAILABLE = True
except ImportError:
    try:
        # 备选导入路径
        sys.path.insert(0, str(WORKFLOW_DIR.parent))
        from workflow.coordinator import WorkflowCoordinator, TaskStatus, WorkflowResult
        WORKFLOW_AVAILABLE = True
    except ImportError:
        pass

try:
    from cognition.memory.vector_store import VectorStore
    VECTOR_STORE_AVAILABLE = True
except ImportError:
    try:
        # 备选：直接加载模块
        _spec = importlib.util.spec_from_file_location(
            "vector_store", str(MEMORY_DIR / "vector_store.py")
        )
        if _spec and _spec.loader:
            _mod = importlib.util.module_from_spec(_spec)
            _spec.loader.exec_module(_mod)
            VectorStore = _mod.VectorStore
            VECTOR_STORE_AVAILABLE = True
    except Exception:
        pass

try:
    from scripts.collect_learning_materials import LearningCollector as MaterialsCollector
    COLLECT_LEARNING_MATERIALS_AVAILABLE = True
except ImportError:
    try:
        _spec = importlib.util.spec_from_file_location(
            "collect_learning_materials", str(SCRIPTS_DIR / "collect_learning_materials.py")
        )
        if _spec and _spec.loader:
            _mod = importlib.util.module_from_spec(_spec)
            _spec.loader.exec_module(_mod)
            MaterialsCollector = _mod.LearningCollector
            COLLECT_LEARNING_MATERIALS_AVAILABLE = True
    except Exception:
        pass

try:
    from scripts.learning_collector import LearningCollector
    LEARNING_COLLECTOR_AVAILABLE = True
except ImportError:
    try:
        _spec = importlib.util.spec_from_file_location(
            "learning_collector", str(SCRIPTS_DIR / "learning_collector.py")
        )
        if _spec and _spec.loader:
            _mod = importlib.util.module_from_spec(_spec)
            _spec.loader.exec_module(_mod)
            LearningCollector = _mod.LearningCollector
            LEARNING_COLLECTOR_AVAILABLE = True
    except Exception:
        LEARNING_COLLECTOR_AVAILABLE = False


# ---------------------------------------------------------------------------
# AutoEvolution 核心类
# ---------------------------------------------------------------------------

class AutoEvolution:
    """
    Hermes AGI 自动进化系统

    集成工作流协调、向量记忆、学习收集、系统测试等模块，
    提供完整的自动进化循环。
    """

    def __init__(self):
        self.base_dir = BASE_DIR
        self.scripts_dir = SCRIPTS_DIR
        self.cognition_dir = COGNITION_DIR
        self.continuous_learning_dir = CONTINUOUS_LEARNING_DIR
        self.log_file = LOG_FILE
        self.status_file = STATUS_FILE

        # 确保目录存在
        META_DIR.mkdir(parents=True, exist_ok=True)

        # 初始化向量记忆库
        self.vector_store = None
        if VECTOR_STORE_AVAILABLE:
            try:
                self.vector_store = VectorStore(
                    store_path=str(VECTOR_STORE_PATH),
                    auto_save=True
                )
                self.log(f"向量记忆库已初始化: {len(self.vector_store.memories)} 条记忆")
            except Exception as e:
                self.log(f"向量记忆库初始化失败: {e}")

        # 记录组件可用状态
        self._component_status = {
            "workflow_coordinator": WORKFLOW_AVAILABLE,
            "vector_store": VECTOR_STORE_AVAILABLE,
            "collect_learning_materials": COLLECT_LEARNING_MATERIALS_AVAILABLE,
            "learning_collector": LEARNING_COLLECTOR_AVAILABLE,
        }
        self.log(f"组件状态: {json.dumps(self._component_status)}")

    # -----------------------------------------------------------------------
    # 日志系统
    # -----------------------------------------------------------------------

    def log(self, message: str, level: str = "INFO"):
        """记录日志到文件和控制台"""
        timestamp = datetime.datetime.now().isoformat()
        log_entry = f"[{level}] {timestamp}: {message}\n"

        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_entry)
        except Exception:
            pass

        level_tag = f"[{level}]" if level != "INFO" else ""
        print(f"{level_tag} [{timestamp}] {message}")

    def log_error(self, message: str):
        self.log(message, level="ERROR")

    def log_warning(self, message: str):
        self.log(message, level="WARNING")

    # -----------------------------------------------------------------------
    # 任务函数（供 WorkflowCoordinator 使用）
    # -----------------------------------------------------------------------

    def task_learning_collection(self) -> Dict[str, Any]:
        """任务：运行学习收集"""
        self.log("开始学习收集...")
        results = {"status": "unknown", "items_collected": 0}

        try:
            # 运行本地学习收集脚本
            result = subprocess.run(
                ["python3", str(self.scripts_dir / "learning_collector.py")],
                capture_output=True, text=True, cwd=str(self.base_dir),
                timeout=300
            )
            if result.returncode == 0:
                results["status"] = "success"
                self.log(f"学习收集完成")
            else:
                results["status"] = "failed"
                results["error"] = result.stderr[:500]
                self.log_warning(f"学习收集失败: {result.stderr[:200]}")
        except Exception as e:
            results["status"] = "error"
            results["error"] = str(e)
            self.log_error(f"学习收集异常: {e}")

        return results

    def task_collect_learning_materials(self) -> Dict[str, Any]:
        """任务：从互联网收集学习素材"""
        self.log("开始收集互联网学习素材...")
        results = {"status": "unknown", "arxiv_papers": 0, "github_repos": 0}

        if not COLLECT_LEARNING_MATERIALS_AVAILABLE:
            results["status"] = "skipped"
            results["reason"] = "collect_learning_materials 模块不可用"
            self.log_warning("collect_learning_materials 模块不可用，跳过")
            return results

        try:
            collector = MaterialsCollector()
            materials = collector.collect_learning_materials()
            results["status"] = "success"
            results["arxiv_papers"] = materials.get("summary", {}).get("arxiv_searches", 0)
            results["github_repos"] = materials.get("summary", {}).get("github_searches", 0)
            self.log(f"互联网素材收集完成: arXiv={results['arxiv_papers']}, GitHub={results['github_repos']}")

            # 将收集结果存入向量记忆库
            if self.vector_store:
                try:
                    self.vector_store.add_memory(
                        content=f"学习素材收集: arXiv搜索{results['arxiv_papers']}个主题, "
                                f"GitHub搜索{results['github_repos']}个主题",
                        memory_type="learning_collection",
                        tags=["learning", "materials", "collection"],
                        importance=0.6
                    )
                except Exception as e:
                    self.log_warning(f"向量记忆存储失败: {e}")

        except Exception as e:
            results["status"] = "error"
            results["error"] = str(e)
            self.log_error(f"互联网素材收集异常: {e}")

        return results

    def task_memory_maintenance(self) -> Dict[str, Any]:
        """任务：记忆维护"""
        self.log("开始记忆维护...")
        results = {"status": "unknown"}

        try:
            result = subprocess.run(
                ["python3", str(self.scripts_dir / "memory_maintenance.py")],
                capture_output=True, text=True, cwd=str(self.base_dir),
                timeout=300
            )
            if result.returncode == 0:
                results["status"] = "success"
                self.log("记忆维护完成")
            else:
                results["status"] = "failed"
                results["error"] = result.stderr[:500]
                self.log_warning(f"记忆维护失败: {result.stderr[:200]}")
        except Exception as e:
            results["status"] = "error"
            results["error"] = str(e)
            self.log_error(f"记忆维护异常: {e}")

        return results

    def task_vector_memory_update(self) -> Dict[str, Any]:
        """任务：向量记忆库维护与优化"""
        self.log("开始向量记忆库维护...")
        results = {"status": "unknown", "total_memories": 0}

        if not self.vector_store:
            results["status"] = "skipped"
            results["reason"] = "向量记忆库不可用"
            self.log_warning("向量记忆库不可用，跳过")
            return results

        try:
            stats = self.vector_store.get_stats()
            results["total_memories"] = stats["total_memories"]
            results["vocabulary_size"] = stats["vocabulary_size"]
            results["store_size_bytes"] = stats["store_size_bytes"]
            results["memory_types"] = stats["memory_types"]

            # 记录进化进度到向量记忆库
            evolution_count = self._get_evolution_count()
            self.vector_store.add_memory(
                content=f"自动进化循环第{evolution_count + 1}次执行, "
                        f"向量记忆库包含{stats['total_memories']}条记忆, "
                        f"词汇量{stats['vocabulary_size']}",
                memory_type="evolution_progress",
                tags=["evolution", "progress", "auto"],
                importance=0.7
            )

            results["status"] = "success"
            self.log(f"向量记忆库维护完成: {stats['total_memories']}条记忆, "
                     f"词汇量{stats['vocabulary_size']}")

        except Exception as e:
            results["status"] = "error"
            results["error"] = str(e)
            self.log_error(f"向量记忆库维护异常: {e}")

        return results

    def task_system_test(self) -> Dict[str, Any]:
        """任务：运行记忆系统测试"""
        self.log("开始系统测试...")
        results = {"status": "unknown", "tests_passed": 0, "tests_failed": 0}

        try:
            result = subprocess.run(
                ["python3", "-m", "unittest", "test_memory_system", "-v"],
                capture_output=True, text=True, cwd=str(self.scripts_dir),
                timeout=300
            )

            output = result.stdout + result.stderr

            # 解析测试结果
            if "OK" in output:
                results["status"] = "success"
                # 尝试提取测试数量
                import re
                ran_match = re.search(r"Ran (\d+) test", output)
                if ran_match:
                    results["tests_passed"] = int(ran_match.group(1))
                self.log(f"系统测试通过: {results['tests_passed']}个测试")
            elif "FAIL" in output or "ERROR" in output:
                results["status"] = "failed"
                fail_match = re.search(r"FAIL=(\d+)", output)
                err_match = re.search(r"ERROR=(\d+)", output)
                if fail_match:
                    results["tests_failed"] = int(fail_match.group(1))
                if err_match:
                    results["tests_failed"] += int(err_match.group(1))
                self.log_warning(f"系统测试有失败: FAIL={fail_match}, ERROR={err_match}")
            else:
                results["status"] = "completed"
                results["output"] = output[:500]
                self.log(f"系统测试完成（状态未知）")

        except Exception as e:
            results["status"] = "error"
            results["error"] = str(e)
            self.log_error(f"系统测试异常: {e}")

        return results

    def task_continuous_learning(self) -> Dict[str, Any]:
        """任务：持续学习"""
        self.log("开始持续学习...")
        results = {"status": "unknown", "modules_run": 0}

        try:
            integrate_script = self.continuous_learning_dir / "integrate_learning.py"
            if not integrate_script.exists():
                results["status"] = "skipped"
                results["reason"] = "integrate_learning.py 不存在"
                self.log_warning("持续学习脚本不存在，跳过")
                return results

            result = subprocess.run(
                ["python3", str(integrate_script)],
                capture_output=True, text=True,
                cwd=str(self.continuous_learning_dir),
                timeout=300
            )

            if result.returncode == 0:
                results["status"] = "success"
                self.log("持续学习完成")
            else:
                results["status"] = "failed"
                results["error"] = result.stderr[:500]
                self.log_warning(f"持续学习失败: {result.stderr[:200]}")

        except Exception as e:
            results["status"] = "error"
            results["error"] = str(e)
            self.log_error(f"持续学习异常: {e}")

        return results

    def task_knowledge_graph_expansion(self) -> Dict[str, Any]:
        """任务：知识图谱扩展"""
        self.log("开始知识图谱扩展...")
        results = {"status": "unknown"}

        try:
            kg_dir = Path("/root/.hermes/cognition/knowledge_graph")
            auto_expand = kg_dir / "auto_expand.py"

            if not auto_expand.exists():
                results["status"] = "skipped"
                results["reason"] = "auto_expand.py 不存在"
                self.log_warning("知识图谱扩展脚本不存在，跳过")
                return results

            result = subprocess.run(
                ["python3", str(auto_expand)],
                capture_output=True, text=True, cwd=str(kg_dir),
                timeout=300
            )

            if result.returncode == 0:
                output_lines = result.stdout.strip().split('\n')
                summary = [l.strip() for l in output_lines
                           if any(kw in l for kw in ['图谱总览', '概念数', '关系数', '新增'])]
                results["status"] = "success"
                results["summary"] = '; '.join(summary[:4])
                self.log(f"知识图谱扩展完成: {results['summary']}")
            else:
                results["status"] = "failed"
                results["error"] = result.stderr[:500]
                self.log_warning(f"知识图谱扩展失败: {result.stderr[:200]}")

        except Exception as e:
            results["status"] = "error"
            results["error"] = str(e)
            self.log_error(f"知识图谱扩展异常: {e}")

        return results

    def task_self_modification(self) -> Dict[str, Any]:
        """任务：自我修改引擎 - 分析认知组件，执行安全改进"""
        self.log("运行自我修改引擎...")
        results = {"status": "unknown"}

        try:
            # 导入自我修改引擎
            sys.path.insert(0, str(COGNITION_DIR / "evolution"))
            from self_modify import SelfModificationEngine

            engine = SelfModificationEngine()
            state = engine.run_full_cycle()

            results["status"] = "success"
            results["components_analyzed"] = state["components_analyzed"]
            results["plans_generated"] = state["plans_generated"]
            results["modifications_executed"] = state["modifications_executed"]
            results["success_count"] = state["success_count"]
            results["component_maturity"] = state["component_maturity"]

            self._component_status["self_modification"] = {
                "status": "success",
                "analyzed": state["components_analyzed"],
                "modified": state["modifications_executed"]
            }

            self.log(f"自我修改完成: 分析{state['components_analyzed']}组件, "
                    f"执行{state['modifications_executed']}修改")

        except Exception as e:
            results["status"] = "error"
            results["error"] = str(e)
            self.log_error(f"自我修改引擎异常: {e}")

        return results

    def task_decision_system(self) -> Dict[str, Any]:
        """任务：决策系统 - 运行决策分析，优化决策能力"""
        self.log("运行决策系统...")
        results = {"status": "unknown"}

        try:
            # 导入决策系统
            sys.path.insert(0, str(COGNITION_DIR / "decision"))
            from decision_system import decision_system, DecisionType

            # 运行决策系统自检和优化
            decision_result = decision_system.make_decision(
                description="决策系统自检：评估当前决策能力并优化",
                decision_type=DecisionType.MULTIPLE_CHOICE,
                options=[
                    {
                        "name": "风险评估优化",
                        "description": "优化风险评估算法和阈值",
                        "pros": ["提高风险识别准确性", "减少误报"],
                        "cons": ["需要更多计算资源", "可能增加复杂度"],
                        "risk_level": 2,
                        "estimated_outcome": 0.8,
                        "confidence": 0.7
                    },
                    {
                        "name": "多目标优化增强",
                        "description": "增强多目标优化算法",
                        "pros": ["处理更复杂决策", "提高决策质量"],
                        "cons": ["算法复杂度增加", "需要更多训练数据"],
                        "risk_level": 3,
                        "estimated_outcome": 0.75,
                        "confidence": 0.65
                    },
                    {
                        "name": "决策树可视化改进",
                        "description": "改进决策树生成和可视化",
                        "pros": ["提高决策透明度", "便于理解和调试"],
                        "cons": ["增加存储开销", "可能影响性能"],
                        "risk_level": 1,
                        "estimated_outcome": 0.85,
                        "confidence": 0.8
                    }
                ],
                constraints=["计算资源有限", "时间限制"],
                objectives=["提升决策准确性", "保持系统稳定性", "优化资源使用"]
            )

            results["status"] = "success"
            results["decision_made"] = True
            results["recommendation"] = decision_result.get("recommendation", {})
            results["risk_assessment"] = decision_result.get("risk_assessment", {})
            results["optimization_result"] = decision_result.get("optimization_result", {})

            self._component_status["decision_system"] = {
                "status": "success",
                "decision_made": True,
                "recommendation": decision_result.get("recommendation", {}).get("primary_recommendation", "")
            }

            self.log(f"决策系统完成: 推荐方案 - {decision_result.get('recommendation', {}).get('primary_recommendation', '无')}")

        except Exception as e:
            results["status"] = "error"
            results["error"] = str(e)
            self.log_error(f"决策系统异常: {e}")

        return results

    def task_emotion_intelligence(self) -> Dict[str, Any]:
        """任务：情感智能 - 运行情感分析和调节，提升情感能力"""
        self.log("运行情感智能系统...")
        results = {"status": "unknown"}

        try:
            # 导入情感智能系统
            sys.path.insert(0, str(COGNITION_DIR / "emotion"))
            from emotional_intelligence import EmotionalIntelligence

            # 初始化情感智能系统
            ei = EmotionalIntelligence()

            # 测试各种情感场景
            test_scenarios = [
                ("太好了！这个功能完成了！", "喜悦场景"),
                ("遇到了一个很难解决的问题", "挑战场景"),
                ("我很好奇这是怎么工作的", "探索场景"),
                ("谢谢你一直帮助我", "信任场景"),
            ]

            emotion_results = []
            for text, scenario in test_scenarios:
                result = ei.generate_response(text, scenario)
                emotion_results.append({
                    "scenario": scenario,
                    "user_emotion": result["analysis"]["user_emotion"],
                    "empathy_need": result["empathy"]["need_level"],
                    "strategy": result["analysis"]["strategy"]["approach"]
                })

            # 获取系统状态
            status = ei.get_status()

            # 保存状态
            ei.save_state()

            results["status"] = "success"
            results["scenarios_tested"] = len(emotion_results)
            results["emotion_results"] = emotion_results
            results["total_memories"] = status["engine"]["total_memories"]
            results["balance_score"] = status["balance"]["overall_balance"]

            self._component_status["emotion_intelligence"] = {
                "status": "success",
                "scenarios_tested": len(emotion_results),
                "total_memories": status["engine"]["total_memories"],
                "balance": status["balance"]["overall_balance"]
            }

            self.log(f"情感智能完成: 测试{len(emotion_results)}个场景, "
                     f"记忆{status['engine']['total_memories']}条, "
                     f"平衡度{status['balance']['overall_balance']:.2f}")

        except Exception as e:
            results["status"] = "error"
            results["error"] = str(e)
            self.log_error(f"情感智能异常: {e}")

        return results

    def task_autonomous_action(self) -> Dict[str, Any]:
        """任务：自主行动 - 执行一个自主行动周期，驱动目标规划和执行"""
        self.log("运行自主行动系统...")
        results = {"status": "unknown"}

        try:
            sys.path.insert(0, str(COGNITION_DIR / "action"))
            from autonomous_action import AutonomousActionSystem

            system = AutonomousActionSystem()
            cycle_result = system.cycle()

            results["status"] = "success"
            results["cycle_id"] = cycle_result.get("cycle_id", 0)
            results["environment_events"] = len(cycle_result.get("environment_events", []))
            results["initiatives"] = len(cycle_result.get("initiatives", []))
            results["tasks_executed"] = len(cycle_result.get("tasks_executed", []))
            results["success_count"] = sum(1 for t in cycle_result.get("tasks_executed", []) if t.get("success"))
            results["reflections"] = cycle_result.get("reflections", [])
            results["system_mode"] = system.get_status().get("system_mode", "unknown")

            # 满足驱动力：每次进化周期都满足成长欲
            system.initiator.satisfy_drive(
                __import__('self_initiator', fromlist=['DriveType']).DriveType.GROWTH, 0.05
            )

            self._component_status["autonomous_action"] = {
                "status": "success",
                "cycle_id": results["cycle_id"],
                "initiatives": results["initiatives"],
                "tasks_executed": results["tasks_executed"],
                "system_mode": results["system_mode"],
            }

            self.log(f"自主行动完成: 周期#{results['cycle_id']}, "
                     f"模式={results['system_mode']}, "
                     f"initiatives={results['initiatives']}, "
                     f"执行={results['tasks_executed']}")

        except Exception as e:
            results["status"] = "error"
            results["error"] = str(e)
            self.log_error(f"自主行动异常: {e}")

        return results

    def task_evolution_summary(self) -> Dict[str, Any]:
        """任务：生成进化摘要并存储到向量记忆库"""
        self.log("生成进化摘要...")
        results = {"status": "unknown"}

        try:
            evolution_count = self._get_evolution_count()
            evolution_count += 1

            summary = {
                "evolution_number": evolution_count,
                "timestamp": datetime.datetime.now().isoformat(),
                "components": self._component_status,
            }

            # 存储到向量记忆库
            if self.vector_store:
                self.vector_store.add_memory(
                    content=f"Hermes AGI 第{evolution_count}次自动进化完成, "
                            f"工作流协调器: {'可用' if WORKFLOW_AVAILABLE else '不可用'}, "
                            f"向量记忆库: {'可用' if VECTOR_STORE_AVAILABLE else '不可用'}, "
                            f"学习素材收集: {'可用' if COLLECT_LEARNING_MATERIALS_AVAILABLE else '不可用'}",
                    memory_type="evolution_record",
                    tags=["evolution", "record", f"evolution_{evolution_count}"],
                    importance=0.9
                )

            results["status"] = "success"
            results["evolution_count"] = evolution_count
            self.log(f"进化摘要生成完成: 第{evolution_count}次进化")

        except Exception as e:
            results["status"] = "error"
            results["error"] = str(e)
            self.log_error(f"进化摘要生成异常: {e}")

        return results

    # -----------------------------------------------------------------------
    # 工作流构建与执行
    # -----------------------------------------------------------------------

    def build_workflow(self) -> Optional[WorkflowCoordinator]:
        """
        构建自动进化工作流 DAG:

            学习收集 ──────────┐
            互联网素材收集 ────┤
            记忆维护 ──────────┤
            向量记忆库维护 ────┼──> 进化摘要
            持续学习 ──────────┤
            知识图谱扩展 ──────┤
            系统测试 ──────────┤
            自我修改引擎 ──────┘
        """
        if not WORKFLOW_AVAILABLE:
            self.log_warning("WorkflowCoordinator 不可用，将使用直接调用模式")
            return None

        coordinator = WorkflowCoordinator(
            workflow_id=f"auto_evolution_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}",
            max_workers=4
        )

        # 独立任务（可并行执行）
        coordinator.add_task(
            task_id="learning_collection",
            func=self.task_learning_collection,
            description="学习收集（本地资料）",
            max_retries=1,
            retry_delay=2.0,
        )

        coordinator.add_task(
            task_id="collect_materials",
            func=self.task_collect_learning_materials,
            description="互联网学习素材收集（arXiv/GitHub）",
            max_retries=1,
            retry_delay=2.0,
        )

        coordinator.add_task(
            task_id="memory_maintenance",
            func=self.task_memory_maintenance,
            description="记忆维护",
            max_retries=1,
            retry_delay=2.0,
        )

        coordinator.add_task(
            task_id="vector_memory_update",
            func=self.task_vector_memory_update,
            description="向量记忆库维护",
            max_retries=1,
            retry_delay=2.0,
        )

        coordinator.add_task(
            task_id="continuous_learning",
            func=self.task_continuous_learning,
            description="持续学习",
            max_retries=1,
            retry_delay=2.0,
        )

        coordinator.add_task(
            task_id="knowledge_graph",
            func=self.task_knowledge_graph_expansion,
            description="知识图谱扩展",
            max_retries=1,
            retry_delay=2.0,
        )

        # 系统测试（独立运行）
        coordinator.add_task(
            task_id="system_test",
            func=self.task_system_test,
            description="系统测试",
            max_retries=0,
        )

        # 自我修改引擎（分析认知组件，执行安全改进）
        coordinator.add_task(
            task_id="self_modification",
            func=self.task_self_modification,
            description="自我修改引擎（分析+改进）",
            max_retries=0,
        )

        # 决策系统（分析决策能力，优化决策流程）
        coordinator.add_task(
            task_id="decision_system",
            func=self.task_decision_system,
            description="决策系统（分析+优化）",
            max_retries=1,
            retry_delay=2.0,
        )

        # 情感智能（分析情感能力，提升同理心和情感表达）
        coordinator.add_task(
            task_id="emotion_intelligence",
            func=self.task_emotion_intelligence,
            description="情感智能（分析+提升）",
            max_retries=1,
            retry_delay=2.0,
        )

        # 自主行动（目标规划+执行+环境感知+驱动力）
        coordinator.add_task(
            task_id="autonomous_action",
            func=self.task_autonomous_action,
            description="自主行动（目标规划+执行+驱动力）",
            max_retries=1,
            retry_delay=2.0,
        )

        # 进化摘要（依赖所有前置任务完成）
        coordinator.add_task(
            task_id="evolution_summary",
            func=self.task_evolution_summary,
            description="进化摘要生成",
            dependencies={
                "learning_collection",
                "collect_materials",
                "memory_maintenance",
                "vector_memory_update",
                "continuous_learning",
                "knowledge_graph",
                "system_test",
                "self_modification",
                "decision_system",
                "emotion_intelligence",
                "autonomous_action",
            },
        )

        return coordinator

    def run_workflow(self, mode: str = "parallel") -> Dict[str, Any]:
        """使用 WorkflowCoordinator 执行进化工作流"""
        coordinator = self.build_workflow()
        if coordinator is None:
            return self.run_direct()

        # 显示工作流结构
        desc = coordinator.describe()
        self.log(f"工作流结构: {desc['task_count']} 个任务")
        self.log(f"执行顺序: {' -> '.join(desc['execution_order'])}")

        # 执行工作流
        result: WorkflowResult = coordinator.run(mode=mode, save_result=True)

        # 解析结果
        summary = result.summary()
        self.log(f"工作流执行完成: 成功={summary['success']}, "
                 f"耗时={summary['duration']:.2f}s, "
                 f"成功={summary['succeeded']}, 失败={summary['failed']}, "
                 f"跳过={summary['skipped']}")

        # 记录每个任务的结果
        for tid, task_result in summary["tasks"].items():
            status = task_result["status"]
            duration = task_result.get("duration", 0)
            if status == "success":
                self.log(f"  ✓ {tid}: {status} ({duration:.2f}s)")
            elif status == "failed":
                self.log_error(f"  ✗ {tid}: {status} - {task_result.get('error', 'N/A')}")
            elif status == "skipped":
                self.log_warning(f"  ○ {tid}: {status} - {task_result.get('error', 'N/A')}")
            else:
                self.log(f"  - {tid}: {status}")

        return summary

    def run_direct(self) -> Dict[str, Any]:
        """直接执行模式（不使用 WorkflowCoordinator）"""
        self.log("使用直接执行模式（WorkflowCoordinator 不可用）")
        results = {}

        tasks = [
            ("learning_collection", self.task_learning_collection),
            ("collect_materials", self.task_collect_learning_materials),
            ("memory_maintenance", self.task_memory_maintenance),
            ("vector_memory_update", self.task_vector_memory_update),
            ("continuous_learning", self.task_continuous_learning),
            ("knowledge_graph", self.task_knowledge_graph_expansion),
            ("system_test", self.task_system_test),
            ("self_modification", self.task_self_modification),
            ("decision_system", self.task_decision_system),
            ("emotion_intelligence", self.task_emotion_intelligence),
            ("autonomous_action", self.task_autonomous_action),
            ("evolution_summary", self.task_evolution_summary),
        ]

        for task_name, task_func in tasks:
            try:
                self.log(f"--- 执行任务: {task_name} ---")
                result = task_func()
                results[task_name] = result
            except Exception as e:
                results[task_name] = {"status": "error", "error": str(e)}
                self.log_error(f"任务 {task_name} 异常: {e}")

        return results

    # -----------------------------------------------------------------------
    # 进化状态管理
    # -----------------------------------------------------------------------

    def _get_evolution_count(self) -> int:
        """获取当前进化次数"""
        if self.status_file.exists():
            try:
                with open(self.status_file, "r", encoding="utf-8") as f:
                    status = json.load(f)
                return status.get("evolution_count", 0)
            except Exception:
                pass
        return 0

    def update_evolution_status(self, workflow_result: Dict[str, Any]):
        """更新进化状态文件"""
        now = datetime.datetime.now()

        if self.status_file.exists():
            try:
                with open(self.status_file, "r", encoding="utf-8") as f:
                    status = json.load(f)
            except Exception:
                status = {}
        else:
            status = {}

        status["last_evolution"] = now.isoformat()
        status["evolution_count"] = status.get("evolution_count", 0) + 1
        status["next_evolution"] = (now + datetime.timedelta(hours=1)).isoformat()

        # 组件状态
        status["components"] = self._component_status

        # 工作流结果摘要
        if workflow_result:
            status["last_workflow"] = {
                "success": workflow_result.get("success", None),
                "duration": workflow_result.get("duration", None),
                "total_tasks": workflow_result.get("total_tasks", 0),
                "succeeded": workflow_result.get("succeeded", 0),
                "failed": workflow_result.get("failed", 0),
            }

        # 持续学习模块状态
        status["continuous_learning"] = {
            "last_run": now.isoformat(),
            "modules_available": self.check_continuous_learning_modules(),
        }

        # 向量记忆库统计
        if self.vector_store:
            try:
                stats = self.vector_store.get_stats()
                status["vector_store"] = {
                    "total_memories": stats["total_memories"],
                    "vocabulary_size": stats["vocabulary_size"],
                    "memory_types": stats["memory_types"],
                }
            except Exception:
                status["vector_store"] = {"error": "获取统计失败"}

        try:
            with open(self.status_file, "w", encoding="utf-8") as f:
                json.dump(status, f, indent=2, ensure_ascii=False)
            self.log(f"进化状态已更新: 第{status['evolution_count']}次进化")
        except Exception as e:
            self.log_error(f"进化状态更新失败: {e}")

    def check_continuous_learning_modules(self) -> List[str]:
        """检查持续学习模块是否可用"""
        modules = [
            "dialogue_learner.py",
            "error_learner.py",
            "active_explorer.py",
            "knowledge_integrator.py",
            "reflection_optimizer.py",
            "integrate_learning.py",
        ]
        available = []
        for module in modules:
            if (self.continuous_learning_dir / module).exists():
                available.append(module)
        return available

    def get_status(self) -> Dict[str, Any]:
        """获取当前进化状态"""
        status = {
            "components": self._component_status,
            "evolution_count": self._get_evolution_count(),
            "continuous_learning_modules": self.check_continuous_learning_modules(),
        }

        if self.vector_store:
            try:
                status["vector_store_stats"] = self.vector_store.get_stats()
            except Exception:
                status["vector_store_stats"] = {"error": "获取失败"}

        if self.status_file.exists():
            try:
                with open(self.status_file, "r", encoding="utf-8") as f:
                    status["last_status"] = json.load(f)
            except Exception:
                pass

        return status

    # -----------------------------------------------------------------------
    # 主入口
    # -----------------------------------------------------------------------

    def run(self, mode: str = "parallel") -> Dict[str, Any]:
        """
        运行一次完整的自动进化循环

        Args:
            mode: 执行模式 - "serial" 或 "parallel"

        Returns:
            工作流执行结果
        """
        self.log("=" * 60)
        self.log("开始自动进化循环")
        self.log(f"执行模式: {mode}")
        self.log(f"组件状态: 工作流={WORKFLOW_AVAILABLE}, 向量存储={VECTOR_STORE_AVAILABLE}, "
                 f"素材收集={COLLECT_LEARNING_MATERIALS_AVAILABLE}")
        self.log("=" * 60)

        start_time = time.time()

        # 执行工作流
        workflow_result = self.run_workflow(mode=mode)

        # 更新进化状态
        self.update_evolution_status(workflow_result)

        elapsed = time.time() - start_time
        self.log("=" * 60)
        self.log(f"自动进化循环完成，总耗时: {elapsed:.2f}秒")
        self.log("=" * 60)

        return workflow_result

    def run_scheduled(self, interval_seconds: int = 3600, mode: str = "parallel"):
        """
        定时执行自动进化

        Args:
            interval_seconds: 执行间隔（秒）
            mode: 执行模式
        """
        self.log(f"启动定时进化模式，间隔: {interval_seconds}秒")

        # 处理终止信号
        running = True

        def signal_handler(signum, frame):
            nonlocal running
            self.log("收到终止信号，正在停止...")
            running = False

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        cycle = 0
        while running:
            cycle += 1
            self.log(f"\n{'#' * 60}")
            self.log(f"定时进化循环 #{cycle}")
            self.log(f"{'#' * 60}")

            try:
                self.run(mode=mode)
            except Exception as e:
                self.log_error(f"进化循环异常: {e}")
                self.log_error(traceback.format_exc())

            if not running:
                break

            self.log(f"下次执行将在 {interval_seconds} 秒后...")
            # 分段等待以便快速响应终止信号
            for _ in range(interval_seconds):
                if not running:
                    break
                time.sleep(1)

        self.log("定时进化已停止")


# ---------------------------------------------------------------------------
# CLI 入口
# -----------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Hermes AGI 自动进化系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 auto_evolution.py                    # 运行一次完整进化
  python3 auto_evolution.py --mode parallel    # 并行执行（默认）
  python3 auto_evolution.py --mode serial      # 串行执行
  python3 auto_evolution.py --schedule 3600    # 每小时执行一次
  python3 auto_evolution.py --test-only        # 仅运行系统测试
  python3 auto_evolution.py --status           # 显示进化状态
        """
    )

    parser.add_argument(
        "--mode", choices=["serial", "parallel"], default="parallel",
        help="工作流执行模式 (default: parallel)"
    )
    parser.add_argument(
        "--schedule", type=int, metavar="SECONDS",
        help="定时执行间隔（秒），不指定则执行一次后退出"
    )
    parser.add_argument(
        "--test-only", action="store_true",
        help="仅运行系统测试"
    )
    parser.add_argument(
        "--status", action="store_true",
        help="显示当前进化状态"
    )
    parser.add_argument(
        "--describe", action="store_true",
        help="显示工作流结构"
    )

    args = parser.parse_args()

    evolution = AutoEvolution()

    # 显示状态
    if args.status:
        status = evolution.get_status()
        print(json.dumps(status, indent=2, ensure_ascii=False))
        return

    # 仅运行测试
    if args.test_only:
        result = evolution.task_system_test()
        print(f"\n测试结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
        return

    # 显示工作流结构
    if args.describe:
        coordinator = evolution.build_workflow()
        if coordinator:
            desc = coordinator.describe()
            print(json.dumps(desc, indent=2, ensure_ascii=False))
        else:
            print("WorkflowCoordinator 不可用，无法显示工作流结构")
        return

    # 定时执行
    if args.schedule:
        evolution.run_scheduled(interval_seconds=args.schedule, mode=args.mode)
    else:
        # 单次执行
        evolution.run(mode=args.mode)


if __name__ == "__main__":
    main()
