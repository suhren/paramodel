import os
import pytest
import imageio.v3 as imageio
from openscad import openscad


@pytest.mark.integration
def test_generate_image(tmpdir: str):
    input_path = "tests/assets/test.stl"
    output_path = os.path.join(tmpdir, "test.png")
    size = (256, 256)

    openscad.generate_image(
        input_path=input_path,
        output_path=output_path,
        size=size,
    )

    image = imageio.imread(output_path)

    assert image.shape == (*size, 3)
