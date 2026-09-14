# Autonomous Airport Operations API

## Run

```powershell
py -m pip install -r requirements.txt
py -m uvicorn main:app --reload
```

Open `http://127.0.0.1:8000/docs` for the interactive API.

## Guaranteed demo flow

1. `POST /delay` with `{ "flight_id": "AI101", "delay_minutes": 40 }`.
2. The response reports conflicts with `AI102` on `G1` and `C1`, and suggests moving `AI101` to `G3` plus crew `C3`.
3. `POST /reassign` with `{ "flight_id": "AI101", "resource_type": "gate", "new_resource_id": "G3" }`.
4. `POST /reassign` with `{ "flight_id": "AI101", "resource_type": "crew", "new_resource_id": "C3" }`.

`delay_minutes` is always calculated from `sched_time`, so resending the same request cannot compound the delay.
