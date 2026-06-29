#!/usr/bin/env python3

import xml.etree.ElementTree as ET
from dataclasses import dataclass

@dataclass
class Pose:
    x: float
    y: float
    z: float
    roll: float
    pitch: float
    yaw: float

class WorldEditor:

    def __init__(self, template_path):
        self.template_path = template_path
        self.tree = ET.parse(template_path)
        self.root = self.tree.getroot()

    def find_model(self, model_name):
        return self.root.find(
            f".//model[@name='{model_name}']"
        )

    def get_pose(self, model_name):
        model = self.find_model(model_name)

        if model is None:
            raise ValueError(f"Model '{model_name}' not found.")

        pose = model.find("pose")

        if pose is None:
            raise ValueError(f"Model '{model_name}' has no pose.")

        values = list(map(float, pose.text.split()))

       	return Pose(
            values[0],
    	    values[1],
    	    values[2],
    	    values[3],
    	    values[4],
    	    values[5]
	)
   
    def set_pose(self,
                 model_name,
                 x,
                 y,
                 z,
                 roll=0.0,
                 pitch=0.0,
                 yaw=0.0):

        model = self.find_model(model_name)

        if model is None:
            raise ValueError(f"Model '{model_name}' not found.")

        pose = model.find("pose")

        if pose is None:
            raise ValueError(f"Model '{model_name}' has no pose.")

        pose.text = f"{x} {y} {z} {roll} {pitch} {yaw}"

    def set_light(self, light_name, intensity):
        """
        Update the diffuse lighting intensity.
        """

        light = self.root.find(f".//light[@name='{light_name}']")

        if light is None:
            raise ValueError(f"Light '{light_name}' not found.")

        diffuse = light.find("diffuse")

        if diffuse is None:
            raise ValueError(f"Light '{light_name}' has no diffuse tag.")

        diffuse.text = f"{intensity} {intensity} {intensity} 1"
     
    def save(self, output_path):
        self.tree.write(
            output_path,
            encoding="utf-8",
            xml_declaration=True
        )

    def hide_model(self, model_name):
        """
        Move a model below the ground so Gazebo ignores it.
        """

        self.set_pose(
            model_name,
            0.0,
            0.0,
            -5.0,
            0.0,
            0.0,
            0.0
        )
