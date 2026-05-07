"""
环境感知器 - 监控外部环境变化，为自主行动提供触发信号
"""
import json
import os
import glob
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum

BJT = timezone(timedelta(hours=8))


class SensorType(Enum):
    """传感器类型"""
    FILE_CHANGE = "file_change"        # 文件变化
    TIME_TRIGGER = "time_trigger"      # 定时触发
    THRESHOLD = "threshold"            # 阈值触发
    PATTERN = "pattern"                # 模式匹配
    EXTERNAL_EVENT = "external_event"  # 外部事件
    SYSTEM_STATE = "system_state"      # 系统状态


class EventPriority(Enum):
    """事件优先级"""
    CRITICAL = 5
    HIGH = 4
    MEDIUM = 3
    LOW = 2
    INFO = 1


@dataclass
class EnvironmentEvent:
    """环境事件"""
    event_id: str
    sensor_type: SensorType
    source: str
    message: str
    data: Dict
    priority: EventPriority = EventPriority.MEDIUM
    timestamp: str = ""
    handled: bool = False

    def to_dict(self) -> Dict:
        d = asdict(self)
        d['sensor_type'] = self.sensor_type.value
        d['priority'] = self.priority.value
        return d


class EnvironmentSensor:
    """环境感知器 - 监控外部环境变化"""

    def __init__(self, data_dir: str = "/root/.hermes/cognition/action"):
        self.data_dir = data_dir
        self.events_file = os.path.join(data_dir, "environment_events.jsonl")
        self.state_file = os.path.join(data_dir, "sensor_state.json")
        self.watched_paths: Dict[str, float] = {}  # path -> last_mtime
        self.time_triggers: List[Dict] = []
        self.threshold_monitors: Dict[str, Dict] = {}
        self.state: Dict[str, Any] = self._load_state()
        self._event_counter = 0

    def _load_state(self) -> Dict:
        """加载传感器状态"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {"last_scan": None, "event_count": 0}

    def _save_state(self):
        """保存传感器状态"""
        os.makedirs(self.data_dir, exist_ok=True)
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def _generate_event_id(self) -> str:
        self._event_counter += 1
        ts = int(time.time() * 1000)
        return f"evt_{ts}_{self._event_counter}"

    def _emit_event(self, event: EnvironmentEvent):
        """发出环境事件"""
        os.makedirs(self.data_dir, exist_ok=True)
        with open(self.events_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
        self.state["event_count"] = self.state.get("event_count", 0) + 1

    # ==================== 文件监控 ====================

    def watch_file(self, path: str):
        """添加文件监控"""
        if os.path.exists(path):
            self.watched_paths[path] = os.path.getmtime(path)

    def watch_directory(self, dir_path: str, pattern: str = "*"):
        """监控目录下的文件"""
        for f in glob.glob(os.path.join(dir_path, pattern)):
            if os.path.isfile(f):
                self.watched_paths[f] = os.path.getmtime(f)

    def check_file_changes(self) -> List[EnvironmentEvent]:
        """检查文件变化"""
        events = []
        for path, last_mtime in list(self.watched_paths.items()):
            if not os.path.exists(path):
                event = EnvironmentEvent(
                    event_id=self._generate_event_id(),
                    sensor_type=SensorType.FILE_CHANGE,
                    source=path,
                    message=f"文件被删除: {path}",
                    data={"change_type": "deleted"},
                    priority=EventPriority.HIGH
                )
                events.append(event)
                self._emit_event(event)
                del self.watched_paths[path]
                continue

            current_mtime = os.path.getmtime(path)
            if current_mtime > last_mtime:
                event = EnvironmentEvent(
                    event_id=self._generate_event_id(),
                    sensor_type=SensorType.FILE_CHANGE,
                    source=path,
                    message=f"文件被修改: {path}",
                    data={"change_type": "modified", "old_mtime": last_mtime, "new_mtime": current_mtime},
                    priority=EventPriority.MEDIUM
                )
                events.append(event)
                self._emit_event(event)
                self.watched_paths[path] = current_mtime

        return events

    # ==================== 定时触发 ====================

    def add_time_trigger(self, name: str, interval_seconds: int, data: Optional[Dict] = None):
        """添加定时触发器"""
        self.time_triggers.append({
            "name": name,
            "interval": interval_seconds,
            "data": data or {},
            "last_fired": 0
        })

    def check_time_triggers(self) -> List[EnvironmentEvent]:
        """检查定时触发器"""
        events = []
        now = time.time()

        for trigger in self.time_triggers:
            if now - trigger["last_fired"] >= trigger["interval"]:
                event = EnvironmentEvent(
                    event_id=self._generate_event_id(),
                    sensor_type=SensorType.TIME_TRIGGER,
                    source=f"timer:{trigger['name']}",
                    message=f"定时触发: {trigger['name']}",
                    data=trigger["data"],
                    priority=EventPriority.LOW
                )
                events.append(event)
                self._emit_event(event)
                trigger["last_fired"] = now

        return events

    # ==================== 阈值监控 ====================

    def add_threshold_monitor(self, name: str, getter: callable,
                               min_val: Optional[float] = None,
                               max_val: Optional[float] = None,
                               priority: EventPriority = EventPriority.MEDIUM):
        """添加阈值监控器"""
        self.threshold_monitors[name] = {
            "getter": getter,
            "min": min_val,
            "max": max_val,
            "priority": priority,
            "last_value": None,
            "last_alert": 0
        }

    def check_thresholds(self) -> List[EnvironmentEvent]:
        """检查阈值"""
        events = []
        now = time.time()

        for name, monitor in self.threshold_monitors.items():
            try:
                value = monitor["getter"]()
                triggered = False
                reason = ""

                if monitor["min"] is not None and value < monitor["min"]:
                    triggered = True
                    reason = f"{name}={value} < min({monitor['min']})"
                elif monitor["max"] is not None and value > monitor["max"]:
                    triggered = True
                    reason = f"{name}={value} > max({monitor['max']})"

                if triggered and (now - monitor["last_alert"] > 300):  # 5分钟冷却
                    event = EnvironmentEvent(
                        event_id=self._generate_event_id(),
                        sensor_type=SensorType.THRESHOLD,
                        source=f"threshold:{name}",
                        message=f"阈值触发: {reason}",
                        data={"name": name, "value": value, "min": monitor["min"], "max": monitor["max"]},
                        priority=monitor["priority"]
                    )
                    events.append(event)
                    self._emit_event(event)
                    monitor["last_alert"] = now

                monitor["last_value"] = value

            except Exception:
                pass

        return events

    # ==================== 系统状态 ====================

    def get_system_state(self) -> Dict:
        """获取系统状态"""
        state = {}

        # 磁盘使用
        try:
            stat = os.statvfs('/')
            state["disk_free_gb"] = round(stat.f_bavail * stat.f_frsize / (1024**3), 2)
            state["disk_usage_pct"] = round((1 - stat.f_bavail / stat.f_blocks) * 100, 1)
        except Exception:
            pass

        # 内存使用
        try:
            with open('/proc/meminfo', 'r') as f:
                mem = {}
                for line in f:
                    parts = line.split(':')
                    if len(parts) == 2:
                        key = parts[0].strip()
                        val = parts[1].strip().split()[0]
                        mem[key] = int(val)
                total = mem.get('MemTotal', 1)
                available = mem.get('MemAvailable', 0)
                state["mem_total_mb"] = round(total / 1024)
                state["mem_available_mb"] = round(available / 1024)
                state["mem_usage_pct"] = round((1 - available / total) * 100, 1)
        except Exception:
            pass

        # 关键文件状态
        critical_files = [
            "/root/.hermes/SOUL.md",
            "/root/.hermes/memory/core/long-term.md",
        ]
        state["critical_files_ok"] = all(os.path.exists(f) for f in critical_files)

        return state

    # ==================== 综合扫描 ====================

    def scan(self) -> List[EnvironmentEvent]:
        """执行一次完整环境扫描"""
        events = []
        events.extend(self.check_file_changes())
        events.extend(self.check_time_triggers())
        events.extend(self.check_thresholds())

        self.state["last_scan"] = datetime.now(BJT).isoformat()
        self._save_state()

        return events

    def get_recent_events(self, limit: int = 50) -> List[Dict]:
        """获取最近的环境事件"""
        events = []
        if os.path.exists(self.events_file):
            try:
                with open(self.events_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            events.append(json.loads(line))
            except Exception:
                pass
        return events[-limit:]

    def get_unhandled_events(self) -> List[Dict]:
        """获取未处理的事件"""
        return [e for e in self.get_recent_events(200) if not e.get('handled', False)]
