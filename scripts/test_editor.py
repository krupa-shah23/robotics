from world_editor import WorldEditor

editor = WorldEditor("../worlds/manipulation_world.sdf")

editor.hide_model("distractor_cube_4")

editor.save("../worlds/test_generated.sdf")

print("Hidden successfully")
