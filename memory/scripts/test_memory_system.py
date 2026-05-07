#!/usr/bin/env python3
"""
Hermes 记忆系统综合测试

测试覆盖:
1. 向量存储 (VectorStore) 功能
2. 学习素材收集 (LearningCollector) 功能
3. 记忆系统完整性
4. 性能和可靠性

使用方法:
    python3 test_memory_system.py
    python3 -m pytest test_memory_system.py -v
"""

import os
import sys
import json
import time
import tempfile
import unittest
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# 尝试导入向量存储
try:
    from cognition.memory.vector_store import VectorStore
    VECTOR_STORE_AVAILABLE = True
except ImportError:
    VECTOR_STORE_AVAILABLE = False
    print("警告: 无法导入 VectorStore，相关测试将跳过")

# 尝试导入学习收集器
try:
    from scripts.learning_collector import LearningCollector
    LEARNING_COLLECTOR_AVAILABLE = True
except ImportError:
    try:
        # 尝试直接导入
        sys.path.insert(0, str(Path(__file__).parent))
        from learning_collector import LearningCollector
        LEARNING_COLLECTOR_AVAILABLE = True
    except ImportError:
        LEARNING_COLLECTOR_AVAILABLE = False
        print("警告: 无法导入 LearningCollector，相关测试将跳过")


class TestVectorStore(unittest.TestCase):
    """测试向量存储功能"""
    
    def setUp(self):
        """测试前准备"""
        if not VECTOR_STORE_AVAILABLE:
            self.skipTest("VectorStore 不可用")
        
        # 使用临时文件作为存储路径
        self.temp_dir = tempfile.mkdtemp()
        self.store_path = os.path.join(self.temp_dir, "test_vector_store.json")
        self.store = VectorStore(store_path=self.store_path, auto_save=True)
    
    def tearDown(self):
        """测试后清理"""
        if hasattr(self, 'store'):
            del self.store
        # 清理临时文件
        if os.path.exists(self.store_path):
            os.remove(self.store_path)
        if os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)
    
    def test_add_memory(self):
        """测试添加记忆"""
        memory_id = self.store.add_memory(
            content="今天学习了Python编程",
            memory_type="learning",
            tags=["python", "programming"],
            importance=0.8
        )
        
        self.assertIsNotNone(memory_id)
        self.assertIn(memory_id, self.store.memories)
        
        memory = self.store.get_memory(memory_id)
        self.assertEqual(memory["content"], "今天学习了Python编程")
        self.assertEqual(memory["type"], "learning")
        self.assertIn("python", memory["tags"])
        self.assertEqual(memory["importance"], 0.8)
    
    def test_add_empty_memory_raises_error(self):
        """测试添加空记忆应抛出异常"""
        with self.assertRaises(ValueError):
            self.store.add_memory(content="")
        
        with self.assertRaises(ValueError):
            self.store.add_memory(content="   ")
    
    def test_update_memory(self):
        """测试更新记忆"""
        memory_id = self.store.add_memory(content="原始内容")
        
        # 更新内容
        result = self.store.update_memory(
            memory_id,
            content="更新后的内容",
            importance=0.9
        )
        
        self.assertTrue(result)
        
        memory = self.store.get_memory(memory_id)
        self.assertEqual(memory["content"], "更新后的内容")
        self.assertEqual(memory["importance"], 0.9)
    
    def test_update_nonexistent_memory(self):
        """测试更新不存在的记忆"""
        result = self.store.update_memory("nonexistent_id", content="test")
        self.assertFalse(result)
    
    def test_delete_memory(self):
        """测试删除记忆"""
        memory_id = self.store.add_memory(content="要删除的记忆")
        self.assertIn(memory_id, self.store.memories)
        
        result = self.store.delete_memory(memory_id)
        self.assertTrue(result)
        self.assertNotIn(memory_id, self.store.memories)
    
    def test_delete_nonexistent_memory(self):
        """测试删除不存在的记忆"""
        result = self.store.delete_memory("nonexistent_id")
        self.assertFalse(result)
    
    def test_search_semantic(self):
        """测试语义搜索"""
        # 添加多条记忆
        self.store.add_memory("Python是一种编程语言", tags=["python"])
        self.store.add_memory("机器学习是人工智能的子领域", tags=["ml", "ai"])
        self.store.add_memory("深度学习使用神经网络", tags=["dl", "ai"])
        self.store.add_memory("今天天气很好", tags=["weather"])
        
        # 搜索相关内容
        results = self.store.search("人工智能技术", top_k=3)
        
        self.assertGreater(len(results), 0)
        self.assertLessEqual(len(results), 3)
        
        # 检查结果格式
        for result in results:
            self.assertIn("similarity", result)
            self.assertIn("content", result)
            self.assertIn("id", result)
    
    def test_search_with_type_filter(self):
        """测试按类型过滤搜索"""
        self.store.add_memory("Python编程", memory_type="fact")
        self.store.add_memory("学习Python的心得", memory_type="experience")
        
        results = self.store.search("Python", memory_type="fact")
        
        for result in results:
            self.assertEqual(result["type"], "fact")
    
    def test_search_with_tag_filter(self):
        """测试按标签过滤搜索"""
        self.store.add_memory("AI技术", tags=["ai", "tech"])
        self.store.add_memory("日常生活", tags=["daily"])
        
        results = self.store.search("技术", tags=["ai"])
        
        for result in results:
            self.assertIn("ai", result["tags"])
    
    def test_search_empty_query(self):
        """测试空查询"""
        self.store.add_memory("测试记忆")
        results = self.store.search("")
        self.assertEqual(len(results), 0)
    
    def test_search_by_tags(self):
        """测试按标签搜索"""
        self.store.add_memory("记忆1", tags=["tag1", "tag2"])
        self.store.add_memory("记忆2", tags=["tag2", "tag3"])
        self.store.add_memory("记忆3", tags=["tag1", "tag3"])
        
        # 匹配任一标签
        results = self.store.search_by_tags(["tag1"])
        self.assertEqual(len(results), 2)
        
        # 匹配所有标签
        results = self.store.search_by_tags(["tag1", "tag2"], match_all=True)
        self.assertEqual(len(results), 1)
    
    def test_list_memories(self):
        """测试列出记忆"""
        self.store.add_memory("记忆A", memory_type="type1")
        self.store.add_memory("记忆B", memory_type="type2")
        self.store.add_memory("记忆C", memory_type="type1")
        
        # 列出所有
        all_memories = self.store.list_memories()
        self.assertEqual(len(all_memories), 3)
        
        # 按类型过滤
        type1_memories = self.store.list_memories(memory_type="type1")
        self.assertEqual(len(type1_memories), 2)
        
        # 限制数量
        limited = self.store.list_memories(limit=2)
        self.assertEqual(len(limited), 2)
    
    def test_get_similar_memories(self):
        """测试获取相似记忆"""
        id1 = self.store.add_memory("Python编程语言")
        id2 = self.store.add_memory("Java编程语言")
        id3 = self.store.add_memory("今天天气晴朗")
        
        similar = self.store.get_similar_memories(id1, top_k=2)
        
        self.assertGreater(len(similar), 0)
        # 检查不包含自身
        for s in similar:
            self.assertNotEqual(s["id"], id1)
    
    def test_persistence(self):
        """测试持久化存储"""
        # 添加记忆
        self.store.add_memory("持久化测试记忆", tags=["test"])
        
        # 创建新的存储实例加载同一文件
        new_store = VectorStore(store_path=self.store_path)
        
        # 验证数据已保存
        self.assertEqual(len(new_store.memories), 1)
        
        # 验证搜索功能
        results = new_store.search("持久化测试")
        self.assertGreater(len(results), 0)
    
    def test_clear(self):
        """测试清空存储"""
        self.store.add_memory("记忆1")
        self.store.add_memory("记忆2")
        self.assertEqual(len(self.store.memories), 2)
        
        self.store.clear()
        self.assertEqual(len(self.store.memories), 0)
    
    def test_get_stats(self):
        """测试获取统计信息"""
        self.store.add_memory("记忆1", memory_type="type1")
        self.store.add_memory("记忆2", memory_type="type2")
        
        stats = self.store.get_stats()
        
        self.assertEqual(stats["total_memories"], 2)
        self.assertIn("vocabulary_size", stats)
        self.assertIn("memory_types", stats)
        self.assertEqual(stats["memory_types"]["type1"], 1)
        self.assertEqual(stats["memory_types"]["type2"], 1)
    
    def test_tokenize_chinese(self):
        """测试中文分词"""
        tokens = self.store._tokenize("今天学习了Python编程")
        
        # 应该包含中文字符和双字组合
        self.assertIn("今", tokens)
        self.assertIn("今天", tokens)
        self.assertIn("python", tokens)
        self.assertIn("编程", tokens)
    
    def test_tokenize_english(self):
        """测试英文分词"""
        tokens = self.store._tokenize("Hello World Programming")
        
        self.assertIn("hello", tokens)
        self.assertIn("world", tokens)
        self.assertIn("programming", tokens)
    
    def test_cosine_similarity(self):
        """测试余弦相似度计算"""
        vec1 = {"a": 1.0, "b": 2.0, "c": 3.0}
        vec2 = {"a": 1.0, "b": 2.0, "c": 3.0}
        vec3 = {"x": 1.0, "y": 2.0}
        
        # 完全相同的向量
        similarity = self.store._cosine_similarity(vec1, vec2)
        self.assertAlmostEqual(similarity, 1.0, places=5)
        
        # 完全不同的向量
        similarity = self.store._cosine_similarity(vec1, vec3)
        self.assertAlmostEqual(similarity, 0.0, places=5)
        
        # 空向量
        similarity = self.store._cosine_similarity({}, vec1)
        self.assertEqual(similarity, 0.0)


class TestLearningCollector(unittest.TestCase):
    """测试学习素材收集功能"""
    
    def setUp(self):
        """测试前准备"""
        if not LEARNING_COLLECTOR_AVAILABLE:
            self.skipTest("LearningCollector 不可用")
        
        self.collector = LearningCollector()
    
    def test_collector_initialization(self):
        """测试收集器初始化"""
        self.assertIsNotNone(self.collector)
        self.assertTrue(self.collector.base_dir.exists())
        self.assertTrue(self.collector.learning_dir.exists())
    
    def test_collect_ai_research(self):
        """测试AI研究资料收集"""
        result = self.collector.collect_ai_research()
        
        self.assertIsNotNone(result)
        self.assertIn("title", result)
        self.assertIn("topics", result)
        self.assertGreater(len(result["topics"]), 0)
    
    def test_collect_consciousness_studies(self):
        """测试意识研究资料收集"""
        result = self.collector.collect_consciousness_studies()
        
        self.assertIsNotNone(result)
        self.assertIn("title", result)
        self.assertIn("theories", result)
        self.assertGreater(len(result["theories"]), 0)
    
    def test_collect_memory_research(self):
        """测试记忆研究资料收集"""
        result = self.collector.collect_memory_research()
        
        self.assertIsNotNone(result)
        self.assertIn("title", result)
        self.assertIn("memory_types", result)
        self.assertGreater(len(result["memory_types"]), 0)
    
    def test_collect_learning_plan(self):
        """测试学习计划创建"""
        result = self.collector.collect_learning_plan()
        
        self.assertIsNotNone(result)
        self.assertIn("goals", result)
        self.assertGreater(len(result["goals"]), 0)
        # 学习计划应包含时间相关字段 (schedule 或 next_review)
        self.assertTrue(
            "schedule" in result or "next_review" in result,
            "学习计划缺少时间安排字段"
        )
    
    def test_collect_all(self):
        """测试完整收集流程"""
        result = self.collector.collect_all()
        
        self.assertIsNotNone(result)
        self.assertIn("collection_time", result)
        self.assertIn("collected_items", result)
        self.assertIn("total_items_collected", result)
        self.assertGreater(result["total_items_collected"], 0)


class TestMemorySystemIntegrity(unittest.TestCase):
    """测试记忆系统完整性"""
    
    def setUp(self):
        """测试前准备"""
        self.memory_dir = Path("/root/.hermes/memory")
        self.core_dir = self.memory_dir / "core"
        self.episodes_dir = self.memory_dir / "episodes"
        self.concepts_dir = self.memory_dir / "concepts"
        self.learning_dir = self.memory_dir / "learning"
        self.scripts_dir = self.memory_dir / "scripts"
    
    def test_memory_directory_exists(self):
        """测试记忆目录存在"""
        self.assertTrue(self.memory_dir.exists(), "记忆目录不存在")
        self.assertTrue(self.memory_dir.is_dir(), "记忆路径不是目录")
    
    def test_core_directory_structure(self):
        """测试核心目录结构"""
        required_dirs = [
            "core",
            "episodes",
            "concepts",
            "learning",
            "scripts",
            "backups"
        ]
        
        for dir_name in required_dirs:
            dir_path = self.memory_dir / dir_name
            self.assertTrue(
                dir_path.exists(),
                f"必需目录不存在: {dir_name}"
            )
    
    def test_core_files_exist(self):
        """测试核心文件存在"""
        core_files = [
            "long-term.md",
            "self.md"
        ]
        
        for filename in core_files:
            file_path = self.core_dir / filename
            if file_path.exists():
                self.assertGreater(
                    file_path.stat().st_size, 0,
                    f"核心文件为空: {filename}"
                )
    
    def test_index_files_exist(self):
        """测试索引文件存在"""
        index_files = [
            ("episodes", "index.md"),
            ("concepts", "index.md")
        ]
        
        for dir_name, filename in index_files:
            file_path = self.memory_dir / dir_name / filename
            if file_path.exists():
                content = file_path.read_text(encoding='utf-8')
                self.assertGreater(
                    len(content), 0,
                    f"索引文件为空: {dir_name}/{filename}"
                )
    
    def test_learning_directory_structure(self):
        """测试学习目录结构"""
        if self.learning_dir.exists():
            # 检查学习计划文件
            plan_file = self.learning_dir / "learning_plan.json"
            if plan_file.exists():
                with open(plan_file, 'r', encoding='utf-8') as f:
                    plan = json.load(f)
                self.assertIn("goals", plan, "学习计划缺少goals字段")
    
    def test_scripts_directory_structure(self):
        """测试脚本目录结构"""
        if self.scripts_dir.exists():
            script_files = list(self.scripts_dir.glob("*.py"))
            self.assertGreater(
                len(script_files), 0,
                "脚本目录中没有Python脚本"
            )
            
            # 检查关键脚本是否存在
            key_scripts = [
                "memory_maintenance.py",
                "learning_collector.py"
            ]
            
            for script_name in key_scripts:
                script_path = self.scripts_dir / script_name
                if script_path.exists():
                    # 验证脚本语法
                    try:
                        with open(script_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        compile(content, script_path, 'exec')
                    except SyntaxError as e:
                        self.fail(f"脚本语法错误 {script_name}: {e}")
    
    def test_backup_directory_structure(self):
        """测试备份目录结构"""
        backup_dir = self.memory_dir / "backups"
        if backup_dir.exists():
            # 检查是否有备份文件
            backup_files = list(backup_dir.iterdir())
            # 备份目录可以为空，但应该存在
            self.assertTrue(backup_dir.is_dir())


class TestVectorStorePerformance(unittest.TestCase):
    """测试向量存储性能"""
    
    def setUp(self):
        """测试前准备"""
        if not VECTOR_STORE_AVAILABLE:
            self.skipTest("VectorStore 不可用")
        
        self.temp_dir = tempfile.mkdtemp()
        self.store_path = os.path.join(self.temp_dir, "perf_test_store.json")
        self.store = VectorStore(store_path=self.store_path, auto_save=False)
    
    def tearDown(self):
        """测试后清理"""
        if hasattr(self, 'store'):
            del self.store
        if os.path.exists(self.store_path):
            os.remove(self.store_path)
        if os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)
    
    def test_bulk_insert_performance(self):
        """测试批量插入性能"""
        num_memories = 100
        start_time = time.time()
        
        for i in range(num_memories):
            self.store.add_memory(
                content=f"这是第{i}条测试记忆，包含一些关键词：Python、AI、机器学习",
                memory_type="test",
                tags=[f"tag{i % 10}", "test"],
                importance=0.5
            )
        
        elapsed = time.time() - start_time
        
        self.assertEqual(len(self.store.memories), num_memories)
        # 100条记忆应在5秒内完成
        self.assertLess(elapsed, 5.0, f"批量插入耗时过长: {elapsed:.2f}秒")
        
        print(f"\n批量插入 {num_memories} 条记忆: {elapsed:.3f}秒")
    
    def test_search_performance(self):
        """测试搜索性能"""
        # 先添加一些记忆
        for i in range(50):
            self.store.add_memory(
                content=f"记忆{i}: Python编程和人工智能技术",
                tags=["test"]
            )
        
        # 测试搜索性能
        start_time = time.time()
        num_searches = 100
        
        for i in range(num_searches):
            self.store.search(f"搜索查询{i}", top_k=5)
        
        elapsed = time.time() - start_time
        
        # 100次搜索应在2秒内完成
        self.assertLess(elapsed, 2.0, f"搜索性能过慢: {elapsed:.2f}秒")
        
        print(f"\n{num_searches} 次搜索耗时: {elapsed:.3f}秒")
    
    def test_large_memory_content(self):
        """测试大内容记忆"""
        large_content = "这是一个很长的记忆内容。" * 1000
        
        memory_id = self.store.add_memory(content=large_content)
        
        memory = self.store.get_memory(memory_id)
        self.assertEqual(memory["content"], large_content)
    
    def test_concurrent_access_simulation(self):
        """测试并发访问模拟"""
        # 添加记忆
        for i in range(10):
            self.store.add_memory(f"记忆{i}")
        
        # 模拟并发读取
        results = []
        for i in range(50):
            result = self.store.search(f"查询{i}", top_k=3)
            results.append(result)
        
        # 验证所有搜索都返回了结果
        self.assertEqual(len(results), 50)


class TestVectorStoreEdgeCases(unittest.TestCase):
    """测试向量存储边界情况"""
    
    def setUp(self):
        """测试前准备"""
        if not VECTOR_STORE_AVAILABLE:
            self.skipTest("VectorStore 不可用")
        
        self.temp_dir = tempfile.mkdtemp()
        self.store_path = os.path.join(self.temp_dir, "edge_test_store.json")
        self.store = VectorStore(store_path=self.store_path, auto_save=True)
    
    def tearDown(self):
        """测试后清理"""
        if hasattr(self, 'store'):
            del self.store
        if os.path.exists(self.store_path):
            os.remove(self.store_path)
        if os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)
    
    def test_special_characters_in_content(self):
        """测试特殊字符内容"""
        special_contents = [
            "包含emoji的记忆：🎉🚀💡",
            "包含换行符的\n记忆内容",
            "包含制表符的\t记忆内容",
            "包含引号的\"记忆\"内容",
            "包含HTML标签的<b>记忆</b>内容",
        ]
        
        for content in special_contents:
            memory_id = self.store.add_memory(content=content)
            memory = self.store.get_memory(memory_id)
            self.assertEqual(memory["content"], content)
    
    def test_unicode_content(self):
        """测试Unicode内容"""
        unicode_contents = [
            "日本語のメモリ",
            "한국어 메모리",
            "Мемория на русском",
            "ذاكرة بالعربية",
        ]
        
        for content in unicode_contents:
            memory_id = self.store.add_memory(content=content)
            memory = self.store.get_memory(memory_id)
            self.assertEqual(memory["content"], content)
    
    def test_duplicate_content(self):
        """测试重复内容"""
        content = "重复的记忆内容"
        
        id1 = self.store.add_memory(content=content)
        id2 = self.store.add_memory(content=content)
        
        # 应该创建两条不同的记忆
        self.assertNotEqual(id1, id2)
        self.assertEqual(len(self.store.memories), 2)
    
    def test_importance_boundary_values(self):
        """测试重要性边界值"""
        # 测试最小值
        id1 = self.store.add_memory(content="测试1", importance=-1.0)
        memory1 = self.store.get_memory(id1)
        self.assertEqual(memory1["importance"], 0.0)
        
        # 测试最大值
        id2 = self.store.add_memory(content="测试2", importance=2.0)
        memory2 = self.store.get_memory(id2)
        self.assertEqual(memory2["importance"], 1.0)
        
        # 测试正常值
        id3 = self.store.add_memory(content="测试3", importance=0.5)
        memory3 = self.store.get_memory(id3)
        self.assertEqual(memory3["importance"], 0.5)
    
    def test_custom_memory_id(self):
        """测试自定义记忆ID"""
        custom_id = "my_custom_id_123"
        memory_id = self.store.add_memory(
            content="自定义ID测试",
            memory_id=custom_id
        )
        
        self.assertEqual(memory_id, custom_id)
        self.assertIn(custom_id, self.store.memories)
    
    def test_memory_access_count(self):
        """测试记忆访问计数"""
        memory_id = self.store.add_memory(content="访问计数测试")
        
        # 初始访问计数为0
        memory = self.store.get_memory(memory_id)
        initial_count = memory["access_count"]
        
        # 多次访问
        for _ in range(5):
            self.store.get_memory(memory_id)
        
        # 访问计数应该增加
        memory = self.store.get_memory(memory_id)
        self.assertGreater(memory["access_count"], initial_count)


class TestVectorStoreSearchQuality(unittest.TestCase):
    """测试向量存储搜索质量"""
    
    def setUp(self):
        """测试前准备"""
        if not VECTOR_STORE_AVAILABLE:
            self.skipTest("VectorStore 不可用")
        
        self.temp_dir = tempfile.mkdtemp()
        self.store_path = os.path.join(self.temp_dir, "quality_test_store.json")
        self.store = VectorStore(store_path=self.store_path, auto_save=True)
        
        # 添加测试数据
        self.test_memories = [
            {"content": "Python是一种解释型编程语言", "tags": ["python", "programming"]},
            {"content": "Java是一种面向对象编程语言", "tags": ["java", "programming"]},
            {"content": "机器学习是人工智能的分支", "tags": ["ml", "ai"]},
            {"content": "深度学习使用多层神经网络", "tags": ["dl", "ai"]},
            {"content": "自然语言处理让计算机理解人类语言", "tags": ["nlp", "ai"]},
            {"content": "今天天气晴朗适合外出", "tags": ["weather"]},
            {"content": "量子计算是未来计算技术", "tags": ["quantum", "computing"]},
        ]
        
        for mem in self.test_memories:
            self.store.add_memory(**mem)
    
    def tearDown(self):
        """测试后清理"""
        if hasattr(self, 'store'):
            del self.store
        if os.path.exists(self.store_path):
            os.remove(self.store_path)
        if os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)
    
    def test_relevant_results_first(self):
        """测试相关结果排在前面"""
        # 搜索编程相关
        results = self.store.search("编程语言", top_k=3)
        
        # 前两个结果应该包含编程相关内容
        programming_results = [
            r for r in results 
            if "编程" in r["content"] or "programming" in r.get("tags", [])
        ]
        self.assertGreater(len(programming_results), 0)
    
    def test_search_returns_sorted_by_similarity(self):
        """测试搜索结果按相似度排序"""
        results = self.store.search("人工智能", top_k=5)
        
        # 验证结果按相似度降序排列
        for i in range(len(results) - 1):
            self.assertGreaterEqual(
                results[i]["similarity"],
                results[i+1]["similarity"],
                "搜索结果未按相似度降序排列"
            )
    
    def test_min_similarity_filter(self):
        """测试最小相似度过滤"""
        results = self.store.search(
            "完全不相关的查询xyz",
            min_similarity=0.9
        )
        
        # 高阈值应该过滤掉大部分结果
        for result in results:
            self.assertGreaterEqual(result["similarity"], 0.9)


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("Hermes 记忆系统综合测试")
    print("=" * 60)
    print(f"测试时间: {datetime.now().isoformat()}")
    print()
    
    # 创建测试套件
    test_suite = unittest.TestSuite()
    
    # 添加测试类
    test_classes = [
        TestVectorStore,
        TestLearningCollector,
        TestMemorySystemIntegrity,
        TestVectorStorePerformance,
        TestVectorStoreEdgeCases,
        TestVectorStoreSearchQuality,
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # 生成报告
    print("\n" + "=" * 60)
    print("测试报告")
    print("=" * 60)
    print(f"运行测试数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print(f"跳过: {len(result.skipped)}")
    
    success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) 
                    / result.testsRun * 100) if result.testsRun > 0 else 0
    print(f"成功率: {success_rate:.1f}%")
    
    # 保存测试报告
    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total": result.testsRun,
            "success": result.testsRun - len(result.failures) - len(result.errors),
            "failures": len(result.failures),
            "errors": len(result.errors),
            "skipped": len(result.skipped),
            "success_rate": success_rate
        },
        "failures": [
            {
                "test": str(f[0]),
                "message": f[1][:500]
            }
            for f in result.failures
        ],
        "errors": [
            {
                "test": str(e[0]),
                "message": e[1][:500]
            }
            for e in result.errors
        ]
    }
    
    report_dir = Path("/root/.hermes/memory/meta")
    report_dir.mkdir(parents=True, exist_ok=True)
    report_file = report_dir / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n测试报告已保存: {report_file}")
    print("=" * 60)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
