#!/usr/bin/env python3
"""
mock_vla.py — scripted, deliberately imperfect 'manipulation attempt'.
Success probability decreases with true occlusion, clutter count, AND
the perception calibration gap — this is intentional: Gap must causally
influence the outcome here so that Contribution 1's regression has a
real, known signal to recover during pipeline validation.
"""
import argparse
import json
import random


BASE_SUCCESS_RATE = 0.95
OCCLUSION_WEIGHT = 0.006
CLUTTER_WEIGHT = 0.03
GAP_WEIGHT = 0.010


def run_mock_trial(metadata_file, rng):
    with open(metadata_file) as f:
        meta = json.load(f)

    true_occlusion = meta.get("measured_occlusion")
    clutter_count = meta.get("clutter_count", 0)
    gap = meta.get("gap")

    if true_occlusion is None:
        raise ValueError(f"{metadata_file} has no measured_occlusion yet.")
    if gap is None:
        raise ValueError(f"{metadata_file} has no gap yet — run mock_perception.py first.")

    success_prob = (
        BASE_SUCCESS_RATE
        - OCCLUSION_WEIGHT * true_occlusion
        - CLUTTER_WEIGHT * clutter_count
        - GAP_WEIGHT * gap
    )
    success_prob = max(0.02, min(0.98, success_prob))

    success = rng.random() < success_prob

    meta["vla_success"] = success
    meta["success_prob_used"] = success_prob

    with open(metadata_file, "w") as f:
        json.dump(meta, f, indent=2)

    return success, success_prob


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata_file", required=True)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    success, prob = run_mock_trial(args.metadata_file, rng)
    print(f"[mock_vla] success={success}, p_used={prob:.3f}")


if __name__ == "__main__":
    main()