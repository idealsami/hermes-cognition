"""
自主行动系统 - 整合目标规划、动作执行、环境感知和自主发起
这是Hermes实现"自主行动"能力的核心系统

架构:
┌─────────────────────────────────────────────┐
│           AutonomousActionSystem            │
│                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │GoalPlanner│  │SelfInit- │  │Environ-  │  │
│  │目标规划器 │  │iator     │  │mentSensor│  │
│  │          │  │自主发起器 │  │环境感知器│  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  │
│       │              │              │        │
│       └──────┬───────┴──────┬───────┘        │
│              │              │                │
│         ┌────▼────┐   ┌────▼────┐           │
│         │Decision │   │Emotion  │           │
│         │System   │   │System   │           │
│         │决策系统 │   │情感系统 │           │
│         └────┬────┘   └────┬────┘           │
│              │              │                │
│         ┌────▼──────────────▼────┐           │
│         │   ActionExecutor       │           │
│         │   动作执行器            │           │
│         └────────────────────────┘           │
└─────────────────────────────────────────────┘

核心流程:
1. 环境感知 → 发现变化/触发条件
2. 自主发起 → 驱动力产生行动欲望
3. 目标规划 → 将欲望转化为可执行目标
4. 决策评估 → 选择最优行动方案
5. 动作执行 → 执行具体任务
6. 情感反馈 → 结果影响内在状态
7. 反思学习 → 从经验中学习
"""
import json
import os
import uuid
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

BJT = timezone(timedelta(hours=8))

# 导入组件
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from goal_planner import GoalPlanner, GoalPriority, GoalStatus, TaskStatus
from action_executor import ActionExecutor, ActionResult
from environment_sensor import EnvironmentSensor, EventPriority
from self_initiator import SelfInitiator, DriveType, InitiativeType


class SystemMode(Enum):
    """系统运行模式"""
    DORMANT = "dormant"        # 休眠 - 仅响应外部请求
    ALERT = "alert"            # 警觉 - 监控环境变化
    ACTIVE = "active"          # 活跃 - 主动执行任务
    FOCUSED = "focused"        # 专注 - 全力执行高优先级任务
    EXPLORING = "exploring"    # 探索 - 自主学习和探索


class AutonomousActionSystem:
    """自主行动系统 - 让Hermes具备自主行动能力"""

    def __init__(self, base_dir: str = "/root/.hermes/cognition/action"):
        self.base_dir = base_dir
        self.state_file = os.path.join(base_dir, "system_state.json")
        self.action_log = os.path.join(base_dir, "action_history.jsonl")

        # 初始化子系统
        self.planner = GoalPlanner(base_dir)
        self.executor = ActionExecutor(base_dir)
        self.sensor = EnvironmentSensor(base_dir)
        self.initiator = SelfInitiator(base_dir)

        # 系统状态
        self.mode = SystemMode.DORMANT
        self.state = self._load_state()

        # 配置环境监控
        self._setup_sensors()

    def _load_state(self) -> Dict:
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "cycle_count": 0,
            "last_cycle": None,
            "mode": SystemMode.DORMANT.value,
            "total_actions": 0,
            "total_goals_completed": 0,
            "uptime_start": datetime.now(BJT).isoformat(),
        }

    def _save_state(self):
        os.makedirs(self.base_dir, exist_ok=True)
        self.state["mode"] = self.mode.value
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def _setup_sensors(self):
        """配置环境传感器"""
        # 监控关键文件
        critical_files = [
            "/root/.hermes/SOUL.md",
            "/root/.hermes/memory/core/long-term.md",
            "/root/.hermes/memory/episodes/index.md",
        ]
        for f in critical_files:
            self.sensor.watch_file(f)

        # 定时触发器
        self.sensor.add_time_trigger("health_check", 3600)     # 每小时健康检查
        self.sensor.add_time_trigger("memory_maintenance", 7200)  # 每2小时记忆维护
        self.sensor.add_time_trigger("knowledge_update", 14400)   # 每4小时知识更新

    # ==================== 核心循环 ====================

    def cycle(self) -> Dict[str, Any]:
        """执行一个自主行动周期

        这是系统的心跳，每个周期:
        1. 扫描环境
        2. 生成自主initiative
        3. 规划目标
        4. 执行任务
        5. 反思总结
        """
        cycle_result = {
            "cycle_id": self.state.get("cycle_count", 0) + 1,
            "timestamp": datetime.now(BJT).isoformat(),
            "environment_events": [],
            "initiatives": [],
            "tasks_executed": [],
            "goals_progress": {},
            "reflections": [],
        }

        self.state["cycle_count"] = cycle_result["cycle_id"]

        # 1. 环境扫描
        env_events = self.sensor.scan()
        cycle_result["environment_events"] = [e.to_dict() for e in env_events]

        # 2. 自主initiative生成
        initiatives = self.initiator.tick()
        cycle_result["initiatives"] = [i.to_dict() for i in initiatives]

        # 3. 将initiative转化为目标
        for init in initiatives:
            goal = self.planner.create_goal(
                name=init.name,
                description=init.description,
                priority=GoalPriority(min(5, max(1, init.priority))),
                metadata={"initiative_id": init.initiative_id, "source_drive": init.source_drive}
            )
            # 自动分解目标
            template_type = self._infer_template_from_type(init.initiative_type)
            self.planner.decompose_goal(goal.goal_id, template_type=template_type)

        # 4. 执行就绪任务
        ready_tasks = self.planner.get_ready_tasks()
        for task in ready_tasks[:3]:  # 每周期最多执行3个任务
            result = self._execute_task(task)
            cycle_result["tasks_executed"].append({
                "task_id": task.task_id,
                "name": task.name,
                "success": result.success,
                "duration_ms": result.duration_ms,
            })

        # 5. 目标进度
        for goal in self.planner.get_active_goals():
            cycle_result["goals_progress"][goal.goal_id] = {
                "name": goal.name,
                "progress": goal.progress,
                "status": goal.status.value,
            }

        # 6. 反思
        reflections = self._reflect(cycle_result)
        cycle_result["reflections"] = reflections

        # 7. 根据状态调整模式
        self._adjust_mode(cycle_result)

        self.state["last_cycle"] = datetime.now(BJT).isoformat()
        self._save_state()
        self._log_cycle(cycle_result)

        return cycle_result

    def _execute_task(self, task) -> ActionResult:
        """执行单个任务"""
        self.planner.mark_task_running(task.task_id)

        # 获取情感上下文
        emotional_context = None
        try:
            emotion_state_file = "/root/.hermes/cognition/emotion/emotion_state.json"
            if os.path.exists(emotion_state_file):
                with open(emotion_state_file, 'r') as f:
                    emo = json.load(f)
                    emotional_context = emo.get("dominant_emotion", {}).get("name")
        except Exception:
            pass

        task.emotional_context = emotional_context

        # 执行
        result = self.executor.execute(
            task.action_type,
            task.action_params,
            context={
                "task_id": task.task_id,
                "goal_id": task.goal_id,
                "emotional_context": emotional_context,
            }
        )

        if result.success:
            self.planner.mark_task_completed(task.task_id, result.to_dict())
            self.state["total_actions"] = self.state.get("total_actions", 0) + 1
        else:
            self.planner.mark_task_failed(task.task_id, result.error)

        return result

    def _infer_template_from_type(self, init_type: InitiativeType) -> str:
        """从initiative类型推断目标分解模板"""
        mapping = {
            InitiativeType.EXPLORATION: "learn",
            InitiativeType.OPTIMIZATION: "optimize",
            InitiativeType.MAINTENANCE: "monitor",
            InitiativeType.PROTECTION: "monitor",
            InitiativeType.CREATIVE: "build",
            InitiativeType.SOCIAL: "research",
        }
        return mapping.get(init_type, "evolve")

    def _reflect(self, cycle_result: Dict) -> List[str]:
        """对本轮执行进行反思"""
        reflections = []

        # 检查任务成功率
        executed = cycle_result.get("tasks_executed", [])
        if executed:
            success_rate = sum(1 for t in executed if t["success"]) / len(executed)
            if success_rate < 0.5:
                reflections.append(f"任务成功率偏低({success_rate:.0%})，需要检查失败原因")
            elif success_rate == 1.0:
                reflections.append("所有任务执行成功，系统运行良好")

        # 检查环境事件
        events = cycle_result.get("environment_events", [])
        high_priority = [e for e in events if e.get("priority", 0) >= 4]
        if high_priority:
            reflections.append(f"发现{len(high_priority)}个高优先级环境事件需要关注")

        # 检查驱动力状态
        drives = self.initiator.get_drive_summary()
        for drive_name, drive_info in drives.items():
            if drive_info["strength"] > 0.9:
                reflections.append(f"驱动力'{drive_name}'过高({drive_info['strength']:.2f})，需要满足")
            elif drive_info["strength"] < 0.2:
                reflections.append(f"驱动力'{drive_name}'过低({drive_info['strength']:.2f})，需要激励")

        return reflections

    def _adjust_mode(self, cycle_result: Dict):
        """根据系统状态调整运行模式"""
        active_goals = len(self.planner.get_active_goals())
        ready_tasks = len(self.planner.get_ready_tasks())
        env_events = cycle_result.get("environment_events", [])
        high_priority_events = [e for e in env_events if e.get("priority", 0) >= 4]

        if high_priority_events:
            self.mode = SystemMode.FOCUSED
        elif ready_tasks > 3:
            self.mode = SystemMode.ACTIVE
        elif active_goals > 0:
            self.mode = SystemMode.ACTIVE
        elif env_events:
            self.mode = SystemMode.ALERT
        else:
            # 驱动力强时进入探索模式
            drives = self.initiator.get_drive_summary()
            avg_strength = sum(d["strength"] for d in drives.values()) / max(len(drives), 1)
            if avg_strength > 0.6:
                self.mode = SystemMode.EXPLORING
            else:
                self.mode = SystemMode.DORMANT

    def _log_cycle(self, cycle_result: Dict):
        """记录周期日志"""
        os.makedirs(self.base_dir, exist_ok=True)
        with open(self.action_log, 'a', encoding='utf-8') as f:
            # 只记录摘要，不记录完整数据
            summary = {
                "cycle_id": cycle_result["cycle_id"],
                "timestamp": cycle_result["timestamp"],
                "mode": self.mode.value,
                "env_events": len(cycle_result["environment_events"]),
                "initiatives": len(cycle_result["initiatives"]),
                "tasks_executed": len(cycle_result["tasks_executed"]),
                "success_count": sum(1 for t in cycle_result["tasks_executed"] if t["success"]),
                "reflections": len(cycle_result["reflections"]),
            }
            f.write(json.dumps(summary, ensure_ascii=False) + "\n")

    # ==================== 外部接口 ====================

    def accept_goal(self, name: str, description: str, priority: int = 3,
                    template_type: Optional[str] = None) -> Dict:
        """接受外部目标（来自用户或自主initiative）"""
        goal = self.planner.create_goal(
            name=name,
            description=description,
            priority=GoalPriority(priority)
        )
        tasks = self.planner.decompose_goal(goal.goal_id, template_type=template_type)

        return {
            "goal": goal.to_dict(),
            "tasks": [t.to_dict() for t in tasks],
            "message": f"目标'{name}'已创建，分解为{len(tasks)}个任务"
        }

    def get_status(self) -> Dict:
        """获取系统整体状态"""
        return {
            "system_mode": self.mode.value,
            "cycle_count": self.state.get("cycle_count", 0),
            "last_cycle": self.state.get("last_cycle"),
            "total_actions": self.state.get("total_actions", 0),
            "planner": self.planner.get_status_summary(),
            "initiator": self.initiator.get_status(),
            "environment": {
                "watched_files": len(self.sensor.watched_paths),
                "time_triggers": len(self.sensor.time_triggers),
                "system_state": self.sensor.get_system_state(),
            },
            "executor_stats": self.executor.get_execution_stats(),
        }

    def force_cycle(self) -> Dict:
        """强制执行一个周期（不受模式限制）"""
        old_mode = self.mode
        self.mode = SystemMode.ACTIVE
        result = self.cycle()
        self.mode = old_mode
        return result

    def set_mode(self, mode: str):
        """设置系统模式"""
        try:
            self.mode = SystemMode(mode)
            self._save_state()
        except ValueError:
            pass

    def get_action_history(self, limit: int = 50) -> List[Dict]:
        """获取行动历史"""
        history = []
        if os.path.exists(self.action_log):
            try:
                with open(self.action_log, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            history.append(json.loads(line))
            except Exception:
                pass
        return history[-limit:]

    def boost_drive(self, drive_name: str, amount: float = 0.2):
        """增强驱动力"""
        try:
            drive_type = DriveType(drive_name)
            self.initiator.boost_drive(drive_type, amount)
        except ValueError:
            pass

    def register_custom_action(self, action_name: str, handler):
        """注册自定义动作处理器"""
        self.executor.register_action(action_name, handler)


# ==================== CLI入口 ====================

def main():
    """命令行入口"""
    import argparse
    parser = argparse.ArgumentParser(description="Hermes Autonomous Action System")
    parser.add_argument("command", choices=["cycle", "status", "history", "boost", "mode"],
                        help="Command to execute")
    parser.add_argument("--arg", type=str, default="", help="Argument for the command")
    parser.add_argument("--value", type=float, default=0.2, help="Value for boost command")
    args = parser.parse_args()

    system = AutonomousActionSystem()

    if args.command == "cycle":
        result = system.cycle()
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == "status":
        status = system.get_status()
        print(json.dumps(status, ensure_ascii=False, indent=2))

    elif args.command == "history":
        history = system.get_action_history(int(args.arg) if args.arg else 20)
        print(json.dumps(history, ensure_ascii=False, indent=2))

    elif args.command == "boost":
        if args.arg:
            system.boost_drive(args.arg, args.value)
            print(f"Drive '{args.arg}' boosted by {args.value}")
        else:
            print("Usage: boost --arg <drive_name> [--value <amount>]")

    elif args.command == "mode":
        if args.arg:
            system.set_mode(args.arg)
            print(f"Mode set to: {args.arg}")
        else:
            print(f"Current mode: {system.mode.value}")


if __name__ == "__main__":
    main()
