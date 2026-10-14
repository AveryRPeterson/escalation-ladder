import csv
import json
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal


def to_utc(s):
    return datetime.fromisoformat(s).astimezone(timezone.utc)


rates = {}
with open("rates.csv", newline="") as f:
    for r in csv.DictReader(f):
        rates.setdefault(r["currency"], []).append((r["effective_date"], Decimal(r["usd_per_unit"])))
for v in rates.values():
    v.sort()


def rate_on(cur, d):
    if cur == "USD":
        return Decimal(1)
    best = None
    for eff, rate in rates[cur]:
        if eff <= d:
            best = rate
    if best is None:
        raise ValueError(f"no rate for {cur} on {d}")
    return best


def cents(amount, rate):
    return int((Decimal(amount) * rate * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP))


kept = {}
with open("orders.csv", newline="") as f:
    for r in csv.DictReader(f):
        key = to_utc(r["updated_at"])
        old = kept.get(r["order_id"])
        if old is None or key >= old[0]:
            kept[r["order_id"]] = (key, r)

report = {}
order_info = {}
for oid, (_, r) in kept.items():
    if r["status"] == "cancelled":
        continue
    created = to_utc(r["created_at"])
    month = created.strftime("%Y-%m")
    d = created.strftime("%Y-%m-%d")
    rate = rate_on(r["currency"], d)
    gross = cents(r["amount"], rate)
    m = report.setdefault(month, {"orders": 0, "gross_cents": 0, "refund_cents": 0, "net_cents": 0})
    m["orders"] += 1
    m["gross_cents"] += gross
    order_info[oid] = (month, r["currency"], rate)

with open("refunds.csv", newline="") as f:
    for r in csv.DictReader(f):
        info = order_info.get(r["order_id"])
        if info is None:
            continue
        month, cur, rate = info
        report[month]["refund_cents"] += cents(r["amount"], rate)

for m in report.values():
    m["net_cents"] = m["gross_cents"] - m["refund_cents"]

with open("report.json", "w") as f:
    json.dump(dict(sorted(report.items())), f, indent=2)
