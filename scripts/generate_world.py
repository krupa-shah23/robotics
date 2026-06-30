#!/usr/bin/env python3
import argparse
import json
import os
import random

from world_editor import WorldEditor
from scene_generator import (
    Point2D,
    TableBounds,
    sample_positions,
    sample_positions_biased,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--x", type=float, default=0.0)
    parser.add_argument("--y", type=float, default=-1.2)
    parser.add_argument("--z", type=float, default=1.0)
    parser.add_argument("--roll", type=float, default=0.0)
    parser.add_argument("--pitch", type=float, default=0.3)
    parser.add_argument("--yaw", type=float, default=1.5708)
    parser.add_argument("--clutter", type=int, default=4)
    parser.add_argument(
        "--bias_sightline",
        action="store_true",
        help="Bias clutter placement toward the camera-target sightline."
    )
    parser.add_argument("--light", type=float, default=0.8)
    parser.add_argument("--occlusion_target", type=float, default=0.0)
    parser.add_argument("--in_file", default=os.path.expanduser("~/robotics/worlds/manipulation_world.sdf"))
    parser.add_argument("--out", default=os.path.expanduser("~/robotics/worlds/generated_world.sdf"))
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducible scene generation")
    parser.add_argument("--metadata_file", default=os.path.expanduser("~/robotics/worlds/trial_metadata.json"))
    args = parser.parse_args()

    editor = WorldEditor(args.in_file)

    editor.set_pose(
        "camera_model",
        args.x,
        args.y,
        args.z,
        args.roll,
        args.pitch,
        args.yaw
    )

    editor.set_light(
        "sun",
        args.light
    )

    rng = random.Random(args.seed)

    bounds = TableBounds(
        x_min=-0.45,
        x_max=0.45,
        y_min=-0.30,
        y_max=0.30,
    )

    camera_xy = Point2D(args.x, args.y)

    target = Point2D(0.0, 0.0)

    if args.bias_sightline:
        scene = sample_positions_biased(
            clutter_count=args.clutter,
            target_position=target,
            camera_xy=camera_xy,
            bounds=bounds,
            min_distance_target=0.15,
            min_distance_cubes=0.15,
            rng=rng,
        )
    else:
        scene = sample_positions(
            clutter_count=args.clutter,
            target_position=target,
            bounds=bounds,
            min_distance_target=0.15,
            min_distance_cubes=0.15,
            rng=rng,
        )

    for i, position in enumerate(scene.positions):

        editor.set_pose(
            f"distractor_cube_{i+1}",
            position.x,
            position.y,
            0.55,
            0.0,
            0.0,
            0.0,
        )
    
    print(f"Placement attempts: {scene.attempts}")
    print(f"Random seed: {args.seed}")

    for i in range(args.clutter, 4):

        editor.hide_model(
            f"distractor_cube_{i+1}"
            )

    editor.save(args.out)

    camera_pose = editor.get_pose("camera_model")

    pose_record = {

        "camera_pose": {
            "x": camera_pose.x,
            "y": camera_pose.y,
            "z": camera_pose.z,
            "roll": camera_pose.roll,
            "pitch": camera_pose.pitch,
            "yaw": camera_pose.yaw,
        },

        "seed": args.seed,

        "clutter_count": args.clutter,

        "clutter_positions": [
            {
                "x": p.x,
                "y": p.y
            }

            for p in scene.positions
        ],

        "sampling_mode": (
                "biased"
                if args.bias_sightline
                else "uniform"
        ),

        "placement_attempts": scene.attempts,

        "light_level": args.light,

        "requested_occlusion": args.occlusion_target,

        "measured_occlusion": None,

        "world_file": args.out,
    }   

    with open(args.metadata_file, "w") as f:
        json.dump(pose_record, f, indent=2)

    print(f"[generate_world] Camera pose: {camera_pose}")
    print(f"[generate_world] Wrote world to {args.out}")
    print(f"[generate_world] Wrote metadata to {args.metadata_file}")


if __name__ == "__main__":
    main()
