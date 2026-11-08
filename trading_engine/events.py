"""Events — the messages that flow through your engine.

Every meaningful thing that happens (a price tick, an order submission,
a fill, a cancel) is emitted as an Event object and picked up by any
component that has subscribed to that event's type.
"""

from datetime import datetime


class Event:
    """Base class for every event on the bus.

    Attributes:
        event_type: string tag (e.g. 'MARKET_DATA', 'ORDER_FILLED')
        timestamp:  when the event happened (defaults to now)
        data:       dict of arbitrary extra fields
    """

    def __init__(self, event_type, data=None, timestamp=None):
        self.event_type = event_type
        self.data = data if data is not None else {}
        self.timestamp = timestamp if timestamp is not None else datetime.now()


        

class MarketDataEvent(Event):
    """A new price tick arrived for a symbol.

    TODO (Step 3): call super().__init__(event_type='MARKET_DATA', data=data,
    timestamp=timestamp).
    """

    def __init__(self, data=None, timestamp=None):
        super().__init__(
            event_type="MARKET_DATA",
            data=data,
            timestamp=timestamp
        )


class OrderSubmittedEvent(Event):
    """An order was accepted by the engine and added to the book.

    TODO (Step 3): event_type='ORDER_SUBMITTED'.
    """

    def __init__(self, data=None, timestamp=None):
        super().__init__(
            event_type="ORDER_SUBMITTED",
            data=data,
            timestamp=timestamp
        )


class OrderFilledEvent(Event):
    """One or more orders were matched — a trade happened.

    TODO (Step 3): event_type='ORDER_FILLED'.
    """

    def __init__(self, data=None, timestamp=None):
        super().__init__(
            event_type="ORDER_FILLED",
            data=data,
            timestamp=timestamp
        )


class OrderCancelledEvent(Event):
    """An order was rejected or cancelled before filling fully.

    TODO (Step 3): event_type='ORDER_CANCELLED'.
    """

    def __init__(self, data=None, timestamp=None):
        super().__init__(
            event_type="ORDER_CANCELLED",
            data=data,
            timestamp=timestamp
        )
