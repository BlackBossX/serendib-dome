#!/usr/bin/env python3
# ─────────────────────────────────────────────
#  Serendib Dome – Main Entry Point
#
#  Run:  python main.py
#
#  Controls
#  ────────
#  Mouse drag (3D view) : orbit camera
#  Mouse scroll         : zoom in / out
#  SPACE                : pause / resume
#  L                    : launch interceptor at nearest tracked missile
#  R                    : reset simulation
#  ESC / Q              : quit
# ─────────────────────────────────────────────

import sys
import pygame
from game.constants   import WIN_WIDTH, WIN_HEIGHT, TARGET_FPS
from game.simulation  import Simulation
from renderer.renderer import Renderer


def main():
    pygame.init()
    pygame.display.set_caption("SERENDIB DOME – Air Defence Simulation")

    screen = pygame.display.set_mode(
        (WIN_WIDTH, WIN_HEIGHT),
        pygame.DOUBLEBUF | pygame.HWSURFACE,
    )

    sim      = Simulation()
    renderer = Renderer(screen)
    clock    = pygame.time.Clock()

    running = True
    while running:
        # ── Event handling ────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif event.key == pygame.K_SPACE:
                    sim.toggle_pause()
                elif event.key == pygame.K_r:
                    sim  = Simulation()
                    renderer = Renderer(screen)
                elif event.key == pygame.K_l:
                    # Launch at the nearest tracked missile
                    tracked = sim.tracked_missiles
                    if tracked:
                        import numpy as np
                        nearest = min(tracked, key=lambda m: float(np.linalg.norm(m.pos)))
                        sim.launch_at(nearest)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                renderer.handle_mouse_down(event.pos, event.button)
                if event.button == 4:        # scroll up → zoom in
                    renderer.handle_scroll(1)
                elif event.button == 5:      # scroll down → zoom out
                    renderer.handle_scroll(-1)

            elif event.type == pygame.MOUSEBUTTONUP:
                renderer.handle_mouse_up(event.button)

            elif event.type == pygame.MOUSEMOTION:
                renderer.handle_mouse_motion(event.pos)

        # ── Simulate & render ─────────────────
        sim.tick()
        renderer.render(sim)
        pygame.display.flip()
        clock.tick(TARGET_FPS)

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
