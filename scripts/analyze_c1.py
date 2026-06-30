#!/usr/bin/env python3
"""analyze_c1.py — validates the calibration-gap pipeline against synthetic data."""
import json
from collections import Counter
import pandas as pd
import statsmodels.api as sm

rows = [json.loads(l) for l in open("/home/student/robotics/worlds/all_trials.jsonl")]
df = pd.DataFrame(rows)
df["vla_success"] = df["vla_success"].astype(int)

print("=== Grid balance check ===")
print("clutter:", Counter(df.clutter_count))
print("noise:", Counter(df.injected_noise_std))
print(f"total: {len(df)}, successes: {df.vla_success.sum()}, failures: {len(df)-df.vla_success.sum()}")

print("\n=== Gap by outcome ===")
print(df.groupby("vla_success")["gap"].agg(["mean", "std", "count"]))

print("\n=== Model 1: occlusion only ===")
m1 = sm.Logit(df.vla_success, sm.add_constant(df.measured_occlusion)).fit()
print(m1.summary())

print("\n=== Model 2: occlusion + gap ===")
m2 = sm.Logit(df.vla_success, sm.add_constant(df[["measured_occlusion", "gap"]])).fit()
print(m2.summary())

print(f"\nMcFadden R² m1: {m1.prsquared:.4f}")
print(f"McFadden R² m2: {m2.prsquared:.4f}")
print(f"R² improvement: {m2.prsquared - m1.prsquared:.4f}")