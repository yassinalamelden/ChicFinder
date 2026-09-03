"""
scripts/(C)_coverage_report.py
================================
Reusable brand x gender coverage report over data/metadata.jsonl.
Per ChicFinder-Master-Plan.md Sec 6.1: "Build the coverage report first ...
the report itself is a paper table" -- and it should run after every
scrape/removal pass so drift is visible, not silent.

Usage:
  python scripts/(C)_coverage_report.py
"""

import json
import sys
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

METADATA_JSONL = "data/metadata.jsonl"


def main():
    brand_counts = Counter()
    gender_counts = Counter()
    brand_gender = defaultdict(Counter)
    total = 0

    with open(METADATA_JSONL, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            brand = rec.get("source") or rec.get("brand") or "UNKNOWN"
            gender = rec.get("gender") or "UNKNOWN"
            brand_counts[brand] += 1
            gender_counts[gender] += 1
            brand_gender[brand][gender] += 1
            total += 1

    print(f"TOTAL records: {total}\n")

    print("=== Overall gender distribution ===")
    for g, c in gender_counts.most_common():
        print(f"{g:12s} {c:6d} ({100*c/total:.1f}%)")

    print("\n=== Per-brand totals ===")
    for b, c in brand_counts.most_common():
        flag = "  <-- over 20% cap" if c / total > 0.20 else ""
        print(f"{b:15s} {c:6d} ({100*c/total:.1f}%){flag}")

    print("\n=== Per-brand x gender breakdown ===")
    for b, c in brand_counts.most_common():
        row = brand_gender[b]
        parts = ", ".join(f"{g}={row[g]}" for g in sorted(row, key=lambda x: -row[x]))
        print(f"{b:15s} total={c:6d}  {parts}")


if __name__ == "__main__":
    main()
