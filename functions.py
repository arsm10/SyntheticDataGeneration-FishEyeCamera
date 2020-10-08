import bpy
import os

if __name__ == "__main__":
    exit("You cannot run this file directly.")

# delete all objects
def delete_all():
    for action in bpy.data.actions:
        bpy.data.actions.remove(action, do_unlink=True)

    for armature in bpy.data.armatures:
        bpy.data.armatures.remove(armature, do_unlink=True)

    for brush in bpy.data.brushes:
        bpy.data.brushes.remove(brush, do_unlink=True)

    for cam in bpy.data.cameras:
        bpy.data.cameras.remove(cam, do_unlink=True)

    for grp in bpy.data.groups:
        bpy.data.groups.remove(grp, do_unlink=True)

    for img in bpy.data.images:
        bpy.data.images.remove(img, do_unlink=True)

    for lamp in bpy.data.lamps:
        bpy.data.lamps.remove(lamp, do_unlink=True)

    for material in bpy.data.materials:
        bpy.data.materials.remove(material, do_unlink=True)

    for mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh, do_unlink=True)

    for object in bpy.data.objects:
        bpy.data.objects.remove(object, do_unlink=True)

    for scene in bpy.data.scenes:
        if scene.name != "Scene":
            bpy.data.scenes.remove(scene, do_unlink=True)

    for texture in bpy.data.textures:
        bpy.data.textures.remove(texture, do_unlink=True)

# add a camera fish eye
def add_fisheye_camera(cam_location, cam_rotation):
    bpy.ops.object.camera_add(view_align=True, location=cam_location, rotation=cam_rotation)
    bpy.context.object.data.type = 'PANO'
    bpy.context.object.data.cycles.panorama_type = 'FISHEYE_EQUIDISTANT'
    # bpy.context.object.data.cycles.fisheye_lens = 1 #2.7
    bpy.context.object.data.cycles.fisheye_fov = 3.14159
    bpy.context.object.data.sensor_width = 8.8
    bpy.context.object.data.sensor_height = 6.6
    return bpy.context.object

def _add_label_data(label_data, name, color):
    label_data.append({'label': name, 'color': color})

def create_object_instance_mhx2(object_path, name, color, label_data):
    if not name:
        raise ValueError("empty object name is not allowed")

    # import the mhx2-model in the scene
    bpy.ops.import_scene.makehuman_mhx2(filepath=object_path)
    bpy.context.object.name = name
    bpy.context.object.color = color

    _add_label_data(label_data, name, color)

    return bpy.context.object

def create_object_instance_obj(object_path, name, color, label_data):
    if not name:
        raise ValueError("empty object name is not allowed")

    # import the obj-model in the scene
    parent = bpy.data.objects.new(name, None)
    bpy.context.scene.objects.link(parent)

    bpy.ops.import_scene.obj(filepath=object_path)

    # create "group"
    obs = bpy.context.selected_editable_objects[:] # editable = not linked from library
    for ob in obs:
        ob.parent = parent

    parent.color = color

    _add_label_data(label_data, name, color)

    return parent

# load motion
def load_motion(motion_path):
    bpy.context.scene['McpEndFrame'] = 5000 # take a large number to load all motion steps
    bpy.context.scene['McpApplyObjectTransforms'] = False
    bpy.ops.mcp.load_and_retarget(filepath=motion_path)
    foot_left_center = bpy.context.object.pose.bones['LeftFoot'].center
    bpy.context.object.location = -foot_left_center
    return bpy.context.object.animation_data.action

def disable_background(value):
    world = bpy.context.scene.world
    worldNt = bpy.data.worlds[world.name].node_tree
    backgroundNode = worldNt.nodes['Background']
    backgroundNode.mute = value

def add_world_node(shaderName):
    # select world node tree
    world = bpy.context.scene.world
    worldNt = bpy.data.worlds[world.name].node_tree
    # create new texture node
    textureNode = worldNt.nodes.get(shaderName) or worldNt.nodes.new(type=shaderName)
    textureNode.name = shaderName
    return textureNode

def set_world_background(textureNode, pinOutName = 'Color'):
    # select world node tree
    world = bpy.context.scene.world
    worldNt = bpy.data.worlds[world.name].node_tree
    backgroundNode = worldNt.nodes['Background']
    backgroundNodeIn = backgroundNode.inputs['Color']
    backgroundNodeIn.default_value = (1.0, 1.0, 1.0, 1.0)

    textureNodeOut = textureNode.outputs[pinOutName]
    # connect 'Color' out of texture node with 'Color' in of Background node
    worldNt.links.new(textureNodeOut, backgroundNodeIn)

def create_background_image_node():
    texImage = add_world_node("ShaderNodeTexImage")
    texImageIn = texImage.inputs['Vector']

    texMapping = add_world_node("ShaderNodeMapping")
    texMapping.rotation.y = 3.14159
    texMappingIn = texMapping.inputs['Vector']
    texMappingOut = texMapping.outputs['Vector']

    texCoord = add_world_node("ShaderNodeTexCoord")
    texCoordOut = texCoord.outputs['Window']

    world = bpy.context.scene.world
    worldNt = bpy.data.worlds[world.name].node_tree
    worldNt.links.new(texCoordOut, texMappingIn)
    worldNt.links.new(texMappingOut, texImageIn)
    return texImage

def create_emission_node(tree, color):
    node = tree.nodes.new(type="ShaderNodeEmission")
    node.inputs['Color'].default_value = color
    return node

def create_tree_surface_map(target):
    mapping = dict()
    for child in target.children:
        for material_slot in child.material_slots.keys():
            material = bpy.data.materials[material_slot]
            material.use_nodes = True
            tree = material.node_tree
            defaultShaderNode  = tree.nodes['Material Output'].inputs['Surface'].links[0].from_node
            defaultShaderNodePin = defaultShaderNode.outputs[0]
            emissionNodePin = create_emission_node(tree, target.color).outputs['Emission']
            mapping[tree] = (emissionNodePin, defaultShaderNodePin)
    return mapping

def enable_color_surface(mapping, value):
    for tree, surfaces in mapping.items():
        output = surfaces[0 if value else 1]
        tree.links.new(output, tree.nodes['Material Output'].inputs['Surface'])

