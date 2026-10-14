import time
from collections import defaultdict, deque


class SlidingWindowLimiter:
    """Allow at most `limit` events per `window` seconds, per key."""

    def __init__(self, limit, window, clock=time.monotonic):
        self.limit = limit
        self.window = window
        self.clock = clock
        self._events = defaultdict(deque)

    def _expire(self, key, now):
        q = self._events[key]
        while q and now - q[0] > self.window:
            q.popleft()

    def allow(self, key):
        """Record the event and return True if it is within the limit."""
        now = self.clock()
        self._expire(key, now)
        q = self._events[key]
        q.append(now)
        return len(q) <= self.limit

    def retry_after(self, key):
        """Seconds until an event for `key` would be allowed; 0.0 if allowed now."""
        now = self.clock()
        self._expire(key, now)
        q = self._events[key]
        if len(q) < self.limit:
            return 0.0
        return self.window
