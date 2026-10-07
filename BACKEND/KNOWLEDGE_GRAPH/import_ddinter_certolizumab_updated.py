import csv
import json
import glob
from pathlib import Path


# =========================================================
# FILES
# =========================================================

SEED = Path("data/seed_graph.json")
OUTPUT = Path("data/seed_graph_ddinter.json")

FILES = glob.glob("ddinter/*.csv")

COL_A = "Drug_A"
COL_B = "Drug_B"
COL_LEVEL = "Level"


# =========================================================
# DDINTER NAMES -> CANONICAL NAMES
# =========================================================

NAME_FIX = {
    "acetylsalicylic acid": "aspirin",
    "acetaminophen": "paracetamol",
}


# =========================================================
# DDINTER SEVERITY -> OUR SEVERITY
# =========================================================

SEV_MAP = {
    "major": "major",
    "moderate": "moderate",
    "minor": "minor",
    "contraindicated": "contraindicated",
}


# =========================================================
# MEDICALLY REVIEWED SEVERITY CONFLICTS
# =========================================================

# =========================================================
# DDINTER CLINICAL DETAIL OVERRIDES
# =========================================================
#
# Targeted first implementation:
# certolizumab pegol + dimethyl fumarate
#
# DDInter classifies this interaction as Major / Synergy and
# reports increased infection risk from combining TNF blockade
# with another immunosuppressive or myelosuppressive agent.
# =========================================================

DDINTER_DETAILS = {
    frozenset(("certolizumab pegol", "dimethyl fumarate")): {
        "mechanism": (
            "Both drugs can suppress immune function. "
            "Combining certolizumab pegol, a TNF blocker, "
            "with dimethyl fumarate may increase immunosuppression "
            "and the risk of infections, including serious infections "
            "and sepsis."
        ),
        "note": (
            "Patients receiving this combination should be monitored "
            "closely for signs and symptoms of infection. "
            "If a serious infection or sepsis occurs, TNF-blocker "
            "therapy should be discontinued according to DDInter guidance."
        ),
        "alternatives": [],
    },
}


REVIEWED_SEVERITIES = {
    frozenset(("aspirin", "ibuprofen")): {
        "custom_dataset": "moderate",
        "ddinter": "major",
        "final_reviewed": "moderate",
    },

    frozenset(("amlodipine", "simvastatin")): {
        "custom_dataset": "moderate",
        "ddinter": "major",
        "final_reviewed": "major",
    },

    frozenset(("warfarin", "celecoxib")): {
        "custom_dataset": "major",
        "ddinter": "moderate",
        "final_reviewed": "major",
    },

    frozenset(("clopidogrel", "ibuprofen")): {
        "custom_dataset": "major",
        "ddinter": "moderate",
        "final_reviewed": "moderate",
    },

    frozenset(("clopidogrel", "diclofenac")): {
        "custom_dataset": "major",
        "ddinter": "moderate",
        "final_reviewed": "moderate",
    },

    frozenset(("clopidogrel", "naproxen")): {
        "custom_dataset": "major",
        "ddinter": "moderate",
        "final_reviewed": "moderate",
    },
}


# =========================================================
# CHECK DDINTER FILES
# =========================================================

if not FILES:
    raise SystemExit(
        "ERROR: No CSV files found in the 'ddinter' folder."
    )


# =========================================================
# LOAD CLEAN VERIFIED CUSTOM DATASET
# =========================================================

with SEED.open(encoding="utf-8") as f:
    seed = json.load(f)


# =========================================================
# CUSTOM DRUG INDEX
#
# Important:
# We preserve all existing custom drug metadata.
# =========================================================

custom_drugs = {
    d["generic"].strip().lower(): d
    for d in seed["drugs"]
}


# =========================================================
# ALL DRUGS SEEN IN DDINTER
#
# This will eventually contain ~1,939 unique drugs.
# =========================================================

ddinter_drugs = set()


# =========================================================
# MARK ALL ORIGINAL CUSTOM INTERACTIONS AS CURATED
# =========================================================

for interaction in seed["interactions"]:

    interaction.setdefault("sources", [])

    if "Custom seed dataset" not in interaction["sources"]:
        interaction["sources"].append(
            "Custom seed dataset"
        )

    interaction["details_status"] = "curated"
    interaction["mechanism_verified"] = True


# =========================================================
# INDEX EXISTING CUSTOM DRUG-DRUG INTERACTIONS
# =========================================================

by_pair = {
    frozenset(
        (
            e["a"].lower(),
            e["b"].lower(),
        )
    ): e

    for e in seed["interactions"]

    if e["type"] == "drug-drug"
}


# =========================================================
# COUNTERS
# =========================================================

added_interactions = 0
added_drugs = 0

invalid_rows = 0

conflict_pairs = set()
agreement_pairs = set()


# =========================================================
# PROCESS DDINTER CSV FILES
# =========================================================

for path in FILES:

    print(f"Reading: {path}")

    with open(
        path,
        newline="",
        encoding="utf-8-sig",
    ) as fh:

        reader = csv.DictReader(fh)

        required = {
            COL_A,
            COL_B,
            COL_LEVEL,
        }

        if not required.issubset(
            reader.fieldnames or []
        ):
            raise SystemExit(
                f"ERROR: {path} does not contain the expected columns.\n"
                f"Found: {reader.fieldnames}\n"
                f"Expected: {required}"
            )

        for row in reader:

            raw_a = row[COL_A].strip()
            raw_b = row[COL_B].strip()
            raw_level = row[COL_LEVEL].strip().lower()

            # -------------------------------------------------
            # BASIC VALIDATION
            # -------------------------------------------------

            if not raw_a or not raw_b:
                invalid_rows += 1
                continue

            # -------------------------------------------------
            # NORMALIZE NAMES
            # -------------------------------------------------

            a = NAME_FIX.get(
                raw_a.lower(),
                raw_a.lower(),
            )

            b = NAME_FIX.get(
                raw_b.lower(),
                raw_b.lower(),
            )

            # -------------------------------------------------
            # RECORD DRUGS SEEN IN DDINTER
            #
            # Do this BEFORE severity validation so that drugs
            # appearing in unknown-severity rows are still
            # included in the DDInter drug catalog.
            # -------------------------------------------------

            ddinter_drugs.add(a)
            ddinter_drugs.add(b)

            # -------------------------------------------------
            # NORMALIZE SEVERITY
            # -------------------------------------------------

            severity = SEV_MAP.get(raw_level)

            if severity is None:
                invalid_rows += 1
                continue

            # -------------------------------------------------
            # SELF INTERACTION
            # -------------------------------------------------

            if a == b:
                invalid_rows += 1
                continue

            # -------------------------------------------------
            # NORMALIZED PAIR
            # -------------------------------------------------

            key = frozenset((a, b))

            # =================================================
            # EXISTING INTERACTION
            # =================================================

            if key in by_pair:

                existing = by_pair[key]

                # -------------------------------------------------
                # DETERMINE WHETHER THIS IS A CURATED INTERACTION
                # OR A DDINTER-ONLY INTERACTION ALREADY ADDED.
                # -------------------------------------------------

                is_curated = (
                    existing.get("details_status")
                    == "curated"

                    or existing.get("mechanism_verified")
                    is True

                    or "Custom seed dataset"
                    in existing.get("sources", [])
                )

                # =================================================
                # EXISTING CURATED CUSTOM INTERACTION
                # =================================================

                if is_curated:

                    custom_severity = existing["severity"]

                    existing.setdefault(
                        "sources",
                        [],
                    )

                    # -------------------------------------------------
                    # Preserve custom provenance
                    # -------------------------------------------------

                    if (
                        "Custom seed dataset"
                        not in existing["sources"]
                    ):
                        existing["sources"].append(
                            "Custom seed dataset"
                        )

                    # -------------------------------------------------
                    # Add DDInter as supporting source
                    # -------------------------------------------------

                    if (
                        "DDInter"
                        not in existing["sources"]
                    ):
                        existing["sources"].append(
                            "DDInter"
                        )

                    # -------------------------------------------------
                    # AGREEMENT
                    # -------------------------------------------------

                    if custom_severity == severity:

                        agreement_pairs.add(key)

                        # Keep curated mechanism.
                        # Keep curated alternatives.
                        # Keep curated note.
                        # Keep curated severity.

                        existing["details_status"] = (
                            "curated"
                        )

                        existing["mechanism_verified"] = True

                        continue

                    # -------------------------------------------------
                    # SEVERITY CONFLICT
                    # -------------------------------------------------

                    conflict_pairs.add(key)

                    # -------------------------------------------------
                    # REVIEWED CONFLICT
                    # -------------------------------------------------

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
                            ),
                        }

                        existing["details_status"] = (
                            "curated"
                        )

                        existing["mechanism_verified"] = True

                        existing.pop(
                            "severity_conflict",
                            None,
                        )

                    # -------------------------------------------------
                    # UNREVIEWED CONFLICT
                    # -------------------------------------------------

                    else:

                        existing[
                            "severity_conflict"
                        ] = {
                            "custom_dataset": (
                                custom_severity
                            ),
                            "DDInter": (
                                severity
                            ),
                            "status": (
                                "needs_review"
                            ),
                        }

                        existing[
                            "details_status"
                        ] = "needs_review"

                        existing[
                            "mechanism_verified"
                        ] = False

                    continue

                # =================================================
                # EXISTING DDINTER-ONLY INTERACTION
                # =================================================

                else:

                    # This is simply another DDInter row for the
                    # same pair.
                    #
                    # IMPORTANT:
                    # Do NOT add Custom seed dataset.
                    # Do NOT change mechanism.
                    # Do NOT mark as curated.
                    # Do NOT change details_status.

                    if (
                        "DDInter"
                        not in existing.get(
                            "sources",
                            [],
                        )
                    ):

                        existing.setdefault(
                            "sources",
                            [],
                        )

                        existing[
                            "sources"
                        ].append(
                            "DDInter"
                        )

                    continue

            # =================================================
            # NEW DDINTER-ONLY INTERACTION
            # =================================================

            details = DDINTER_DETAILS.get(key)

            edge = {

                "a": a,

                "b": b,

                "type": "drug-drug",

                "severity": severity,

                "mechanism": (
                    details["mechanism"]
                    if details
                    else (
                        "Interaction detected by DDInter. "
                        "Detailed mechanism has not been clinically "
                        "curated in this dataset."
                    )
                ),

                "alternatives": (
                    details["alternatives"]
                    if details
                    else []
                ),

                "replace": None,

                "note": (
                    details["note"]
                    if details
                    else (
                        "Severity imported from DDInter. "
                        "Detailed mechanism requires clinical review."
                    )
                ),

                "source": "DDInter",

                "sources": [
                    "DDInter"
                ],

                "details_status": (
                    "ddinter_severity_only"
                ),

                "mechanism_verified": False,
            }

            seed["interactions"].append(edge)

            by_pair[key] = edge

            added_interactions += 1


# =========================================================
# ADD MISSING DDINTER DRUG NODES
# =========================================================

existing_drug_names = {
    d["generic"].strip().lower()
    for d in seed["drugs"]
}


for drug_name in sorted(ddinter_drugs):

    # Already present in the curated catalog.
    if drug_name in existing_drug_names:
        continue

    # ---------------------------------------------------------
    # Minimal DDInter catalog node.
    #
    # We intentionally do NOT invent:
    #   - ATC code
    #   - drug class
    #   - aliases
    #
    # because the DDInter CSV files do not provide those fields.
    # ---------------------------------------------------------

    seed["drugs"].append(
        {
            "generic": drug_name,
            "atc": None,
            "class": "DDInter catalog",
            "aliases": [],
        }
    )

    existing_drug_names.add(drug_name)

    added_drugs += 1


# =========================================================
# CHECK FOR UNREVIEWED CONFLICTS
# =========================================================

unreviewed_conflicts = [
    key
    for key in conflict_pairs
    if key not in REVIEWED_SEVERITIES
]


if unreviewed_conflicts:

    print()

    print(
        "WARNING: Unreviewed severity conflicts found:"
    )

    for key in sorted(
        unreviewed_conflicts,
        key=lambda x: tuple(sorted(x)),
    ):

        print(
            "  - "
            + " + ".join(
                sorted(key)
            )
        )

    print()


# =========================================================
# SAVE NEW DATASET
# =========================================================

with OUTPUT.open(
    "w",
    encoding="utf-8",
) as f:

    json.dump(
        seed,
        f,
        indent=2,
        ensure_ascii=False,
    )


# =========================================================
# SUMMARY
# =========================================================

print()

print(
    "========== DDInter IMPORT =========="
)

print(
    f"CSV files read          : {len(FILES)}"
)

print(
    f"DDInter drugs found     : {len(ddinter_drugs)}"
)

print(
    f"New drug nodes added    : {added_drugs}"
)

print(
    f"New interactions        : {added_interactions}"
)

print(
    f"Unique conflicts        : {len(conflict_pairs)}"
)

print(
    f"Unique agreements       : {len(agreement_pairs)}"
)

print(
    f"Invalid/skipped rows    : {invalid_rows}"
)

print(
    f"Total drugs             : {len(seed['drugs'])}"
)

print(
    f"Total interactions      : {len(seed['interactions'])}"
)

print(
    f"Output                  : {OUTPUT}"
)

print(
    "===================================="
)