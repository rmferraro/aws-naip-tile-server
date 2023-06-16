from src.handler import handler


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
