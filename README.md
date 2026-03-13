# Serendib Dome

Serendib Dome is a real-time air-defence simulation written in Python with `pygame`.
It visualizes incoming ballistic missiles, radar tracking, trajectory prediction,
counter-missile launches, interception attempts, and battle statistics in a dual-view UI.

The project runs in two modes:

- **Desktop mode** — native Python + `pygame`
- **Web mode** — compiled to WebAssembly with `pygbag`, then served as a static site

---

## Overview

The simulation models a defended base at the origin.

1. Incoming missiles spawn from the outer edge of the world.
2. A rotating radar sweeps and records detections.
3. Once enough detections are collected, the predictor estimates:
     - the future trajectory,
     - the ground impact point,
     - a reachable intercept point.
4. The dome auto-launches interceptors.
5. Interceptors lock onto their assigned target and attempt a proximity kill.
6. All important events and motion samples are logged to CSV for later plotting.

---

## Current Feature Set

### Simulation

- Ballistic incoming missiles with gravity-based vertical motion
- Auto-spawning threats from random directions
- Adjustable maximum simultaneous incoming missile count from the HUD
- Runtime speed control for slow-motion or accelerated testing
- Automatic interceptor launches with per-target cooldown control
- Target lock after intercept point generation
- Kill / miss / breach scoring

### Radar + Prediction

- 360° rotating radar sweep
- Detection history stored per missile
- Polynomial trajectory fit using `numpy.polyfit`
- Predicted future path rendering
- Predicted impact point rendering
- **Locked** intercept point once first valid intercept is computed

### UI / Visualization

- 3D battlefield view on the left
- 2D radar panel on the right
- Compact HUD with:
    - simulation speed,
    - threat list,
    - score block,
    - time,
    - incoming salvo control,
    - pause status
- Lock indicators for interceptors / targets
- Predicted path and intercept markers

### Data Logging

Every run writes CSV files into `logs/`:

- `events_YYYYMMDD_HHMMSS.csv`
- `trajectory_YYYYMMDD_HHMMSS.csv`

These files are intended for later graphing with pandas / matplotlib / Excel / BI tools.

---

## Technology Stack

- **Python 3.12**
- **pygame** — rendering and input
- **numpy** — vectors and polynomial fitting
- **pygbag** — WebAssembly/web packaging
- **Vercel** — static hosting of prebuilt `web-build/`

No `scikit-learn` is required.

---

## Project Structure

```text
serendib-dome/
├── main.py                  # Async entry point for desktop + web
├── run.sh                   # Desktop launcher
├── build_web.sh             # Local WASM bundle builder
├── vercel.json              # Static deployment config for Vercel
├── pygbag.ini               # pygbag project config
├── requirements.txt         # Python dependencies
├── web-build/               # Prebuilt static web bundle served by Vercel
├── logs/                    # Generated CSV logs from simulation runs
├── game/
│   ├── constants.py         # Tunable simulation constants
│   ├── missile.py           # Incoming missile physics
│   ├── interceptor.py       # Counter-missile target lock logic
│   ├── radar.py             # Rotating radar detection system
│   ├── predictor.py         # Trajectory / impact / intercept prediction
│   ├── simulation.py        # Main simulation state and orchestration
│   └── datalogger.py        # CSV event + trajectory logging
└── renderer/
    ├── camera.py            # Orbit camera controls
    └── renderer.py          # 3D view, radar, HUD drawing
```

---

## Installation

### Option A — use the helper script

```bash
./run.sh
```

This creates `.venv` if needed and runs the app.

### Option B — manual setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

---

## Running the Simulation

### Desktop

```bash
./run.sh
```

or

```bash
source .venv/bin/activate
python main.py
```

### Web build preview

```bash
./build_web.sh --serve
```

This rebuilds `web-build/` and starts a local static server.

---

## Controls

### Keyboard

| Key | Action |
|---|---|
| `SPACE` | Pause / resume |
| `[` | Slow down simulation |
| `]` | Speed up simulation |
| `L` | Manually launch interceptor at nearest tracked missile |
| `R` | Reset simulation and start a fresh log run |
| `Q` / `ESC` | Quit desktop application |

### Mouse

| Input | Action |
|---|---|
| Left-drag in 3D area | Orbit camera |
| Mouse wheel | Zoom in / out |
| Left-click HUD `- / +` | Decrease / increase max incoming salvo |

---

## HUD Guide

The HUD is split into two columns so all information fits in the available space.

### Left column

- Mission status
- Current simulation speed
- Auto-interceptor status
- Number of interceptors in flight
- Live threat table with per-missile:
    - ID
    - speed
    - range
    - altitude
    - detection/tracking state

### Right column

- Kills
- Breaches
- Score
- Real time / sim time
- Incoming salvo control (`1` to `10`)
- Pause banner when paused

---

## Radar / Prediction Logic

Each incoming missile stores radar detections over time.

Once at least 4 detections are available, the predictor:

1. Fits degree-2 polynomials to `x(t)`, `y(t)`, and `z(t)`.
2. Generates a predicted future path.
3. Finds the predicted ground impact point.
4. Finds a reachable intercept point based on interceptor speed.
5. Locks that intercept point once first computed.

The blue intercept marker is intentionally **locked**, not continuously moved.

---

## Interceptor Logic

Interceptors are launched from the base and assigned to a specific incoming missile.

Current behavior:

- launch occurs only after a valid intercept point exists,
- interceptors immediately lock to their target,
- they steer using the target's live position,
- they detonate on proximity kill distance,
- misses are detected and logged,
- relaunches can occur after cooldown if the target is still alive.

There can be multiple active incoming missiles, and the dome can engage multiple targets at once.

---

## Adjustable Incoming Salvo Size

The HUD contains a manual control to set how many incoming missiles can be active simultaneously.

- Minimum: `1`
- Maximum: `10`

This is useful for testing dome capability under different threat saturation levels.

---

## CSV Logging

Every simulation run creates two files in `logs/`.

### 1. Events CSV

Example file:

```text
logs/events_20260312_165526.csv
```

Contains discrete events such as:

- `MISSILE_SPAWN`
- `RADAR_DETECT`
- `TRACKED`
- `INTERCEPT_LOCKED`
- `INTERCEPTOR_LAUNCH`
- `KILL`
- `INTERCEPTOR_MISS`
- `BREACH`
- `GROUND_IMPACT`

Columns:

```text
run_id, real_time, sim_time, event,
obj_type, obj_id, x_km, y_km, z_km, speed_ms,
ref_type, ref_id, notes
```

### 2. Trajectory CSV

Example file:

```text
logs/trajectory_20260312_165526.csv
```

Contains position samples every `0.5` real-seconds for all live missiles and interceptors.

Columns:

```text
run_id, real_time, sim_time,
obj_type, obj_id, x_km, y_km, z_km, speed_ms, status
```

### Quick analysis example

```python
import pandas as pd

events = pd.read_csv("logs/events_YYYYMMDD_HHMMSS.csv")
traj = pd.read_csv("logs/trajectory_YYYYMMDD_HHMMSS.csv")

print(events.head())
print(traj.head())
```

---

## Web / WASM Build

The web version is generated locally and committed as a static bundle.

### Build locally

```bash
./build_web.sh
```

Output goes to:

```text
web-build/
```

### Preview locally

```bash
./build_web.sh --serve
```

### Notes

- `build_web.sh` stages only source files into a temp directory before packaging.
- The script also works around known `pygbag` config issues during build.
- `web-build/` is intended to be committed and served directly.

---

## Vercel Deployment

This project uses **static deployment** on Vercel.

Vercel does **not** compile the project from source.
It simply serves the already-built files from `web-build/`.

### Deploy workflow

1. Rebuild local bundle:

```bash
./build_web.sh
```

2. Commit updated bundle files in `web-build/`
3. Push to GitHub
4. Let Vercel deploy the updated static site

If the deployed website still shows an old version:

- confirm `web-build/serendib-dome.tar.gz` and `web-build/index.html` were committed,
- push again,
- hard-refresh the browser (`Ctrl+Shift+R`),
- or test in incognito mode.

---

## Known Limitations

- The simulation is designed for visualization and experimentation, not strict real-world missile guidance fidelity.
- Web builds depend on `pygbag` behavior and can occasionally require build-script workarounds.
- CSV logs are written on desktop runs; browser persistence depends on the web runtime sandbox.

---

## Development Notes

Useful files to inspect when changing behavior:

- `game/constants.py` — tune world, radar, missile, and interceptor parameters
- `game/predictor.py` — intercept/impact prediction logic
- `game/interceptor.py` — counter-missile homing behavior
- `game/simulation.py` — auto-launch, scoring, cleanup, logging
- `renderer/renderer.py` — all visual/UI changes

---

## Typical Developer Workflow

### Change desktop behavior

```bash
./run.sh
```

### Change web behavior

```bash
./build_web.sh
```

Then commit the new `web-build/` output.

### Analyze logs

```bash
python -c "import pandas as pd; print(pd.read_csv('logs/<file>.csv').head())"
```

---

## License / Usage

This repository currently has no explicit license file.
Add one if you plan to distribute or open-source it publicly.

