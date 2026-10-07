import json

path = "data/seed_graph.json"

targets = {
    frozenset(("amlodipine", "atorvastatin")),
    frozenset(("amlodipine", "rosuvastatin")),
    frozenset(("amlodipine", "grapefruit")),
}

with open(path, encoding="utf-8") as f:
    data = json.load(f)

before = len(data["interactions"])

data["interactions"] = [
    interaction
    for interaction in data["interactions"]
    if frozenset((
        interaction["a"].lower(),
        interaction["b"].lower()
    )) not in targets
]

removed = before - len(data["interactions"])

with open(path, "w", encoding="utf-8") as f:
    json.dump(
        data,
        f,
        indent=2,
        ensure_ascii=False
    )

print(f"Removed: {removed}")
print(f"Remaining interactions: {len(data['interactions'])}")