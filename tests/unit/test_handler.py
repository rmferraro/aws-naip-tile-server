import base64
import os
from io import BytesIO

import pytest
from PIL import Image

from src.lambda_functions.get_naip_tile import _get_tile_server_config, handler
from src.utils.env import TileServerConfig


@pytest.fixture(scope="module")
def tile_server_config():
    return TileServerConfig.from_env()


def test_tile_image_with_naip_coverage_via_event():
    """Test confirms Lambda handler (via event) returns valid image for a tile with NAIP coverage."""
    result = handler({"x": 425, "y": 776, "z": 11, "year": 2021}, {})
    assert result["statusCode"] == 200


def test_tile_image_without_naip_coverage_via_event():
    """Test confirms Lambda handler (via event) returns blank tile image for a tile without NAIP coverage."""
    result = handler({"x": 776, "y": 425, "z": 11, "year": 2021}, {})
    assert result["statusCode"] == 200
    tile_image = Image.open(BytesIO(base64.b64decode(result["body"])))
    extrema = tile_image.convert("L").getextrema()
    assert extrema[0] == extrema[1]


def test_tile_image_with_naip_coverage_via_path_params():
    """Test confirms Lambda handler (via path params) returns valid image for a tile with NAIP coverage."""
    event = {"pathParameters": {"x": 425, "y": 776, "z": 11, "year": 2021}}
    result = handler(event, {})
    assert result["statusCode"] == 200


def test_tile_image_without_naip_coverage_via_path_params():
    """Test confirms Lambda handler (via path params) returns blank tile image for a tile without NAIP coverage."""
    event = {"pathParameters": {"x": 776, "y": 425, "z": 11, "year": 2021}}
    result = handler(event, {})
    assert result["statusCode"] == 200
    tile_image = Image.open(BytesIO(base64.b64decode(result["body"])))
    extrema = tile_image.convert("L").getextrema()
    assert extrema[0] == extrema[1]


def test_missing_parameters():
    """Test confirms Lambda handler (via path params) returns error if required parameters are missing."""
    event = {"pathParameters": {"z": 11, "year": 2021}}
    result = handler(event, {})
    assert result["statusCode"] == 400


def test_min_zoom_violation(tile_server_config):
    """Test confirms Lambda handler (via event) returns error if zoom level is less than configured MinZoom."""
    result = handler({"x": 425, "y": 776, "z": tile_server_config.min_zoom - 1, "year": 2021}, {})
    assert result["statusCode"] == 400


def test_max_zoom_violation(tile_server_config):
    """Test confirms Lambda handler (via event) returns error if zoom level is greater than configured MaxZoom."""
    result = handler({"x": 425, "y": 776, "z": tile_server_config.max_zoom + 1, "year": 2021}, {})
    assert result["statusCode"] == 400


def test_no_cache_bucket():
    """Test confirms Lambda handler (via event) returns valid image even when no TileCacheBucket provided."""
    _get_tile_server_config.cache_clear()
    os.environ["TileCacheBucket"] = ""
    result = handler({"x": 425, "y": 776, "z": 11, "year": 2021}, {})
    assert result["statusCode"] == 200


def test_non_existing_bucket():
    """Test confirms Lambda handler (via event) returns valid image even when erroneous TileCacheBucket provided."""
    _get_tile_server_config.cache_clear()
    os.environ["TileCacheBucket"] = "some-non-existent-bucket"
    result = handler({"x": 425, "y": 776, "z": 11, "year": 2021}, {})
    assert result["statusCode"] == 200
