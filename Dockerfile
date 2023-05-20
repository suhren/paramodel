# syntax=docker/dockerfile:1

# Specify the start image
FROM ubuntu:20.04

# We might be required to do some user interaction when setting up the container
# One type of such interaction is setting the geographic area. We can avoid thus with the below setting.
# https://askubuntu.com/questions/909277/avoiding-user-interaction-with-tzdata-when-installing-certbot-in-a-docker-contai
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# First install software-properties-common to run the command add-apt-repository
# Read more at https://itsfoss.com/add-apt-repository-command-not-found/
# Usually installed with sudo, but dockerfiles run as sudo by default
RUN apt-get update -y
RUN apt-get install software-properties-common -y

# Add repository for the latest freecad
# Initially, there was the following error:
# > Extension is not a python addable version: 'App::GeoFeatureGroupExtension'
# This was due to a version mismatch between existing freecad file we are trying to load
# (created on version 0.20 on Windows) and the version used to read the file (0.18.4 on linux)
# This is resolved by making sure we are using the latest version on Linux.
# https://launchpad.net/~freecad-maintainers/+archive/ubuntu/freecad-stable
RUN add-apt-repository ppa:freecad-maintainers/freecad-stable

# Also, add the latest openscad since it is used for the image generation
# https://launchpad.net/~openscad/+archive/ubuntu/releases
RUN add-apt-repository ppa:openscad/releases

# Update the package index files after adding repositories
RUN apt-get update -y

# Install python and freecad
RUN apt-get install -y python3.8 python3-pip && pip3 install --upgrade pip
RUN apt-get install -y freecad
RUN apt-get install -y openscad

# Install virtual framebuffer for use with OpenSCAD
RUN apt-get install -y xvfb

# There is an issue with using the FreeCAD Python library where we might get errors like below:
# > Issue: No modules found in /usr/lib/freecad-python3/Mod
# > No modules found in /usr/lib/freecad-python3/Mod
# We create extra symlinks for this to work properly:
# https://forum.freecadweb.org/viewtopic.php?t=37099
# https://forum.freecadweb.org/viewtopic.php?t=33684
RUN ln -s /usr/share/freecad/Ext /usr/lib/freecad-python3/Ext && \
    ln -s /usr/share/freecad/Gui /usr/lib/freecad-python3/Gui && \
    ln -s /usr/share/freecad/Mod /usr/lib/freecad-python3/Mod && \
    ln -s /usr/share/freecad/lib /usr/lib/freecad-python3/lib

# all commands start from this directory
WORKDIR /application

# copy all files from this folder to working directory (ignores files in .dockerignore)
COPY requirements.txt .

# Install dependencies
# We might get an error like this: pip cannot uninstall <package>: "It is a distutils installed project"
# To avoid it, we can specify --ignore-installed when using pip
RUN pip3 install --ignore-installed -r requirements.txt

# copy all files from this folder to working directory (ignores files in .dockerignore)
COPY . .

# RUN is an image build step
# CMD is the command the container executes when you launch the built image.
# A Dockerfile will only use the final CMD defined!
# Set the start command
CMD ["bash", "headless_service.sh"]