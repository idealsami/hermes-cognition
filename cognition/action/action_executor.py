"""
动作执行器 - 执行具体任务并监控结果
"""
import json
import os
import subprocess
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum

BJT = timezone(timedelta(hours=8))


class ActionType(Enum):
    """动作类型"""
    TERMINAL = "terminal"      # 终端命令
    FILE = "file"              # 文件操作
    WEB = "web"                # 网络请求
    COGNITION = "cognition"    # 认知操作
    DELEGATE = "delegate"      # 委派给subagent
    COMPOSITE = "composite"    # 组合动作
    WAIT = "wait"              # 等待条件


class ActionResult:
    """动作执行结果"""
    def __init__(self, success: bool, output: Any = None, error: str = "",
                 duration_ms: int = 0, metadata: Optional[Dict] = None):
        self.success = success
        self.output = output
        self.error = error
        self.duration_ms = duration_ms
        self.metadata = metadata or {}

    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata
        }


class ActionExecutor:
    """动作执行器 - 执行各种类型的任务"""

    def __init__(self, log_dir: str = "/root/.hermes/cognition/action"):
        self.log_dir = log_dir
        self.execution_log = os.path.join(log_dir, "execution_log.jsonl")
        self.handlers: Dict[str, Callable] = {
            "terminal": self._execute_terminal,
            "file": self._execute_file,
            "web": self._execute_web,
            "cognition": self._execute_cognition,
            "delegate": self._execute_delegate,
            "composite": self._execute_composite,
            "wait": self._execute_wait,
        }
        # 自定义动作注册表
        self.custom_actions: Dict[str, Callable] = {}

    def register_action(self, action_name: str, handler: Callable):
        """注册自定义动作处理器"""
        self.custom_actions[action_name] = handler

    def execute(self, action_type: str, params: Dict, context: Optional[Dict] = None) -> ActionResult:
        """执行动作"""
        start_time = time.time()

        try:
            # 检查是否有自定义处理器
            action_key = params.get('action', '')
            if action_key in self.custom_actions:
                result = self.custom_actions[action_key](params, context)
            elif action_type in self.handlers:
                result = self.handlers[action_type](params, context or {})
            else:
                result = ActionResult(False, error=f"Unknown action type: {action_type}")

            duration = int((time.time() - start_time) * 1000)
            result.duration_ms = duration

        except Exception as e:
            duration = int((time.time() - start_time) * 1000)
            result = ActionResult(False, error=str(e), duration_ms=duration)

        # 记录执行日志
        self._log_execution(action_type, params, result)

        return result

    def _execute_terminal(self, params: Dict, context: Dict) -> ActionResult:
        """执行终端命令"""
        command = params.get('command', '')
        if not command:
            return ActionResult(False, error="No command specified")

        timeout = params.get('timeout', 300)
        workdir = params.get('workdir', '/root')

        try:
            proc = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                timeout=timeout, cwd=workdir
            )
            return ActionResult(
                success=proc.returncode == 0,
                output={
                    "stdout": proc.stdout[-5000:] if proc.stdout else "",
                    "stderr": proc.stderr[-2000:] if proc.stderr else "",
                    "returncode": proc.returncode
                },
                error=proc.stderr[-2000:] if proc.returncode != 0 else ""
            )
        except subprocess.TimeoutExpired:
            return ActionResult(False, error=f"Command timed out after {timeout}s")
        except Exception as e:
            return ActionResult(False, error=str(e))

    def _execute_file(self, params: Dict, context: Dict) -> ActionResult:
        """执行文件操作"""
        action = params.get('action', 'read')
        path = params.get('path', '')

        try:
            if action == 'read':
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return ActionResult(True, output={"content": content[:10000]})

            elif action == 'write':
                content = params.get('content', '')
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return ActionResult(True, output={"bytes_written": len(content)})

            elif action == 'append':
                content = params.get('content', '')
                with open(path, 'a', encoding='utf-8') as f:
                    f.write(content)
                return ActionResult(True, output={"bytes_appended": len(content)})

            elif action == 'exists':
                return ActionResult(True, output={"exists": os.path.exists(path)})

            elif action == 'list':
                if os.path.isdir(path):
                    items = os.listdir(path)
                    return ActionResult(True, output={"items": items[:100]})
                return ActionResult(False, error=f"Not a directory: {path}")

            else:
                return ActionResult(False, error=f"Unknown file action: {action}")

        except Exception as e:
            return ActionResult(False, error=str(e))

    def _execute_web(self, params: Dict, context: Dict) -> ActionResult:
        """执行网络操作"""
        action = params.get('action', 'fetch')
        url = params.get('url', '')

        try:
            import urllib.request
            import urllib.parse

            if action == 'fetch':
                if not url:
                    return ActionResult(False, error="No URL specified")
                req = urllib.request.Request(url, headers=params.get('headers', {}))
                with urllib.request.urlopen(req, timeout=params.get('timeout', 30)) as resp:
                    data = resp.read().decode('utf-8', errors='replace')
                    return ActionResult(True, output={"data": data[:50000], "status": resp.status})

            elif action == 'search':
                # 模拟搜索（实际使用时会调用web_search工具）
                query = params.get('query', '')
                return ActionResult(True, output={"query": query, "note": "search_simulated"})

            else:
                return ActionResult(False, error=f"Unknown web action: {action}")

        except Exception as e:
            return ActionResult(False, error=str(e))

    def _execute_cognition(self, params: Dict, context: Dict) -> ActionResult:
        """执行认知操作"""
        action = params.get('action', 'analyze')

        # 认知操作通常需要LLM参与，这里记录意图
        # 实际执行时由AutonomousActionSystem调用相应认知模块
        return ActionResult(
            True,
            output={
                "cognition_action": action,
                "params": params,
                "context": context,
                "note": "cognition_action_registered"
            }
        )

    def _execute_delegate(self, params: Dict, context: Dict) -> ActionResult:
        """委派给subagent"""
        task_description = params.get('task', '')
        toolsets = params.get('toolsets', ['terminal', 'file', 'web'])

        return ActionResult(
            True,
            output={
                "delegate_task": task_description,
                "toolsets": toolsets,
                "note": "delegation_registered"
            }
        )

    def _execute_composite(self, params: Dict, context: Dict) -> ActionResult:
        """执行组合动作"""
        sub_actions = params.get('actions', [])
        results = []

        for sub in sub_actions:
            sub_type = sub.get('action_type', 'terminal')
            sub_params = sub.get('params', {})
            result = self.execute(sub_type, sub_params, context)
            results.append(result.to_dict())

            # 如果某个子动作失败且标记为必须，整体失败
            if not result.success and sub.get('required', False):
                return ActionResult(False, output={"partial_results": results},
                                    error=f"Required sub-action failed: {result.error}")

        return ActionResult(True, output={"results": results})

    def _execute_wait(self, params: Dict, context: Dict) -> ActionResult:
        """等待条件满足"""
        wait_seconds = params.get('seconds', 1)
        condition = params.get('condition', '')

        if wait_seconds > 0:
            time.sleep(min(wait_seconds, 60))  # 最多等60秒

        return ActionResult(True, output={"waited_seconds": wait_seconds, "condition": condition})

    def _log_execution(self, action_type: str, params: Dict, result: ActionResult):
        """记录执行日志"""
        os.makedirs(self.log_dir, exist_ok=True)
        entry = {
            "timestamp": datetime.now(BJT).isoformat(),
            "action_type": action_type,
            "params": {k: v for k, v in params.items() if k != 'content'},  # 不记录大内容
            "success": result.success,
            "duration_ms": result.duration_ms,
            "error": result.error[:500] if result.error else None
        }
        with open(self.execution_log, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def get_execution_stats(self) -> Dict:
        """获取执行统计"""
        if not os.path.exists(self.execution_log):
            return {"total": 0}

        stats = {"total": 0, "success": 0, "failed": 0, "by_type": {}}
        try:
            with open(self.execution_log, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        entry = json.loads(line)
                        stats["total"] += 1
                        if entry.get("success"):
                            stats["success"] += 1
                        else:
                            stats["failed"] += 1
                        at = entry.get("action_type", "unknown")
                        stats["by_type"][at] = stats["by_type"].get(at, 0) + 1
        except Exception:
            pass

        return stats
