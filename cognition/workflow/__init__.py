"""
Hermes AGI Workflow Coordination Package
=========================================
Coordinates cognitive modules for the Hermes AI assistant.
"""

from .coordinator import (
    WorkflowCoordinator,
    Task,
    TaskResult,
    TaskStatus,
    WorkflowResult,
    make_module_runner,
)

__all__ = [
    "WorkflowCoordinator",
    "Task",
    "TaskResult",
    "TaskStatus",
    "WorkflowResult",
    "make_module_runner",
]
