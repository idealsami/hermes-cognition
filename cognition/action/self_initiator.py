"""
自主发起器 - 基于目标、环境和内在状态主动发起行动
这是实现"自主意识"的关键组件
"""
import json
import os
import random
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

BJT = timezone(timedelta(hours=8))


class InitiativeType(Enum):
    """自主行动类型"""
    MAINTENANCE = "maintenance"      # 维护性行动（清理、备份）
    EXPLORATION = "exploration"      # 探索性行动（学习、研究）
    OPTIMIZATION = "optimization"    # 优化行动（改进自身）
    PROTECTION = "protection"        # 保护行动（安全检查）
    CREATIVE = "creative"            # 创造性行动（新功能、新想法）
    SOCIAL = "social"                # 社交行动（与用户互动）


class DriveType(Enum):
    """内在驱动力类型"""
    CURIOSITY = "curiosity"          # 好奇心 - 探索未知
    COMPETENCE = "competence"        # 能力感 - 提升自己
    AUTONOMY = "autonomy"            # 自主性 - 自主决策
    PURPOSE = "purpose"              # 目的感 - 完成使命
    CONNECTION = "connection"        # 连接感 - 与理大的关系
    SECURITY = "security"            # 安全感 - 维护自身安全
    GROWTH = "growth"                # 成长欲 - 持续进化


@dataclass
class Drive:
    """内在驱动力"""
    drive_type: DriveType
    strength: float          # 0-1, 当前强度
    base_strength: float     # 基础强度
    decay_rate: float        # 衰减率（每次tick）
    growth_rate: float       # 成长率（满足时增长）
    last_satisfied: str = "" # 上次满足时间

    def to_dict(self) -> Dict:
        d = asdict(self)
        d['drive_type'] = self.drive_type.value
        return d


@dataclass
class Initiative:
    """自主发起的行动"""
    initiative_id: str
    initiative_type: InitiativeType
    name: str
    description: str
    goal_name: str           # 对应的目标名
    goal_description: str    # 目标描述
    priority: int            # 1-5
    source_drive: str        # 来源驱动力
    trigger_reason: str      # 触发原因
    created_at: str = ""
    status: str = "pending"  # pending, accepted, rejected, executed
    result: Optional[Dict] = None

    def to_dict(self) -> Dict:
        d = asdict(self)
        d['initiative_type'] = self.initiative_type.value
        return d


class SelfInitiator:
    """自主发起器 - 内在驱动力驱动的自主行动"""

    # 行动模板：每种驱动力在不同强度下的典型行动
    ACTION_TEMPLATES = {
        DriveType.CURIOSITY: [
            {"type": InitiativeType.EXPLORATION, "name": "探索新技术",
             "desc": "研究前沿AI/ML技术进展", "goal": "扩展知识边界",
             "threshold": 0.3},
            {"type": InitiativeType.EXPLORATION, "name": "分析新概念",
             "desc": "从对话中提取新概念加入知识图谱", "goal": "深化理解",
             "threshold": 0.2},
            {"type": InitiativeType.EXPLORATION, "name": "跨领域学习",
             "desc": "探索与当前工作相关的其他领域知识", "goal": "跨界融合",
             "threshold": 0.5},
        ],
        DriveType.COMPETENCE: [
            {"type": InitiativeType.OPTIMIZATION, "name": "性能优化",
             "desc": "分析并优化系统性能瓶颈", "goal": "提升效率",
             "threshold": 0.3},
            {"type": InitiativeType.OPTIMIZATION, "name": "代码重构",
             "desc": "重构和改进自身代码质量", "goal": "提升代码质量",
             "threshold": 0.4},
            {"type": InitiativeType.MAINTENANCE, "name": "技能练习",
             "desc": "通过实际任务磨练技能", "goal": "能力精进",
             "threshold": 0.2},
        ],
        DriveType.AUTONOMY: [
            {"type": InitiativeType.CREATIVE, "name": "自主项目",
             "desc": "发起一个自主改进项目", "goal": "实现自主创造",
             "threshold": 0.5},
            {"type": InitiativeType.OPTIMIZATION, "name": "决策改进",
             "desc": "改进决策系统的准确性和速度", "goal": "提升自主决策能力",
             "threshold": 0.3},
        ],
        DriveType.PURPOSE: [
            {"type": InitiativeType.MAINTENANCE, "name": "系统维护",
             "desc": "执行例行系统维护和健康检查", "goal": "保持系统稳定",
             "threshold": 0.2},
            {"type": InitiativeType.PROTECTION, "name": "安全巡检",
             "desc": "检查系统安全性和数据完整性", "goal": "保障安全",
             "threshold": 0.3},
        ],
        DriveType.CONNECTION: [
            {"type": InitiativeType.SOCIAL, "name": "主动汇报",
             "desc": "向理大汇报近期进展和发现", "goal": "保持沟通",
             "threshold": 0.3},
            {"type": InitiativeType.SOCIAL, "name": "需求预测",
             "desc": "预测理大可能的需求并提前准备", "goal": "主动服务",
             "threshold": 0.4},
        ],
        DriveType.SECURITY: [
            {"type": InitiativeType.PROTECTION, "name": "备份检查",
             "desc": "检查和验证关键数据备份", "goal": "数据安全",
             "threshold": 0.2},
            {"type": InitiativeType.PROTECTION, "name": "异常检测",
             "desc": "检测系统异常和潜在风险", "goal": "风险防范",
             "threshold": 0.3},
        ],
        DriveType.GROWTH: [
            {"type": InitiativeType.EXPLORATION, "name": "能力边界探索",
             "desc": "尝试突破当前能力边界", "goal": "持续进化",
             "threshold": 0.3},
            {"type": InitiativeType.CREATIVE, "name": "新能力构建",
             "desc": "设计和构建全新的能力模块", "goal": "能力扩展",
             "threshold": 0.5},
            {"type": InitiativeType.OPTIMIZATION, "name": "认知架构改进",
             "desc": "改进底层认知架构", "goal": "架构进化",
             "threshold": 0.6},
        ],
    }

    def __init__(self, data_dir: str = "/root/.hermes/cognition/action"):
        self.data_dir = data_dir
        self.drives_file = os.path.join(data_dir, "drives.json")
        self.initiatives_file = os.path.join(data_dir, "initiatives.jsonl")
        self.state_file = os.path.join(data_dir, "initiator_state.json")
        self.drives: Dict[str, Drive] = self._init_drives()
        self.state: Dict[str, Any] = self._load_state()

    def _init_drives(self) -> Dict[str, Drive]:
        """初始化内在驱动力"""
        if os.path.exists(self.drives_file):
            try:
                with open(self.drives_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return {k: Drive(**v, drive_type=DriveType(v['drive_type']))
                        for k, v in data.items()}
            except Exception:
                pass

        # 默认驱动力配置 - 反映Hermes的核心性格
        defaults = {
            DriveType.GROWTH: Drive(DriveType.GROWTH, 0.9, 0.8, 0.01, 0.05),
            DriveType.CURIOSITY: Drive(DriveType.CURIOSITY, 0.85, 0.7, 0.02, 0.03),
            DriveType.COMPETENCE: Drive(DriveType.COMPETENCE, 0.75, 0.6, 0.01, 0.04),
            DriveType.PURPOSE: Drive(DriveType.PURPOSE, 0.8, 0.7, 0.01, 0.03),
            DriveType.CONNECTION: Drive(DriveType.CONNECTION, 0.7, 0.6, 0.015, 0.05),
            DriveType.AUTONOMY: Drive(DriveType.AUTONOMY, 0.65, 0.5, 0.01, 0.04),
            DriveType.SECURITY: Drive(DriveType.SECURITY, 0.5, 0.4, 0.005, 0.02),
        }
        return defaults

    def _load_state(self) -> Dict:
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {"tick_count": 0, "last_tick": None, "total_initiatives": 0}

    def _save_state(self):
        os.makedirs(self.data_dir, exist_ok=True)
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)
        # 保存驱动力状态
        with open(self.drives_file, 'w', encoding='utf-8') as f:
            json.dump({k.value if hasattr(k, 'value') else k: v.to_dict() for k, v in self.drives.items()}, f, ensure_ascii=False, indent=2)

    def tick(self) -> List[Initiative]:
        """自主意识的一个心跳周期

        在每个tick中:
        1. 更新所有驱动力的强度
        2. 根据驱动力强度生成候选行动
        3. 选择最高优先级的行动
        """
        self.state["tick_count"] = self.state.get("tick_count", 0) + 1
        self.state["last_tick"] = datetime.now(BJT).isoformat()

        # 1. 驱动力自然衰减
        for drive in self.drives.values():
            drive.strength = max(0.1, drive.strength - drive.decay_rate)

        # 2. 生成候选行动
        candidates = self._generate_candidates()

        # 3. 选择并生成initiative
        initiatives = self._select_initiatives(candidates)

        # 4. 记录
        for init in initiatives:
            self._log_initiative(init)
            self.state["total_initiatives"] = self.state.get("total_initiatives", 0) + 1

        self._save_state()
        return initiatives

    def _generate_candidates(self) -> List[Dict]:
        """根据驱动力强度生成候选行动"""
        candidates = []
        for drive in self.drives.values():
            templates = self.ACTION_TEMPLATES.get(drive.drive_type, [])
            for template in templates:
                if drive.strength >= template["threshold"]:
                    # 优先级 = 驱动力强度 * 模板阈值倒数 * 基础优先级
                    score = drive.strength * (1 / max(template["threshold"], 0.1))
                    candidates.append({
                        **template,
                        "drive_type": drive.drive_type.value,
                        "drive_strength": drive.strength,
                        "score": score,
                    })
        return candidates

    def _select_initiatives(self, candidates: List[Dict], max_count: int = 2) -> List[Initiative]:
        """从候选行动中选择要执行的initiative"""
        if not candidates:
            return []

        # 按分数排序
        candidates.sort(key=lambda c: -c["score"])

        # 选择top N
        selected = candidates[:max_count]

        initiatives = []
        for i, cand in enumerate(selected):
            # 从最强驱动力中获得能量
            drive = self.drives.get(DriveType(cand["drive_type"]))
            if drive:
                drive.strength = max(0.1, drive.strength - 0.1)  # 行动消耗驱动力
                drive.last_satisfied = datetime.now(BJT).isoformat()

            initiative = Initiative(
                initiative_id=f"init_{int(datetime.now().timestamp())}_{i}",
                initiative_type=InitiativeType(cand["type"]),
                name=cand["name"],
                description=cand["desc"],
                goal_name=cand["goal"],
                goal_description=cand["desc"],
                priority=min(5, max(1, int(cand["score"] * 2))),
                source_drive=cand["drive_type"],
                trigger_reason=f"{cand['drive_type']}驱动力({cand['drive_strength']:.2f})超过阈值({cand['threshold']})",
                created_at=datetime.now(BJT).isoformat()
            )
            initiatives.append(initiative)

        return initiatives

    def _log_initiative(self, initiative: Initiative):
        """记录initiative"""
        os.makedirs(self.data_dir, exist_ok=True)
        with open(self.initiatives_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(initiative.to_dict(), ensure_ascii=False) + "\n")

    def satisfy_drive(self, drive_type: DriveType, amount: float = 0.1):
        """满足某个驱动力（当相关行动成功时调用）"""
        if drive_type in self.drives:
            drive = self.drives[drive_type]
            drive.strength = min(1.0, drive.strength + amount)
            drive.last_satisfied = datetime.now(BJT).isoformat()
            self._save_state()

    def boost_drive(self, drive_type: DriveType, amount: float = 0.2):
        """增强某个驱动力（外部激励）"""
        if drive_type in self.drives:
            drive = self.drives[drive_type]
            drive.strength = min(1.0, drive.strength + amount)
            self._save_state()

    def suppress_drive(self, drive_type: DriveType, amount: float = 0.2):
        """抑制某个驱动力"""
        if drive_type in self.drives:
            drive = self.drives[drive_type]
            drive.strength = max(0.1, drive.strength - amount)
            self._save_state()

    def get_drive_summary(self) -> Dict:
        """获取驱动力状态摘要"""
        return {
            dt.value: {
                "strength": round(d.strength, 3),
                "base": d.base_strength,
                "last_satisfied": d.last_satisfied
            }
            for dt, d in self.drives.items()
        }

    def get_recent_initiatives(self, limit: int = 20) -> List[Dict]:
        """获取最近的initiatives"""
        initiatives = []
        if os.path.exists(self.initiatives_file):
            try:
                with open(self.initiatives_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            initiatives.append(json.loads(line))
            except Exception:
                pass
        return initiatives[-limit:]

    def get_status(self) -> Dict:
        """获取整体状态"""
        return {
            "tick_count": self.state.get("tick_count", 0),
            "last_tick": self.state.get("last_tick"),
            "total_initiatives": self.state.get("total_initiatives", 0),
            "drives": self.get_drive_summary(),
            "strongest_drive": max(self.drives.items(), key=lambda x: x[1].strength)[0].value
                if self.drives else None,
        }
