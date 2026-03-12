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
├── main.py                 # Entry point & event loop
├── requirements.txt
├── game/
│   ├── constants.py        # All tunable parameters
│   ├── missile.py          # Ballistic missile physics
│   ├── interceptor.py      # Interceptor missile homing logic
│   ├── radar.py            # Rotating radar beam detection
│   ├── predictor.py        # Polynomial Linear Regression predictor
│   └── simulation.py       # Central simulation state manager
└── renderer/
    ├── camera.py           # Perspective camera (spherical orbit)
    └── renderer.py         # Full pygame renderer (3D + radar + HUD)
```
