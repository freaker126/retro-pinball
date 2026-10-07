"""
=============================================================================
entities.py - Interactive Game Objects for PyPinball
=============================================================================
Educational Note:
Object-Oriented Programming (OOP) in Game Development:
Each physical element on a pinball table has unique geometry, behaviors, and
collision rules. We model each element as a distinct Python class:
  - Ball: Dynamic body updated via numerical integration
  - Flipper: Kinematic body with angular rotation and linear momentum transfer
  - Bumper: Active impulse circle that repels the ball and scores points
  - Slingshot: Triangular rubber kicker with elastic spring recoil
  - TargetBank: Set of drop targets tracking completion for massive bonuses
  - RolloverLane: Sensor trigger updating the score multiplier
  - SpinnerGate: Rotational inertia toy spinning rapidly on ball passage
  - Plunger: Spring-loaded mechanical launcher

Encapsulation & Single Responsibility:
Each entity manages its own state, timers, animations, and drawing routines.
=============================================================================
"""

import math
from collections import deque
import pygame
from pygame.math import Vector2

from constants import (
    BALL_RADIUS, BALL_RESTITUTION, BALL_MAX_SPEED, BALL_AIR_DRAG, GRAVITY,
    FLIPPER_LENGTH, FLIPPER_REST_ANGLE, FLIPPER_UP_ANGLE, FLIPPER_ANGULAR_SPEED,
    FLIPPER_WIDTH_BASE, FLIPPER_WIDTH_TIP,
    BUMPER_RADIUS, BUMPER_POP_FORCE, SLINGSHOT_FORCE,
    PLUNGER_MAX_PULL, PLUNGER_CHARGE_RATE, PLUNGER_RELEASE_SPEED,
    PLUNGER_MIN_LAUNCH_SPEED, PLUNGER_MAX_LAUNCH_SPEED,
    COLOR_BLACK, COLOR_WHITE, COLOR_LIGHT_GRAY, COLOR_MID_GRAY, COLOR_DARK_GRAY,
    SCORE_BUMPER, SCORE_SLINGSHOT, SCORE_STANDUP_TARGET, SCORE_TARGET_BANK_CLEARED,
    SCORE_ROLLOVER_LANE, SCORE_SPINNER_PER_REV
)
from physics import (
    clamp, closest_point_on_segment, check_circle_segment_collision,
    check_circle_circle_collision, resolve_elastic_reflection
)


# -----------------------------------------------------------------------------
# Ball Entity (Dynamic Rigid Body)
# -----------------------------------------------------------------------------

class Ball:
    """
    Simulates the steel pinball.
    
    Educational Note - Motion Trails:
    In early vector arcade monitors (and classic CRT oscilloscopes), bright
    phosphor elements left a fading persistence of vision on the screen.
    We mimic this retro vector look by storing a history of previous positions
    in a `deque` and drawing diminishing vector circles.
    """
    def __init__(self, x: float = 0.0, y: float = 0.0):
        self.pos = Vector2(x, y)
        self.vel = Vector2(0.0, 0.0)
        self.radius = BALL_RADIUS
        self.in_play = False
        self.drained = False
        # Store recent positions for vector phosphor trail (max 6 points)
        self.trail: deque[Vector2] = deque(maxlen=6)

    def reset(self, x: float, y: float):
        """Places the ball in the shooter lane at rest."""
        self.pos = Vector2(x, y)
        self.vel = Vector2(0.0, 0.0)
        self.in_play = False
        self.drained = False
        self.trail.clear()

    def update_physics(self, dt: float, apply_gravity: bool = True):
        """
        Advances position and velocity using numerical integration.
        Educational Note:
        Euler Integration:
          velocity = velocity + acceleration * dt
          position = position + velocity * dt
        """
        if not self.in_play:
            return

        if apply_gravity:
            # Gravity accelerates the ball downwards along the playfield
            self.vel.y += GRAVITY * dt

        # Apply slight air resistance
        self.vel *= BALL_AIR_DRAG

        # Cap maximum speed to prevent physics instability
        speed_sq = self.vel.length_squared()
        if speed_sq > (BALL_MAX_SPEED * BALL_MAX_SPEED):
            self.vel.scale_to_length(BALL_MAX_SPEED)

        # Update position
        self.pos += self.vel * dt

    def record_trail(self):
        """Appends current position to the phosphor trail buffer."""
        self.trail.append(Vector2(self.pos))

    def draw(self, surface: pygame.Surface):
        """Renders the high-contrast retro monochrome ball and vector trail."""
        # 1. Draw fading phosphor trail
        trail_len = len(self.trail)
        for i, past_pos in enumerate(self.trail):
            # Alpha/brightness fades from dimmest to brightest
            ratio = (i + 1) / (trail_len + 1)
            trail_color = (int(140 * ratio), int(140 * ratio), int(150 * ratio))
            trail_radius = max(2.0, self.radius * ratio * 0.75)
            pygame.draw.circle(surface, trail_color, (int(past_pos.x), int(past_pos.y)), int(trail_radius))

        # 2. Draw solid chrome ball with bright white specular highlight
        int_pos = (int(self.pos.x), int(self.pos.y))
        pygame.draw.circle(surface, COLOR_WHITE, int_pos, int(self.radius))
        # Inner specular reflection highlight
        highlight_pos = (int(self.pos.x - self.radius * 0.3), int(self.pos.y - self.radius * 0.3))
        pygame.draw.circle(surface, COLOR_WHITE, highlight_pos, max(1, int(self.radius * 0.4)))


# -----------------------------------------------------------------------------
# Flipper Entity (Kinematic Rotating Arm)
# -----------------------------------------------------------------------------

class Flipper:
    """
    Electromechanical flipper with true angular momentum transfer.
    
    Educational Note - Transferring Angular Momentum:
    When a flipper rotates at angular speed ω (rad/s), any point on the flipper
    at distance s from the pivot has a tangential linear velocity:
        V_flipper = ω * s * (-sin(θ), cos(θ))
    When the flipper strikes the ball, this linear velocity is imparted into the
    collision calculation! Hitting the ball with the tip (large s) while flipping
    upwards launches the ball with great speed.
    """
    def __init__(self, pivot: Vector2, is_left: bool):
        self.pivot = Vector2(pivot)
        self.is_left = is_left
        self.length = FLIPPER_LENGTH
        
        # Determine resting and maximum up angles based on left/right orientation
        if is_left:
            self.angle_rest = FLIPPER_REST_ANGLE      # ~ +28 deg (sloping down-right)
            self.angle_up = FLIPPER_UP_ANGLE          # ~ -26 deg (angled up-right)
        else:
            self.angle_rest = 180.0 - FLIPPER_REST_ANGLE   # ~ 152 deg (sloping down-left)
            self.angle_up = 180.0 - FLIPPER_UP_ANGLE       # ~ 206 deg (angled up-left)

        self.current_angle = self.angle_rest
        self.angular_velocity = 0.0  # Radians per second
        self.is_active = False

    def update(self, dt: float):
        """Rotates flipper toward target angle and tracks angular velocity."""
        target_angle = self.angle_up if self.is_active else self.angle_rest
        prev_angle = self.current_angle

        diff = target_angle - self.current_angle
        step = FLIPPER_ANGULAR_SPEED * dt

        if abs(diff) <= step:
            self.current_angle = target_angle
        else:
            self.current_angle += step if diff > 0 else -step

        # Compute instantaneous angular velocity in radians per second
        angle_delta_deg = self.current_angle - prev_angle
        self.angular_velocity = math.radians(angle_delta_deg) / max(0.0001, dt)

    def get_tip_pos(self) -> Vector2:
        """Calculates current world position of the flipper tip."""
        rad = math.radians(self.current_angle)
        return self.pivot + Vector2(math.cos(rad), math.sin(rad)) * self.length

    def check_ball_collision(self, ball: Ball) -> bool:
        """
        Tests and resolves collision between the ball and this moving flipper.
        Imparts angular flipper velocity to the ball.
        """
        tip = self.get_tip_pos()
        col = check_circle_segment_collision(ball.pos, ball.radius + 3.0, self.pivot, tip)
        
        if not col.occurred:
            return False

        # 1. Positional correction: separate ball from flipper surface
        ball.pos += col.normal * col.depth

        # 2. Determine distance along flipper arm where ball made contact
        contact_dist = (col.contact_point - self.pivot).length()
        contact_dist = clamp(contact_dist, 0.0, self.length)

        # 3. Calculate linear velocity of the flipper at that contact point
        rad = math.radians(self.current_angle)
        # Tangential direction perpendicular to flipper arm
        tangent_dir = Vector2(-math.sin(rad), math.cos(rad))
        flipper_lin_vel = tangent_dir * (self.angular_velocity * contact_dist)

        # 4. Relative velocity between ball and flipper
        v_rel = ball.vel - flipper_lin_vel
        v_dot_n = v_rel.dot(col.normal)

        # Only bounce if ball is approaching flipper surface
        if v_dot_n < 0:
            # Reflection of relative velocity
            restitution = 0.72
            friction = 0.94
            v_rel_normal = col.normal * v_dot_n
            v_rel_tangent = v_rel - v_rel_normal
            v_rel_new = (v_rel_tangent * friction) - (v_rel_normal * restitution)

            # Reconstruct absolute velocity by adding back flipper velocity
            ball.vel = flipper_lin_vel + v_rel_new
            return True

        return False

    def draw(self, surface: pygame.Surface):
        """Draws the tapered retro monochrome flipper polygon."""
        tip = self.get_tip_pos()
        rad = math.radians(self.current_angle)
        # Normal vector perpendicular to the flipper arm
        perp = Vector2(-math.sin(rad), math.cos(rad))

        # Tapered polygon vertices (wide at pivot, narrow at tip)
        r_base = FLIPPER_WIDTH_BASE * 0.5
        r_tip = FLIPPER_WIDTH_TIP * 0.5

        p1 = self.pivot + perp * r_base
        p2 = tip + perp * r_tip
        p3 = tip - perp * r_tip
        p4 = self.pivot - perp * r_base

        points = [(int(p.x), int(p.y)) for p in (p1, p2, p3, p4)]
        
        # Solid white body
        pygame.draw.polygon(surface, COLOR_WHITE, points)
        # Black outline for crisp vector separation
        pygame.draw.polygon(surface, COLOR_BLACK, points, 2)
        # Pivot hub circle
        pygame.draw.circle(surface, COLOR_BLACK, (int(self.pivot.x), int(self.pivot.y)), int(r_base * 0.8))
        pygame.draw.circle(surface, COLOR_LIGHT_GRAY, (int(self.pivot.x), int(self.pivot.y)), int(r_base * 0.4))


# -----------------------------------------------------------------------------
# Pop Bumper Entity (Active Repulsion Coil)
# -----------------------------------------------------------------------------

class Bumper:
    """
    Circular electro-mechanical pop bumper.
    Pops the ball away forcefully when struck, flashes, and awards points.
    """
    def __init__(self, x: float, y: float, radius: float = BUMPER_RADIUS):
        self.pos = Vector2(x, y)
        self.radius = radius
        self.flash_timer = 0.0
        self.shockwave_radius = 0.0
        self.score_value = SCORE_BUMPER

    def update(self, dt: float):
        """Updates hit flash animation and expanding shockwave ring."""
        if self.flash_timer > 0.0:
            self.flash_timer = max(0.0, self.flash_timer - dt)
            self.shockwave_radius += 120.0 * dt

    def check_ball_collision(self, ball: Ball) -> bool:
        """Tests collision with ball. If hit, repels ball with active impulse."""
        col = check_circle_circle_collision(ball.pos, ball.radius, self.pos, self.radius)
        if not col.occurred:
            return False

        # Positional correction: move ball outside bumper perimeter
        ball.pos += col.normal * col.depth

        # Active pop: project ball outward along collision normal
        # We blend the reflected velocity with a strong outward kick
        reflected = resolve_elastic_reflection(ball.vel, col.normal, restitution=0.85)
        kick_velocity = col.normal * BUMPER_POP_FORCE
        ball.vel = reflected + kick_velocity

        # Trigger visual feedback
        self.flash_timer = 0.18
        self.shockwave_radius = self.radius
        return True

    def draw(self, surface: pygame.Surface):
        """Renders vector concentric rings with flash effect when hit."""
        center = (int(self.pos.x), int(self.pos.y))
        
        # Outer ring
        outer_color = COLOR_WHITE if self.flash_timer > 0.0 else COLOR_LIGHT_GRAY
        pygame.draw.circle(surface, outer_color, center, int(self.radius), 2)

        # Inner ring & core
        inner_radius = int(self.radius * 0.6)
        fill_color = COLOR_WHITE if self.flash_timer > 0.0 else COLOR_BLACK
        pygame.draw.circle(surface, fill_color, center, inner_radius)
        pygame.draw.circle(surface, COLOR_LIGHT_GRAY, center, inner_radius, 2)

        # Center indicator dot
        dot_color = COLOR_BLACK if self.flash_timer > 0.0 else COLOR_WHITE
        pygame.draw.circle(surface, dot_color, center, 4)

        # Expanding vector shockwave ring
        if self.flash_timer > 0.0:
            ring_r = int(self.shockwave_radius)
            if ring_r < self.radius * 2.2:
                pygame.draw.circle(surface, COLOR_WHITE, center, ring_r, 1)


# -----------------------------------------------------------------------------
# Slingshot Entity (Triangular Rubber Kicker)
# -----------------------------------------------------------------------------

class Slingshot:
    """
    Triangular rubber bumper located above each flipper.
    When the ball strikes the front rubber face, an internal solenoid kicks
    the ball diagonally across the table.
    """
    def __init__(self, p0: Vector2, p1: Vector2, p2: Vector2, kick_normal: Vector2):
        self.p0 = Vector2(p0)  # Top point
        self.p1 = Vector2(p1)  # Bottom point
        self.p2 = Vector2(p2)  # Outer corner
        self.kick_normal = Vector2(kick_normal).normalize()
        self.flash_timer = 0.0
        self.score_value = SCORE_SLINGSHOT

    def update(self, dt: float):
        if self.flash_timer > 0.0:
            self.flash_timer = max(0.0, self.flash_timer - dt)

    def check_ball_collision(self, ball: Ball) -> bool:
        """Tests collision with the active front rubber face (p0 -> p1)."""
        col = check_circle_segment_collision(ball.pos, ball.radius, self.p0, self.p1)
        if not col.occurred:
            return False

        # Position correction
        ball.pos += col.normal * col.depth

        # Apply active kick in the designated outward direction
        reflected = resolve_elastic_reflection(ball.vel, col.normal, restitution=0.8)
        ball.vel = reflected + self.kick_normal * SLINGSHOT_FORCE

        self.flash_timer = 0.15
        return True

    def draw(self, surface: pygame.Surface):
        """Renders the triangular vector slingshot."""
        points = [
            (int(self.p0.x), int(self.p0.y)),
            (int(self.p1.x), int(self.p1.y)),
            (int(self.p2.x), int(self.p2.y)),
        ]
        color = COLOR_WHITE if self.flash_timer > 0.0 else COLOR_LIGHT_GRAY
        # Fill triangle
        pygame.draw.polygon(surface, COLOR_DARK_GRAY, points)
        pygame.draw.polygon(surface, color, points, 2)
        # Draw posts at triangle corners
        for pt in points:
            pygame.draw.circle(surface, COLOR_WHITE, pt, 4)


# -----------------------------------------------------------------------------
# Stand-up / Drop Target & Bank
# -----------------------------------------------------------------------------

class StandupTarget:
    """An individual target that registers hits."""
    def __init__(self, p1: Vector2, p2: Vector2):
        self.p1 = Vector2(p1)
        self.p2 = Vector2(p2)
        self.is_hit = False
        self.flash_timer = 0.0

    def check_ball_collision(self, ball: Ball) -> bool:
        if self.is_hit:
            return False

        col = check_circle_segment_collision(ball.pos, ball.radius, self.p1, self.p2)
        if not col.occurred:
            return False

        # Bounce ball off target
        ball.pos += col.normal * col.depth
        ball.vel = resolve_elastic_reflection(ball.vel, col.normal, restitution=0.75)

        self.is_hit = True
        self.flash_timer = 0.25
        return True


class TargetBank:
    """
    A sequence of targets (e.g. 4 targets on the upper-left wall).
    Clearing all targets awards a massive bonus and resets the bank!
    """
    def __init__(self, targets: list[StandupTarget]):
        self.targets = targets
        self.reset_timer = 0.0

    def update(self, dt: float) -> bool:
        """
        Updates targets. Returns True if bank just completed a reset.
        """
        all_hit = all(t.is_hit for t in self.targets)
        for t in self.targets:
            if t.flash_timer > 0.0:
                t.flash_timer = max(0.0, t.flash_timer - dt)

        if all_hit:
            if self.reset_timer == 0.0:
                self.reset_timer = 1.0  # Pause for 1 second before pop-up reset
            else:
                self.reset_timer = max(0.0, self.reset_timer - dt)
                if self.reset_timer == 0.0:
                    for t in self.targets:
                        t.is_hit = False
                    return True
        return False

    def draw(self, surface: pygame.Surface):
        """Draws target bank with active indicators."""
        for t in self.targets:
            color = COLOR_DARK_GRAY if t.is_hit else COLOR_WHITE
            if t.flash_timer > 0.0:
                color = COLOR_WHITE
            p1 = (int(t.p1.x), int(t.p1.y))
            p2 = (int(t.p2.x), int(t.p2.y))
            # Draw thick target line
            pygame.draw.line(surface, color, p1, p2, 4)


# -----------------------------------------------------------------------------
# Rollover Lane Entity (Sensor Trigger)
# -----------------------------------------------------------------------------

class RolloverLane:
    """
    Sensor lane at top of table (e.g. 1 - 2 - 3).
    Rolling over lights the lane indicator.
    """
    def __init__(self, name: str, center: Vector2, width: float, height: float):
        self.name = name
        self.center = Vector2(center)
        self.rect = pygame.Rect(
            int(self.center.x - width / 2),
            int(self.center.y - height / 2),
            int(width),
            int(height)
        )
        self.is_lit = False
        self.cooldown = 0.0

    def update(self, dt: float):
        if self.cooldown > 0.0:
            self.cooldown = max(0.0, self.cooldown - dt)

    def check_ball_trigger(self, ball: Ball) -> bool:
        """Checks if ball passes over the lane trigger."""
        if self.cooldown > 0.0:
            return False

        if self.rect.collidepoint(ball.pos.x, ball.pos.y):
            self.cooldown = 0.6  # Prevent double trigger
            was_lit = self.is_lit
            self.is_lit = True
            return not was_lit  # True if newly activated
        return False

    def draw(self, surface: pygame.Surface, font: pygame.font.Font):
        """Draws the lane symbol (e.g. '1', '2', '3') lit or unlit."""
        color = COLOR_WHITE if self.is_lit else COLOR_MID_GRAY
        # Center circle indicator
        center = (int(self.center.x), int(self.center.y))
        pygame.draw.circle(surface, COLOR_DARK_GRAY, center, 14)
        if self.is_lit:
            pygame.draw.circle(surface, COLOR_WHITE, center, 14, 2)
            pygame.draw.circle(surface, COLOR_WHITE, center, 8)
        else:
            pygame.draw.circle(surface, COLOR_MID_GRAY, center, 14, 1)

        # Draw number text
        txt_surf = font.render(self.name, True, COLOR_BLACK if (self.is_lit and True) else color)
        rect = txt_surf.get_rect(center=center)
        surface.blit(txt_surf, rect)


# -----------------------------------------------------------------------------
# Spinner Gate Entity (Rotational Inertia)
# -----------------------------------------------------------------------------

class SpinnerGate:
    """
    Spinning gate on the upper orbit loop.
    Imparts spinning angular speed when the ball rushes through.
    """
    def __init__(self, center: Vector2, width: float = 30.0):
        self.center = Vector2(center)
        self.width = width
        self.angle = 0.0            # Rotation angle in degrees
        self.spin_speed = 0.0       # Deg / sec
        self.cooldown = 0.0

    def update(self, dt: float) -> int:
        """
        Advances spinner rotation. Returns number of full rotations completed this frame.
        """
        revolutions = 0
        if self.spin_speed > 0.0:
            prev_angle = self.angle
            self.angle += self.spin_speed * dt
            # Count 360-degree rotations
            if int(self.angle / 360.0) > int(prev_angle / 360.0):
                revolutions = int(self.angle / 360.0) - int(prev_angle / 360.0)

            # Apply friction to slow spinner down
            self.spin_speed = max(0.0, self.spin_speed - 1200.0 * dt)
            if self.spin_speed == 0.0:
                self.angle = 0.0

        if self.cooldown > 0.0:
            self.cooldown = max(0.0, self.cooldown - dt)

        return revolutions

    def check_ball_trigger(self, ball: Ball) -> bool:
        """Triggers spin when ball zooms through spinner position."""
        if self.cooldown > 0.0:
            return False

        dist = (ball.pos - self.center).length()
        if dist < (self.width * 0.6):
            # Impart spin proportional to ball speed
            ball_speed = ball.vel.length()
            self.spin_speed = max(1800.0, ball_speed * 4.0)
            self.cooldown = 0.3
            return True
        return False

    def draw(self, surface: pygame.Surface):
        """Renders 3D perspective illusion of the spinning blade."""
        # Scale vertical height based on cosine of angle to simulate 3D rotation
        rad = math.radians(self.angle)
        scale_y = math.cos(rad)
        h = max(2, int(abs(scale_y) * 14))

        x = int(self.center.x - self.width / 2)
        y = int(self.center.y - h / 2)
        rect = pygame.Rect(x, y, int(self.width), h)

        pygame.draw.rect(surface, COLOR_WHITE, rect)
        pygame.draw.rect(surface, COLOR_BLACK, rect, 1)


# -----------------------------------------------------------------------------
# Plunger Entity (Spring-Loaded Ball Launcher)
# -----------------------------------------------------------------------------

class Plunger:
    """
    Spring-loaded plunger at bottom right.
    Holding the launch key pulls the spring backward. Releasing fires the spring,
    striking the ball and launching it up the shooter lane into the top arch.
    """
    def __init__(self, x: float, rest_y: float):
        self.x = x
        self.rest_y = rest_y
        self.pull_amount = 0.0
        self.is_pulling = False
        self.is_releasing = False

    def update(self, dt: float, ball: Ball) -> bool:
        """
        Updates plunger position and strikes ball if released.
        Returns True when spring snaps and fires ball.
        """
        fired = False
        if self.is_pulling:
            # Charge spring compression
            self.pull_amount = min(PLUNGER_MAX_PULL, self.pull_amount + PLUNGER_CHARGE_RATE * dt)
            # The ball rests directly on the plunger head while being drawn back
            if not ball.in_play and abs(ball.pos.x - self.x) < 18.0:
                ball.pos.y = self.rest_y + self.pull_amount - ball.radius - 2.0
                ball.vel = Vector2(0.0, 0.0)
        elif self.is_releasing:
            prev_pull = self.pull_amount
            snap_step = PLUNGER_RELEASE_SPEED * dt
            self.pull_amount = max(0.0, self.pull_amount - snap_step)
            current_tip_y = self.rest_y + self.pull_amount

            # Check if plunger tip strikes the ball
            if not ball.in_play and abs(ball.pos.x - self.x) < 18.0:
                if current_tip_y <= (ball.pos.y + ball.radius + 4.0):
                    # Launch ball with powerful impulse that easily sweeps through the top arch
                    launch_ratio = max(0.40, prev_pull / PLUNGER_MAX_PULL)
                    launch_speed = PLUNGER_MIN_LAUNCH_SPEED + launch_ratio * (PLUNGER_MAX_LAUNCH_SPEED - PLUNGER_MIN_LAUNCH_SPEED)
                    # Slight inward (-X) velocity bias helps ball hug curve smoothly
                    ball.vel = Vector2(-22.0, -launch_speed)
                    ball.in_play = True
                    fired = True
                    self.pull_amount = 0.0
                    self.is_releasing = False

            if self.pull_amount <= 0.0:
                self.pull_amount = 0.0
                self.is_releasing = False

        return fired

    def start_pull(self):
        """Called when player holds the launch key."""
        self.is_pulling = True
        self.is_releasing = False

    def release(self):
        """Called when player lets go of the launch key."""
        if self.is_pulling:
            self.is_pulling = False
            self.is_releasing = True

    def draw(self, surface: pygame.Surface):
        """Draws the spring coils and plunger rod."""
        plunger_tip_y = int(self.rest_y + self.pull_amount)
        rod_bottom_y = int(self.rest_y + PLUNGER_MAX_PULL + 30)

        # 1. Plunger tip head (solid block)
        tip_rect = pygame.Rect(int(self.x - 12), plunger_tip_y - 8, 24, 8)
        pygame.draw.rect(surface, COLOR_WHITE, tip_rect)

        # 2. Draw zig-zag spring coils
        coils = 8
        spring_length = rod_bottom_y - plunger_tip_y
        step_y = spring_length / coils
        points = []
        for i in range(coils + 1):
            py = plunger_tip_y + i * step_y
            px = self.x + (-8 if i % 2 == 0 else 8)
            points.append((int(px), int(py)))

        if len(points) >= 2:
            pygame.draw.lines(surface, COLOR_LIGHT_GRAY, False, points, 2)

        # 3. Plunger handle rod
        pygame.draw.line(surface, COLOR_DARK_GRAY, (int(self.x), plunger_tip_y), (int(self.x), rod_bottom_y), 4)


# -----------------------------------------------------------------------------
# Vector Sparks / Visual Effects
# -----------------------------------------------------------------------------

class VectorSpark:
    """Brief vector particle emitted on bumper hits and target strikes."""
    def __init__(self, pos: Vector2, vel: Vector2, lifespan: float = 0.25):
        self.pos = Vector2(pos)
        self.vel = Vector2(vel)
        self.lifespan = lifespan
        self.age = 0.0

    def update(self, dt: float) -> bool:
        self.pos += self.vel * dt
        self.age += dt
        return self.age < self.lifespan

    def draw(self, surface: pygame.Surface):
        ratio = max(0.0, 1.0 - (self.age / self.lifespan))
        brightness = int(255 * ratio)
        color = (brightness, brightness, brightness)
        # Draw small crosshair / dot
        p = (int(self.pos.x), int(self.pos.y))
        pygame.draw.circle(surface, color, p, 1)
