import mercantile

from src.utils.conversion import bbox_to_box, val_to_type


def test_bbox_to_box():
    bbox = mercantile.LngLatBbox(-180, -90, 180, 90)
    box = bbox_to_box(bbox)
    box_bounds = box.bounds
    assert box_bounds == (-180, -90, 180, 90)


def test_val_to_type():
    converted_val = val_to_type("6", int)
    assert converted_val == 6
