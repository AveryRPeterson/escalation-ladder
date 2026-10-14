import threading
import time


class _Flight:
    __slots__ = ("event", "value", "error")

    def __init__(self):
        self.event = threading.Event()
        self.value = None
        self.error = None


class TTLCache:
    def __init__(self, ttl, clock=time.monotonic):
        self.ttl = ttl
        self.clock = clock
        self._data = {}
        self._flights = {}
        self._lock = threading.Lock()

    def get_or_compute(self, key, fn):
        with self._lock:
            hit = self._data.get(key)
            if hit is not None and self.clock() < hit[1]:
                return hit[0]
            flight = self._flights.get(key)
            leader = flight is None
            if leader:
                flight = _Flight()
                self._flights[key] = flight
        if not leader:
            flight.event.wait()
            if flight.error is not None:
                raise flight.error
            return flight.value
        try:
            value = fn()
        except BaseException as e:
            flight.error = e
            with self._lock:
                del self._flights[key]
            flight.event.set()
            raise
        with self._lock:
            self._data[key] = (value, self.clock() + self.ttl)
            del self._flights[key]
        flight.value = value
        flight.event.set()
        return value
