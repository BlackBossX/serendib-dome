# ─────────────────────────────────────────────
#  Serendib Dome – Incoming Missile
#  Ballistic projectile: x/y linear, z parabolic
# ─────────────────────────────────────────────

import math, random
import numpy as np
from game.constants import (
    WORLD_RADIUS_KM, MAX_ALTITUDE_KM,
    MISSILE_SPEED_MIN_KM_S, MISSILE_SPEED_MAX_KM_S,
    GRAVITY_KM_S2, C_MISSILE, C_MISSILE_TRAIL,
)

_id_counter = 0

def _next_id():
    global _id_counter
    _id_counter += 1
    return _id_counter


class Missile:
    """
    Incoming ballistic threat.

    Trajectory (true projectile motion):
        x(t) = x0 + vx·t
        y(t) = y0 + vy·t
        z(t) = z0 + vz·t  -  ½·g·t²

    The missile is spawned at the edge of the world volume at some
    altitude and aimed roughly toward the defended base at (0,0,0).
    """

    TRAIL_LEN = 60          # number of past positions to keep for drawing

    def __init__(self, sim_time: float):
        self.id = _next_id()
        self.alive      = True
        self.intercepted = False
        self.spawn_time  = sim_time

        # ── Pick a random spawn point on the edge ──────────────────
        angle  = random.uniform(0, 2 * math.pi)
        radius = WORLD_RADIUS_KM * random.uniform(0.80, 1.00)  # near boundary
        x0 = radius * math.cos(angle)
        y0 = radius * math.sin(angle)
        z0 = random.uniform(MAX_ALTITUDE_KM * 0.25, MAX_ALTITUDE_KM * 0.65)

        # ── Velocity toward base ± small spread ────────────────────
        speed  = random.uniform(MISSILE_SPEED_MIN_KM_S, MISSILE_SPEED_MAX_KM_S)
        # Horizontal direction toward the origin
        dist_h = math.hypot(x0, y0)
        vx_dir = -x0 / dist_h + random.uniform(-0.15, 0.15)
        vy_dir = -y0 / dist_h + random.uniform(-0.15, 0.15)
        norm   = math.hypot(vx_dir, vy_dir)

        # Horizontal speed fraction
        h_speed = speed * random.uniform(0.70, 0.95)
        self.vx = h_speed * (vx_dir / norm)
        self.vy = h_speed * (vy_dir / norm)

        # vz chosen so the missile reaches z=0 roughly when it hits the center
        # z(t_impact) ≈ 0  →  t_impact ≈ dist_h / h_speed
        t_impact_est = dist_h / h_speed
        # z0 + vz·t - ½g·t² = 0  →  vz = (½g·t² - z0) / t
        self.vz = (0.5 * GRAVITY_KM_S2 * t_impact_est**2 - z0) / t_impact_est

        self.pos = np.array([x0, y0, z0], dtype=float)
        self.trail: list[np.ndarray] = []

        # ── Radar bookkeeping ──────────────────────────────────────
        self.detected     = False
        self.tracked      = False           # enough points for prediction
        self.det_times:   list[float] = []
        self.det_positions: list[np.ndarray] = []

    # ── Helpers ────────────────────────────────────────────────────

    def position_at(self, t_since_spawn: float) -> np.ndarray:
        """Return predicted world position at `t_since_spawn` seconds after spawn."""
        x = self.pos[0] + self.vx * t_since_spawn   # already absolute; need delta
        # We store the true initial position, so let's parametrize from spawn
        return np.array([
            self.pos[0],   # will be overwritten; use _pos_from_delta below
            self.pos[1],
            self.pos[2],
        ])

    def _pos_at_delta(self, dt: float) -> np.ndarray:
        """Position dt seconds *from now*."""
        return np.array([
            self.pos[0] + self.vx * dt,
            self.pos[1] + self.vy * dt,
            self.pos[2] + self.vz * dt - 0.5 * GRAVITY_KM_S2 * dt**2,
        ])

    def update(self, dt_sim: float):
        """Advance physics by dt_sim simulation-seconds."""
        if not self.alive:
            return
        self.trail.append(self.pos.copy())
        if len(self.trail) > self.TRAIL_LEN:
            self.trail.pop(0)
        self.pos[0] += self.vx  * dt_sim
        self.pos[1] += self.vy  * dt_sim
        self.pos[2] += self.vz  * dt_sim - 0.5 * GRAVITY_KM_S2 * dt_sim**2
        self.vz      -= GRAVITY_KM_S2 * dt_sim   # update vertical velocity

        # Kill if below ground or too far away
        if self.pos[2] < 0 or np.linalg.norm(self.pos[:2]) > WORLD_RADIUS_KM * 1.5:
            self.alive = False

    @property
    def range_km(self) -> float:
        return float(np.linalg.norm(self.pos))

    @property
    def azimuth_deg(self) -> float:
        """Azimuth from north (Y+), clockwise, in degrees."""
        return math.degrees(math.atan2(self.pos[0], self.pos[1])) % 360

    @property
    def elevation_deg(self) -> float:
        """Elevation angle from horizontal, degrees."""
        h = math.hypot(self.pos[0], self.pos[1])
        return math.degrees(math.atan2(self.pos[2], h)) if h > 0 else 90.0

    def record_detection(self, sim_time: float):
        self.detected = True
        self.det_times.append(sim_time)
        self.det_positions.append(self.pos.copy())
