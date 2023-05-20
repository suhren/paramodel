#!/bin/sh

# This file initializes a virtual framebuffer server for
# OpenSCAD and then launches the model generator service

# The error output if you don't have this framebuffer server would be:
# Openscad returned with code -11. See the output:
# Compiling design (CSG Products normalization)...
# Normalized CSG tree has 1 elements
# Unable to open a connection to the X server.
# DISPLAY=
# Can't create OpenGL OffscreenView. Code: -1.
# Geometries in cache: 1
# Geometry cache size in bytes: 498824
# CGAL Polyhedrons in cache: 0
# CGAL cache size in bytes: 0
# Total rendering time: 0:00:00.006

# Start the virtual framebuffer server for OpenSCAD
Xvfb :5 -screen 0 800x600x24 &

# Set the DISPLAY env variable to the same display started by xvfb
export DISPLAY=:5

# Run the python script
python3 -m app.model_generator_service