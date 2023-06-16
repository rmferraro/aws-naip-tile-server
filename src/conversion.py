import base64
from io import BytesIO
from typing import Any

import mercantile
from PIL import Image
from shapely.geometry import box


def bbox_to_box(bbox: mercantile.Bbox) -> box:
    """Convert mercantile.Bbox to shapely.box.

    Parameters
    ----------
    bbox: mercantile.Bbox
        bbox to to convert

    Returns
    -------
    shapely.box
        converted bbox
    """
    return box(bbox[0], bbox[1], bbox[2], bbox[3])


def img_to_b64(image: Image) -> bytes:
    """base64 encode a PIL image.

    Parameters
    ----------
    image: PIL.image
        image to encode

    Returns
    -------
    bytes
        base64 encoded image

    """
    buffered = BytesIO()
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue())


def val_to_type(val: Any, val_type: type, raise_error: bool = False) -> Any:
    """Converts a value to specific python type.

    Parameters
    ----------
    val: Any
        value to convert
    val_type: type
        type for converted value
    raise_error: bool
        raise error if conversion fails
    Returns
    Any
        converted value is successful, None if conversion failed and raise_error=False
    -------

    """
    try:
        return val_type(val)
    except Exception:
        if raise_error:
            raise
        return None
