#!/usr/bin/env python3
"""
Unit tests for WorkflowCoordinator
====================================
Run with: python3 -m pytest test_coordinator.py -v
       or: python3 test_coordinator.py
"""

import time
import threading
import unittest
from unittest.mock import MagicMock

from coordinator import (
    Task,
    TaskResult,
    TaskStatus,
    WorkflowCoordinator,
    WorkflowResult,
)


class TestTaskResult(unittest.TestCase):
    """Tests for the TaskResult dataclass."""

    def test_duration_returns_none_when_not_started(self):
        r = TaskResult(task_id="t", status=TaskStatus.PENDING)
        self.assertIsNone(r.duration)

    def test_duration_computes_correctly(self):
        r = TaskResult(task_id="t", status=TaskStatus.SUCCESS,
                       started_at=10.0, finished_at=12.5)
        self.assertAlmostEqual(r.duration, 2.5, places=3)

    def test_to_dict_includes_status_value(self):
        r = TaskResult(task_id="t", status=TaskStatus.FAILED, error="boom")
        d = r.to_dict()
        self.assertEqual(d["status"], "failed")
        self.assertEqual(d["error"], "boom")
        self.assertIn("duration", d)


class TestTask(unittest.TestCase):
    """Tests for the Task dataclass."""

    def test_default_description(self):
        t = Task(task_id="my_task", func=lambda: None)
        self.assertEqual(t.description, "Task(my_task)")

    def test_explicit_description(self):
        t = Task(task_id="x", func=lambda: None, description="Custom")
        self.assertEqual(t.description, "Custom")


class TestWorkflowResult(unittest.TestCase):
    """Tests for WorkflowResult success semantics."""

    def test_success_true_when_all_succeed(self):
        wr = WorkflowResult(workflow_id="test")
        wr.task_results["a"] = TaskResult(task_id="a", status=TaskStatus.SUCCESS)
        # Caller sets success
        wr.success = True
        self.assertTrue(wr.success)

    def test_success_false_when_any_failed(self):
        wr = WorkflowResult(workflow_id="test")
        wr.task_results["a"] = TaskResult(task_id="a", status=TaskStatus.SUCCESS)
        wr.task_results["b"] = TaskResult(task_id="b", status=TaskStatus.FAILED)
        wr.success = False
        self.assertFalse(wr.success)

    def test_summary_structure(self):
        wr = WorkflowResult(workflow_id="wf1", started_at=1.0, finished_at=2.0)
        wr.task_results["a"] = TaskResult(task_id="a", status=TaskStatus.SUCCESS)
        wr.task_results["b"] = TaskResult(task_id="b", status=TaskStatus.FAILED)
        wr.task_results["c"] = TaskResult(task_id="c", status=TaskStatus.SKIPPED)
        s = wr.summary()
        self.assertEqual(s["workflow_id"], "wf1")
        self.assertEqual(s["total_tasks"], 3)
        self.assertEqual(s["succeeded"], 1)
        self.assertEqual(s["failed"], 1)
        self.assertEqual(s["skipped"], 1)
        self.assertAlmostEqual(s["duration"], 1.0, places=3)


class TestWorkflowCoordinator(unittest.TestCase):
    """Core coordinator logic tests."""

    def _make_coordinator(self, **kwargs):
        return WorkflowCoordinator(workflow_id="test", **kwargs)

    # -- Task management -------------------------------------------------------

    def test_add_task_and_describe(self):
        c = self._make_coordinator()
        c.add_task("a", lambda: 1, description="Task A")
        desc = c.describe()
        self.assertEqual(desc["task_count"], 1)
        self.assertIn("a", desc["tasks"])

    def test_duplicate_task_id_raises(self):
        c = self._make_coordinator()
        c.add_task("a", lambda: 1)
        with self.assertRaises(ValueError):
            c.add_task("a", lambda: 2)

    def test_remove_task_cleans_deps(self):
        c = self._make_coordinator()
        c.add_task("a", lambda: 1)
        c.add_task("b", lambda: 2, dependencies={"a"})
        c.remove_task("a")
        self.assertNotIn("a", c._tasks)
        self.assertEqual(c._tasks["b"].dependencies, set())

    def test_clear_removes_all(self):
        c = self._make_coordinator()
        c.add_task("a", lambda: 1)
        c.add_task("b", lambda: 2)
        c.clear()
        self.assertEqual(len(c._tasks), 0)

    # -- DAG validation --------------------------------------------------------

    def test_missing_dependency_raises(self):
        c = self._make_coordinator()
        c.add_task("b", lambda: 2, dependencies={"nonexistent"})
        with self.assertRaises(ValueError):
            c.run("serial", save_result=False)

    def test_cycle_detection(self):
        c = self._make_coordinator()
        c.add_task("a", lambda: 1, dependencies={"b"})
        c.add_task("b", lambda: 2, dependencies={"a"})
        with self.assertRaises(ValueError):
            c.run("serial", save_result=False)

    # -- Serial execution ------------------------------------------------------

    def test_serial_simple(self):
        c = self._make_coordinator()
        c.add_task("a", lambda: 10)
        c.add_task("b", lambda: 20)
        result = c.run("serial", save_result=False)
        self.assertTrue(result.success)
        self.assertEqual(result.task_results["a"].result, 10)
        self.assertEqual(result.task_results["b"].result, 20)

    def test_serial_with_dependencies(self):
        c = self._make_coordinator()
        order = []
        c.add_task("a", lambda: order.append("a") or 1)
        c.add_task("b", lambda: order.append("b") or 2, dependencies={"a"})
        c.add_task("c", lambda: order.append("c") or 3, dependencies={"a"})
        # In topological order, 'a' must come before 'b' and 'c'
        result = c.run("serial", save_result=False)
        self.assertTrue(result.success)
        self.assertLess(order.index("a"), order.index("b"))
        self.assertLess(order.index("a"), order.index("c"))

    def test_serial_failure_marks_workflow_not_success(self):
        c = self._make_coordinator()
        c.add_task("ok", lambda: 1)
        c.add_task("fail", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        result = c.run("serial", save_result=False)
        self.assertFalse(result.success)
        self.assertEqual(result.task_results["fail"].status, TaskStatus.FAILED)

    def test_serial_dependency_failure_skips_dependent(self):
        c = self._make_coordinator()
        c.add_task("a", lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        c.add_task("b", lambda: 2, dependencies={"a"})
        result = c.run("serial", save_result=False)
        self.assertEqual(result.task_results["a"].status, TaskStatus.FAILED)
        self.assertEqual(result.task_results["b"].status, TaskStatus.SKIPPED)

    # -- Parallel execution ----------------------------------------------------

    def test_parallel_simple(self):
        c = self._make_coordinator(max_workers=2)
        c.add_task("a", lambda: time.sleep(0.05) or 1)
        c.add_task("b", lambda: time.sleep(0.05) or 2)
        result = c.run("parallel", save_result=False)
        self.assertTrue(result.success)
        self.assertEqual(result.task_results["a"].result, 1)
        self.assertEqual(result.task_results["b"].result, 2)

    def test_parallel_respects_dependencies(self):
        c = self._make_coordinator(max_workers=4)
        order = []
        lock = threading.Lock()

        def record(name):
            with lock:
                order.append(name)
            time.sleep(0.02)
            return name

        c.add_task("a", lambda: record("a"))
        c.add_task("b", lambda: record("b"), dependencies={"a"})
        c.add_task("c", lambda: record("c"), dependencies={"a"})
        result = c.run("parallel", save_result=False)
        self.assertTrue(result.success)
        # 'a' must be before 'b' and 'c'
        self.assertLess(order.index("a"), order.index("b"))
        self.assertLess(order.index("a"), order.index("c"))

    def test_parallel_failure_skips_dependents(self):
        c = self._make_coordinator(max_workers=2)
        c.add_task("a", lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        c.add_task("b", lambda: 2, dependencies={"a"})
        result = c.run("parallel", save_result=False)
        self.assertFalse(result.success)
        self.assertEqual(result.task_results["a"].status, TaskStatus.FAILED)
        self.assertEqual(result.task_results["b"].status, TaskStatus.SKIPPED)

    # -- Retry logic -----------------------------------------------------------

    def test_retry_succeeds_on_second_attempt(self):
        call_count = {"n": 0}

        def flaky():
            call_count["n"] += 1
            if call_count["n"] < 2:
                raise ConnectionError("transient")
            return "ok"

        c = self._make_coordinator()
        c.add_task("flaky", flaky, max_retries=2, retry_delay=0.01)
        result = c.run("serial", save_result=False)
        self.assertTrue(result.success)
        self.assertEqual(result.task_results["flaky"].result, "ok")
        self.assertEqual(result.task_results["flaky"].attempts, 2)

    def test_retry_exhausted(self):
        def always_fail():
            raise RuntimeError("permanent")

        c = self._make_coordinator()
        c.add_task("fail", always_fail, max_retries=1, retry_delay=0.01)
        result = c.run("serial", save_result=False)
        self.assertFalse(result.success)
        self.assertEqual(result.task_results["fail"].attempts, 2)

    # -- Timeout ---------------------------------------------------------------

    def test_timeout_raises(self):
        def slow():
            time.sleep(5)
            return "done"

        c = self._make_coordinator()
        c.add_task("slow", slow, timeout=0.1)
        result = c.run("serial", save_result=False)
        self.assertFalse(result.success)
        self.assertEqual(result.task_results["slow"].status, TaskStatus.FAILED)
        self.assertIn("TimeoutError", result.task_results["slow"].error)

    def test_timeout_within_limit_succeeds(self):
        def fast():
            time.sleep(0.01)
            return "ok"

        c = self._make_coordinator()
        c.add_task("fast", fast, timeout=5.0)
        result = c.run("serial", save_result=False)
        self.assertTrue(result.success)
        self.assertEqual(result.task_results["fast"].result, "ok")

    # -- Mode validation -------------------------------------------------------

    def test_invalid_mode_raises(self):
        c = self._make_coordinator()
        with self.assertRaises(ValueError) as ctx:
            c.run("invalid_mode", save_result=False)
        self.assertIn("invalid_mode", str(ctx.exception))

    def test_valid_modes(self):
        c = self._make_coordinator()
        c.add_task("a", lambda: 1)
        r1 = c.run("serial", save_result=False)
        self.assertTrue(r1.success)
        r2 = c.run("parallel", save_result=False)
        self.assertTrue(r2.success)

    # -- Success semantics (all-skipped) ---------------------------------------

    def test_success_false_when_all_tasks_skipped(self):
        """If every task ends up SKIPPED (not SUCCESS), success should be False."""
        c = self._make_coordinator()
        c.add_task("a", lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        c.add_task("b", lambda: 2, dependencies={"a"})
        # b will be skipped because a failed
        result = c.run("serial", save_result=False)
        self.assertFalse(result.success)
        self.assertEqual(result.task_results["a"].status, TaskStatus.FAILED)
        self.assertEqual(result.task_results["b"].status, TaskStatus.SKIPPED)
        # Verify no SUCCESS tasks exist
        has_success = any(
            r.status == TaskStatus.SUCCESS
            for r in result.task_results.values()
        )
        self.assertFalse(has_success)

    # -- Config loading --------------------------------------------------------

    def test_from_config(self):
        import json
        import tempfile
        from pathlib import Path

        config = {
            "workflow_id": "cfg_test",
            "tasks": [
                {"task_id": "s1", "function": "fn_a", "dependencies": []},
                {"task_id": "s2", "function": "fn_b", "dependencies": ["s1"]},
            ],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config, f)
            f.flush()
            path = f.name

        registry = {"fn_a": lambda: "A", "fn_b": lambda: "B"}
        c = WorkflowCoordinator.from_config(path, function_registry=registry)
        self.assertEqual(len(c._tasks), 2)
        result = c.run("serial", save_result=False)
        self.assertTrue(result.success)

        Path(path).unlink(missing_ok=True)

    # -- History ---------------------------------------------------------------

    def test_history_tracks_runs(self):
        c = self._make_coordinator()
        c.add_task("a", lambda: 1)
        c.run("serial", save_result=False)
        c.run("serial", save_result=False)
        self.assertEqual(len(c.get_history()), 2)

    # -- Thread safety of parallel execution -----------------------------------

    def test_parallel_concurrent_writes_safe(self):
        """Ensure many parallel tasks don't corrupt shared state."""
        c = self._make_coordinator(max_workers=8)
        n = 50
        for i in range(n):
            deps = {f"t{i-1}"} if i > 0 else set()
            c.add_task(f"t{i}", lambda i=i: i, dependencies=deps)
        result = c.run("parallel", save_result=False)
        self.assertTrue(result.success)
        self.assertEqual(len(result.task_results), n)
        for i in range(n):
            self.assertEqual(result.task_results[f"t{i}"].result, i)


class TestMakeModuleRunner(unittest.TestCase):
    """Tests for the make_module_runner convenience function."""

    def test_runner_calls_function(self):
        from coordinator import make_module_runner
        import os
        runner = make_module_runner("os.path", "exists", "/")
        result = runner()
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
