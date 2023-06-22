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


def test_valid_tile_via_event():
    result = handler({"x": 425, "y": 776, "z": 11, "year": 2021}, {})
    assert result["statusCode"] == 200


def test_invalid_tile_via_event():
    result = handler({"x": 776, "y": 425, "z": 11, "year": 2021}, {})
    assert result["statusCode"] == 200
    tile_image = Image.open(BytesIO(base64.b64decode(result["body"])))
    extrema = tile_image.convert("L").getextrema()
    assert extrema[0] == extrema[1]


def test_valid_tile_via_path_params():
    event = {"pathParameters": {"x": 425, "y": 776, "z": 11, "year": 2021}}
    result = handler(event, {})
    assert result["statusCode"] == 200


def test_invalid_tile_via_path_params():
    event = {"pathParameters": {"x": 776, "y": 425, "z": 11, "year": 2021}}
    result = handler(event, {})
    assert result["statusCode"] == 200
    tile_image = Image.open(BytesIO(base64.b64decode(result["body"])))
    extrema = tile_image.convert("L").getextrema()
    assert extrema[0] == extrema[1]


def test_missing_parameters():
    event = {"pathParameters": {"z": 11, "year": 2021}}
    result = handler(event, {})
    assert result["statusCode"] == 400


def test_min_zoom_violation(tile_server_config):
    result = handler({"x": 425, "y": 776, "z": tile_server_config.min_zoom - 1, "year": 2021}, {})
    assert result["statusCode"] == 400


def test_max_zoom_violation(tile_server_config):
    result = handler({"x": 425, "y": 776, "z": tile_server_config.max_zoom + 1, "year": 2021}, {})
    assert result["statusCode"] == 400


def test_no_cache_bucket():
    _get_tile_server_config.cache_clear()
    os.environ["TileCacheBucket"] = ""
    result = handler({"x": 425, "y": 776, "z": 11, "year": 2021}, {})
    assert result["statusCode"] == 200


def test_non_existing_bucket():
    _get_tile_server_config.cache_clear()
    os.environ["TileCacheBucket"] = "some-non-existent-bucket"
    result = handler({"x": 425, "y": 776, "z": 11, "year": 2021}, {})
    assert result["statusCode"] == 200
