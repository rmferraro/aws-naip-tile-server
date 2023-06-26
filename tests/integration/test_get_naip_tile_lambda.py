import json
from io import BytesIO

import boto3
import pytest
import requests
from PIL import Image

from src.utils.stack_info import (
    get_is_cache_enabled,
    get_is_stack_deployed,
    get_stack_output_value,
)

pytestmark = pytest.mark.skipif(get_is_stack_deployed() is False, reason="AWS Stack not deployed")


@pytest.fixture(scope="module")
def tile_base_uri():
    return get_stack_output_value("NAIPTileApi")


@pytest.fixture(scope="module")
def is_cache_enabled():
    return get_is_cache_enabled()


def test_tile_image_with_naip_coverage_via_api(tile_base_uri):
    """Test confirms API gateway returns valid image for a tile with NAIP coverage."""
    r = requests.get(f"{tile_base_uri}/2021/11/776/425")
    assert r.status_code == 200


def test_tile_image_without_naip_coverage_via_api(tile_base_uri, helpers, is_cache_enabled):
    """Test confirms API gateway returns blank image for a tile without NAIP coverage."""
    r = requests.get(f"{tile_base_uri}/2021/11/425/776")
    if is_cache_enabled:
        assert r.status_code == 200
        img = Image.open(BytesIO(r.content))
        assert helpers.is_blank_image(img)
    else:
        assert r.status_code == 404


def test_tile_image_with_naip_coverage_via_boto():
    """Test confirms invoking Lambda via boto3 returns valid image for a tile with NAIP coverage."""
    client = boto3.client("lambda")
    payload = {"year": 2021, "x": 425, "y": 776, "z": 11}
    response = client.invoke(
        FunctionName="get-naip-tile",
        InvocationType="RequestResponse",
        Payload=json.dumps(payload),
    )
    response_payload = json.loads(response["Payload"].read())
    assert response_payload["statusCode"] == 200
    assert response_payload["isBase64Encoded"] is True


def test_tile_image_without_naip_coverage_via_boto(helpers, is_cache_enabled):
    """Test confirms invoking Lambda via boto3 returns blank image for a tile without NAIP coverage."""
    client = boto3.client("lambda")
    payload = {"year": 2021, "x": 776, "y": 425, "z": 11}
    response = client.invoke(
        FunctionName="get-naip-tile",
        InvocationType="RequestResponse",
        Payload=json.dumps(payload),
    )
    response_payload = json.loads(response["Payload"].read())
    if is_cache_enabled:
        assert response_payload["statusCode"] == 200
        tile_image = helpers.decode_b64_image(response_payload["body"])
        assert tile_image is not None
        assert helpers.is_blank_image(tile_image)
    else:
        assert response_payload["statusCode"] == 404
