from collections import OrderedDict


def _pos_int(n):
    return isinstance(n, int) and not isinstance(n, bool) and n > 0


class WeightedLRU:
    def __init__(self, capacity):
        if not _pos_int(capacity):
            raise ValueError("capacity must be a positive int")
        self.capacity = capacity
        self._d = OrderedDict()
        self._total = 0

    def put(self, key, value, weight=1):
        if not _pos_int(weight):
            raise ValueError("weight must be a positive int")
        if weight > self.capacity:
            return False
        if key in self._d:
            self._total -= self._d.pop(key)[1]
        self._d[key] = (value, weight)
        self._total += weight
        while self._total > self.capacity:
            k = next(iter(self._d))
            self._total -= self._d.pop(k)[1]
        return True

    def get(self, key, default=None):
        if key not in self._d:
            return default
        self._d.move_to_end(key)
        return self._d[key][0]

    def peek(self, key, default=None):
        if key not in self._d:
            return default
        return self._d[key][0]

    def __contains__(self, key):
        return key in self._d

    def __len__(self):
        return len(self._d)

    def total_weight(self):
        return self._total

    def keys(self):
        return list(self._d.keys())
