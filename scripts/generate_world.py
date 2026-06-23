#!/usr/bin/env python3
import argparse
import re

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--x", type=float, default=0.0)
    parser.add_argument("--y", type=float, default=-1.2)
    parser.add_argument("--z", type=float, default=1.0)
    parser.add_argument("--roll", type=float, default=0.0)
    parser.add_argument("--pitch", type=float, default=0.3)
    parser.add_argument("--yaw", type=float, default=1.5708)
    parser.add_argument("--in_file", default="manipulation_world.sdf")
    parser.add_argument("--out", default="manipulation_world.sdf")
    args = parser.parse_args()

    new_pose = f"{args.x} {args.y} {args.z} {args.roll} {args.pitch} {args.yaw}"

    with open(args.in_file, "r") as f:
        content = f.read()

    pattern = re.compile(r'(<model name="camera_model">\s*<pose>)([^<]+)(</pose>)')
    if not pattern.search(content):
        raise RuntimeError("Could not find camera_model pose tag.")

    new_content = pattern.sub(lambda m: f"{m.group(1)}{new_pose}{m.group(3)}", content)

    with open(args.out, "w") as f:
        f.write(new_content)

    print(f"Wrote camera pose '{new_pose}' to {args.out}")

if __name__ == "__main__":
    main()
