# ✈️ SkyResolve - Airport Operations Conflict Resolver

A high-velocity, integration-first airport operations dashboard and rule-based conflict resolution engine engineered for a 2-hour hackathon build.

Built with **FastAPI**, in-memory state, pure Python deterministic conflict detection, and a high-contrast dark ops room dashboard in vanilla HTML5/CSS3/JavaScript.

---

## 👥 Hackathon Team Roles & Architecture

| Role | Domain | Responsibilities & Artifacts |
|---|---|---|
| **Person 1** | Frontend UI | Single-page operations dashboard (`static/index.html`, `style.css`, `app.js`) with color-coded flight rows, real-time KPI stats, conflict alert cards with Approve/Reject buttons, and auto-sync. |
| **Person 2** | Backend API | FastAPI application (`main.py`) with in-memory state, CORS enabled, and endpoints for `/flights`, `/gates`, `/crew`, `/delay`, `/reassign`, and `/reset`. |
| **Person 3** | Conflict Logic | Pure Python conflict engine (`conflict_engine.py`) implementing turnaround buffer overlaps, linear-scan resource search, and safe `no_solution` fallbacks. |
| **Person 4** | Seed Data & Demo | Pre-calibrated 12-flight schedule (`seed_data.py`), test suite (`test_engine.py`), and the 3-scenario presentation guide (`demo_script.md`). |

---

## 🚀 Quick Start

### 1. Requirements & Setup
Ensure Python 3.10+ is installed.

```powershell
# Create virtual environment and install dependencies
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

### 2. Run the Server
```powershell
.venv\Scripts\uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in any modern browser.

### 3. Run Automated Tests
```powershell
.venv\Scripts\pytest test_engine.py -v
```

---

## 📡 API Contract

### Resource Endpoints
- `GET /flights`: Lists all flights with current status (`ON_TIME`, `DELAYED`, `CRITICAL`), assigned gate, and crew.
- `GET /gates`: Lists airport gates (G1 through G5) with current occupancy and `busy_until` timestamps.
- `GET /crew`: Lists flight crew rotations (C1 through C4) with active flight assignments.

### Operational Endpoints
- `POST /delay`:
  - **Payload**: `{"flight_id": "FL101", "delay_minutes": 45}`
  - **Response**: `{ "flight": {...}, "conflicts": [...], "suggestion": {...} }`
  - Evaluates turnaround buffer overlaps (30m buffer) and automatically calculates the optimal resource reassignment.
- `POST /reassign`:
  - **Payload**: `{"flight_id": "FL104", "resource_type": "gate", "new_resource_id": "G2"}`
  - **Response**: `{ "success": true, "flight": {...}, "message": "..." }`
  - Applies approved remediation and syncs gate/crew occupancy.
- `POST /reset`:
  - Restores all flights, gates, and crews to pristine seed state in < 100ms.

---

## 🎭 3-Scenario Demo Guide

See [demo_script.md](file:///c:/Users/calvi/Documents/Adapthon/demo_script.md) for the complete presenter narration.

1. **Scenario 1 (Gate Conflict)**: Delay `AA101` (`FL101`) by 45m. Gate A1 becomes blocked for downstream departure `AA104`. SkyResolve detects the conflict and suggests reassigning `AA104` to `Gate A2`. Click **"Approve Reassignment"** to solve in 1 click.
2. **Scenario 2 (Crew Conflict)**: Delay `UA302` (`FL102`) by 50m. Flight Crew Bravo cannot make flight `UA306`. SkyResolve suggests dispatching standby Crew Charlie. Click **"Approve Reassignment"**.
3. **Scenario 3 (Peak Capacity Overload)**: Delay `BA707` (`FL107`) by 25m during the 16:55 rush hour when all 5 gates are occupied. The engine flags `no_solution: true` and the UI alerts dispatchers that **Manual Intervention / Ground Hold** is required.
