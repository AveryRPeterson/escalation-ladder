import time


class TTLCache:
    """Caches the result of an expensive function per key for `ttl` seconds."""

    def __init__(self, ttl, clock=time.monotonic):
        self.ttl = ttl
        self.clock = clock
        self._data = {}

    def get_or_compute(self, key, fn):
        hit = self._data.get(key)
        if hit is not None and self.clock() - hit[1] < self.ttl:
            return hit[0]
        value = fn()
        self._data[key] = (value, self.clock())
        return value
