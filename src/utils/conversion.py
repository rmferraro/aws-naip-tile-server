import base64
from io import BytesIO
from typing import Any

import mercantile
from PIL import Image
from shapely.geometry import Polygon, box


def bbox_to_box(bbox: mercantile.Bbox) -> Polygon:
    """Convert mercantile.Bbox to shapely.box.

    Parameters
    ----------
    bbox: mercantile.Bbox
        bbox to to convert

    Returns
    -------
    Polygon
        converted bbox
    """
    return box(bbox[0], bbox[1], bbox[2], bbox[3])


def img_to_b64(image: Image, format: str = "PNG") -> bytes:
    """base64 encode a PIL image.

    Parameters
    ----------
    image: PIL.image
        image to encode
    format: str

    Returns
    -------
    bytes
        base64 encoded image

    """
    buffered = BytesIO()
    if image.mode == "RGB" and format == "PNG":
        image = image.convert("RGBA")
    elif image.mode == "RGBA" and format == "JPEG":
        image = image.convert("RGB")
    image.save(buffered, format=format)
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
