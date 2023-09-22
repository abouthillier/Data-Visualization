import os
import numpy as np
from pyproj import Proj
from mathutils import Matrix, Vector
import mathutils
from matplotlib import cm 
#import overpy
import pandas as pd

import bpy
import bmesh
import utils
import utils_osm
from math import sin, cos, pi
from pathlib import Path

def normalize_points(points):
    """Normalize points while preserving aspect ratio"""

    data = np.array(points)

    minX, minY = np.min(data, axis=0)
    maxX, maxY = np.max(data, axis=0)
    rangeX, rangeY = maxX - minX, maxY - minY

    if rangeX > rangeY:
        data[:, 0] = (data[:, 0] - minX - 0.5*rangeX) / rangeX + 0.5
        data[:, 1] = (data[:, 1] - minY - 0.5*rangeY) / rangeX + 0.5
    else:
        data[:, 0] = (data[:, 0] - minX - 0.5*rangeX) / rangeY + 0.5
        data[:, 1] = (data[:, 1] - minY - 0.5*rangeY) / rangeY + 0.5

    return data


def heatmap_grid(data, sigma_sq=0.0001, n=20, m=2):
    """Create n by n grid with heatmap from data with gaussian distribution of input data set"""

    X = np.ndarray((n, n), dtype=object)
    for idx in np.arange(len(points)):
        x, y = data[idx]
        i, j = int(x * (n - 1)), int(y * (n - 1))
        if X[i, j] is None:
            X[i, j] = [(x, y)]
        else:
            X[i, j].append((x, y))
    
    grid = np.zeros((n, n))

    for i0 in range(n):
        for j0 in range(n):
            x0, y0 = i0 / (n - 1), j0 / (n - 1)

            # Sum all available neighboring elements
            for i in range(max(0, i0 - m), min(i0 + m, n)):
                for j in range(max(0, j0 - m), min(j0 + m, n)):
                    if X[i, j] is not None:
                        for x, y in X[i, j]:
                            grid[i0][j0] += np.exp(- ((x0 - x)**2)/
                                (2*sigma_sq) - ((y0 - y)**2)/(2*sigma_sq))

    #print(grid)
    return grid


def heatmap_barplot(grid, h=4, width=10, bar_scale=0.9, num_colors=10, colormap=cm.summer, bevel_width=0.015, logarithmic=False):
    """Create 3D barplot from heatmap grid"""

    # Logarithmic scale
    if logarithmic:
        grid = np.log(grid + 1)

    # Find maximum value
    z_max = np.max(grid)

    n, m = grid.shape
    bar_width = bar_scale * width / max(n, m)

    # List of bmesh elements for each color group
    bmList = [bmesh.new() for _ in range(num_colors)]

    # Iterate over grid
    for i in range(n):
        for j in range(m):
            x, y, z = i / (n - 1), j / (m - 1), grid[i][j]
            if z > 0.001:
                bar_height = ((h - bar_width) * z / z_max) + bar_width
                t = 1 - np.exp(-(z / z_max)/0.2)
                k = min(int(num_colors*t), num_colors - 1)
                bm = bmList[k]

                T = Matrix.Translation(Vector((
                    width*(x - 0.5),
                    width*(y - 0.5),
                    bar_height / 2)))

                S = Matrix.Scale(bar_height / bar_width, 4, Vector((0, 0, 1)))

                if bpy.app.version < (2, 80, 0):
                    bmesh.ops.create_cube(bm, size=bar_width, matrix=T*S)
                else:
                    bmesh.ops.create_cube(bm, size=bar_width, matrix=T@S)

    objList = []
    for i, bm in enumerate(bmList):
        # Create object
        obj = utils.bmesh_to_object(bm)

        # Create material with colormap
        color = colormap(i / num_colors)
        mat = utils.simple_material(color[:3])
        obj.data.materials.append(mat)
        objList.append(obj)

        # Add bevel modifier
        bevel = obj.modifiers.new('Bevel', 'BEVEL')
        bevel.width = bevel_width

    bm_plane = bmesh.new()
    bmesh.ops.create_circle(bm_plane, radius=n**2)
    obj = utils.bmesh_to_object(bm_plane)
    mat = utils.simple_material(color[:3])
    obj.data.materials.append(mat)
    objList.append(obj)



"""

Blender Scene Variables

"""

# Set resolution of rendered image
res_x, res_y = 1280, 720

camera_position, target_position = (9.5, -20, 13), (0.3, -1.8, 2.0)
camera_type, ortho_scale, lens = 'PERSP', 18, 50
bg_color = (0.9, 0.9, 0)

# Remove all default elements in the scene
if bpy.app.version < (2, 80, 0):
    bpy.ops.object.select_by_layer()
else:
    bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

# Create scene
target = utils.create_target(target_position)
camera = utils.create_camera(camera_position, target=target, camera_type=camera_type, ortho_scale=ortho_scale, lens=lens)
sun = utils.create_lamp((5, 5, 10), 'SUN', target=target)
label = utils.create_text("Invasive Plant Species Distribution in RI")
#ground = util.create_plane()

# Set background color
if bpy.app.version < (2, 80, 0):
    bpy.context.scene.world.horizon_color = bg_color
else:
    bpy.context.scene.world.color = bg_color

# Ambient occlusion
bpy.context.scene.world.light_settings.use_ambient_occlusion = True
if bpy.app.version < (2, 80, 0):
    bpy.context.scene.world.light_settings.samples = 8


# Load data points
path = Path(os.path.dirname(os.path.abspath(__file__)))
print(path.parents[0])
filepath = 'data.csv'
datapath = path.parents[0].name + filepath

# data.csv moves to blender folder temporarily
dataframe = pd.read_csv(filepath)

points_df = dataframe.get(['X', 'Y'])
points = points_df.values.tolist()

print('Number of points: {}'.format(len(points)))

# Project points into Mercator projection
p = Proj(init="epsg:3785")  # Popular Visualisation CRS / Mercator
points = np.apply_along_axis(lambda x : p(*x), 1, points)

data = normalize_points(points)

hist = heatmap_grid(data, sigma_sq=0.00005, n=80)

heatmap_barplot(hist, colormap=cm.viridis)

render_folder = 'render'
render_name = 'render'
animation = False
num_frames = 0
utils.render_to_folder(render_folder, render_name, res_x=res_x, res_y=res_y, animation=animation, frame_end=num_frames, render_opengl=False)