#!/usr/bin/env python3
"""
Hermes AGI Workflow Coordinator
================================
Coordinates different cognitive modules (memory, metacognition, knowledge graph)
for the Hermes AI assistant AGI evolution project.

Features:
- Serial and parallel task execution
- Task dependency management (DAG-based)
- Error handling with configurable retry
- Execution logging to file
"""

import json
import time
import logging
import threading
import traceback
from enum import Enum
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, List, Optional, Set
from concurrent.futures import ThreadPoolExecutor, as_completed, Future


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


def _get_logger(name: str = "workflow_coordinator") -> logging.Logger:
    """Create a logger that writes to both file and console."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fh = logging.FileHandler(LOG_DIR / f"workflow_{ts}.log", encoding="utf-8")
    fh.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fh.setFormatter(fmt)
    ch.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


@dataclass
class TaskResult:
    """Holds the result of a single task execution."""
    task_id: str
    status: TaskStatus
    result: Any = None
    error: Optional[str] = None
    attempts: int = 0
    started_at: Optional[float] = None
    finished_at: Optional[float] = None

    @property
    def duration(self) -> Optional[float]:
        if self.started_at and self.finished_at:
            return round(self.finished_at - self.started_at, 4)
        return None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        d["duration"] = self.duration
        return d


@dataclass
class Task:
    """Represents a unit of work in a workflow."""
    task_id: str
    func: Callable[..., Any]
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)
    dependencies: Set[str] = field(default_factory=set)
    max_retries: int = 0
    retry_delay: float = 1.0
    timeout: Optional[float] = None
    description: str = ""

    def __post_init__(self):
        if not self.description:
            self.description = f"Task({self.task_id})"


@dataclass
class WorkflowResult:
    """Aggregated result of an entire workflow run."""
    workflow_id: str
    task_results: Dict[str, TaskResult] = field(default_factory=dict)
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    success: bool = True

    @property
    def duration(self) -> Optional[float]:
        if self.started_at and self.finished_at:
            return round(self.finished_at - self.started_at, 4)
        return None

    def summary(self) -> dict:
        return {
            "workflow_id": self.workflow_id,
            "success": self.success,
            "duration": self.duration,
            "total_tasks": len(self.task_results),
            "succeeded": sum(1 for r in self.task_results.values() if r.status == TaskStatus.SUCCESS),
            "failed": sum(1 for r in self.task_results.values() if r.status == TaskStatus.FAILED),
            "skipped": sum(1 for r in self.task_results.values() if r.status == TaskStatus.SKIPPED),
            "tasks": {tid: r.to_dict() for tid, r in self.task_results.items()},
        }

    def save(self, path: Optional[Path] = None):
        """Persist workflow result to a JSON file."""
        if path is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = LOG_DIR / f"result_{self.workflow_id}_{ts}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.summary(), f, indent=2, ensure_ascii=False, default=str)


# ---------------------------------------------------------------------------
# Workflow Coordinator
# ---------------------------------------------------------------------------

class WorkflowCoordinator:
    """
    Coordinates different cognitive modules by managing a directed acyclic
    graph (DAG) of tasks with serial or parallel execution strategies.
    """

    def __init__(self, workflow_id: str = "default", max_workers: int = 4):
        self.workflow_id = workflow_id
        self.max_workers = max_workers
        self._tasks: Dict[str, Task] = {}
        self._registered_functions: Dict[str, Callable] = {}
        self._logger = _get_logger(f"coordinator.{workflow_id}")
        self._history: List[WorkflowResult] = []
        self._logger.info("WorkflowCoordinator '%s' initialized (max_workers=%d)", workflow_id, max_workers)

    # ------------------------------------------------------------------
    # Task management
    # ------------------------------------------------------------------

    def register_function(self, name: str, func: Callable):
        """Register a reusable function by name."""
        self._registered_functions[name] = func
        self._logger.debug("Registered function: %s", name)

    def add_task(
        self,
        task_id: str,
        func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        dependencies: Set[str] = None,
        max_retries: int = 0,
        retry_delay: float = 1.0,
        timeout: Optional[float] = None,
        description: str = "",
    ) -> "WorkflowCoordinator":
        """Add a task to the workflow. Returns self for chaining."""
        if task_id in self._tasks:
            raise ValueError(f"Duplicate task_id: '{task_id}'")

        task = Task(
            task_id=task_id,
            func=func,
            args=args,
            kwargs=kwargs or {},
            dependencies=dependencies or set(),
            max_retries=max_retries,
            retry_delay=retry_delay,
            timeout=timeout,
            description=description or task_id,
        )
        self._tasks[task_id] = task
        self._logger.debug("Added task '%s' (deps=%s)", task_id, task.dependencies)
        return self

    def remove_task(self, task_id: str):
        """Remove a task and clean up dependencies referencing it."""
        self._tasks.pop(task_id, None)
        for t in self._tasks.values():
            t.dependencies.discard(task_id)
        self._logger.debug("Removed task '%s'", task_id)

    def clear(self):
        """Remove all tasks."""
        self._tasks.clear()
        self._logger.debug("All tasks cleared")

    # ------------------------------------------------------------------
    # DAG validation
    # ------------------------------------------------------------------

    def _validate_dag(self):
        """Ensure no missing deps and no cycles."""
        ids = set(self._tasks.keys())
        # Check missing dependencies
        for t in self._tasks.values():
            missing = t.dependencies - ids
            if missing:
                raise ValueError(f"Task '{t.task_id}' has unknown dependencies: {missing}")
        # Topological sort to detect cycles
        visited: Set[str] = set()
        in_stack: Set[str] = set()

        def _dfs(node: str):
            if node in in_stack:
                raise ValueError(f"Cycle detected involving task '{node}'")
            if node in visited:
                return
            in_stack.add(node)
            for dep in self._tasks[node].dependencies:
                _dfs(dep)
            in_stack.discard(node)
            visited.add(node)

        for tid in self._tasks:
            _dfs(tid)

    def _topological_order(self) -> List[str]:
        """Return tasks in a valid topological order."""
        in_degree: Dict[str, int] = {tid: 0 for tid in self._tasks}
        dependents: Dict[str, List[str]] = {tid: [] for tid in self._tasks}
        for tid, task in self._tasks.items():
            for dep in task.dependencies:
                dependents[dep].append(tid)
                in_degree[tid] += 1

        queue = [tid for tid, deg in in_degree.items() if deg == 0]
        order = []
        while queue:
            node = queue.pop(0)
            order.append(node)
            for child in dependents[node]:
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)
        return order

    # ------------------------------------------------------------------
    # Execution helpers
    # ------------------------------------------------------------------

    def _execute_task(
        self,
        task: Task,
        results: Dict[str, TaskResult],
        lock: Optional[threading.Lock] = None,
    ) -> TaskResult:
        """Execute a single task with retry logic and optional timeout.

        Args:
            task: The task to execute.
            results: Shared dict of completed task results (may be written by
                other threads).  When *lock* is provided reads are serialised.
            lock: Optional lock that guards *results* when running in parallel.
        """

        # -- Thread-safe dependency check ------------------------------------
        def _read_dep(dep_id: str) -> Optional[TaskResult]:
            if lock is not None:
                with lock:
                    return results.get(dep_id)
            return results.get(dep_id)

        for dep_id in task.dependencies:
            dep_result = _read_dep(dep_id)
            if dep_result and dep_result.status != TaskStatus.SUCCESS:
                return TaskResult(
                    task_id=task.task_id,
                    status=TaskStatus.SKIPPED,
                    error=f"Dependency '{dep_id}' did not succeed (status={dep_result.status.value})",
                )

        result = TaskResult(task_id=task.task_id, status=TaskStatus.RUNNING)
        attempt = 0
        max_attempts = task.max_retries + 1

        while attempt < max_attempts:
            attempt += 1
            result.attempts = attempt
            result.started_at = time.time()
            result.status = TaskStatus.RUNNING

            if attempt > 1:
                self._logger.info(
                    "Retrying task '%s' (attempt %d/%d)", task.task_id, attempt, max_attempts
                )
                result.status = TaskStatus.RETRYING
                time.sleep(task.retry_delay)

            try:
                self._logger.info("Executing task '%s' (attempt %d)", task.task_id, attempt)
                # -- Honour task.timeout if set ----------------------------
                if task.timeout is not None:
                    _result_box: list = [None]
                    _error_box: list = [None]

                    def _target():
                        try:
                            _result_box[0] = task.func(*task.args, **task.kwargs)
                        except Exception as _exc:
                            _error_box[0] = _exc

                    worker = threading.Thread(target=_target, daemon=True)
                    worker.start()
                    worker.join(timeout=task.timeout)
                    if worker.is_alive():
                        raise TimeoutError(
                            f"Task '{task.task_id}' exceeded timeout of {task.timeout}s"
                        )
                    if _error_box[0] is not None:
                        raise _error_box[0]
                    output = _result_box[0]
                else:
                    output = task.func(*task.args, **task.kwargs)
                result.result = output
                result.status = TaskStatus.SUCCESS
                result.finished_at = time.time()
                self._logger.info(
                    "Task '%s' completed in %.3fs", task.task_id, result.duration or 0
                )
                return result
            except Exception as exc:
                result.error = f"{type(exc).__name__}: {exc}"
                result.finished_at = time.time()
                self._logger.warning(
                    "Task '%s' failed on attempt %d: %s",
                    task.task_id, attempt, result.error,
                )
                if attempt >= max_attempts:
                    result.status = TaskStatus.FAILED
                    self._logger.error(
                        "Task '%s' permanently failed after %d attempts: %s",
                        task.task_id, attempt, result.error,
                    )

        return result

    # ------------------------------------------------------------------
    # Run strategies
    # ------------------------------------------------------------------

    def run_serial(self, save_result: bool = True) -> WorkflowResult:
        """Execute all tasks in topological (serial) order."""
        self._validate_dag()
        order = self._topological_order()
        self._logger.info("Starting SERIAL workflow '%s' with %d tasks", self.workflow_id, len(order))
        self._logger.info("Execution order: %s", " -> ".join(order))

        wf_result = WorkflowResult(workflow_id=self.workflow_id, started_at=time.time())

        for tid in order:
            task = self._tasks[tid]
            task_result = self._execute_task(task, wf_result.task_results)
            wf_result.task_results[tid] = task_result
            if task_result.status == TaskStatus.FAILED:
                wf_result.success = False

        # Fix success semantics: at least one task must have actually succeeded
        wf_result.success = (
            wf_result.success
            and any(r.status == TaskStatus.SUCCESS for r in wf_result.task_results.values())
        )

        wf_result.finished_at = time.time()
        self._logger.info(
            "Serial workflow '%s' finished in %.3fs (success=%s)",
            self.workflow_id, wf_result.duration, wf_result.success,
        )
        self._history.append(wf_result)
        if save_result:
            wf_result.save()
        return wf_result

    def run_parallel(self, save_result: bool = True) -> WorkflowResult:
        """
        Execute tasks respecting dependencies, running independent tasks
        in parallel via a thread pool.  Uses ``as_completed`` to avoid
        busy-wait polling and a ``threading.Lock`` to protect the shared
        *results* dictionary from concurrent writes.
        """
        self._validate_dag()
        self._logger.info(
            "Starting PARALLEL workflow '%s' with %d tasks", self.workflow_id, len(self._tasks)
        )

        wf_result = WorkflowResult(workflow_id=self.workflow_id, started_at=time.time())
        results = wf_result.task_results
        lock = threading.Lock()

        # Track which tasks are done
        done_tasks: Set[str] = set()
        futures: Dict[str, Future] = {}

        def _all_deps_met(task: Task) -> bool:
            # Caller must already hold *lock*
            return task.dependencies.issubset(done_tasks)

        def _submit_ready(executor: ThreadPoolExecutor):
            """Submit all tasks whose dependencies are satisfied."""
            with lock:
                ready = [
                    (tid, task)
                    for tid, task in self._tasks.items()
                    if tid not in done_tasks and tid not in futures and _all_deps_met(task)
                ]
            for tid, task in ready:
                fut = executor.submit(self._execute_task, task, results, lock)
                futures[tid] = fut

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Initial submission
            _submit_ready(executor)

            while futures:
                # Block until at least one future completes (no busy-wait)
                done_iter = as_completed(futures.values())
                fut = next(done_iter)

                # Find the task id for this future
                tid = next(t for t, f in futures.items() if f is fut)
                del futures[tid]

                task_result = fut.result()
                with lock:
                    results[tid] = task_result
                    done_tasks.add(tid)
                    if task_result.status == TaskStatus.FAILED:
                        wf_result.success = False

                self._logger.debug(
                    "Task '%s' finished with status=%s", tid, task_result.status.value
                )

                # Submit newly eligible tasks
                _submit_ready(executor)

        # Skip any tasks still not done (e.g. unreachable due to failures)
        with lock:
            for tid in self._tasks:
                if tid not in done_tasks:
                    results[tid] = TaskResult(
                        task_id=tid,
                        status=TaskStatus.SKIPPED,
                        error="Workflow incomplete; skipping",
                    )
                    done_tasks.add(tid)

        # Fix success semantics: at least one task must have actually succeeded
        wf_result.success = (
            wf_result.success
            and any(r.status == TaskStatus.SUCCESS for r in results.values())
        )

        wf_result.finished_at = time.time()
        self._logger.info(
            "Parallel workflow '%s' finished in %.3fs (success=%s)",
            self.workflow_id, wf_result.duration, wf_result.success,
        )
        self._history.append(wf_result)
        if save_result:
            wf_result.save()
        return wf_result

    def run(self, mode: str = "serial", save_result: bool = True) -> WorkflowResult:
        """
        Convenience entry point. mode: 'serial' or 'parallel'.
        """
        valid_modes = ("serial", "parallel")
        if mode not in valid_modes:
            raise ValueError(f"Invalid mode '{mode}'. Must be one of {valid_modes}")
        if mode == "parallel":
            return self.run_parallel(save_result=save_result)
        return self.run_serial(save_result=save_result)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def get_history(self) -> List[dict]:
        """Return summary dicts for all past workflow runs."""
        return [wr.summary() for wr in self._history]

    def describe(self) -> dict:
        """Return a human-readable description of the current workflow DAG."""
        self._validate_dag()
        return {
            "workflow_id": self.workflow_id,
            "max_workers": self.max_workers,
            "task_count": len(self._tasks),
            "tasks": {
                tid: {
                    "description": t.description,
                    "dependencies": sorted(t.dependencies),
                    "max_retries": t.max_retries,
                }
                for tid, t in self._tasks.items()
            },
            "execution_order": self._topological_order(),
        }

    # ------------------------------------------------------------------
    # JSON config loader
    # ------------------------------------------------------------------

    @classmethod
    def from_config(
        cls,
        config_path: str,
        function_registry: Dict[str, Callable] = None,
        max_workers: int = 4,
    ) -> "WorkflowCoordinator":
        """
        Create a coordinator from a JSON config file.

        Example config:
        {
            "workflow_id": "daily_cognition",
            "tasks": [
                {
                    "task_id": "load_memory",
                    "function": "memory.load",
                    "args": [],
                    "kwargs": {},
                    "dependencies": [],
                    "max_retries": 2
                },
                {
                    "task_id": "update_graph",
                    "function": "knowledge.update",
                    "args": [],
                    "kwargs": {},
                    "dependencies": ["load_memory"],
                    "max_retries": 1
                }
            ]
        }
        """
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        registry = function_registry or {}
        wf_id = config.get("workflow_id", "config_workflow")
        workers = config.get("max_workers", max_workers)

        coordinator = cls(workflow_id=wf_id, max_workers=workers)

        for task_cfg in config.get("tasks", []):
            func_name = task_cfg["function"]
            if func_name not in registry:
                raise ValueError(
                    f"Function '{func_name}' not found in registry. "
                    f"Available: {list(registry.keys())}"
                )
            coordinator.add_task(
                task_id=task_cfg["task_id"],
                func=registry[func_name],
                args=tuple(task_cfg.get("args", [])),
                kwargs=task_cfg.get("kwargs", {}),
                dependencies=set(task_cfg.get("dependencies", [])),
                max_retries=task_cfg.get("max_retries", 0),
                retry_delay=task_cfg.get("retry_delay", 1.0),
                description=task_cfg.get("description", ""),
            )

        return coordinator


# ---------------------------------------------------------------------------
# Convenience: built-in cognitive module wrappers
# ---------------------------------------------------------------------------

def make_module_runner(module_name: str, method: str, *args, **kwargs) -> Callable:
    """
    Factory that returns a callable which imports and calls
    `module_name.method(*args, **kwargs)` at execution time.
    Useful for lazy-loading cognitive modules.
    """
    def _runner():
        import importlib
        mod = importlib.import_module(module_name)
        fn = getattr(mod, method)
        return fn(*args, **kwargs)
    _runner.__name__ = f"{module_name}.{method}"
    return _runner


# ---------------------------------------------------------------------------
# Quick demo / self-test
# ---------------------------------------------------------------------------

def _demo():
    """Demonstrate coordinator capabilities."""
    print("=" * 60)
    print("  WorkflowCoordinator Demo")
    print("=" * 60)

    coordinator = WorkflowCoordinator(workflow_id="demo", max_workers=3)

    # Define some mock cognitive tasks
    def init_memory():
        time.sleep(0.1)
        return {"status": "memory initialized", "records": 42}

    def load_knowledge_graph():
        time.sleep(0.15)
        return {"status": "graph loaded", "nodes": 128, "edges": 356}

    def run_metacognition():
        time.sleep(0.05)
        return {"status": "metacognition check passed", "confidence": 0.92}

    def analyze_context(memory_data=None, graph_data=None):
        time.sleep(0.1)
        return {
            "status": "analysis complete",
            "memory_ref": memory_data,
            "graph_ref": graph_data,
        }

    def generate_report(analysis=None):
        time.sleep(0.05)
        return {"status": "report generated", "pages": 3}

    def flaky_task():
        """Fails first time, succeeds on retry."""
        if not hasattr(flaky_task, "called"):
            flaky_task.called = True
            raise ConnectionError("Transient network error")
        return {"status": "recovered"}

    # Build DAG:
    #   init_memory ──┐
    #                 ├──> analyze_context ──> generate_report
    #   load_kg ──────┘
    #
    #   run_metacognition (independent)
    #   flaky_task (independent, with retry)

    coordinator.add_task("init_memory", init_memory, description="Initialize memory system")
    coordinator.add_task("load_kg", load_knowledge_graph, description="Load knowledge graph")
    coordinator.add_task("metacognition", run_metacognition, description="Run metacognition check")
    coordinator.add_task(
        "analyze",
        analyze_context,
        kwargs={"memory_data": "mem_ref", "graph_data": "graph_ref"},
        dependencies={"init_memory", "load_kg"},
        description="Analyze combined context",
    )
    coordinator.add_task(
        "report",
        generate_report,
        dependencies={"analyze"},
        description="Generate final report",
    )
    coordinator.add_task(
        "flaky",
        flaky_task,
        max_retries=2,
        retry_delay=0.05,
        description="Task with transient failure",
    )

    # Show DAG description
    desc = coordinator.describe()
    print("\nWorkflow structure:")
    print(json.dumps(desc, indent=2))

    # Run serial
    print("\n--- SERIAL execution ---")
    result = coordinator.run("serial")
    print(json.dumps(result.summary(), indent=2, default=str))

    # Reset flaky for parallel run
    if hasattr(flaky_task, "called"):
        delattr(flaky_task, "called")

    # Run parallel
    coordinator.clear()
    coordinator.add_task("init_memory", init_memory)
    coordinator.add_task("load_kg", load_knowledge_graph)
    coordinator.add_task("metacognition", run_metacognition)
    coordinator.add_task(
        "analyze", analyze_context,
        kwargs={"memory_data": "mem_ref", "graph_data": "graph_ref"},
        dependencies={"init_memory", "load_kg"},
    )
    coordinator.add_task("report", generate_report, dependencies={"analyze"})
    coordinator.add_task("flaky", flaky_task, max_retries=2, retry_delay=0.05)

    print("\n--- PARALLEL execution ---")
    result = coordinator.run("parallel")
    print(json.dumps(result.summary(), indent=2, default=str))

    # Test config-based loading
    config = {
        "workflow_id": "from_config",
        "tasks": [
            {"task_id": "step1", "function": "task_a", "dependencies": []},
            {"task_id": "step2", "function": "task_b", "dependencies": ["step1"]},
        ],
    }
    config_path = Path(__file__).parent / "demo_config.json"
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    registry = {"task_a": lambda: "A done", "task_b": lambda: "B done"}
    coord2 = WorkflowCoordinator.from_config(str(config_path), function_registry=registry)
    print("\n--- CONFIG-BASED execution ---")
    print(json.dumps(coord2.describe(), indent=2))
    r2 = coord2.run("serial")
    print(json.dumps(r2.summary(), indent=2, default=str))

    # Cleanup demo config
    config_path.unlink(missing_ok=True)

    print("\n✓ All demos completed. Check logs/ for detailed execution logs.")


if __name__ == "__main__":
    _demo()
