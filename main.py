#!/usr/bin/env python3
# ─────────────────────────────────────────────
#  Serendib Dome – Main Entry Point
#
#  Desktop:  python main.py   (or ./run.sh)
#  Web:      pygbag .         (builds WASM bundle)
#
#  The async main() + asyncio.run() pattern is
#  required by pygbag (WebAssembly) and works
#  identically on desktop.
#
#  Controls
#  ────────
#  Mouse drag (3D view) : orbit camera
#  Mouse scroll         : zoom in / out
#  SPACE                : pause / resume
#  L                    : launch interceptor at nearest tracked missile
#  R                    : reset simulation
#  ESC / Q              : quit (desktop only)
# ─────────────────────────────────────────────

import asyncio
import sys
import numpy as np
import pygame

from game.constants    import WIN_WIDTH, WIN_HEIGHT, TARGET_FPS
from game.simulation   import Simulation
from renderer.renderer import Renderer


async def main():
    pygame.init()
    pygame.display.set_caption("SERENDIB DOME – Air Defence Simulation")

    screen = pygame.display.set_mode(
        (WIN_WIDTH, WIN_HEIGHT),
        pygame.DOUBLEBUF,          # HWSURFACE removed – unsupported in WASM
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
                    sim      = Simulation()
                    renderer = Renderer(screen)
                elif event.key == pygame.K_l:
                    tracked = sim.tracked_missiles
                    if tracked:
                        nearest = min(
                            tracked,
                            key=lambda m: float(np.linalg.norm(m.pos)),
                        )
                        sim.launch_at(nearest)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                renderer.handle_mouse_down(event.pos, event.button)
                if event.button == 4:
                    renderer.handle_scroll(1)
                elif event.button == 5:
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

        # ── Yield to browser event loop ───────
        # On desktop this is a no-op; in WASM it lets the browser breathe.
        await asyncio.sleep(0)

    pygame.quit()
    try:
        sys.exit(0)
    except SystemExit:
        pass   # suppressed in WASM environments


asyncio.run(main())

