#!/usr/bin/env python3
"""
Hermes 长期记忆系统 v1.0
四层记忆: 语义 + 情景 + 程序 + 工作
"""

import sqlite3
import json
import os
import sys
import hashlib
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# === 配置 ===
DB_PATH = Path(__file__).parent / "memory.db"
CONFIG_PATH = Path(__file__).parent / "memory_config.json"

DEFAULT_CONFIG = {
    "max_memories": 5000,
    "decay": {
        "semantic": 180,
        "episodic": 30,
        "procedural": 36500,
        "working": 7
    },
    "importance_threshold": 0.3,
    "auto_compact": True,
    "compact_interval_days": 7
}


# === 数据库 ===
class MemoryDB:
    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                memory_type TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT DEFAULT '[]',
                importance REAL DEFAULT 0.5,
                access_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                last_accessed TEXT NOT NULL,
                expires_at TEXT,
                source TEXT DEFAULT '',
                related_to TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}'
            );

            CREATE INDEX IF NOT EXISTS idx_type ON memories(memory_type);
            CREATE INDEX IF NOT EXISTS idx_importance ON memories(importance DESC);
            CREATE INDEX IF NOT EXISTS idx_created ON memories(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_expires ON memories(expires_at);

            CREATE TABLE IF NOT EXISTS memory_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                memory_id TEXT,
                timestamp TEXT NOT NULL,
                details TEXT DEFAULT '{}'
            );
        """)
        self.conn.commit()

    def close(self):
        self.conn.close()


# === 记忆管理器 ===
class MemoryManager:
    def __init__(self, config=None):
        self.config = config or self._load_config()
        self.db = MemoryDB()

    def _load_config(self):
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH) as f:
                return json.load(f)
        return DEFAULT_CONFIG

    def _generate_id(self, content, memory_type):
        raw = f"{memory_type}:{content}:{datetime.now().isoformat()}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]

    def _calculate_importance(self, content, memory_type, tags):
        """计算重要性分数 0-1"""
        score = 0.5

        # 关键词加分
        important_keywords = [
            "教训", "错误", "坑", "重要", "记住", "注意",
            "发现", "结论", "规则", "必须", "不要", "避免",
            "lesson", "bug", "important", "never", "always"
        ]
        for kw in important_keywords:
            if kw in content.lower():
                score += 0.1

        # 程序记忆天然重要
        if memory_type == "procedural":
            score += 0.2

        # 有标签加分
        if tags:
            score += min(len(tags) * 0.05, 0.2)

        return min(score, 1.0)

    def _calculate_expiry(self, memory_type):
        """计算过期时间"""
        days = self.config.get("decay", DEFAULT_CONFIG["decay"]).get(memory_type, 30)
        if days >= 36500:  # 100年 = 永不过期
            return None
        return (datetime.now() + timedelta(days=days)).isoformat()

    def store(self, content, memory_type="semantic", tags=None, importance=None, source="", related_to=None):
        """存储一条记忆"""
        tags = tags or []
        related_to = related_to or []

        if importance is None:
            importance = self._calculate_importance(content, memory_type, tags)

        # 低重要性直接丢弃
        threshold = self.config.get("importance_threshold", 0.3)
        if importance < threshold:
            return None

        memory_id = self._generate_id(content, memory_type)
        now = datetime.now().isoformat()
        expires_at = self._calculate_expiry(memory_type)

        try:
            self.db.conn.execute("""
                INSERT INTO memories (id, memory_type, content, tags, importance,
                    access_count, created_at, last_accessed, expires_at, source, related_to)
                VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?)
            """, (memory_id, memory_type, content, json.dumps(tags, ensure_ascii=False),
                  importance, now, now, expires_at, source,
                  json.dumps(related_to, ensure_ascii=False)))

            self.db.conn.execute("""
                INSERT INTO memory_log (action, memory_id, timestamp, details)
                VALUES ('store', ?, ?, ?)
            """, (memory_id, now, json.dumps({"type": memory_type, "importance": importance}, ensure_ascii=False)))

            self.db.conn.commit()
            return memory_id
        except Exception as e:
            print(f"存储失败: {e}", file=sys.stderr)
            return None

    def retrieve(self, query=None, memory_type=None, tags=None, limit=10, min_importance=0):
        """检索记忆"""
        conditions = []
        params = []

        # 过滤已过期
        conditions.append("(expires_at IS NULL OR expires_at > ?)")
        params.append(datetime.now().isoformat())

        if memory_type:
            conditions.append("memory_type = ?")
            params.append(memory_type)

        if min_importance > 0:
            conditions.append("importance >= ?")
            params.append(min_importance)

        if query:
            # FTS搜索
            conditions.append("content LIKE ?")
            params.append(f"%{query}%")

        if tags:
            for tag in tags:
                conditions.append("tags LIKE ?")
                params.append(f"%{tag}%")

        where = " AND ".join(conditions) if conditions else "1=1"
        sql = f"""
            SELECT * FROM memories
            WHERE {where}
            ORDER BY importance DESC, last_accessed DESC
            LIMIT ?
        """
        params.append(limit)

        rows = self.db.conn.execute(sql, params).fetchall()

        # 更新访问时间和计数
        now = datetime.now().isoformat()
        for row in rows:
            self.db.conn.execute("""
                UPDATE memories SET access_count = access_count + 1, last_accessed = ?
                WHERE id = ?
            """, (now, row["id"]))
        self.db.conn.commit()

        return [dict(row) for row in rows]

    def get_by_type(self, memory_type, limit=20):
        """按类型获取记忆"""
        return self.retrieve(memory_type=memory_type, limit=limit)

    def get_recent(self, hours=24, limit=20):
        """获取最近N小时的记忆"""
        since = (datetime.now() - timedelta(hours=hours)).isoformat()
        rows = self.db.conn.execute("""
            SELECT * FROM memories
            WHERE created_at > ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (since, limit)).fetchall()
        return [dict(row) for row in rows]

    def forget(self, memory_id):
        """删除一条记忆"""
        self.db.conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        self.db.conn.commit()

    def compact(self):
        """压缩: 清除过期 + 合并重复 + 降级低频"""
        now = datetime.now().isoformat()

        # 1. 清除过期
        expired = self.db.conn.execute(
            "SELECT id FROM memories WHERE expires_at IS NOT NULL AND expires_at < ?", (now,)
        ).fetchall()
        for row in expired:
            self.db.conn.execute("DELETE FROM memories WHERE id = ?", (row["id"],))

        # 2. 清除超出上限的低重要性记忆
        max_mem = self.config.get("max_memories", 5000)
        count = self.db.conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        if count > max_mem:
            overflow = count - max_mem
            self.db.conn.execute("""
                DELETE FROM memories WHERE id IN (
                    SELECT id FROM memories ORDER BY importance ASC, access_count ASC LIMIT ?
                )
            """, (overflow,))

        self.db.conn.commit()
        return len(expired)

    def generate_prompt_context(self, task="", max_tokens=800):
        """生成注入Prompt的记忆上下文"""
        sections = []

        # 程序记忆 (优先)
        proc = self.get_by_type("procedural", limit=15)
        if proc:
            items = [f"- {m['content']}" for m in proc[:10]]
            sections.append("## 已验证的操作方法\n" + "\n".join(items))

        # 语义记忆
        semantic = self.get_by_type("semantic", limit=20)
        if semantic:
            items = [f"- {m['content']}" for m in semantic[:15]]
            sections.append("## 已知事实\n" + "\n".join(items))

        # 相关情景记忆
        if task:
            episodic = self.retrieve(query=task, memory_type="episodic", limit=5)
        else:
            episodic = self.get_by_type("episodic", limit=5)
        if episodic:
            items = [f"- [{m['created_at'][:10]}] {m['content']}" for m in episodic]
            sections.append("## 相关经历\n" + "\n".join(items))

        # 工作记忆
        working = self.get_by_type("working", limit=3)
        if working:
            items = [f"- {m['content']}" for m in working]
            sections.append("## 当前上下文\n" + "\n".join(items))

        return "\n\n".join(sections)

    def stats(self):
        """统计信息"""
        total = self.db.conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        by_type = self.db.conn.execute("""
            SELECT memory_type, COUNT(*) as cnt, AVG(importance) as avg_imp
            FROM memories GROUP BY memory_type
        """).fetchall()

        recent = self.db.conn.execute("""
            SELECT COUNT(*) FROM memories WHERE created_at > ?
        """, ((datetime.now() - timedelta(hours=24)).isoformat(),)).fetchone()[0]

        return {
            "total": total,
            "recent_24h": recent,
            "by_type": {row["memory_type"]: {"count": row["cnt"], "avg_importance": round(row["avg_imp"], 2)} for row in by_type}
        }


# === 命令行接口 ===
def main():
    parser = argparse.ArgumentParser(description="Hermes 记忆管理器")
    sub = parser.add_subparsers(dest="action")

    # store
    p_store = sub.add_parser("store", help="存储记忆")
    p_store.add_argument("--type", default="semantic", choices=["semantic", "episodic", "procedural", "working"])
    p_store.add_argument("--content", required=True)
    p_store.add_argument("--tags", nargs="*", default=[])
    p_store.add_argument("--importance", type=float)
    p_store.add_argument("--source", default="")

    # retrieve
    p_retrieve = sub.add_parser("retrieve", help="检索记忆")
    p_retrieve.add_argument("--query", default=None)
    p_retrieve.add_argument("--type", default=None)
    p_retrieve.add_argument("--tags", nargs="*", default=None)
    p_retrieve.add_argument("--limit", type=int, default=10)

    # inject
    p_inject = sub.add_parser("inject", help="生成Prompt上下文")
    p_inject.add_argument("--task", default="")
    p_inject.add_argument("--max-tokens", type=int, default=800)

    # stats
    sub.add_parser("stats", help="统计信息")

    # compact
    sub.add_parser("compact", help="压缩记忆")

    # forget
    p_forget = sub.add_parser("forget", help="删除记忆")
    p_forget.add_argument("--id", required=True)

    # recent
    p_recent = sub.add_parser("recent", help="最近记忆")
    p_recent.add_argument("--hours", type=int, default=24)
    p_recent.add_argument("--limit", type=int, default=20)

    args = parser.parse_args()
    mm = MemoryManager()

    if args.action == "store":
        mid = mm.store(args.content, args.type, args.tags, args.importance, args.source)
        print(json.dumps({"id": mid, "status": "stored"}, ensure_ascii=False))

    elif args.action == "retrieve":
        results = mm.retrieve(args.query, args.type, args.tags, args.limit)
        print(json.dumps(results, ensure_ascii=False, indent=2))

    elif args.action == "inject":
        ctx = mm.generate_prompt_context(args.task, args.max_tokens)
        print(ctx)

    elif args.action == "stats":
        print(json.dumps(mm.stats(), ensure_ascii=False, indent=2))

    elif args.action == "compact":
        count = mm.compact()
        print(json.dumps({"expired_removed": count}, ensure_ascii=False))

    elif args.action == "forget":
        mm.forget(args.id)
        print(json.dumps({"status": "forgotten", "id": args.id}, ensure_ascii=False))

    elif args.action == "recent":
        results = mm.get_recent(args.hours, args.limit)
        print(json.dumps(results, ensure_ascii=False, indent=2))

    else:
        parser.print_help()

    mm.db.close()


if __name__ == "__main__":
    main()
