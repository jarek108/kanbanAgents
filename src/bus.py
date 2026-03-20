from typing import Dict, List, Callable, Type
from events import Event

class EventBus:
    def __init__(self):
        self._listeners: Dict[Type[Event], List[Callable]] = {}

    def subscribe(self, event_type: Type[Event], callback: Callable):
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(callback)

    def emit(self, event: Event):
        event_type = type(event)
        if event_type in self._listeners:
            for callback in self._listeners[event_type]:
                callback(event)
