import argparse
import logging
import os
import platform
import subprocess
import textwrap
import typing as t
from tempfile import TemporaryDirectory

logging.basicConfig(
    format="%(asctime)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.DEBUG,
)

OPENSCAD_PATH_LINUX = "/usr/bin/openscad"
OPENSCAD_PATH_WINDOWS = "C:/Program Files/OpenSCAD/openscad.exe"
OPENSCAD_PATH = OPENSCAD_PATH_WINDOWS

SYSTEM = platform.system()

if SYSTEM == "Linux":
    OPENSCAD_PATH = OPENSCAD_PATH_LINUX
    if os.environ.get("DISPLAY") is None:
        logging.warning(
            "Environment variable $DISPLAY is not set. "
            "This will cause OpenSCAD to fail when attempting to run. "
            "If you are running in a headless environment, consider using "
            "a virtual framebuffer program like Xvnc or Xvfb. "
            "https://github.com/openscad/openscad/blob/master/doc/testing.txt"
        )
elif SYSTEM == "Windows":
    OPENSCAD_PATH = OPENSCAD_PATH_WINDOWS
else:
    raise Exception(f"Unknown operating system: ''{SYSTEM}")


# Custom Exceptions
class ImageGenerationException(Exception):
    pass


def generate_image(
    input_path: str,
    output_path: str,
    size: t.Tuple[int, int] = (512, 512),
):
    """
    Generate a PNG image from a STL file
    :param input_path: Path to the input STL file
    :param output_path: Path to the output PNG file
    :param size: Tuple on the form (width, height) specifying the image size
    """
    input_path = os.path.abspath(input_path)
    output_path = os.path.abspath(output_path)

    with TemporaryDirectory() as tempdir:
        tempfile = os.path.join(tempdir, "export.scad")

        with open(tempfile, "w", encoding="utf-8") as file:
            file.write(f'import("{input_path}", convexity=1);'.replace("\\", "/"))

        size_str = f"{size[0]},{size[1]}"

        cmd = [
            OPENSCAD_PATH,
            "-o",
            output_path,
            "--autocenter",
            "--viewall",
            f"--imgsize={size_str}",
            tempfile,
        ]

        logging.info(f"Executing command: {cmd}")

        process = subprocess.run(
            cmd,
            text=True,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        if process.returncode != 0:
            raise ImageGenerationException(
                f"Openscad returned with code {process.returncode}. "
                f"See the output:\n{process.stdout}"
            )

        if "ERROR:" in process.stdout:
            if os.path.exists(output_path):
                os.remove(output_path)

            raise ImageGenerationException(
                f"The command encounterd an error. See the output:\n{process.stdout}"
            )


if __name__ == "__main__":
    file_name = os.path.basename(__file__)

    parser = argparse.ArgumentParser(
        description=textwrap.dedent(f"""\
            Automatic OpenSCAD STL image-renderer utility.

            This program calls OpenSCAD to import STL files to generate PNG
            images.

            Example usage:
            {file_name} <my_model.stl> <my_image.png> --size 128,128
            """),
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "input_path",
        type=str,
        help="Input path to the STL file",
    )

    parser.add_argument(
        "output_path",
        type=str,
        help="Output path to the generated image file (must end in .png)",
    )

    parser.add_argument(
        "-s",
        "--size",
        type=lambda x: x.split(","),
        default=(512, 512),
        required=False,
        help="Size of the exported image given as width,height",
    )

    args = parser.parse_args()

    generate_image(
        input_path=args.input_path,
        output_path=args.output_path,
        size=args.size,
    )
