# ─────────────────────────────────────────────
#  Serendib Dome – Trajectory Predictor
#
#  Uses scikit-learn LinearRegression to fit the
#  radar detection history and predict:
#   • Future trajectory samples (for rendering)
#   • Predicted ground-impact point (z = 0)
#   • Best intercept point / time for launch
#
#  Feature engineering:
#   x(t), y(t) are linear  → features = [t]
#   z(t) is quadratic       → features = [t, t²]
#  We use the same Polynomial (degree-2) model for
#  all three axes to keep things uniform and to let
#  the model capture the gravity term.
# ─────────────────────────────────────────────

import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from game.constants import RADAR_MIN_DETECTIONS, INTERCEPTOR_SPEED_KM_S


class TrajectoryPredictor:
    """
    Holds prediction state for ONE tracked missile.
    Call `update()` whenever new detections arrive.
    """

    PREDICT_HORIZON = 60.0   # seconds of future trajectory to show
    PREDICT_STEPS   = 80     # number of sample points along predicted path

    def __init__(self, missile_id: int):
        self.missile_id = missile_id
        self.ready       = False            # True once we have a valid model
        self.impact_point: np.ndarray | None = None   # predicted z=0 crossing
        self.intercept_point: np.ndarray | None = None
        self.intercept_time_from_now: float = 0.0
        self.predicted_path: list[np.ndarray] = []   # future trajectory samples
        self._poly = PolynomialFeatures(degree=2, include_bias=True)
        self._reg_x = LinearRegression()
        self._reg_y = LinearRegression()
        self._reg_z = LinearRegression()

    # ── public API ────────────────────────────

    def update(self, missile, sim_time: float):
        """
        Re-fit the regression model using all detection history so far.
        Returns True if prediction is usable.
        """
        times = missile.det_times
        positions = missile.det_positions

        if len(times) < RADAR_MIN_DETECTIONS:
            self.ready = False
            return False

        T = np.array(times, dtype=float).reshape(-1, 1)
        T_poly = self._poly.fit_transform(T)

        xs = np.array([p[0] for p in positions])
        ys = np.array([p[1] for p in positions])
        zs = np.array([p[2] for p in positions])

        self._reg_x.fit(T_poly, xs)
        self._reg_y.fit(T_poly, ys)
        self._reg_z.fit(T_poly, zs)

        # ── Sample the predicted future path ──────────────────────
        t_now  = sim_time
        t_end  = t_now + self.PREDICT_HORIZON
        t_samp = np.linspace(t_now, t_end, self.PREDICT_STEPS).reshape(-1, 1)
        T_s    = self._poly.transform(t_samp)

        px = self._reg_x.predict(T_s)
        py = self._reg_y.predict(T_s)
        pz = self._reg_z.predict(T_s)

        self.predicted_path = [
            np.array([px[i], py[i], pz[i]])
            for i in range(len(px))
            if pz[i] >= 0.0   # only show above-ground portion
        ]

        # ── Find ground impact (z = 0 crossing) ──────────────────
        self.impact_point = self._find_impact(t_now, t_end)

        # ── Compute best intercept point ──────────────────────────
        if self.impact_point is not None:
            ip, idt = self._find_intercept(t_now, t_end)
            self.intercept_point            = ip
            self.intercept_time_from_now    = idt
        else:
            self.intercept_point = None

        self.ready = True
        return True

    # ── helpers ───────────────────────────────

    def _predict_pos(self, t_abs: float) -> np.ndarray:
        T_p = self._poly.transform([[t_abs]])
        return np.array([
            self._reg_x.predict(T_p)[0],
            self._reg_y.predict(T_p)[0],
            self._reg_z.predict(T_p)[0],
        ])

    def _find_impact(self, t_start: float, t_end: float) -> np.ndarray | None:
        """Binary-search for z=0 crossing."""
        p_start = self._predict_pos(t_start)
        p_end   = self._predict_pos(t_end)

        # Need sign change
        if p_start[2] <= 0:
            result = p_start.copy()
            result[2] = 0.0
            return result
        if p_end[2] > 0:
            return None   # doesn't reach ground in horizon

        lo, hi = t_start, t_end
        for _ in range(30):
            mid = (lo + hi) / 2
            if self._predict_pos(mid)[2] > 0:
                lo = mid
            else:
                hi = mid

        pt = self._predict_pos((lo + hi) / 2)
        pt[2] = 0.0
        return pt

    def _find_intercept(
        self, t_now: float, t_end: float
    ) -> tuple[np.ndarray, float]:
        """
        Find the earliest time T* such that:
          distance(base_origin, predicted_pos(T*))  ≤  interceptor_speed · (T* - t_now)
        i.e. the interceptor can reach the predicted missile position in time.
        Steps through the predicted future coarsely and refines.
        """
        best_pt   = None
        best_dt   = 0.0

        steps = 120
        for i in range(steps + 1):
            t = t_now + (t_end - t_now) * i / steps
            pt  = self._predict_pos(t)
            if pt[2] < 0:
                break
            dist_to_pt = float(np.linalg.norm(pt))
            dt_needed  = dist_to_pt / INTERCEPTOR_SPEED_KM_S
            dt_avail   = t - t_now
            if dt_avail >= dt_needed:
                best_pt  = pt
                best_dt  = dt_avail
                break

        return best_pt, best_dt
