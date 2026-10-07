"""
=============================================================================
game.py - Core Game Controller, State Machine, and Scalable Vector Renderer
=============================================================================
Educational Note:
The Finite State Machine (FSM) & Resolution-Independent Rendering:
  1. STATE MACHINE PATTERN:
     The game transitions between explicit states:
       - STATE_TITLE: Display retro logo, prompt player to start, attract mode
       - STATE_LAUNCHING: Ball waiting in plunger lane; spring charging
       - STATE_PLAYING: Main physics simulation; flippers active; scoring live
       - STATE_DRAINING: Brief intermission when ball falls past flippers
       - STATE_TILT: Table penalty if player nudges cabinet too aggressively
       - STATE_HIGH_SCORE_ENTRY: Interactive 3-letter initials input
       - STATE_VIEW_HIGH_SCORES: Leaderboard display table
       - STATE_GAME_OVER: End of 3-ball run summary

  2. RESOLUTION-INDEPENDENT VIRTUAL SURFACE:
     All gameplay, physics, and vector graphics are drawn onto a virtual
     500x800 surface (`virtual_screen`).
     The final image is smoothly scaled to the player's active window size
     using `pygame.transform.smoothscale()`. This allows players to:
       - Press [TAB] to toggle between Compact (380x608), Medium (440x704), and Large (500x800)
       - Press [-] or [+] to zoom in or out
       - Freely resize the window with the mouse!

  3. ANTI-STUCK WATCHDOG:
     In real pinball, balls occasionally settle into dead zones. Our game
     features an automated watchdog that detects if a ball is nearly stationary
     for over 1.0 second, automatically applying a dislodge pulse to keep the action moving.
=============================================================================
"""

import math
import random
import pygame
from pygame.math import Vector2

from constants import (
    VIRTUAL_WIDTH, VIRTUAL_HEIGHT, HUD_HEIGHT,
    COLOR_BLACK, COLOR_WHITE, COLOR_LIGHT_GRAY, COLOR_MID_GRAY, COLOR_DARK_GRAY,
    TABLE_SIZE_PRESETS, DEFAULT_SIZE_INDEX,
    INITIAL_BALLS, SCORE_BUMPER, SCORE_SLINGSHOT, SCORE_STANDUP_TARGET,
    SCORE_TARGET_BANK_CLEARED, SCORE_ROLLOVER_LANE, SCORE_ROLLOVER_ALL_BONUS,
    SCORE_SPINNER_PER_REV, SCORE_OUTLANE, MAX_MULTIPLIER,
    NUDGE_IMPULSE_X, NUDGE_IMPULSE_Y, TILT_WARNING_LIMIT, TILT_COOLDOWN_TIME,
    PHYSICS_SUB_STEPS,
    STATE_TITLE, STATE_LAUNCHING, STATE_PLAYING, STATE_DRAINING,
    STATE_TILT, STATE_GAME_OVER, STATE_HIGH_SCORE_ENTRY, STATE_VIEW_HIGH_SCORES
)
from table import Table
from audio import SoundManager
from highscores import HighScoreManager
from entities import VectorSpark


class PinballGame:
    """
    Main Game Controller orchestrating inputs, physics sub-stepping,
    scoring rules, audio triggers, and resolution-independent vector rendering.
    """
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.window_width = screen.get_width()
        self.window_height = screen.get_height()
        self.size_index = DEFAULT_SIZE_INDEX

        # Virtual 500x800 surface where all simulation and drawing takes place
        self.virtual_screen = pygame.Surface((VIRTUAL_WIDTH, VIRTUAL_HEIGHT))

        self.sound = SoundManager()
        self.highscores = HighScoreManager()
        self.table = Table()

        # Fonts for retro vector typography
        self.font_title = pygame.font.Font(None, 46)
        self.font_large = pygame.font.Font(None, 34)
        self.font_medium = pygame.font.Font(None, 24)
        self.font_small = pygame.font.Font(None, 18)

        # Game State Machine
        self.state = STATE_TITLE

        # Session Metrics
        self.score = 0
        self.multiplier = 1
        self.balls_left = INITIAL_BALLS
        self.extra_ball_awarded = False

        # Visual Flash Banner
        self.banner_text = ""
        self.banner_timer = 0.0

        # Vector Sparks collection
        self.sparks: list[VectorSpark] = []

        # Tilt / Nudge Tracking
        self.nudge_count = 0
        self.nudge_timer = 0.0
        self.tilt_timer = 0.0

        # Anti-Stuck Watchdog timer
        self.ball_stuck_timer = 0.0

        # High Score Entry State
        self.entry_initials = ["A", "A", "A"]
        self.entry_index = 0
        self.cursor_blink_timer = 0.0
        self.achieved_rank = 0

        # Start retro MIDI background music
        self.sound.start_music()

    # -------------------------------------------------------------------------
    # Window Resizing & Sizing Presets
    # -------------------------------------------------------------------------

    def cycle_table_size(self):
        """Cycles through Compact -> Medium -> Large table presets."""
        self.size_index = (self.size_index + 1) % len(TABLE_SIZE_PRESETS)
        preset = TABLE_SIZE_PRESETS[self.size_index]
        self.resize_window(preset["width"], preset["height"])
        self.set_banner(f"SIZE: {preset['name'].upper()} ({preset['width']}x{preset['height']})", 1.8)

    def adjust_scale(self, delta: float):
        """Scales current window up or down by percentage delta."""
        new_w = int(self.window_width * (1.0 + delta))
        new_h = int(self.window_height * (1.0 + delta))
        # Clamp within reasonable monitor bounds
        new_w = max(320, min(1200, new_w))
        new_h = max(512, min(1400, new_h))
        self.resize_window(new_w, new_h)
        self.set_banner(f"ZOOM: {new_w}x{new_h}", 1.5)

    def resize_window(self, w: int, h: int):
        """Reconfigures display surface to new dimensions while keeping aspect ratio."""
        self.window_width = max(320, w)
        self.window_height = max(500, h)
        self.screen = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE | pygame.DOUBLEBUF)

    # -------------------------------------------------------------------------
    # Game Flow Control Methods
    # -------------------------------------------------------------------------

    def start_new_game(self):
        """Initializes a fresh 3-ball pinball match."""
        self.score = 0
        self.multiplier = 1
        self.balls_left = INITIAL_BALLS
        self.extra_ball_awarded = False
        self.nudge_count = 0
        self.nudge_timer = 0.0
        self.ball_stuck_timer = 0.0
        self.sparks.clear()

        self.table.reset_ball_to_plunger()
        self.set_state(STATE_LAUNCHING)
        self.set_banner("BALL 1 - PULL SPRING!", 2.5)

    def set_state(self, new_state: str):
        self.state = new_state

    def set_banner(self, text: str, duration: float = 2.0):
        self.banner_text = text
        self.banner_timer = duration
      
    def award_points(self, base_points: int):
        pts = base_points * self.multiplier
        self.score += pts

        # Initialize tracking attributes if they don't exist yet
        if not hasattr(self, 'extra_ball_10k'): self.extra_ball_10k = False
        if not hasattr(self, 'extra_ball_20k'): self.extra_ball_20k = False
        if not hasattr(self, 'extra_ball_30k'): self.extra_ball_30k = False

        # 10,000 pts Extra Ball Award
        if not self.extra_ball_10k and self.score >= 10000:
            self.extra_ball_10k = True
            self.balls_left += 1
            self.sound.play_sound("high_score")
            self.set_banner("10K BONUS: EXTRA BALL!", 3.0)
        
        # 20,000 pts Extra Ball Award
        if not self.extra_ball_20k and self.score >= 20000:
            self.extra_ball_20k = True
            self.balls_left += 1
            self.sound.play_sound("high_score")
            self.set_banner("20K BONUS: EXTRA BALL!", 3.0)
   
        # 30,000 pts Extra Ball Award
        if not self.extra_ball_30k and self.score >= 30000:
            self.extra_ball_30k = True
            self.balls_left += 1
            self.sound.play_sound("high_score")
            self.set_banner("30K BONUS: EXTRA BALL!", 3.0)

    def emit_sparks(self, pos: Vector2, count: int = 8, speed: float = 140.0):
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            spd = random.uniform(speed * 0.4, speed)
            vel = Vector2(math.cos(angle), math.sin(angle)) * spd
            self.sparks.append(VectorSpark(pos, vel, lifespan=random.uniform(0.18, 0.35)))
       

    # -------------------------------------------------------------------------
    # Input Handling
    # -------------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event):
        """Dispatches keyboard inputs and window resize events."""
        if event.type == pygame.VIDEORESIZE:
            self.resize_window(event.w, event.h)
            return

        if event.type == pygame.KEYDOWN:
            # Table Size Controls: [TAB] to cycle presets, [-]/[+] to zoom
            if event.key == pygame.K_TAB:
                self.cycle_table_size()
                return
            elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                self.adjust_scale(-0.1)
                return
            elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                self.adjust_scale(0.1)
                return

            # Audio toggles
            if event.key == pygame.K_m:
                self.sound.toggle_music()
            elif event.key == pygame.K_s:
                self.sound.toggle_sfx()

            # State-specific input
            if self.state == STATE_TITLE:
                self._handle_title_input(event)
            elif self.state == STATE_VIEW_HIGH_SCORES:
                if event.key in (pygame.K_SPACE, pygame.K_ESCAPE, pygame.K_h):
                    self.set_state(STATE_TITLE)
            elif self.state in (STATE_LAUNCHING, STATE_PLAYING, STATE_TILT):
                self._handle_playing_keydown(event)
            elif self.state == STATE_HIGH_SCORE_ENTRY:
                self._handle_score_entry_input(event)
            elif self.state == STATE_GAME_OVER:
                if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    self.start_new_game()
                elif event.key == pygame.K_ESCAPE:
                    self.set_state(STATE_TITLE)

        elif event.type == pygame.KEYUP:
            if self.state in (STATE_LAUNCHING, STATE_PLAYING, STATE_TILT):
                self._handle_playing_keyup(event)

    def _handle_title_input(self, event: pygame.event.Event):
        if event.key == pygame.K_SPACE:
            self.start_new_game()
        elif event.key == pygame.K_h:
            self.set_state(STATE_VIEW_HIGH_SCORES)

    def _handle_playing_keydown(self, event: pygame.event.Event):
        # Flippers
        if self.state != STATE_TILT:
            if event.key in (pygame.K_a, pygame.K_z, pygame.K_LEFT, pygame.K_LSHIFT):
                if not self.table.left_flipper.is_active:
                    self.table.left_flipper.is_active = True
                    self.sound.play_sound("flipper_up")

            if event.key in (pygame.K_d, pygame.K_SLASH, pygame.K_RIGHT, pygame.K_RSHIFT):
                if not self.table.right_flipper.is_active:
                    self.table.right_flipper.is_active = True
                    self.sound.play_sound("flipper_up")

        # Plunger Launch Pull (When key is pressed down)
        if event.type == pygame.KEYDOWN:
           if self.state == STATE_LAUNCHING:
            if event.key in (pygame.K_DOWN, pygame.K_SPACE):
                self.table.plunger.start_pull()
                self.sound.play_sound("plunger_pull")

        # When the key is released (When key is released)
        elif event.type == pygame.KEYUP:
            if self.state == STATE_LAUNCHING:
             if event.key in (pygame.K_DOWN, pygame.K_SPACE):
                # Tell the plunger to actually release and fire the ball
                self.table.plunger.fire()

        # Nudge
        if self.state == STATE_PLAYING:
            if event.key in (pygame.K_w, pygame.K_t, pygame.K_SPACE):
                self._apply_table_nudge()

        if event.key == pygame.K_ESCAPE:
            self.set_state(STATE_TITLE)

    def _handle_playing_keyup(self, event: pygame.event.Event):
        # Flippers Release
        if event.key in (pygame.K_a, pygame.K_z, pygame.K_LEFT, pygame.K_LSHIFT):
            if self.table.left_flipper.is_active:
                self.table.left_flipper.is_active = False
                self.sound.play_sound("flipper_down")

        if event.key in (pygame.K_d, pygame.K_SLASH, pygame.K_RIGHT, pygame.K_RSHIFT):
            if self.table.right_flipper.is_active:
                self.table.right_flipper.is_active = False
                self.sound.play_sound("flipper_down")

        # Plunger Launch Release
        if self.state == STATE_LAUNCHING:
            if event.key in (pygame.K_DOWN, pygame.K_SPACE):
                self.table.plunger.release()
                self.sound.play_sound("plunger_release")

    def _handle_score_entry_input(self, event: pygame.event.Event):
        letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_!"
        current_char = self.entry_initials[self.entry_index]
        char_idx = letters.find(current_char) if current_char in letters else 0

        if event.key in (pygame.K_UP, pygame.K_w):
            char_idx = (char_idx - 1) % len(letters)
            self.entry_initials[self.entry_index] = letters[char_idx]
            self.sound.play_sound("plunger_pull")
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            char_idx = (char_idx + 1) % len(letters)
            self.entry_initials[self.entry_index] = letters[char_idx]
            self.sound.play_sound("plunger_pull")
        elif event.key in (pygame.K_LEFT, pygame.K_a):
            self.entry_index = max(0, self.entry_index - 1)
        elif event.key in (pygame.K_RIGHT, pygame.K_d):
            self.entry_index = min(2, self.entry_index + 1)
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            if self.entry_index < 2:
                self.entry_index += 1
            else:
                name = "".join(self.entry_initials)
                self.achieved_rank = self.highscores.add_score(name, self.score)
                self.sound.play_sound("bank_cleared")
                self.set_state(STATE_VIEW_HIGH_SCORES)
        elif event.unicode and event.unicode.upper() in letters:
            self.entry_initials[self.entry_index] = event.unicode.upper()
            if self.entry_index < 2:
                self.entry_index += 1

    def _apply_table_nudge(self):
        self.nudge_count += 1
        self.nudge_timer = TILT_COOLDOWN_TIME

        impulse_x = random.choice([-1.0, 1.0]) * NUDGE_IMPULSE_X
        self.table.ball.vel.x += impulse_x
        self.table.ball.vel.y += NUDGE_IMPULSE_Y

        if self.nudge_count >= TILT_WARNING_LIMIT:
            self.set_state(STATE_TILT)
            self.tilt_timer = 4.0
            self.table.left_flipper.is_active = False
            self.table.right_flipper.is_active = False
            self.sound.play_sound("tilt")
            self.set_banner("!!! TILT !!!", 3.0)
        else:
            self.sound.play_sound("slingshot")
            remaining = TILT_WARNING_LIMIT - self.nudge_count
            self.set_banner(f"WARNING: NUDGE! ({remaining} LEFT)", 1.2)

    # -------------------------------------------------------------------------
    # Main Simulation Update Loop
    # -------------------------------------------------------------------------

    def update(self, dt: float):
        if self.banner_timer > 0.0:
            self.banner_timer = max(0.0, self.banner_timer - dt)

        self.sparks = [s for s in self.sparks if s.update(dt)]

        fired = self.table.plunger.update(dt, self.table.ball)
        if fired and self.state == STATE_LAUNCHING:
            self.set_state(STATE_PLAYING)

        if self.nudge_timer > 0.0:
            self.nudge_timer = max(0.0, self.nudge_timer - dt)
            if self.nudge_timer == 0.0:
                self.nudge_count = 0

        if self.state == STATE_TILT:
            self.tilt_timer = max(0.0, self.tilt_timer - dt)

        # Anti-Stuck Watchdog:
        # If ball is in active play but nearly motionless (< 25 px/s) for over 1.0 second,
        # dislodge it with a gentle mechanical table nudge!
        if self.state in (STATE_PLAYING, STATE_TILT) and self.table.ball.in_play:
            if self.table.ball.vel.length_squared() < 625.0:
                self.ball_stuck_timer += dt
                if self.ball_stuck_timer > 1.0:
                    self.table.ball.vel = Vector2(random.choice([-60.0, 60.0]), 200.0)
                    self.ball_stuck_timer = 0.0
                    self.sound.play_sound("slingshot")
                    self.set_banner("TABLE NUDGE", 1.0)
            else:
                self.ball_stuck_timer = 0.0

        # Frame animations
        frame_events = self.table.update_frame(dt)
        if frame_events["target_bank_cleared"]:
            self.award_points(SCORE_TARGET_BANK_CLEARED)
            self.sound.play_sound("bank_cleared")
            self.set_banner("5000 BONUS: TARGETS CLEARED!", 2.5)

        if frame_events["rollover_all_lit"]:
            self.multiplier = min(MAX_MULTIPLIER, self.multiplier + 1)
            self.award_points(SCORE_ROLLOVER_ALL_BONUS)
            self.sound.play_sound("bank_cleared")
            self.set_banner(f"BONUS MULTIPLIER: {self.multiplier}X!", 2.5)

        if frame_events["spinner_revolutions"] > 0:
            self.award_points(SCORE_SPINNER_PER_REV * frame_events["spinner_revolutions"])
            self.sound.play_sound("spinner")

        # High-Frequency Sub-Stepping
        if self.state in (STATE_LAUNCHING, STATE_PLAYING, STATE_TILT):
            dt_sub = dt / PHYSICS_SUB_STEPS
            for _ in range(PHYSICS_SUB_STEPS):
                sub_events = self.table.update_physics_substep(dt_sub)

                if sub_events["bumper_hit"]:
                    self.award_points(SCORE_BUMPER)
                    self.sound.play_sound("bumper")
                    self.emit_sparks(self.table.ball.pos, count=8, speed=160.0)

                if sub_events["slingshot_hit"]:
                    self.award_points(SCORE_SLINGSHOT)
                    self.sound.play_sound("slingshot")
                    self.emit_sparks(self.table.ball.pos, count=5, speed=120.0)

                if sub_events["target_hit"]:
                    self.award_points(SCORE_STANDUP_TARGET)
                    self.sound.play_sound("target_hit")
                    self.emit_sparks(self.table.ball.pos, count=6, speed=130.0)

                if sub_events["rollover_hit"]:
                    self.award_points(SCORE_ROLLOVER_LANE)
                    self.sound.play_sound("rollover")

                if sub_events["drained"]:
                    self._handle_ball_drain()
                    break

        if self.state == STATE_HIGH_SCORE_ENTRY:
            self.cursor_blink_timer += dt

    def _handle_ball_drain(self):
        self.sound.play_sound("drain")
        self.balls_left -= 1
        self.multiplier = 1

        if self.balls_left > 0:
            self.table.reset_ball_to_plunger()
            self.set_state(STATE_LAUNCHING)
            ball_num = INITIAL_BALLS - self.balls_left + 1
            self.set_banner(f"BALL {ball_num} READY", 2.5)
        else:
            if self.highscores.is_high_score(self.score):
                self.sound.play_sound("high_score")
                self.set_state(STATE_HIGH_SCORE_ENTRY)
                self.entry_index = 0
                self.set_banner("NEW HIGH SCORE! ENTER INITIALS", 3.0)
            else:
                self.set_state(STATE_GAME_OVER)
                self.set_banner("GAME OVER", 3.5)

    # -------------------------------------------------------------------------
    # Render Pipeline (Virtual Surface + Dynamic Aspect-Preserving Scaling)
    # -------------------------------------------------------------------------

    def render(self):
        """Draws the virtual 500x800 surface and smoothly scales it to the window."""
        # 1. Clear Virtual Screen
        self.virtual_screen.fill(COLOR_BLACK)

        # 2. Draw Table Playfield
        self.table.draw(self.virtual_screen, self.font_small)

        # 3. Draw Vector Sparks
        for spark in self.sparks:
            spark.draw(self.virtual_screen)

        # 4. Draw Header HUD
        self._render_hud()

        # 5. Draw Overlays
        if self.state == STATE_TITLE:
            self._render_title_overlay()
        elif self.state == STATE_LAUNCHING:
            self._render_launch_prompt()
        elif self.state == STATE_HIGH_SCORE_ENTRY:
            self._render_score_entry_overlay()
        elif self.state == STATE_VIEW_HIGH_SCORES:
            self._render_high_scores_overlay()
        elif self.state == STATE_GAME_OVER:
            self._render_game_over_overlay()

        # 6. Flash Banner
        if self.banner_timer > 0.0 and self.state != STATE_TITLE:
            self._render_banner()

        # 7. Subtle vector border frame around virtual table
        pygame.draw.rect(self.virtual_screen, COLOR_LIGHT_GRAY, (0, 0, VIRTUAL_WIDTH, VIRTUAL_HEIGHT), 2)

        # 8. Aspect-Preserving Viewport Scaling onto Physical Window
        scale = min(self.window_width / VIRTUAL_WIDTH, self.window_height / VIRTUAL_HEIGHT)
        scaled_w = max(1, int(VIRTUAL_WIDTH * scale))
        scaled_h = max(1, int(VIRTUAL_HEIGHT * scale))
        offset_x = (self.window_width - scaled_w) // 2
        offset_y = (self.window_height - scaled_h) // 2

        scaled_surf = pygame.transform.smoothscale(self.virtual_screen, (scaled_w, scaled_h))
        self.screen.fill(COLOR_BLACK)
        self.screen.blit(scaled_surf, (offset_x, offset_y))

    def _render_hud(self):
        pygame.draw.line(self.virtual_screen, COLOR_LIGHT_GRAY, (0, HUD_HEIGHT), (VIRTUAL_WIDTH, HUD_HEIGHT), 2)

        # Score
        score_lbl = self.font_small.render("SCORE", True, COLOR_MID_GRAY)
        score_val = self.font_large.render(f"{self.score:,}", True, COLOR_WHITE)
        self.virtual_screen.blit(score_lbl, (25, 6))
        self.virtual_screen.blit(score_val, (25, 23))

        # High Score
        top_score = max(self.score, self.highscores.get_top_score())
        top_lbl = self.font_small.render("HIGH SCORE", True, COLOR_MID_GRAY)
        top_val = self.font_large.render(f"{top_score:,}", True, COLOR_LIGHT_GRAY)
        self.virtual_screen.blit(top_lbl, (190, 6))
        self.virtual_screen.blit(top_val, (190, 23))

        # Ball
        ball_lbl = self.font_small.render("BALL", True, COLOR_MID_GRAY)
        cur_ball = max(1, INITIAL_BALLS - self.balls_left + 1) if self.balls_left > 0 else 3
        ball_val = self.font_large.render(f"{cur_ball}/{INITIAL_BALLS}", True, COLOR_WHITE)
        self.virtual_screen.blit(ball_lbl, (390, 6))
        self.virtual_screen.blit(ball_val, (390, 23))

        # Multiplier
        if self.multiplier > 1:
            mult_txt = self.font_medium.render(f"{self.multiplier}X", True, COLOR_WHITE)
            pygame.draw.rect(self.virtual_screen, COLOR_WHITE, (330, 23, 40, 22), 1)
            self.virtual_screen.blit(mult_txt, (337, 26))

    def _render_banner(self):
        txt = self.font_medium.render(self.banner_text, True, COLOR_WHITE)
        rect = txt.get_rect(center=(VIRTUAL_WIDTH // 2, 440))
        bg_rect = rect.inflate(24, 12)
        pygame.draw.rect(self.virtual_screen, COLOR_BLACK, bg_rect)
        pygame.draw.rect(self.virtual_screen, COLOR_WHITE, bg_rect, 1)
        self.virtual_screen.blit(txt, rect)

    def _render_launch_prompt(self):
        txt = self.font_small.render("HOLD [SPACE] OR [DOWN] TO PLUNGE", True, COLOR_LIGHT_GRAY)
        rect = txt.get_rect(center=(VIRTUAL_WIDTH // 2, 735))
        self.virtual_screen.blit(txt, rect)

    def _render_title_overlay(self):
        overlay = pygame.Surface((VIRTUAL_WIDTH, VIRTUAL_HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 10, 12, 235))
        self.virtual_screen.blit(overlay, (0, 0))

        t1 = self.font_title.render("P Y P I N B A L L", True, COLOR_WHITE)
        t1_rect = t1.get_rect(center=(VIRTUAL_WIDTH // 2, 200))
        self.virtual_screen.blit(t1, t1_rect)
        pygame.draw.line(self.virtual_screen, COLOR_WHITE, (t1_rect.left, t1_rect.bottom + 4), (t1_rect.right, t1_rect.bottom + 4), 2)

        subtitle = self.font_medium.render("RETRO VECTOR ARCADE PINBALL", True, COLOR_MID_GRAY)
        self.virtual_screen.blit(subtitle, subtitle.get_rect(center=(VIRTUAL_WIDTH // 2, 238)))

        # Control Guide Box
        box_rect = pygame.Rect(55, 280, VIRTUAL_WIDTH - 110, 310)
        pygame.draw.rect(self.virtual_screen, COLOR_DARK_GRAY, box_rect, 1)

        instructions = [
            ("LEFT FLIPPER", "[A] / [Z] / [LEFT]"),
            ("RIGHT FLIPPER", "[D] / [/] / [RIGHT]"),
            ("PLUNGER SPRING", "HOLD & RELEASE [SPACE]"),
            ("TABLE NUDGE", "[W] or [T] (BEWARE TILT!)"),
            ("TABLE SIZE", "[TAB] or [-]/[+] TO RESIZE"),
            ("HIGH SCORES", "[H]"),
            ("MUSIC TOGGLE", "[M]"),
            ("SOUND SFX TOGGLE", "[S]"),
        ]
        start_y = 295
        for action, key in instructions:
            act_txt = self.font_small.render(action, True, COLOR_MID_GRAY)
            key_txt = self.font_small.render(key, True, COLOR_WHITE)
            self.virtual_screen.blit(act_txt, (75, start_y))
            self.virtual_screen.blit(key_txt, (250, start_y))
            start_y += 32

        if int(pygame.time.get_ticks() / 500) % 2 == 0:
            prompt = self.font_large.render("PRESS [SPACE] TO START", True, COLOR_WHITE)
            self.virtual_screen.blit(prompt, prompt.get_rect(center=(VIRTUAL_WIDTH // 2, 640)))

        # Current Size Indicator
        cur_preset = TABLE_SIZE_PRESETS[self.size_index]["name"]
        size_lbl = self.font_small.render(f"CURRENT SIZE: {cur_preset.upper()} (PRESS TAB TO RESIZE)", True, COLOR_MID_GRAY)
        self.virtual_screen.blit(size_lbl, size_lbl.get_rect(center=(VIRTUAL_WIDTH // 2, 690)))

    def _render_score_entry_overlay(self):
        overlay = pygame.Surface((VIRTUAL_WIDTH, VIRTUAL_HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 10, 12, 225))
        self.virtual_screen.blit(overlay, (0, 0))

        title = self.font_title.render("NEW HIGH SCORE!", True, COLOR_WHITE)
        self.virtual_screen.blit(title, title.get_rect(center=(VIRTUAL_WIDTH // 2, 230)))

        score_txt = self.font_large.render(f"{self.score:,} POINTS", True, COLOR_LIGHT_GRAY)
        self.virtual_screen.blit(score_txt, score_txt.get_rect(center=(VIRTUAL_WIDTH // 2, 280)))

        sub = self.font_small.render("USE [UP]/[DOWN] TO CHANGE LETTER, [ENTER] TO CONFIRM", True, COLOR_MID_GRAY)
        self.virtual_screen.blit(sub, sub.get_rect(center=(VIRTUAL_WIDTH // 2, 330)))

        slot_x_start = (VIRTUAL_WIDTH // 2) - 80
        blink = int(self.cursor_blink_timer * 3) % 2 == 0

        for i in range(3):
            sx = slot_x_start + i * 60
            char = self.entry_initials[i]
            char_surf = self.font_title.render(char, True, COLOR_WHITE)
            self.virtual_screen.blit(char_surf, char_surf.get_rect(center=(sx + 20, 410)))

            if i == self.entry_index and blink:
                pygame.draw.line(self.virtual_screen, COLOR_WHITE, (sx + 5, 445), (sx + 35, 445), 3)
            else:
                pygame.draw.line(self.virtual_screen, COLOR_DARK_GRAY, (sx + 5, 445), (sx + 35, 445), 2)

    def _render_high_scores_overlay(self):
        overlay = pygame.Surface((VIRTUAL_WIDTH, VIRTUAL_HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 10, 12, 235))
        self.virtual_screen.blit(overlay, (0, 0))

        title = self.font_title.render("HALL OF FAME", True, COLOR_WHITE)
        self.virtual_screen.blit(title, title.get_rect(center=(VIRTUAL_WIDTH // 2, 140)))

        header_rank = self.font_small.render("RANK", True, COLOR_MID_GRAY)
        header_name = self.font_small.render("NAME", True, COLOR_MID_GRAY)
        header_score = self.font_small.render("SCORE", True, COLOR_MID_GRAY)
        header_date = self.font_small.render("DATE", True, COLOR_MID_GRAY)

        self.virtual_screen.blit(header_rank, (70, 195))
        self.virtual_screen.blit(header_name, (135, 195))
        self.virtual_screen.blit(header_score, (220, 195))
        self.virtual_screen.blit(header_date, (340, 195))

        pygame.draw.line(self.virtual_screen, COLOR_MID_GRAY, (70, 215), (430, 215), 1)

        y = 230
        for idx, entry in enumerate(self.highscores.scores):
            rank_txt = self.font_medium.render(f"#{idx + 1}", True, COLOR_LIGHT_GRAY)
            name_txt = self.font_medium.render(entry["name"], True, COLOR_WHITE)
            score_txt = self.font_medium.render(f"{entry['score']:,}", True, COLOR_WHITE)
            date_txt = self.font_small.render(entry.get("date", "---"), True, COLOR_MID_GRAY)

            self.virtual_screen.blit(rank_txt, (70, y))
            self.virtual_screen.blit(name_txt, (135, y))
            self.virtual_screen.blit(score_txt, (220, y))
            self.virtual_screen.blit(date_txt, (340, y + 2))
            y += 38

        prompt = self.font_small.render("PRESS [SPACE] OR [ESC] TO RETURN", True, COLOR_LIGHT_GRAY)
        self.virtual_screen.blit(prompt, prompt.get_rect(center=(VIRTUAL_WIDTH // 2, 660)))

    def _render_game_over_overlay(self):
        overlay = pygame.Surface((VIRTUAL_WIDTH, VIRTUAL_HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 10, 12, 220))
        self.virtual_screen.blit(overlay, (0, 0))

        title = self.font_title.render("G A M E   O V E R", True, COLOR_WHITE)
        self.virtual_screen.blit(title, title.get_rect(center=(VIRTUAL_WIDTH // 2, 290)))

        score_txt = self.font_large.render(f"FINAL SCORE: {self.score:,}", True, COLOR_LIGHT_GRAY)
        self.virtual_screen.blit(score_txt, score_txt.get_rect(center=(VIRTUAL_WIDTH // 2, 350)))

        prompt = self.font_medium.render("PRESS [SPACE] TO PLAY AGAIN", True, COLOR_WHITE)
        self.virtual_screen.blit(prompt, prompt.get_rect(center=(VIRTUAL_WIDTH // 2, 440)))

        esc_prompt = self.font_small.render("PRESS [ESC] FOR MAIN MENU", True, COLOR_MID_GRAY)
        self.virtual_screen.blit(esc_prompt, esc_prompt.get_rect(center=(VIRTUAL_WIDTH // 2, 480)))
