# ─────────────────────────────────────────────
#  Serendib Dome – Interceptor Missile
# ─────────────────────────────────────────────

import numpy as np
import math
from game.constants import INTERCEPTOR_SPEED_KM_S, INTERCEPTOR_KILL_DIST

_iid = 0
def _next_iid():
    global _iid
    _iid += 1
    return _iid


class Interceptor:
    """
    Flies from the base (origin) toward a predicted impact point.
    Uses proportional-navigation-style homing: recalculates direction
    each frame toward the *current best estimate* of the intercept point,
    so it will adjust if the prediction is updated.
    """

    TRAIL_LEN = 80

    def __init__(self, target_missile, intercept_point: np.ndarray):
        self.id              = _next_iid()
        self.target          = target_missile       # Missile object
        self.intercept_point = intercept_point.copy()

        self.pos   = np.array([0.0, 0.0, 0.02])    # launch from base + tiny altitude
        self.alive = True
        self.hit   = False
        self.miss  = False
        self.trail: list[np.ndarray] = []

        self._update_velocity()

    # ── internals ─────────────────────────────

    def _update_velocity(self):
        """Recompute velocity vector toward current intercept_point."""
        direction = self.intercept_point - self.pos
        dist = np.linalg.norm(direction)
        if dist < 1e-6:
            self.vel = np.zeros(3)
        else:
            self.vel = (direction / dist) * INTERCEPTOR_SPEED_KM_S

    # ── public API ────────────────────────────

    def update_intercept_point(self, new_point: np.ndarray):
        self.intercept_point = new_point.copy()
        self._update_velocity()

    def update(self, dt_sim: float):
        if not self.alive:
            return

        self.trail.append(self.pos.copy())
        if len(self.trail) > self.TRAIL_LEN:
            self.trail.pop(0)

        self.pos += self.vel * dt_sim

        # ── proximity kill check ──────────────
        if self.target.alive:
            dist = float(np.linalg.norm(self.pos - self.target.pos))
            if dist <= INTERCEPTOR_KILL_DIST:
                self.hit              = True
                self.alive            = False
                self.target.alive     = False
                self.target.intercepted = True
                return

        # ── miss check: flew past intercept point ─────────────────
        dist_to_ip = float(np.linalg.norm(self.intercept_point - self.pos))
        started_far = np.linalg.norm(self.intercept_point) > 2.0   # sanity guard
        if dist_to_ip < 0.5 and not self.target.alive:
            self.alive = False
            return

        # Flew very far or target already dead
        if np.linalg.norm(self.pos) > 55.0 or not self.target.alive:
            if not self.hit:
                self.miss  = True
            self.alive = False
