# 元认知系统 (Metacognitive System)

## 目的
监控和调节Hermes的思维过程，实现认知的自我观察和优化。

## 元认知四大组件

### 1. 元认知知识 (Metacognitive Knowledge)
- [x] 认知任务知识：12种任务类型分类
- [x] 认知策略知识：10种认知策略库
- [x] 自我知识：通过监控积累认知特征

### 2. 元认知体验 (Metacognitive Experience)
- [x] 认知感受记录：通过监控器记录思维步骤
- [x] 困惑检测：低信心识别
- [x] 信心评估：7因素加权评估模型

### 3. 元认知监控 (Metacognitive Monitoring)
- [x] 思维过程跟踪：记录思维的步骤和路径
- [x] 错误检测：通过结果更新识别问题
- [x] 进度监控：会话级别的进度跟踪

### 4. 元认知调节 (Metacognitive Regulation)
- [x] 策略选择：根据任务自动选择认知策略
- [x] 计划制定：预估步骤和执行计划
- [x] 策略调整：根据信心动态调整

## 核心组件

| 组件 | 文件 | 功能 |
|------|------|------|
| 认知监控器 | `cognitive_monitor.py` | 跟踪和记录思维过程 |
| 策略选择器 | `strategy_selector.py` | 自动选择最佳认知策略 |
| 信心评估器 | `confidence_assessor.py` | 评估对回答的信心程度 |
| 元认知系统 | `metacognitive_system.py` | 整合所有组件的主系统 |

## 已实现功能

### 认知监控器
- 10种思维类型（分析、创造、批判等）
- 5级信心程度
- 自动记录会话日志
- 生成认知统计报告

### 策略选择器
- 12种任务类型自动分类
- 10种认知策略库
- 基于权重的策略推荐
- 策略详情和使用指南

### 信心评估器
- 7因素加权评估模型
- 自动生成改进建议
- 信心趋势分析
- 历史记录追踪

## 使用示例

```python
from metacognitive_system import metacognitive_system

# 开始认知任务
result = metacognitive_system.start_cognitive_task("分析代码性能问题")

# 记录思维步骤
metacognitive_system.record_thought(
    thought_type="analysis",
    content="识别性能瓶颈",
    reasoning="需要找到最耗时的部分",
    confidence_level=4
)

# 动态更新信心
metacognitive_system.update_confidence(
    knowledge_level=0.7,
    evidence_quality=0.8
)

# 记录学习经验
metacognitive_system.add_lesson("优化前先做性能分析")

# 结束任务
summary = metacognitive_system.end_cognitive_task("问题已解决")
```

## 文件结构
```
/root/.hermes/cognition/meta/
├── README.md                 ← 本文件
├── cognitive_monitor.py      ← 认知监控器
├── strategy_selector.py      ← 策略选择器
├── confidence_assessor.py    ← 信心评估器
├── metacognitive_system.py   ← 元认知系统主模块
├── system_state.json         ← 系统状态持久化
├── journal/                  ← 认知会话日志
│   └── 2026-05-06/
│       └── session_*.json
└── confidence_logs/          ← 信心评估日志
    └── 2026-05-06/
        └── assessment_*.json
```

## 决策系统集成

元认知系统现已与决策系统深度集成，提供高级决策能力：

### 集成功能
- **决策监控**: 自动记录决策过程到认知监控器
- **策略推荐**: 使用策略选择器推荐决策策略
- **信心评估**: 评估决策信心并提供改进建议
- **经验学习**: 从决策结果中学习经验

### 决策系统组件
- **决策引擎**: 整合元认知系统的完整决策流程
- **风险评估器**: 评估决策风险并提供缓解建议
- **多目标优化器**: 处理多个冲突目标的决策问题
- **决策树生成器**: 可视化决策过程和最优路径

### 使用示例
```python
from decision_system import decision_system, DecisionType

# 执行综合决策
result = decision_system.make_decision(
    description="选择下一个要开发的AI功能模块",
    decision_type=DecisionType.MULTIPLE_CHOICE,
    options=[...],
    objectives=["提升AI能力", "保持稳定性", "控制成本"]
)
```

## 当前状态
- ✅ 构建完成: 2026-05-06
- ✅ 测试通过: 演示运行成功
- ✅ 已记录1次任务，平均信心65.5%
- ✅ 决策系统集成: 2026-05-07
- ✅ 决策系统测试通过: 综合决策演示成功

## 统计
- 代码行数: ~1200行（元认知系统）+ ~2000行（决策系统）
- 测试覆盖: 演示测试
- 任务类型: 12种
- 认知策略: 10种
- 决策类型: 8种
- 风险类别: 8种
- 优化方法: 5种
