from __future__ import annotations

from datetime import datetime, timedelta
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"
TURNAROUND_MINUTES = 45

app = FastAPI(title="Autonomous Airport Operations API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def dt(value: str) -> datetime:
    return datetime.strptime(value, TIME_FORMAT)


def iso(value: datetime) -> str:
    return value.strftime(TIME_FORMAT)


# The first demo action is intentionally deterministic:
# POST /delay {"flight_id": "AI101", "delay_minutes": 40}
# causes a Gate G1 / Crew C1 conflict with AI102 and suggests G3 / C3.
flights: dict[str, dict] = {
    "AI101": {"id": "AI101", "flight_no": "AI 101", "sched_time": "2026-09-14T10:00:00", "est_time": "2026-09-14T10:00:00", "status": "On Time", "gate_id": "G1", "crew_id": "C1", "aircraft_id": "VT-AAA"},
    "AI102": {"id": "AI102", "flight_no": "AI 102", "sched_time": "2026-09-14T11:20:00", "est_time": "2026-09-14T11:20:00", "status": "On Time", "gate_id": "G1", "crew_id": "C1", "aircraft_id": "VT-AAB"},
    "AI103": {"id": "AI103", "flight_no": "AI 103", "sched_time": "2026-09-14T10:30:00", "est_time": "2026-09-14T10:30:00", "status": "On Time", "gate_id": "G2", "crew_id": "C2", "aircraft_id": "VT-AAC"},
    "AI104": {"id": "AI104", "flight_no": "AI 104", "sched_time": "2026-09-14T12:15:00", "est_time": "2026-09-14T12:15:00", "status": "On Time", "gate_id": "G2", "crew_id": "C2", "aircraft_id": "VT-AAD"},
    "AI105": {"id": "AI105", "flight_no": "AI 105", "sched_time": "2026-09-14T12:00:00", "est_time": "2026-09-14T12:00:00", "status": "On Time", "gate_id": "G3", "crew_id": "C4", "aircraft_id": "VT-AAE"},
    "AI106": {"id": "AI106", "flight_no": "AI 106", "sched_time": "2026-09-14T13:20:00", "est_time": "2026-09-14T13:20:00", "status": "On Time", "gate_id": "G3", "crew_id": "C3", "aircraft_id": "VT-AAF"},
    "AI107": {"id": "AI107", "flight_no": "AI 107", "sched_time": "2026-09-14T09:15:00", "est_time": "2026-09-14T09:15:00", "status": "On Time", "gate_id": "G4", "crew_id": "C3", "aircraft_id": "VT-AAG"},
    "AI108": {"id": "AI108", "flight_no": "AI 108", "sched_time": "2026-09-14T11:00:00", "est_time": "2026-09-14T11:00:00", "status": "On Time", "gate_id": "G4", "crew_id": "C4", "aircraft_id": "VT-AAH"},
    "AI109": {"id": "AI109", "flight_no": "AI 109", "sched_time": "2026-09-14T14:00:00", "est_time": "2026-09-14T14:00:00", "status": "On Time", "gate_id": "G5", "crew_id": "C1", "aircraft_id": "VT-AAI"},
    "AI110": {"id": "AI110", "flight_no": "AI 110", "sched_time": "2026-09-14T15:30:00", "est_time": "2026-09-14T15:30:00", "status": "On Time", "gate_id": "G5", "crew_id": "C2", "aircraft_id": "VT-AAJ"},
}
gates = {key: {"id": key, "name": f"Gate {key[-1]}"} for key in ["G1", "G2", "G3", "G4", "G5"]}
crews = {key: {"id": key, "name": f"Crew {key[-1]}"} for key in ["C1", "C2", "C3", "C4"]}


class DelayRequest(BaseModel):
    flight_id: str
    delay_minutes: int = Field(ge=0, le=720)


class ReassignRequest(BaseModel):
    flight_id: str
    resource_type: Literal["gate", "crew"]
    new_resource_id: str


def occupancy_end(flight: dict) -> datetime:
    return dt(flight["est_time"]) + timedelta(minutes=TURNAROUND_MINUTES)


def ordered_resource_flights(resource_type: Literal["gate", "crew"], resource_id: str, exclude_id: str | None = None) -> list[dict]:
    field = f"{resource_type}_id"
    return sorted(
        (f for f in flights.values() if f[field] == resource_id and f["id"] != exclude_id),
        key=lambda flight: dt(flight["est_time"]),
    )


def conflicts_for(flight: dict, resource_type: Literal["gate", "crew"], resource_id: str) -> list[dict]:
    """Return every overlap for flight's estimated arrival through turnaround."""
    start, end = dt(flight["est_time"]), occupancy_end(flight)
    conflicts = []
    for other in ordered_resource_flights(resource_type, resource_id, flight["id"]):
        other_start, other_end = dt(other["est_time"]), occupancy_end(other)
        if start < other_end and other_start < end:
            conflicts.append({
                "type": resource_type,
                "resource_id": resource_id,
                "affected_flight_id": other["id"],
                "message": f"{resource_type.title()} {resource_id} overlaps with {other['flight_no']}",
            })
    return conflicts


def resource_is_available(flight: dict, resource_type: Literal["gate", "crew"], resource_id: str) -> bool:
    return not conflicts_for(flight, resource_type, resource_id)


def find_available(resource_type: Literal["gate", "crew"], flight: dict) -> str | None:
    pool = gates if resource_type == "gate" else crews
    current = flight[f"{resource_type}_id"]
    for resource_id in pool:
        if resource_id != current and resource_is_available(flight, resource_type, resource_id):
            return resource_id
    return None


def resource_view(resource_type: Literal["gate", "crew"]) -> list[dict]:
    pool = gates if resource_type == "gate" else crews
    field = f"{resource_type}_id"
    result = []
    for resource_id, resource in pool.items():
        assigned = ordered_resource_flights(resource_type, resource_id)
        current = assigned[0] if assigned else None
        result.append({
            **resource,
            "busy_until": iso(max((occupancy_end(f) for f in assigned), default=dt("2026-09-14T00:00:00"))),
            "current_flight_id": current["id"] if current else None,
            "assigned_flight_ids": [f["id"] for f in assigned],
        })
    return result


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/flights")
def get_flights() -> list[dict]:
    return sorted(flights.values(), key=lambda flight: dt(flight["est_time"]))


@app.get("/gates")
def get_gates() -> list[dict]:
    return resource_view("gate")


@app.get("/crew")
def get_crew() -> list[dict]:
    return resource_view("crew")


@app.post("/delay")
def delay_flight(payload: DelayRequest) -> dict:
    flight = flights.get(payload.flight_id)
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")

    # Absolute from scheduled time: calling the same request twice is idempotent.
    flight["est_time"] = iso(dt(flight["sched_time"]) + timedelta(minutes=payload.delay_minutes))
    flight["status"] = "Delayed" if payload.delay_minutes else "On Time"

    conflicts = conflicts_for(flight, "gate", flight["gate_id"]) + conflicts_for(flight, "crew", flight["crew_id"])
    suggestions = []
    if conflicts:
        for resource_type in ("gate", "crew"):
            candidate = find_available(resource_type, flight)
            if candidate:
                suggestions.append({
                    "flight_id": flight["id"],
                    "resource_type": resource_type,
                    "new_resource_id": candidate,
                    "reason": f"{resource_type.title()} {candidate} is free during the revised turnaround window",
                })

    conflicted_types = {conflict["type"] for conflict in conflicts}
    suggested_types = {item["resource_type"] for item in suggestions}
    return {
        "flight_id": flight["id"],
        "new_est_time": flight["est_time"],
        "conflicts": conflicts,
        # `suggestion` keeps the original simple frontend contract. Newer clients
        # should render every item in `suggestions` when a delay affects both types.
        "suggestion": suggestions[0] if suggestions else None,
        "suggestions": suggestions,
        "needs_manual_intervention": bool(conflicted_types - suggested_types),
    }


@app.post("/reassign")
def reassign(payload: ReassignRequest) -> dict:
    flight = flights.get(payload.flight_id)
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")
    pool = gates if payload.resource_type == "gate" else crews
    if payload.new_resource_id not in pool:
        raise HTTPException(status_code=404, detail=f"{payload.resource_type.title()} not found")
    if not resource_is_available(flight, payload.resource_type, payload.new_resource_id):
        raise HTTPException(status_code=409, detail=f"{payload.resource_type.title()} is no longer available")

    flight[f"{payload.resource_type}_id"] = payload.new_resource_id
    return {"message": "Reassignment applied", "flight": flight}
