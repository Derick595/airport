# 🎯 2-Hour Hackathon Demo Script: Airport Operations Conflict Resolver

> **Presenter Role (Person 4 / Team)**: This script provides the exact narrative, mouse actions, and terminal commands to deliver a flawless, high-impact 3-minute hackathon pitch.

---

## ⚡ 1. Pre-Flight Setup (30 Seconds Before Presenting)

1. **Start the backend server**:
   ```powershell
   .venv\Scripts\uvicorn main:app --host 127.0.0.1 --port 8000
   ```
2. **Open the browser**:
   Navigate to [http://127.0.0.1:8000](http://127.0.0.1:8000).
3. **Verify clean state**:
   - Total Flights: `12`
   - On Time: `12` (all green)
   - Active Alerts: None
   - Gates: 5 active, Crew: 4 active
   *(Tip: You can click **"Reset Seed Data"** in the top-right nav anytime to return to this pristine state!)*

---

## 🎤 2. Pitch Narrative & Live Walkthrough

### Introduction (15s)
> *"Judges, in commercial airport operations, a single inbound delay triggers catastrophic domino effects: delayed planes block gates, grounding downstream departures, stranding flight crews, and costing airlines millions. Today, our 4-person team built SkyResolve — a zero-database, rule-based conflict detection engine with real-time AI remediation built within a strict 2-hour hackathon scope."*

---

### Scenario 1: Gate Contention & Automated Reassignment (45s)
**The Problem**: Flight AA101 suffers a 45-minute ground delay, overstaying at Gate A1.

1. **In the UI Delay Simulator**:
   - Select Target Flight: `AA101 (14:00) - Gate G1` (or click `+45m` directly in the table row).
   - Click **"Simulate Delay & Check Conflicts"**.
2. **Show the Audience**:
   - Flight `AA101` turns red (`CRITICAL`), est. time updates to `14:45`.
   - The **Active Operational Conflicts** banner instantly slides in.
   - **Conflict Explanation**: *Flight AA101 delay pushes Gate A1 occupancy to 15:15, overlapping Flight AA104 (scheduled at 14:45).*
   - **AI Recommendation**: *Reassign Flight AA104 to Gate A2 (free from 14:45 - 15:15).*
3. **The Fix**:
   - Click the green **"✓ Approve Reassignment"** button.
   - Notice the table instantly reflects `AA104` moving to `Gate A2` (`G2`).
   - The conflict alert clears, and system returns to green/yellow status!

---

### Scenario 2: Crew Domino Effect & Standby Dispatch (45s)
**The Problem**: Flight UA302 is delayed by 50 minutes. Flight Crew Bravo was scheduled to pilot downstream flight UA306.

1. **In the UI Delay Simulator**:
   - Select Target Flight: `UA302 (14:15) - Gate G2`.
   - Set Delay: `50` minutes (or click `+45m` and bump to `50`).
   - Click **"Simulate Delay & Check Conflicts"**.
2. **Show the Audience**:
   - `UA302` is delayed to `15:05`, keeping Crew Bravo busy until `15:35`.
   - Alert appears: *Crew Bravo cannot make Flight UA306 scheduled at 15:15!*
   - Engine automatically searches available crews and recommends:
     *Reassign Flight UA306 to Flight Crew Charlie (on standby).*
3. **The Fix**:
   - Click **"✓ Approve Reassignment"**.
   - Crew roster syncs and conflict is instantly mitigated.

---

### Scenario 3: Peak Capacity Crunch & Safe Fallback (45s)
**The Edge Case**: What happens during peak rush hour when *every single gate* is occupied? Instead of crashing or hallucinating an impossible gate, the system cleanly triggers manual intervention.

1. **In the UI Delay Simulator**:
   - Select Target Flight: `BA707 (16:30) - Gate G1`.
   - Set Delay: `25` minutes (est. time becomes `16:55`).
   - Click **"Simulate Delay & Check Conflicts"**.
2. **Show the Audience**:
   - At 16:55, downstream flight `QF112` on Gate G1 is blocked.
   - But looking across the airport:
     - Gate G1: Busy with BA707
     - Gate G2: Busy with AF808
     - Gate G3: Busy with LH909
     - Gate G4: Busy with DL410
     - Gate G5: Busy with UA311
   - Engine detects `no_solution: true`.
   - The alert card displays:
     **🚨 Manual Intervention Needed**: *All 5 gates are occupied during turnaround window (16:55 - 17:25). Manual intervention / ground hold required.*
3. **Key Takeaway for Judges**:
   > *"Notice how SkyResolve fails safely — alerting dispatchers to hold the aircraft on taxiway rather than double-booking passengers onto a phantom gate."*

---

### Resetting for Q&A (5s)
Click **"Reset Seed Data"** in the top navigation bar.
Show how the entire system returns to pristine initial state in < 100ms.

---

## 🛠️ 3. Direct API / CLI Demonstration (Cheat Sheet)

If judges or technical mentors ask to see the API endpoints directly:

```bash
# 1. Fetch all flights
curl http://127.0.0.1:8000/flights

# 2. Simulate delay on FL101
curl -X POST http://127.0.0.1:8000/delay \
  -H "Content-Type: application/json" \
  -d '{"flight_id": "FL101", "delay_minutes": 45}'

# 3. Apply the reassignment fix
curl -X POST http://127.0.0.1:8000/reassign \
  -H "Content-Type: application/json" \
  -d '{"flight_id": "FL104", "resource_type": "gate", "new_resource_id": "G2"}'

# 4. Instant reset
curl -X POST http://127.0.0.1:8000/reset
```
