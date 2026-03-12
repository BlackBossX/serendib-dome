# Serendib Dome 🛡️

A real-time **3D Air-Defence Missile Simulation** built in Python with pygame.

## Features

| Feature | Details |
|---|---|
| **3D Battlefield** | Custom software perspective renderer — orbit, rotate, zoom with the mouse |
| **Radar System** | Rotating 50 km phased-array radar with persistent sweep-glow on the plan view |
| **Ballistic Threats** | Projectile-motion missiles (parabolic z, linear x/y) spawned from the world edge |
| **ML Path Prediction** | Polynomial (degree-2) Linear Regression fitted to radar detections — predicts trajectory, ground impact point and optimal intercept point |
| **Auto Intercept** | Interceptors launch automatically once 4+ radar detections are collected |
| **Dual View** | Left = 3D perspective view; Right = 2D radar plan view + HUD stats |

## Setup

```bash
pip install -r requirements.txt
python main.py
```

## Deploy to Vercel (Web / WASM)

The game compiles to WebAssembly via **[pygbag](https://github.com/pygame-web/pygbag)** and can be hosted anywhere as a static site.

### Option A – Vercel auto-build (recommended)

1. Push this repo to GitHub
2. Import the project on [vercel.com](https://vercel.com/)
3. Vercel reads `vercel.json` and runs:
   ```
   pip install pygbag numpy pygame
   python -m pygbag --build --width 1440 --height 840 .
   ```
4. The `web-build/` directory is deployed automatically

> The `vercel.json` also sets the required COOP/COEP HTTP headers needed for WebAssembly SharedArrayBuffer.

### Option B – Local build → deploy

```bash
# Build once (creates web-build/)
./build_web.sh

# Preview locally before deploying
./build_web.sh --serve   # opens http://localhost:8000

# Then push + let Vercel serve the web-build/ directory
```

## Controls

| Key / Input | Action |
|---|---|
| **Mouse drag** (3D view) | Orbit camera |
| **Scroll wheel** | Zoom in / out |
| **SPACE** | Pause / Resume |
| **L** | Manually launch interceptor at nearest tracked missile |
| **R** | Reset simulation |
| **ESC / Q** | Quit |

## Project Layout

```
serendib-dome/
├── main.py                 # Entry point – async (works on desktop + pygbag WASM)
├── requirements.txt        # pygame, numpy, pygbag  (no scikit-learn needed)
├── vercel.json             # Vercel static deployment config
├── build_web.sh            # Local WASM build helper
├── run.sh                  # Desktop run helper (auto-creates .venv)
├── game/
│   ├── constants.py        # All tunable parameters
│   ├── missile.py          # Ballistic missile physics
│   ├── interceptor.py      # Interceptor missile homing logic
│   ├── radar.py            # Rotating radar beam detection
│   ├── predictor.py        # NumPy polyfit trajectory predictor
│   └── simulation.py       # Central simulation state manager
└── renderer/
    ├── camera.py           # Perspective camera (spherical orbit)
    └── renderer.py         # Full pygame renderer (3D + radar + HUD)
```

