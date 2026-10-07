"""
=============================================================================
test_pypinball.py - Comprehensive Unit & Headless Integration Test Suite
=============================================================================
Educational Note:
Automated Testing in Game Development:
Writing automated tests for games ensures that:
  1. Physics calculations don't break when modifying parameters.
  2. Data persistence (high scores) works reliably across crashes and restarts.
  3. Audio assets (MIDI files and synthesized PCM sounds) are created properly.
  4. The game loop can run dozens of frames without runtime exceptions or memory leaks.

This test script uses Python's standard `unittest` framework and can be run
completely headless (without opening a graphical window) by setting:
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
=============================================================================
"""

import os
import sys
import unittest
from pathlib import Path

# Force headless execution for testing
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
from pygame.math import Vector2

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from constants import (
    WINDOW_WIDTH, WINDOW_HEIGHT, BALL_RADIUS, GRAVITY,
    STATE_TITLE, STATE_LAUNCHING, STATE_PLAYING, STATE_DRAINING
)
from physics import (
    clamp, closest_point_on_segment, check_circle_segment_collision,
    check_circle_circle_collision, resolve_elastic_reflection
)
from entities import (
    Ball, Flipper, Bumper, Slingshot, StandupTarget, TargetBank,
    RolloverLane, SpinnerGate, Plunger
)
from audio import encode_variable_length_quantity, generate_retro_midi_track, SoundManager
from highscores import HighScoreManager
from table import Table
from game import PinballGame


class TestPhysicsMath(unittest.TestCase):
    """Verifies 2D vector mathematics and collision functions."""

    def test_clamp(self):
        self.assertEqual(clamp(5.0, 0.0, 10.0), 5.0)
        self.assertEqual(clamp(-5.0, 0.0, 10.0), 0.0)
        self.assertEqual(clamp(15.0, 0.0, 10.0), 10.0)

    def test_closest_point_on_segment(self):
        p1 = Vector2(0, 0)
        p2 = Vector2(100, 0)

        # Point directly above center of segment
        pt, t = closest_point_on_segment(Vector2(50, 20), p1, p2)
        self.assertAlmostEqual(pt.x, 50.0)
        self.assertAlmostEqual(pt.y, 0.0)
        self.assertAlmostEqual(t, 0.5)

        # Point to the left of start
        pt, t = closest_point_on_segment(Vector2(-30, 0), p1, p2)
        self.assertAlmostEqual(pt.x, 0.0)
        self.assertAlmostEqual(t, 0.0)

        # Point to the right of end
        pt, t = closest_point_on_segment(Vector2(140, 10), p1, p2)
        self.assertAlmostEqual(pt.x, 100.0)
        self.assertAlmostEqual(t, 1.0)

    def test_circle_segment_collision(self):
        p1 = Vector2(0, 50)
        p2 = Vector2(100, 50)
        ball_pos = Vector2(50, 45)  # 5 units above line; radius is 8.5
        col = check_circle_segment_collision(ball_pos, 8.5, p1, p2)
        self.assertTrue(col.occurred)
        self.assertAlmostEqual(col.depth, 3.5)
        self.assertAlmostEqual(col.normal.y, -1.0)

        # Far away point (no collision)
        col_miss = check_circle_segment_collision(Vector2(50, 20), 8.5, p1, p2)
        self.assertFalse(col_miss.occurred)

    def test_circle_circle_collision(self):
        c1 = Vector2(100, 100)
        c2 = Vector2(130, 100)
        col = check_circle_circle_collision(c1, 10.0, c2, 25.0)
        # Distance = 30; sum of radii = 35; penetration = 5
        self.assertTrue(col.occurred)
        self.assertAlmostEqual(col.depth, 5.0)

    def test_elastic_reflection(self):
        vel = Vector2(100, 100)
        normal = Vector2(0, -1)  # Bouncing off horizontal floor
        refl = resolve_elastic_reflection(vel, normal, restitution=1.0, friction=1.0)
        self.assertAlmostEqual(refl.x, 100.0)
        self.assertAlmostEqual(refl.y, -100.0)


class TestEntities(unittest.TestCase):
    """Tests interactive entity logic and state progression."""

    def test_ball_integration(self):
        ball = Ball(100, 100)
        ball.in_play = True
        ball.vel = Vector2(50, 0)
        ball.update_physics(0.1, apply_gravity=False)
        self.assertAlmostEqual(ball.pos.x, 105.0, places=2)

    def test_flipper_rotation(self):
        flipper = Flipper(pivot=Vector2(100, 100), is_left=True)
        self.assertEqual(flipper.current_angle, flipper.angle_rest)
        flipper.is_active = True
        flipper.update(0.1)
        self.assertNotEqual(flipper.current_angle, flipper.angle_rest)

    def test_bumper_active_kick(self):
        bumper = Bumper(x=200, y=200, radius=24.0)
        ball = Ball(x=200, y=180)  # Falling down into bumper
        ball.vel = Vector2(0, 100)
        hit = bumper.check_ball_collision(ball)
        self.assertTrue(hit)
        self.assertLess(ball.vel.y, 0)  # Ball pushed upwards!

    def test_target_bank(self):
        targets = [
            StandupTarget(Vector2(0, 0), Vector2(0, 20)),
            StandupTarget(Vector2(0, 30), Vector2(0, 50))
        ]
        bank = TargetBank(targets)
        self.assertFalse(all(t.is_hit for t in targets))
        targets[0].is_hit = True
        targets[1].is_hit = True
        # Update bank timer
        bank.update(0.5)
        self.assertTrue(bank.reset_timer > 0.0)

    def test_plunger_launch(self):
        plunger = Plunger(x=100, rest_y=500)
        ball = Ball(x=100, y=488)
        plunger.start_pull()
        for _ in range(10):
            plunger.update(0.05, ball)
        self.assertGreater(plunger.pull_amount, 0.0)
        plunger.release()
        fired = False
        for _ in range(20):
            if plunger.update(0.02, ball):
                fired = True
        self.assertTrue(fired or ball.in_play)


class TestAudioAndMIDI(unittest.TestCase):
    """Verifies pure-Python MIDI file generation and sound synthesis."""

    def test_varlen_encoding(self):
        self.assertEqual(encode_variable_length_quantity(0), b'\x00')
        self.assertEqual(encode_variable_length_quantity(127), b'\x7F')
        self.assertEqual(encode_variable_length_quantity(128), b'\x81\x00')

    def test_midi_file_compilation(self):
        temp_midi = BASE_DIR / "test_temp.mid"
        try:
            generate_retro_midi_track(temp_midi)
            self.assertTrue(temp_midi.exists())
            self.assertGreater(temp_midi.stat().st_size, 500)
            with open(temp_midi, "rb") as f:
                header = f.read(4)
                self.assertEqual(header, b"MThd")
        finally:
            if temp_midi.exists():
                temp_midi.unlink()

    def test_sound_manager(self):
        pygame.init()
        sm = SoundManager()
        self.assertIn("bumper", sm.sounds)
        self.assertIn("flipper_up", sm.sounds)
        self.assertIn("plunger_release", sm.sounds)


class TestHighScores(unittest.TestCase):
    """Tests JSON leaderboard loading, saving, and qualification."""

    def test_high_score_manager(self):
        test_file = BASE_DIR / "test_highscores.json"
        try:
            if test_file.exists():
                test_file.unlink()

            mgr = HighScoreManager(filepath=test_file)
            self.assertGreater(len(mgr.scores), 0)

            # Test qualification
            self.assertTrue(mgr.is_high_score(999999))
            self.assertFalse(mgr.is_high_score(0))

            # Add score
            rank = mgr.add_score("TST", 999999)
            self.assertEqual(rank, 1)
            self.assertEqual(mgr.get_top_score(), 999999)

            # Reload from disk
            mgr_reloaded = HighScoreManager(filepath=test_file)
            self.assertEqual(mgr_reloaded.get_top_score(), 999999)
            self.assertEqual(mgr_reloaded.scores[0]["name"], "TST")
        finally:
            if test_file.exists():
                test_file.unlink()


class TestHeadlessGameLoop(unittest.TestCase):
    """Runs the complete PinballGame simulation for 120 frames in headless mode."""

    def test_game_execution(self):
        pygame.init()
        pygame.font.init()
        screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        game = PinballGame(screen)

        self.assertEqual(game.state, STATE_TITLE)

        # Start game
        game.start_new_game()
        self.assertEqual(game.state, STATE_LAUNCHING)

        # Pull and release plunger
        game.table.plunger.start_pull()
        for _ in range(30):
            game.update(1.0 / 60.0)

        game.table.plunger.release()
        for _ in range(60):
            game.update(1.0 / 60.0)
            game.render()

        self.assertTrue(game.table.ball.in_play or game.state == STATE_PLAYING)


if __name__ == "__main__":
    unittest.main()
