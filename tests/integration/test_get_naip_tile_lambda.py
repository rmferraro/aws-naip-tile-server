import json

import boto3
import pytest
import requests

from aws_naip_tile_server.admin.utils.stack_info import (
    get_is_stack_deployed,
    get_stack_output_value,
)

pytestmark = pytest.mark.skipif(get_is_stack_deployed() is False, reason="AWS Stack not deployed")


@pytest.fixture(scope="module")
def tile_base_uri():
    return get_stack_output_value("NAIPTileApi")


def test_get_valid_tile_via_api(tile_base_uri):
    r = requests.get(f"{tile_base_uri}/2021/11/776/425")
    assert r.status_code == 200


def test_get_invalid_tile_via_api(tile_base_uri):
    r = requests.get(f"{tile_base_uri}/2021/11/425/776")
    assert r.status_code == 404


def test_get_valid_tile_via_boto():
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


def test_get_invalid_tile_via_boto():
    client = boto3.client("lambda")
    payload = {"year": 2021, "x": 776, "y": 425, "z": 11}
    response = client.invoke(
        FunctionName="get-naip-tile",
        InvocationType="RequestResponse",
        Payload=json.dumps(payload),
    )
    response_payload = json.loads(response["Payload"].read())
    assert response_payload["statusCode"] == 404
    assert response_payload["isBase64Encoded"] is False
