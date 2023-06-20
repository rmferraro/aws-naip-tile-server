import os

from aws_naip_tile_server.functions.get_naip_tile import _get_cache, handler


def test_valid_tile_via_event():
    result = handler({"x": 425, "y": 776, "z": 11, "year": 2021}, {})
    assert result["statusCode"] == 200


def test_invalid_tile_via_event():
    result = handler({"x": 776, "y": 425, "z": 11, "year": 2021}, {})
    assert result["statusCode"] == 404


def test_valid_tile_via_path_params():
    event = {"pathParameters": {"x": 425, "y": 776, "z": 11, "year": 2021}}
    result = handler(event, {})
    assert result["statusCode"] == 200


def test_invalid_tile_via_path_params():
    event = {"pathParameters": {"x": 776, "y": 425, "z": 11, "year": 2021}}
    result = handler(event, {})
    assert result["statusCode"] == 404


def test_missing_parameters():
    event = {"pathParameters": {"z": 11, "year": 2021}}
    result = handler(event, {})
    assert result["statusCode"] == 400


def test_no_cache_bucket():
    _get_cache.cache_clear()
    os.environ["TILE_CACHE_S3_BUCKET"] = ""
    result = handler({"x": 425, "y": 776, "z": 11, "year": 2021}, {})
    assert result["statusCode"] == 200


def test_non_existing_bucket():
    _get_cache.cache_clear()
    os.environ["TILE_CACHE_S3_BUCKET"] = "some-non-existent-bucket"
    result = handler({"x": 425, "y": 776, "z": 11, "year": 2021}, {})
    assert result["statusCode"] == 200
