"""
Thread-safe explicit finite state machine for OmniAssist workflow lifecycle.
"""

from __future__ import annotations

import threading
from enum import Enum
from typing import Callable, Dict, Set, List

from logging_service.logger import get_logger

logger = get_logger("app.state_machine")


class AssistantState(str, Enum):
    """Explicit workflow states."""
    IDLE = "IDLE"
    ACTIVATING = "ACTIVATING"
    CAPTURING = "CAPTURING"
    GENERATING = "GENERATING"
    VALIDATING = "VALIDATING"
    READY = "READY"
    DELIVERING = "DELIVERING"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"


class StateTransitionError(Exception):
    """Raised when an illegal state transition is attempted."""
    pass


class AssistantStateMachine:
    """
    Guarantees valid linear state progression with thread synchronization.
    """

    # Permitted transitions table
    VALID_TRANSITIONS: Dict[AssistantState, Set[AssistantState]] = {
        AssistantState.IDLE: {AssistantState.ACTIVATING, AssistantState.CAPTURING, AssistantState.ERROR},
        AssistantState.ACTIVATING: {AssistantState.CAPTURING, AssistantState.IDLE, AssistantState.ERROR},
        AssistantState.CAPTURING: {AssistantState.GENERATING, AssistantState.READY, AssistantState.IDLE, AssistantState.ERROR},
        AssistantState.GENERATING: {AssistantState.VALIDATING, AssistantState.READY, AssistantState.IDLE, AssistantState.ERROR},
        AssistantState.VALIDATING: {AssistantState.READY, AssistantState.ERROR, AssistantState.IDLE},
        AssistantState.READY: {AssistantState.DELIVERING, AssistantState.COMPLETED, AssistantState.IDLE, AssistantState.ERROR},
        AssistantState.DELIVERING: {AssistantState.COMPLETED, AssistantState.READY, AssistantState.IDLE, AssistantState.ERROR},
        AssistantState.COMPLETED: {AssistantState.IDLE, AssistantState.ACTIVATING},
        AssistantState.ERROR: {AssistantState.IDLE, AssistantState.ACTIVATING, AssistantState.READY},
    }

    def __init__(self, initial_state: AssistantState = AssistantState.IDLE) -> None:
        self._current_state = initial_state
        self._lock = threading.RLock()
        self._listeners: List[Callable[[AssistantState, AssistantState], None]] = []

    @property
    def current_state(self) -> AssistantState:
        with self._lock:
            return self._current_state

    def add_listener(self, callback: Callable[[AssistantState, AssistantState], None]) -> None:
        """Registers listener invoked on (old_state, new_state)."""
        with self._lock:
            self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[AssistantState, AssistantState], None]) -> None:
        with self._lock:
            if callback in self._listeners:
                self._listeners.remove(callback)

    def transition_to(self, new_state: AssistantState) -> None:
        """
        Attempts transition to new_state. Enforces transition table rules.
        """
        with self._lock:
            old_state = self._current_state
            if old_state == new_state:
                return

            allowed_targets = self.VALID_TRANSITIONS.get(old_state, set())
            if new_state not in allowed_targets:
                err_msg = f"Illegal state transition from {old_state.value} to {new_state.value}."
                logger.error(err_msg)
                raise StateTransitionError(err_msg)

            self._current_state = new_state
            logger.info("State transition: %s -> %s", old_state.value, new_state.value)

            # Fire listeners
            for listener in list(self._listeners):
                try:
                    listener(old_state, new_state)
                except Exception as exc:
                    logger.warning("State change listener error: %s", exc)

    def reset_to_idle(self) -> None:
        """Safely resets the state machine to IDLE."""
        with self._lock:
            if self._current_state != AssistantState.IDLE:
                self.transition_to(AssistantState.IDLE)
