"""Event-Driven State Dispatcher."""
from typing import Callable, List, Dict

class StateDispatcher:
    def __init__(self):
        self._listeners: Dict[str, List[Callable[[], None]]] = {}

    def subscribe(self, state: str, callback: Callable[[], None]):
        self._listeners.setdefault(state, []).append(callback)

    def transition_to(self, new_state: str):
        for cb in self._listeners.get(new_state, []):
            cb()
