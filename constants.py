"""
=============================================================================
constants.py - Global Configuration, Physics & Sizing Presets for PyPinball
=============================================================================
Educational Note:
Resolution-Independent Game Design:
Monitors and laptop screens come in various resolutions. If a game hardcodes
pixel coordinates to an 860px window, it may overflow on smaller laptop screens.

To provide seamless scaling while keeping physics math 100% deterministic:
  1. VIRTUAL COORDINATES (500 x 800):
     All physics, collision geometry, flippers, and bumpers live in a fixed
     "virtual coordinate space". This ensures game mechanics and collision
     detection never alter when the window is resized.
  2. DYNAMIC VIEWPORT SCALING:
     The game renders all vector art onto a 500x800 virtual surface, and
     smoothly scales it to fit the player's active window using
     `pygame.transform.smoothscale()`, preserving the classic vertical aspect ratio.
  3. TABLE SIZE PRESETS:
     Players can press [TAB] or [-] / [+] to toggle between Compact, Medium,
     and Large table sizes, or freely drag the window border to any size!
=============================================================================
"""

import os
from pathlib import Path

# -----------------------------------------------------------------------------
# File System Paths
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
HIGHSCORES_FILE = BASE_DIR / "highscores.json"
MIDI_MUSIC_FILE = BASE_DIR / "pypinball_theme.mid"

# -----------------------------------------------------------------------------
# Base Virtual Coordinate System (Fixed for Physics Simulation)
# -----------------------------------------------------------------------------
VIRTUAL_WIDTH = 500
VIRTUAL_HEIGHT = 800
FPS = 60
WINDOW_TITLE = "FREAKER126 PyPinball - Retro Vector Arcade (Black & White)"

# Playfield Boundaries within the Virtual Coordinate Space
HUD_HEIGHT = 65
PLAYFIELD_LEFT = 25
PLAYFIELD_RIGHT = 475                    # 450 px wide playfield
PLAYFIELD_TOP = HUD_HEIGHT               # 65
PLAYFIELD_BOTTOM = 775                   # Bottom trough

# Plunger Lane Dimensions (located on the far right)
PLUNGER_LANE_WIDTH = 34
PLUNGER_LANE_X = PLAYFIELD_RIGHT - PLUNGER_LANE_WIDTH  # 441
PLUNGER_REST_Y = PLAYFIELD_BOTTOM - 25   # 750
PLUNGER_MAX_PULL = 50.0                  # Maximum spring displacement in pixels
PLUNGER_CHARGE_RATE = 40.0              # Rapid spring compression rate
PLUNGER_RELEASE_SPEED = 700.0            # Snappy spring release velocity
PLUNGER_MIN_LAUNCH_SPEED = 1050.0        # High minimum launch speed to easily clear arch
PLUNGER_MAX_LAUNCH_SPEED = 1700.0        # Maximum launch speed at full compression

# -----------------------------------------------------------------------------
# Table Size Presets (User-selectable on the fly)
# -----------------------------------------------------------------------------
TABLE_SIZE_PRESETS = [
    {"name": "Compact", "width": 380, "height": 608},  # ~76% - Ideal for laptops / small screens
    {"name": "Medium",  "width": 440, "height": 704},  # ~88% - Default comfortable size
    {"name": "Large",   "width": 500, "height": 800},  # 100% - Full virtual resolution
]
DEFAULT_SIZE_INDEX = 1                   # Start at Medium (440 x 704) by default
WINDOW_WIDTH = TABLE_SIZE_PRESETS[DEFAULT_SIZE_INDEX]["width"]
WINDOW_HEIGHT = TABLE_SIZE_PRESETS[DEFAULT_SIZE_INDEX]["height"]

# -----------------------------------------------------------------------------
# Color Palette (Retro Monochrome / CRT Vector Aesthetics)
# -----------------------------------------------------------------------------
COLOR_BLACK = (10, 10, 12)               # Deep vector black background
COLOR_WHITE = (255, 255, 255)            # Vector beam bright white
COLOR_LIGHT_GRAY = (215, 215, 220)       # High-contrast light gray
COLOR_MID_GRAY = (140, 140, 148)         # Mid-tone gray
COLOR_DARK_GRAY = (55, 55, 62)           # Dark gray for structural accents
COLOR_PHOSPHOR_DIM = (24, 24, 28)        # Very faint phosphor glow

# -----------------------------------------------------------------------------
# Physics Engine Parameters
# -----------------------------------------------------------------------------
GRAVITY = 660.0                          # Downward gravitational acceleration (px/s^2)
PHYSICS_SUB_STEPS = 8                    # Sub-steps per frame to prevent tunneling

# Ball Specifications
BALL_RADIUS = 8.5                        # Radius in virtual pixels
BALL_MASS = 1.0
BALL_RESTITUTION = 0.68                  # Bounciness against metal walls
BALL_RUBBER_RESTITUTION = 0.88           # Bounciness against rubber bands
BALL_MAX_SPEED = 1600.0                  # Safety speed ceiling (px/s)
BALL_AIR_DRAG = 0.9996                   # Minimal air drag

# Flipper Kinematics
FLIPPER_LENGTH = 60.0                    # Arm length in virtual pixels
FLIPPER_REST_ANGLE = 28.0                # Degrees sloping downward at rest
FLIPPER_UP_ANGLE = -27.0                 # Degrees pointing upward when activated
FLIPPER_ANGULAR_SPEED = 760.0            # Degrees per second rotation speed
FLIPPER_WIDTH_BASE = 14.0                # Pivot thickness
FLIPPER_WIDTH_TIP = 7.0                  # Tip thickness

# Pop Bumpers (The trio of circular electromagnets)
BUMPER_RADIUS = 22.0
BUMPER_POP_FORCE = 540.0                 # Outward launch impulse speed on impact

# Slingshots (Triangles above flippers)
SLINGSHOT_FORCE = 480.0                  # Active kick impulse away from rubber face

# Tilt & Nudge Mechanics
NUDGE_IMPULSE_X = 95.0
NUDGE_IMPULSE_Y = -65.0
TILT_WARNING_LIMIT = 3
TILT_COOLDOWN_TIME = 4.0
TILT_PENALTY_DURATION = 3.5

# -----------------------------------------------------------------------------
# Scoring & Pinball Gameplay Rules
# -----------------------------------------------------------------------------
INITIAL_BALLS = 3
SCORE_BUMPER = 100
SCORE_SLINGSHOT = 50
SCORE_STANDUP_TARGET = 250
SCORE_TARGET_BANK_CLEARED = 5000         # Bonus when all 4 drop targets are hit
SCORE_ROLLOVER_LANE = 500
SCORE_ROLLOVER_ALL_BONUS = 3000          # Multiplier increment + point bonus
SCORE_SPINNER_PER_REV = 40
SCORE_OUTLANE = 1000
SCORE_INLANE = 300
MAX_MULTIPLIER = 5

# -----------------------------------------------------------------------------
# Game States (State Machine Pattern)
# -----------------------------------------------------------------------------
STATE_TITLE = "STATE_TITLE"
STATE_LAUNCHING = "STATE_LAUNCHING"
STATE_PLAYING = "STATE_PLAYING"
STATE_DRAINING = "STATE_DRAINING"
STATE_TILT = "STATE_TILT"
STATE_GAME_OVER = "STATE_GAME_OVER"
STATE_HIGH_SCORE_ENTRY = "STATE_HIGH_SCORE_ENTRY"
STATE_VIEW_HIGH_SCORES = "STATE_VIEW_HIGH_SCORES"
