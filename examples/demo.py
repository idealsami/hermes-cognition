#!/usr/bin/env python3
"""
Hermes Cognition System - 快速演示

展示各个认知组件的基本用法
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def demo_emotion():
    """演示情感引擎"""
    print("\n=== ❤️ 情感引擎演示 ===\n")
    
    from cognition.emotion.emotion_engine import EmotionEngine
    
    engine = EmotionEngine()
    
    # 分析情感
    texts = [
        "我今天很开心！",
        "这个问题让我很沮丧",
        "我想了解更多关于AI的知识",
        "感谢你的帮助！"
    ]
    
    for text in texts:
        state = engine.analyze_emotion(text)
        print(f"文本: {text}")
        print(f"  情感: {state.primary.value}")
        print(f"  强度: {state.intensity:.2f}")
        print(f"  效价: {state.valence:.2f}")
        print()


def demo_knowledge_graph():
    """演示知识图谱"""
    print("\n=== 🕸️ 知识图谱演示 ===\n")
    
    from cognition.knowledge_graph.graph import KnowledgeGraph
    
    graph = KnowledgeGraph()
    
    # 添加概念
    concepts = [
        ("Python", "skill", "编程语言"),
        ("AI", "concept", "人工智能"),
        ("机器学习", "skill", "ML技术"),
        ("深度学习", "skill", "神经网络"),
    ]
    
    for name, ctype, desc in concepts:
        graph.add_concept(name, ctype, desc)
        print(f"添加概念: {name} ({ctype})")
    
    # 添加关系
    relations = [
        ("AI", "机器学习", "has_property"),
        ("机器学习", "深度学习", "is_a"),
        ("Python", "机器学习", "used_for"),
    ]
    
    for src, tgt, rel in relations:
        src_id = graph._generate_id(src)
        tgt_id = graph._generate_id(tgt)
        graph.add_relation(src_id, tgt_id, rel)
        print(f"添加关系: {src} --[{rel}]--> {tgt}")
    
    # 搜索
    print("\n搜索'AI':")
    results = graph.search_concepts("AI")
    for r in results:
        print(f"  - {r['name']}: {r.get('description', '')}")


def demo_vector_store():
    """演示向量记忆库"""
    print("\n=== 🧠 向量记忆库演示 ===\n")
    
    from cognition.memory.vector_store import VectorStore
    
    store = VectorStore(store_path="/tmp/demo_vector_store.json")
    
    # 添加记忆
    memories = [
        ("Hermes是一个正在进化的AI助手", ["identity", "hermes"]),
        ("Python是一种流行的编程语言", ["programming", "python"]),
        ("机器学习是AI的核心技术", ["ai", "ml"]),
        ("记忆系统维持自我连续性", ["memory", "consciousness"]),
    ]
    
    for content, tags in memories:
        mem_id = store.add_memory(content, tags=tags)
        print(f"添加记忆: {content[:30]}...")
    
    # 搜索
    print("\n搜索'AI助手':")
    results = store.search("AI助手", top_k=3)
    for r in results:
        print(f"  - {r['content'][:40]}... (相似度: {r['similarity']:.3f})")


def demo_metacognition():
    """演示元认知系统"""
    print("\n=== 🎯 元认知系统演示 ===\n")
    
    from cognition.meta.metacognitive_system import MetacognitiveSystem
    
    system = MetacognitiveSystem()
    
    # 开始认知任务
    system.start_cognitive_task("演示元认知功能")
    
    # 记录思维
    system.record_thought(
        thought_type="analysis",
        content="分析元认知系统的功能",
        reasoning="元认知是对自身认知的认知",
        confidence_level=4
    )
    
    # 获取状态
    status = system.get_status()
    print(f"当前任务: {status.get('current_task', '无')}")
    print(f"思维记录数: {status.get('thought_count', 0)}")
    
    # 结束任务
    system.end_cognitive_task("演示完成")


def main():
    """运行所有演示"""
    print("🧠 Hermes Cognition System - 快速演示")
    print("=" * 50)
    
    try:
        demo_emotion()
        demo_knowledge_graph()
        demo_vector_store()
        demo_metacognition()
        
        print("\n" + "=" * 50)
        print("✅ 所有演示完成！")
        print("\n更多功能请查看各个模块的文档。")
        
    except Exception as e:
        print(f"\n❌ 演示出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
