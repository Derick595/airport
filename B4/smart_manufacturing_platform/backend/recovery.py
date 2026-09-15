"""Read-only material-hold recovery planning."""

import json
from datetime import datetime

from backend.database import get_connection


def plan_material_recovery(lot_id: str):
    conn = get_connection()
    try:
        lot = conn.execute("SELECT lot_id, material_code, status, hold_reason FROM materials WHERE lot_id = ?", (lot_id,)).fetchone()
        if not lot:
            raise ValueError(f"Material lot '{lot_id}' not found")
        if lot["status"] != "ON_HOLD":
            return {"lot_id": lot_id, "hold_reason": None, "affected_runs": []}

        today = datetime.now().date().isoformat()
        alternatives = [dict(row) for row in conn.execute("""
            SELECT lot_id, remaining_qty FROM materials
            WHERE material_code = ? AND lot_id != ? AND status = 'AVAILABLE'
              AND reserved_by_run_id IS NULL AND expiration_date >= ?
            ORDER BY remaining_qty DESC
        """, (lot["material_code"], lot_id, today))]
        machines = [dict(row) for row in conn.execute("SELECT id FROM machines WHERE status = 'IDLE' AND current_run_id IS NULL ORDER BY id")]
        operators = [dict(row) for row in conn.execute("""
            SELECT id, certified_operations FROM operators
            WHERE status = 'AVAILABLE' AND active_run_id IS NULL AND certification_expires >= ? ORDER BY id
        """, (today,))]
        affected = []
        for row in conn.execute("""
            SELECT id, order_number, status, target_qty, produced_qty, required_material_qty
            FROM production_runs
            WHERE required_material_lot_id = ? AND status IN ('SCHEDULED', 'BLOCKED')
            ORDER BY due_date, id
        """, (lot_id,)):
            run = dict(row)
            remaining_units = max(0, run["target_qty"] - run["produced_qty"])
            needed_qty = remaining_units * run["required_material_qty"]
            options = []
            if run["status"] == "SCHEDULED":
                for alt in alternatives:
                    if alt["remaining_qty"] < needed_qty:
                        continue
                    for machine in machines:
                        operator = next((op for op in operators if machine["id"] in json.loads(op["certified_operations"] or "[]")), None)
                        if operator:
                            options.append({"material_lot_id": alt["lot_id"], "machine_id": machine["id"], "operator_id": operator["id"], "available_qty": alt["remaining_qty"]})
            reason = None if options else ("Abort or resolve the blocked run before redispatch" if run["status"] == "BLOCKED" else "No certified, available machine/operator and matching lot with enough stock")
            affected.append({"run_id": run["id"], "order_number": run["order_number"], "status": run["status"], "remaining_units": remaining_units, "material_needed": needed_qty, "options": options, "reason": reason})
        return {"lot_id": lot_id, "hold_reason": lot["hold_reason"], "affected_runs": affected}
    finally:
        conn.close()
