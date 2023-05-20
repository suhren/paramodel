#!/bin/sh

# Start the virtual framebuffer server for OpenSCAD
Xvfb :5 -screen 0 800x600x24 &

# Set the DISPLAY env variable to the same display started by xvfb
export DISPLAY=:5

# Run the python script
python3 -m app.model_generator_service