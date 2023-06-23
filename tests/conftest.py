import base64
from io import BytesIO

import pytest
from PIL import Image


class Helpers:
    """A class to contain generic helper methods to be used in tests."""

    @staticmethod
    def is_blank_image(img: Image) -> bool:
        """Test if an PIL image is 'blank' (ie all pixels have save value).

        Parameters
        ----------
        img: Image
            image to test

        Returns
        -------
        bool:
            True if image pixels are all same value, False otherwise

        """
        extrema = img.convert("L").getextrema()
        return extrema[0] == extrema[1]

    @staticmethod
    def decode_b64_image(b64_img: str | bytes | bytearray) -> Image:
        """Decode b64 image data into PIL.Image.

        Parameters
        ----------
        b64_img: str | bytes | bytearray
            b64 encoded image

        Returns
        -------
        Image:
            Decoded image

        """
        return Image.open(BytesIO(base64.b64decode(b64_img)))


@pytest.fixture
def helpers():
    return Helpers
