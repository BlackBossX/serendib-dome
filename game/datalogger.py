# ─────────────────────────────────────────────
#  Serendib Dome – Data Logger
#
#  Writes two CSV files to  logs/  on each run:
#
#  events.csv     – discrete events (spawn, detect, track, lock,
#                   launch, kill, miss, breach)
#
#  trajectory.csv – position snapshot every SAMPLE_INTERVAL real-
#                   seconds for every live missile + interceptor;
#                   useful for plotting full flight paths.
#
#  Column reference
#  ────────────────
#  events.csv:
#    run_id, real_time, sim_time, event,
#    obj_type, obj_id, x_km, y_km, z_km, speed_ms,
#    ref_id, notes
#
#  trajectory.csv:
#    run_id, real_time, sim_time,
#    obj_type, obj_id, x_km, y_km, z_km, speed_ms, status
# ─────────────────────────────────────────────

import csv
import math
import os
import time
import datetime

SAMPLE_INTERVAL = 0.5   # real-seconds between trajectory snapshots


def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


class DataLogger:
    """
    Instantiated once per simulation run.
    Call the on_* methods from Simulation at the appropriate moments.
    Call sample() every tick to capture position snapshots.
    Call close() (or use as context manager) when the run ends.
    """

    def __init__(self, log_dir: str = "logs"):
        _ensure_dir(log_dir)

        # Unique run ID based on wall-clock time
        self.run_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        ev_path   = os.path.join(log_dir, f"events_{self.run_id}.csv")
        traj_path = os.path.join(log_dir, f"trajectory_{self.run_id}.csv")

        self._ev_fh   = open(ev_path,   "w", newline="")
        self._traj_fh = open(traj_path, "w", newline="")

        self._ev_w   = csv.writer(self._ev_fh)
        self._traj_w = csv.writer(self._traj_fh)

        # Write headers
        self._ev_w.writerow([
            "run_id", "real_time", "sim_time",
            "event",
            "obj_type", "obj_id",
            "x_km", "y_km", "z_km", "speed_ms",
            "ref_type", "ref_id",     # secondary object (e.g. interceptor ↔ missile)
            "notes",
        ])
        self._traj_w.writerow([
            "run_id", "real_time", "sim_time",
            "obj_type", "obj_id",
            "x_km", "y_km", "z_km", "speed_ms",
            "status",
        ])

        self._ev_fh.flush()
        self._traj_fh.flush()

        self._next_sample = 0.0   # real_time of next trajectory snapshot
        self._closed      = False

        print(f"[DataLogger] logging to {ev_path}")
        print(f"[DataLogger]            {traj_path}")

    # ── Private helpers ───────────────────────────────────────────

    def _ev(self, real_time, sim_time, event,
            obj_type, obj_id, pos, speed_ms,
            ref_type="", ref_id="", notes=""):
        if self._closed:
            return
        x, y, z = (round(float(v), 4) for v in pos)
        self._ev_w.writerow([
            self.run_id,
            round(real_time, 3),
            round(sim_time,  3),
            event,
            obj_type, obj_id,
            x, y, z,
            round(speed_ms, 1),
            ref_type, ref_id,
            notes,
        ])
        self._ev_fh.flush()

    def _speed_ms(self, missile_or_interceptor) -> float:
        obj = missile_or_interceptor
        if hasattr(obj, "speed_km_s"):          # Missile
            return obj.speed_km_s * 1000
        elif hasattr(obj, "vel"):               # Interceptor
            import numpy as np
            return float(np.linalg.norm(obj.vel)) * 1000
        return 0.0

    # ── Event hooks ───────────────────────────────────────────────

    def on_missile_spawn(self, missile, real_time: float, sim_time: float):
        self._ev(real_time, sim_time, "MISSILE_SPAWN",
                 "MISSILE", missile.id,
                 missile.pos, self._speed_ms(missile),
                 notes=f"init_spd={missile.initial_speed_km_s*1000:.0f}m/s")

    def on_missile_detected(self, missile, real_time: float, sim_time: float):
        self._ev(real_time, sim_time, "RADAR_DETECT",
                 "MISSILE", missile.id,
                 missile.pos, self._speed_ms(missile),
                 notes=f"det_count={len(missile.det_times)}")

    def on_missile_tracked(self, missile, real_time: float, sim_time: float):
        self._ev(real_time, sim_time, "TRACKED",
                 "MISSILE", missile.id,
                 missile.pos, self._speed_ms(missile))

    def on_intercept_locked(self, missile, intercept_point,
                            real_time: float, sim_time: float):
        import numpy as np
        ip = intercept_point
        self._ev(real_time, sim_time, "INTERCEPT_LOCKED",
                 "MISSILE", missile.id,
                 missile.pos, self._speed_ms(missile),
                 notes=(f"ip=({ip[0]:.2f},{ip[1]:.2f},{ip[2]:.2f})"))

    def on_interceptor_launch(self, interceptor, target_missile,
                              real_time: float, sim_time: float):
        self._ev(real_time, sim_time, "INTERCEPTOR_LAUNCH",
                 "INTERCEPTOR", interceptor.id,
                 interceptor.pos, self._speed_ms(interceptor),
                 ref_type="MISSILE", ref_id=target_missile.id,
                 notes=f"ip=({interceptor.intercept_point[0]:.2f},"
                       f"{interceptor.intercept_point[1]:.2f},"
                       f"{interceptor.intercept_point[2]:.2f})")

    def on_kill(self, interceptor, missile,
                real_time: float, sim_time: float):
        self._ev(real_time, sim_time, "KILL",
                 "INTERCEPTOR", interceptor.id,
                 interceptor.pos, self._speed_ms(interceptor),
                 ref_type="MISSILE", ref_id=missile.id)

    def on_miss(self, interceptor, real_time: float, sim_time: float):
        self._ev(real_time, sim_time, "INTERCEPTOR_MISS",
                 "INTERCEPTOR", interceptor.id,
                 interceptor.pos, self._speed_ms(interceptor),
                 ref_type="MISSILE", ref_id=interceptor.target.id)

    def on_missile_breach(self, missile, real_time: float, sim_time: float):
        self._ev(real_time, sim_time, "BREACH",
                 "MISSILE", missile.id,
                 missile.pos, self._speed_ms(missile))

    def on_missile_missed(self, missile, real_time: float, sim_time: float):
        """Missile hit the ground outside the defended zone."""
        self._ev(real_time, sim_time, "GROUND_IMPACT",
                 "MISSILE", missile.id,
                 missile.pos, self._speed_ms(missile))

    # ── Trajectory sampling ───────────────────────────────────────

    def sample(self, missiles, interceptors,
               real_time: float, sim_time: float):
        """Call every tick; snapshots are written every SAMPLE_INTERVAL seconds."""
        if self._closed:
            return
        if real_time < self._next_sample:
            return
        self._next_sample = real_time + SAMPLE_INTERVAL

        for m in missiles:
            if not m.alive:
                continue
            status = "tracked" if m.tracked else "detected" if m.detected else "undetected"
            x, y, z = (round(float(v), 4) for v in m.pos)
            self._traj_w.writerow([
                self.run_id,
                round(real_time, 3), round(sim_time, 3),
                "MISSILE", m.id,
                x, y, z,
                round(self._speed_ms(m), 1),
                status,
            ])

        for i in interceptors:
            if not i.alive:
                continue
            x, y, z = (round(float(v), 4) for v in i.pos)
            self._traj_w.writerow([
                self.run_id,
                round(real_time, 3), round(sim_time, 3),
                "INTERCEPTOR", i.id,
                x, y, z,
                round(self._speed_ms(i), 1),
                f"target={i.target.id}",
            ])

        self._traj_fh.flush()

    # ── Lifecycle ─────────────────────────────────────────────────

    def close(self):
        if not self._closed:
            self._ev_fh.close()
            self._traj_fh.close()
            self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
