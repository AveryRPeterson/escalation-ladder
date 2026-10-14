def _clean(intervals):
    out = []
    for iv in intervals:
        s, e = iv
        if s > e:
            raise ValueError(f"start > end: {iv!r}")
        if s < e:
            out.append((s, e))
    return out


def merge(intervals):
    items = sorted(_clean(intervals))
    out = []
    for s, e in items:
        if out and s <= out[-1][1]:
            if e > out[-1][1]:
                out[-1] = (out[-1][0], e)
        else:
            out.append((s, e))
    return out


def subtract(a, b):
    A = merge(a)
    B = merge(b)
    out = []
    for s, e in A:
        cur = s
        for bs, be in B:
            if be <= cur or bs >= e:
                continue
            if bs > cur:
                out.append((cur, bs))
            cur = max(cur, be)
            if cur >= e:
                break
        if cur < e:
            out.append((cur, e))
    return out


def total_length(intervals):
    return sum(e - s for s, e in merge(intervals))


def gaps(intervals, lo, hi):
    if lo > hi:
        raise ValueError("lo > hi")
    if lo == hi:
        merge(intervals)
        return []
    clipped = []
    for s, e in merge(intervals):
        s2, e2 = max(s, lo), min(e, hi)
        if s2 < e2:
            clipped.append((s2, e2))
    return subtract([(lo, hi)], clipped)
