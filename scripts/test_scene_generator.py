import random

from scene_generator import (
    Point2D,
    TableBounds,
    distance,
    random_xy,
)

from scene_generator import (
    Point2D,
    TableBounds,
    distance,
    random_xy,
    sample_positions,
)

rng = random.Random(42)

bounds = TableBounds(
    x_min=-0.45,
    x_max=0.45,
    y_min=-0.30,
    y_max=0.30,
)

a = Point2D(0, 0)
b = Point2D(3, 4)

print("Distance =", distance(a, b))
print()

for i in range(5):
    p = random_xy(bounds, rng)
    print(p)

print("\nSampled positions:\n")

scene = sample_positions(
    clutter_count=4,
    target_position=Point2D(0.0, 0.0),
    bounds=bounds,
    min_distance_target=0.15,
    min_distance_cubes=0.15,
    rng=rng,
)

for p in scene.positions:
    print(p)

print(scene.attempts)