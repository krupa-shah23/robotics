#!/usr/bin/env python3
import argparse
import json
import re
import os


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--x", type=float, default=0.0)
    parser.add_argument("--y", type=float, default=-1.2)
    parser.add_argument("--z", type=float, default=1.0)
    parser.add_argument("--roll", type=float, default=0.0)
    parser.add_argument("--pitch", type=float, default=0.3)
    parser.add_argument("--yaw", type=float, default=1.5708)
    parser.add_argument("--in_file", default=os.path.expanduser("~/robotics/worlds/manipulation_world.sdf"))
    parser.add_argument("--out", default=os.path.expanduser("~/robotics/worlds/manipulation_world.sdf"))
    parser.add_argument("--pose_sidecar", default=os.path.expanduser("~/robotics/worlds/current_camera_pose.json"))
    args = parser.parse_args()

    new_pose = f"{args.x} {args.y} {args.z} {args.roll} {args.pitch} {args.yaw}"

    with open(args.in_file, "r") as f:
        content = f.read()

    pattern = re.compile(r'(<model name="camera_model">\s*<pose>)([^<]+)(</pose>)')
    if not pattern.search(content):
        raise RuntimeError("Could not find camera_model pose tag in SDF.")

    new_content = pattern.sub(lambda m: f"{m.group(1)}{new_pose}{m.group(3)}", content)

    with open(args.out, "w") as f:
        f.write(new_content)

    pose_record = {
        "x": args.x, "y": args.y, "z": args.z,
        "roll": args.roll, "pitch": args.pitch, "yaw": args.yaw,
        "world_file": args.out,
    }
    with open(args.pose_sidecar, "w") as f:
        json.dump(pose_record, f, indent=2)

    print(f"[generate_world] Wrote pose '{new_pose}' to {args.out}")
    print(f"[generate_world] Wrote sidecar to {args.pose_sidecar}")


if __name__ == "__main__":
    main()
