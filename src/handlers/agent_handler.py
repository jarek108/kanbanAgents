from bus import EventBus
from events import StartCoding, WorkCompleted

class AgentHandler:
    def __init__(self, bus: EventBus):
        self.bus = bus
        self.bus.subscribe(StartCoding, self.on_start)

    def on_start(self, event: StartCoding):
        print(f"Agent starting for task: {event.context.get('id')}")
        # Placeholder for actual agent logic
        print("Agent work in progress...")
        self.bus.emit(WorkCompleted(diff=None))
