"""
=============================================================================
table.py - Pinball Playfield Geometry, Walls, and Level Layout
=============================================================================
Educational Note:
Representing 2D Game Worlds via Line Segments:
A 2D pinball table consists of fixed boundaries (metal rails, wooden walls,
plastic guides) and interactive mechanisms (bumpers, flippers, targets).

Instead of treating the world as a rigid grid or pixel mask, we model all
static boundaries as a collection of 2D LINE SEGMENTS:
    LineSegment(p1: Vector2, p2: Vector2, restitution: float)

Advantages of Segment-Based Geometry:
  1. Smooth Curved Surfaces: Arches and bends are represented as chains of
     connected segments (polylines).
  2. Exact Mathematical Collisions: Using vector dot products, collisions
     are calculated with sub-pixel precision.
  3. No Flat Shelves: All curves and deflectors are angled so gravity rolls
     the ball naturally into the playfield, preventing ball jams.
=============================================================================
"""

import math
import pygame
from pygame.math import Vector2

from constants import (
    COLOR_BLACK, COLOR_WHITE, COLOR_LIGHT_GRAY, COLOR_MID_GRAY, COLOR_DARK_GRAY,
    COLOR_PHOSPHOR_DIM, PLAYFIELD_LEFT, PLAYFIELD_RIGHT, PLAYFIELD_TOP,
    PLAYFIELD_BOTTOM, PLUNGER_LANE_X, SCORE_OUTLANE, SCORE_INLANE
)
from physics import (
    check_circle_segment_collision, resolve_elastic_reflection
)
from entities import (
    Ball, Flipper, Bumper, Slingshot, StandupTarget, TargetBank,
    RolloverLane, SpinnerGate, Plunger
)


class WallSegment:
    """A static physical barrier with defined elasticity."""
    def __init__(self, p1: tuple[float, float] | Vector2, p2: tuple[float, float] | Vector2, restitution: float = 0.68):
        self.p1 = Vector2(p1)
        self.p2 = Vector2(p2)
        self.restitution = restitution


class OneWayGate:
    """
    Directional wire gate at the exit of the shooter lane arch.
    Allows launched balls to enter the table freely, but blocks balls on the
    playfield from bouncing back into the shooter lane.
    """
    def __init__(self, p1: Vector2, p2: Vector2):
        self.p1 = Vector2(p1)
        self.p2 = Vector2(p2)

    def check_ball(self, ball: Ball) -> bool:
        # If ball is traveling out of the shooter lane (moving leftward into table),
        # the wire flap swings open freely without resistance!
        if ball.vel.x < 0.0 or ball.vel.y < -40.0:
            return False

        # If a ball on the playfield tries to bounce rightward back into shooter lane (vel.x > 0):
        col = check_circle_segment_collision(ball.pos, ball.radius, self.p1, self.p2)
        if col.occurred and col.normal.x < 0:
            ball.pos += col.normal * col.depth
            ball.vel = resolve_elastic_reflection(ball.vel, col.normal, restitution=0.5)
            return True
        return False


class Table:
    """
    Contains all physical elements, layout geometry, and entities for the
    classic retro single-level pinball table in 500x800 virtual coordinates.
    """
    def __init__(self):
        # 1. Instantiate Interactive Entities
        self.plunger = Plunger(x=PLUNGER_LANE_X + 17, rest_y=PLAYFIELD_BOTTOM - 25)
        # Ball rests directly against plunger head in the shooter lane
        self.ball = Ball(x=PLUNGER_LANE_X + 17, y=self.plunger.rest_y - 12.0)

        # Flippers (Left and Right)
        # Left pivot at (155, 680), Right pivot at (305, 680)
        self.left_flipper = Flipper(pivot=Vector2(155, 680), is_left=True)
        self.right_flipper = Flipper(pivot=Vector2(305, 680), is_left=False)

        # Trio of Pop Bumpers arranged in an arcade triangle
        self.bumpers = [
            Bumper(x=185, y=250, radius=22.0),
            Bumper(x=275, y=250, radius=22.0),
            Bumper(x=230, y=320, radius=22.0),
        ]

        # Slingshots (Triangular kickers above flippers)
        self.left_slingshot = Slingshot(
            p0=Vector2(105, 570),
            p1=Vector2(138, 650),
            p2=Vector2(105, 650),
            kick_normal=Vector2(0.85, -0.52)
        )
        self.right_slingshot = Slingshot(
            p0=Vector2(355, 570),
            p1=Vector2(322, 650),
            p2=Vector2(355, 650),
            kick_normal=Vector2(-0.85, -0.52)
        )

        # Drop Target Bank: 4 stand-up targets on upper-left wall
        targets = [
            StandupTarget(Vector2(58, 210), Vector2(58, 240)),
            StandupTarget(Vector2(58, 250), Vector2(58, 280)),
            StandupTarget(Vector2(58, 290), Vector2(58, 320)),
            StandupTarget(Vector2(58, 330), Vector2(58, 360)),
        ]
        self.target_bank = TargetBank(targets)

        # Top Rollover Lanes: [ 1 ] [ 2 ] [ 3 ]
        self.rollovers = [
            RolloverLane("1", center=Vector2(175, 135), width=38, height=34),
            RolloverLane("2", center=Vector2(225, 135), width=38, height=34),
            RolloverLane("3", center=Vector2(275, 135), width=38, height=34),
        ]

        # Spinner Gate on upper orbit entry
        self.spinner = SpinnerGate(center=Vector2(95, 170), width=28.0)

        # One-Way Wire Gate at exit of shooter lane curve
        self.shooter_gate = OneWayGate(Vector2(330, 65), Vector2(330, 108))

        # Static Wall Geometry
        self.walls: list[WallSegment] = []
        self._build_table_geometry()

        # Drain sensor threshold Y coordinate
        self.drain_y = PLAYFIELD_BOTTOM - 5

    def _build_table_geometry(self):
        """Constructs all static walls, curves, lanes, and guides."""
        w = self.walls

        # ---------------------------------------------------------------------
        # 1. Outer Perimeter & Upper Smooth Arch
        # ---------------------------------------------------------------------
        # Left wall
        w.append(WallSegment((PLAYFIELD_LEFT, 190), (PLAYFIELD_LEFT, 560)))

        # Top-Left Curved Arch
        arch_left = [
            (PLAYFIELD_LEFT, 190),
            (30, 150),
            (45, 115),
            (75, 88),
            (120, 68),
            (200, PLAYFIELD_TOP)
        ]
        for i in range(len(arch_left) - 1):
            w.append(WallSegment(arch_left[i], arch_left[i+1], restitution=0.72))

        # Top Ceiling
        w.append(WallSegment((200, PLAYFIELD_TOP), (405, PLAYFIELD_TOP), restitution=0.72))

        # Top-Right Outer Arch (Shooter lane loop)
        arch_right = [
            (405, PLAYFIELD_TOP),
            (445, 80),
            (468, 105),
            (PLAYFIELD_RIGHT, 140),
            (PLAYFIELD_RIGHT, PLAYFIELD_BOTTOM)
        ]
        for i in range(len(arch_right) - 1):
            w.append(WallSegment(arch_right[i], arch_right[i+1], restitution=0.68))

        # Bottom Shooter Lane Floor
        w.append(WallSegment((PLUNGER_LANE_X, PLAYFIELD_BOTTOM), (PLAYFIELD_RIGHT, PLAYFIELD_BOTTOM)))

        # ---------------------------------------------------------------------
        # 2. Shooter Lane Inner Divider & Upper Deflector Curve
        # ---------------------------------------------------------------------
        # Straight vertical divider
        w.append(WallSegment((PLUNGER_LANE_X, PLAYFIELD_BOTTOM - 25), (PLUNGER_LANE_X, 210), restitution=0.65))

        # Curved deflector directing launched ball smoothly into table
        # Crucial: The deflector ends with a downward slope (360, 92) -> (315, 108)
        # so gravity immediately drops the ball into the playfield!
        deflector = [
            (PLUNGER_LANE_X, 210),
            (438, 170),
            (425, 135),
            (400, 106),
            (360, 92),
            (315, 108)
        ]
        for i in range(len(deflector) - 1):
            w.append(WallSegment(deflector[i], deflector[i+1], restitution=0.75))

        # ---------------------------------------------------------------------
        # 3. Top Rollover Wire Dividers with Angled Roof Caps
        # ---------------------------------------------------------------------
        # Leftmost guide
        w.append(WallSegment((150, 112), (150, 155), restitution=0.5))

        # Divider between 1 and 2 with angled anti-stuck roof cap
        w.append(WallSegment((200, 112), (200, 155), restitution=0.5))
        w.append(WallSegment((194, 118), (200, 108), restitution=0.6))
        w.append(WallSegment((200, 108), (206, 118), restitution=0.6))

        # Divider between 2 and 3 with angled anti-stuck roof cap
        w.append(WallSegment((250, 112), (250, 155), restitution=0.5))
        w.append(WallSegment((244, 118), (250, 108), restitution=0.6))
        w.append(WallSegment((250, 108), (256, 118), restitution=0.6))

        # Rightmost guide with angled cap
        w.append(WallSegment((300, 112), (300, 155), restitution=0.5))
        w.append(WallSegment((294, 118), (300, 108), restitution=0.6))
        w.append(WallSegment((300, 108), (306, 118), restitution=0.6))

        # ---------------------------------------------------------------------
        # 4. Inlane & Outlane Structures (Left & Right)
        # ---------------------------------------------------------------------
        # --- LEFT SIDE ---
        # Left Outlane outer diagonal wall leading down to drain
        w.append(WallSegment((PLAYFIELD_LEFT, 560), (45, 675), restitution=0.85))
        w.append(WallSegment((45, 675), (120, 755), restitution=0.6))

        # Left Inlane/Outlane Divider Guide
        w.append(WallSegment((75, 560), (75, 660), restitution=0.85))
        w.append(WallSegment((75, 660), (155, 685), restitution=0.85))

        # --- RIGHT SIDE ---
        # Right Outlane outer diagonal wall leading down to drain
        w.append(WallSegment((PLUNGER_LANE_X, 560), (415, 675), restitution=0.85))
        w.append(WallSegment((415, 675), (340, 755), restitution=0.6))

        # Right Inlane/Outlane Divider Guide
        w.append(WallSegment((385, 560), (385, 660), restitution=0.85))
        w.append(WallSegment((385, 660), (305, 685), restitution=0.85))

        # ---------------------------------------------------------------------
        # 5. Playfield Rebound Rubbers
        # ---------------------------------------------------------------------
        # Left upper angled rubber
        w.append(WallSegment((65, 380), (95, 435), restitution=0.9))
        w.append(WallSegment((95, 435), (65, 490), restitution=0.9))

        # Right upper angled rubber
        w.append(WallSegment((395, 380), (365, 435), restitution=0.9))
        w.append(WallSegment((365, 435), (395, 490), restitution=0.9))

        # Center top guide post
        w.append(WallSegment((223, 185), (227, 185), restitution=0.85))

    def update_physics_substep(self, dt_sub: float) -> dict:
        """
        Runs one physics sub-step: updates ball motion, resolves wall/entity collisions.
        """
        events = {
            "bumper_hit": False,
            "slingshot_hit": False,
            "target_hit": False,
            "target_bank_cleared": False,
            "rollover_hit": False,
            "rollover_all_lit": False,
            "spinner_revolutions": 0,
            "drained": False
        }

        # 1. Advance Ball Position & Gravity
        self.ball.update_physics(dt_sub, apply_gravity=self.ball.in_play)

        # 2. Check Static Wall Collisions
        for wall in self.walls:
            col = check_circle_segment_collision(self.ball.pos, self.ball.radius, wall.p1, wall.p2)
            if col.occurred:
                # Positional correction
                self.ball.pos += col.normal * col.depth
                # Elastic velocity reflection
                self.ball.vel = resolve_elastic_reflection(self.ball.vel, col.normal, restitution=wall.restitution)

        # 3. Shooter Lane One-Way Wire Gate
        self.shooter_gate.check_ball(self.ball)

        # 4. Flippers Collision & Momentum Transfer
        self.left_flipper.check_ball_collision(self.ball)
        self.right_flipper.check_ball_collision(self.ball)

        # 5. Pop Bumpers
        for bumper in self.bumpers:
            if bumper.check_ball_collision(self.ball):
                events["bumper_hit"] = True

        # 6. Slingshots
        if self.left_slingshot.check_ball_collision(self.ball) or self.right_slingshot.check_ball_collision(self.ball):
            events["slingshot_hit"] = True

        # 7. Stand-up / Drop Targets
        for target in self.target_bank.targets:
            if target.check_ball_collision(self.ball):
                events["target_hit"] = True

        # 8. Rollover Lanes
        for lane in self.rollovers:
            if lane.check_ball_trigger(self.ball):
                events["rollover_hit"] = True

        # 9. Spinner Gate
        self.spinner.check_ball_trigger(self.ball)

        # 10. Check Ball Drain
        if self.ball.pos.y > self.drain_y:
            self.ball.drained = True
            events["drained"] = True

        return events

    def update_frame(self, dt: float) -> dict:
        """Updates animations, timers, and flipper rotation for the frame."""
        self.left_flipper.update(dt)
        self.right_flipper.update(dt)

        for b in self.bumpers:
            b.update(dt)

        self.left_slingshot.update(dt)
        self.right_slingshot.update(dt)

        bank_cleared = self.target_bank.update(dt)

        for r in self.rollovers:
            r.update(dt)

        revs = self.spinner.update(dt)

        # Check if all 3 top rollovers are lit
        all_rollovers_lit = all(r.is_lit for r in self.rollovers)
        if all_rollovers_lit:
            for r in self.rollovers:
                r.is_lit = False

        if self.ball.in_play:
            self.ball.record_trail()

        return {
            "target_bank_cleared": bank_cleared,
            "rollover_all_lit": all_rollovers_lit,
            "spinner_revolutions": revs
        }

    def reset_ball_to_plunger(self):
        """Restores the ball to resting position atop the plunger."""
        self.ball.reset(x=PLUNGER_LANE_X + 17, y=self.plunger.rest_y - 12.0)

    def draw(self, surface: pygame.Surface, font: pygame.font.Font):
        """Renders the entire monochrome pinball playfield."""
        # 1. Retro vector grid
        self._draw_retro_grid(surface)

        # 2. Static Walls & Curved Rails
        for wall in self.walls:
            p1 = (int(wall.p1.x), int(wall.p1.y))
            p2 = (int(wall.p2.x), int(wall.p2.y))
            pygame.draw.line(surface, COLOR_DARK_GRAY, p1, p2, 4)
            pygame.draw.line(surface, COLOR_WHITE, p1, p2, 2)

        # 3. Shooter Lane & Plunger
        self.plunger.draw(surface)

        # 4. Target Bank & Rollovers
        self.target_bank.draw(surface)
        for r in self.rollovers:
            r.draw(surface, font)

        # 5. Spinner Gate
        self.spinner.draw(surface)

        # 6. Slingshots & Pop Bumpers
        self.left_slingshot.draw(surface)
        self.right_slingshot.draw(surface)
        for bumper in self.bumpers:
            bumper.draw(surface)

        # 7. Flippers
        self.left_flipper.draw(surface)
        self.right_flipper.draw(surface)

        # 8. Steel Ball
        self.ball.draw(surface)

        # 9. Outlane & Inlane Labels
        self._draw_lane_labels(surface, font)

    def _draw_retro_grid(self, surface: pygame.Surface):
        for y in range(PLAYFIELD_TOP + 30, PLAYFIELD_BOTTOM - 60, 42):
            for x in range(PLAYFIELD_LEFT + 25, PLUNGER_LANE_X - 15, 42):
                surface.set_at((x, y), COLOR_PHOSPHOR_DIM)

    def _draw_lane_labels(self, surface: pygame.Surface, font: pygame.font.Font):
        out_l = font.render("OUT", True, COLOR_MID_GRAY)
        surface.blit(out_l, (28, 625))
        in_l = font.render("IN", True, COLOR_MID_GRAY)
        surface.blit(in_l, (80, 625))

        in_r = font.render("IN", True, COLOR_MID_GRAY)
        surface.blit(in_r, (390, 625))
        out_r = font.render("OUT", True, COLOR_MID_GRAY)
        surface.blit(out_r, (422, 625))
