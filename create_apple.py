"""Create a first apple with Blender. Run with blender --background --python create_apple.py."""
import bpy
import math
import random
from pathlib import Path
from mathutils import Vector

OUT = Path(__file__).resolve().parent / 'first_apple'
OUT.mkdir(exist_ok=True)
# Start with a new in-memory scene; no existing project files are touched.
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
asset = bpy.data.collections.new('Apple model')
scene.collection.children.link(asset)
studio = bpy.data.collections.new('Studio')
scene.collection.children.link(studio)

def material(name, color, roughness=0.4):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*color, 1)
    shader.inputs['Roughness'].default_value = roughness
    return mat, shader

skin, shader = material('Crimson apple skin', (0.42, 0.014, 0.021), 0.3)
shader.inputs['Coat Weight'].default_value = 0.22
shader.inputs['Coat Roughness'].default_value = 0.26
nodes, links = skin.node_tree.nodes, skin.node_tree.links
attr = nodes.new('ShaderNodeVertexColor')
attr.layer_name = 'Color'
links.new(attr.outputs['Color'], shader.inputs['Base Color'])
noise = nodes.new('ShaderNodeTexNoise')
noise.inputs['Scale'].default_value = 165
noise.inputs['Detail'].default_value = 2
bump = nodes.new('ShaderNodeBump')
bump.inputs['Strength'].default_value = 0.07
bump.inputs['Distance'].default_value = 0.008
links.new(noise.outputs['Fac'], bump.inputs['Height'])
links.new(bump.outputs['Normal'], shader.inputs['Normal'])
bark, _ = material('Warm brown stem', (0.095, 0.034, 0.011), 0.72)
leafmat, ls = material('Living green leaf', (0.045, 0.22, 0.012), 0.42)
la = leafmat.node_tree.nodes.new('ShaderNodeVertexColor')
la.layer_name = 'Color'
leafmat.node_tree.links.new(la.outputs['Color'], ls.inputs['Base Color'])
veinmat, _ = material('Leaf veins', (0.12, 0.29, 0.035), 0.6)

def mesh_object(name, verts, faces, mat, colors=None):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    asset.objects.link(obj)
    mesh.materials.append(mat)
    for poly in mesh.polygons:
        poly.use_smooth = True
    if colors:
        attribute = mesh.color_attributes.new(name='Color', type='FLOAT_COLOR', domain='POINT')
        for entry, color in zip(attribute.data, colors):
            entry.color = (*color, 1)
    return obj

N, M = 160, 100
verts, colors, faces = [], [], []
rng = random.Random(2026)

def apple_point(t, p):
    # Broad shoulders, a narrower base, five subtle lobes and a recessed crown.
    lobes = math.cos(5*p + 0.4)
    r = 1.035 * math.sin(t) * (1 + 0.15*math.cos(t))
    r *= 1 + 0.024*lobes*(0.3 + abs(math.cos(t))**3)
    z = 1.02 + 0.96*math.cos(t)
    z -= 0.275*math.exp(-(t/0.30)**2)
    z += 0.13*math.exp(-((math.pi-t)/0.30)**2)
    z += 0.025*lobes*math.sin(t)*abs(math.cos(t))**4
    return (r*math.cos(p), r*math.sin(p), z)

for i in range(1, M):
    t = math.pi*i/M
    for j in range(N):
        p = 2*math.pi*j/N
        verts.append(apple_point(t, p))
        stripe = (0.5 + 0.5*math.sin(23*p + 2.8*math.sin(3*t)))**8
        mottling = math.sin(9*p + 11*t)*math.sin(17*p - 6*t)
        col = (0.34 + 0.09*stripe + 0.035*mottling,
               0.009 + 0.014*stripe, 0.016 + 0.006*stripe)
        if rng.random() < 0.012:
            col = (0.49, 0.20, 0.075)
        colors.append(col)
for i in range(M-2):
    for j in range(N):
        a = i*N+j
        b = i*N+(j+1)%N
        faces.append((a, a+N, b+N, b))
top, bottom = len(verts), len(verts)+1
verts.extend([apple_point(0, 0), apple_point(math.pi, 0)])
colors.extend([(0.19, 0.033, 0.008), (0.16, 0.023, 0.007)])
for j in range(N):
    k = (j+1)%N
    faces.append((top, j, k))
    a = (M-2)*N
    faces.append((bottom, a+k, a+j))
body = mesh_object('Apple • sculpted fruit', verts, faces, skin, colors)

def tube(name, points, radii, mat, sides=12):
    vertices, polygons = [], []
    points = [Vector(p) for p in points]
    for i, p in enumerate(points):
        tangent = (points[min(i+1, len(points)-1)] - points[max(0, i-1)]).normalized()
        u = tangent.cross(Vector((0, 1, 0))).normalized()
        v = tangent.cross(u).normalized()
        for j in range(sides):
            angle = 2*math.pi*j/sides
            q = p + radii[i]*(math.cos(angle)*u + math.sin(angle)*v)
            vertices.append(q)
    for i in range(len(points)-1):
        for j in range(sides):
            a = i*sides+j
            b = i*sides+(j+1)%sides
            polygons.append((a, b, b+sides, a+sides))
    polygons.append(tuple(reversed(range(sides))))
    polygons.append(tuple((len(points)-1)*sides+j for j in range(sides)))
    return mesh_object(name, vertices, polygons, mat)

points = []
for i in range(20):
    t = i/19
    points.append((0.02 + 0.11*t*t, 0.025*math.sin(t*2), 1.69 + 0.48*t))
tube('Apple • curved stem', points, [0.048*(1-0.36*i/19) for i in range(20)], bark, 16)

def leaf_point(t, s):
    width = 0.27*math.sin(math.pi*t)**0.85
    return (0.1 + 1.04*t,
            0.012 + 0.05*t + s*width,
            2.04 + 0.28*math.sin(t*math.pi/1.9) + 0.052*(1-s*s)*math.sin(math.pi*t) + 0.17*s*math.sin(math.pi*t))

lv, lf, lc = [], [], []
L, W = 44, 16
for i in range(L+1):
    t = i/L
    for j in range(W+1):
        s = 2*j/W-1
        lv.append(leaf_point(t, s))
        f = 1-0.35*abs(s)
        lc.append((0.031*f, (0.18+0.04*math.sin(t*8))*f, 0.008*f))
for i in range(L):
    for j in range(W):
        a = i*(W+1)+j
        lf.append((a, a+W+1, a+W+2, a+1))
leaf = mesh_object('Apple • leaf', lv, lf, leafmat, lc)
sol = leaf.modifiers.new('Natural leaf thickness', 'SOLIDIFY')
sol.thickness = 0.008
def above(t, s):
    p = Vector(leaf_point(t, s))
    p.z += 0.009
    return p
tube('Leaf • central vein', [above(i/40, 0) for i in range(41)], [0.010*(1-0.83*i/40) for i in range(41)], veinmat, 8)
for i, t0 in enumerate((0.19, 0.31, 0.44, 0.57, 0.69, 0.79)):
    for side in (-1, 1):
        pts = [above(t0+0.13*j/10, side*0.86*j/10) for j in range(11)]
        tube(f'Leaf • side vein {i} {side}', pts, [0.0045*(1-0.8*j/10) for j in range(11)], veinmat, 6)

root = bpy.data.objects.new('Apple', None)
asset.objects.link(root)
for obj in list(asset.objects):
    if obj != root:
        obj.parent = root
root['description'] = 'First Blender apple: editable mesh, stem, leaf and veins.'
root['units_note'] = 'Artistic scene units; scale as needed for your Three.js scene.'

floor, _ = material('Warm ivory studio', (0.68, 0.61, 0.49), 0.8)
bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, min(v[2] for v in verts)-0.01))
ground = bpy.context.object
ground.name = 'Studio • ground'
for collection in list(ground.users_collection):
    collection.objects.unlink(ground)
studio.objects.link(ground)
ground.data.materials.append(floor)

def aim(obj, target):
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat('-Z', 'Y').to_euler()

camdata = bpy.data.cameras.new('Portrait camera')
cam = bpy.data.objects.new('Portrait camera', camdata)
studio.objects.link(cam)
cam.location = (3.4, -6.5, 3.15)
aim(cam, (0.12, 0, 1.22))
camdata.type = 'ORTHO'
camdata.ortho_scale = 3.8
scene.camera = cam

def area(name, location, power, size, color):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy, data.shape, data.size, data.color = power, 'DISK', size, color
    obj = bpy.data.objects.new(name, data)
    studio.objects.link(obj)
    obj.location = location
    aim(obj, (0, 0, 1))
area('Key • large softbox', (-3.5, -4, 6), 450, 4, (1, 0.9, 0.8))
area('Fill • cool softbox', (4, -1, 3.8), 180, 3, (0.78, 0.88, 1))
area('Rim • softbox', (0, 3.5, 4.8), 500, 3, (1, 0.92, 0.78))
world = bpy.data.worlds.new('Studio atmosphere')
scene.world = world
world.use_nodes = True
world.node_tree.nodes['Background'].inputs[0].default_value = (0.65, 0.72, 0.8, 1)
world.node_tree.nodes['Background'].inputs[1].default_value = 0.25
scene.render.engine = 'CYCLES'
scene.cycles.samples = 64
scene.cycles.use_denoising = True
scene.render.resolution_x = 1200
scene.render.resolution_y = 1200
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = str(OUT / 'apple_preview.png')
scene.view_settings.view_transform = 'AgX'
scene.render.film_transparent = False

bpy.ops.object.select_all(action='DESELECT')
for obj in asset.objects:
    obj.select_set(True)
bpy.context.view_layer.objects.active = body
for screen in bpy.data.screens:
    for a in screen.areas:
        if a.type == 'VIEW_3D':
            a.spaces.active.region_3d.view_perspective = 'CAMERA'
            a.spaces.active.shading.type = 'MATERIAL'
# GLB contains the apple only; the blend also retains the studio for rendering.
bpy.ops.export_scene.gltf(filepath=str(OUT / 'apple.glb'), export_format='GLB',
                          use_selection=True, export_apply=True,
                          export_cameras=False, export_lights=False)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'apple.blend'))
bpy.ops.render.render(write_still=True)
print('APPLE_DONE', OUT)
