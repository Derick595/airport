"""
seed_data.py - Realistic seed data for the 2-hour hackathon airport ops build.
Contains 12 flights, 5 gates, and 4 crews.
Provides get_initial_data() returning fresh deep-copied data dictionaries.
Calibrated for 3 deterministic live demo scenarios:
  1. Gate Conflict & Auto-Fix: Delay FL101 by 45m -> overlaps FL104 on G1 -> reassign FL104 to G2.
  2. Crew Conflict & Auto-Fix: Delay FL102 by 50m -> overlaps FL106 with Crew C2 -> reassign FL106 to C3.
  3. Peak Hour No-Solution: Delay FL107 by 25m -> overlaps FL112 on G1, but all 5 gates full -> no_solution: True.
"""

import copy

INITIAL_GATES = [
    {"id": "G1", "name": "Gate A1", "busy_until": "14:30", "current_flight_id": "FL101"},
    {"id": "G2", "name": "Gate A2", "busy_until": "14:45", "current_flight_id": "FL102"},
    {"id": "G3", "name": "Gate B1", "busy_until": "13:30", "current_flight_id": None},
    {"id": "G4", "name": "Gate B2", "busy_until": "13:45", "current_flight_id": None},
    {"id": "G5", "name": "Gate C1", "busy_until": "15:00", "current_flight_id": "FL103"},
]

INITIAL_CREW = [
    {"id": "C1", "name": "Flight Crew Alpha", "busy_until": "14:30", "current_flight_id": "FL101"},
    {"id": "C2", "name": "Flight Crew Bravo", "busy_until": "14:45", "current_flight_id": "FL102"},
    {"id": "C3", "name": "Flight Crew Charlie", "busy_until": "15:00", "current_flight_id": "FL103"},
    {"id": "C4", "name": "Flight Crew Delta", "busy_until": "13:30", "current_flight_id": None},
]

# 12 flights across two operational banks (Bank 1: 14:00-15:45, Bank 2 Peak: 16:30-17:25)
# Turnaround buffer: 30 mins
INITIAL_FLIGHTS = [
    # --- Operational Bank 1: 14:00 - 15:45 ---
    {
        "id": "FL101",
        "flight_no": "AA101",
        "sched_time": "14:00",
        "est_time": "14:00",
        "status": "ON_TIME",
        "gate_id": "G1",
        "crew_id": "C1",
        "aircraft_id": "N101AA"
    },
    {
        "id": "FL102",
        "flight_no": "UA302",
        "sched_time": "14:15",
        "est_time": "14:15",
        "status": "ON_TIME",
        "gate_id": "G2",
        "crew_id": "C2",
        "aircraft_id": "N202UA"
    },
    {
        "id": "FL103",
        "flight_no": "DL403",
        "sched_time": "14:30",
        "est_time": "14:30",
        "status": "ON_TIME",
        "gate_id": "G5",
        "crew_id": "C3",
        "aircraft_id": "N303DL"
    },
    {
        "id": "FL104",
        "flight_no": "AA104",
        "sched_time": "14:45",
        "est_time": "14:45",
        "status": "ON_TIME",
        "gate_id": "G1",  # Downstream on Gate G1
        "crew_id": "C4",
        "aircraft_id": "N104AA"
    },
    {
        "id": "FL105",
        "flight_no": "SW505",
        "sched_time": "15:00",
        "est_time": "15:00",
        "status": "ON_TIME",
        "gate_id": "G3",
        "crew_id": "C1",
        "aircraft_id": "N505SW"
    },
    {
        "id": "FL106",
        "flight_no": "UA306",
        "sched_time": "15:15",
        "est_time": "15:15",
        "status": "ON_TIME",
        "gate_id": "G4",
        "crew_id": "C2",  # Downstream with Crew C2
        "aircraft_id": "N206UA"
    },

    # --- Operational Bank 2: Peak Hour 16:30 - 17:25 ---
    {
        "id": "FL107",
        "flight_no": "BA707",
        "sched_time": "16:30",
        "est_time": "16:30",
        "status": "ON_TIME",
        "gate_id": "G1",
        "crew_id": "C1",
        "aircraft_id": "G-XLEA"
    },
    {
        "id": "FL108",
        "flight_no": "AF808",
        "sched_time": "16:35",
        "est_time": "16:35",
        "status": "ON_TIME",
        "gate_id": "G2",
        "crew_id": "C2",
        "aircraft_id": "F-GZCP"
    },
    {
        "id": "FL109",
        "flight_no": "LH909",
        "sched_time": "16:40",
        "est_time": "16:40",
        "status": "ON_TIME",
        "gate_id": "G3",
        "crew_id": "C3",
        "aircraft_id": "D-AIMB"
    },
    {
        "id": "FL110",
        "flight_no": "DL410",
        "sched_time": "16:45",
        "est_time": "16:45",
        "status": "ON_TIME",
        "gate_id": "G4",
        "crew_id": "C4",
        "aircraft_id": "N410DL"
    },
    {
        "id": "FL111",
        "flight_no": "UA311",
        "sched_time": "16:50",
        "est_time": "16:50",
        "status": "ON_TIME",
        "gate_id": "G5",
        "crew_id": "C1",
        "aircraft_id": "N311UA"
    },
    {
        "id": "FL112",
        "flight_no": "QF112",
        "sched_time": "16:55",
        "est_time": "16:55",
        "status": "ON_TIME",
        "gate_id": "G1",  # Downstream on G1 during peak crunch
        "crew_id": "C2",
        "aircraft_id": "VH-OQA"
    },
]


def get_initial_data():
    """Returns deep copied initial data for flights, gates, and crew."""
    return {
        "flights": copy.deepcopy(INITIAL_FLIGHTS),
        "gates": copy.deepcopy(INITIAL_GATES),
        "crew": copy.deepcopy(INITIAL_CREW)
    }
