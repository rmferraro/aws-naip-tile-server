import mercantile
import shapely

from src.utils.conversion import bbox_to_box, val_to_type


def test_bbox_to_box():
    """Test confirms conversion of LngLatBbox to Polygon."""
    bbox = mercantile.LngLatBbox(-180, -90, 180, 90)
    box = bbox_to_box(bbox)
    assert isinstance(box, shapely.Polygon)
    box_bounds = box.bounds
    assert box_bounds == (-180, -90, 180, 90)


def test_val_to_type():
    """Test confirms typed conversion of arbitrary object."""
    converted_val = val_to_type("6", int)
    assert converted_val == 6
