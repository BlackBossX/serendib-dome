# ─────────────────────────────────────────────
#  Serendib Dome – Simulation Manager
#  Ties everything together: missiles, radar,
#  predictors, interceptors, scoring.
# ─────────────────────────────────────────────

import time
import numpy as np
from game.constants import (
    SIM_TIME_SCALE, MISSILE_SPAWN_INTERVAL,
    MAX_ACTIVE_MISSILES, MAX_INTERCEPTORS,
    MAX_INTERCEPTORS_PER_MISSILE, RELAUNCH_COOLDOWN_S,
    INTERCEPTOR_KILL_DIST,
)
from game.missile      import Missile
from game.interceptor  import Interceptor
from game.radar        import Radar
from game.predictor    import TrajectoryPredictor


class Explosion:
    """Visual-only explosion marker."""
    LIFETIME = 1.8   # real seconds

    def __init__(self, pos: np.ndarray):
        self.pos      = pos.copy()
        self.born     = time.time()
        self.alive    = True

    def update(self):
        if time.time() - self.born > self.LIFETIME:
            self.alive = False

    @property
    def age(self) -> float:
        return time.time() - self.born

    @property
    def frac(self) -> float:
        """0.0 = just born, 1.0 = dead."""
        return min(1.0, self.age / self.LIFETIME)


class Simulation:
    """Central simulation state."""

    def __init__(self):
        self.radar        = Radar()
        self.missiles:     list[Missile]             = []
        self.interceptors: list[Interceptor]         = []
        self.predictors:   dict[int, TrajectoryPredictor] = {}
        self.explosions:   list[Explosion]           = []

        # Timing
        self.sim_time      = 0.0     # simulated seconds elapsed
        self.real_time     = 0.0     # real seconds elapsed
        self._last_real    = time.time()
        self._spawn_timer  = 0.0    # real-seconds until next spawn
        self.time_scale    = SIM_TIME_SCALE  # adjustable at runtime

        # Per-missile relaunch cooldown: missile_id -> real_time of last launch
        # Default of -9999 means "never launched" so first launch is always immediate
        self._relaunch_times: dict[int, float] = {}

        # Stats
        self.score         = 0
        self.intercepted   = 0
        self.missed        = 0
        self.breached      = 0      # missiles that hit the ground near base
        self.total_spawned = 0
        self.interceptors_remaining = MAX_INTERCEPTORS

        # Paused flag
        self.paused = False

        # Spawn first missile immediately
        self._spawn_missile()

    # ── Main tick ─────────────────────────────

    def tick(self):
        """Call every frame from the game loop."""
        now   = time.time()
        dt_r  = now - self._last_real
        if dt_r > 0.1:
            dt_r = 0.1   # cap to avoid spiral of death on slow frames
        self._last_real = now

        if self.paused:
            return

        dt_sim = dt_r * self.time_scale
        self.sim_time   += dt_sim
        self.real_time  += dt_r

        # ── Spawn timer ──────────────────────
        self._spawn_timer -= dt_r
        if self._spawn_timer <= 0:
            active = sum(1 for m in self.missiles if m.alive)
            if active < MAX_ACTIVE_MISSILES:
                self._spawn_missile()
            self._spawn_timer = MISSILE_SPAWN_INTERVAL

        # ── Physics ──────────────────────────
        for m in self.missiles:
            m.update(dt_sim)

        for i in self.interceptors:
            i.update(dt_sim)

        for e in self.explosions:
            e.update()

        # ── Radar scan ───────────────────────
        self.radar.azimuth_deg = (
            self.radar.azimuth_deg
            + 60.0 * dt_sim  # degrees per sim-second
        ) % 360

        for m in self.missiles:
            if not m.alive:
                continue
            self.radar.scan_missile(m, self.sim_time)

            # Update or create predictor
            if m.id not in self.predictors:
                self.predictors[m.id] = TrajectoryPredictor(m.id)

            pred = self.predictors[m.id]
            if len(m.det_times) >= 4:
                pred.update(m, self.sim_time)
                m.tracked = pred.ready

                if pred.ready and pred.intercept_point is not None:
                    # Intercept point is locked on first detection —
                    # no need to update in-flight interceptors.

                    # ── Continuous auto-launch: fire whenever a slot is free
                    #    and the per-missile cooldown has elapsed ────────────
                    in_flight  = sum(
                        1 for i in self.interceptors
                        if i.target is m and i.alive
                    )
                    last_t     = self._relaunch_times.get(m.id, -9999.0)
                    cooldown_ok = (self.real_time - last_t) >= RELAUNCH_COOLDOWN_S

                    if (in_flight < MAX_INTERCEPTORS_PER_MISSILE
                            and cooldown_ok
                            and self.interceptors_remaining > 0):
                        self._launch_interceptor(m, pred.intercept_point)
                        self._relaunch_times[m.id] = self.real_time

        # ── Collisions / ground impacts ───────
        for m in self.missiles:
            if not m.alive and not m.intercepted:
                # Hit the ground
                if np.linalg.norm(m.pos[:2]) < 5.0:
                    self.breached += 1
                self.missed += 1
                self.explosions.append(Explosion(m.pos))

        for i in self.interceptors:
            if i.hit and i.alive == False:
                self.intercepted += 1
                self.score       += 100
                self.explosions.append(Explosion(i.pos))

        # ── Cleanup ──────────────────────────
        self.missiles     = [m for m in self.missiles     if m.alive]
        self.interceptors = [i for i in self.interceptors if i.alive]
        self.explosions   = [e for e in self.explosions   if e.alive]

    # ── Actions ───────────────────────────────

    def launch_at(self, missile: 'Missile'):
        """Manually launch an interceptor at a tracked missile."""
        if self.interceptors_remaining <= 0:
            return
        pred = self.predictors.get(missile.id)
        if pred and pred.intercept_point is not None:
            self._launch_interceptor(missile, pred.intercept_point)
        else:
            # Aim directly at current position as fallback
            self._launch_interceptor(missile, missile.pos.copy())
        self._relaunch_times[missile.id] = self.real_time

    def toggle_pause(self):
        self.paused = not self.paused

    def speed_up(self):
        """Increase simulation speed (capped at 8×)."""
        self.time_scale = min(8.0, round(self.time_scale + 0.5, 1))

    def slow_down(self):
        """Decrease simulation speed (minimum 0.25×)."""
        self.time_scale = max(0.25, round(self.time_scale - 0.5, 1))

    # ── Private helpers ───────────────────────

    def _spawn_missile(self):
        m = Missile(self.sim_time)
        self.missiles.append(m)
        self.total_spawned += 1
        self._spawn_timer = MISSILE_SPAWN_INTERVAL

    def _has_interceptor_for(self, missile: 'Missile') -> bool:
        return any(i.target is missile and i.alive for i in self.interceptors)

    def _launch_interceptor(self, missile: 'Missile', point: np.ndarray):
        inter = Interceptor(missile, point)
        self.interceptors.append(inter)
        self.interceptors_remaining = max(0, self.interceptors_remaining - 1)

    # ── Accessors ─────────────────────────────

    @property
    def live_missiles(self) -> list['Missile']:
        return [m for m in self.missiles if m.alive]

    @property
    def tracked_missiles(self) -> list['Missile']:
        return [m for m in self.missiles if m.alive and m.tracked]

    def get_predictor(self, missile: 'Missile') -> 'TrajectoryPredictor | None':
        return self.predictors.get(missile.id)
