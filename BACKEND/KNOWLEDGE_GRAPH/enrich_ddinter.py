"""
enrich_ddinter.py

Enrich DDInter-only interactions in data/seed_graph_ddinter.json
with mechanism descriptions from the normalized DDInter 2.0 knowledge base.

IMPORTANT:
- Custom curated interactions are never overwritten.
- DDInter severity is never changed here.
- No management/alternative text is invented.
- If DDInter has no mechanism text for a pair, the existing
  severity-only explanation is preserved.

Expected DDInter knowledge-base file:
    ddinter/ddi_knowledge_base.json

Source structure:
    {
        "mechanisms": {
            "34": {
                "text": "...",
                "categories": ["..."]
            }
        },
        "drugs": [
            {"id": "DDInter1", "name": "Abacavir", ...}
        ],
        "interactions": [
            ["DDInter1089", "DDInter1479", "Major", "34"]
        ]
    }
"""

import json
from pathlib import Path


# =========================================================
# FILES
# =========================================================

BASE_DIR = Path(__file__).parent

GRAPH_FILE = (
    BASE_DIR
    / "data"
    / "seed_graph_ddinter.json"
)

KB_FILE = (
    BASE_DIR
    / "ddinter"
    / "ddi_knowledge_base.json"
)


# =========================================================
# NAME NORMALIZATION
# =========================================================

# Keep normalization aligned with import_ddinter.py.

NAME_MAP = {
    "acetylsalicylic acid": "aspirin",
    "acetaminophen": "paracetamol",
}


def normalize_name(name):
    """
    Convert a DDInter drug name into the canonical name
    used by our graph.
    """

    name = str(name).strip().lower()

    return NAME_MAP.get(
        name,
        name
    )


# =========================================================
# JSON LOADER
# =========================================================

def load_json(path):
    """
    Load a UTF-8 JSON file.
    """

    with path.open(
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


# =========================================================
# BUILD DDINTER MECHANISM INDEX
# =========================================================

def build_ddinter_pair_index(kb):
    """
    Build a lookup like:

        frozenset(
            (
                normalized_drug_a,
                normalized_drug_b
            )
        )

        ->
        {
            "mechanism": str | None,
            "categories": list[str],
            "ddinter_ids": [...]
        }

    The DDInter interaction table may contain repeated rows
    for the same normalized drug pair.

    Therefore:

    - retain the first non-empty mechanism
    - merge mechanism categories
    """

    # -----------------------------------------------------
    # DDINTER DRUG ID -> NORMALIZED DRUG NAME
    # -----------------------------------------------------

    drugs_by_id = {
        str(drug["id"]): normalize_name(
            drug["name"]
        )

        for drug in kb.get(
            "drugs",
            []
        )

        if drug.get("id")
        and drug.get("name")
    }

    # -----------------------------------------------------
    # MECHANISM RECORDS
    # -----------------------------------------------------

    mechanisms = kb.get(
        "mechanisms",
        {}
    )

    # -----------------------------------------------------
    # FINAL PAIR INDEX
    # -----------------------------------------------------

    pair_index = {}

    # -----------------------------------------------------
    # PROCESS DDINTER INTERACTIONS
    # -----------------------------------------------------

    for row in kb.get(
        "interactions",
        []
    ):

        # Expected:
        #
        # [
        #     drug_a_id,
        #     drug_b_id,
        #     severity,
        #     mechanism_group_id
        # ]

        if len(row) < 4:
            continue

        (
            drug_a_id,
            drug_b_id,
            severity,
            group_id
        ) = row[:4]

        # -------------------------------------------------
        # RESOLVE DRUG IDS
        # -------------------------------------------------

        a = drugs_by_id.get(
            str(drug_a_id)
        )

        b = drugs_by_id.get(
            str(drug_b_id)
        )

        if not a or not b:
            continue

        # Ignore self-interactions.

        if a == b:
            continue

        # -------------------------------------------------
        # CANONICAL PAIR
        # -------------------------------------------------

        key = frozenset(
            (
                a,
                b
            )
        )

        # -------------------------------------------------
        # GET MECHANISM
        # -------------------------------------------------

        mechanism_record = mechanisms.get(
            str(group_id),
            {}
        )

        mechanism_text = (
            mechanism_record.get(
                "text"
            )
        )

        categories = (
            mechanism_record.get(
                "categories"
            )
            or []
        )

        # -------------------------------------------------
        # FIRST OCCURRENCE
        # -------------------------------------------------

        existing = pair_index.get(
            key
        )

        if existing is None:

            pair_index[key] = {
                "mechanism": mechanism_text,

                "categories": list(
                    dict.fromkeys(
                        categories
                    )
                ),

                "ddinter_ids": [
                    str(drug_a_id),
                    str(drug_b_id)
                ],
            }

        # -------------------------------------------------
        # DUPLICATE PAIR
        # -------------------------------------------------

        else:

            # If the first record had no mechanism but a
            # later DDInter record does, use the later one.

            if (
                not existing["mechanism"]
                and mechanism_text
            ):

                existing["mechanism"] = (
                    mechanism_text
                )

            # Merge mechanism categories without duplicates.

            existing["categories"] = list(
                dict.fromkeys(
                    existing["categories"]
                    + list(categories)
                )
            )

    return pair_index


# =========================================================
# MAIN
# =========================================================

def main():

    # -----------------------------------------------------
    # CHECK GRAPH
    # -----------------------------------------------------

    if not GRAPH_FILE.exists():

        raise FileNotFoundError(
            f"Graph not found: {GRAPH_FILE}"
        )

    # -----------------------------------------------------
    # CHECK DDINTER KNOWLEDGE BASE
    # -----------------------------------------------------

    if not KB_FILE.exists():

        raise FileNotFoundError(
            f"DDInter knowledge base not found: {KB_FILE}\n"
            "Place ddi_knowledge_base.json in the ddinter folder first."
        )

    # -----------------------------------------------------
    # LOAD FILES
    # -----------------------------------------------------

    graph = load_json(
        GRAPH_FILE
    )

    kb = load_json(
        KB_FILE
    )

    # -----------------------------------------------------
    # BUILD MECHANISM INDEX
    # -----------------------------------------------------

    print(
        "Building DDInter mechanism index..."
    )

    pair_index = build_ddinter_pair_index(
        kb
    )

    print(
        f"DDInter mechanism pairs indexed : "
        f"{len(pair_index):,}"
    )

    # -----------------------------------------------------
    # COUNTERS
    # -----------------------------------------------------

    enriched = 0

    no_mechanism = 0

    skipped_curated = 0

    skipped_non_ddinter = 0

    # -----------------------------------------------------
    # PROCESS GRAPH INTERACTIONS
    # -----------------------------------------------------

    for interaction in graph.get(
        "interactions",
        []
    ):

        sources = set(
            interaction.get(
                "sources",
                []
            )
        )

        # =================================================
        # NEVER MODIFY CURATED INTERACTIONS
        # =================================================

        if (
            interaction.get(
                "details_status"
            ) == "curated"

            or interaction.get(
                "mechanism_verified"
            ) is True

            or "Custom seed dataset"
            in sources
        ):

            skipped_curated += 1

            continue

        # =================================================
        # ONLY PROCESS DDINTER INTERACTIONS
        # =================================================

        if (
            "DDInter" not in sources
            and interaction.get(
                "source"
            ) != "DDInter"
        ):

            skipped_non_ddinter += 1

            continue

        # =================================================
        # ONLY DRUG-DRUG INTERACTIONS
        # =================================================

        if interaction.get(
            "type"
        ) != "drug-drug":

            continue

        # =================================================
        # NORMALIZE GRAPH DRUG NAMES
        # =================================================

        a = normalize_name(
            interaction.get(
                "a",
                ""
            )
        )

        b = normalize_name(
            interaction.get(
                "b",
                ""
            )
        )

        if not a or not b:
            continue

        # =================================================
        # LOOK UP DDINTER DETAILS
        # =================================================

        details = pair_index.get(
            frozenset(
                (
                    a,
                    b
                )
            )
        )

        # =================================================
        # NO MECHANISM
        # =================================================

        if (
            not details
            or not details.get(
                "mechanism"
            )
        ):

            no_mechanism += 1

            continue

        # =================================================
        # ADD MECHANISM
        # =================================================

        interaction["mechanism"] = (
            details["mechanism"]
        )

        # =================================================
        # ADD MECHANISM CATEGORIES
        # =================================================

        if details.get(
            "categories"
        ):

            interaction[
                "ddinter_mechanism_categories"
            ] = details[
                "categories"
            ]

        # =================================================
        # MARK AS DDINTER-DETAILED
        # =================================================

        interaction[
            "details_status"
        ] = "ddinter_detailed"

        # -------------------------------------------------
        # IMPORTANT:
        #
        # This does NOT mean that our project manually
        # verified the mechanism.
        #
        # It means the mechanism came from DDInter.
        # -------------------------------------------------

        interaction[
            "mechanism_verified"
        ] = False

        # =================================================
        # KEEP DDINTER PROVENANCE
        # =================================================

        interaction[
            "source"
        ] = "DDInter"

        interaction[
            "sources"
        ] = [
            "DDInter"
        ]

        # =================================================
        # DO NOT CREATE ALTERNATIVES
        # =================================================
        #
        # We intentionally do not invent:
        #
        # - safer drugs
        # - replacement drugs
        # - treatment recommendations
        #
        # Those require separate clinical verification.
        #

        enriched += 1

    # =====================================================
    # WRITE UPDATED GRAPH
    # =====================================================

    with GRAPH_FILE.open(
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            graph,
            f,
            indent=2,
            ensure_ascii=False
        )

    # =====================================================
    # SUMMARY
    # =====================================================

    print()

    print(
        "========== DDINTER ENRICHMENT =========="
    )

    print(
        f"Interactions enriched      : "
        f"{enriched:,}"
    )

    print(
        f"No mechanism available     : "
        f"{no_mechanism:,}"
    )

    print(
        f"Curated interactions kept  : "
        f"{skipped_curated:,}"
    )

    print(
        f"Non-DDInter skipped        : "
        f"{skipped_non_ddinter:,}"
    )

    print(
        f"Graph written              : "
        f"{GRAPH_FILE}"
    )

    print(
        "========================================"
    )


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":
    main()