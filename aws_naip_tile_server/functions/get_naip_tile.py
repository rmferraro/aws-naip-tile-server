import os
from functools import lru_cache

import aws_naip_tile_server.layers.utils.conversion as conversion
import aws_naip_tile_server.layers.utils.naip as naip
from aws_naip_tile_server.layers.utils import logger
from aws_naip_tile_server.layers.utils.tile_cache import S3TileCache


@lru_cache(maxsize=1)
def _get_cache() -> S3TileCache | None:
    """Attempt to get a tile cache based on environment variables.

    Returns
    -------
    S3TileCache
        S3TileCache instance if environment variables support it, else None
    """
    cache_bucket = os.getenv("TILE_CACHE_S3_BUCKET")
    if not cache_bucket:
        logger.warn("TILE_CACHE_S3_BUCKET env var missing - no tilecache")
        return None
    try:
        tile_cache = S3TileCache(cache_bucket)
        logger.info(f"Successfully created S3TileCache backed by bucket: {cache_bucket}")
        return tile_cache
    except Exception as e:
        logger.error(f"error creating S3TileCache backed by bucket {cache_bucket}: {e}")
        return None


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

    cache = _get_cache()
    if cache:
        tile_image = cache.get_tile(x, y, z, year)
        if not tile_image:
            tile_image = naip.get_tile(z, y, x, year)
            if tile_image:
                cache.save_tile(x, y, z, year, tile_image)
    else:
        tile_image = naip.get_tile(z, y, x, year)

    if tile_image:
        b64_tile = conversion.img_to_b64(tile_image)
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "image/jpeg"},
            "body": b64_tile,
            "isBase64Encoded": True,
        }
    else:
        return {"statusCode": 404, "body": None, "isBase64Encoded": False}
