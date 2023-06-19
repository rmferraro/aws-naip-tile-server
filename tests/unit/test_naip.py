import pytest
from shapely import wkt

from aws_naip_tile_server.layers.utils.naip import get_naip_geotiffs, get_tile


@pytest.fixture
def sample_aoi():
    # random area in CO
    aoi = "POLYGON ((-105.2709 38.8831, -105.0403 38.8831, -105.0403 39.0795, -105.2709 39.0795, -105.2709 38.8831))"
    return wkt.loads(aoi)


def test_get_valid_tile():
    tile_image = get_tile(11, 776, 425, 2021)
    assert tile_image is not None


def test_get_invalid_tile():
    tile_image = get_tile(11, 425, 776, 2021)
    assert tile_image is None


def test_get_naip_geotiffs_no_params():
    try:
        get_naip_geotiffs(None, None)
        raise AssertionError()
    except Exception as e:
        assert isinstance(e, ValueError)


def test_get_naip_geotiffs_by_year():
    geotiffs = get_naip_geotiffs(year=2011)
    assert len(geotiffs) == 15862


def test_get_naip_geotiffs_by_coverage(sample_aoi):
    geotiffs = get_naip_geotiffs(coverage=sample_aoi)
    assert len(geotiffs) == 100


def test_get_naip_geotiffs_by_year_and_coverage(sample_aoi):
    geotiffs = get_naip_geotiffs(coverage=sample_aoi, year=2013)
    assert len(geotiffs) == 20
