# ─────────────────────────────────────────────
#  Serendib Dome – Interceptor Missile
# ─────────────────────────────────────────────

import numpy as np
from game.constants import INTERCEPTOR_SPEED_KM_S, INTERCEPTOR_KILL_DIST

_iid = 0
def _next_iid():
    global _iid
    _iid += 1
    return _iid


class Interceptor:
    """
    Target-locked interceptor.

    The predictor computes an intercept point to verify the interceptor
    can reach the missile in time.  Once launched, the interceptor
    immediately and continuously steers toward the missile's LIVE
    position every frame (pure pursuit + speed advantage = guaranteed
    closure).  It never flies to a static marker in space.
    """

    TRAIL_LEN = 80

    def __init__(self, target_missile, intercept_point: np.ndarray):
        self.id              = _next_iid()
        self.target          = target_missile
        self.intercept_point = intercept_point.copy()   # kept for rendering only

        self.pos   = np.array([0.0, 0.0, 0.02])   # launch from base origin
        self.alive = True
        self.hit   = False
        self.miss  = False
        self.locked = True    # target lock confirmed at launch
        self.trail: list[np.ndarray] = []

        self._min_dist = float('inf')   # closest approach to the target

        # Initial heading: lead toward intercept point so we don't chase tail
        self._steer_toward(intercept_point)

    # ── internals ─────────────────────────────────────────────────────

    def _steer_toward(self, point: np.ndarray):
        """Recalculate velocity to point toward `point` at full speed."""
        direction = point - self.pos
        dist = float(np.linalg.norm(direction))
        if dist > 1e-6:
            self.vel = (direction / dist) * INTERCEPTOR_SPEED_KM_S
        # If already on top of the point, keep previous velocity -- never zero

    # ── public API ────────────────────────────────────────────────────

    def update_intercept_point(self, new_point: np.ndarray):
        """Update stored intercept point (used for rendering only once locked)."""
        self.intercept_point = new_point.copy()
        # No heading change -- we are already locked on the live target

    def update(self, dt_sim: float):
        if not self.alive:
            return

        # Record trail
        self.trail.append(self.pos.copy())
        if len(self.trail) > self.TRAIL_LEN:
            self.trail.pop(0)

        # ── Target-lock steering: always home on live missile position ──
        if self.target.alive:
            self._steer_toward(self.target.pos)

        # ── Move ──────────────────────────────────────────────────
        self.pos += self.vel * dt_sim

        # ── Proximity kill check ───────────────────────────────────
        if self.target.alive:
            dist_to_target = float(np.linalg.norm(self.pos - self.target.pos))
            self._min_dist = min(self._min_dist, dist_to_target)

            if dist_to_target <= INTERCEPTOR_KILL_DIST:
                self.hit                = True
                self.alive              = False
                self.target.alive       = False
                self.target.intercepted = True
                return

        # ── Miss / out-of-bounds checks ────────────────────────────
        # Overshoot: was closing, now receding well past closest approach
        if (self.target.alive
                and self._min_dist < float('inf')
                and float(np.linalg.norm(self.pos - self.target.pos))
                    > self._min_dist + 2.0):
            self.miss  = True
            self.alive = False
            return

        # Out of world bounds or target already destroyed
        if np.linalg.norm(self.pos) > 58.0 or not self.target.alive:
            if not self.hit:
                self.miss = True
            self.alive = False

        # Out of world bounds or target already destroyed by another interceptor
        if np.linalg.norm(self.pos) > 58.0 or not self.target.alive:
            if not self.hit:
                self.miss = True
            self.alive = False
