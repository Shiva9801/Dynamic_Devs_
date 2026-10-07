import json
from itertools import combinations
from pathlib import Path
from typing import List, Optional

import networkx as nx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


DATA_FILE = Path(__file__).parent / "data" / "seed_graph_ddinter.json"

SEV_RANK = {
    "contraindicated": 0,
    "major": 1,
    "moderate": 2,
    "minor": 3
}


def load_graph(path: Path = DATA_FILE):
    data = json.loads(path.read_text(encoding="utf-8"))

    g = nx.Graph()
    lookup = {}

    # ---------------------------------------------------------
    # DRUG NODES
    # ---------------------------------------------------------

    for d in data["drugs"]:
        g.add_node(
            d["generic"],
            kind="drug",
            atc=d["atc"],
            drug_class=d["class"]
        )

        lookup[d["generic"].lower()] = (
            d["generic"],
            "drug"
        )

        lookup[d["atc"].lower()] = (
            d["generic"],
            "drug"
        )

        for alias in d.get("aliases", []):
            lookup[alias.lower()] = (
                d["generic"],
                "drug"
            )

    # ---------------------------------------------------------
    # FOOD NODES
    # ---------------------------------------------------------

    for f in data["foods"]:
        g.add_node(
            f["name"],
            kind="food"
        )

        lookup[f["name"].lower()] = (
            f["name"],
            "food"
        )

        for alias in f.get("aliases", []):
            lookup[alias.lower()] = (
                f["name"],
                "food"
            )

    # ---------------------------------------------------------
    # INTERACTION EDGES
    # ---------------------------------------------------------

    for e in data["interactions"]:
        g.add_edge(
            e["a"],
            e["b"],
            type=e["type"],
            severity=e["severity"],
            mechanism=e["mechanism"],
            note=e.get("note"),
            alternatives=e.get("alternatives", []),
            replace=e.get("replace"),

            source=e.get(
                "source",
                "seed data - verify"
            ),

            sources=e.get(
                "sources",
                [e["source"]] if e.get("source") else []
            ),

            details_status=e.get(
                "details_status",
                "curated"
            ),

            mechanism_verified=e.get(
                "mechanism_verified",
                True
            ),

            evidence=e.get(
                "evidence",
                {}
            )
        )

    return g, lookup


G, LOOKUP = load_graph()


def resolve(name: Optional[str], kind: str):
    """
    Match OCR text like 'Ecosprin 75' to a graph node.

    Tries:
    1. exact match
    2. first word
    3. substring match
    """

    if not name:
        return None

    n = name.lower().strip()

    candidates = [
        n,
        n.split()[0] if n.split() else n
    ]

    # Exact / first-word match
    for candidate in candidates:
        hit = LOOKUP.get(candidate)

        if hit and hit[1] == kind:
            return hit[0]

    # Substring fallback
    for key, (node, k) in LOOKUP.items():
        if (
            k == kind
            and len(key) > 3
            and key in n
        ):
            return node

    return None


class DrugIn(BaseModel):
    name: str
    generic: Optional[str] = None
    code: Optional[str] = None
    dose: Optional[str] = None
    confidence: Optional[float] = None


class CheckIn(BaseModel):
    patient_id: Optional[str] = None
    drugs: List[DrugIn]
    foods: List[str] = []


app = FastAPI(
    title="Drug Interaction Graph API"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)


# ---------------------------------------------------------
# HEALTH
# ---------------------------------------------------------

@app.get("/health")
def health():
    return {
        "ok": True,
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges()
    }


# ---------------------------------------------------------
# DRUGS / FOODS
# ---------------------------------------------------------

@app.get("/drugs")
def drugs():
    return {
        "drugs": sorted(
            n
            for n, d in G.nodes(data=True)
            if d["kind"] == "drug"
        ),
        "foods": sorted(
            n
            for n, d in G.nodes(data=True)
            if d["kind"] == "food"
        )
    }


# ---------------------------------------------------------
# CHECK INTERACTIONS
# ---------------------------------------------------------

@app.post("/check")
def check(req: CheckIn):

    patient = []
    unresolved = []
    low_conf = []

    # -----------------------------------------------------
    # RESOLVE PATIENT DRUGS
    # -----------------------------------------------------

    for d in req.drugs:

        node = (
            resolve(d.code, "drug")
            or resolve(d.generic, "drug")
            or resolve(d.name, "drug")
        )

        if node is None:
            unresolved.append({
                "name": d.name,
                "reason": "not in knowledge graph"
            })
            continue

        if node not in patient:
            patient.append(node)

        if (
            d.confidence is not None
            and d.confidence < 0.7
        ):
            low_conf.append({
                "name": d.name,
                "matched": node,
                "confidence": d.confidence
            })

    # -----------------------------------------------------
    # RESOLVE FOODS
    # -----------------------------------------------------

    foods = [
        f
        for f in (
            resolve(x, "food")
            for x in req.foods
        )
        if f
    ]

    found = []

    # -----------------------------------------------------
    # ADD INTERACTION TO RESPONSE
    # -----------------------------------------------------

    def add(a, b):

        e = G.edges[a, b]

        safe_alts = []
        cautious_alts = []

        # ---------------------------------------------
        # CHECK ALTERNATIVES
        # ---------------------------------------------

        for alternative in e["alternatives"]:

            blocked = False

            for patient_drug in patient:

                if patient_drug == e["replace"]:
                    continue

                if G.has_edge(
                    alternative,
                    patient_drug
                ):

                    alt_edge = G.edges[
                        alternative,
                        patient_drug
                    ]

                    if alt_edge["severity"] in {
                        "major",
                        "contraindicated"
                    }:
                        blocked = True
                        break

                    # Moderate/minor interaction:
                    # still show alternative, but warn.
                    cautious_alts.append({
                        "drug": alternative,
                        "with": patient_drug,
                        "severity": alt_edge["severity"]
                    })

            if (
                not blocked
                and alternative not in safe_alts
            ):
                safe_alts.append(alternative)

        # ---------------------------------------------
        # BUILD RESPONSE OBJECT
        # ---------------------------------------------

        found.append({
            "drug_a": a,
            "drug_b": b,
            "type": e["type"],
            "severity": e["severity"],
            "mechanism": e["mechanism"],
            "note": e["note"],

            "source": e["source"],

            "sources": e.get(
                "sources",
                []
            ),

            "details_status": e.get(
                "details_status",
                "curated"
            ),

            "mechanism_verified": e.get(
                "mechanism_verified",
                True
            ),

            "evidence": e.get(
                "evidence",
                {}
            ),

            "suggest_replacing": e["replace"],

            "alternatives": safe_alts,

            "alternative_warnings": cautious_alts,

            "alternatives_note": (
                "For clinician review only; not a prescription."
                if safe_alts
                else None
            )
        })

    # -----------------------------------------------------
    # DRUG-DRUG INTERACTIONS
    # -----------------------------------------------------

    for a, b in combinations(patient, 2):

        if G.has_edge(a, b):
            add(a, b)

    # -----------------------------------------------------
    # DRUG-FOOD INTERACTIONS
    # -----------------------------------------------------

    for p in patient:

        for f in foods:

            if G.has_edge(p, f):
                add(p, f)

    # -----------------------------------------------------
    # SORT BY SEVERITY
    # -----------------------------------------------------

    found.sort(
        key=lambda x: SEV_RANK[x["severity"]]
    )

    return {
        "patient_id": req.patient_id,
        "drugs_checked": patient,
        "foods_checked": foods,
        "interactions": found,
        "unresolved_drugs": unresolved,
        "low_confidence_drugs": low_conf,
        "disclaimer": (
            "Decision support only. "
            "Not a substitute for a doctor or pharmacist."
        )
    }


# ---------------------------------------------------------
# GRAPH
# ---------------------------------------------------------

@app.get("/graph")
def graph():
    """Nodes + edges for D3 / vis.js visualisation."""

    return {
        "nodes": [
            {
                "id": n,
                **d
            }
            for n, d in G.nodes(data=True)
        ],

        "edges": [
            {
                "source": a,
                "target": b,
                "severity": e["severity"],
                "type": e["type"],
                "mechanism": e["mechanism"],

                "sources": e.get(
                    "sources",
                    []
                ),

                "details_status": e.get(
                    "details_status",
                    "curated"
                ),

                "mechanism_verified": e.get(
                    "mechanism_verified",
                    True
                )
            }

            for a, b, e in G.edges(data=True)
        ]
    }