import logging
import json
import os
import hashlib
import typing as t

import flask
import pydantic

from generation import freecad

# Custom Exceptions
class InvalidModelException(Exception):
    pass


# Local directory paths
CAD_MODEL_DIR = "assets"
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


def initialize_models():
    logging.info("Initializing avaiable CAD models")

    logging.info(f"Listing models in {CAD_MODEL_DIR}")
    for file_name in os.listdir(CAD_MODEL_DIR):
        model_name = os.path.splitext(file_name)[0]
        path = os.path.join(CAD_MODEL_DIR, file_name)
        logging.info(f"Found model {model_name} at path {path}")
        logging.info(f"Reading parameters from {path}")
        parameters = freecad.get_parameters(path)
        MODEL_PARAMS[model_name] = parameters
        MODEL_PATHS[model_name] = path
        MODELS.append(model_name)

    logging.info(f"Done initializing {len(MODELS)} models: {MODELS}")


def generate_pot(model: str, parameters: dict):
    if model not in MODELS:
        raise InvalidModelException(f"Input '{model}' must be one of {MODELS}")

    param_str = json.dumps(parameters, sort_keys=True).encode()
    param_hash = hashlib.sha256(param_str).hexdigest()[:8]
    logging.info(param_hash)

    output_path = f"{OUTPUT_DIR}/{model}_{param_hash}.stl"

    freecad.generate_mesh(
        input_path=MODEL_PATHS[model],
        output_path=output_path,
        parameters=parameters,
    )

    return output_path


def render(**kwargs: t.Any):
    variables = dict(
        available_models=MODELS,
        selected_model=None,
        selected_parameters=None,
        download_link=None,
        download_text=None,
        message="",
    )
    variables.update(kwargs)
    return flask.render_template("pot_generator_service.html", **variables)


@app.route("/download/<filename>", methods=["GET", "POST"])
def download(filename: str):
    logging.info(f"Recieved download request for {filename}")

    return flask.send_from_directory(
        directory=OUTPUT_DIR,
        path=filename,
        as_attachment=True,
    )


@app.route("/", methods=["GET"])
def index():
    selected_model = MODELS[0]
    selected_parameters = MODEL_PARAMS[selected_model]
    return render(
        selected_model=selected_model,
        selected_parameters=selected_parameters,
    )


@app.route("/submit_model", methods=["POST"])
def submit_model():
    selected_model = flask.request.form.get("select_models")
    selected_parameters = MODELS[selected_model].parameters
    return render(
        selected_model=selected_model,
        selected_parameters=selected_parameters,
    )


@app.route("/submit_parameters", methods=["POST"])
def submit_parameters():
    message = "Model generated successfully"
    download_link = None
    download_text = None
    parameters = flask.request.form.to_dict()
    model = parameters.pop("selected_model")
    logging.info(f"Recieved request to generate {model} with parameters {parameters}")

    try:
        output_path = generate_pot(model=model, parameters=parameters)
        output_filename = os.path.basename(output_path)
        download_link = f"download/{output_filename}"
        download_text = output_filename
    except Exception as e:
        message = str(e)

    return render(
        selected_model=model,
        selected_parameters=parameters,
        download_link=download_link,
        download_text=download_text,
        message=message,
    )


@app.route("/api/health", methods=["GET"])
def health():
    return flask.jsonify({"status": "ok"})


@app.route("/api/models", methods=["GET"])
def models():
    return flask.jsonify(MODEL_PARAMS)


class GenerationRequest(pydantic.BaseModel):
    class Config:
        """Class to disallow extra attributes in the json"""

        extra = "forbid"

    model: str
    parameters: t.Dict[str, str]


def generate(request: flask.Request, download_link: bool):
    try:
        json = request.json
        req = GenerationRequest(**json)
        output_path = generate_pot(model=req.model, parameters=req.parameters)
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
    else:
        return download(filename=output_filename)


@app.route("/api/generate_and_send", methods=["POST"])
def generate_and_send():
    return generate(flask.request, download_link=False)


@app.route("/api/generate_download_link", methods=["POST"])
def generate_download_link():
    return generate(flask.request, download_link=True)


if __name__ == "__main__":
    initialize_models()
    app.run(
        host=HOST,
        port=PORT,
        debug=True,
    )
