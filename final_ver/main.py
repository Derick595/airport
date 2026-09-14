"""
main.py - Airport Operations FastAPI Backend
(Person 2 Hackathon Implementation)

Provides in-memory REST API with CORS enabled:
  GET  /flights
  GET  /gates
  GET  /crew
  POST /delay
  POST /reassign
  POST /reset
  Static UI hosting at /
"""

import os
from typing import Optional, Literal
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

import seed_data
import conflict_engine

app = FastAPI(
    title="Airport Operations Conflict Resolver",
    description="2-Hour Hackathon Flight Operations & Conflict Management API",
    version="1.0.0"
)

# Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory database state
STATE = seed_data.get_initial_data()


# -------------------------------------------------------------
# Request / Response Models
# -------------------------------------------------------------
class DelayRequest(BaseModel):
    flight_id: str = Field(..., description="ID of the flight, e.g. FL101")
    delay_minutes: int = Field(..., ge=0, description="Delay in minutes")


class ReassignRequest(BaseModel):
    flight_id: str = Field(..., description="ID of the flight to reassign")
    resource_type: Literal["gate", "crew"] = Field(..., description="'gate' or 'crew'")
    new_resource_id: str = Field(..., description="Target Gate ID (e.g. G2) or Crew ID (e.g. C4)")


# -------------------------------------------------------------
# Helper Functions
# -------------------------------------------------------------
def find_flight(flight_id: str):
    for f in STATE["flights"]:
        if f["id"] == flight_id:
            return f
    return None


def update_flight_status(flight: dict):
    sched_m = conflict_engine.time_to_minutes(flight["sched_time"])
    est_m = conflict_engine.time_to_minutes(flight["est_time"])
    delay = est_m - sched_m

    if delay <= 0:
        flight["status"] = "ON_TIME"
    elif delay < 45:
        flight["status"] = "DELAYED"
    else:
        flight["status"] = "CRITICAL"


# -------------------------------------------------------------
# Endpoints
# -------------------------------------------------------------
@app.get("/flights")
def get_flights():
    """List all scheduled and active flights."""
    return STATE["flights"]


@app.get("/gates")
def get_gates():
    """List all airport gates with current occupancy."""
    return STATE["gates"]


@app.get("/crew")
def get_crew():
    """List all flight crew teams with current status."""
    return STATE["crew"]


@app.post("/delay")
def post_delay(req: DelayRequest):
    """
    Updates flight estimated time, updates gate/crew busy times,
    and returns detected conflicts along with automated fix suggestions.
    """
    flight = find_flight(req.flight_id)
    if not flight:
        raise HTTPException(status_code=404, detail=f"Flight '{req.flight_id}' not found.")

    # Calculate new estimated departure/arrival time
    new_est_time = conflict_engine.add_minutes(flight["sched_time"], req.delay_minutes)
    flight["est_time"] = new_est_time
    update_flight_status(flight)

    # Update gate and crew busy_until for this flight
    gate_id = flight.get("gate_id")
    crew_id = flight.get("crew_id")
    flight_busy_until = conflict_engine.add_minutes(new_est_time, conflict_engine.TURNAROUND_BUFFER)

    if gate_id:
        for g in STATE["gates"]:
            if g["id"] == gate_id and g.get("current_flight_id") == flight["id"]:
                g["busy_until"] = flight_busy_until

    if crew_id:
        for c in STATE["crew"]:
            if c["id"] == crew_id and c.get("current_flight_id") == flight["id"]:
                c["busy_until"] = flight_busy_until

    # Check for conflicts
    conflicts = conflict_engine.check_conflicts(
        flight=flight,
        new_est_time=new_est_time,
        gates=STATE["gates"],
        crew=STATE["crew"],
        flights=STATE["flights"]
    )

    suggestion = None
    suggestions = []
    if conflicts:
        flight["status"] = "CRITICAL"
        suggestion = conflict_engine.suggest_fix(
            conflict=conflicts[0],
            gates=STATE["gates"],
            crew=STATE["crew"],
            flights=STATE["flights"]
        )
        for c in conflicts:
            s = conflict_engine.suggest_fix(
                conflict=c,
                gates=STATE["gates"],
                crew=STATE["crew"],
                flights=STATE["flights"]
            )
            suggestions.append(s)

    return {
        "flight": flight,
        "conflicts": conflicts,
        "suggestion": suggestion,
        "suggestions": suggestions
    }


@app.post("/reassign")
def post_reassign(req: ReassignRequest):
    """
    Reassigns a flight to a different gate or flight crew.
    Updates the flight record and synchronizes resource occupancy.
    """
    flight = find_flight(req.flight_id)
    if not flight:
        raise HTTPException(status_code=404, detail=f"Flight '{req.flight_id}' not found.")

    if req.resource_type == "gate":
        # Validate gate exists
        target_gate = next((g for g in STATE["gates"] if g["id"] == req.new_resource_id), None)
        if not target_gate:
            raise HTTPException(status_code=404, detail=f"Gate '{req.new_resource_id}' not found.")

        old_gate_id = flight.get("gate_id")
        flight["gate_id"] = req.new_resource_id

        # Update old gate if current flight was assigned
        if old_gate_id:
            for g in STATE["gates"]:
                if g["id"] == old_gate_id and g.get("current_flight_id") == flight["id"]:
                    g["current_flight_id"] = None

        # If flight is currently active or upcoming, update target gate
        flight_busy_until = conflict_engine.add_minutes(flight["est_time"], conflict_engine.TURNAROUND_BUFFER)
        target_gate["busy_until"] = max(target_gate.get("busy_until", "00:00"), flight_busy_until)

        # Re-evaluate flight status
        active_conflicts = conflict_engine.check_conflicts(
            flight=flight,
            new_est_time=flight["est_time"],
            gates=STATE["gates"],
            crew=STATE["crew"],
            flights=STATE["flights"]
        )
        if not active_conflicts:
            update_flight_status(flight)

        return {
            "success": True,
            "flight": flight,
            "message": f"Flight {flight.get('flight_no', flight['id'])} successfully reassigned to {target_gate['name']} ({target_gate['id']})."
        }

    elif req.resource_type == "crew":
        # Validate crew exists
        target_crew = next((c for c in STATE["crew"] if c["id"] == req.new_resource_id), None)
        if not target_crew:
            raise HTTPException(status_code=404, detail=f"Crew '{req.new_resource_id}' not found.")

        old_crew_id = flight.get("crew_id")
        flight["crew_id"] = req.new_resource_id

        # Update old crew
        if old_crew_id:
            for c in STATE["crew"]:
                if c["id"] == old_crew_id and c.get("current_flight_id") == flight["id"]:
                    c["current_flight_id"] = None

        flight_busy_until = conflict_engine.add_minutes(flight["est_time"], conflict_engine.TURNAROUND_BUFFER)
        target_crew["busy_until"] = max(target_crew.get("busy_until", "00:00"), flight_busy_until)

        active_conflicts = conflict_engine.check_conflicts(
            flight=flight,
            new_est_time=flight["est_time"],
            gates=STATE["gates"],
            crew=STATE["crew"],
            flights=STATE["flights"]
        )
        if not active_conflicts:
            update_flight_status(flight)

        return {
            "success": True,
            "flight": flight,
            "message": f"Flight {flight.get('flight_no', flight['id'])} successfully reassigned to {target_crew['name']} ({target_crew['id']})."
        }

    raise HTTPException(status_code=400, detail=f"Invalid resource_type '{req.resource_type}'.")


@app.post("/reset")
def post_reset():
    """Resets in-memory state back to pristine seed data."""
    global STATE
    STATE = seed_data.get_initial_data()
    return {"success": True, "message": "In-memory state reset to seed data."}


# -------------------------------------------------------------
# Static Frontend Serving
# -------------------------------------------------------------
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def serve_index():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Airport Operations API running. Static files not yet mounted."}
