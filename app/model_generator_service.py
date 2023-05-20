"""
Module defining a simple web application and REST API to generate parametrized
STL files from CAD models.
"""

import hashlib
import io
import json
import logging
import os
import tempfile
import typing as t

import flask
import pydantic
from freecad import freecad
from openscad import openscad


# Custom Exceptions
class InvalidModelException(Exception):
    """Exception raised when an invalid model has been specified"""


# Local directory paths
CAD_MODEL_DIR = "app/assets"
OUTPUT_DIR = "app/output"
TEMPLATES_DIR = "app/templates"
STATIC_DIR = "app/static"

# Server connection configuration
HOST = "0.0.0.0"
PORT = 80

# Global variables holding information about available models
MODEL_PARAMS = {}
MODEL_PATHS = {}
MODELS = []

app = flask.Flask(
    import_name=__name__,
    template_folder=TEMPLATES_DIR,
    static_folder=STATIC_DIR,
    root_path=os.getcwd(),
)


def initialize_models(cad_model_dir: str = CAD_MODEL_DIR):
    """
    Initialize the path to cad models and their known default parameters into
    global variables of this module.
    :param cad_model_dir: Path to a directory containing FreeCAD .FCStd models
    """
    logging.info("Initializing avaiable CAD models")

    logging.info(f"Listing models in {cad_model_dir}")
    for file_name in os.listdir(cad_model_dir):
        model_name, file_type = os.path.splitext(file_name)

        if file_type != ".FCStd":
            continue

        path = os.path.join(cad_model_dir, file_name)
        logging.info(f"Found model {model_name} at path {path}")
        logging.info(f"Reading parameters from {path}")
        parameters = freecad.get_parameters(path)
        MODEL_PARAMS[model_name] = parameters
        MODEL_PATHS[model_name] = path
        MODELS.append(model_name)

    logging.info(f"Done initializing {len(MODELS)} models: {MODELS}")


def generate_model(model: str, parameters: dict):
    """
    Generate a STL mesh from a model with the given parameters.
    :param model: The name of the model
    :param parameters: A dictionary of parameters that will be set in the model
    """
    if model not in MODELS:
        raise InvalidModelException(f"Input '{model}' must be one of {MODELS}")

    param_str = json.dumps(parameters, sort_keys=True).encode()
    param_hash = hashlib.sha256(param_str).hexdigest()[:8]

    output_path = f"{OUTPUT_DIR}/{model}_{param_hash}.stl"

    freecad.generate_mesh(
        input_path=MODEL_PATHS[model],
        output_path=output_path,
        parameters=parameters,
    )

    return output_path


def _render(**kwargs: t.Any):
    variables = dict(
        available_models=MODELS,
        selected_model=None,
        selected_parameters=None,
        download_link=None,
        download_text=None,
        generated_image=None,
        message="",
    )
    variables.update(kwargs)
    return flask.render_template("model_generator_service.html", **variables)


@app.route("/", methods=["GET"])
def index():
    """
    Starting page for the model generator interface with the default model and
    parameters selected.
    """
    if MODELS:
        selected_model = MODELS[0]
        selected_parameters = MODEL_PARAMS[selected_model]
    else:
        selected_model = None
        selected_parameters = {}

    return _render(
        selected_model=selected_model,
        selected_parameters=selected_parameters,
    )


@app.route("/submit_model", methods=["POST"])
def submit_model():
    """
    Page shown when a model is selected.
    """
    selected_model = flask.request.form.get("select_models")
    selected_parameters = MODEL_PARAMS[selected_model]
    return _render(
        selected_model=selected_model,
        selected_parameters=selected_parameters,
    )


@app.route("/submit_parameters", methods=["POST"])
def submit_parameters():
    """
    Page shown when a model is generated.
    """
    # pylint: disable=broad-except
    message = "Model generated successfully"
    download_link = None
    download_text = None
    parameters = flask.request.form.to_dict()
    model = parameters.pop("selected_model")
    generated_image = None

    logging.info(f"Recieved request to generate {model} with parameters {parameters}")

    try:
        assert model in MODELS
        output_path = generate_model(model=model, parameters=parameters)
        output_filename = os.path.basename(output_path)
        output_image_filename = f"{os.path.splitext(output_filename)[0]}.png"
        output_image_path = f"{OUTPUT_DIR}/{output_image_filename}"
        generated_image = flask.url_for("download", filename=output_image_filename)
        output_filename = os.path.basename(output_path)
        download_link = f"api/download/{output_filename}"
        download_text = output_filename
        openscad.generate_image(
            input_path=output_path,
            output_path=output_image_path,
        )
    except Exception as e:
        message = str(e)

    return _render(
        selected_model=model,
        selected_parameters=parameters,
        download_link=download_link,
        download_text=download_text,
        generated_image=generated_image,
        message=message,
    )


@app.route("/api/health", methods=["GET"])
def health():
    """
    API endpoint for getting the API health
    """
    return flask.jsonify({"status": "ok"})


@app.route("/api/models", methods=["GET"])
def models():
    """
    API endpoint for getting the available models and parameters
    """
    return flask.jsonify(MODEL_PARAMS)


@app.route("/api/download/<filename>", methods=["GET"])
def download(filename: str):
    """
    API endpoint for downloading a generated file
    """
    logging.info(f"Recieved download request for {filename}")

    return flask.send_from_directory(
        directory=OUTPUT_DIR,
        path=filename,
        as_attachment=True,
    )


class GenerationRequest(pydantic.BaseModel):
    """Model generation request passed in the POST requests to the API"""

    # pylint: disable=too-few-public-methods
    class Config:
        """Class to disallow extra attributes in the json"""

        extra = "forbid"

    model: str
    parameters: t.Dict[str, str]


def _generate(request: flask.Request, download_link: bool):
    # pylint: disable=broad-except
    try:
        req = GenerationRequest(**request.json)
        output_path = generate_model(model=req.model, parameters=req.parameters)
        output_filename = os.path.basename(output_path)
    except Exception as e:
        return (
            flask.jsonify(
                {"status": "fail", "message": str(e), "exception": type(e).__name__}
            ),
            500,
        )

    if download_link:
        return flask.jsonify(
            {
                "link": flask.url_for(
                    "download", filename=output_filename, _external=True
                )
            }
        )

    return download(filename=output_filename)


@app.route("/api/generate_and_send", methods=["POST"])
def generate_and_send():
    """
    API endpoint for generating a model and sending it back as a file
    """
    return _generate(flask.request, download_link=False)


@app.route("/api/generate_download_link", methods=["POST"])
def generate_download_link():
    """
    API endpoint for generating a model and sending back a download link
    """
    return _generate(flask.request, download_link=True)


@app.route("/api/generate_image", methods=["POST"])
def generate_image():
    """
    API endpoint for generating a image from a STL file
    """
    file = flask.request.files["file"]
    input_filename = os.path.basename(file.filename)
    output_filename = f"{os.path.splitext(input_filename)[0]}.png"

    with tempfile.TemporaryDirectory() as tempdir:
        input_path = os.path.join(tempdir, input_filename)
        file.save(input_path)

        output_path = os.path.join(tempdir, output_filename)

        openscad.generate_image(
            input_path=input_path,
            output_path=output_path,
        )

        # While it would be possible to simply return the image as the
        # 'output_path' variable, we are removing this tempdir at the same
        # time we return from the function, which would not be possible if the
        # file was open. Therefore, we read the image file into a BytesIO
        # in-memory buffer first to use when returining the image data
        with open(output_path, "rb") as file:
            data = io.BytesIO(file.read())

        return flask.send_file(
            data,
            as_attachment=True,
            download_name=output_filename,
        )


if __name__ == "__main__":
    initialize_models()
    app.run(
        host=HOST,
        port=PORT,
        debug=True,
    )
