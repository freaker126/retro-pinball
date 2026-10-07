"""
=============================================================================
main.py - Entry Point for PyPinball (Retro Monochrome Arcade)
=============================================================================
Educational Note:
The Heart of Every Real-Time Game: The Master Game Loop.

Almost all real-time interactive simulations (from Pong to modern 3D games)
operate on a continuous three-phase cycle executed 60 times per second:

  1. PROCESS INPUT (Events):
     Query the operating system's event queue for keyboard presses, releases,
     mouse movements, and window close buttons.
     `pygame.event.get()` drains this queue every frame.

  2. UPDATE STATE (Simulation):
     Compute how objects move and interact over the elapsed time `dt`.
     `dt = clock.tick(FPS) / 1000.0` gives the exact fractional seconds
     that passed since the last frame. Multiplying speeds by `dt` guarantees
     that physics simulations run at the same speed on any computer,
     regardless of CPU speed.

  3. RENDER OUTPUT (Drawing):
     Clear the display buffer, draw all visual elements, and swap the
     hidden back-buffer to the physical monitor using `pygame.display.flip()`.
     Double-buffering eliminates visual screen tearing and flickering.

Controls:
  - [A] / [Z] / [LEFT ARROW]  : Left Flipper
  - [D] / [/] / [RIGHT ARROW] : Right Flipper
  - [SPACE] / [DOWN ARROW]    : Pull & Release Plunger Spring (Launch)
  - [W] / [T]                 : Table Nudge (Tilt Warning!)
  - [H]                       : Hall of Fame (High Scores)
  - [M]                       : Toggle Retro MIDI Background Music
  - [S]                       : Toggle Sound Effects
  - [ESC]                     : Return to Title / Quit
=============================================================================
"""

import sys
import pygame

from constants import (
    WINDOW_WIDTH, WINDOW_HEIGHT, FPS, WINDOW_TITLE
)
from game import PinballGame


def main():
    """Initializes Pygame, opens window, and runs the master game loop."""
    # 1. Initialize Pygame core modules
    pygame.init()
    pygame.font.init()

    # 2. Configure Game Window & Double-Buffered Display Surface (Resizable)
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE | pygame.DOUBLEBUF)
    pygame.display.set_caption(WINDOW_TITLE)

    # 3. Create high-resolution frame clock to regulate FPS
    clock = pygame.time.Clock()

    # 4. Instantiate the Master Game Controller
    game = PinballGame(screen)

    print("=" * 65)
    print("  * * *   P Y P I N B A L L   * * *")
    print("  Retro Vector Arcade Pinball (Black & White)")
    print("=" * 65)
    print("Controls:")
    print("  [A] / [Z] / [LEFT]   - Left Flipper")
    print("  [D] / [/] / [RIGHT]  - Right Flipper")
    print("  [SPACE] / [DOWN]     - Pull & Release Plunger Spring")
    print("  [W] / [T]            - Nudge Table (Watch out for TILT!)")
    print("  [TAB]                - Cycle Table Size (Compact / Medium / Large)")
    print("  [-] / [+]            - Zoom Table In / Out")
    print("  [H]                  - High Scores Leaderboard")
    print("  [M]                  - Toggle MIDI Music")
    print("  [S]                  - Toggle Sound Effects")
    print("  [ESC]                - Back to Menu / Quit")
    print("=" * 65)

    running = True

    # 5. Master Game Loop
    while running:
        # Measure delta time in seconds (clamped to prevent crazy spikes if window dragged)
        dt = clock.tick(FPS) / 1000.0
        dt = min(dt, 0.05)

        # Step 1: Input Event Dispatching
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            else:
                game.handle_event(event)

        # Step 2: Physics Simulation & State Updates
        game.update(dt)

        # Step 3: Monochrome Vector Render Pipeline
        game.render()

        # Step 4: Swap Back Buffer to Display Screen
        pygame.display.flip()

    # 6. Clean Exit
    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
