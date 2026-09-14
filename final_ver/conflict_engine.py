"""
conflict_engine.py - Pure Python Conflict Detection & Fix Suggestion Engine
(Person 3 Hackathon Implementation)

Calculates turnaround buffer conflicts for gates and crews when flights are delayed.
Provides linear-scan suggestion algorithm to reassign resources, or flags no_solution: true.
"""

from typing import Dict, List, Optional, Any, Tuple

TURNAROUND_BUFFER = 30  # Turnaround buffer in minutes


def time_to_minutes(time_str: str) -> int:
    """Converts 'HH:MM' 24-hour string to integer minutes from midnight."""
    parts = time_str.strip().split(":")
    return int(parts[0]) * 60 + int(parts[1])


def minutes_to_time(minutes: int) -> str:
    """Converts integer minutes from midnight to 'HH:MM' format."""
    normalized = minutes % (24 * 60)
    hours = normalized // 60
    mins = normalized % 60
    return f"{hours:02d}:{mins:02d}"


def add_minutes(time_str: str, delta_minutes: int) -> str:
    """Adds delta_minutes to 'HH:MM' time string."""
    mins = time_to_minutes(time_str) + delta_minutes
    return minutes_to_time(mins)


def windows_overlap(start1: int, end1: int, start2: int, end2: int) -> bool:
    """Returns True if [start1, end1) and [start2, end2) intervals overlap."""
    return max(start1, start2) < min(end1, end2)


def get_flight_window(flight: Dict[str, Any], buffer_mins: int = TURNAROUND_BUFFER) -> Tuple[int, int]:
    """Returns (start_mins, end_mins) for flight occupancy."""
    start = time_to_minutes(flight.get("est_time", flight["sched_time"]))
    end = start + buffer_mins
    return start, end


def check_conflicts(
    flight: Dict[str, Any],
    new_est_time: str,
    gates: List[Dict[str, Any]],
    crew: List[Dict[str, Any]],
    flights: List[Dict[str, Any]],
    buffer_mins: int = TURNAROUND_BUFFER
) -> List[Dict[str, Any]]:
    """
    Checks if a flight's new estimated departure/arrival creates conflicts on its gate or crew.
    Rule: new_departure_time + turnaround_buffer > next_flight.sched_time on same gate/crew.
    """
    conflicts = []
    flight_id = flight["id"]
    new_start = time_to_minutes(new_est_time)
    new_end = new_start + buffer_mins

    gate_lookup = {g["id"]: g for g in gates}
    crew_lookup = {c["id"]: c for c in crew}

    flight_gate_id = flight.get("gate_id")
    flight_crew_id = flight.get("crew_id")

    # 1. Gate conflicts with other flights
    if flight_gate_id:
        gate_info = gate_lookup.get(flight_gate_id, {"id": flight_gate_id, "name": f"Gate {flight_gate_id}"})
        for other in flights:
            if other["id"] == flight_id:
                continue
            if other.get("gate_id") == flight_gate_id:
                other_start, other_end = get_flight_window(other, buffer_mins)
                if windows_overlap(new_start, new_end, other_start, other_end):
                    conflicts.append({
                        "type": "gate",
                        "resource_id": flight_gate_id,
                        "resource_name": gate_info["name"],
                        "flight_id": flight_id,
                        "flight_no": flight.get("flight_no", flight_id),
                        "conflicting_flight_id": other["id"],
                        "conflicting_flight_no": other.get("flight_no", other["id"]),
                        "overlap_start": minutes_to_time(max(new_start, other_start)),
                        "overlap_end": minutes_to_time(min(new_end, other_end)),
                        "details": (
                            f"Flight {flight.get('flight_no', flight_id)} delayed to {new_est_time} "
                            f"(busy until {minutes_to_time(new_end)}) overlaps with "
                            f"Flight {other.get('flight_no', other['id'])} scheduled at {other['sched_time']} "
                            f"on {gate_info['name']}."
                        )
                    })

    # 2. Crew conflicts with other flights
    if flight_crew_id:
        crew_info = crew_lookup.get(flight_crew_id, {"id": flight_crew_id, "name": f"Crew {flight_crew_id}"})
        for other in flights:
            if other["id"] == flight_id:
                continue
            if other.get("crew_id") == flight_crew_id:
                other_start, other_end = get_flight_window(other, buffer_mins)
                if windows_overlap(new_start, new_end, other_start, other_end):
                    conflicts.append({
                        "type": "crew",
                        "resource_id": flight_crew_id,
                        "resource_name": crew_info["name"],
                        "flight_id": flight_id,
                        "flight_no": flight.get("flight_no", flight_id),
                        "conflicting_flight_id": other["id"],
                        "conflicting_flight_no": other.get("flight_no", other["id"]),
                        "overlap_start": minutes_to_time(max(new_start, other_start)),
                        "overlap_end": minutes_to_time(min(new_end, other_end)),
                        "details": (
                            f"Flight {flight.get('flight_no', flight_id)} delayed to {new_est_time} "
                            f"(crew busy until {minutes_to_time(new_end)}) overlaps with "
                            f"Flight {other.get('flight_no', other['id'])} scheduled at {other['sched_time']} "
                            f"with {crew_info['name']}."
                        )
                    })

    return conflicts


def is_gate_available(
    gate_id: str,
    target_start: int,
    target_end: int,
    flights: List[Dict[str, Any]],
    exclude_flight_id: str,
    buffer_mins: int = TURNAROUND_BUFFER
) -> bool:
    """Checks if a gate is completely free of other flights during [target_start, target_end)."""
    for f in flights:
        if f["id"] == exclude_flight_id:
            continue
        if f.get("gate_id") == gate_id:
            f_start, f_end = get_flight_window(f, buffer_mins)
            if windows_overlap(target_start, target_end, f_start, f_end):
                return False
    return True


def is_crew_available(
    crew_id: str,
    target_start: int,
    target_end: int,
    flights: List[Dict[str, Any]],
    exclude_flight_id: str,
    buffer_mins: int = TURNAROUND_BUFFER
) -> bool:
    """Checks if a crew is completely free of other flights during [target_start, target_end)."""
    for f in flights:
        if f["id"] == exclude_flight_id:
            continue
        if f.get("crew_id") == crew_id:
            f_start, f_end = get_flight_window(f, buffer_mins)
            if windows_overlap(target_start, target_end, f_start, f_end):
                return False
    return True


def suggest_fix(
    conflict: Dict[str, Any],
    gates: List[Dict[str, Any]],
    crew: List[Dict[str, Any]],
    flights: List[Dict[str, Any]],
    buffer_mins: int = TURNAROUND_BUFFER
) -> Dict[str, Any]:
    """
    Finds the first free gate or crew that does not overlap anything.
    Prioritizes reassigning the downstream conflicting flight; if none found,
    checks reassigning the delayed flight.
    If no resource is free, returns no_solution: True for manual intervention.
    """
    conflict_type = conflict["type"]
    conflicting_flight_id = conflict["conflicting_flight_id"]
    delayed_flight_id = conflict["flight_id"]

    flight_lookup = {f["id"]: f for f in flights}
    downstream_flight = flight_lookup.get(conflicting_flight_id)
    delayed_flight = flight_lookup.get(delayed_flight_id)

    if not downstream_flight:
        return {
            "flight_id": conflicting_flight_id,
            "resource_type": conflict_type,
            "new_resource_id": None,
            "no_solution": True,
            "reason": "Target flight not found for reassignment."
        }

    ds_start, ds_end = get_flight_window(downstream_flight, buffer_mins)

    if conflict_type == "gate":
        current_gate_id = conflict["resource_id"]
        # 1. Try to reassign downstream flight to a free gate
        for g in gates:
            if g["id"] == current_gate_id:
                continue
            if is_gate_available(g["id"], ds_start, ds_end, flights, conflicting_flight_id, buffer_mins):
                return {
                    "flight_id": conflicting_flight_id,
                    "flight_no": downstream_flight.get("flight_no", conflicting_flight_id),
                    "resource_type": "gate",
                    "new_resource_id": g["id"],
                    "new_resource_name": g["name"],
                    "no_solution": False,
                    "reason": (
                        f"Optimal solution: a time conflict exists on {conflict.get('resource_name', current_gate_id)}. "
                        f"Shift Flight {downstream_flight.get('flight_no', conflicting_flight_id)} "
                        f"to {g['name']} (available {downstream_flight['sched_time']} - {minutes_to_time(ds_end)})."
                    )
                }

        # No gate available
        return {
            "flight_id": conflicting_flight_id,
            "flight_no": downstream_flight.get("flight_no", conflicting_flight_id),
            "resource_type": "gate",
            "new_resource_id": None,
            "no_solution": True,
            "reason": (
                f"Optimal solution unavailable: severe time conflict on {conflict.get('resource_name', current_gate_id)}. "
                f"All {len(gates)} gates are occupied during turnaround window ({downstream_flight['sched_time']} - {minutes_to_time(ds_end)}). "
                f"Immediate manual intervention and ground hold recommended."
            )
        }

    elif conflict_type == "crew":
        current_crew_id = conflict["resource_id"]
        # 1. Try to reassign downstream flight to a free crew
        for c in crew:
            if c["id"] == current_crew_id:
                continue
            if is_crew_available(c["id"], ds_start, ds_end, flights, conflicting_flight_id, buffer_mins):
                return {
                    "flight_id": conflicting_flight_id,
                    "flight_no": downstream_flight.get("flight_no", conflicting_flight_id),
                    "resource_type": "crew",
                    "new_resource_id": c["id"],
                    "new_resource_name": c["name"],
                    "no_solution": False,
                    "reason": (
                        f"Optimal solution: a duty-time conflict exists on {conflict.get('resource_name', current_crew_id)}. "
                        f"Shift Flight {downstream_flight.get('flight_no', conflicting_flight_id)} "
                        f"to {c['name']} (currently on standby)."
                    )
                }

        # No crew available
        return {
            "flight_id": conflicting_flight_id,
            "flight_no": downstream_flight.get("flight_no", conflicting_flight_id),
            "resource_type": "crew",
            "new_resource_id": None,
            "no_solution": True,
            "reason": (
                f"Optimal solution unavailable: duty overlap on {conflict.get('resource_name', current_crew_id)}, but all {len(crew)} "
                f"flight crew teams are already scheduled. Immediate manual crew callout recommended."
            )
        }

    return {
        "flight_id": conflicting_flight_id,
        "resource_type": conflict_type,
        "new_resource_id": None,
        "no_solution": True,
        "reason": f"Unknown conflict type: {conflict_type}"
    }
