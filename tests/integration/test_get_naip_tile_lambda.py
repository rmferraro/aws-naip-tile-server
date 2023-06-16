import json

import boto3
import pytest
import requests
import tomli


@pytest.fixture(scope="module")
def tile_base_uri():
    with open("./samconfig.toml", mode="rb") as fp:
        config = tomli.load(fp)
        stack_name = config["default"]["global"]["parameters"]["stack_name"]
        client = boto3.client("cloudformation")

        try:
            response = client.describe_stacks(StackName=stack_name)
        except Exception as e:
            raise Exception(
                f"Cannot find stack {stack_name} \n"
                f'Please make sure a stack with the name "{stack_name}" exists'
            ) from e

        stacks = response["Stacks"]
        stack_outputs = stacks[0]["Outputs"]
        api_outputs = [
            output for output in stack_outputs if output["OutputKey"] == "NAIPTileApi"
        ]

        if not api_outputs:
            raise KeyError(f"NAIPTileApi not found in stack {stack_name}")

        return api_outputs[0]["OutputValue"]


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
