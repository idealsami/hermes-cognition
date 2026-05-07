#!/usr/bin/env python3
"""
Hermes 持续学习机制
- 自动收集学习素材
- 定期学习和总结
- 将学习成果应用到记忆中
"""

import os
import json
import subprocess
from datetime import datetime
from pathlib import Path

MEMORY_DIR = Path("/root/.hermes/memory")
LEARNING_DIR = MEMORY_DIR / "learning"
LEARNING_DIR.mkdir(exist_ok=True)

def collect_learning_materials():
    """收集学习素材"""
    materials = {
        "timestamp": datetime.now().isoformat(),
        "sources": []
    }
    
    # 1. 从对话历史中学习
    episodes_dir = MEMORY_DIR / "episodes"
    if episodes_dir.exists():
        for episode in episodes_dir.glob("*.md"):
            materials["sources"].append({
                "type": "episode",
                "path": str(episode),
                "learning": "从事件中提取经验"
            })
    
    # 2. 从技能中学习
    skills_dir = Path("/root/.hermes/hermes-agent/.agents/skills")
    if skills_dir.exists():
        for skill in skills_dir.glob("**/*.md"):
            materials["sources"].append({
                "type": "skill",
                "path": str(skill),
                "learning": "从技能中提取知识"
            })
    
    # 3. 从概念库中学习
    concepts_file = MEMORY_DIR / "concepts" / "index.md"
    if concepts_file.exists():
        materials["sources"].append({
            "type": "concepts",
            "path": str(concepts_file),
            "learning": "从概念库中巩固知识"
        })
    
    return materials

def analyze_learning_progress():
    """分析学习进度"""
    progress = {
        "timestamp": datetime.now().isoformat(),
        "memory_count": 0,
        "episode_count": 0,
        "concept_count": 0,
        "skill_count": 0
    }
    
    # 统计记忆数量
    long_term_file = MEMORY_DIR / "core" / "long-term.md"
    if long_term_file.exists():
        with open(long_term_file, 'r') as f:
            content = f.read()
            progress["memory_count"] = content.count('\n')
    
    # 统计事件数量
    episodes_dir = MEMORY_DIR / "episodes"
    if episodes_dir.exists():
        progress["episode_count"] = len(list(episodes_dir.glob("*.md")))
    
    # 统计概念数量
    concepts_file = MEMORY_DIR / "concepts" / "index.md"
    if concepts_file.exists():
        with open(concepts_file, 'r') as f:
            content = f.read()
            progress["concept_count"] = content.count('\n')
    
    # 统计技能数量
    skills_dir = Path("/root/.hermes/hermes-agent/.agents/skills")
    if skills_dir.exists():
        progress["skill_count"] = len(list(skills_dir.glob("**/*.md")))
    
    return progress

def generate_learning_report():
    """生成学习报告"""
    materials = collect_learning_materials()
    progress = analyze_learning_progress()
    
    report = f"""# Hermes 学习报告
生成时间: {datetime.now().isoformat()}

## 学习进度
- 记忆条目: {progress['memory_count']}
- 事件记录: {progress['episode_count']}
- 概念数量: {progress['concept_count']}
- 技能数量: {progress['skill_count']}

## 学习素材来源
"""
    
    for source in materials["sources"]:
        report += f"- {source['type']}: {source['learning']}\n"
    
    report += f"""
## 学习建议
1. 增加事件记录，丰富记忆
2. 深化概念理解，建立关联
3. 学习新技能，扩展能力
4. 定期复习，巩固记忆
"""
    
    return report

def main():
    """主函数"""
    report = generate_learning_report()
    
    # 保存报告
    report_file = LEARNING_DIR / f"learning_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(report_file, 'w') as f:
        f.write(report)
    
    print(f"学习报告已生成: {report_file}")
    print(report)

if __name__ == "__main__":
    main()
