"""
test_engine.py - Automated tests for conflict detection and API endpoints
"""

import pytest
from fastapi.testclient import TestClient
import conflict_engine
import seed_data
from main import app


@pytest.fixture
def client():
    # Reset state before each test
    client = TestClient(app)
    client.post("/reset")
    return client


def test_time_conversion_and_overlap():
    assert conflict_engine.time_to_minutes("14:00") == 840
    assert conflict_engine.minutes_to_time(840) == "14:00"
    assert conflict_engine.add_minutes("14:00", 45) == "14:45"
    assert conflict_engine.add_minutes("23:45", 30) == "00:15"

    # Overlap test: [14:00, 14:30) vs [14:20, 14:50)
    assert conflict_engine.windows_overlap(840, 870, 860, 890) is True
    # Non-overlap: [14:00, 14:30) vs [14:30, 15:00)
    assert conflict_engine.windows_overlap(840, 870, 870, 900) is False


def test_conflict_detection_gate_and_crew():
    data = seed_data.get_initial_data()
    fl101 = next(f for f in data["flights"] if f["id"] == "FL101")
    new_time = conflict_engine.add_minutes(fl101["sched_time"], 45)  # 14:45

    confs = conflict_engine.check_conflicts(
        flight=fl101,
        new_est_time=new_time,
        gates=data["gates"],
        crew=data["crew"],
        flights=data["flights"]
    )
    assert len(confs) >= 1
    gate_conf = next((c for c in confs if c["type"] == "gate"), None)
    assert gate_conf is not None
    assert gate_conf["resource_id"] == "G1"
    assert gate_conf["conflicting_flight_id"] == "FL104"

    # Suggestion
    fix = conflict_engine.suggest_fix(gate_conf, data["gates"], data["crew"], data["flights"])
    assert fix["no_solution"] is False
    assert fix["resource_type"] == "gate"
    assert fix["new_resource_id"] is not None


def test_no_solution_when_all_resources_full():
    data = seed_data.get_initial_data()
    # Force all gates to have flights at 14:45
    for i, g in enumerate(data["gates"]):
        data["flights"].append({
            "id": f"TEST_{i}",
            "flight_no": f"TST{i}",
            "sched_time": "14:45",
            "est_time": "14:45",
            "status": "ON_TIME",
            "gate_id": g["id"],
            "crew_id": "C1",
            "aircraft_id": f"N_TEST_{i}"
        })

    mock_conflict = {
        "type": "gate",
        "resource_id": "G1",
        "flight_id": "FL101",
        "conflicting_flight_id": "FL104"
    }
    fix = conflict_engine.suggest_fix(mock_conflict, data["gates"], data["crew"], data["flights"])
    assert fix["no_solution"] is True
    assert "manual intervention" in fix["reason"].lower()


def test_api_flights_gates_crew(client):
    r_flights = client.get("/flights")
    assert r_flights.status_code == 200
    flights = r_flights.json()
    assert len(flights) == 12

    r_gates = client.get("/gates")
    assert r_gates.status_code == 200
    assert len(r_gates.json()) == 5

    r_crew = client.get("/crew")
    assert r_crew.status_code == 200
    assert len(r_crew.json()) == 4


def test_api_delay_and_reassign_flow(client):
    # 1. Trigger 45 min delay on FL101
    delay_resp = client.post("/delay", json={"flight_id": "FL101", "delay_minutes": 45})
    assert delay_resp.status_code == 200
    res = delay_resp.json()
    assert res["flight"]["est_time"] == "14:45"
    assert len(res["conflicts"]) >= 1
    assert res["suggestion"] is not None

    sugg = res["suggestion"]
    assert sugg["no_solution"] is False
    target_flight_id = sugg["flight_id"]
    new_gate = sugg["new_resource_id"]

    # 2. Reassign flight to resolve conflict
    reassign_resp = client.post("/reassign", json={
        "flight_id": target_flight_id,
        "resource_type": "gate",
        "new_resource_id": new_gate
    })
    assert reassign_resp.status_code == 200
    reassign_data = reassign_resp.json()
    assert reassign_data["success"] is True
    assert reassign_data["flight"]["gate_id"] == new_gate

    # 3. Check updated flight in /flights
    all_flights = client.get("/flights").json()
    updated = next(f for f in all_flights if f["id"] == target_flight_id)
    assert updated["gate_id"] == new_gate

    # 4. Reset restores original state
    reset_resp = client.post("/reset")
    assert reset_resp.status_code == 200
    reset_flights = client.get("/flights").json()
    restored = next(f for f in reset_flights if f["id"] == target_flight_id)
    assert restored["gate_id"] == "G1"
