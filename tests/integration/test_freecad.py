import os
from freecad import freecad
import stl
import pytest


@pytest.mark.integration
def test_get_parameters():
    input_path = "tests/assets/block.FCStd"

    expected_parameters = {
        "length": "100",
        "width": "200",
        "height": "300",
    }

    actual_parameters = freecad.get_parameters(doc=input_path)

    assert expected_parameters == actual_parameters


@pytest.mark.integration
def test_generate_mesh(tmpdir: str):
    input_path = "tests/assets/block.FCStd"
    output_path = os.path.join(tmpdir, "block.stl")

    parameters = {
        "length": "123",
        "width": "123",
        "height": "123",
    }

    freecad.generate_mesh(
        input_path=input_path,
        output_path=output_path,
        parameters=parameters,
    )

    assert stl.Mesh.from_file(output_path)
