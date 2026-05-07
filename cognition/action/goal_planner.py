"""
目标规划器 - 将高层目标分解为可执行的任务DAG
"""
import json
import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

BJT = timezone(timedelta(hours=8))


class GoalStatus(Enum):
    """目标状态"""
    PENDING = "pending"           # 待规划
    PLANNED = "planned"           # 已规划
    IN_PROGRESS = "in_progress"   # 执行中
    COMPLETED = "completed"       # 已完成
    FAILED = "failed"             # 失败
    ABANDONED = "abandoned"       # 放弃


class GoalPriority(Enum):
    """目标优先级"""
    CRITICAL = 5    # 关键
    HIGH = 4        # 高
    MEDIUM = 3      # 中
    LOW = 2         # 低
    OPTIONAL = 1    # 可选


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    READY = "ready"           # 依赖已满足，可执行
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class Task:
    """可执行任务"""
    task_id: str
    goal_id: str
    name: str
    description: str
    action_type: str           # terminal, file, web, cognition, delegate
    action_params: Dict        # 动作参数
    dependencies: List[str]    # 依赖的task_id列表
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 3
    max_retries: int = 3
    retry_count: int = 0
    timeout_seconds: int = 300
    result: Optional[Dict] = None
    error: Optional[str] = None
    created_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    emotional_context: Optional[str] = None  # 执行时的情感上下文

    def to_dict(self) -> Dict:
        d = asdict(self)
        d['status'] = self.status.value
        return d

    @classmethod
    def from_dict(cls, data: Dict) -> 'Task':
        data['status'] = TaskStatus(data.get('status', 'pending'))
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Goal:
    """高层目标"""
    goal_id: str
    name: str
    description: str
    priority: GoalPriority = GoalPriority.MEDIUM
    status: GoalStatus = GoalStatus.PENDING
    parent_goal_id: Optional[str] = None
    sub_goals: List[str] = field(default_factory=list)
    tasks: List[str] = field(default_factory=list)  # task_id列表
    success_criteria: str = ""
    progress: float = 0.0  # 0-1
    created_at: str = ""
    deadline: Optional[str] = None
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        d = asdict(self)
        d['priority'] = self.priority.value
        d['status'] = self.status.value
        return d

    @classmethod
    def from_dict(cls, data: Dict) -> 'Goal':
        data['priority'] = GoalPriority(data.get('priority', 3))
        data['status'] = GoalStatus(data.get('status', 'pending'))
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class GoalPlanner:
    """目标规划器 - 分解目标为任务DAG"""

    # 目标分解模板：常见目标类型 -> 任务模板
    DECOMPOSITION_TEMPLATES = {
        "research": [
            {"name": "收集信息", "action_type": "web", "params": {"action": "search"}},
            {"name": "整理分析", "action_type": "cognition", "params": {"action": "analyze"}},
            {"name": "生成报告", "action_type": "file", "params": {"action": "write"}},
        ],
        "build": [
            {"name": "需求分析", "action_type": "cognition", "params": {"action": "analyze"}},
            {"name": "架构设计", "action_type": "cognition", "params": {"action": "design"}},
            {"name": "实现编码", "action_type": "terminal", "params": {"action": "code"}},
            {"name": "测试验证", "action_type": "terminal", "params": {"action": "test"}},
            {"name": "部署上线", "action_type": "terminal", "params": {"action": "deploy"}},
        ],
        "monitor": [
            {"name": "配置监控", "action_type": "terminal", "params": {"action": "configure"}},
            {"name": "数据采集", "action_type": "web", "params": {"action": "fetch"}},
            {"name": "异常检测", "action_type": "cognition", "params": {"action": "detect"}},
            {"name": "告警通知", "action_type": "terminal", "params": {"action": "notify"}},
        ],
        "optimize": [
            {"name": "现状分析", "action_type": "cognition", "params": {"action": "analyze"}},
            {"name": "瓶颈识别", "action_type": "cognition", "params": {"action": "identify"}},
            {"name": "方案设计", "action_type": "cognition", "params": {"action": "design"}},
            {"name": "实施改进", "action_type": "terminal", "params": {"action": "implement"}},
            {"name": "效果评估", "action_type": "cognition", "params": {"action": "evaluate"}},
        ],
        "learn": [
            {"name": "知识获取", "action_type": "web", "params": {"action": "fetch"}},
            {"name": "理解消化", "action_type": "cognition", "params": {"action": "understand"}},
            {"name": "实践验证", "action_type": "terminal", "params": {"action": "practice"}},
            {"name": "知识整合", "action_type": "cognition", "params": {"action": "integrate"}},
        ],
        "evolve": [
            {"name": "自我评估", "action_type": "cognition", "params": {"action": "self_assess"}},
            {"name": "差距分析", "action_type": "cognition", "params": {"action": "gap_analysis"}},
            {"name": "进化设计", "action_type": "cognition", "params": {"action": "design"}},
            {"name": "能力构建", "action_type": "terminal", "params": {"action": "build"}},
            {"name": "集成测试", "action_type": "terminal", "params": {"action": "test"}},
            {"name": "反思总结", "action_type": "cognition", "params": {"action": "reflect"}},
        ],
    }

    def __init__(self, data_dir: str = "/root/.hermes/cognition/action"):
        self.data_dir = data_dir
        self.goals_file = os.path.join(data_dir, "goals.json")
        self.tasks_file = os.path.join(data_dir, "tasks.json")
        self.history_file = os.path.join(data_dir, "plan_history.jsonl")
        self.goals: Dict[str, Goal] = {}
        self.tasks: Dict[str, Task] = {}
        self._load_data()

    def _load_data(self):
        """加载目标和任务数据"""
        if os.path.exists(self.goals_file):
            try:
                with open(self.goals_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.goals = {k: Goal.from_dict(v) for k, v in data.items()}
            except Exception:
                self.goals = {}

        if os.path.exists(self.tasks_file):
            try:
                with open(self.tasks_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.tasks = {k: Task.from_dict(v) for k, v in data.items()}
            except Exception:
                self.tasks = {}

    def _save_data(self):
        """保存目标和任务数据"""
        os.makedirs(self.data_dir, exist_ok=True)
        with open(self.goals_file, 'w', encoding='utf-8') as f:
            json.dump({k: v.to_dict() for k, v in self.goals.items()}, f, ensure_ascii=False, indent=2)
        with open(self.tasks_file, 'w', encoding='utf-8') as f:
            json.dump({k: v.to_dict() for k, v in self.tasks.items()}, f, ensure_ascii=False, indent=2)

    def _log_event(self, event_type: str, data: Dict):
        """记录事件到历史"""
        entry = {
            "timestamp": datetime.now(BJT).isoformat(),
            "event_type": event_type,
            **data
        }
        with open(self.history_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def create_goal(self, name: str, description: str, priority: GoalPriority = GoalPriority.MEDIUM,
                    parent_goal_id: Optional[str] = None, success_criteria: str = "",
                    deadline: Optional[str] = None, metadata: Optional[Dict] = None) -> Goal:
        """创建新目标"""
        goal_id = f"goal_{uuid.uuid4().hex[:12]}"
        now = datetime.now(BJT).isoformat()

        goal = Goal(
            goal_id=goal_id,
            name=name,
            description=description,
            priority=priority,
            status=GoalStatus.PENDING,
            parent_goal_id=parent_goal_id,
            success_criteria=success_criteria,
            created_at=now,
            deadline=deadline,
            metadata=metadata or {}
        )

        # 如果有父目标，添加到父目标的子目标列表
        if parent_goal_id and parent_goal_id in self.goals:
            self.goals[parent_goal_id].sub_goals.append(goal_id)

        self.goals[goal_id] = goal
        self._save_data()
        self._log_event("goal_created", {"goal_id": goal_id, "name": name})

        return goal

    def decompose_goal(self, goal_id: str, template_type: Optional[str] = None,
                       custom_tasks: Optional[List[Dict]] = None) -> List[Task]:
        """将目标分解为任务列表

        Args:
            goal_id: 目标ID
            template_type: 模板类型 (research/build/monitor/optimize/learn/evolve)
            custom_tasks: 自定义任务列表，每项包含 name, action_type, action_params, dependencies
        """
        if goal_id not in self.goals:
            raise ValueError(f"Goal {goal_id} not found")

        goal = self.goals[goal_id]
        now = datetime.now(BJT).isoformat()

        # 确定任务模板
        if custom_tasks:
            task_templates = custom_tasks
        elif template_type and template_type in self.DECOMPOSITION_TEMPLATES:
            task_templates = self.DECOMPOSITION_TEMPLATES[template_type]
        else:
            # 尝试自动推断模板类型
            task_templates = self._infer_template(goal)

        # 创建任务
        created_tasks = []
        task_ids = []

        for i, template in enumerate(task_templates):
            task_id = f"task_{uuid.uuid4().hex[:12]}"
            dependencies = template.get('dependencies', [])
            # 如果没有指定依赖，按顺序依赖前一个任务
            if not dependencies and i > 0 and created_tasks:
                dependencies = [created_tasks[-1].task_id]

            task = Task(
                task_id=task_id,
                goal_id=goal_id,
                name=template.get('name', f"任务{i+1}"),
                description=template.get('description', ''),
                action_type=template.get('action_type', 'cognition'),
                action_params=template.get('params', template.get('action_params', {})),
                dependencies=dependencies,
                priority=template.get('priority', goal.priority.value),
                max_retries=template.get('max_retries', 3),
                timeout_seconds=template.get('timeout_seconds', 300),
                created_at=now
            )

            self.tasks[task_id] = task
            created_tasks.append(task)
            task_ids.append(task_id)

        # 更新目标状态
        goal.tasks = task_ids
        goal.status = GoalStatus.PLANNED
        self._save_data()
        self._log_event("goal_decomposed", {
            "goal_id": goal_id,
            "task_count": len(task_ids),
            "template": template_type or "auto"
        })

        return created_tasks

    def _infer_template(self, goal: Goal) -> List[Dict]:
        """根据目标描述自动推断任务模板"""
        desc_lower = goal.description.lower() + " " + goal.name.lower()

        if any(w in desc_lower for w in ['研究', '分析', '调查', 'research', 'analyze']):
            return self.DECOMPOSITION_TEMPLATES["research"]
        elif any(w in desc_lower for w in ['构建', '开发', '创建', '实现', 'build', 'create', 'implement']):
            return self.DECOMPOSITION_TEMPLATES["build"]
        elif any(w in desc_lower for w in ['监控', '监视', '观察', 'monitor', 'watch']):
            return self.DECOMPOSITION_TEMPLATES["monitor"]
        elif any(w in desc_lower for w in ['优化', '改进', '提升', 'optimize', 'improve']):
            return self.DECOMPOSITION_TEMPLATES["optimize"]
        elif any(w in desc_lower for w in ['学习', '掌握', '了解', 'learn', 'study']):
            return self.DECOMPOSITION_TEMPLATES["learn"]
        elif any(w in desc_lower for w in ['进化', '升级', '突破', 'evolve', 'upgrade']):
            return self.DECOMPOSITION_TEMPLATES["evolve"]
        else:
            # 默认：分析 -> 执行 -> 验证
            return [
                {"name": "分析理解", "action_type": "cognition", "params": {"action": "analyze"}},
                {"name": "执行操作", "action_type": "terminal", "params": {"action": "execute"}},
                {"name": "验证结果", "action_type": "cognition", "params": {"action": "verify"}},
            ]

    def get_ready_tasks(self) -> List[Task]:
        """获取所有依赖已满足、可以执行的任务"""
        ready = []
        for task in self.tasks.values():
            if task.status != TaskStatus.PENDING:
                continue
            # 检查所有依赖是否完成
            deps_met = all(
                self.tasks.get(dep_id) is not None and self.tasks[dep_id].status == TaskStatus.COMPLETED
                for dep_id in task.dependencies
            )
            if deps_met:
                task.status = TaskStatus.READY
                ready.append(task)

        if ready:
            self._save_data()

        return sorted(ready, key=lambda t: -t.priority)

    def mark_task_running(self, task_id: str):
        """标记任务为执行中"""
        if task_id in self.tasks:
            self.tasks[task_id].status = TaskStatus.RUNNING
            self.tasks[task_id].started_at = datetime.now(BJT).isoformat()
            # 更新目标状态
            goal_id = self.tasks[task_id].goal_id
            if goal_id in self.goals:
                self.goals[goal_id].status = GoalStatus.IN_PROGRESS
            self._save_data()

    def mark_task_completed(self, task_id: str, result: Optional[Dict] = None):
        """标记任务完成"""
        if task_id in self.tasks:
            self.tasks[task_id].status = TaskStatus.COMPLETED
            self.tasks[task_id].completed_at = datetime.now(BJT).isoformat()
            self.tasks[task_id].result = result
            self._update_goal_progress(self.tasks[task_id].goal_id)
            self._save_data()
            self._log_event("task_completed", {"task_id": task_id, "result": result})

    def mark_task_failed(self, task_id: str, error: str):
        """标记任务失败"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.retry_count += 1
            task.error = error

            if task.retry_count < task.max_retries:
                # 重试
                task.status = TaskStatus.PENDING
                self._log_event("task_retry", {"task_id": task_id, "retry": task.retry_count})
            else:
                task.status = TaskStatus.FAILED
                task.completed_at = datetime.now(BJT).isoformat()
                self._log_event("task_failed", {"task_id": task_id, "error": error})

            self._save_data()

    def _update_goal_progress(self, goal_id: str):
        """更新目标进度"""
        if goal_id not in self.goals:
            return

        goal = self.goals[goal_id]
        if not goal.tasks:
            return

        completed = sum(1 for tid in goal.tasks
                        if tid in self.tasks and self.tasks[tid].status == TaskStatus.COMPLETED)
        goal.progress = completed / len(goal.tasks)

        if goal.progress >= 1.0:
            goal.status = GoalStatus.COMPLETED
            self._log_event("goal_completed", {"goal_id": goal_id})

    def get_active_goals(self) -> List[Goal]:
        """获取所有活跃目标"""
        return [g for g in self.goals.values()
                if g.status in (GoalStatus.PENDING, GoalStatus.PLANNED, GoalStatus.IN_PROGRESS)]

    def get_goal_tasks(self, goal_id: str) -> List[Task]:
        """获取目标的所有任务"""
        if goal_id not in self.goals:
            return []
        return [self.tasks[tid] for tid in self.goals[goal_id].tasks if tid in self.tasks]

    def get_status_summary(self) -> Dict:
        """获取整体状态摘要"""
        goal_counts = {}
        for g in self.goals.values():
            goal_counts[g.status.value] = goal_counts.get(g.status.value, 0) + 1

        task_counts = {}
        for t in self.tasks.values():
            task_counts[t.status.value] = task_counts.get(t.status.value, 0) + 1

        return {
            "total_goals": len(self.goals),
            "goal_status": goal_counts,
            "total_tasks": len(self.tasks),
            "task_status": task_counts,
            "active_goals": [g.to_dict() for g in self.get_active_goals()],
            "ready_tasks": [t.to_dict() for t in self.get_ready_tasks()],
        }

    def add_task_to_goal(self, goal_id: str, name: str, action_type: str,
                         action_params: Dict, dependencies: Optional[List[str]] = None,
                         description: str = "") -> Task:
        """向目标添加单个任务"""
        if goal_id not in self.goals:
            raise ValueError(f"Goal {goal_id} not found")

        task_id = f"task_{uuid.uuid4().hex[:12]}"
        now = datetime.now(BJT).isoformat()

        task = Task(
            task_id=task_id,
            goal_id=goal_id,
            name=name,
            description=description,
            action_type=action_type,
            action_params=action_params,
            dependencies=dependencies or [],
            priority=self.goals[goal_id].priority.value,
            created_at=now
        )

        self.tasks[task_id] = task
        self.goals[goal_id].tasks.append(task_id)
        self._save_data()

        return task

    def abandon_goal(self, goal_id: str, reason: str = ""):
        """放弃目标"""
        if goal_id in self.goals:
            self.goals[goal_id].status = GoalStatus.ABANDONED
            # 跳过所有未完成的任务
            for tid in self.goals[goal_id].tasks:
                if tid in self.tasks and self.tasks[tid].status in (TaskStatus.PENDING, TaskStatus.READY):
                    self.tasks[tid].status = TaskStatus.SKIPPED
            self._save_data()
            self._log_event("goal_abandoned", {"goal_id": goal_id, "reason": reason})
