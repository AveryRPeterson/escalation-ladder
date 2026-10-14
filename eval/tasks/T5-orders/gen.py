"""Generates the T5 input CSVs and the expected report (seeded, deterministic).

Run from this directory:  python gen.py
Writes start/orders.csv, start/refunds.csv, start/rates.csv, hidden_expected.json, reference/report.py
The reference solution here is the single source of truth for the expected numbers.
"""
import csv
import json
import os
import random
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

HERE = os.path.dirname(os.path.abspath(__file__))
rng = random.Random(20261013)

RATES = {
    "EUR": [("2026-01-01", "1.0412"), ("2026-02-15", "1.0855"), ("2026-03-10", "1.0790"), ("2026-04-01", "1.0921")],
    "GBP": [("2026-01-01", "1.2650"), ("2026-03-01", "1.2905"), ("2026-04-15", "1.3010")],
    "JPY": [("2026-01-01", "0.006650"), ("2026-03-20", "0.006710")],
}
OFFSETS = ["-08:00", "-05:00", "+00:00", "+01:00", "+05:30", "+09:00"]


def fmt(dt, off):
    sign = 1 if off[0] == "+" else -1
    h, m = int(off[1:3]), int(off[4:6])
    tz = timezone(sign * timedelta(hours=h, minutes=m))
    return dt.astimezone(tz).isoformat()


def utc(y, mo, d, h=0, mi=0, s=0):
    return datetime(y, mo, d, h, mi, s, tzinfo=timezone.utc)


def amount_for(cur):
    if cur == "JPY":
        return str(rng.randrange(800, 60000, 10))
    return f"{rng.randrange(500, 40000) / 100:.2f}"


orders = []  # (order_id, customer, status, currency, amount, created_at, updated_at)
n = 0


def add(created_utc, off, status="paid", cur=None, amount=None, oid=None):
    global n
    n += 1
    oid = oid or f"O-{n:04d}"
    cur = cur or rng.choice(["USD", "EUR", "GBP", "JPY"])
    amount = amount or amount_for(cur)
    created = fmt(created_utc, off)
    updated = fmt(created_utc + timedelta(minutes=rng.randrange(1, 300)), off)
    row = [oid, f"C{rng.randrange(1, 60):03d}", status, cur, amount, created, updated]
    orders.append(row)
    return row


# deliberate boundary cases
add(utc(2026, 4, 1, 4, 30), "-05:00", cur="USD", amount="10.00")        # local 2026-03-31 23:30 -> UTC April
add(utc(2026, 3, 31, 15, 0), "+09:00", cur="USD", amount="20.00")       # local 2026-04-01 00:00 -> UTC March
add(utc(2026, 2, 14, 15, 30), "+09:00", cur="EUR", amount="100.00")     # UTC Feb 14: old EUR rate
add(utc(2026, 2, 15, 4, 30), "-05:00", cur="EUR", amount="100.00")      # UTC Feb 15: new EUR rate
add(utc(2026, 3, 19, 23, 59, 59), "+00:00", cur="JPY", amount="10000")
add(utc(2026, 3, 20, 0, 0, 0), "+00:00", cur="JPY", amount="10000")
add(utc(2026, 1, 31, 23, 59, 59), "+00:00", cur="GBP", amount="0.01")
add(utc(2026, 2, 1, 0, 0, 0), "+00:00", cur="EUR", amount="0.07")       # half-cent rounding

# bulk
start = utc(2026, 1, 1)
for _ in range(230):
    t = start + timedelta(minutes=rng.randrange(0, 60 * 24 * 150))
    st = rng.choices(["paid", "shipped", "cancelled"], [8, 2, 1])[0]
    add(t, rng.choice(OFFSETS), status=st)

# duplicates: later versions with newer updated_at; file order is shuffled on purpose
dups = []
for row in rng.sample(orders, 45):
    base_created = datetime.fromisoformat(row[5])
    for k in range(rng.choice([1, 2])):
        r = list(row)
        r[6] = (datetime.fromisoformat(row[6]) + timedelta(hours=k + 1)).isoformat()
        change = rng.choice(["status", "amount", "both"])
        if change in ("status", "both"):
            r[2] = rng.choice(["paid", "shipped", "cancelled"])
        if change in ("amount", "both"):
            r[4] = amount_for(r[3])
        dups.append(r)
orders.extend(dups)
rng.shuffle(orders)

# refunds
ids = sorted({r[0] for r in orders})
refunds = []
for i in range(70):
    oid = rng.choice(ids) if i % 12 else f"O-9{i:03d}"  # a few refunds for unknown orders
    cur_row = next((r for r in orders if r[0] == oid), None)
    cur = cur_row[3] if cur_row else "USD"
    amt = str(rng.randrange(100, 4000, 10)) if cur == "JPY" else f"{rng.randrange(100, 3000) / 100:.2f}"
    when = fmt(utc(2026, rng.randrange(1, 6), rng.randrange(1, 28), rng.randrange(0, 24)), rng.choice(OFFSETS))
    refunds.append([f"R-{i + 1:04d}", oid, amt, when])

os.makedirs(os.path.join(HERE, "start"), exist_ok=True)
with open(os.path.join(HERE, "start", "orders.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["order_id", "customer", "status", "currency", "amount", "created_at", "updated_at"])
    w.writerows(orders)
with open(os.path.join(HERE, "start", "refunds.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["refund_id", "order_id", "amount", "refunded_at"])
    w.writerows(refunds)
with open(os.path.join(HERE, "start", "rates.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["currency", "effective_date", "usd_per_unit"])
    for cur, rows in RATES.items():
        for d, r in rows:
            w.writerow([cur, d, r])

REFERENCE = '''import csv
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
'''
os.makedirs(os.path.join(HERE, "reference"), exist_ok=True)
with open(os.path.join(HERE, "reference", "report.py"), "w", newline="\n") as f:
    f.write(REFERENCE)

# run the reference to produce the expected file
import subprocess, sys
subprocess.run([sys.executable, os.path.join(HERE, "reference", "report.py")], cwd=os.path.join(HERE, "start"), check=True)
os.replace(os.path.join(HERE, "start", "report.json"), os.path.join(HERE, "hidden_expected.json"))
print("rows:", len(orders), "refunds:", len(refunds))
print(open(os.path.join(HERE, "hidden_expected.json")).read()[:700])
