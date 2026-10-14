import re

_SECS = {"w": 604800, "d": 86400, "h": 3600, "m": 60, "s": 1}
_ORDER = ["w", "d", "h", "m", "s"]
_TOKEN = re.compile(r"\s*(\d+(?:\.\d+)?)\s*([wdhmsWDHMS])")


def parse_duration(text):
    if not isinstance(text, str):
        raise ValueError("not a string")
    s = text.strip()
    if s == "":
        raise ValueError("empty")
    if s == "0":
        return 0.0
    pos = 0
    last = -1
    total = 0.0
    nums = []
    while pos < len(s):
        m = _TOKEN.match(s, pos)
        if not m:
            raise ValueError(f"bad duration near {s[pos:]!r}")
        num, unit = m.group(1), m.group(2).lower()
        rank = _ORDER.index(unit)
        if rank <= last:
            raise ValueError("units out of order or repeated")
        last = rank
        nums.append(num)
        total += float(num) * _SECS[unit]
        pos = m.end()
    if any("." in n for n in nums[:-1]):
        raise ValueError("only the last component may be fractional")
    return float(total)
