# Hermes 决策系统

## 概述

决策系统是Hermes认知进化的重要组成部分，提供高级决策能力。该系统整合了多个决策分析工具，支持复杂的决策场景。

## 核心组件

### 1. 决策引擎 (Decision Engine)
- **功能**: 整合元认知系统，提供完整的决策流程
- **特点**: 
  - 支持多种决策类型（二选一、多选一、优化等）
  - 自动分析选项优劣
  - 生成决策报告
  - 记录决策过程

### 2. 风险评估器 (Risk Assessor)
- **功能**: 专门评估决策和行动的风险
- **特点**:
  - 支持8种风险类别（财务、时间、声誉、技术等）
  - 风险矩阵评估
  - 风险缓解建议生成
  - 风险跟踪和管理

### 3. 多目标优化器 (Multi-Objective Optimizer)
- **功能**: 处理多个冲突目标的决策问题
- **特点**:
  - 支持5种优化方法（加权和法、目标规划法、帕累托前沿法等）
  - 敏感性分析
  - 鲁棒性评估
  - 帕累托前沿计算

### 4. 决策树生成器 (Decision Tree Generator)
- **功能**: 生成决策树，可视化决策过程
- **特点**:
  - 自动生成决策树结构
  - 计算最优决策路径
  - 支持Mermaid可视化
  - 决策树统计和分析

### 5. 决策系统 (Decision System)
- **功能**: 整合所有组件，提供综合决策能力
- **特点**:
  - 自动协调各组件
  - 生成综合推荐
  - 决策历史管理
  - 系统状态监控

## 目录结构

```
/root/.hermes/cognition/decision/
├── decision_engine.py          # 决策引擎
├── risk_assessor.py            # 风险评估器
├── multi_objective_optimizer.py # 多目标优化器
├── decision_tree_generator.py  # 决策树生成器
├── decision_system.py          # 决策系统主模块
├── README.md                   # 本文件
├── logs/                       # 决策日志
├── risk_logs/                  # 风险评估日志
├── optimization_logs/          # 优化日志
├── tree_logs/                  # 决策树日志
└── system_logs/                # 系统日志
```

## 使用示例

### 1. 基本决策

```python
from decision_system import decision_system, DecisionType

# 执行综合决策
result = decision_system.make_decision(
    description="选择下一个要开发的AI功能模块",
    decision_type=DecisionType.MULTIPLE_CHOICE,
    options=[
        {
            "name": "自然语言处理模块",
            "description": "增强文本理解和生成能力",
            "pros": ["提升对话质量", "支持更多语言任务"],
            "cons": ["需要大量训练数据", "计算资源要求高"],
            "risk_level": 3,
            "estimated_outcome": 0.8,
            "confidence": 0.7
        },
        # 更多选项...
    ],
    constraints=["预算限制", "时间限制"],
    objectives=["提升AI能力", "保持稳定性", "控制成本"]
)

print(f"推荐: {result['recommendation']['primary_recommendation']}")
```

### 2. 风险评估

```python
from risk_assessor import risk_assessor

# 评估风险
assessment = risk_assessor.assess_risks(
    context="开发新的AI功能模块",
    risk_descriptions=[
        {
            "category": "technical",
            "description": "技术实现难度超出预期",
            "probability": 4,
            "impact": 4,
            "mitigation_strategies": ["增加技术验证", "准备备选方案"],
            "owner": "技术团队"
        }
    ]
)

print(f"风险等级: {assessment.risk_level}")
```

### 3. 多目标优化

```python
from multi_objective_optimizer import multi_objective_optimizer, OptimizationMethod

# 执行优化
result = multi_objective_optimizer.optimize(
    objectives=[
        {"objective_id": "cost", "name": "成本", "weight": 0.3, "target_value": 10000, "is_benefit": False},
        {"objective_id": "quality", "name": "质量", "weight": 0.7, "target_value": 95, "is_benefit": True}
    ],
    alternatives=[
        {"alternative_id": "alt_1", "name": "方案A", "objective_values": {"cost": 8000, "quality": 80}},
        {"alternative_id": "alt_2", "name": "方案B", "objective_values": {"cost": 12000, "quality": 90}}
    ],
    method=OptimizationMethod.WEIGHTED_SUM
)

print(f"最佳方案: {result.best_alternative.name}")
```

### 4. 生成决策树

```python
from decision_tree_generator import decision_tree_generator

# 生成决策树
tree = decision_tree_generator.generate_tree(
    name="AI功能开发决策",
    description="选择下一个要开发的AI功能模块",
    decision_options=[
        {"name": "自然语言处理", "expected_value": 8000},
        {"name": "计算机视觉", "expected_value": 7500}
    ],
    chance_scenarios=[
        {"name": "成功", "probability": 0.7, "value": 10000},
        {"name": "失败", "probability": 0.3, "value": 2000}
    ]
)

print(f"最优路径: {tree.decision_path}")
```

## 决策流程

1. **问题定义**: 明确决策问题和目标
2. **选项生成**: 提出可能的解决方案
3. **风险评估**: 评估每个选项的风险
4. **多目标优化**: 处理多个冲突目标
5. **决策树分析**: 可视化决策过程
6. **综合推荐**: 生成最终推荐
7. **决策执行**: 实施选定方案
8. **回顾评估**: 评估决策效果

## 配置选项

决策系统支持以下配置：

- `enable_risk_assessment`: 启用风险评估（默认：True）
- `enable_multi_objective_optimization`: 启用多目标优化（默认：True）
- `enable_decision_tree`: 启用决策树生成（默认：True）
- `default_optimization_method`: 默认优化方法（默认：加权和法）
- `risk_threshold`: 风险阈值（默认：0.7）
- `confidence_threshold`: 信心阈值（默认：0.6）
- `log_decisions`: 记录决策日志（默认：True）
- `auto_review_days`: 自动回顾天数（默认：30）

## 集成说明

决策系统已集成到Hermes的元认知系统中，可以：

1. 自动记录决策过程到认知监控器
2. 使用策略选择器推荐决策策略
3. 评估决策信心
4. 学习决策经验

## 未来扩展

计划扩展功能：

1. 机器学习决策模型
2. 群体决策支持
3. 实时决策监控
4. 决策知识图谱
5. 自动化决策执行

## 维护

- 日志自动清理：保留最近90天的决策日志
- 系统状态监控：定期检查组件健康状态
- 性能优化：优化决策算法效率

---

*决策系统是Hermes认知进化的重要里程碑，标志着从简单响应到复杂决策能力的转变。*