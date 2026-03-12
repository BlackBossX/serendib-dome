# ─────────────────────────────────────────────
#  Serendib Dome – 3D Camera & Projection
#  Software perspective renderer (no OpenGL)
#  Camera uses spherical coordinates around (0,0,0).
# ─────────────────────────────────────────────

import math
import numpy as np


class Camera:
    """
    Perspective camera orbiting the world origin.

    azimuth   – rotation around Z axis (degrees, 0 = looking from +Y toward origin)
    elevation – tilt above horizon     (degrees, clamped 5–89)
    distance  – distance from origin   (km, world units)
    fov       – vertical field-of-view (degrees)
    """

    def __init__(self, azimuth=35.0, elevation=28.0, distance=90.0, fov=45.0):
        self.azimuth   = azimuth
        self.elevation = elevation
        self.distance  = distance
        self.fov       = fov

        # Viewport we project into (set by renderer each frame)
        self.viewport_w = 840
        self.viewport_h = 840

        # Mouse drag state
        self._drag   = False
        self._last_m = (0, 0)

    # ── Camera position ───────────────────────

    @property
    def position(self) -> np.ndarray:
        az  = math.radians(self.azimuth)
        el  = math.radians(self.elevation)
        x   = self.distance * math.cos(el) * math.sin(az)
        y   = self.distance * math.cos(el) * math.cos(az)
        z   = self.distance * math.sin(el)
        return np.array([x, y, z])

    # ── Drag controls ─────────────────────────

    def start_drag(self, mx: int, my: int):
        self._drag   = True
        self._last_m = (mx, my)

    def end_drag(self):
        self._drag = False

    def drag(self, mx: int, my: int):
        if not self._drag:
            return
        dx = mx - self._last_m[0]
        dy = my - self._last_m[1]
        self._last_m = (mx, my)
        self.azimuth   = (self.azimuth + dx * 0.35) % 360
        self.elevation = max(5.0, min(89.0, self.elevation - dy * 0.25))

    def zoom(self, delta: int):
        """delta > 0 = zoom in."""
        factor = 0.9 if delta > 0 else 1.1
        self.distance = max(20.0, min(250.0, self.distance * factor))

    # ── Projection ────────────────────────────

    def project(self, world_pt: np.ndarray) -> tuple[int, int] | None:
        """
        Project a 3D world point into 2D viewport pixel coordinates.
        Returns None if the point is behind the camera.
        """
        cam_pos = self.position
        forward = -cam_pos / np.linalg.norm(cam_pos)        # toward origin

        # ── Build camera axes ─────────────────
        world_up = np.array([0.0, 0.0, 1.0])
        right    = np.cross(forward, world_up)
        r_len    = np.linalg.norm(right)
        if r_len < 1e-6:
            right = np.array([1.0, 0.0, 0.0])
        else:
            right /= r_len
        up = np.cross(right, forward)

        # ── Transform to camera space ─────────
        rel = world_pt - cam_pos
        cam_x = np.dot(rel, right)
        cam_y = np.dot(rel, up)
        cam_z = np.dot(rel, forward)   # depth along view direction

        if cam_z <= 0.01:
            return None   # behind camera

        # ── Perspective divide ────────────────
        half_h = math.tan(math.radians(self.fov / 2))
        aspect = self.viewport_w / self.viewport_h
        ndc_x  = cam_x / (cam_z * half_h * aspect)
        ndc_y  = cam_y / (cam_z * half_h)

        px = int((ndc_x + 1) * 0.5 * self.viewport_w)
        py = int((1 - (ndc_y + 1) * 0.5) * self.viewport_h)

        return (px, py)

    def project_many(
        self, points: list[np.ndarray]
    ) -> list[tuple[int, int] | None]:
        return [self.project(p) for p in points]
