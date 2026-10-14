import time
from collections import defaultdict, deque


class SlidingWindowLimiter:
    def __init__(self, limit, window, clock=time.monotonic):
        self.limit = limit
        self.window = window
        self.clock = clock
        self._events = defaultdict(deque)

    def _expire(self, key, now):
        q = self._events[key]
        while q and now - q[0] >= self.window:
            q.popleft()

    def allow(self, key):
        now = self.clock()
        self._expire(key, now)
        q = self._events[key]
        if len(q) >= self.limit:
            return False
        q.append(now)
        return True

    def retry_after(self, key):
        now = self.clock()
        self._expire(key, now)
        q = self._events[key]
        if len(q) < self.limit:
            return 0.0
        return q[0] + self.window - now
