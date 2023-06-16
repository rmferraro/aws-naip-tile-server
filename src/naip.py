import importlib.resources
import os
from functools import cache

import affine
import mercantile
import numpy as np
import polars as pl
import pyproj
import rasterio
from PIL import Image
from rasterio.plot import reshape_as_image
from rasterio.session import AWSSession
from rasterio.vrt import WarpedVRT
from shapely.geometry import box
from shapely.ops import transform

from src.conversion import bbox_to_box

session = AWSSession(
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    requester_pays=True,
)


def _build_image(
    bounds: box,
    year: int,
    epsg: int = 3857,
    height: int = 256,
    width: int = 256,
) -> Image:
    geotiffs = get_naip_geotiffs(bounds, year, epsg)
    if not geotiffs:
        return None

    composite_image = np.zeros((width, height, 3), "uint8")

    # Output image transform
    left, bottom, right, top = bounds.bounds
    xres = (right - left) / width
    yres = (top - bottom) / height
    dst_transform = rasterio.transform.AffineTransformer(affine.Affine(xres, 0.0, left, 0.0, -yres, top))

    with rasterio.Env(session):
        for tif in geotiffs:
            with rasterio.open(tif) as src:
                with WarpedVRT(src, crs=f"EPSG:{epsg}") as vrt:
                    vrt_bounds = box(vrt.bounds[0], vrt.bounds[1], vrt.bounds[2], vrt.bounds[3])
                    if not vrt_bounds.intersects(bounds):
                        # this would occur only if geometry in naip_index is inaccurate
                        continue

                    # determine intersecting area of geotiff with bounds
                    crop_bounds = bounds.intersection(vrt_bounds).bounds

                    # determine the window to use in reading from the dataset.
                    crop_window = vrt.window(crop_bounds[0], crop_bounds[1], crop_bounds[2], crop_bounds[3])

                    # determine where crop data will be written in composite image
                    ul_y, ul_x = dst_transform.rowcol(crop_bounds[0], crop_bounds[3])
                    lr_y, lr_x = dst_transform.rowcol(crop_bounds[2], crop_bounds[1])

                    # crop applicable data from this geotiff
                    crop_data = reshape_as_image(
                        vrt.read(
                            window=crop_window,
                            out_shape=(3, (lr_y - ul_y), (lr_x - ul_x)),
                        )
                    )

                    # naip geotiffs can overlap.  and in overlapping areas, some
                    # image(layers) might have valid pixel data and the other(layers)
                    # dont (ie black pixels).  to avoid overwriting valid pixel data we
                    # compare crop data with composite data, and only overwrite if crop
                    # data has higher pixel value
                    current_data = composite_image[ul_y:lr_y, ul_x:lr_x, :]
                    crop_data = np.maximum(crop_data, current_data)

                    composite_image[ul_y:lr_y, ul_x:lr_x, :] = crop_data

    return Image.fromarray(composite_image)


@cache
def _get_transformer(src_epsg: int, dest_epsg: int):
    src_crs = pyproj.CRS(f"EPSG:{src_epsg}")
    dest_crs = pyproj.CRS(f"EPSG:{dest_epsg}")
    return pyproj.Transformer.from_crs(src_crs, dest_crs, always_xy=True).transform


def get_naip_geotiffs(bounds: box, year: int, epsg: int) -> list[str] | None:
    """Find NAIP rgb geotiffs that cover a specific area, for a specific year.

    Parameters
    ----------
    bounds: shapely.box
        bounding box to query
    year: int
        year to query
    epsg: int
        coordinate reference system that bounds uses

    Returns
    -------
    list[str]
        A list of s3 paths to rgb geotiffs

    """
    if epsg != 4326:
        transformer = _get_transformer(epsg, 4326)
        wgs84_bounds = transform(transformer, bounds)
    else:
        wgs84_bounds = bounds
    bounds = wgs84_bounds.bounds
    naip_index_parquet = importlib.resources.path("src.data", "naip_index.parquet")

    df = pl.read_parquet(naip_index_parquet)
    df = df.filter(
        (pl.col("year") == year)
        & ~(
            (pl.col("max_x") < bounds[0])
            | (pl.col("min_x") > bounds[2])
            | (pl.col("max_y") < bounds[1])
            | (pl.col("min_y") > bounds[3])
        )
    )
    return df["geotiff"].to_list()


def get_tile(z: int, y: int, x: int, year: int) -> Image:
    """Get a NAIP slippy map tile for a specific year.

    Parameters
    ----------
    z: int
        zoom level of tile
    y: int
        y coordinate of tile
    x: int
        x coordinate of tile
    year: int
        NAIP imagery year

    Returns
    -------
    Image
        a tile image, or None if imagery not available for tile for specific year

    """
    tile_box = bbox_to_box(mercantile.xy_bounds(x, y, z))
    return _build_image(tile_box, year)
