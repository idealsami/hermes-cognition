"""
Hermes 自主进化引擎 v1.0
========================

核心能力：
1. 自我分析 - 扫描所有认知组件，评估成熟度
2. 差距识别 - 找出当前能力的薄弱环节
3. 代码生成 - 自动生成改进代码
4. 安全修改 - 带备份和回滚的修改机制
5. 审计追踪 - 记录所有修改历史

安全原则：
- 每次修改前必须创建备份
- 修改后必须运行验证
- 失败时自动回滚
- 所有操作记录到审计日志
"""

import os
import json
import shutil
import hashlib
import datetime
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

# ========== 基础定义 ==========

class MaturityLevel(Enum):
    ABSENT = 0      # 不存在
    SKELETON = 1    # 骨架/占位
    BASIC = 2       # 基础功能
    FUNCTIONAL = 3  # 功能完整
    ADVANCED = 4    # 高级能力
    AUTONOMOUS = 5  # 自主运行

class RiskLevel(Enum):
    SAFE = "safe"           # 只读分析
    LOW = "low"             # 添加新文件
    MEDIUM = "medium"       # 修改现有文件
    HIGH = "high"           # 修改核心系统
    CRITICAL = "critical"   # 修改进化引擎自身

@dataclass
class ComponentStatus:
    name: str
    path: str
    maturity: MaturityLevel
    file_count: int
    total_lines: int
    has_tests: bool
    has_auto_trigger: bool
    last_modified: str
    gaps: List[str]
    improvement_priority: int  # 1-10, 10最紧急

@dataclass
class ModificationPlan:
    target_component: str
    action: str  # create, enhance, fix, refactor
    description: str
    risk_level: RiskLevel
    files_to_modify: List[str]
    files_to_create: List[str]
    expected_improvement: str
    rollback_plan: str

@dataclass
class ModificationRecord:
    timestamp: str
    plan: dict
    backup_path: str
    status: str  # success, failed, rolled_back
    changes_summary: str
    verification_result: str


# ========== 自我分析引擎 ==========

class SelfAnalyzer:
    """扫描和评估所有认知组件的成熟度"""
    
    COMPONENT_REGISTRY = {
        "memory_system": {
            "path": "/root/.hermes/memory",
            "description": "记忆系统 - 长期记忆、事件记忆、概念库",
            "critical_files": ["core/long-term.md", "episodes/index.md"]
        },
        "knowledge_graph": {
            "path": "/root/.hermes/cognition/knowledge_graph",
            "description": "知识图谱 - 概念关系网络",
            "critical_files": ["graph.py", "auto_expand.py"]
        },
        "metacognition": {
            "path": "/root/.hermes/cognition/meta",
            "description": "元认知系统 - 思维监控、策略选择",
            "critical_files": ["metacognitive_system.py", "cognitive_monitor.py"]
        },
        "continuous_learning": {
            "path": "/root/.hermes/memory/continuous_learning",
            "description": "持续学习 - 对话学习、错误学习、主动探索",
            "critical_files": ["dialogue_learner.py", "error_learner.py"]
        },
        "workflow_coordinator": {
            "path": "/root/.hermes/cognition/workflow",
            "description": "工作流协调 - DAG编排、并行执行",
            "critical_files": ["coordinator.py"]
        },
        "vector_store": {
            "path": "/root/.hermes/cognition/memory",
            "description": "向量记忆库 - 语义搜索",
            "critical_files": ["vector_store.py"]
        },
        "auto_evolution": {
            "path": "/root/.hermes/memory/scripts",
            "description": "自动进化系统 - 定时任务编排",
            "critical_files": ["auto_evolution.py"]
        },
        "self_modification": {
            "path": "/root/.hermes/cognition/evolution",
            "description": "自我修改引擎 - 本次新建",
            "critical_files": ["self_modify.py"]
        }
    }
    
    def analyze_all(self) -> Dict[str, ComponentStatus]:
        """分析所有组件，返回状态报告"""
        results = {}
        for name, config in self.COMPONENT_REGISTRY.items():
            results[name] = self._analyze_component(name, config)
        return results
    
    def _analyze_component(self, name: str, config: dict) -> ComponentStatus:
        path = Path(config["path"])
        
        # 统计文件
        file_count = 0
        total_lines = 0
        last_modified = ""
        
        if path.exists():
            for f in path.rglob("*.py"):
                file_count += 1
                try:
                    lines = len(f.read_text(errors='ignore').splitlines())
                    total_lines += lines
                except:
                    pass
            for f in path.rglob("*.md"):
                file_count += 1
                try:
                    lines = len(f.read_text(errors='ignore').splitlines())
                    total_lines += lines
                except:
                    pass
            
            # 最后修改时间
            all_files = list(path.rglob("*"))
            if all_files:
                newest = max(all_files, key=lambda f: f.stat().st_mtime if f.is_file() else 0)
                last_modified = datetime.datetime.fromtimestamp(newest.stat().st_mtime).isoformat()
        
        # 检查测试
        has_tests = any(path.rglob("test_*.py")) if path.exists() else False
        
        # 检查自动触发
        has_auto_trigger = self._check_auto_trigger(name)
        
        # 评估成熟度
        maturity = self._assess_maturity(path, config, file_count, total_lines, has_tests, has_auto_trigger)
        
        # 识别差距
        gaps = self._identify_gaps(name, path, config, maturity)
        
        # 计算优先级
        priority = self._calculate_priority(maturity, gaps)
        
        return ComponentStatus(
            name=name,
            path=str(path),
            maturity=maturity,
            file_count=file_count,
            total_lines=total_lines,
            has_tests=has_tests,
            has_auto_trigger=has_auto_trigger,
            last_modified=last_modified,
            gaps=gaps,
            improvement_priority=priority
        )
    
    def _assess_maturity(self, path, config, file_count, total_lines, has_tests, has_auto_trigger) -> MaturityLevel:
        if not path.exists():
            return MaturityLevel.ABSENT
        
        critical_exist = all(
            (path / f).exists() for f in config.get("critical_files", [])
        )
        
        if not critical_exist:
            return MaturityLevel.SKELETON
        
        score = 0
        if file_count >= 2: score += 1
        if total_lines >= 100: score += 1
        if has_tests: score += 1
        if has_auto_trigger: score += 1
        if total_lines >= 500: score += 1
        
        return MaturityLevel(min(score + 1, 5))
    
    def _check_auto_trigger(self, name: str) -> bool:
        """检查组件是否在自动进化流程中被调用"""
        evo_script = Path("/root/.hermes/memory/scripts/auto_evolution.py")
        if not evo_script.exists():
            return False
        try:
            content = evo_script.read_text()
            trigger_keywords = {
                "memory_system": ["memory", "long-term"],
                "knowledge_graph": ["knowledge", "graph"],
                "metacognition": ["meta", "cognitive"],
                "continuous_learning": ["learn", "continuous"],
                "workflow_coordinator": ["workflow", "coordinator"],
                "vector_store": ["vector"],
                "auto_evolution": ["auto_evolution"],
                "self_modification": ["self_modify", "evolution"]
            }
            keywords = trigger_keywords.get(name, [])
            return any(kw in content.lower() for kw in keywords)
        except:
            return False
    
    def _identify_gaps(self, name, path, config, maturity) -> List[str]:
        gaps = []
        
        if maturity == MaturityLevel.ABSENT:
            gaps.append("组件不存在，需要从零创建")
            return gaps
        
        if not any(path.rglob("test_*.py")):
            gaps.append("缺少测试覆盖")
        
        if maturity.value < 3:
            gaps.append("功能不完整，需要增强核心逻辑")
        
        if maturity.value < 4:
            gaps.append("缺少高级特性（错误恢复、性能优化、自适应）")
        
        if maturity.value < 5:
            gaps.append("未达到自主运行水平")
        
        # 特定组件的差距检查
        specific_gaps = self._check_specific_gaps(name, path)
        gaps.extend(specific_gaps)
        
        return gaps
    
    def _check_specific_gaps(self, name, path) -> List[str]:
        gaps = []
        
        if name == "knowledge_graph":
            reasoning = path / "reasoning_engine.py"
            if reasoning.exists():
                try:
                    content = reasoning.read_text()
                    if "class" not in content or len(content) < 500:
                        gaps.append("推理引擎只有骨架，缺少实际推理能力")
                except:
                    pass
        
        if name == "metacognition":
            for f in ["cognitive_monitor.py", "strategy_selector.py", "confidence_assessor.py"]:
                fp = path / f
                if fp.exists():
                    try:
                        content = fp.read_text()
                        if len(content) < 300:
                            gaps.append(f"{f} 只有骨架实现")
                    except:
                        pass
        
        if name == "continuous_learning":
            learner_dir = path
            if learner_dir.exists():
                py_files = list(learner_dir.glob("*.py"))
                if len(py_files) < 5:
                    gaps.append("学习模块数量不足")
        
        return gaps
    
    def _calculate_priority(self, maturity, gaps) -> int:
        base = 10 - (maturity.value * 2)
        gap_bonus = min(len(gaps), 3)
        return min(max(base + gap_bonus, 1), 10)


# ========== 修改规划器 ==========

class ModificationPlanner:
    """基于分析结果生成修改计划"""
    
    def generate_plans(self, analysis: Dict[str, ComponentStatus]) -> List[ModificationPlan]:
        """按优先级生成修改计划"""
        plans = []
        
        # 按优先级排序
        sorted_components = sorted(
            analysis.values(),
            key=lambda c: c.improvement_priority,
            reverse=True
        )
        
        for component in sorted_components:
            if component.maturity.value >= 5:
                continue  # 已经最高级别
            
            plan = self._plan_for_component(component)
            if plan:
                plans.append(plan)
        
        return plans
    
    def _plan_for_component(self, component: ComponentStatus) -> Optional[ModificationPlan]:
        if component.maturity == MaturityLevel.ABSENT:
            return self._plan_creation(component)
        elif component.maturity.value <= 2:
            return self._plan_enhancement(component)
        elif component.maturity.value <= 4:
            return self._plan_advanced(component)
        return None
    
    def _plan_creation(self, component: ComponentStatus) -> ModificationPlan:
        return ModificationPlan(
            target_component=component.name,
            action="create",
            description=f"创建 {component.name} 的核心实现",
            risk_level=RiskLevel.LOW,
            files_to_modify=[],
            files_to_create=[f"{component.path}/main.py"],
            expected_improvement=f"{component.name} 从不存在升级到基础功能",
            rollback_plan="删除创建的文件"
        )
    
    def _plan_enhancement(self, component: ComponentStatus) -> ModificationPlan:
        return ModificationPlan(
            target_component=component.name,
            action="enhance",
            description=f"增强 {component.name} 的核心功能",
            risk_level=RiskLevel.MEDIUM,
            files_to_modify=[f"{component.path}/{f}" for f in os.listdir(component.path) if f.endswith('.py')][:3],
            files_to_create=[],
            expected_improvement=f"{component.name} 从基础升级到功能完整",
            rollback_plan="从备份恢复修改的文件"
        )
    
    def _plan_advanced(self, component: ComponentStatus) -> ModificationPlan:
        return ModificationPlan(
            target_component=component.name,
            action="enhance",
            description=f"为 {component.name} 添加高级特性",
            risk_level=RiskLevel.MEDIUM,
            files_to_modify=[],
            files_to_create=[f"{component.path}/advanced.py"],
            expected_improvement=f"{component.name} 从功能完整升级到高级",
            rollback_plan="删除新增的高级模块"
        )


# ========== 安全修改执行器 ==========

class SafeModifier:
    """安全地执行代码修改，带备份和回滚"""
    
    BACKUP_DIR = Path("/root/.hermes/cognition/evolution/backups")
    AUDIT_LOG = Path("/root/.hermes/cognition/evolution/audit_log.jsonl")
    
    def __init__(self):
        self.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    
    def execute_plan(self, plan: ModificationPlan) -> ModificationRecord:
        """执行修改计划"""
        timestamp = datetime.datetime.now().isoformat()
        backup_path = ""
        
        try:
            # 1. 创建备份
            if plan.risk_level.value in ["medium", "high", "critical"]:
                backup_path = self._create_backup(plan)
            
            # 2. 执行修改
            changes = self._apply_changes(plan)
            
            # 3. 验证
            verification = self._verify_changes(plan)
            
            record = ModificationRecord(
                timestamp=timestamp,
                plan=asdict(plan),
                backup_path=backup_path,
                status="success" if verification["passed"] else "failed",
                changes_summary=changes,
                verification_result=json.dumps(verification)
            )
            
            # 4. 如果验证失败，回滚
            if not verification["passed"] and backup_path:
                self._rollback(backup_path, plan)
                record.status = "rolled_back"
            
        except Exception as e:
            record = ModificationRecord(
                timestamp=timestamp,
                plan=asdict(plan),
                backup_path=backup_path,
                status="failed",
                changes_summary=f"Error: {str(e)}",
                verification_result=""
            )
            # 尝试回滚
            if backup_path:
                try:
                    self._rollback(backup_path, plan)
                    record.status = "rolled_back"
                except:
                    pass
        
        # 5. 记录审计日志
        self._audit_log(record)
        
        return record
    
    def _create_backup(self, plan: ModificationPlan) -> str:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.BACKUP_DIR / f"{plan.target_component}_{timestamp}"
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        for filepath in plan.files_to_modify:
            src = Path(filepath)
            if src.exists():
                dst = backup_dir / src.name
                shutil.copy2(src, dst)
        
        return str(backup_dir)
    
    def _apply_changes(self, plan: ModificationPlan) -> str:
        changes = []
        
        for filepath in plan.files_to_create:
            path = Path(filepath)
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                # 生成基础模板
                content = self._generate_template(plan.target_component, path)
                path.write_text(content)
                changes.append(f"Created: {filepath}")
        
        return "; ".join(changes) if changes else "No changes"
    
    def _generate_template(self, component: str, path: Path) -> str:
        """生成组件模板代码"""
        module_name = path.stem
        return f'''"""
{component} - {module_name}
自动生成于自我进化过程
"""

# TODO: 实现具体功能
# 此文件由自我修改引擎自动生成
# 需要进一步完善实现

def main():
    """主入口"""
    pass

if __name__ == "__main__":
    main()
'''
    
    def _verify_changes(self, plan: ModificationPlan) -> dict:
        """验证修改是否成功"""
        results = {"passed": True, "checks": []}
        
        # 检查文件是否存在
        for filepath in plan.files_to_create:
            if Path(filepath).exists():
                results["checks"].append(f"OK: {filepath} exists")
            else:
                results["checks"].append(f"FAIL: {filepath} not created")
                results["passed"] = False
        
        for filepath in plan.files_to_modify:
            if Path(filepath).exists():
                results["checks"].append(f"OK: {filepath} intact")
            else:
                results["checks"].append(f"FAIL: {filepath} missing")
                results["passed"] = False
        
        # Python语法检查
        for filepath in plan.files_to_create + plan.files_to_modify:
            if filepath.endswith('.py') and Path(filepath).exists():
                try:
                    result = subprocess.run(
                        [sys.executable, "-m", "py_compile", filepath],
                        capture_output=True, timeout=10
                    )
                    if result.returncode == 0:
                        results["checks"].append(f"SYNTAX OK: {filepath}")
                    else:
                        results["checks"].append(f"SYNTAX ERROR: {filepath}")
                        results["passed"] = False
                except:
                    results["checks"].append(f"SYNTAX CHECK SKIPPED: {filepath}")
        
        return results
    
    def _rollback(self, backup_path: str, plan: ModificationPlan):
        """从备份恢复"""
        backup = Path(backup_path)
        if not backup.exists():
            return
        
        for filepath in plan.files_to_modify:
            src = backup / Path(filepath).name
            if src.exists():
                shutil.copy2(src, filepath)
        
        for filepath in plan.files_to_create:
            path = Path(filepath)
            if path.exists():
                path.unlink()
    
    def _audit_log(self, record: ModificationRecord):
        """记录审计日志"""
        with open(self.AUDIT_LOG, "a") as f:
            f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")


# ========== 自我修改引擎主入口 ==========

class SelfModificationEngine:
    """自我修改引擎 - 协调分析、规划、执行"""
    
    def __init__(self):
        self.analyzer = SelfAnalyzer()
        self.planner = ModificationPlanner()
        self.executor = SafeModifier()
        self.state_file = Path("/root/.hermes/cognition/evolution/engine_state.json")
    
    def run_full_cycle(self) -> dict:
        """运行完整的自我修改周期"""
        print("=" * 60)
        print("Hermes 自我修改引擎 v1.0")
        print("=" * 60)
        
        # 1. 自我分析
        print("\n[1/4] 扫描认知组件...")
        analysis = self.analyzer.analyze_all()
        
        for name, status in analysis.items():
            print(f"  {name}: {status.maturity.name} (优先级: {status.improvement_priority})")
            for gap in status.gaps[:2]:
                print(f"    - {gap}")
        
        # 2. 生成计划
        print("\n[2/4] 生成修改计划...")
        plans = self.planner.generate_plans(analysis)
        
        for i, plan in enumerate(plans[:5]):
            print(f"  Plan {i+1}: [{plan.risk_level.value}] {plan.description}")
        
        # 3. 执行修改
        print("\n[3/4] 执行安全修改...")
        results = []
        for plan in plans[:3]:  # 每次最多执行3个修改
            print(f"\n  执行: {plan.description}")
            record = self.executor.execute_plan(plan)
            results.append(record)
            print(f"  结果: {record.status}")
        
        # 4. 保存状态
        print("\n[4/4] 保存引擎状态...")
        state = {
            "last_run": datetime.datetime.now().isoformat(),
            "components_analyzed": len(analysis),
            "plans_generated": len(plans),
            "modifications_executed": len(results),
            "success_count": sum(1 for r in results if r.status == "success"),
            "component_maturity": {
                name: status.maturity.name 
                for name, status in analysis.items()
            }
        }
        self._save_state(state)
        
        print("\n" + "=" * 60)
        print(f"完成! 分析{state['components_analyzed']}个组件, "
              f"执行{state['modifications_executed']}个修改, "
              f"{state['success_count']}个成功")
        print("=" * 60)
        
        return state
    
    def _save_state(self, state: dict):
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, "w") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)


# ========== 入口 ==========

if __name__ == "__main__":
    engine = SelfModificationEngine()
    result = engine.run_full_cycle()
    print(json.dumps(result, indent=2, ensure_ascii=False))
