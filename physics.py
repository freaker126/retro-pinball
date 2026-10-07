"""
=============================================================================
physics.py - 2D Vector Mechanics & Collision Engine for PyPinball
=============================================================================
Educational Note:
How Video Game Physics Works:
At its core, a 2D physics engine simulates the real world through two stages:
  1. NUMERICAL INTEGRATION: Updating positions based on velocity and forces
     like gravity using Euler's Method:
         velocity = velocity + acceleration * dt
         position = position + velocity * dt
  2. COLLISION DETECTION & RESOLUTION:
     - Detection: Did the ball intersect another object?
     - Resolution: Separate overlapping shapes (positional correction) and
       compute new velocities (momentum & energy conservation via impulse).

To prevent high-speed balls from passing straight through thin walls or flippers
(a common bug known as "tunneling"), we employ Sub-Stepping: we divide each
animation frame's delta time (dt) into multiple sub-steps (e.g. 8 substeps).
=============================================================================
"""

import math
import pygame
from pygame.math import Vector2


# -----------------------------------------------------------------------------
# Vector Math Helper Functions
# -----------------------------------------------------------------------------

def clamp(value: float, min_val: float, max_val: float) -> float:
    """
    Restricts a numerical value within a defined [min_val, max_val] range.
    Educational Note:
    Clamping is used everywhere in games: limiting player speeds, clamping
    animation angles, and bounding projection parameters onto line segments.
    """
    return max(min_val, min(max_val, value))


def closest_point_on_segment(point: Vector2, seg_start: Vector2, seg_end: Vector2) -> tuple[Vector2, float]:
    """
    Finds the closest point on a finite line segment (seg_start -> seg_end) to a given point.
    
    Educational Note - The Dot Product Projection:
    Consider a vector from seg_start to the target point: V = point - seg_start.
    Consider the segment direction vector: S = seg_end - seg_start.
    
    The scalar projection of V onto S is given by:
        t = (V • S) / |S|^2
        
    If t <= 0: The closest point is seg_start.
    If t >= 1: The closest point is seg_end.
    If 0 < t < 1: The closest point lies strictly on the segment at seg_start + t * S.
    
    Returns:
        (closest_point, t) where t is the normalized parameter between 0.0 and 1.0.
    """
    segment = seg_end - seg_start
    seg_length_sq = segment.length_squared()
    
    # Degenerate segment check (start and end points coincide)
    if seg_length_sq < 0.00001:
        return Vector2(seg_start), 0.0
        
    # Vector from segment start to the external point
    to_point = point - seg_start
    
    # Calculate scalar projection parameter t
    t = to_point.dot(segment) / seg_length_sq
    t_clamped = clamp(t, 0.0, 1.0)
    
    closest = seg_start + segment * t_clamped
    return closest, t_clamped


# -----------------------------------------------------------------------------
# Collision Detection & Response Classes
# -----------------------------------------------------------------------------

class CollisionResult:
    """
    Encapsulates detailed information regarding a physical collision event.
    Passing a structured object rather than raw tuples makes code self-documenting.
    """
    __slots__ = ("occurred", "normal", "depth", "contact_point")

    def __init__(self, occurred: bool = False, normal: Vector2 = None, depth: float = 0.0, contact_point: Vector2 = None):
        self.occurred = occurred
        self.normal = normal if normal is not None else Vector2(0, 0)
        self.depth = depth
        self.contact_point = contact_point if contact_point is not None else Vector2(0, 0)


def check_circle_segment_collision(
    circle_pos: Vector2,
    radius: float,
    seg_start: Vector2,
    seg_end: Vector2
) -> CollisionResult:
    """
    Detects collision between a circular ball and a static line segment.
    
    Educational Note:
    To detect if a circle collides with a line segment, we:
      1. Find the point Q on the segment that is closest to circle center C.
      2. Measure the distance d = |C - Q|.
      3. If d < radius, the circle penetrates the segment by (radius - d)!
      4. The collision normal points from the segment toward the circle center:
         Normal = (C - Q) / d
    """
    closest, _ = closest_point_on_segment(circle_pos, seg_start, seg_end)
    diff = circle_pos - closest
    dist_sq = diff.length_squared()
    
    if dist_sq < (radius * radius):
        dist = math.sqrt(dist_sq)
        if dist > 0.0001:
            normal = diff / dist
            depth = radius - dist
        else:
            # Ball center sits exactly on the line segment; generate an arbitrary normal
            seg_dir = seg_end - seg_start
            if seg_dir.length_squared() > 0.0001:
                normal = Vector2(-seg_dir.y, seg_dir.x).normalize()
            else:
                normal = Vector2(0, -1)
            depth = radius
            
        return CollisionResult(
            occurred=True,
            normal=normal,
            depth=depth,
            contact_point=closest
        )
        
    return CollisionResult(occurred=False)


def check_circle_circle_collision(
    pos1: Vector2, radius1: float,
    pos2: Vector2, radius2: float
) -> CollisionResult:
    """
    Detects collision between two circles (e.g. Ball hitting a circular Pop Bumper).
    
    Educational Note:
    Two circles touch when the distance between their centers is less than the
    sum of their radii: |pos1 - pos2| < (radius1 + radius2).
    """
    diff = pos1 - pos2
    dist_sq = diff.length_squared()
    min_dist = radius1 + radius2
    
    if dist_sq < (min_dist * min_dist):
        dist = math.sqrt(dist_sq)
        if dist > 0.0001:
            normal = diff / dist
            depth = min_dist - dist
        else:
            normal = Vector2(0, -1)
            depth = min_dist
            
        contact_point = pos2 + normal * radius2
        return CollisionResult(
            occurred=True,
            normal=normal,
            depth=depth,
            contact_point=contact_point
        )
        
    return CollisionResult(occurred=False)


def resolve_elastic_reflection(
    velocity: Vector2,
    normal: Vector2,
    restitution: float = 0.7,
    friction: float = 0.98
) -> Vector2:
    """
    Calculates the resulting velocity vector when a ball reflects off a surface.
    
    Educational Note - The Physics of Bouncing:
    Any velocity vector V can be split into two perpendicular components:
      1. Normal component (perpendicular to surface):
         V_normal = (V • N) * N
      2. Tangential component (parallel to surface):
         V_tangent = V - V_normal
         
    When bouncing:
      - The normal component reverses and scales by the coefficient of
        restitution (e): V_normal' = -e * V_normal.
      - The tangential component is slightly reduced by friction:
        V_tangent' = friction * V_tangent.
      - Combining both yields the reflected velocity vector:
        V' = V_tangent' + V_normal'
    """
    v_dot_n = velocity.dot(normal)
    
    # Only bounce if the ball is moving toward the surface (not away from it)
    if v_dot_n < 0:
        v_normal = normal * v_dot_n
        v_tangent = velocity - v_normal
        return (v_tangent * friction) - (v_normal * restitution)
        
    return Vector2(velocity)
