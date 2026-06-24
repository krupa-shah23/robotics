#!/usr/bin/env python3
import argparse
import json
import math
import os

import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

IMG_WIDTH = 640
IMG_HEIGHT = 480
HORIZONTAL_FOV = 1.047
FX = (IMG_WIDTH / 2.0) / math.tan(HORIZONTAL_FOV / 2.0)
FY = FX
CX = IMG_WIDTH / 2.0
CY = IMG_HEIGHT / 2.0

TARGET_HALF_SIZE = 0.05
DEPTH_EPSILON = 0.02


def load_camera_pose(sidecar_path):
    if not os.path.exists(sidecar_path):
        raise FileNotFoundError(
            f"Pose sidecar not found at '{sidecar_path}'.\n"
            f"Run: python3 ~/robotics/scripts/generate_world.py first."
        )
    with open(sidecar_path, "r") as f:
        record = json.load(f)
    return (record["x"], record["y"], record["z"],
            record["roll"], record["pitch"], record["yaw"])


def project_point(camera_pose, point_world):
    cam_x, cam_y, cam_z, roll, pitch, yaw = camera_pose
    px, py, pz = point_world

    dx, dy, dz = px - cam_x, py - cam_y, pz - cam_z

    cy_, sy_ = math.cos(-yaw), math.sin(-yaw)
    x1 = dx * cy_ - dy * sy_
    y1 = dx * sy_ + dy * cy_
    z1 = dz

    cp_, sp_ = math.cos(-pitch), math.sin(-pitch)
    x2 = x1 * cp_ + z1 * sp_
    z2 = -x1 * sp_ + z1 * cp_
    y2 = y1

    cr_, sr_ = math.cos(-roll), math.sin(-roll)
    y3 = y2 * cr_ - z2 * sr_
    z3 = y2 * sr_ + z2 * cr_
    x3 = x2

    depth = x3
    if depth <= 0.01:
        return None

    u = CX - (y3 / depth) * FX
    v = CY - (z3 / depth) * FY
    return u, v, depth


def target_silhouette_pixels(camera_pose, target_center):
    half = TARGET_HALF_SIZE
    corners = [
        (target_center[0] + sx * half,
         target_center[1] + sy * half,
         target_center[2] + sz * half)
        for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)
    ]

    projected = [project_point(camera_pose, c) for c in corners]
    projected = [p for p in projected if p is not None]
    if not projected:
        return None, None

    us = [p[0] for p in projected]
    vs = [p[1] for p in projected]
    depths = [p[2] for p in projected]

    u_min, u_max = max(0, int(min(us))), min(IMG_WIDTH - 1, int(max(us)))
    v_min, v_max = max(0, int(min(vs))), min(IMG_HEIGHT - 1, int(max(vs)))
    target_depth = min(depths)

    return (u_min, u_max, v_min, v_max), target_depth


class OcclusionEstimator(Node):
    def __init__(self, pose_sidecar, target_center):
        super().__init__("occlusion_estimator")
        self.bridge = CvBridge()
        self.sub = self.create_subscription(
            Image, "/camera/depth/image_raw", self.depth_callback, 10
        )
        self.camera_pose = load_camera_pose(pose_sidecar)
        self.target_center = target_center

        self.get_logger().info(
            f"Loaded camera pose from sidecar: {self.camera_pose}"
        )
        self.get_logger().info(
            f"Target center: {self.target_center}. Waiting for depth frames..."
        )

    def depth_callback(self, msg):
        depth_img = self.bridge.imgmsg_to_cv2(msg, desired_encoding="32FC1")

        bbox, target_depth = target_silhouette_pixels(self.camera_pose, self.target_center)
        if bbox is None:
            self.get_logger().warn("Target not visible in camera frustum.")
            return

        u_min, u_max, v_min, v_max = bbox
        region = depth_img[v_min:v_max + 1, u_min:u_max + 1]

        valid = np.isfinite(region) & (region > 0)
        total_pixels = int(valid.sum())
        if total_pixels == 0:
            self.get_logger().warn("No valid depth pixels in target bbox.")
            return

        occluded = np.sum(region[valid] < (target_depth - DEPTH_EPSILON))
        occlusion_pct = 100.0 * occluded / total_pixels

        self.get_logger().info(
            f"bbox=({u_min},{v_min})-({u_max},{v_max}) | "
            f"target_depth={target_depth:.3f}m | "
            f"occlusion={occlusion_pct:.1f}%"
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--pose_sidecar",
        default=os.path.expanduser("~/robotics/worlds/current_camera_pose.json")
    )
    parser.add_argument("--target_x", type=float, default=0.0)
    parser.add_argument("--target_y", type=float, default=0.0)
    parser.add_argument("--target_z", type=float, default=0.55)
    args, ros_args = parser.parse_known_args()

    rclpy.init(args=ros_args)
    node = OcclusionEstimator(
        pose_sidecar=args.pose_sidecar,
        target_center=(args.target_x, args.target_y, args.target_z),
    )
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
