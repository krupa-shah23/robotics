#!/usr/bin/env python3
"""scenario_generator.py — orchestrates generate -> reset -> measure -> log, relaunch only."""
import argparse, json, os, subprocess, time

CAMERA_HEIGHTS = [0.9, 1.0, 1.1]
LIGHT_LEVELS = [0.4, 0.7, 1.0]
CLUTTER_COUNTS = [0, 2, 4]
NOISE_LEVELS = [0.0, 5.0, 15.0]
DEFAULT_SEEDS_PER_CONDITION = 2

def build_experiment_grid(seeds_per_condition):
    grid = []
    trial_id = 0
    for cam_z in CAMERA_HEIGHTS:
        for light in LIGHT_LEVELS:
            for clutter in CLUTTER_COUNTS:
                for noise_std in NOISE_LEVELS:
                    for rep in range(seeds_per_condition):
                        grid.append({
                            "trial_id": trial_id,
                            "camera_x": 0.0, "camera_y": -1.2, "camera_z": cam_z,
                            "camera_pitch": 0.3,
                            "light": light, "clutter": clutter,
                            "noise_std": noise_std,
                            "seed": trial_id * 7919 + 1,
                        })
                        trial_id += 1
    return grid

def generate_world_for_trial(params, out_dir):
    metadata_file = os.path.join(out_dir, f"trial_metadata_{params['trial_id']:04d}.json")
    world_file = os.path.join(out_dir, f"generated_world_{params['trial_id']:04d}.sdf")
    cmd = [
        "python3",
        os.path.expanduser("~/robotics/scripts/generate_world.py"),
        "--x", str(params["camera_x"]),
        "--y", str(params["camera_y"]),
        "--z", str(params["camera_z"]),
        "--pitch", str(params["camera_pitch"]),
        "--clutter", str(params["clutter"]),
        "--light", str(params["light"]),
        "--seed", str(params["seed"]),
            "--out", world_file,
        "--metadata_file", metadata_file,
        "--bias_sightline",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"generate_world.py failed:\n{result.stderr}")
    return world_file, metadata_file

def reset_via_relaunch(world_file, gz_process_holder):
    GAZEBO_STARTUP_DELAY = 8
    if gz_process_holder.get("proc") is not None:
        gz_process_holder["proc"].terminate()
        try:
            gz_process_holder["proc"].wait(timeout=10)
        except subprocess.TimeoutExpired:
            gz_process_holder["proc"].kill()

    log_file = open("/tmp/gz_debug.log", "w")
    proc = subprocess.Popen(
        ["gz", "sim", world_file, "-r", "-s"],
        env={
            **os.environ,
            "LIBGL_ALWAYS_SOFTWARE": "1",
            "GALLIUM_DRIVER": "llvmpipe",
            "__EGL_VENDOR_LIBRARY_FILENAMES": "/usr/share/glvnd/egl_vendor.d/50_mesa.json",
        },
        stdout=log_file,
        stderr=subprocess.STDOUT,
    )
    gz_process_holder["proc"] = proc
    time.sleep(GAZEBO_STARTUP_DELAY)
    

    # Check if it's actually alive
    if proc.poll() is not None:
        log_file.close()
        with open("/tmp/gz_debug.log") as f:
            print("=== GAZEBO CRASHED, LOG OUTPUT ===")
            print(f.read())
        raise RuntimeError(f"gz sim exited immediately with code {proc.returncode}")

    print(f"[DEBUG] gz sim running, PID={proc.pid}")
    return proc

def run_occlusion_estimator(metadata_file, timeout=25):
    cmd = ["python3", os.path.expanduser("~/robotics/scripts/occlusion_estimator.py"),
           "--metadata_file", metadata_file]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            print(f"[WARN] occlusion_estimator failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
            return False
        return True
    except subprocess.TimeoutExpired as e:
        print(f"[TIMEOUT] occlusion_estimator timed out after {timeout}s")
        print(f"--- Partial STDOUT ---\n{e.stdout}")
        print(f"--- Partial STDERR ---\n{e.stderr}")
        return False

def run_mock_perception(metadata_file, noise_std, seed):
    cmd = [
        "python3",
        os.path.expanduser("~/robotics/scripts/mock_perception.py"),
        "--metadata_file", metadata_file,
        "--noise_std", str(noise_std),
        "--seed", str(seed + 1000)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(result.stderr)


def run_mock_vla(metadata_file, seed):
    cmd = [
        "python3",
        os.path.expanduser("~/robotics/scripts/mock_vla.py"),
        "--metadata_file", metadata_file,
        "--seed", str(seed + 2000)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(result.stderr)

def append_to_master_log(metadata_file, master_log_path):
    with open(metadata_file) as f:
        record = json.load(f)
    with open(master_log_path, "a") as f:
        f.write(json.dumps(record) + "\n")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n_trials", type=int, default=None,
                         help="Limit number of trials (for quick testing); default = full grid")
    parser.add_argument("--out_dir", default=os.path.expanduser("~/robotics/worlds/trials"))
    parser.add_argument("--master_log", default=os.path.expanduser("~/robotics/worlds/all_trials.jsonl"))
    
    parser.add_argument("--seeds_per_condition",type=int,
                        default=DEFAULT_SEEDS_PER_CONDITION,
                        help="Number of random scene repetitions per experiment condition.")
    parser.add_argument("--fresh",action="store_true",help="Delete existing master log before starting.")

    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    if args.fresh and os.path.exists(args.master_log):
        os.remove(args.master_log)

    # Start the ROS2 bridge once, before any trials
    bridge_proc = subprocess.Popen(
        ["ros2", "run", "ros_gz_bridge", "parameter_bridge",
         "--ros-args", "-p",
         f"config_file:={os.path.expanduser('~/robotics/scripts/bridge_config.yaml')}"],
    )
    time.sleep(3)  # let it come up before first trial

    grid = build_experiment_grid(args.seeds_per_condition)
    if args.n_trials is not None:
        grid = grid[:args.n_trials]

    gz_process_holder = {"proc": None}
    timings = []

    try:
        for params in grid:
            t0 = time.time()
            print(f"\n=== Trial {params['trial_id']} ===")
            try:
                world_file, metadata_file = generate_world_for_trial(params, args.out_dir)
                reset_via_relaunch(world_file, gz_process_holder)
                ok = run_occlusion_estimator(metadata_file)
                
                if ok:
                    run_mock_perception(
                        metadata_file,
                        params["noise_std"],
                        params["seed"],
                    )

                    run_mock_vla(
                        metadata_file,
                        params["seed"],
                    )

                    append_to_master_log(
                        metadata_file,
                        args.master_log,
                    )

            except Exception as e:
                print(f"[ERROR] Trial {params['trial_id']} failed: {e}")
            timings.append(time.time() - t0)
            print(f"Trial {params['trial_id']} took {timings[-1]:.2f}s")
    finally:
        if gz_process_holder["proc"] is not None:
            gz_process_holder["proc"].terminate()
            try:
                gz_process_holder["proc"].wait(timeout=10)
            except subprocess.TimeoutExpired:
                gz_process_holder["proc"].kill()
        bridge_proc.terminate()
        try:
            bridge_proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            bridge_proc.kill()

    if timings:
        print(f"\nAvg trial time: {sum(timings)/len(timings):.2f}s")
        print(f"Total: {sum(timings):.2f}s for {len(timings)} trials")

if __name__ == "__main__":
    main()