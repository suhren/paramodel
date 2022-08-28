import pytest
import os
import json
import tempfile
from app import pot_generator_service


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


@pytest.fixture
def temp_dir():
    """
    Fixture to set up a temporary directory that is deleted on exit.
    """
    with tempfile.TemporaryDirectory() as directory:
        yield directory


@pytest.fixture
def test_client(temp_dir: str, mocker):
    """
    Fixture to generate a test client for the app
    It will set up the configuration of the app to
    - include a dummy model for testing
    - mock functions from FreeCAD mesh generation to not actually run FreeCAD
    - set up a temporary directory where output dummy mesh files will be saved
    """
    pot_generator_service.OUTPUT_DIR = temp_dir
    pot_generator_service.MODELS = [MockModel.name]
    pot_generator_service.MODEL_PATHS = {MockModel.name: MockModel.cad_path}
    pot_generator_service.MODEL_PARAMS = {MockModel.name: MockModel.parameters}

    def _generate_mesh(input_path, output_path, parameters):
        with open(output_path, "a") as file:
            file.write(MockModel.output_file_contents)

    mocker.patch("generation.freecad.get_parameters", return_value=MockModel.parameters)
    mocker.patch("generation.freecad.generate_mesh", side_effect=_generate_mesh)

    # Create a test client using the Flask application configured for testing
    with pot_generator_service.app.test_client() as testing_client:
        yield testing_client


def assert_json_equal(left: dict, right: dict):
    """
    Helper function to assert dictionary equality after sorting their keys
    """
    assert json.dumps(left, sort_keys=True) == json.dumps(right, sort_keys=True)


# Test index route
def test_index(test_client):
    """
    Test the integrity of the index route by returning an OK status response code
    """
    response = test_client.get("/")
    assert response.status_code == 200


# Test API endpoints
def test_api_health(test_client):
    """
    Test the API endpoint to get the API health status in the response
    """
    response = test_client.get("/api/health")
    assert response.status_code == 200
    assert_json_equal(response.json, {"status": "ok"})


def test_api_models(test_client):
    """
    Test the API endpoint to get a dictionary of avaiable models and parameters in the response
    """
    response = test_client.get("/api/models")
    assert response.status_code == 200
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

    assert response.status_code == 200

    download_link = response.json["link"]
    generated_file_name = os.path.basename(download_link)
    generated_file_path = os.path.join(
        pot_generator_service.OUTPUT_DIR, generated_file_name
    )

    assert os.path.exists(generated_file_path)


def test_api_generate_and_send(test_client):
    """
    Test the API endpoint to generate a model and return it as an attachment in the response
    """
    response = test_client.post(
        "/api/generate_and_send",
        json={"model": MockModel.name, "parameters": MockModel.parameters},
    )

    assert response.status_code == 200

    content_disposition = response.headers.get("Content-Disposition")
    file_name = content_disposition.split("filename=")[1]

    # Dummy file with text content and not a true STL file
    assert response.get_data(as_text=True) == MockModel.output_file_contents
