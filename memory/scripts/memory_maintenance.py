#!/usr/bin/env python3
"""
记忆维护和优化系统 - 定期维护记忆库
"""
import os
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
import shutil

class MemoryMaintenance:
    def __init__(self):
        self.base_dir = Path("/root/.hermes/memory")
        self.backup_dir = self.base_dir / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # 记忆文件路径
        self.memory_files = {
            "long_term": self.base_dir / "core" / "long-term.md",
            "self_awareness": self.base_dir / "core" / "self.md",
            "episodes_index": self.base_dir / "episodes" / "index.md",
            "concepts_index": self.base_dir / "concepts" / "index.md",
            "biases_index": self.base_dir / "biases" / "index.md",
            "learning_plan": self.base_dir / "learning" / "learning_plan.json"
        }
    
    def backup_memories(self):
        """备份所有记忆文件"""
        print("开始备份记忆文件...")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_subdir = self.backup_dir / timestamp
        backup_subdir.mkdir(parents=True, exist_ok=True)
        
        backed_up = []
        for name, path in self.memory_files.items():
            if path.exists():
                backup_path = backup_subdir / path.name
                shutil.copy2(path, backup_path)
                backed_up.append(name)
                print(f"  ✓ 备份 {name}: {path.name}")
        
        # 备份episodes目录下的所有文件
        episodes_dir = self.base_dir / "episodes"
        if episodes_dir.exists():
            for file in episodes_dir.glob("*.md"):
                if file.name != "index.md":
                    backup_path = backup_subdir / file.name
                    shutil.copy2(file, backup_path)
                    backed_up.append(f"episodes/{file.name}")
                    print(f"  ✓ 备份 episodes/{file.name}")
        
        print(f"备份完成: {len(backed_up)} 个文件")
        return backup_subdir
    
    def analyze_memory_usage(self):
        """分析记忆使用情况"""
        print("\n分析记忆使用情况...")
        
        analysis = {
            "timestamp": datetime.now().isoformat(),
            "files": {},
            "total_size": 0,
            "total_lines": 0
        }
        
        for name, path in self.memory_files.items():
            if path.exists():
                stat = path.stat()
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = len(content.split('\n'))
                
                analysis["files"][name] = {
                    "size_bytes": stat.st_size,
                    "size_kb": round(stat.st_size / 1024, 2),
                    "lines": lines,
                    "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                }
                
                analysis["total_size"] += stat.st_size
                analysis["total_lines"] += lines
        
        print(f"总文件数: {len(analysis['files'])}")
        print(f"总大小: {analysis['total_size']} bytes ({round(analysis['total_size']/1024, 2)} KB)")
        print(f"总行数: {analysis['total_lines']}")
        
        return analysis
    
    def optimize_long_term_memory(self):
        """优化长期记忆文件"""
        print("\n优化长期记忆...")
        
        long_term_path = self.memory_files["long_term"]
        if not long_term_path.exists():
            print("长期记忆文件不存在")
            return False
        
        with open(long_term_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 分析内容结构
        sections = content.split('## ')
        optimized_sections = []
        
        for section in sections:
            if section.strip():
                # 清理多余的空行
                lines = section.split('\n')
                cleaned_lines = []
                prev_empty = False
                
                for line in lines:
                    is_empty = line.strip() == ''
                    if is_empty and prev_empty:
                        continue  # 跳过连续空行
                    cleaned_lines.append(line)
                    prev_empty = is_empty
                
                optimized_sections.append('\n'.join(cleaned_lines))
        
        # 重新组合
        optimized_content = '## '.join(optimized_sections)
        
        # 保存优化后的内容
        with open(long_term_path, 'w', encoding='utf-8') as f:
            f.write(optimized_content)
        
        print("长期记忆优化完成")
        return True
    
    def check_memory_integrity(self):
        """检查记忆完整性"""
        print("\n检查记忆完整性...")
        
        issues = []
        
        # 检查必要文件是否存在
        for name, path in self.memory_files.items():
            if not path.exists():
                issues.append(f"缺失文件: {name} ({path})")
        
        # 检查episodes目录
        episodes_dir = self.base_dir / "episodes"
        if episodes_dir.exists():
            index_path = episodes_dir / "index.md"
            if not index_path.exists():
                issues.append("episodes/index.md 不存在")
            
            # 检查是否有孤立的episode文件（没有在index中记录）
            episode_files = list(episodes_dir.glob("*.md"))
            if index_path.exists():
                with open(index_path, 'r', encoding='utf-8') as f:
                    index_content = f.read()
                
                for file in episode_files:
                    if file.name != "index.md" and file.name not in index_content:
                        issues.append(f"孤立的episode文件: {file.name}")
        
        if issues:
            print(f"发现 {len(issues)} 个问题:")
            for issue in issues:
                print(f"  ⚠ {issue}")
        else:
            print("✓ 记忆完整性检查通过")
        
        return issues
    
    def cleanup_old_backups(self, keep_days=7):
        """清理旧备份"""
        print(f"\n清理 {keep_days} 天前的备份...")
        
        cutoff_date = datetime.now() - timedelta(days=keep_days)
        deleted_count = 0
        
        for backup_dir in self.backup_dir.iterdir():
            if backup_dir.is_dir():
                try:
                    # 从目录名解析日期
                    dir_date = datetime.strptime(backup_dir.name, "%Y%m%d_%H%M%S")
                    if dir_date < cutoff_date:
                        shutil.rmtree(backup_dir)
                        deleted_count += 1
                        print(f"  ✓ 删除旧备份: {backup_dir.name}")
                except ValueError:
                    # 目录名不是日期格式，跳过
                    continue
        
        print(f"清理完成: 删除 {deleted_count} 个旧备份")
        return deleted_count
    
    def generate_maintenance_report(self):
        """生成维护报告"""
        print("\n生成维护报告...")
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "analysis": self.analyze_memory_usage(),
            "integrity_check": self.check_memory_integrity(),
            "maintenance_actions": []
        }
        
        # 备份
        backup_path = self.backup_memories()
        report["maintenance_actions"].append(f"备份到: {backup_path}")
        
        # 优化
        if self.optimize_long_term_memory():
            report["maintenance_actions"].append("优化长期记忆")
        
        # 清理旧备份
        deleted = self.cleanup_old_backups()
        report["maintenance_actions"].append(f"清理旧备份: {deleted} 个")
        
        # 保存报告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.base_dir / "meta" / f"maintenance_report_{timestamp}.json"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n维护报告已保存到: {report_file}")
        return report

def main():
    maintenance = MemoryMaintenance()
    
    print("=== 记忆维护和优化系统 ===")
    print(f"运行时间: {datetime.now().isoformat()}")
    
    # 生成维护报告
    report = maintenance.generate_maintenance_report()
    
    # 显示摘要
    print("\n=== 维护摘要 ===")
    print(f"文件数量: {len(report['analysis']['files'])}")
    print(f"总大小: {report['analysis']['total_size']} bytes")
    print(f"完整性问题: {len(report['integrity_check'])} 个")
    print(f"维护操作: {len(report['maintenance_actions'])} 项")
    
    print("\n记忆维护完成！")

if __name__ == "__main__":
    main()
