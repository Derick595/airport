"""Read-only factory disruption analysis for the What-If Decision Lab."""

import json
from datetime import datetime

from backend.database import get_connection


VALID_SCENARIOS = {"machine_failure", "material_hold", "operator_absence"}


def analyze_what_if(scenario_type: str, resource_id: str):
    if scenario_type not in VALID_SCENARIOS:
        raise ValueError("Unknown what-if scenario")

    conn = get_connection()
    try:
        if scenario_type == "machine_failure":
            resource = conn.execute("SELECT id, name, status, current_run_id FROM machines WHERE id = ?", (resource_id,)).fetchone()
            if not resource:
                raise ValueError(f"Machine '{resource_id}' not found")
            runs = conn.execute("""
                SELECT id, order_number, product_name, status, target_qty, produced_qty, due_date,
                       machine_id, operator_id, required_material_lot_id
                FROM production_runs WHERE machine_id = ? AND status IN ('RUNNING', 'SCHEDULED', 'BLOCKED')
            """, (resource_id,)).fetchall()
            alternatives = [row["id"] for row in conn.execute("SELECT id FROM machines WHERE id != ? AND status = 'IDLE' AND current_run_id IS NULL ORDER BY id", (resource_id,))]
            title = f"Failure of {resource_id} - {resource['name']}"
            resource_kind = "Machine"
            response = ["Stop and isolate the machine", "Preserve active resource locks for incident review", "Evaluate compatible idle machines before rescheduling"]
        elif scenario_type == "material_hold":
            resource = conn.execute("SELECT lot_id, name, material_code, status FROM materials WHERE lot_id = ?", (resource_id,)).fetchone()
            if not resource:
                raise ValueError(f"Material lot '{resource_id}' not found")
            runs = conn.execute("""
                SELECT id, order_number, product_name, status, target_qty, produced_qty, due_date,
                       machine_id, operator_id, required_material_lot_id
                FROM production_runs WHERE required_material_lot_id = ? AND status IN ('RUNNING', 'SCHEDULED', 'BLOCKED')
            """, (resource_id,)).fetchall()
            alternatives = [row["lot_id"] for row in conn.execute("""
                SELECT lot_id FROM materials WHERE material_code = ? AND lot_id != ?
                  AND status = 'AVAILABLE' AND reserved_by_run_id IS NULL AND remaining_qty > 0
                ORDER BY remaining_qty DESC
            """, (resource["material_code"], resource_id))]
            title = f"Quality hold on {resource_id} - {resource['name']}"
            resource_kind = "Material"
            response = ["Freeze consumption from the selected lot", "Trace every unit already produced from the lot", "Validate an alternate lot before rerouting queued orders"]
        else:
            resource = conn.execute("SELECT id, name, status, active_run_id, certified_operations FROM operators WHERE id = ?", (resource_id,)).fetchone()
            if not resource:
                raise ValueError(f"Operator '{resource_id}' not found")
            runs = conn.execute("""
                SELECT id, order_number, product_name, status, target_qty, produced_qty, due_date,
                       machine_id, operator_id, required_material_lot_id
                FROM production_runs WHERE operator_id = ? AND status IN ('RUNNING', 'SCHEDULED', 'BLOCKED')
            """, (resource_id,)).fetchall()
            needed_machines = {row["machine_id"] for row in runs if row["machine_id"]}
            alternatives = []
            for row in conn.execute("SELECT id, certified_operations FROM operators WHERE id != ? AND status = 'AVAILABLE' AND active_run_id IS NULL ORDER BY id", (resource_id,)):
                certifications = set(json.loads(row["certified_operations"] or "[]"))
                if not needed_machines or certifications.intersection(needed_machines):
                    alternatives.append(row["id"])
            title = f"Unexpected absence of {resource_id} - {resource['name']}"
            resource_kind = "Operator"
            response = ["Pause the operator's active assignment", "Keep the machine and material reservation visible", "Assign a certified replacement before production resumes"]

        today = datetime.now()
        affected = []
        active_count = 0
        overdue_count = 0
        units_at_risk = 0
        for row in runs:
            item = dict(row)
            remaining = max(0, item["target_qty"] - item["produced_qty"])
            active = item["status"] == "RUNNING"
            try:
                overdue = datetime.fromisoformat(item["due_date"]) < today
            except (TypeError, ValueError):
                overdue = False
            active_count += int(active)
            overdue_count += int(overdue)
            units_at_risk += remaining
            affected.append({
                "run_id": item["id"], "order_number": item["order_number"],
                "product_name": item["product_name"], "status": item["status"],
                "remaining_units": remaining, "overdue": overdue,
            })

        no_alternative = bool(affected) and not alternatives
        risk_score = min(100, len(affected) * 20 + active_count * 30 + overdue_count * 15 + int(no_alternative) * 25)
        risk_level = "CRITICAL" if risk_score >= 75 else "HIGH" if risk_score >= 50 else "MEDIUM" if risk_score >= 25 else "LOW"
        estimated_delay_hours = active_count * 4 + max(0, len(affected) - active_count) * 2 + int(no_alternative) * 4

        return {
            "scenario_type": scenario_type,
            "resource_id": resource_id,
            "resource_kind": resource_kind,
            "title": title,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "affected_runs": affected,
            "affected_run_count": len(affected),
            "units_at_risk": units_at_risk,
            "estimated_delay_hours": estimated_delay_hours,
            "alternatives": alternatives,
            "recommended_response": response,
            "explanation": f"Score = {len(affected)} affected run(s) x 20 + {active_count} active x 30 + {overdue_count} overdue x 15" + (" + 25 because no alternative is available." if no_alternative else "."),
            "read_only": True,
        }
    finally:
        conn.close()
