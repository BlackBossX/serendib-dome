# ─────────────────────────────────────────────
#  Serendib Dome – Radar System
#  Rotary-sweep phased-array radar
#  Detects threats within RADAR_RANGE_KM when
#  the rotating beam passes over them.
# ─────────────────────────────────────────────

import math
from game.constants import (
    RADAR_RANGE_KM, RADAR_SWEEP_DEG_S,
    RADAR_BEAM_WIDTH_DEG, RADAR_MIN_DETECTIONS,
)


def _angle_diff(a: float, b: float) -> float:
    """Signed shortest angular distance from b to a, degrees."""
    d = (a - b) % 360
    if d > 180:
        d -= 360
    return d


class Radar:
    """
    The radar sweeps in azimuth (plan view) continuously.
    When its beam sweeps across a missile within range, it records
    a detection event and logs the missile's position.

    Attributes
    ----------
    azimuth_deg : float
        Current beam heading (0 = North / +Y axis, CW).
    """

    def __init__(self):
        self.azimuth_deg: float = 0.0        # current beam azimuth
        # History of "blips" for the radar screen: list of (azimuth, range, alpha)
        self.blip_history: list[dict] = []
        self._MAX_BLIPS = 300

    # ── Update ────────────────────────────────

    def update(self, dt_sim: float, missiles: list):
        """Advance the sweep and detect any missiles in the beam."""
        self.azimuth_deg = (self.azimuth_deg + RADAR_SWEEP_DEG_S * dt_sim) % 360

        # Fade existing blips
        self.blip_history = [
            b for b in self.blip_history if b["alpha"] > 8
        ]
        for b in self.blip_history:
            b["alpha"] = max(0, b["alpha"] - 1)

        for m in missiles:
            if not m.alive:
                continue
            rng = m.range_km
            if rng > RADAR_RANGE_KM:
                continue

            # Angular distance from beam centre to missile azimuth
            diff = abs(_angle_diff(self.azimuth_deg, m.azimuth_deg))
            if diff <= RADAR_BEAM_WIDTH_DEG / 2:
                # ── Detection event ──────────────────────
                m.record_detection(None)       # sim_time filled by simulation

                # Add blip to radar screen history
                self.blip_history.append({
                    "azimuth": m.azimuth_deg,
                    "range":   rng,
                    "alpha":   255,
                    "mid":     m.id,
                })
                if len(self.blip_history) > self._MAX_BLIPS:
                    self.blip_history.pop(0)

    def scan_missile(self, missile, sim_time: float) -> bool:
        """
        Returns True if the missile is currently illuminated by the beam
        (range ≤ RADAR_RANGE_KM and within beam width).
        Also records detection and sim_time if newly hit.
        """
        if not missile.alive or missile.range_km > RADAR_RANGE_KM:
            return False
        diff = abs(_angle_diff(self.azimuth_deg, missile.azimuth_deg))
        if diff <= RADAR_BEAM_WIDTH_DEG / 2:
            missile.record_detection(sim_time)
            self.blip_history.append({
                "azimuth": missile.azimuth_deg,
                "range":   missile.range_km,
                "alpha":   255,
                "mid":     missile.id,
            })
            if len(self.blip_history) > self._MAX_BLIPS:
                self.blip_history.pop(0)
            return True
        return False

    def is_missile_tracked(self, missile) -> bool:
        return len(missile.det_times) >= RADAR_MIN_DETECTIONS
