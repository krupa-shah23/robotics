#!/usr/bin/env python3
"""
mock_perception.py — simulates a noisy perception module's occlusion estimate.
Reads a trial's metadata (which already has measured_occlusion = ground truth),
injects controlled noise to produce a "perceived" value, and computes the gap.
"""
import argparse
import json
import os
import random


def add_perceived_occlusion(metadata_file, noise_std, rng):
    with open(metadata_file) as f:
        meta = json.load(f)

    true_occlusion = meta.get("measured_occlusion")
    if true_occlusion is None:
        raise ValueError(f"{metadata_file} has no measured_occlusion yet — run occlusion_estimator first.")

    noise = rng.gauss(0, noise_std)
    perceived_occlusion = true_occlusion + noise
    perceived_occlusion = max(0.0, min(100.0, perceived_occlusion))  # clip to valid range

    gap = abs(perceived_occlusion - true_occlusion)

    meta["perceived_occlusion"] = perceived_occlusion
    meta["injected_noise_std"] = noise_std
    meta["gap"] = gap

    with open(metadata_file, "w") as f:
        json.dump(meta, f, indent=2)

    return perceived_occlusion, gap


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata_file", required=True)
    parser.add_argument("--noise_std", type=float, default=10.0,
                         help="Std dev of injected perception noise (in occlusion percentage points)")
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    perceived, gap = add_perceived_occlusion(args.metadata_file, args.noise_std, rng)
    print(f"[mock_perception] perceived={perceived:.2f}, gap={gap:.2f}")


if __name__ == "__main__":
    main()