"""Conflict detection for the airport-operations demo.

The functions in this module deliberately use only the project's in-memory
dictionary shape.  They do not mutate flights, gates, or crew, so FastAPI can
call them before applying a proposed delay or reassignment.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Iterable, Mapping


DEFAULT_TURNAROUND_MINUTES = 45


def check_conflicts(
    flight: Mapping[str, Any],
    delay_minutes: int,
    gates: Iterable[Mapping[str, Any]] | Mapping[Any, Mapping[str, Any]],
    crew: Iterable[Mapping[str, Any]] | Mapping[Any, Mapping[str, Any]],
    flights: Iterable[Mapping[str, Any]] | Mapping[Any, Mapping[str, Any]],
    turnaround_buffer: int = DEFAULT_TURNAROUND_MINUTES,
) -> list[dict[str, Any]]:
    """Return gate/crew conflicts caused by delaying ``flight``.

    ``flight['est_time']`` is treated as the estimate *before* this delay.
    Therefore the API should call this function before persisting the delay.
    If the API has already changed ``est_time``, pass ``delay_minutes=0``.

    A conflict occurs when the delayed flight's resource occupancy end
    (new estimated time + turnaround buffer) is later than the next flight's
    scheduled time on the same resource.
    """
    if delay_minutes < 0:
        raise ValueError("delay_minutes must be zero or greater")

    all_flights = _as_list(flights)
    delayed_end = _time(flight["est_time"]) + timedelta(
        minutes=delay_minutes + turnaround_buffer
    )
    conflicts: list[dict[str, Any]] = []

    for resource_type, collection, id_field in (
        ("gate", gates, "gate_id"),
        ("crew", crew, "crew_id"),
    ):
        resource_id = flight.get(id_field)
        if resource_id is None:
            continue

        next_flight = _next_flight_using(
            all_flights, flight["id"], id_field, resource_id, _time(flight["sched_time"])
        )
        if next_flight is not None and delayed_end > _time(next_flight["sched_time"]):
            resource = _by_id(_as_list(collection), resource_id)
            conflicts.append(
                {
                    "type": resource_type,
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "resource_name": resource.get("name") if resource else None,
                    "flight_id": flight["id"],
                    "flight_no": flight.get("flight_no"),
                    "next_flight_id": next_flight["id"],
                    "next_flight_no": next_flight.get("flight_no"),
                    "next_flight_sched_time": next_flight["sched_time"],
                    "delayed_resource_free_at": _format_like(flight["est_time"], delayed_end),
                    "message": (
                        f"{resource_type.title()} {resource.get('name', resource_id) if resource else resource_id} "
                        f"is needed by {next_flight.get('flight_no', next_flight['id'])} before "
                        f"{flight.get('flight_no', flight['id'])} clears it."
                    ),
                }
            )
    return conflicts


def suggest_fix(
    conflict: Mapping[str, Any],
    available_gates: Iterable[Mapping[str, Any]] | Mapping[Any, Mapping[str, Any]],
    available_crew: Iterable[Mapping[str, Any]] | Mapping[Any, Mapping[str, Any]],
    flights: Iterable[Mapping[str, Any]] | Mapping[Any, Mapping[str, Any]] | None = None,
    turnaround_buffer: int = DEFAULT_TURNAROUND_MINUTES,
) -> dict[str, Any]:
    """Find the first resource that can take the delayed flight.

    Return shape is API-ready: either a reassign suggestion or
    ``{'no_solution': True}``.  ``flights`` is optional for compatibility with
    the original four-argument handoff; when provided it prevents suggestions
    that overlap another scheduled flight.
    """
    resource_type = conflict.get("resource_type", conflict.get("type"))
    if resource_type not in {"gate", "crew"}:
        raise ValueError("conflict must have resource_type 'gate' or 'crew'")

    candidates = _as_list(available_gates if resource_type == "gate" else available_crew)
    target_id = conflict.get("flight_id")
    start = _time(conflict["delayed_resource_free_at"]) - timedelta(minutes=turnaround_buffer)
    end = _time(conflict["delayed_resource_free_at"])
    id_field = "gate_id" if resource_type == "gate" else "crew_id"
    all_flights = _as_list(flights) if flights is not None else []

    for candidate in candidates:
        if candidate.get("id") == conflict.get("resource_id"):
            continue
        if candidate.get("busy_until") and _time(candidate["busy_until"]) > start:
            continue
        if _has_schedule_overlap(all_flights, target_id, id_field, candidate.get("id"), start, end):
            continue
        return {
            "no_solution": False,
            "action": "reassign",
            "flight_id": target_id,
            "resource_type": resource_type,
            "new_resource_id": candidate["id"],
            "new_resource_name": candidate.get("name"),
            "reason": f"{candidate.get('name', candidate['id'])} is available for the delayed flight.",
        }

    return {
        "no_solution": True,
        "flight_id": target_id,
        "resource_type": resource_type,
        "reason": f"No available {resource_type} can be assigned automatically.",
    }


def build_suggestion(
    conflicts: Iterable[Mapping[str, Any]],
    gates: Iterable[Mapping[str, Any]] | Mapping[Any, Mapping[str, Any]],
    crew: Iterable[Mapping[str, Any]] | Mapping[Any, Mapping[str, Any]],
    flights: Iterable[Mapping[str, Any]] | Mapping[Any, Mapping[str, Any]],
) -> dict[str, Any]:
    """Return the first usable fix, or the no-solution result for the first conflict."""
    for conflict in conflicts:
        suggestion = suggest_fix(conflict, gates, crew, flights)
        if not suggestion["no_solution"]:
            return suggestion
    return {"no_solution": False, "action": None, "reason": "No conflicts detected."}


def _next_flight_using(flights, current_id, id_field, resource_id, current_scheduled):
    later = [
        item for item in flights
        if item.get("id") != current_id
        and item.get(id_field) == resource_id
        and _time(item["sched_time"]) >= current_scheduled
    ]
    return min(later, key=lambda item: _time(item["sched_time"]), default=None)


def _has_schedule_overlap(flights, target_id, id_field, resource_id, start, end):
    for item in flights:
        if item.get("id") == target_id or item.get(id_field) != resource_id:
            continue
        item_start = _time(item.get("est_time", item["sched_time"]))
        item_end = item_start + timedelta(minutes=DEFAULT_TURNAROUND_MINUTES)
        if start < item_end and end > item_start:
            return True
    return False


def _as_list(items):
    return list(items.values()) if isinstance(items, Mapping) else list(items)


def _by_id(items, resource_id):
    return next((item for item in items if item.get("id") == resource_id), None)


def _time(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        for parser in (datetime.fromisoformat, lambda text: datetime.strptime(text, "%H:%M")):
            try:
                return parser(value.replace("Z", "+00:00"))
            except ValueError:
                pass
    raise ValueError(f"Unsupported time value: {value!r}; use ISO-8601 or HH:MM")


def _format_like(original: Any, value: datetime) -> str:
    return value.strftime("%H:%M") if isinstance(original, str) and len(original) == 5 else value.isoformat()
