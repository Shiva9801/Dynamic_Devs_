import csv
import glob
from collections import defaultdict

files = glob.glob("ddinter/*.csv")

drugs = set()
pairs = set()
rows = 0

severity_by_pair = defaultdict(set)

for file in files:
    with open(file, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            rows += 1

            a = row["Drug_A"].strip().lower()
            b = row["Drug_B"].strip().lower()
            severity = row["Level"].strip().lower()

            drugs.add(a)
            drugs.add(b)

            # Normalize pair direction
            pair = tuple(sorted((a, b)))

            pairs.add(pair)
            severity_by_pair[pair].add(severity)

duplicate_rows = rows - len(pairs)

conflicts = {
    pair: levels
    for pair, levels in severity_by_pair.items()
    if len(levels) > 1
}

print("CSV files:", len(files))
print("Total CSV rows:", rows)
print("Unique drugs:", len(drugs))
print("Unique drug pairs:", len(pairs))
print("Duplicate rows:", duplicate_rows)
print("Severity conflicts:", len(conflicts))

print("\nSeverity distribution:")
severity_count = defaultdict(int)

for pair, levels in severity_by_pair.items():
    for level in levels:
        severity_count[level] += 1

for level, count in sorted(severity_count.items()):
    print(f"{level}: {count}")

print("\nFirst 20 severity conflicts:")

for pair, levels in list(conflicts.items())[:20]:
    print(pair, "->", levels)