"""The EventBus — a tiny pub/sub message board.

Every component in the engine talks through the bus. This keeps the
market-data feed, the execution engine, the risk manager, and any
dashboards you write from having to know about each other directly.
"""
from collections import defaultdict


class EventBus:
    def __init__(self):
        self.subscribers = defaultdict(list)

    def subscribe(self, event_type, handler):
        self.subscribers[event_type].append(handler)

    def publish(self, event):
        for handler in self.subscribers.get(event.event_type, []):
            handler(event)
