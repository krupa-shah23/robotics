#!/usr/bin/env python3

from dataclasses import dataclass
import math
import random

@dataclass
class Point2D:
    x: float
    y: float

@dataclass
class TableBounds:
    x_min: float
    x_max: float
    y_min: float
    y_max: float

def distance(a: Point2D, b: Point2D):
    return math.sqrt(
        (a.x - b.x) ** 2 +
        (a.y - b.y) ** 2
    )

def random_xy(bounds: TableBounds, rng):
    return Point2D(
        rng.uniform(bounds.x_min, bounds.x_max),
        rng.uniform(bounds.y_min, bounds.y_max)
    )

def sample_positions(
    clutter_count,
    target_position,
    bounds,
    min_distance_target,
    min_distance_cubes,
    rng,
    max_attempts=500,
):
    positions = []
    attempts = 0

    while len(positions) < clutter_count:

        attempts += 1

        if attempts > max_attempts:
            raise RuntimeError(
                f"Failed to place {clutter_count} cubes "
                f"after {max_attempts} attempts."
            )

        candidate = random_xy(bounds, rng)

        if distance(candidate, target_position) < min_distance_target:
            continue

        too_close = False

        for cube in positions:
            if distance(candidate, cube) < min_distance_cubes:
                too_close = True
                break

        if too_close:
            continue

        positions.append(candidate)

    return SceneLayout(
        positions=positions,
        attempts=attempts
    )

def sample_positions_biased(
    clutter_count,
    target_position,
    camera_xy,           # NEW: (cam_x, cam_y) projected onto table plane
    bounds,
    min_distance_target,
    min_distance_cubes,
    rng,
    sightline_bias=0.6,  # fraction of placements pulled toward the line
    sightline_width=0.15,  # how tightly clustered around the line
    max_attempts=500,
):
    # NOTE: assumes camera_xy.x ≈ target_position.x ≈ 0 (true for current grid,
    # where only camera_z varies). If camera/target x ever differ, this needs
    # to compute the actual line between them instead of hardcoding x≈0.
    # NOTE: assumes camera_xy.x ≈ target_position.x ≈ 0 (true for current grid,
    # where only camera_z varies). If camera/target x ever differ, this needs
    # to compute the actual line between them instead of hardcoding x≈0.
    
    positions = []
    attempts = 0
    while len(positions) < clutter_count:
        attempts += 1
        if attempts > max_attempts:
            raise RuntimeError(f"Failed to place {clutter_count} cubes after {max_attempts} attempts.")

        if rng.random() < sightline_bias:
            # bias x near the camera-target line (x≈0), free in y within bounds
            x = rng.gauss(0, sightline_width)
            x = max(bounds.x_min, min(bounds.x_max, x))
            y = rng.uniform(bounds.y_min, bounds.y_max)
            candidate = Point2D(x, y)
        else:
            candidate = random_xy(bounds, rng)  # existing uniform fallback

        if distance(candidate, target_position) < min_distance_target:
            continue
        if any(distance(candidate, p) < min_distance_cubes for p in positions):
            continue
        positions.append(candidate)

    return SceneLayout(positions=positions, attempts=attempts)

@dataclass
class SceneLayout:
    positions: list[Point2D]
    attempts: int