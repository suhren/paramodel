import json
import os
import re

import pytest
from app import model_generator_service


class MockModel:
    """
    Single mocked model used for testing.
    """

    name: str = "block"
    cad_path: str = "tests/assets/block.FCStd"
    parameters: dict = {
        "length": "100",
        "width": "200",
        "height": "300",
    }
    output_file_contents: str = "test"


HTTP_OK = 200


@pytest.fixture(name="test_client")
def fixture_test_client(tmpdir, mocker):
    """
    Fixture to generate a test client for the app
    It will set up the configuration of the app to
    - include a dummy model for testing
    - mock functions from FreeCAD mesh generation to not actually run FreeCAD
    - set up a temporary directory where output dummy mesh files will be saved
    """

    model_generator_service.OUTPUT_DIR = tmpdir
    model_generator_service.MODELS = [MockModel.name]
    model_generator_service.MODEL_PATHS = {MockModel.name: MockModel.cad_path}
    model_generator_service.MODEL_PARAMS = {MockModel.name: MockModel.parameters}

    def _generate_mesh(input_path, output_path, parameters):
        with open(output_path, "w", encoding="utf-8") as file:
            file.write(MockModel.output_file_contents)

    def _generate_image(input_path, output_path):
        with open(output_path, "w", encoding="utf-8") as file:
            file.write("mock_image_contents")

    mocker.patch("freecad.freecad.get_parameters", return_value=MockModel.parameters)
    mocker.patch("freecad.freecad.generate_mesh", side_effect=_generate_mesh)
    mocker.patch("openscad.openscad.generate_image", side_effect=_generate_image)

    # Create a test client using the Flask application configured for testing
    with model_generator_service.app.test_client() as testing_client:
        yield testing_client


def assert_json_equal(left: dict, right: dict):
    """
    Helper function to assert dictionary equality after sorting their keys
    """
    assert json.dumps(left, sort_keys=True) == json.dumps(right, sort_keys=True)


# Test routes
def test_index(test_client):
    """
    Test the integrity of index route by returning an OK status
    """
    response = test_client.get("/")
    assert response.status_code == HTTP_OK


def test_submit_model(test_client):
    """
    Test the integrity of test_submit_model route by returning an OK status
    """
    response = test_client.post(
        "/submit_model",
        content_type="multipart/form-data",
        data={"select_models": MockModel.name},
    )
    assert response.status_code == HTTP_OK


def test_submit_parameters(test_client):
    """
    Test the integrity of test_submit_parameters route by returning an OK status
    """
    response = test_client.post(
        "/submit_parameters",
        content_type="multipart/form-data",
        data={"selected_model": MockModel.name, **MockModel.parameters},
    )
    assert response.status_code == HTTP_OK


# Test API endpoints
def test_api_health(test_client):
    """
    Test the API endpoint to get the API health status in the response
    """
    response = test_client.get("/api/health")
    assert response.status_code == HTTP_OK
    assert_json_equal(response.json, {"status": "ok"})


def test_api_models(test_client):
    """
    Test API endpoint to get a dict of avaiable models and parameters in the response
    """
    response = test_client.get("/api/models")
    assert response.status_code == HTTP_OK
    assert_json_equal(
        response.json,
        {MockModel.name: MockModel.parameters},
    )


def test_api_generate_download_link(test_client):
    """
    Test the API endpoint to generate a model and return a download link in the response
    """
    response = test_client.post(
        "/api/generate_download_link",
        json={"model": MockModel.name, "parameters": MockModel.parameters},
    )

    assert response.status_code == HTTP_OK

    download_link = response.json["link"]
    file_name = os.path.basename(download_link)

    # Check that the filename is the name of the model followed by a hex string
    assert re.match(f"{MockModel.name}_[a-fA-F0-9]+.stl", file_name)

    generated_file_path = os.path.join(model_generator_service.OUTPUT_DIR, file_name)

    assert os.path.exists(generated_file_path)


def test_api_generate_and_send(test_client):
    """
    Test API endpoint to generate a model and return it as an attachment in the response
    """
    response = test_client.post(
        "/api/generate_and_send",
        json={"model": MockModel.name, "parameters": MockModel.parameters},
    )

    assert response.status_code == HTTP_OK

    content_disposition = response.headers.get("Content-Disposition")
    file_name = content_disposition.split("filename=")[1]

    # Check that the filename is the name of the model followed by a hex string
    assert re.match(f"{MockModel.name}_[a-fA-F0-9]+.stl", file_name)

    # Dummy file with text content and not a true STL file
    assert response.get_data(as_text=True) == MockModel.output_file_contents


def test_generate_image(test_client):
    """
    Test the API endpoint to generate a image from a STL file
    """

    data = {
        "size": [128, 128],
        # "file": (io.BytesIO(b"some initial text data"), "test.stl"),
        "file": open("tests/assets/test.stl", "rb"),
    }
    response = test_client.post(
        "/api/generate_image",
        data=data,
        content_type="multipart/form-data",
    )

    assert response.status_code == HTTP_OK

    content_disposition = response.headers.get("Content-Disposition")
    file_name = content_disposition.split("filename=")[1]

    assert file_name == "test.png"

    # Dummy file with text content and not a true PNG file
    assert response.get_data(as_text=True) == "mock_image_contents"
