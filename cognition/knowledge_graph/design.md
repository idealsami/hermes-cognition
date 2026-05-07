# 知识图谱系统设计文档

## 设计日期: 2026-05-06

---

## 1. 系统目标

构建一个自进化的知识图谱系统，用于：
- 结构化存储概念和关系
- 自动从对话和学习素材中提取新知识
- 提供推理和联想能力
- 支持多跳推理和知识发现

---

## 2. 数据模型

### 2.1 节点类型 (Concept)

```
概念 (Concept)
├── id: 唯一标识符
├── name: 概念名称
├── type: 概念类型 [person|tool|concept|event|location|skill]
├── description: 描述
├── properties: 自定义属性字典
├── source: 来源 [conversation|learning|reflection|manual]
├── confidence: 置信度 (0-1)
├── access_count: 访问次数
├── created_at: 创建时间
└── updated_at: 更新时间
```

### 2.2 边类型 (Relation)

```
关系 (Relation)
├── id: 唯一标识符
├── source_id: 源节点ID
├── target_id: 目标节点ID
├── type: 关系类型 [is_a|has|uses|part_of|related_to|causes|opposite_of|instance_of|knows|created_by]
├── weight: 权重 (0-1)
├── properties: 自定义属性
├── source: 来源
├── confidence: 置信度
├── evidence: 支撑证据 (引用原文)
├── created_at: 创建时间
└── updated_at: 更新时间
```

### 2.3 关系类型定义

| 关系类型 | 含义 | 示例 |
|---------|------|------|
| is_a | 是一种 | Python is_a ProgrammingLanguage |
| has | 拥有 | 理大 has Hermes |
| uses | 使用 | 理大 uses Telegram |
| part_of | 属于 | 记忆系统 part_of 认知系统 |
| related_to | 相关 | 意识 related_to 感知 |
| causes | 导致 | 学习 causes 进化 |
| opposite_of | 相反 | 自动 opposite_of 手动 |
| instance_of | 实例 | 理大 instance_of 用户 |
| knows | 知道 | Hermes knows Python |
| created_by | 创建 | SOUL.md created_by 理大 |

---

## 3. 存储方案

### 3.1 主存储: SQLite

位置: `/root/.hermes/cognition/knowledge_graph/graph.db`

```sql
-- 概念表
CREATE TABLE concepts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    description TEXT,
    properties TEXT,  -- JSON
    source TEXT,
    confidence REAL DEFAULT 1.0,
    access_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 关系表
CREATE TABLE relations (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    type TEXT NOT NULL,
    weight REAL DEFAULT 1.0,
    properties TEXT,  -- JSON
    source TEXT,
    confidence REAL DEFAULT 1.0,
    evidence TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_id) REFERENCES concepts(id),
    FOREIGN KEY (target_id) REFERENCES concepts(id)
);

-- 索引
CREATE INDEX idx_concepts_name ON concepts(name);
CREATE INDEX idx_concepts_type ON concepts(type);
CREATE INDEX idx_relations_source ON relations(source_id);
CREATE INDEX idx_relations_target ON relations(target_id);
CREATE INDEX idx_relations_type ON relations(type);
```

### 3.2 快照备份

每日自动备份到: `/root/.hermes/memory/backups/knowledge_graph_YYYYMMDD.db`

---

## 4. 核心功能模块

### 4.1 知识管理器 (KnowledgeManager)

功能：
- 添加/删除/更新概念
- 添加/删除/更新关系
- 批量导入
- 导出为JSON/CSV

### 4.2 查询引擎 (QueryEngine)

功能：
- 概念搜索 (模糊匹配)
- 关系查询 (A→? 或 ?→B 或 A→?→B)
- 路径查找 (A到B的最短路径)
- 邻居查询 (N跳内的所有节点)
- 子图提取

### 4.3 推理引擎 (ReasoningEngine)

功能：
- 关系推理 (A is_a B, B is_a C → A is_a C)
- 类比推理 (A:B = C:?)
- 概念聚类
- 矛盾检测

### 4.4 自动学习器 (AutoLearner)

功能：
- 从对话中提取概念和关系
- 从学习素材中提取
- 从事件记录中提取
- 定期整理和合并重复概念

---

## 5. 自动学习流程

### 5.1 对话学习

```
对话内容 → 概念提取 → 关系提取 → 去重/合并 → 写入图谱
```

提取策略：
- 识别实体 (人名、工具名、概念名)
- 识别关系动词 (使用、创建、包含、导致...)
- 置信度评估 (基于上下文强度)

### 5.2 学习素材学习

```
学习素材 → 分段 → 概念/关系提取 → 去重/合并 → 写入图谱
```

### 5.3 反思学习

```
定期反思 → 识别高频概念 → 识别缺失关系 → 推理补全 → 写入图谱
```

---

## 6. 与记忆系统集成

### 6.1 读取集成

在需要知识时：
1. 先查图谱获取相关概念
2. 按需展开关联概念
3. 用于推理和回答

### 6.2 写入集成

在记忆新事件时：
1. 从事件中提取概念
2. 更新图谱
3. 建立与现有概念的关联

---

## 7. 文件结构

```
/root/.hermes/cognition/knowledge_graph/
├── design.md          ← 本设计文档
├── graph.db           ← SQLite数据库
├── knowledge_manager.py  ← 知识管理器
├── query_engine.py    ← 查询引擎
├── reasoning_engine.py ← 推理引擎
├── auto_learner.py    ← 自动学习器
└── main.py            ← 主入口/CLI工具
```

---

## 8. 实施计划

| 阶段 | 内容 | 预计时间 |
|------|------|---------|
| Phase 1 | 数据库 + 知识管理器 | 15分钟 |
| Phase 2 | 查询引擎 | 10分钟 |
| Phase 3 | 推理引擎 | 15分钟 |
| Phase 4 | 自动学习器 | 20分钟 |
| Phase 5 | 集成 + 测试 | 10分钟 |

总计: ~70分钟

---

## 9. 成功标准

- [ ] 能存储和检索概念
- [ ] 能存储和检索关系
- [ ] 能进行路径查找
- [ ] 能从对话中自动提取知识
- [ ] 能与记忆系统协同工作
- [ ] 自动扩展能正常运行

---

**设计完成，准备实施。**
