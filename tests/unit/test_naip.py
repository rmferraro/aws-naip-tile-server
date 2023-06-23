import mercantile
import pytest
from shapely import wkt

from src.utils.naip import get_naip_geotiffs, get_tile_image


@pytest.fixture
def sample_aoi():
    # random area in CO
    aoi = "POLYGON ((-105.2709 38.8831, -105.0403 38.8831, -105.0403 39.0795, -105.2709 39.0795, -105.2709 38.8831))"
    return wkt.loads(aoi)


def test_get_tile_image_with_naip_coverage():
    """Test confirms requesting a tile image for a tile with NAIP coverage returns None."""
    tile = mercantile.Tile(425, 776, 11)
    tile_image = get_tile_image(tile, 2021)
    assert tile_image is not None


def test_get_tile_image_without_naip_coverage():
    """Test confirms requesting a tile image for a tile without NAIP coverage returns None."""
    tile = mercantile.Tile(776, 425, 11)
    tile_image = get_tile_image(tile, 2021)
    assert tile_image is None


def test_get_naip_geotiffs_no_params():
    """Test confirms that querying NAIP geotiffs without coverage or year raises error."""
    try:
        get_naip_geotiffs(None, None)
        raise AssertionError()
    except Exception as e:
        assert isinstance(e, ValueError)


def test_get_naip_geotiffs_by_year():
    """Test confirms that querying NAIP geotiffs by year alone returns expected result."""
    geotiffs = get_naip_geotiffs(year=2011)
    assert len(geotiffs) == 15862


def test_get_naip_geotiffs_by_coverage(sample_aoi):
    """Test confirms that querying NAIP geotiffs by coverage alone returns expected result."""
    geotiffs = get_naip_geotiffs(coverage=sample_aoi)
    assert len(geotiffs) == 100


def test_get_naip_geotiffs_by_year_and_coverage(sample_aoi):
    """Test confirms that querying NAIP geotiffs by coverage & year returns expected result."""
    geotiffs = get_naip_geotiffs(coverage=sample_aoi, year=2013)
    assert len(geotiffs) == 20
