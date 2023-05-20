# syntax=docker/dockerfile:1

# specify start image
FROM ubuntu:20.04

# https://octopus.com/blog/using-ubuntu-docker-image

# https://askubuntu.com/questions/909277/avoiding-user-interaction-with-tzdata-when-installing-certbot-in-a-docker-contai
# https://askubuntu.com/questions/876240/how-to-automate-setting-up-of-keyboard-configuration-package
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Usually installed with sudo, but dockerfiles run as sudo by default

# First install software-properties-common to run the command add-apt-repository
# Read more at https://itsfoss.com/add-apt-repository-command-not-found/
RUN apt-get update -y
RUN apt-get install software-properties-common -y
# Add repository for the latest freecad and openscad versions
RUN add-apt-repository ppa:freecad-maintainers/freecad-stable
RUN add-apt-repository ppa:openscad/releases
RUN apt-get update -y
# Install python and freecad
RUN apt-get install -y python3.8 python3-pip && pip3 install --upgrade pip
RUN apt-get install -y freecad
RUN apt-get install -y openscad
# Install virtual framebuffer for use with OpenSCAD
RUN apt-get install -y xvfb

# Create extra symlinks for freecad to work properly
RUN ln -s /usr/share/freecad/Ext /usr/lib/freecad-python3/Ext && \
    ln -s /usr/share/freecad/Gui /usr/lib/freecad-python3/Gui && \
    ln -s /usr/share/freecad/Mod /usr/lib/freecad-python3/Mod && \
    ln -s /usr/share/freecad/lib /usr/lib/freecad-python3/lib

# all commands start from this directory
WORKDIR /application

# copy all files from this folder to working directory (ignores files in .dockerignore)
COPY requirements.txt .

# install dependencies
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