from functools import lru_cache

import src.utils.conversion as conversion
import src.utils.naip as naip
from src.utils.env import TileServerConfig


@lru_cache(maxsize=1)
def _get_tile_server_config() -> TileServerConfig:
    return TileServerConfig.from_env()


def handler(event: dict, _context: object) -> dict:
    """NAIP slippy map tile AWS Lambda function handler.

    https://docs.aws.amazon.com/lambda/latest/dg/python-handler.html

    Parameters
    ----------
    event: dict
        contains information from the invoking service

        when lambda function invoked through gateway api - event.pathParameters should
        have x,y,z,year properties.  when lambda invoked directly (e.g. through boto3),
        event dict itself should have x,y,z,year properties
    _context: object
        information about the invocation, function, and execution environment

        not used anywhere in this function

    Returns
    -------
    dict
        if getting tile was successful, dict will have a statusCode of 200 and contain
        base64 encoded tile as body

        if getting tile wasn't successful - statusCode will be something other than 200
        (depending on reason why tile wasn't successful) and body will be null

    """
    if "pathParameters" in event:
        year = conversion.val_to_type(event["pathParameters"].get("year"), int)
        x = conversion.val_to_type(event["pathParameters"].get("x"), int)
        y = conversion.val_to_type(event["pathParameters"].get("y"), int)
        z = conversion.val_to_type(event["pathParameters"].get("z"), int)
    else:
        year = conversion.val_to_type(event.get("year"), int)
        x = conversion.val_to_type(event.get("x"), int)
        y = conversion.val_to_type(event.get("y"), int)
        z = conversion.val_to_type(event.get("z"), int)

    if not x or not y or not z or not year:
        return {"statusCode": 400, "body": None, "isBase64Encoded": False}

    tile_server_config = _get_tile_server_config()
    if z < tile_server_config.min_zoom or z > tile_server_config.max_zoom:
        return {"statusCode": 400, "body": None, "isBase64Encoded": False}

    if tile_server_config.tile_cache:
        tile_image = tile_server_config.tile_cache.get_tile(x, y, z, year)
        if not tile_image:
            tile_image = naip.get_tile(z, y, x, year)
            if tile_image:
                tile_server_config.tile_cache.save_tile(x, y, z, year, tile_image)
            else:
                tile_server_config.tile_cache.handle_null_tile(x, y, z, year)
    else:
        tile_image = naip.get_tile(z, y, x, year)

    if tile_image:
        b64_tile = conversion.img_to_b64(tile_image, tile_server_config.image_format)
        return {
            "statusCode": 200,
            "headers": {"Content-Type": f"image/{tile_server_config.image_format.lower()}"},
            "body": b64_tile,
            "isBase64Encoded": True,
        }
    else:
        return {"statusCode": 404, "body": None, "isBase64Encoded": False}
