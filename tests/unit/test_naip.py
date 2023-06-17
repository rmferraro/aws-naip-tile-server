from aws_naip_tile_server.layers.utils.naip import get_tile


def test_get_valid_tile():
    tile_image = get_tile(11, 776, 425, 2021)
    assert tile_image is not None


def test_get_invalid_tile():
    tile_image = get_tile(11, 425, 776, 2021)
    assert tile_image is None
