# 知识图谱系统 (Knowledge Graph System)

## 概述

Hermes的结构化知识存储系统，用于存储、查询和推理概念与关系。

## 功能

- **知识管理**: 添加/删除/更新概念和关系
- **查询引擎**: 搜索、路径查找、邻居查询
- **推理引擎**: 传递推理、类比推理、建议生成
- **自动学习**: 从对话和素材中自动提取知识

## 使用方法

### Python API

```python
from main import KnowledgeGraphSystem

kgs = KnowledgeGraphSystem()

# 学习
kgs.learn("Hermes是一个AI助手，由理大创建")

# 查询
context = kgs.query("Hermes")

# 搜索
results = kgs.search("AI")

# 路径查找
path = kgs.find_path("理大", "记忆系统")

# 推理
inferred = kgs.infer("Hermes", "has")

# 建议
suggestions = kgs.suggest("Hermes")

# 自动扩展
kgs.auto_expand()
```

### CLI

```bash
cd /root/.hermes/cognition/knowledge_graph

# 系统状态
python3 main.py status

# 学习文本
python3 main.py learn "Hermes是一个AI助手"

# 查询概念
python3 main.py query "Hermes"

# 搜索
python3 main.py search "AI"

# 查找路径
python3 main.py path "理大" "记忆系统"

# 自动扩展
python3 main.py expand
```

## 文件结构

```
/root/.hermes/cognition/knowledge_graph/
├── README.md              ← 本文档
├── design.md              ← 设计文档
├── graph.db               ← SQLite数据库
├── knowledge_manager.py   ← 知识管理器
├── query_engine.py        ← 查询引擎
├── reasoning_engine.py    ← 推理引擎
├── auto_learner.py        ← 自动学习器
└── main.py                ← 主入口
```

## 当前状态

- 概念数量: 358
- 关系数量: 17,902
- 概念类型: ai_agent, component, concept, data, event, person, system, tool
- 关系类型: created_by, has, is_a, knows, part_of, related_to, stores, uses

## 集成

- 已集成到自动进化系统 (每6小时自动扩展)
- 与记忆系统协同工作
- 从对话中自动学习新知识

## 创建日期

2026-05-06
