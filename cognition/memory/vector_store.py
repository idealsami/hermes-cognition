"""
向量记忆库 (Vector Memory Store)

用于存储和检索记忆的语义向量，支持：
- TF-IDF 文本嵌入
- 余弦相似度搜索
- JSON 持久化存储
- 记忆的增删改查

使用示例：
    store = VectorStore("/path/to/store.json")
    store.add_memory("今天学习了Python编程", tags=["learning", "python"])
    results = store.search("编程语言学习", top_k=3)
"""

import json
import os
import re
import math
import uuid
import tempfile
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple
from collections import Counter
from pathlib import Path


class VectorStore:
    """向量记忆库，支持基于TF-IDF的语义搜索"""

    def __init__(self, store_path: str = None, auto_save: bool = True):
        """
        初始化向量记忆库
        
        Args:
            store_path: 持久化存储路径，默认为同目录下的 vector_memory.json
            auto_save: 是否在修改时自动保存
        """
        if store_path is None:
            store_path = os.path.join(os.path.dirname(__file__), "vector_memory.json")
        
        self.store_path = store_path
        self.auto_save = auto_save
        
        # 记忆存储: {id: memory_record}
        self.memories: Dict[str, Dict[str, Any]] = {}
        
        # TF-IDF 相关
        self.document_vectors: Dict[str, Dict[str, float]] = {}  # {id: {term: tfidf_score}}
        self.idf_cache: Dict[str, float] = {}  # {term: idf_score}
        self.vocabulary: set = set()
        self.num_documents = 0
        
        # 停用词（中英文常见停用词）
        self.stop_words = {
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
            '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好',
            '自己', '这', '他', '她', '它', '们', '那', '些', '么', '什么', '怎么', '吗',
            '吧', '啊', '呢', '哦', '嗯', '把', '被', '让', '给', '从', '向', '对', '与',
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'shall', 'can', 'need', 'dare', 'to', 'of',
            'in', 'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into', 'through',
            'during', 'before', 'after', 'above', 'below', 'between', 'out', 'off',
            'over', 'under', 'again', 'further', 'then', 'once', 'and', 'but', 'or',
            'nor', 'not', 'so', 'if', 'when', 'where', 'how', 'what', 'which', 'who',
            'whom', 'this', 'that', 'these', 'those', 'i', 'me', 'my', 'he', 'him',
            'his', 'she', 'her', 'we', 'us', 'they', 'them', 'their', 'it', 'its',
        }
        
        # 加载已有数据
        self._load()

    def _tokenize(self, text: str) -> List[str]:
        """
        分词器，支持中英文混合文本
        
        对中文按字符分词（单字 + 双字组合）
        对英文按空格和标点分词
        """
        text = text.lower()
        
        # 提取中文字符序列
        chinese_chars = re.findall(r'[\u4e00-\u9fff]+', text)
        # 提取英文单词
        english_words = re.findall(r'[a-z]+(?:\'[a-z]+)?', text)
        # 提取数字
        numbers = re.findall(r'\d+', text)
        
        tokens = []
        
        # 中文分词：单字 + 双字组合（简单n-gram）
        for segment in chinese_chars:
            if len(segment) > 0:
                for i in range(len(segment)):
                    tokens.append(segment[i])
                for i in range(len(segment) - 1):
                    tokens.append(segment[i:i+2])
        
        # 英文分词
        for word in english_words:
            if word not in self.stop_words and len(word) > 1:
                tokens.append(word)
        
        # 数字
        for num in numbers:
            tokens.append(f"num_{num}")
        
        return tokens

    def _compute_tf(self, tokens: List[str]) -> Dict[str, float]:
        """计算词频 (Term Frequency)"""
        if not tokens:
            return {}
        
        counter = Counter(tokens)
        
        # 使用对数归一化的TF
        tf = {}
        for term, freq in counter.items():
            tf[term] = 1 + math.log(freq) if freq > 0 else 0
        
        return tf

    def _compute_idf(self) -> None:
        """计算逆文档频率 (Inverse Document Frequency)，缓存结果"""
        self.num_documents = len(self.document_vectors)
        if self.num_documents == 0:
            return
        
        # 统计每个词出现在多少文档中
        doc_freq = Counter()
        for doc_vector in self.document_vectors.values():
            for term in doc_vector.keys():
                doc_freq[term] += 1
        
        # IDF = log(N / (1 + df))，使用平滑
        self.idf_cache = {}
        for term, df in doc_freq.items():
            self.idf_cache[term] = math.log(self.num_documents / (1 + df))
        
        # 更新词汇表
        self.vocabulary = set(doc_freq.keys())

    def _vectorize(self, text: str) -> Dict[str, float]:
        """将文本转换为TF-IDF向量"""
        tokens = self._tokenize(text)
        tf = self._compute_tf(tokens)
        
        # 计算TF-IDF
        vector = {}
        for term, tf_score in tf.items():
            idf_score = self.idf_cache.get(term, math.log(max(self.num_documents, 1)))
            vector[term] = tf_score * idf_score
        
        return vector

    def _cosine_similarity(self, vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
        """计算两个稀疏向量的余弦相似度"""
        if not vec1 or not vec2:
            return 0.0
        
        # 计算点积
        dot_product = 0.0
        for term in vec1:
            if term in vec2:
                dot_product += vec1[term] * vec2[term]
        
        # 计算向量范数
        norm1 = math.sqrt(sum(v * v for v in vec1.values()))
        norm2 = math.sqrt(sum(v * v for v in vec2.values()))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)

    def _generate_id(self) -> str:
        """生成唯一ID (使用UUID避免碰撞)"""
        return f"mem_{uuid.uuid4().hex}"

    def _save(self) -> None:
        """保存到JSON文件（原子写入，异常安全）"""
        data = {
            "memories": self.memories,
            "document_vectors": self.document_vectors,
            "idf_cache": self.idf_cache,
            "vocabulary": list(self.vocabulary),
            "num_documents": self.num_documents,
            "metadata": {
                "last_saved": datetime.now().isoformat(),
                "total_memories": len(self.memories),
            }
        }
        
        try:
            store_dir = os.path.dirname(self.store_path)
            if store_dir:
                os.makedirs(store_dir, exist_ok=True)
            
            # 先写临时文件，再原子替换，防止写入中断导致数据损坏
            fd, tmp_path = tempfile.mkstemp(
                dir=store_dir or '.', suffix='.tmp', prefix='.vecstore_'
            )
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                os.replace(tmp_path, self.store_path)
            except Exception:
                # 清理临时文件
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise
        except OSError as e:
            print(f"[VectorStore] 保存失败 (IO错误): {e}")
        except (TypeError, ValueError) as e:
            print(f"[VectorStore] 保存失败 (序列化错误): {e}")

    def _load(self) -> None:
        """从JSON文件加载"""
        if not os.path.exists(self.store_path):
            return
        
        try:
            with open(self.store_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.memories = data.get("memories", {})
            self.document_vectors = data.get("document_vectors", {})
            self.idf_cache = data.get("idf_cache", {})
            self.vocabulary = set(data.get("vocabulary", []))
            self.num_documents = data.get("num_documents", 0)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"[VectorStore] 加载失败，将使用空存储: {e}")
        except OSError as e:
            print(f"[VectorStore] 加载失败 (IO错误)，将使用空存储: {e}")

    def _rebuild_index(self) -> None:
        """重建所有向量索引"""
        self.document_vectors = {}
        for mem_id, memory in self.memories.items():
            text = memory.get("content", "")
            tokens = self._tokenize(text)
            self.document_vectors[mem_id] = self._compute_tf(tokens)
        
        self._compute_idf()
        
        # 用更新后的IDF重新计算向量
        for mem_id, memory in self.memories.items():
            text = memory.get("content", "")
            self.document_vectors[mem_id] = self._vectorize(text)

    def add_memory(
        self,
        content: str,
        memory_id: str = None,
        memory_type: str = "general",
        tags: List[str] = None,
        metadata: Dict[str, Any] = None,
        importance: float = 0.5
    ) -> str:
        """
        添加一条记忆
        
        Args:
            content: 记忆内容文本
            memory_id: 自定义ID，默认自动生成
            memory_type: 记忆类型（如 fact, experience, skill, emotion 等）
            tags: 标签列表
            metadata: 额外元数据
            importance: 重要性评分 (0-1)
            
        Returns:
            记忆ID
        """
        if not content or not content.strip():
            raise ValueError("记忆内容不能为空")
        
        mem_id = memory_id if memory_id else self._generate_id()
        
        # 创建记忆记录
        memory_record = {
            "id": mem_id,
            "content": content.strip(),
            "type": memory_type,
            "tags": tags or [],
            "metadata": metadata or {},
            "importance": max(0.0, min(1.0, importance)),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "access_count": 0,
            "last_accessed": None,
        }
        
        # 存储记忆
        self.memories[mem_id] = memory_record
        
        # 重建IDF（因为文档集变了），然后计算新文档的TF-IDF向量
        self._compute_idf()
        self.document_vectors[mem_id] = self._vectorize(content)
        
        if self.auto_save:
            self._save()
        
        return mem_id

    def update_memory(
        self,
        memory_id: str,
        content: str = None,
        memory_type: str = None,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None,
        importance: float = None
    ) -> bool:
        """
        更新一条记忆
        
        Args:
            memory_id: 记忆ID
            content: 新内容（可选）
            memory_type: 新类型（可选）
            tags: 新标签（可选）
            metadata: 新元数据（可选）
            importance: 新重要性（可选）
            
        Returns:
            是否成功
        """
        if memory_id not in self.memories:
            return False
        
        memory = self.memories[memory_id]
        
        if content is not None:
            memory["content"] = content.strip()
            # 先更新该文档向量，再重建IDF，最后用新IDF更新所有文档向量
            self.document_vectors[memory_id] = self._vectorize(content)
            self._compute_idf()
            # IDF变了，需要用新IDF更新所有文档的向量
            for mid, mem in self.memories.items():
                self.document_vectors[mid] = self._vectorize(mem.get("content", ""))
        
        if memory_type is not None:
            memory["type"] = memory_type
        if tags is not None:
            memory["tags"] = tags
        if metadata is not None:
            memory["metadata"].update(metadata)
        if importance is not None:
            memory["importance"] = max(0.0, min(1.0, importance))
        
        memory["updated_at"] = datetime.now().isoformat()
        
        if self.auto_save:
            self._save()
        
        return True

    def delete_memory(self, memory_id: str) -> bool:
        """
        删除一条记忆
        
        Args:
            memory_id: 记忆ID
            
        Returns:
            是否成功删除
        """
        if memory_id not in self.memories:
            return False
        
        del self.memories[memory_id]
        if memory_id in self.document_vectors:
            del self.document_vectors[memory_id]
        
        # 重建索引
        self._compute_idf()
        
        if self.auto_save:
            self._save()
        
        return True

    def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """
        获取一条记忆
        
        Args:
            memory_id: 记忆ID
            
        Returns:
            记忆记录，不存在则返回None
        """
        memory = self.memories.get(memory_id)
        if memory:
            # 更新访问信息（仅更新内存，不触发磁盘写入）
            memory["access_count"] = memory.get("access_count", 0) + 1
            memory["last_accessed"] = datetime.now().isoformat()
        return memory

    def search(
        self,
        query: str,
        top_k: int = 5,
        memory_type: str = None,
        tags: List[str] = None,
        min_similarity: float = 0.0,
        boost_importance: bool = True
    ) -> List[Dict[str, Any]]:
        """
        语义搜索记忆
        
        Args:
            query: 查询文本
            top_k: 返回前K个结果
            memory_type: 过滤记忆类型
            tags: 过滤标签（包含任一标签即可）
            min_similarity: 最低相似度阈值
            boost_importance: 是否提升重要记忆的排名
            
        Returns:
            匹配的记忆列表，每个包含 similarity 字段
        """
        if not query or not query.strip():
            return []
        
        if top_k is None or top_k < 1:
            top_k = 1
        
        # 将查询向量化
        query_vector = self._vectorize(query)
        
        results = []
        
        for mem_id, memory in self.memories.items():
            # 类型过滤
            if memory_type and memory.get("type") != memory_type:
                continue
            
            # 标签过滤
            if tags:
                memory_tags = set(memory.get("tags", []))
                if not any(tag in memory_tags for tag in tags):
                    continue
            
            # 计算相似度
            doc_vector = self.document_vectors.get(mem_id, {})
            similarity = self._cosine_similarity(query_vector, doc_vector)
            
            # 提升重要性
            if boost_importance:
                importance = memory.get("importance", 0.5)
                similarity = similarity * 0.7 + importance * 0.3
            
            # 相似度过滤
            if similarity < min_similarity:
                continue
            
            # 创建结果副本，附加相似度
            result = memory.copy()
            result["similarity"] = round(similarity, 6)
            results.append(result)
        
        # 按相似度排序
        results.sort(key=lambda x: x["similarity"], reverse=True)
        
        # 更新访问记录
        for result in results[:top_k]:
            mem_id = result["id"]
            if mem_id in self.memories:
                self.memories[mem_id]["access_count"] = self.memories[mem_id].get("access_count", 0) + 1
                self.memories[mem_id]["last_accessed"] = datetime.now().isoformat()
        
        if self.auto_save:
            self._save()
        
        return results[:top_k]

    def search_by_tags(
        self,
        tags: List[str],
        match_all: bool = False
    ) -> List[Dict[str, Any]]:
        """
        按标签搜索记忆
        
        Args:
            tags: 标签列表
            match_all: 是否要求匹配所有标签
            
        Returns:
            匹配的记忆列表
        """
        results = []
        
        for memory in self.memories.values():
            memory_tags = set(memory.get("tags", []))
            
            if match_all:
                if all(tag in memory_tags for tag in tags):
                    results.append(memory.copy())
            else:
                if any(tag in memory_tags for tag in tags):
                    results.append(memory.copy())
        
        return results

    def list_memories(
        self,
        memory_type: str = None,
        limit: int = None
    ) -> List[Dict[str, Any]]:
        """
        列出所有记忆
        
        Args:
            memory_type: 过滤类型
            limit: 最大返回数量
            
        Returns:
            记忆列表
        """
        memories = list(self.memories.values())
        
        if memory_type:
            memories = [m for m in memories if m.get("type") == memory_type]
        
        # 按创建时间降序
        memories.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        if limit:
            memories = memories[:limit]
        
        return memories

    def get_similar_memories(
        self,
        memory_id: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        获取与指定记忆相似的其他记忆
        
        Args:
            memory_id: 记忆ID
            top_k: 返回前K个
            
        Returns:
            相似记忆列表
        """
        if memory_id not in self.memories:
            return []
        
        target_vector = self.document_vectors.get(memory_id, {})
        
        results = []
        for mem_id, doc_vector in self.document_vectors.items():
            if mem_id == memory_id:
                continue
            
            similarity = self._cosine_similarity(target_vector, doc_vector)
            result = self.memories[mem_id].copy()
            result["similarity"] = round(similarity, 6)
            results.append(result)
        
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]

    def clear(self) -> None:
        """清空所有记忆"""
        self.memories.clear()
        self.document_vectors.clear()
        self.idf_cache.clear()
        self.vocabulary.clear()
        self.num_documents = 0
        
        if self.auto_save:
            self._save()

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        type_counts = Counter(m.get("type", "unknown") for m in self.memories.values())
        
        return {
            "total_memories": len(self.memories),
            "vocabulary_size": len(self.vocabulary),
            "memory_types": dict(type_counts),
            "store_path": self.store_path,
            "store_size_bytes": os.path.getsize(self.store_path) if os.path.exists(self.store_path) else 0,
        }

    def save(self) -> None:
        """手动触发保存"""
        self._save()

    def load(self) -> None:
        """手动触发加载"""
        self._load()


def demo():
    """演示向量记忆库的使用"""
    print("=" * 60)
    print("向量记忆库 (Vector Memory Store) - 演示")
    print("=" * 60)
    
    # 使用临时存储路径
    demo_path = "/tmp/vector_store_demo.json"
    store = VectorStore(store_path=demo_path)
    store.clear()
    
    # 1. 添加记忆
    print("\n[1] 添加记忆...")
    memories_data = [
        {"content": "Python是一种解释型、面向对象的高级编程语言", "memory_type": "fact", "tags": ["python", "programming"], "importance": 0.8},
        {"content": "机器学习是人工智能的一个子领域，使用数据驱动的方法进行预测", "memory_type": "fact", "tags": ["ml", "ai"], "importance": 0.9},
        {"content": "深度学习使用多层神经网络来学习数据的层次化表示", "memory_type": "fact", "tags": ["dl", "ai", "neural_network"], "importance": 0.85},
        {"content": "今天在公园散步时看到了一只可爱的金毛犬", "memory_type": "experience", "tags": ["daily", "pet"], "importance": 0.3},
        {"content": "学习了向量数据库的原理，包括FAISS和Pinecone的实现方式", "memory_type": "learning", "tags": ["vector_db", "learning", "programming"], "importance": 0.7},
        {"content": "自然语言处理是让计算机理解人类语言的技术", "memory_type": "fact", "tags": ["nlp", "ai"], "importance": 0.8},
        {"content": "Hermes AI助手正在进化为通用人工智能系统", "memory_type": "fact", "tags": ["hermes", "agi"], "importance": 1.0},
        {"content": "向量空间中的余弦相似度可以衡量两个文本的语义相似程度", "memory_type": "learning", "tags": ["vector", "similarity", "nlp"], "importance": 0.75},
    ]
    
    for data in memories_data:
        mid = store.add_memory(**data)
        print(f"  添加: [{mid}] {data['content'][:30]}...")
    
    # 2. 统计信息
    print("\n[2] 统计信息:")
    stats = store.get_stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")
    
    # 3. 语义搜索
    print("\n[3] 语义搜索 '人工智能技术':")
    results = store.search("人工智能技术", top_k=3)
    for r in results:
        print(f"  [相似度:{r['similarity']:.4f}] {r['content'][:50]}...")
    
    print("\n[4] 语义搜索 '编程语言学习':")
    results = store.search("编程语言学习", top_k=3)
    for r in results:
        print(f"  [相似度:{r['similarity']:.4f}] {r['content'][:50]}...")
    
    print("\n[5] 语义搜索 '自然语言理解':")
    results = store.search("自然语言理解", top_k=3)
    for r in results:
        print(f"  [相似度:{r['similarity']:.4f}] {r['content'][:50]}...")
    
    # 4. 标签搜索
    print("\n[6] 标签搜索 [ai, ml]:")
    results = store.search_by_tags(["ai", "ml"])
    for r in results:
        print(f"  [{','.join(r['tags'])}] {r['content'][:50]}...")
    
    # 5. 类型过滤搜索
    print("\n[7] 过滤类型=learning 的搜索 '向量数据库':")
    results = store.search("向量数据库", memory_type="learning", top_k=3)
    for r in results:
        print(f"  [相似度:{r['similarity']:.4f}] {r['content'][:50]}...")
    
    # 6. 找相似记忆
    print("\n[8] 与 '机器学习' 相似的记忆:")
    ml_memory_id = list(store.search("机器学习", top_k=1))[0]["id"]
    similar = store.get_similar_memories(ml_memory_id, top_k=3)
    for s in similar:
        print(f"  [相似度:{s['similarity']:.4f}] {s['content'][:50]}...")
    
    # 7. 更新记忆
    print("\n[9] 更新记忆...")
    store.update_memory(ml_memory_id, importance=1.0, tags=["ml", "ai", "important"])
    updated = store.get_memory(ml_memory_id)
    print(f"  更新后的重要性: {updated['importance']}, 标签: {updated['tags']}")
    
    # 8. 持久化验证
    print("\n[10] 持久化验证 - 重新加载存储...")
    store2 = VectorStore(store_path=demo_path)
    stats2 = store2.get_stats()
    print(f"  重新加载后记忆数: {stats2['total_memories']}")
    results2 = store2.search("人工智能", top_k=1)
    if results2:
        print(f"  搜索成功: {results2[0]['content'][:50]}...")
    
    # 清理
    os.remove(demo_path)
    print("\n" + "=" * 60)
    print("演示完成！所有功能正常工作。")
    print("=" * 60)


if __name__ == "__main__":
    demo()
