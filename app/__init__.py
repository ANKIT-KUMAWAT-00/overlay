"""
Application lifecycle, state machine, and task management subsystem for OmniAssist.
"""

from .state_machine import AssistantStateMachine, AssistantState
from .task_manager import TaskManager
from .lifecycle import LifecycleManager

__all__ = [
    "AssistantStateMachine",
    "AssistantState",
    "TaskManager",
    "LifecycleManager",
]
