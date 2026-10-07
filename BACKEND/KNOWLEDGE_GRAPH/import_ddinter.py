from pathlib import Path
import csv
import json
import re


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).parent

SEED_FILE = BASE_DIR / "data" / "seed_graph.json"
OUTPUT_FILE = BASE_DIR / "data" / "seed_graph_ddinter.json"
DDINTER_DIR = BASE_DIR / "ddinter"


# ============================================================
# DDInter severity mapping
# ============================================================

SEV_MAP = {
    "major": "major",
    "moderate": "moderate",
    "minor": "minor",
    "contraindicated": "major",
}


# ============================================================
# Name normalization
# ============================================================

NAME_MAP = {
    "acetylsalicylic acid": "aspirin",
    "acetaminophen": "paracetamol",
}


def normalize_name(name):
    """
    Normalize DDInter drug names so they can be matched
    against the custom graph and other DDInter records.
    """

    if not name:
        return ""

    name = name.strip().lower()

    # Normalize whitespace
    name = re.sub(r"\s+", " ", name)

    # Normalize known equivalent names
    if name in NAME_MAP:
        return NAME_MAP[name]

    return name


# ============================================================
# Pair key
# ============================================================

def pair_key(a, b):
    """
    Create an order-independent key for a drug-drug pair.
    """

    return tuple(sorted((a, b)))


# ============================================================
# Main importer
# ============================================================

def main():

    # --------------------------------------------------------
    # Load clean custom graph
    # --------------------------------------------------------

    with open(SEED_FILE, "r", encoding="utf-8") as f:
        seed = json.load(f)

    drugs = seed.get("drugs", [])
    interactions = seed.get("interactions", [])

    # --------------------------------------------------------
    # Normalize / protect custom interactions
    # --------------------------------------------------------

    by_pair = {}

    for interaction in interactions:

        a = normalize_name(interaction.get("a", ""))
        b = normalize_name(interaction.get("b", ""))

        interaction["a"] = a
        interaction["b"] = b

        # Mark original custom interactions as curated.
        interaction["source"] = "Custom seed dataset"

        interaction["sources"] = [
            "Custom seed dataset"
        ]

        interaction["details_status"] = "curated"
        interaction["mechanism_verified"] = True

        key = pair_key(a, b)

        by_pair[key] = interaction

    # --------------------------------------------------------
    # Existing drug names
    # --------------------------------------------------------

    existing_drugs = set()

    for drug in drugs:

        generic = normalize_name(
            drug.get("generic", "")
        )

        if generic:
            drug["generic"] = generic
            existing_drugs.add(generic)

    # --------------------------------------------------------
    # Statistics
    # --------------------------------------------------------

    csv_files_read = 0
    total_rows = 0

    new_interactions = 0
    new_drug_nodes = 0

    invalid_rows = 0
    unique_conflicts = 0
    unique_agreements = 0

    conflict_pairs = set()
    agreement_pairs = set()

    ddinter_drugs = set()

    # --------------------------------------------------------
    # Read all DDInter CSV files
    # --------------------------------------------------------

    csv_files = sorted(
        DDINTER_DIR.glob("*.csv")
    )

    for csv_file in csv_files:

        csv_files_read += 1

        print(
            f"Reading: {csv_file.name}"
        )

        with open(
            csv_file,
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as f:

            reader = csv.DictReader(f)

            for row in reader:

                total_rows += 1

                raw_a = row.get(
                    "Drug_A",
                    ""
                )

                raw_b = row.get(
                    "Drug_B",
                    ""
                )

                raw_level = row.get(
                    "Level",
                    ""
                )

                a = normalize_name(raw_a)
                b = normalize_name(raw_b)

                # ------------------------------------------------
                # Ignore malformed rows
                # ------------------------------------------------

                if not a or not b or a == b:
                    invalid_rows += 1
                    continue

                # ------------------------------------------------
                # IMPORTANT:
                # Collect every DDInter drug before severity
                # validation so the complete DDInter catalog
                # is represented.
                # ------------------------------------------------

                ddinter_drugs.add(a)
                ddinter_drugs.add(b)

                # ------------------------------------------------
                # Convert severity
                # ------------------------------------------------

                severity = SEV_MAP.get(
                    raw_level.strip().lower()
                )

                if severity is None:
                    invalid_rows += 1
                    continue

                key = pair_key(a, b)

                # ------------------------------------------------
                # Existing interaction
                # ------------------------------------------------

                if key in by_pair:

                    existing = by_pair[key]

                    # Determine whether this interaction came
                    # from the original curated dataset.
                    is_curated = (
                        existing.get(
                            "details_status"
                        ) == "curated"
                        or existing.get(
                            "mechanism_verified"
                        ) is True
                        or "Custom seed dataset"
                        in existing.get(
                            "sources",
                            []
                        )
                    )

                    # ------------------------------------------------
                    # CURATED interaction
                    # ------------------------------------------------

                    if is_curated:

                        existing_severity = (
                            existing.get(
                                "severity"
                            )
                        )

                        # Compare DDInter severity with the
                        # reviewed custom severity.
                        if existing_severity == severity:

                            if key not in agreement_pairs:
                                agreement_pairs.add(key)
                                unique_agreements += 1

                        else:

                            if key not in conflict_pairs:
                                conflict_pairs.add(key)
                                unique_conflicts += 1

                        # Preserve the custom clinical information.
                        existing.setdefault(
                            "sources",
                            []
                        )

                        if (
                            "Custom seed dataset"
                            not in existing["sources"]
                        ):
                            existing["sources"].insert(
                                0,
                                "Custom seed dataset"
                            )

                        if (
                            "DDInter"
                            not in existing["sources"]
                        ):
                            existing["sources"].append(
                                "DDInter"
                            )

                        existing["source"] = (
                            "Custom seed dataset"
                        )

                        existing[
                            "details_status"
                        ] = "curated"

                        existing[
                            "mechanism_verified"
                        ] = True

                    # ------------------------------------------------
                    # DDInter-only duplicate
                    # ------------------------------------------------

                    else:

                        # Do NOT incorrectly mark this interaction
                        # as coming from the custom seed dataset.
                        #
                        # This fixes the metadata bug where duplicate
                        # DDInter rows were incorrectly receiving:
                        #
                        # ["DDInter", "Custom seed dataset"]

                        if (
                            "DDInter"
                            not in existing.get(
                                "sources",
                                []
                            )
                        ):
                            existing[
                                "sources"
                            ] = ["DDInter"]

                        existing[
                            "source"
                        ] = "DDInter"

                        existing[
                            "details_status"
                        ] = existing.get(
                            "details_status",
                            "ddinter_severity_only"
                        )

                        existing[
                            "mechanism_verified"
                        ] = False

                    continue

                # ------------------------------------------------
                # New DDInter-only interaction
                # ------------------------------------------------

                interaction = {
                    "a": a,
                    "b": b,
                    "type": "drug-drug",
                    "severity": severity,

                    "mechanism": (
                        "Detailed mechanism is not yet "
                        "clinically curated in this dataset; "
                        "DDInter reports an interaction."
                    ),

                    "alternatives": [],
                    "replace": None,

                    "note": (
                        "Severity imported from DDInter. "
                        "Detailed mechanism requires clinical review."
                    ),

                    "source": "DDInter",

                    "sources": [
                        "DDInter"
                    ],

                    "details_status":
                        "ddinter_severity_only",

                    "mechanism_verified":
                        False,
                }

                interactions.append(
                    interaction
                )

                by_pair[key] = interaction

                new_interactions += 1

    # ============================================================
    # Add all missing DDInter drug nodes
    # ============================================================

    for drug_name in sorted(ddinter_drugs):

        if drug_name in existing_drugs:
            continue

        drugs.append(
            {
                "generic": drug_name,
                "atc": None,
                "class": "DDInter catalog",
                "aliases": [],
            }
        )

        existing_drugs.add(drug_name)
        new_drug_nodes += 1

    # ============================================================
    # Build final graph
    # ============================================================

    output = {
        "drugs": drugs,
        "foods": seed.get(
            "foods",
            []
        ),
        "interactions": interactions,
    }

    # ============================================================
    # Write output
    # ============================================================

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            output,
            f,
            indent=2,
            ensure_ascii=False
        )

    # ============================================================
    # Summary
    # ============================================================

    print()
    print("=" * 50)
    print("       DDINTER IMPORT COMPLETE")
    print("=" * 50)

    print(
        f"CSV files read          : {csv_files_read}"
    )

    print(
        f"CSV rows processed      : {total_rows}"
    )

    print(
        f"DDInter drugs found     : {len(ddinter_drugs)}"
    )

    print(
        f"New drug nodes added    : {new_drug_nodes}"
    )

    print(
        f"New interactions        : {new_interactions}"
    )

    print(
        f"Unique conflicts        : {unique_conflicts}"
    )

    print(
        f"Unique agreements       : {unique_agreements}"
    )

    print(
        f"Invalid/skipped rows    : {invalid_rows}"
    )

    print(
        f"Total drugs             : {len(drugs)}"
    )

    print(
        f"Total interactions      : {len(interactions)}"
    )

    print(
        f"Output                  : {OUTPUT_FILE}"
    )

    print("=" * 50)


if __name__ == "__main__":
    main()