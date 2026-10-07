import json
from pathlib import Path

from fastapi.testclient import TestClient

from app import app



# Setup


client = TestClient(app)

MOCK_FILE = Path(__file__).parent / "data" / "mock_prescriptions.json"



# 1. Health check


def test_health():
    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["ok"] is True

    print("PASS: /health")



# 2. Drugs endpoint


def test_drugs():
    response = client.get("/drugs")

    assert response.status_code == 200

    data = response.json()

    assert "drugs" in data
    assert "foods" in data

    assert len(data["drugs"]) > 0
    assert len(data["foods"]) > 0

    print("PASS: /drugs")



# 3. Major drug-drug interaction


def test_major_interaction():
    payload = {
        "patient_id": "test_major_01",
        "drugs": [
            {"name": "warfarin"},
            {"name": "ibuprofen"}
        ],
        "foods": []
    }

    response = client.post("/check", json=payload)

    assert response.status_code == 200

    data = response.json()

    assert len(data["interactions"]) >= 1

    found = False

    for interaction in data["interactions"]:
        if (
            {interaction["drug_a"], interaction["drug_b"]}
            == {"warfarin", "ibuprofen"}
        ):
            assert interaction["severity"] == "major"
            found = True

    assert found

    print("PASS: major drug-drug interaction")



# 4. Drug-food interaction


def test_drug_food():
    payload = {
        "patient_id": "test_food_01",
        "drugs": [
            {"name": "warfarin"}
        ],
        "foods": [
            "leafy greens"
        ]
    }

    response = client.post("/check", json=payload)

    assert response.status_code == 200

    data = response.json()

    found = False

    for interaction in data["interactions"]:
        if (
            {interaction["drug_a"], interaction["drug_b"]}
            == {"warfarin", "leafy greens"}
        ):
            found = True

    assert found

    print("PASS: drug-food interaction")



# 5. Polypharmacy


def test_polypharmacy():
    payload = {
        "patient_id": "test_polypharmacy_01",
        "drugs": [
            {"name": "warfarin"},
            {"name": "aspirin"},
            {"name": "ibuprofen"}
        ],
        "foods": [
            "leafy greens"
        ]
    }

    response = client.post("/check", json=payload)

    assert response.status_code == 200

    data = response.json()

    assert len(data["interactions"]) == 4

    severities = [
        interaction["severity"]
        for interaction in data["interactions"]
    ]

    assert severities == [
        "major",
        "major",
        "moderate",
        "moderate"
    ]

    assert data["unresolved_drugs"] == []
    assert data["low_confidence_drugs"] == []

    print("PASS: polypharmacy")



# 6. Brand-name resolution


def test_brand_resolution():
    payload = {
        "patient_id": "test_brand_01",
        "drugs": [
            {"name": "Ecosprin 75"},
            {"name": "warfarin 5mg"}
        ],
        "foods": []
    }

    response = client.post("/check", json=payload)

    assert response.status_code == 200

    data = response.json()

    assert data["drugs_checked"] == [
        "aspirin",
        "warfarin"
    ]

    assert data["unresolved_drugs"] == []

    assert len(data["interactions"]) == 1
    assert data["interactions"][0]["severity"] == "major"

    print("PASS: brand-name resolution")



# 7. OCR-style input


def test_ocr_style():
    payload = {
        "patient_id": "test_ocr_01",
        "drugs": [
            {"name": "Warfarin 5 mg"},
            {"name": "Brufen 400"}
        ],
        "foods": []
    }

    response = client.post("/check", json=payload)

    assert response.status_code == 200

    data = response.json()

    assert data["drugs_checked"] == [
        "warfarin",
        "ibuprofen"
    ]

    assert data["unresolved_drugs"] == []

    assert len(data["interactions"]) >= 1

    print("PASS: OCR-style resolution")



# 8. Unknown drug


def test_unknown_drug():
    payload = {
        "patient_id": "test_unknown_01",
        "drugs": [
            {"name": "Zyxolan 5"}
        ],
        "foods": []
    }

    response = client.post("/check", json=payload)

    assert response.status_code == 200

    data = response.json()

    assert len(data["unresolved_drugs"]) == 1

    assert data["unresolved_drugs"][0]["name"] == "Zyxolan 5"

    assert data["interactions"] == []

    print("PASS: unknown drug")



# 9. Low OCR confidence


def test_low_confidence():
    payload = {
        "patient_id": "test_confidence_01",
        "drugs": [
            {
                "name": "warfarin",
                "confidence": 0.45
            }
        ],
        "foods": []
    }

    response = client.post("/check", json=payload)

    assert response.status_code == 200

    data = response.json()

    assert len(data["low_confidence_drugs"]) == 1

    assert data["low_confidence_drugs"][0]["name"] == "warfarin"
    assert data["low_confidence_drugs"][0]["confidence"] == 0.45

    print("PASS: low confidence")



# 10. Alternatives


def test_alternatives():
    payload = {
        "patient_id": "test_alt_01",
        "drugs": [
            {"name": "warfarin"},
            {"name": "ibuprofen"}
        ],
        "foods": []
    }

    response = client.post("/check", json=payload)

    assert response.status_code == 200

    data = response.json()

    interaction = data["interactions"][0]

    assert interaction["suggest_replacing"] == "ibuprofen"

    assert "paracetamol" in interaction["alternatives"]

    assert interaction["alternatives_note"] is not None

    print("PASS: alternatives")



# 11. Severity ordering
# 11. Severity ordering


def test_severity_order():
    payload = {
        "patient_id": "test_severity_01",
        "drugs": [
            {"name": "warfarin"},
            {"name": "aspirin"},
            {"name": "ibuprofen"},
            {"name": "spironolactone"}
        ],
        "foods": []
    }

    response = client.post("/check", json=payload)

    assert response.status_code == 200

    data = response.json()

    severities = [
        interaction["severity"]
        for interaction in data["interactions"]
    ]

    expected_rank = {
        "contraindicated": 0,
        "major": 1,
        "moderate": 2,
        "minor": 3
    }

    # Verify interactions are sorted by severity
    assert severities == sorted(
        severities,
        key=lambda s: expected_rank[s]
    )

    # Verify the two known major interactions
    # remain at the top.
    assert severities[:2] == [
        "major",
        "major"
    ]

    print("PASS: severity ordering")

# 12. Graph endpoint


def test_graph():
    response = client.get("/graph")

    assert response.status_code == 200

    data = response.json()

    assert "nodes" in data
    assert "edges" in data

    assert len(data["nodes"]) > 0
    assert len(data["edges"]) > 0

    print("PASS: /graph")



# 13. Mock prescription file


def test_mock_prescriptions():
    prescriptions = json.loads(
        MOCK_FILE.read_text(encoding="utf-8")
    )

    assert len(prescriptions) > 0

    for prescription in prescriptions:
        response = client.post(
            "/check",
            json=prescription
        )

        assert response.status_code == 200

        data = response.json()

        assert "drugs_checked" in data
        assert "interactions" in data
        assert "unresolved_drugs" in data
        assert "low_confidence_drugs" in data
        assert "disclaimer" in data

    print("PASS: mock prescriptions")



# Run everything


if __name__ == "__main__":

    print("\n========== MEMBER 2 BACKEND TESTS ==========\n")

    test_health()
    test_drugs()
    test_major_interaction()
    test_drug_food()
    test_polypharmacy()
    test_brand_resolution()
    test_ocr_style()
    test_unknown_drug()
    test_low_confidence()
    test_alternatives()
    test_severity_order()
    test_graph()
    test_mock_prescriptions()

    print("\n=============================================")
    print("ALL MEMBER 2 TESTS PASSED")
    print("=============================================\n")