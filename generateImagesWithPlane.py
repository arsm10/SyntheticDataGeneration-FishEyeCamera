#!/usr/bin/env python

import bpy
import os
import random
import sys

from mathutils import Vector

from functions import *
from settings import image_dir, image_dir_tmp, label_map, target_dir, write_label_data

# Add The Path where do you want to extract the Background Image and Generate Synthetic Data
user_dir = "--User Path----"
pic = "--.jpg for Background Image---"
seed = random.randint(0, sys.maxsize)
random.seed(seed)

# user defined values
target_img_h = 1680
target_img_w = 1680

camera_location = (0, 0, 2.5)
camera_rotation = (0, 0, 0)

# resolution percentage
res_per = 50 # use a lower value for test purposes to improve speed

label_data = []

delete_all()

scn = bpy.context.scene
scn.world.use_nodes = True
scn.render.engine = 'CYCLES'
scn.unit_settings.system = 'METRIC'

scn.camera = add_fisheye_camera(camera_location, camera_rotation)

#add plane to generate shadow of the object
bpy.ops.mesh.primitive_plane_add(location=(0,0,0))  
plane = bpy.context.object  
plane.dimensions = (125,125,0)

mat = bpy.data.materials.new('Material')
mat.use_nodes = True
nt = mat.node_tree
nodes = nt.nodes
links = nt.links

# clear
while(nodes): nodes.remove(nodes[0])

output  = nodes.new("ShaderNodeOutputMaterial")
diffuse = nodes.new("ShaderNodeBsdfDiffuse")
texture = nodes.new("ShaderNodeTexImage")
tex_coord  = nodes.new("ShaderNodeTexCoord")

texture.image = bpy.data.images.load(user_dir+pic)

mtex = mat.texture_slots.add()

links.new( output.inputs['Surface'], diffuse.outputs['BSDF'])
links.new(diffuse.inputs['Color'],   texture.outputs['Color'])
links.new(texture.inputs['Vector'],   tex_coord.outputs['Generated'])

plane.data.materials.append(mat)
plane.active_material = mat

# add a lamp
bpy.ops.object.lamp_add(type='POINT', radius=1, view_align=False, location=(0.17, -0.7, 1.7),
    layers=(True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False))
bpy.context.object.data.shadow_soft_size = 0.01
bpy.context.object.data.cycles.cast_shadow = True

target_objects = []

obj_path = os.path.join(user_dir, "human", "human1.mhx2")
target_objects.append(create_object_instance_mhx2(obj_path, "person", (255,255,255,255), label_data))

# apply motion to person to get different poses
motion_path = os.path.join(user_dir, "human", "motion.bvh")
target_action = load_motion(motion_path)

# set the rendering parameter
scn.render.resolution_x = target_img_w
scn.render.resolution_y = target_img_h
scn.render.resolution_percentage = res_per
scn.render.pixel_aspect_x = 1
scn.render.pixel_aspect_y = 1
## add the file format extensions to the rendered file name
scn.render.use_file_extension = True
scn.render.image_settings.color_mode ='RGB'
scn.render.image_settings.compression = 90

#scn.cycles.device = 'GPU'  # enable if a dedicated GPU is available
scn.cycles.progressive = 'PATH'
scn.cycles.samples = 50
scn.cycles.max_bounces = 1
scn.cycles.min_bounces = 1
scn.cycles.glossy_bounces = 1
scn.cycles.transmission_bounces = 1
scn.cycles.volume_bounces = 1
scn.cycles.transparent_max_bounces = 1
scn.cycles.transparent_min_bounces = 1
scn.cycles.use_progressive_refine = True
scn.render.tile_x = 64
scn.render.tile_y = 64

#set_world_background(add_world_node("ShaderNodeTexNoise"))

images = []
dir = os.path.join(user_dir, "background")
for filename in os.listdir(dir):
    imagePath = os.path.join(dir, filename)
    images.append(bpy.data.images.load(imagePath))

background_image_node = create_background_image_node()

set_world_background(background_image_node)

tree_surface_maps = []

init_locations = dict()
for target in target_objects:
    init_locations[target] = target.location.copy()
    tree_surface_maps.append(create_tree_surface_map(target))

write_label_data(label_map, label_data)

num_images = len(images)
if not num_images:
    raise ValueError("At least one background image is required.")

# increase range to place object in different positions
range_x = range(0, 1, 1)
range_y = range(0, 1, 1)
range_z = range(6, 7, 6)

with open(os.path.join(target_dir,'used_setup_config'), 'w') as f:
    f.write("seed: {}\n".format(seed))
    f.write("camera_location: {}\n".format(camera_location))
    f.write("camera_rotation: {}\n".format(camera_rotation))
    f.write("motion_path: {}\n".format(motion_path))
    f.write("range_x: {}\n".format(range_x))
    f.write("range_y: {}\n".format(range_y))
    f.write("range_z: {}\n".format(range_z))

# iterate over different poses
# don't start with one to avoid init position
start_frame = int(target_action.frame_range.x)+30
stop_frame = start_frame + 10 # int(target_action.frame_range.y)

frame = (start_frame + stop_frame)/2
bpy.context.scene.frame_current = frame
# for loops to move object position
for obj_x in range_x:
    for obj_y in range_y:
        for obj_z in range_z:
            background_image_node.image = images[random.randint(0,num_images-1)]
            # TODO avoid collision
            for target in target_objects:
                new_pos = Vector([obj_x*random.random(), obj_y*random.random(), 0])
                target.location = init_locations[target] + new_pos
                target.rotation_euler = (0, 0, obj_z)

            filename = "{}_{}_{}_{}_{}".format("imageWithShadow", frame, obj_x, obj_y, obj_z)
            
            # unhide plane because of step-size
            plane.hide_render = False
            
            # generate train/test image
            disable_background(False)
            for surface_map in tree_surface_maps:
                enable_color_surface(surface_map, False)

            scn.render.image_settings.file_format='JPEG'
            scn.render.filepath = os.path.join(image_dir, filename)
            bpy.ops.render.render(write_still=True)
            
            # hide the plane
            plane.hide_render = True

            # generate image for bounding box detection
            disable_background(True)

            for surface_map in tree_surface_maps:
                enable_color_surface(surface_map, True)

            scn.render.image_settings.file_format='PNG'
            scn.render.filepath = os.path.join(image_dir_tmp, filename)
            bpy.ops.render.render(write_still=True)

