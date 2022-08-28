# https://freecad-python-stubs.readthedocs.io/en/latest/

import re
import sys
import json
import logging
import textwrap
import argparse
import platform
import typing as t


logging.basicConfig(
    format="%(asctime)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.DEBUG,
)

# Custom Exceptions
class GenerationException(Exception):
    pass


# Path to the FreeCAD libraries
# Change this depending on your installation or if you use Windows/Linux
FREECAD_PATH_LINUX = "/usr/lib/freecad/lib"
FREECAD_PATH_WINDOWS = "C:/Program Files/FreeCAD 0.20/bin"

system = platform.system()

if system == "Linux":
    logging.debug("Loading Linux FreeCAD library")
    sys.path.append(FREECAD_PATH_LINUX)
elif system == "Windows":
    logging.debug("Loading Windows FreeCAD library")
    sys.path.append(FREECAD_PATH_WINDOWS)
else:
    raise Exception(f"Unknown operating system: ''{system}")


import FreeCAD
import Mesh


def get_parameters(doc: t.Union[str, FreeCAD.Document]):
    if not isinstance(doc, FreeCAD.Document):
        doc = FreeCAD.open(doc)

    sheet = doc.getObject("Spreadsheet")

    # Messy "hack" to get the available aliases in the Spreadsheet?
    # Might there be a better way?
    available_parameters = {}
    for line in sheet.cells.Content.splitlines():
        alias = re.findall(r'alias="(\S+)"', line)
        content = re.findall(r'content="(\S+)"', line)
        if alias and content:
            available_parameters[alias[0]] = content[0]

    return available_parameters


def generate_mesh(
    input_path: str,
    output_path: str,
    parameters: t.Optional[dict] = None,
):
    """
    Generate a mesh from a FreeCAD file with the given parameters.
    :param input_path: The path to the FreeCAD cad file
    :param output_path: The output path to the resulting mesh file
    :param parameters: A dictionary of parameters to set in the file
    """

    logging.debug(f"Opening FreeCAD file at {input_path}")
    doc = FreeCAD.open(input_path)

    logging.debug("Getting objects from document")
    obj = doc.getObject("Body")
    sheet = doc.getObject("Spreadsheet")

    # Messy "hack" to get the available aliases in the Spreadsheet?
    # Might there be a better way?
    available_parameters = get_parameters(doc=doc)

    logging.debug(f"Found default parameters {available_parameters}")

    # Set the parameters if specified
    if parameters:
        # Filter out None values
        parameters = {k: v for k, v in parameters.items() if v is not None}

        if not set(parameters).issubset(available_parameters):
            raise GenerationException(
                f"Recieved the parameters {parameters}, but found only the "
                f"parameters {available_parameters} exist in the input file."
            )

        # The spreadsheet object only accepts string values
        parameters = {k: str(v) for k, v in parameters.items()}

        logging.debug(f"Setting parameter values {parameters}")
        for parameter_name, value in parameters.items():
            sheet.set(parameter_name, value)

        new_parameters = {**available_parameters, **parameters}
        logging.debug(f"Recomputing  with updated parameters {new_parameters}")

        recompute_code = doc.recompute()
        # If the document is still touched, something went wrong with the
        # recompute and there are changes that did not go through
        if doc.isTouched():
            raise GenerationException(
                "Could not recompute the document after updating parameters. "
                f"The recompute operation returned the code {recompute_code}. "
                f"Make sure that the parameters are valid: {new_parameters}"
            )
    else:
        logging.debug(f"No parameters specified, using default found in file")

    # Export the mesh as the specified file type
    logging.debug(f"Exporting mesh to {output_path}")
    Mesh.export([obj], output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=textwrap.dedent(
            """\
            Automatic FreeCAD model parametrizer and exporter

            This program can automatically perform the following steps:
            1. Open an existing FreeCAD .FCStd file
            2. Modify parametric dimension aliases in the Spreadsheet object
            3. Update and recompute the model
            4. Export the results as a mesh file

            This enables programatic generation of different mesh files from a
            single CAD file by overriding parameters (aliases) provided through
            this program. For example, a CAD file might define a model of a cup
            with some diameter and height specified in its corresponding
            Spreadsheet object as "cup_diameter" and "cup_height". This program
            can then be run as follows to generate diffent variants of the cup:

            Cup with diameter 100 mm and height 60 mm:
            main.py <cup.FCStd> <mesh1.stl> -p '{"cup_diameter": 100, "cup_height": 60}'

            Cup with diameter 80 mm and height set to exiting dimension in model:
            main.py <cup.FCStd> <mesh2.stl> -p '{"cup_diameter": 80}'
            """
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "input_path",
        type=str,
        help=textwrap.dedent(
            """\
            Path to the FreeCAD .FCStd file defining the model.
            The file is required to have the following objects:
            - Spreadsheet object with parametric dimensions with aliases
            - Body object with the Part referencing the aliases
            """
        ),
    )

    parser.add_argument(
        "output_path",
        type=str,
        help=textwrap.dedent(
            """\
            Output path to the generated mesh file.
            The file ending determines the type of mesh, like .stl or .3mf.
            See the FreeCAD documentation for available output file types.
            """
        ),
    )

    parser.add_argument(
        "-p",
        "--parameters",
        type=json.loads,
        required=False,
        help=textwrap.dedent(
            """\
            JSON string used to override existing Spreadsheet parameters.
            The string should be formatted as a JSON string like
            '{\"key1\": value1, \"key2\": value2}'.
            """
        ),
    )

    args = parser.parse_args()

    generate_mesh(
        input_path=args.input_path,
        output_path=args.output_path,
        parameters=args.parameters,
    )
