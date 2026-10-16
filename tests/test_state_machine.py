"""
Unit tests for finite state machine lifecycle and transition rules.
"""

import pytest
from app.state_machine import AssistantStateMachine, AssistantState, StateTransitionError


def test_initial_state():
    sm = AssistantStateMachine()
    assert sm.current_state == AssistantState.IDLE


def test_valid_linear_lifecycle():
    sm = AssistantStateMachine()
    
    # IDLE -> ACTIVATING
    sm.transition_to(AssistantState.ACTIVATING)
    assert sm.current_state == AssistantState.ACTIVATING

    # ACTIVATING -> CAPTURING
    sm.transition_to(AssistantState.CAPTURING)
    assert sm.current_state == AssistantState.CAPTURING

    # CAPTURING -> GENERATING
    sm.transition_to(AssistantState.GENERATING)
    assert sm.current_state == AssistantState.GENERATING

    # GENERATING -> VALIDATING
    sm.transition_to(AssistantState.VALIDATING)
    assert sm.current_state == AssistantState.VALIDATING

    # VALIDATING -> READY
    sm.transition_to(AssistantState.READY)
    assert sm.current_state == AssistantState.READY

    # READY -> DELIVERING
    sm.transition_to(AssistantState.DELIVERING)
    assert sm.current_state == AssistantState.DELIVERING

    # DELIVERING -> COMPLETED
    sm.transition_to(AssistantState.COMPLETED)
    assert sm.current_state == AssistantState.COMPLETED

    # COMPLETED -> IDLE
    sm.transition_to(AssistantState.IDLE)
    assert sm.current_state == AssistantState.IDLE


def test_illegal_state_transition_raises():
    sm = AssistantStateMachine()
    # Cannot jump directly from IDLE to DELIVERING
    with pytest.raises(StateTransitionError):
        sm.transition_to(AssistantState.DELIVERING)


def test_state_change_listeners():
    sm = AssistantStateMachine()
    events = []

    def listener(old_state, new_state):
        events.append((old_state, new_state))

    sm.add_listener(listener)
    sm.transition_to(AssistantState.ACTIVATING)
    sm.transition_to(AssistantState.CAPTURING)

    assert len(events) == 2
    assert events[0] == (AssistantState.IDLE, AssistantState.ACTIVATING)
    assert events[1] == (AssistantState.ACTIVATING, AssistantState.CAPTURING)


def test_reset_to_idle():
    sm = AssistantStateMachine(initial_state=AssistantState.GENERATING)
    sm.reset_to_idle()
    assert sm.current_state == AssistantState.IDLE
