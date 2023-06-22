import os
from dataclasses import dataclass
from functools import cache
from pathlib import Path

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
from shapely import Geometry
from shapely.geometry import box
from shapely.ops import transform

from src.utils.conversion import bbox_to_box

_naip_index_parquet = os.path.join(Path(__file__).parent.parent, "data", "naip_index.parquet")
_NAIP_INDEX_DF = pl.read_parquet(_naip_index_parquet)


@dataclass()
class AWSGeotiff:
    """A class to represent AWS Geotiff."""

    s3_path: str
    min_x: float
    min_y: float
    max_x: float
    max_y: float
    year: int

    def get_extent(self) -> Geometry:
        """Get extent of geotiff.

        Returns
        -------
        Geometry
            shapely Geometry via box function
        """
        return box(self.min_x, self.min_y, self.max_x, self.max_y)

    def get_resolution(self) -> str:
        """Get resolution of geotiff based on s3_path.

        Returns
        -------
        str
            resolution (eg 60cm) of geotiff
        """
        return self.s3_path.split("/")[5]


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
        for geotiff in geotiffs:
            with rasterio.open(geotiff.s3_path) as src:
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

    # Add an alpha channel, fully opaque (255)
    rgba = np.dstack((composite_image, np.zeros((height, width), dtype=np.uint8) + 255))
    # Make mask of black pixels - mask is True where image is black
    nodata_mask = (rgba[:, :, 0:3] == [0, 0, 0]).all(2)
    # Make alpha channel pixels matched by mask into transparent ones
    rgba[:, :, 3][nodata_mask] = 0
    # Convert Numpy array back to PIL Image
    return Image.fromarray(rgba)


@cache
def _get_transformer(src_epsg: int, dest_epsg: int):
    src_crs = pyproj.CRS(f"EPSG:{src_epsg}")
    dest_crs = pyproj.CRS(f"EPSG:{dest_epsg}")
    return pyproj.Transformer.from_crs(src_crs, dest_crs, always_xy=True).transform


def get_naip_geotiffs(coverage: Geometry = None, year: int = None, epsg: int = 4326) -> list[AWSGeotiff] | None:
    """Find NAIP rgb geotiffs that cover a specific area, for a specific year.

    Parameters
    ----------
    coverage: shapely.Geometry
        geometry to filter geotiffs by
    year: int
        year to filter geotiffs by
    epsg: int
        coordinate reference system that bounds uses

    Returns
    -------
    list[AWSGeotiff]
        A list of AWSGeotiff instances

    """
    if not coverage and not year:
        raise ValueError("must supply coverage and/or year parameters")

    if coverage:
        if epsg != 4326:
            transformer = _get_transformer(epsg, 4326)
            wgs84_coverage = transform(transformer, coverage)
        else:
            wgs84_coverage = coverage
        bounds = wgs84_coverage.bounds

    if coverage and year:
        rows = _NAIP_INDEX_DF.filter(
            (pl.col("year") == year)
            & ~(
                (pl.col("max_x") < bounds[0])
                | (pl.col("min_x") > bounds[2])
                | (pl.col("max_y") < bounds[1])
                | (pl.col("min_y") > bounds[3])
            )
        ).rows(named=True)
    elif coverage:
        rows = _NAIP_INDEX_DF.filter(
            ~(
                (pl.col("max_x") < bounds[0])
                | (pl.col("min_x") > bounds[2])
                | (pl.col("max_y") < bounds[1])
                | (pl.col("min_y") > bounds[3])
            )
        ).rows(named=True)
    else:
        rows = _NAIP_INDEX_DF.filter((pl.col("year") == year)).rows(named=True)

    geotiffs = [AWSGeotiff(**row) for row in rows]

    # if geometry is not a box, test that
    if coverage and wgs84_coverage != box(bounds[0], bounds[1], bounds[2], bounds[3]):
        geotiffs = [gt for gt in geotiffs if wgs84_coverage.intersects(gt.get_extent())]

    return geotiffs


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
