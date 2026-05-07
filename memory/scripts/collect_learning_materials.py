#!/usr/bin/env python3
"""
学习素材收集脚本 - 从互联网收集AGI/意识/认知科学资料
"""
import os
import json
import requests
from datetime import datetime
from pathlib import Path
import subprocess

class LearningCollector:
    def __init__(self):
        self.base_dir = Path("/root/.hermes/memory")
        self.learning_dir = self.base_dir / "learning"
        self.learning_dir.mkdir(parents=True, exist_ok=True)
        
        # 学习主题
        self.topics = [
            "artificial general intelligence",
            "machine consciousness",
            "cognitive architecture",
            "self-awareness in AI",
            "memory systems in AI",
            "attention mechanism",
            "transformer architecture",
            "reinforcement learning",
            "meta-learning",
            "neural networks"
        ]
    
    def search_arxiv(self, query, max_results=5):
        """从arXiv搜索最新论文"""
        try:
            base_url = "http://export.arxiv.org/api/query"
            params = {
                "search_query": f"all:{query}",
                "start": 0,
                "max_results": max_results,
                "sortBy": "lastUpdatedDate",
                "sortOrder": "descending"
            }
            
            response = requests.get(base_url, params=params, timeout=30)
            if response.status_code == 200:
                # 简化解析，实际应用需要XML解析
                return {"query": query, "status": "success", "raw": response.text[:2000]}
            else:
                return {"query": query, "status": "error", "code": response.status_code}
                
        except Exception as e:
            return {"query": query, "status": "error", "message": str(e)}
    
    def search_github_repos(self, query):
        """搜索GitHub相关仓库"""
        try:
            headers = {"Accept": "application/vnd.github.v3+json"}
            url = f"https://api.github.com/search/repositories?q={query}&sort=updated&order=desc&per_page=5"
            
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                data = response.json()
                repos = []
                for repo in data.get("items", []):
                    repos.append({
                        "name": repo["full_name"],
                        "description": repo.get("description", ""),
                        "url": repo["html_url"],
                        "stars": repo.get("stargazers_count", 0),
                        "updated": repo.get("updated_at", "")
                    })
                return {"query": query, "status": "success", "repos": repos}
            else:
                return {"query": query, "status": "error", "code": response.status_code}
                
        except Exception as e:
            return {"query": query, "status": "error", "message": str(e)}
    
    def collect_learning_materials(self):
        """收集学习素材"""
        print("开始收集学习素材...")
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "arxiv_papers": [],
            "github_repos": [],
            "summary": {}
        }
        
        # 搜索arXiv论文
        print("搜索arXiv论文...")
        for topic in self.topics[:3]:  # 先搜索3个主题
            result = self.search_arxiv(topic)
            results["arxiv_papers"].append(result)
            print(f"  - {topic}: {result['status']}")
        
        # 搜索GitHub仓库
        print("搜索GitHub仓库...")
        for topic in ["AGI", "consciousness-AI", "cognitive-architecture"]:
            result = self.search_github_repos(topic)
            results["github_repos"].append(result)
            print(f"  - {topic}: {result['status']}")
        
        # 生成摘要
        results["summary"] = {
            "total_topics": len(self.topics),
            "arxiv_searches": len(results["arxiv_papers"]),
            "github_searches": len(results["github_repos"]),
            "collection_time": datetime.now().isoformat()
        }
        
        # 保存结果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.learning_dir / f"learning_materials_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"学习素材已保存到: {filename}")
        return results
    
    def create_learning_plan(self):
        """创建学习计划"""
        plan = {
            "created": datetime.now().isoformat(),
            "goals": [
                "理解AGI的核心概念和实现路径",
                "研究机器意识的理论框架",
                "学习认知架构的设计原理",
                "掌握注意力机制和Transformer架构",
                "探索元学习和自我改进方法"
            ],
            "schedule": {
                "daily": "阅读1-2篇相关论文或文章",
                "weekly": "总结学习成果，更新概念库",
                "monthly": "评估学习进展，调整学习方向"
            },
            "resources": {
                "arxiv": "最新研究论文",
                "github": "开源实现和项目",
                "books": "经典教材和专著",
                "courses": "在线课程和教程"
            }
        }
        
        plan_file = self.learning_dir / "learning_plan.json"
        with open(plan_file, 'w', encoding='utf-8') as f:
            json.dump(plan, f, ensure_ascii=False, indent=2)
        
        print(f"学习计划已保存到: {plan_file}")
        return plan

def main():
    collector = LearningCollector()
    
    # 创建学习计划
    print("=== 创建学习计划 ===")
    collector.create_learning_plan()
    
    # 收集学习素材
    print("\n=== 收集学习素材 ===")
    results = collector.collect_learning_materials()
    
    # 显示摘要
    print("\n=== 收集摘要 ===")
    print(f"收集时间: {results['summary']['collection_time']}")
    print(f"arXiv搜索: {results['summary']['arxiv_searches']}个主题")
    print(f"GitHub搜索: {results['summary']['github_searches']}个主题")
    
    print("\n学习素材收集完成！")

if __name__ == "__main__":
    main()
