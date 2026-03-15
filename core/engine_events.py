import threading

_listeners = {}
_lock = threading.Lock()

def subscribe(event_type, callback):
    """Register a callback for a specific event type."""
    with _lock:
        if event_type not in _listeners:
            _listeners[event_type] = []
        if callback not in _listeners[event_type]:
            _listeners[event_type].append(callback)

def unsubscribe(event_type, callback):
    """Remove a callback."""
    with _lock:
        if event_type in _listeners and callback in _listeners[event_type]:
            _listeners[event_type].remove(callback)

def emit(event_type, data=None):
    """Trigger all callbacks for an event type."""
    with _lock:
        if event_type not in _listeners:
            return
        callbacks = list(_listeners[event_type])
    
    for callback in callbacks:
        try:
            callback(data)
        except Exception as e:
            print(f"EventBus Error ({event_type}): {e}")
