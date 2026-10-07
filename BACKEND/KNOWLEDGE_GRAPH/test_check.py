from fastapi.testclient import TestClient

from app import app


client = TestClient(app)


# ============================================================
# HELPERS
# ============================================================

def check(condition, message):
    if condition:
        print(f"PASS: {message}")
    else:
        print(f"FAIL: {message}")
        raise AssertionError(message)


def get_interactions(payload):
    response = client.post(
        "/check",
        json=payload
    )

    check(
        response.status_code == 200,
        f"/check returned HTTP {response.status_code}"
    )

    return response.json()


# ============================================================
# TEST HEADER
# ============================================================

print()
print("========== MEMBER 2 BACKEND TESTS ==========")
print()


# ============================================================
# 1. HEALTH
# ============================================================

response = client.get("/health")

check(
    response.status_code == 200,
    "/health"
)

health_data = response.json()

check(
    health_data.get("ok") is True,
    "/health returns ok=True"
)


# ============================================================
# 2. DRUGS
# ============================================================

response = client.get("/drugs")

check(
    response.status_code == 200,
    "/drugs"
)

drug_data = response.json()

check(
    len(drug_data.get("drugs", [])) > 0,
    "/drugs returns drug nodes"
)

check(
    len(drug_data.get("foods", [])) > 0,
    "/drugs returns food nodes"
)


# ============================================================
# 3. MAJOR DRUG-DRUG INTERACTION
# ============================================================

data = get_interactions({
    "drugs": [
        {"name": "warfarin"},
        {"name": "ibuprofen"}
    ]
})

interactions = data["interactions"]

check(
    len(interactions) >= 1,
    "major drug-drug interaction"
)

interaction = interactions[0]

check(
    interaction["severity"] == "major",
    "warfarin + ibuprofen severity is major"
)

check(
    interaction["details_status"] == "curated",
    "curated interaction remains curated"
)

check(
    interaction["mechanism_verified"] is True,
    "curated mechanism remains verified"
)


# ============================================================
# 4. DRUG-FOOD INTERACTION
# ============================================================

data = get_interactions({
    "drugs": [
        {"name": "warfarin"}
    ],
    "foods": [
        "leafy greens"
    ]
})

check(
    len(data["interactions"]) >= 1,
    "drug-food interaction"
)


# ============================================================
# 5. POLYPHARMACY
# ============================================================

data = get_interactions({
    "drugs": [
        {"name": "warfarin"},
        {"name": "ibuprofen"},
        {"name": "aspirin"}
    ]
})

check(
    len(data["interactions"]) == 3,
    "polypharmacy"
)


# ============================================================
# 6. BRAND-NAME RESOLUTION
# ============================================================

data = get_interactions({
    "drugs": [
        {"name": "Ecosprin 75"}
    ]
})

check(
    "aspirin" in data["drugs_checked"],
    "brand-name resolution"
)


# ============================================================
# 7. OCR-STYLE RESOLUTION
# ============================================================

data = get_interactions({
    "drugs": [
        {"name": "warfarin 5mg"}
    ]
})

check(
    "warfarin" in data["drugs_checked"],
    "OCR-style resolution"
)


# ============================================================
# 8. UNKNOWN DRUG
# ============================================================

data = get_interactions({
    "drugs": [
        {"name": "Zyxolan 5"}
    ]
})

check(
    len(data["unresolved_drugs"]) == 1,
    "unknown drug"
)


# ============================================================
# 9. LOW CONFIDENCE
# ============================================================

data = get_interactions({
    "drugs": [
        {
            "name": "warfarin",
            "confidence": 0.5
        }
    ]
})

check(
    len(data["low_confidence_drugs"]) == 1,
    "low confidence"
)


# ============================================================
# 10. ALTERNATIVES
# ============================================================

data = get_interactions({
    "drugs": [
        {"name": "warfarin"},
        {"name": "ibuprofen"}
    ]
})

interaction = data["interactions"][0]

check(
    "paracetamol" in interaction["alternatives"],
    "alternatives"
)


# ============================================================
# 11. SEVERITY ORDERING
# ============================================================

data = get_interactions({
    "drugs": [
        {"name": "warfarin"},
        {"name": "aspirin"},
        {"name": "ibuprofen"}
    ]
})

severities = [
    i["severity"]
    for i in data["interactions"]
]

expected_order = [
    "major",
    "major",
    "moderate"
]

check(
    severities == expected_order,
    "severity ordering"
)


# ============================================================
# 12. GRAPH ENDPOINT
# ============================================================

response = client.get("/graph")

check(
    response.status_code == 200,
    "/graph"
)

graph_data = response.json()

check(
    len(graph_data.get("nodes", [])) > 0,
    "/graph returns nodes"
)

check(
    len(graph_data.get("edges", [])) > 0,
    "/graph returns edges"
)


# ============================================================
# 13. MOCK PRESCRIPTION
# ============================================================

data = get_interactions({
    "patient_id": "test-patient",
    "drugs": [
        {"name": "warfarin"},
        {"name": "aspirin"},
        {"name": "ibuprofen"},
        {"name": "amiodarone"}
    ]
})

check(
    len(data["interactions"]) == 4,
    "mock prescriptions"
)


# ============================================================
# FINAL RESULT
# ============================================================

print()
print("=============================================")
print("ALL MEMBER 2 TESTS PASSED")
print("=============================================")