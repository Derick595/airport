import unittest
import os
import json
import tempfile
import asyncio
import backend.database as database
from datetime import datetime

from backend.database import init_db, get_connection, DB_PATH
from backend.lock_manager import LockManager, ResourceConflictException
from backend.traceability import TraceabilityEngine
from backend.anomaly_detector import AnomalyDetector
from backend.simulator import FactorySimulator
from backend.recovery import plan_material_recovery
from backend.what_if import analyze_what_if

class SmartManufacturingPlatformTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Never delete the application's working database during a test run.
        cls._original_db_path = database.DB_PATH
        cls._temp_dir = tempfile.TemporaryDirectory()
        database.DB_PATH = os.path.join(cls._temp_dir.name, "factory.db")
        init_db()

    @classmethod
    def tearDownClass(cls):
        database.DB_PATH = cls._original_db_path
        cls._temp_dir.cleanup()

    def test_01_prevent_machine_double_booking(self):
        """
        Verify that a machine currently running a job cannot be booked by another run.
        """
        # CNC-01 is seeded as RUNNING for RUN-2026-001
        with self.assertRaises(ResourceConflictException) as ctx:
            LockManager.allocate_and_lock(
                run_id="RUN-2026-003",
                machine_id="CNC-01",
                operator_id="OP-103",
                material_lot_id="LOT-RESIN-205"
            )
        self.assertEqual(ctx.exception.conflict_type, "MACHINE_DOUBLE_BOOKED")
        self.assertIn("already double-booked", str(ctx.exception))

    def test_02_prevent_operator_double_booking(self):
        """
        Verify that an operator currently assigned cannot be double-booked to another machine.
        """
        # OP-101 is seeded as ASSIGNED to CNC-01
        with self.assertRaises(ResourceConflictException) as ctx:
            LockManager.allocate_and_lock(
                run_id="RUN-2026-003",
                machine_id="LSW-04",
                operator_id="OP-101",
                material_lot_id="LOT-RESIN-205"
            )
        self.assertEqual(ctx.exception.conflict_type, "OPERATOR_DOUBLE_BOOKED")
        self.assertIn("busy on Machine", str(ctx.exception))

    def test_03_prevent_material_on_hold_booking(self):
        """
        Verify that a material lot on hold immediately blocks booking and triggers alert.
        """
        # Put LOT-RESIN-204 ON HOLD
        hold_result = LockManager.set_material_hold(
            "LOT-RESIN-204", 
            "Incoming quality check: viscosity index out of spec"
        )
        self.assertTrue(hold_result["success"])

        # Attempt to allocate LOT-RESIN-204
        with self.assertRaises(ResourceConflictException) as ctx:
            LockManager.allocate_and_lock(
                run_id="RUN-2026-003",
                machine_id="INJ-03",
                operator_id="OP-103",
                material_lot_id="LOT-RESIN-204"
            )
        self.assertEqual(ctx.exception.conflict_type, "MATERIAL_ON_HOLD")
        self.assertIn("Lot is ON HOLD", str(ctx.exception))

    def test_04_successful_atomic_allocation_and_release(self):
        """
        Verify valid resource allocation succeeds atomically and releases cleanly.
        """
        # INJ-03 is IDLE, OP-103 is AVAILABLE, LOT-RESIN-205 is AVAILABLE
        alloc_res = LockManager.allocate_and_lock(
            run_id="RUN-2026-003",
            machine_id="INJ-03",
            operator_id="OP-103",
            material_lot_id="LOT-RESIN-205",
            required_qty=2.0
        )
        self.assertTrue(alloc_res["success"])

        # Verify DB states
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT status, current_run_id FROM machines WHERE id = 'INJ-03'")
        mach = cursor.fetchone()
        self.assertEqual(mach["status"], "RUNNING")
        self.assertEqual(mach["current_run_id"], "RUN-2026-003")

        cursor.execute("SELECT status, active_run_id FROM operators WHERE id = 'OP-103'")
        op = cursor.fetchone()
        self.assertEqual(op["status"], "ASSIGNED")

        cursor.execute("SELECT status, reserved_by_run_id FROM materials WHERE lot_id = 'LOT-RESIN-205'")
        mat = cursor.fetchone()
        self.assertEqual(mat["status"], "IN_USE")
        self.assertEqual(mat["reserved_by_run_id"], "RUN-2026-003")
        conn.close()

        # Now release
        rel_res = LockManager.release_locks("RUN-2026-003", "COMPLETED")
        self.assertTrue(rel_res["success"])

        # Verify release states
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT status, current_run_id FROM machines WHERE id = 'INJ-03'")
        mach = cursor.fetchone()
        self.assertEqual(mach["status"], "IDLE")
        self.assertIsNone(mach["current_run_id"])
        conn.close()

    def test_05_digital_thread_unit_story(self):
        """
        Verify that a serialized unit can tell its complete lifecycle story.
        """
        story = TraceabilityEngine.get_unit_story("SN-VALVE-2026-1017")
        self.assertEqual(story["serial_number"], "SN-VALVE-2026-1017")
        self.assertEqual(story["qc_status"], "DEFECTIVE")
        self.assertEqual(story["defect_code"], "ERR-CHIP-BURR")
        self.assertEqual(story["machine"]["id"], "CNC-01")
        self.assertEqual(story["operator"]["id"], "OP-101")
        self.assertEqual(story["material"]["lot_id"], "LOT-ALU-101")
        self.assertGreater(len(story["story_timeline"]), 3)

    def test_06_forward_traceability(self):
        """
        Verify forward traceability from material lot to all manufactured serialized units.
        """
        trace = TraceabilityEngine.trace_material_forward("LOT-ALU-101")
        self.assertEqual(trace["lot_id"], "LOT-ALU-101")
        self.assertGreater(trace["total_units_produced"], 20)
        self.assertIn("SN-VALVE-2026-1017", [u["serial_number"] for u in trace["serialized_units"]])
        self.assertIn("quarantine_scope", trace)

    def test_07_root_cause_analysis_patient_zero(self):
        """
        Verify root-cause analysis identifies Patient Zero and factors with confidence.
        """
        rca = TraceabilityEngine.root_cause_investigation()
        self.assertIsNotNone(rca["patient_zero_unit"])
        self.assertEqual(rca["patient_zero_unit"]["serial_number"], "SN-VALVE-2026-1017")
        self.assertEqual(rca["patient_zero_unit"]["machine_id"], "CNC-01")
        self.assertGreater(rca["confidence_pct"], 70.0)

    def test_08_predictive_spc_drift_detection(self):
        """
        Verify SPC drift rule surfaces a developing vibration problem before trip limit.
        """
        # Feed 6 consecutive increasing vibration values strictly below warning threshold (4.0)
        vibrations = [1.2, 1.45, 1.70, 1.95, 2.20, 2.45, 2.70]
        alerts = []
        for v in vibrations:
            a = AnomalyDetector.evaluate_machine_telemetry("LSW-04", 40.0, v, 30.0, 6.5)
            if a:
                alerts.extend(a)

        # Check if predictive drift alert was generated
        drift_alerts = [al for al in alerts if "ALT-SPC-DRIFT" in al["id"]]
        self.assertGreater(len(drift_alerts), 0)
        self.assertIn("Predictive Warning", drift_alerts[0]["title"])

    def test_09_terminal_run_cannot_be_dispatched_again(self):
        with self.assertRaises(ResourceConflictException) as ctx:
            LockManager.allocate_and_lock("RUN-2026-003", "INJ-03", "OP-103", "LOT-RESIN-205")
        self.assertEqual(ctx.exception.conflict_type, "RUN_NOT_DISPATCHABLE")

    def test_10_hold_survives_allocation_release(self):
        # An already-running lot can be held; ending its run must not clear QA's hold.
        LockManager.set_material_hold("LOT-ALU-101", "QA retest")
        LockManager.release_locks("RUN-2026-001", "ABORTED")
        conn = get_connection()
        try:
            lot = conn.execute("SELECT status, reserved_by_run_id FROM materials WHERE lot_id = 'LOT-ALU-101'").fetchone()
            self.assertEqual(lot["status"], "ON_HOLD")
            self.assertIsNone(lot["reserved_by_run_id"])
        finally:
            conn.close()

    def test_11_release_hold_preserves_active_reservation(self):
        LockManager.set_material_hold("LOT-PCB-305", "QA retest")
        result = LockManager.release_material_hold("LOT-PCB-305")
        self.assertEqual(result["status"], "IN_USE")
        conn = get_connection()
        try:
            lot = conn.execute("SELECT status, reserved_by_run_id FROM materials WHERE lot_id = 'LOT-PCB-305'").fetchone()
            self.assertEqual(lot["reserved_by_run_id"], "RUN-2026-002")
        finally:
            conn.close()

    def test_12_simulator_stops_before_consuming_unavailable_material(self):
        conn = get_connection()
        try:
            before = conn.execute("SELECT produced_qty FROM production_runs WHERE id = 'RUN-2026-002'").fetchone()[0]
            conn.execute("UPDATE materials SET remaining_qty = 0 WHERE lot_id = 'LOT-PCB-305'")
            conn.execute("UPDATE materials SET status = 'IN_USE' WHERE lot_id = 'LOT-PCB-305'")
            conn.execute("UPDATE production_runs SET status = 'RUNNING' WHERE id = 'RUN-2026-002'")
            conn.execute("UPDATE machines SET status = 'RUNNING', current_run_id = 'RUN-2026-002' WHERE id = 'SMT-02'")
            conn.commit()
        finally:
            conn.close()

        asyncio.run(FactorySimulator().tick())
        conn = get_connection()
        try:
            run = conn.execute("SELECT status, produced_qty FROM production_runs WHERE id = 'RUN-2026-002'").fetchone()
            self.assertEqual(run["status"], "BLOCKED")
            self.assertEqual(run["produced_qty"], before)
        finally:
            conn.close()

    def test_13_recovery_plan_finds_compatible_batch_and_resources(self):
        plan = plan_material_recovery("LOT-RESIN-204")
        run = next(r for r in plan["affected_runs"] if r["run_id"] == "RUN-2026-004")
        self.assertTrue(run["options"])
        option = run["options"][0]
        self.assertEqual(option["material_lot_id"], "LOT-RESIN-205")
        self.assertGreaterEqual(option["available_qty"], run["material_needed"])

    def test_14_recovery_plan_rejects_insufficient_batch(self):
        conn = get_connection()
        try:
            conn.execute("UPDATE materials SET remaining_qty = 0 WHERE lot_id = 'LOT-RESIN-205'")
            conn.commit()
        finally:
            conn.close()
        plan = plan_material_recovery("LOT-RESIN-204")
        self.assertTrue(all(not run["options"] for run in plan["affected_runs"]))

    def test_15_simulator_can_pause_and_resume(self):
        async def exercise():
            simulator = FactorySimulator()
            simulator.start()
            self.assertTrue(simulator.is_running)
            simulator.stop()
            self.assertFalse(simulator.is_running)
            simulator.start()
            self.assertTrue(simulator.is_running)
            simulator.stop()

        asyncio.run(exercise())

    def test_16_machine_fault_and_shortage_scenarios(self):
        original_path = database.DB_PATH
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                database.DB_PATH = os.path.join(temp_dir, "scenario.db")
                init_db()
                simulator = FactorySimulator()
                fault = simulator.trigger_machine_fault_scenario()
                shortage = simulator.trigger_material_shortage_scenario()

                conn = get_connection()
                try:
                    cnc = conn.execute("SELECT status FROM machines WHERE id = 'CNC-01'").fetchone()
                    smt = conn.execute("SELECT status FROM machines WHERE id = 'SMT-02'").fetchone()
                    run1 = conn.execute("SELECT status FROM production_runs WHERE id = 'RUN-2026-001'").fetchone()
                    run2 = conn.execute("SELECT status FROM production_runs WHERE id = 'RUN-2026-002'").fetchone()
                    stock = conn.execute("SELECT status, remaining_qty FROM materials WHERE lot_id = 'LOT-PCB-305'").fetchone()
                    locks = conn.execute("SELECT COUNT(*) FROM resource_locks WHERE run_id IN ('RUN-2026-001', 'RUN-2026-002') AND lock_status = 'HELD'").fetchone()[0]
                    alerts = conn.execute("SELECT COUNT(*) FROM alerts WHERE id IN (?, ?) AND status = 'ACTIVE'", (fault["alert_id"], shortage["alert_id"])).fetchone()[0]
                    self.assertEqual((cnc["status"], smt["status"]), ("MAINTENANCE", "BLOCKED"))
                    self.assertEqual((run1["status"], run2["status"]), ("BLOCKED", "BLOCKED"))
                    self.assertEqual((stock["status"], stock["remaining_qty"]), ("DEPLETED", 0))
                    self.assertEqual(locks, 6)
                    self.assertEqual(alerts, 2)
                finally:
                    conn.close()
                LockManager.release_locks("RUN-2026-001", "ABORTED")
                conn = get_connection()
                try:
                    machine = conn.execute("SELECT status, current_run_id FROM machines WHERE id = 'CNC-01'").fetchone()
                    self.assertEqual(machine["status"], "MAINTENANCE")
                    self.assertIsNone(machine["current_run_id"])
                finally:
                    conn.close()
        finally:
            database.DB_PATH = original_path

    def test_17_what_if_lab_is_read_only_and_explainable(self):
        original_path = database.DB_PATH
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                database.DB_PATH = os.path.join(temp_dir, "what_if.db")
                init_db()
                conn = get_connection()
                try:
                    before = [tuple(row) for row in conn.execute("SELECT id, status, current_run_id FROM machines ORDER BY id")]
                finally:
                    conn.close()

                machine = analyze_what_if("machine_failure", "CNC-01")
                material = analyze_what_if("material_hold", "LOT-RESIN-204")
                operator = analyze_what_if("operator_absence", "OP-101")

                self.assertGreater(machine["risk_score"], 0)
                self.assertEqual(machine["affected_run_count"], 1)
                self.assertIn("LOT-RESIN-205", material["alternatives"])
                self.assertTrue(operator["recommended_response"])
                self.assertTrue(all(result["read_only"] for result in (machine, material, operator)))

                conn = get_connection()
                try:
                    after = [tuple(row) for row in conn.execute("SELECT id, status, current_run_id FROM machines ORDER BY id")]
                finally:
                    conn.close()
                self.assertEqual(before, after)
        finally:
            database.DB_PATH = original_path

if __name__ == "__main__":
    unittest.main()
