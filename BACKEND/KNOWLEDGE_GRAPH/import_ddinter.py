import csv
import json
import glob

SEED = "data/seed_graph.json"
OUTPUT = "data/seed_graph_ddinter.json"

FILES = glob.glob("ddinter/*.csv")

COL_A = "Drug_A"
COL_B = "Drug_B"
COL_LEVEL = "Level"

# DDInter names → your canonical names
NAME_FIX = {
    "acetylsalicylic acid": "aspirin",
    "acetaminophen": "paracetamol",
}

SEV_MAP = {
    "major": "major",
    "moderate": "moderate",
    "minor": "minor",
    "contraindicated": "contraindicated",
}


# ---------------------------------------------------------
# MEDICALLY REVIEWED SEVERITY CONFLICTS
# ---------------------------------------------------------

REVIEWED_SEVERITIES = {
    frozenset(("aspirin", "ibuprofen")): {
        "custom_dataset": "moderate",
        "ddinter": "major",
        "final_reviewed": "moderate"
    },

    frozenset(("amlodipine", "simvastatin")): {
        "custom_dataset": "moderate",
        "ddinter": "major",
        "final_reviewed": "major"
    },

    frozenset(("warfarin", "celecoxib")): {
        "custom_dataset": "major",
        "ddinter": "moderate",
        "final_reviewed": "major"
    },

    frozenset(("clopidogrel", "ibuprofen")): {
        "custom_dataset": "major",
        "ddinter": "moderate",
        "final_reviewed": "moderate"
    },

    frozenset(("clopidogrel", "diclofenac")): {
        "custom_dataset": "major",
        "ddinter": "moderate",
        "final_reviewed": "moderate"
    },

    frozenset(("clopidogrel", "naproxen")): {
        "custom_dataset": "major",
        "ddinter": "moderate",
        "final_reviewed": "moderate"
    },
}


if not FILES:
    raise SystemExit(
        "ERROR: No CSV files found in the 'ddinter' folder."
    )


# ---------------------------------------------------------
# LOAD VERIFIED CUSTOM DATASET
# ---------------------------------------------------------

with open(SEED, encoding="utf-8") as f:
    seed = json.load(f)

known = {
    d["generic"].strip().lower()
    for d in seed["drugs"]
}

# All original custom interactions are medically reviewed.
for interaction in seed["interactions"]:
    interaction.setdefault("sources", [])

    if "Custom seed dataset" not in interaction["sources"]:
        interaction["sources"].append("Custom seed dataset")

    interaction["details_status"] = "curated"
    interaction["mechanism_verified"] = True


# ---------------------------------------------------------
# INDEX EXISTING DRUG-DRUG INTERACTIONS
# ---------------------------------------------------------

by_pair = {
    frozenset((e["a"].lower(), e["b"].lower())): e
    for e in seed["interactions"]
    if e["type"] == "drug-drug"
}


added = 0
skipped_unknown = 0
skipped_invalid = 0

conflict_pairs = set()
agreement_pairs = set()


# ---------------------------------------------------------
# PROCESS DDINTER CSV FILES
# ---------------------------------------------------------

for path in FILES:

    print(f"Reading: {path}")

    with open(
        path,
        newline="",
        encoding="utf-8-sig"
    ) as fh:

        reader = csv.DictReader(fh)

        required = {
            COL_A,
            COL_B,
            COL_LEVEL
        }

        if not required.issubset(reader.fieldnames or []):
            raise SystemExit(
                f"ERROR: {path} does not contain the expected columns.\n"
                f"Found: {reader.fieldnames}\n"
                f"Expected: {required}"
            )

        for row in reader:

            raw_a = row[COL_A].strip()
            raw_b = row[COL_B].strip()
            raw_level = row[COL_LEVEL].strip().lower()

            if not raw_a or not raw_b:
                skipped_invalid += 1
                continue

            a = NAME_FIX.get(
                raw_a.lower(),
                raw_a.lower()
            )

            b = NAME_FIX.get(
                raw_b.lower(),
                raw_b.lower()
            )

            severity = SEV_MAP.get(raw_level)

            if severity is None:
                skipped_invalid += 1
                continue

            if a not in known or b not in known:
                skipped_unknown += 1
                continue

            if a == b:
                skipped_invalid += 1
                continue

            key = frozenset((a, b))


            # -------------------------------------------------
            # EXISTING CUSTOM INTERACTION
            # -------------------------------------------------

            if key in by_pair:

                existing = by_pair[key]
                custom_severity = existing["severity"]

                existing.setdefault("sources", [])

                if "Custom seed dataset" not in existing["sources"]:
                    existing["sources"].append("Custom seed dataset")

                if "DDInter" not in existing["sources"]:
                    existing["sources"].append("DDInter")


                # ---------------------------------------------
                # AGREEMENT
                # ---------------------------------------------

                if custom_severity == severity:

                    agreement_pairs.add(key)

                    existing.setdefault(
                        "details_status",
                        "curated"
                    )

                    existing.setdefault(
                        "mechanism_verified",
                        True
                    )

                    continue


                # ---------------------------------------------
                # CONFLICT
                # ---------------------------------------------

                conflict_pairs.add(key)

                if key in REVIEWED_SEVERITIES:

                    review = REVIEWED_SEVERITIES[key]

                    existing["severity"] = (
                        review["final_reviewed"]
                    )

                    existing["evidence"] = {
                        "custom_dataset": (
                            review["custom_dataset"]
                        ),
                        "ddinter": (
                            review["ddinter"]
                        ),
                        "final_reviewed": (
                            review["final_reviewed"]
                        )
                    }

                    existing["details_status"] = "curated"
                    existing["mechanism_verified"] = True

                    existing.pop(
                        "severity_conflict",
                        None
                    )

                else:

                    existing["severity_conflict"] = {
                        "custom_dataset": custom_severity,
                        "DDInter": severity,
                        "status": "needs_review"
                    }

                    existing["details_status"] = "needs_review"
                    existing["mechanism_verified"] = False

                continue


            # -------------------------------------------------
            # NEW DDINTER-ONLY INTERACTION
            # -------------------------------------------------

            edge = {
                "a": a,
                "b": b,
                "type": "drug-drug",
                "severity": severity,

                "mechanism": (
                    "Detailed mechanism is not yet curated "
                    "in this dataset; DDInter reports an interaction."
                ),

                "alternatives": [],
                "replace": None,

                "note": (
                    "Severity imported from DDInter. "
                    "Detailed mechanism requires clinical review."
                ),

                "source": "DDInter",
                "sources": ["DDInter"],

                "details_status": "ddinter_severity_only",
                "mechanism_verified": False
            }

            seed["interactions"].append(edge)

            by_pair[key] = edge

            added += 1


# ---------------------------------------------------------
# CHECK FOR UNREVIEWED CONFLICTS
# ---------------------------------------------------------

unreviewed_conflicts = [
    key
    for key in conflict_pairs
    if key not in REVIEWED_SEVERITIES
]

if unreviewed_conflicts:

    print()
    print("WARNING: Unreviewed severity conflicts found:")

    for key in sorted(
        unreviewed_conflicts,
        key=lambda x: tuple(sorted(x))
    ):
        print(
            "  - "
            + " + ".join(sorted(key))
        )

    print()


# ---------------------------------------------------------
# SAVE NEW DATASET
# ---------------------------------------------------------

with open(
    OUTPUT,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        seed,
        f,
        indent=2,
        ensure_ascii=False
    )


# ---------------------------------------------------------
# SUMMARY
# ---------------------------------------------------------

print()
print("========== DDInter IMPORT ==========")
print(f"CSV files read          : {len(FILES)}")
print(f"New interactions        : {added}")
print(f"Unique conflicts        : {len(conflict_pairs)}")
print(f"Unique agreements       : {len(agreement_pairs)}")
print(f"Unknown-drug rows       : {skipped_unknown}")
print(f"Invalid/skipped rows    : {skipped_invalid}")
print(f"Total interactions      : {len(seed['interactions'])}")
print(f"Output                  : {OUTPUT}")
print("====================================")