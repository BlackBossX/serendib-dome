# ─────────────────────────────────────────────
#  Serendib Dome – Renderer
#  Draws the 3-D perspective view, 2-D radar
#  plan view, and HUD statistics panel using
#  pygame surfaces (pure software rasteriser).
# ─────────────────────────────────────────────

import math
import pygame
import numpy as np
from game.constants import *
from renderer.camera import Camera


# ── Helpers ────────────────────────────────────────────────────────────────

def _clamp(v, lo, hi):
    return max(lo, min(hi, v))

def _alpha_color(color, alpha):
    return (*color, _clamp(alpha, 0, 255))

def _blend(c1, c2, t):
    """Linear interpolate between two RGB colours."""
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))

def _draw_circle_aa(surf, color, center, radius, width=1):
    """Anti-aliased circle using pygame.draw.circle with thickness."""
    if radius > 0:
        pygame.draw.circle(surf, color, center, radius, width)

def _draw_line_aa(surf, color, p1, p2, width=1):
    if p1 and p2:
        pygame.draw.line(surf, color, p1, p2, width)

def _draw_dashed_line(surf, color, p1, p2, dash=8, gap=5):
    """Draw a straight dashed line between two screen points."""
    if not p1 or not p2:
        return
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    total = math.hypot(dx, dy)
    if total < 1:
        return
    ux, uy = dx / total, dy / total
    pos = 0
    drawing = True
    while pos < total:
        seg = dash if drawing else gap
        end = min(pos + seg, total)
        if drawing:
            x0 = int(p1[0] + ux * pos)
            y0 = int(p1[1] + uy * pos)
            x1 = int(p1[0] + ux * end)
            y1 = int(p1[1] + uy * end)
            pygame.draw.line(surf, color, (x0, y0), (x1, y1), 1)
        pos += seg
        drawing = not drawing

def _draw_glow_circle(surf, color, center, r, intensity=120):
    """Draw a simple 'glow' by layering translucent circles."""
    for i in range(3, 0, -1):
        a = intensity // (i * 2)
        c = (*color, a)
        s = pygame.Surface((r * 2 + 10, r * 2 + 10), pygame.SRCALPHA)
        pygame.draw.circle(s, c, (r + 5, r + 5), r + i * 3)
        surf.blit(s, (center[0] - r - 5, center[1] - r - 5))
    pygame.draw.circle(surf, color, center, r)


# ── Renderer class ─────────────────────────────────────────────────────────

class Renderer:
    """Manages all rendering onto a single pygame.Surface window."""

    # Grid line count (each side)
    GRID_LINES = 10

    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.camera = Camera(azimuth=40.0, elevation=30.0, distance=95.0)
        self.camera.viewport_w = VIEW3D_W
        self.camera.viewport_h = VIEW3D_H

        # Surfaces
        self.surf_3d    = pygame.Surface((VIEW3D_W, VIEW3D_H))
        self.surf_radar = pygame.Surface((RADAR_W,  RADAR_H))
        self.surf_hud   = pygame.Surface((RADAR_W,  HUD_H))

        # Fonts
        pygame.font.init()
        self.font_lg = pygame.font.SysFont("consolas", 18, bold=True)
        self.font_md = pygame.font.SysFont("consolas", 14)
        self.font_sm = pygame.font.SysFont("consolas", 12)

        # Radar sweep trail surface (persistent, faded each frame)
        self.radar_trail_surf = pygame.Surface((RADAR_W, RADAR_H), pygame.SRCALPHA)

        # Selected missile index for manual intercept
        self.selected_idx = 0

    # ══════════════════════════════════════════
    #  Public entry point
    # ══════════════════════════════════════════

    def render(self, sim):
        """Draw everything and flip the display."""
        self._draw_3d(sim)
        self._draw_radar(sim)
        self._draw_hud(sim)

        self.screen.blit(self.surf_3d,    (0,        0))
        self.screen.blit(self.surf_radar, (VIEW3D_W, 0))
        self.screen.blit(self.surf_hud,   (VIEW3D_W, RADAR_H))

        # Dividers
        pygame.draw.line(self.screen, (30, 60, 50),
                         (VIEW3D_W, 0), (VIEW3D_W, WIN_HEIGHT), 2)
        pygame.draw.line(self.screen, (30, 60, 50),
                         (VIEW3D_W, RADAR_H), (WIN_WIDTH, RADAR_H), 2)

    # ══════════════════════════════════════════
    #  3-D Perspective View
    # ══════════════════════════════════════════

    def _draw_3d(self, sim):
        s = self.surf_3d
        s.fill(C_BG)

        self._draw_grid(s)
        self._draw_base(s)
        self._draw_predicted_paths_3d(s, sim)
        self._draw_interceptors_3d(s, sim)
        self._draw_missiles_3d(s, sim)
        self._draw_explosions_3d(s, sim)
        self._draw_3d_labels(s, sim)
        self._draw_3d_overlay(s, sim)

    def _proj(self, world_pt) -> tuple[int, int] | None:
        return self.camera.project(np.asarray(world_pt, dtype=float))

    # ── Ground grid ───────────────────────────

    def _draw_grid(self, s):
        step = WORLD_RADIUS_KM / self.GRID_LINES
        R    = WORLD_RADIUS_KM

        for i in range(-self.GRID_LINES, self.GRID_LINES + 1):
            v = i * step
            # X-parallel lines
            pa = self._proj([-R, v, 0])
            pb = self._proj([ R, v, 0])
            if pa and pb:
                pygame.draw.line(s, C_GRID, pa, pb, 1)
            # Y-parallel lines
            pa = self._proj([v, -R, 0])
            pb = self._proj([v,  R, 0])
            if pa and pb:
                pygame.draw.line(s, C_GRID, pa, pb, 1)

        # Range rings (on ground)
        for r in [10, 20, 30, 40, 50]:
            pts = []
            for a in range(0, 361, 6):
                rad = math.radians(a)
                p = self._proj([r * math.cos(rad), r * math.sin(rad), 0])
                if p:
                    pts.append(p)
            if len(pts) > 2:
                pygame.draw.lines(s, (20, 45, 35), False, pts, 1)

    # ── Base marker ───────────────────────────

    def _draw_base(self, s):
        p = self._proj([0, 0, 0])
        if p:
            pygame.draw.circle(s, C_BASE, p, 7)
            pygame.draw.circle(s, (255, 255, 255), p, 7, 2)
            label = self.font_sm.render("BASE", True, C_BASE)
            s.blit(label, (p[0] + 9, p[1] - 7))

        # Tiny radar mast
        p1 = self._proj([0, 0, 0])
        p2 = self._proj([0, 0, 1.5])
        if p1 and p2:
            pygame.draw.line(s, C_BASE, p1, p2, 2)

    # ── Missiles ──────────────────────────────

    def _draw_missiles_3d(self, s, sim):
        for m in sim.missiles:
            if not m.alive:
                continue

            # Trail
            trail_pts = [self._proj(t) for t in m.trail]
            valid = [p for p in trail_pts if p]
            for k in range(1, len(valid)):
                alpha = int(255 * k / len(valid))
                col   = _blend((30, 15, 8), C_MISSILE_TRAIL, k / len(valid))
                pygame.draw.line(s, col, valid[k - 1], valid[k], 1)

            # Head
            p = self._proj(m.pos)
            if p:
                _draw_glow_circle(s, C_MISSILE, p, 5, 80)
                # Label
                lbl = self.font_sm.render(f"M{m.id}", True, C_MISSILE)
                s.blit(lbl, (p[0] + 7, p[1] - 6))

    # ── Interceptors ──────────────────────────

    def _draw_interceptors_3d(self, s, sim):
        for i in sim.interceptors:
            if not i.alive:
                continue
            # Trail
            pts = [self._proj(t) for t in i.trail]
            valid = [p for p in pts if p]
            for k in range(1, len(valid)):
                col = _blend((10, 20, 60), C_INTER_TRAIL, k / len(valid))
                pygame.draw.line(s, col, valid[k - 1], valid[k], 1)
            # Head
            p = self._proj(i.pos)
            if p:
                _draw_glow_circle(s, C_INTERCEPTOR, p, 4, 80)

    # ── Predicted paths ───────────────────────

    def _draw_predicted_paths_3d(self, s, sim):
        for m in sim.tracked_missiles:
            pred = sim.get_predictor(m)
            if pred is None or not pred.ready:
                continue
            pts = [self._proj(p) for p in pred.predicted_path]
            pts = [p for p in pts if p]
            for k in range(1, len(pts)):
                if k % 3 != 0:
                    pygame.draw.line(s, C_PREDICTED, pts[k - 1], pts[k], 1)

            # Impact cross
            if pred.impact_point is not None:
                ip = self._proj(pred.impact_point)
                if ip:
                    pygame.draw.line(s, C_IMPACT, (ip[0]-8, ip[1]), (ip[0]+8, ip[1]), 2)
                    pygame.draw.line(s, C_IMPACT, (ip[0], ip[1]-8), (ip[0], ip[1]+8), 2)
                    pygame.draw.circle(s, C_IMPACT, ip, 6, 2)

            # Intercept target point (blue diamond)
            if pred.intercept_point is not None:
                tp = self._proj(pred.intercept_point)
                if tp:
                    pygame.draw.polygon(s, C_INTERCEPTOR, [
                        (tp[0], tp[1]-9), (tp[0]+7, tp[1]),
                        (tp[0], tp[1]+9), (tp[0]-7, tp[1]),
                    ], 2)

    # ── Explosions ────────────────────────────

    def _draw_explosions_3d(self, s, sim):
        for e in sim.explosions:
            p = self._proj(e.pos)
            if not p:
                continue
            frac = e.frac
            r    = int(4 + 18 * frac)
            a    = int(255 * (1 - frac))
            col  = _blend(C_EXPLOSION, (80, 20, 0), frac)
            surf = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*col, a), (r + 1, r + 1), r)
            s.blit(surf, (p[0] - r - 1, p[1] - r - 1))

    # ── Labels overlay ────────────────────────

    def _draw_3d_labels(self, s, sim):
        # Compass
        for label, pt in [("N", [0, 55, 0]), ("E", [55, 0, 0]),
                           ("S", [0,-55, 0]), ("W", [-55, 0, 0])]:
            p = self._proj(pt)
            if p:
                t = self.font_sm.render(label, True, (60, 100, 80))
                s.blit(t, (p[0] - 5, p[1] - 7))

    def _draw_3d_overlay(self, s, sim):
        # Title bar
        t = self.font_lg.render("SERENDIB DOME  –  3D BATTLE VIEW", True, C_TEXT)
        s.blit(t, (10, 8))
        # Controls hint
        h = self.font_sm.render("DRAG: rotate    SCROLL: zoom    SPACE: pause    L: launch", True, (50, 80, 70))
        s.blit(h, (10, VIEW3D_H - 20))

    # ══════════════════════════════════════════
    #  2-D Radar Plan View
    # ══════════════════════════════════════════

    def _draw_radar(self, sim):
        s = self.surf_radar
        s.fill(C_PANEL_BG)

        cx, cy = RADAR_W // 2, RADAR_H // 2
        max_r  = min(cx, cy) - 20   # pixel radius for RADAR_RANGE_KM

        def world_to_radar(wx, wy) -> tuple[int, int]:
            px = cx + int(wx / WORLD_RADIUS_KM * max_r)
            py = cy - int(wy / WORLD_RADIUS_KM * max_r)
            return (px, py)

        # ── Radar fade overlay (persistent sweep glow) ────────────
        fade = pygame.Surface((RADAR_W, RADAR_H), pygame.SRCALPHA)
        fade.fill((0, 0, 0, 18))
        self.radar_trail_surf.blit(fade, (0, 0))

        # Draw sweep wedge onto trail surface
        az_rad = math.radians(sim.radar.azimuth_deg - 90)   # convert to screen
        bw_rad = math.radians(RADAR_BEAM_WIDTH_DEG)
        sweep_pts = [
            (cx, cy),
        ]
        steps = 24
        for step in range(steps + 1):
            angle = az_rad + bw_rad * (step / steps - 0.5)
            sweep_pts.append((
                cx + int(math.cos(angle) * max_r),
                cy + int(math.sin(angle) * max_r),
            ))
        sweep_surf = pygame.Surface((RADAR_W, RADAR_H), pygame.SRCALPHA)
        pygame.draw.polygon(sweep_surf, (0, 255, 80, 55), sweep_pts)
        self.radar_trail_surf.blit(sweep_surf, (0, 0))

        s.blit(self.radar_trail_surf, (0, 0))

        # ── Range rings ───────────────────────
        for km in [10, 20, 30, 40, 50]:
            pr = int(km / WORLD_RADIUS_KM * max_r)
            pygame.draw.circle(s, C_RADAR_RING, (cx, cy), pr, 1)
            lbl = self.font_sm.render(f"{km}km", True, (40, 80, 60))
            s.blit(lbl, (cx + pr + 2, cy - 8))

        # Outer ring (bold)
        pygame.draw.circle(s, C_RADAR_SWEEP, (cx, cy), max_r, 2)

        # Crosshairs
        pygame.draw.line(s, C_GRID, (cx - max_r, cy), (cx + max_r, cy), 1)
        pygame.draw.line(s, C_GRID, (cx, cy - max_r), (cx, cy + max_r), 1)

        # ── Sweep line (leading edge) ──────────
        lx = cx + int(math.cos(az_rad) * max_r)
        ly = cy + int(math.sin(az_rad) * max_r)
        pygame.draw.line(s, C_RADAR_SWEEP, (cx, cy), (lx, ly), 2)

        # ── Blip history ──────────────────────
        for blip in sim.radar.blip_history:
            baz_rad = math.radians(blip["azimuth"] - 90)
            brng    = blip["range"] / WORLD_RADIUS_KM * max_r
            bx = cx + int(math.cos(baz_rad) * brng)
            by = cy + int(math.sin(baz_rad) * brng)
            a  = blip["alpha"]
            col = (0, min(255, a), int(a * 0.3))
            pygame.draw.circle(s, col, (bx, by), 3)

        # ── Live missile positions ─────────────
        for m in sim.live_missiles:
            bx, by = world_to_radar(m.pos[0], m.pos[1])
            pygame.draw.circle(s, C_MISSILE, (bx, by), 5)
            pygame.draw.circle(s, (255, 200, 150), (bx, by), 5, 1)
            lbl = self.font_sm.render(f"M{m.id}", True, C_MISSILE)
            s.blit(lbl, (bx + 7, by - 6))

            # Predicted impact on radar
            pred = sim.get_predictor(m)
            if pred and pred.ready and pred.impact_point is not None:
                ix, iy = world_to_radar(
                    pred.impact_point[0], pred.impact_point[1]
                )
                pygame.draw.line(s, C_PREDICTED, (bx, by), (ix, iy), 1)
                pygame.draw.circle(s, C_IMPACT, (ix, iy), 5, 2)

                # Predicted path dots
                for pt in pred.predicted_path[::4]:
                    dx, dy = world_to_radar(pt[0], pt[1])
                    pygame.draw.circle(s, (60, 50, 10), (dx, dy), 2)

        # ── Interceptors on radar ──────────────
        for inter in sim.interceptors:
            if not inter.alive:
                continue
            bx, by = world_to_radar(inter.pos[0], inter.pos[1])
            pygame.draw.circle(s, C_INTERCEPTOR, (bx, by), 4)

        # ── Base marker ───────────────────────
        pygame.draw.circle(s, C_BASE, (cx, cy), 7)
        pygame.draw.circle(s, (255, 255, 255), (cx, cy), 7, 2)

        # ── Title ─────────────────────────────
        t = self.font_lg.render("RADAR  –  50 km RANGE", True, C_TEXT)
        s.blit(t, (RADAR_W // 2 - t.get_width() // 2, 6))

        # ── Azimuth readout ───────────────────
        az_lbl = self.font_sm.render(
            f"AZ {sim.radar.azimuth_deg:06.2f}°", True, C_RADAR_SWEEP
        )
        s.blit(az_lbl, (8, RADAR_H - 22))

    # ══════════════════════════════════════════
    #  HUD Panel
    # ══════════════════════════════════════════

    def _draw_hud(self, sim):
        s = self.surf_hud
        s.fill(C_PANEL_BG)

        # Border
        pygame.draw.rect(s, (30, 60, 45), s.get_rect(), 2)

        x, y = 12, 8
        line_h = 19

        def text(msg, color=C_TEXT, font=None):
            nonlocal y
            f = font or self.font_md
            lbl = f.render(msg, True, color)
            s.blit(lbl, (x, y))
            y += line_h

        def sep():
            nonlocal y
            pygame.draw.line(s, (30, 55, 40), (x, y), (RADAR_W - x, y), 1)
            y += 5

        text("── MISSION STATUS ──", (80, 160, 100), self.font_lg)
        sep()

        # Threats
        live = len(sim.live_missiles)
        trk  = len(sim.tracked_missiles)
        text(f"Threats active  : {live}", C_MISSILE if live > 0 else C_TEXT)
        text(f"Tracked (ML)    : {trk}",  C_PREDICTED)

        sep()

        # Interceptors
        text(f"Interceptors    : {sim.interceptors_remaining}/{MAX_INTERCEPTORS}", C_INTERCEPTOR)
        text(f"In flight       : {len(sim.interceptors)}", C_INTER_TRAIL)

        sep()

        # Score
        text(f"Kills           : {sim.intercepted}", C_BASE)
        text(f"Breaches        : {sim.breached}", C_TEXT_WARN if sim.breached > 0 else C_TEXT)
        text(f"Score           : {sim.score}", (220, 220, 100))

        sep()

        # Sim time
        mm = int(sim.real_time) // 60
        ss = int(sim.real_time) % 60
        text(f"Time            : {mm:02d}:{ss:02d}", C_TEXT)
        text(f"Sim time        : {sim.sim_time:.1f}s", (60, 80, 70))

        if sim.paused:
            text("  *** PAUSED ***", (255, 200, 50), self.font_lg)

    # ══════════════════════════════════════════
    #  Input routing
    # ══════════════════════════════════════════

    def handle_mouse_down(self, pos, button):
        if pos[0] < VIEW3D_W:
            if button == 1:
                self.camera.start_drag(*pos)

    def handle_mouse_up(self, button):
        if button == 1:
            self.camera.end_drag()

    def handle_mouse_motion(self, pos):
        self.camera.drag(*pos)

    def handle_scroll(self, y):
        self.camera.zoom(y)
