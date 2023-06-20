import asyncio

import aiohttp
import click
import mercantile
import polars as pl
from shapely import union_all, wkt
from tqdm.asyncio import tqdm_asyncio

from aws_naip_tile_server.admin.utils.stack_info import (
    get_is_cache_enabled,
    get_is_stack_deployed,
    get_stack_output_value,
)
from aws_naip_tile_server.layers.utils import logger
from aws_naip_tile_server.layers.utils.conversion import bbox_to_box
from aws_naip_tile_server.layers.utils.naip import get_naip_geotiffs

pl.Config.set_tbl_rows(1000)
pl.Config.set_tbl_hide_dataframe_shape(True)


def _seed_tiles_by_year(tiles: list[mercantile.Tile], year: int):
    naip_tile_api_base_uri = get_stack_output_value("NAIPTileApi")

    async def _invoke_get_naip_tile_lambda(session: aiohttp.ClientSession, tile: mercantile.Tile, year: int):
        url = f"{naip_tile_api_base_uri}/{year}/{tile.z}/{tile.y}/{tile.x}"
        await session.request("GET", url=url)

    async def _seed_tiles_runner():
        async with aiohttp.ClientSession() as session:
            tasks = []
            for t in tiles:
                tasks.append(_invoke_get_naip_tile_lambda(session=session, tile=t, year=year))
            await tqdm_asyncio.gather(*tasks)

    asyncio.run(_seed_tiles_runner())


def _validate_coverage(_ctx, _param, value):
    try:
        if not value:
            return None
        coverage = wkt.loads(value)
        west, south, east, north = coverage.bounds
        if west < -180 or south < -90 or east > 180 or north > 90:
            raise click.BadParameter("coverage not valid WGS84 geometry")
        return coverage
    except Exception:
        raise click.BadParameter("Error parsing coverage_wkt to geometry")


def _seed_preflight_check(from_zoom, to_zoom, _years, _coverage, dry_run):
    if from_zoom > to_zoom:
        raise click.BadParameter("from_zoom must be less that to_zoom")

    if not dry_run and not get_is_stack_deployed():
        if not get_is_stack_deployed():
            msg = "Stack not deployed to AWS. If this is expected, try running with --dry_run flag"
            raise click.ClickException(msg)

    if not dry_run and not get_is_cache_enabled():
        msg = "Tile cache does not appear to be enabled. If this is expected, try running with --dry_run flag"
        raise click.ClickException(msg)


@click.command()
@click.option("--from_zoom", type=int, default=0, help="Zoom level caching will start at")
@click.option("--to_zoom", type=int, required=True, help="Zoom level caching will end at")
@click.option(
    "--years",
    "-y",
    type=int,
    multiple=True,
    help="NAIP years to cache",
)
@click.option(
    "--coverage",
    callback=_validate_coverage,
    help="WKT geometry (WGS84) of ground area to cache tiles for",
)
@click.option("--dry-run", is_flag=True, help="Only print summary of how many tiles would be cached")
def seed(from_zoom, to_zoom, years, coverage, dry_run):
    """Seed Tile Cache for specific areas/years."""
    _seed_preflight_check(from_zoom, to_zoom, years, coverage, dry_run)
    for year in years:
        tileable_geotiffs = get_naip_geotiffs(coverage, year)
        logger.info(f"{len(tileable_geotiffs)} tile-able geotiffs found for year: {year}")
        if not tileable_geotiffs:
            continue

        tileable_geotiff_coverage = union_all([gt.get_extent() for gt in tileable_geotiffs])

        # cache zoom levels in descending order to maximize downscaling of existing tiles
        cache_tilesets = []
        for zoom in sorted(range(from_zoom, to_zoom + 1), reverse=True):
            west, south, east, north = tileable_geotiff_coverage.bounds
            tiles = []
            for tile in mercantile.tiles(west, south, east, north, zooms=zoom):
                tile_bounds = bbox_to_box(mercantile.bounds(tile))
                if not coverage or coverage.intersects(tile_bounds):
                    tiles.append(tile)

            cache_tilesets.append({"year": year, "zoom": zoom, "tiles": tiles})

        cache_summary_df = pl.DataFrame(
            [{"Year": r["year"], "Zoom Level": r["zoom"], "Tiles": len(r["tiles"])} for r in cache_tilesets]
        )
        logger.info(f"{year} Cache Summary:\n{cache_summary_df}")

        if not dry_run:
            for cache_tileset in cache_tilesets:
                info_msg = (
                    f"start seeding year: {cache_tileset['year']}, zoom: {cache_tileset['zoom']}, tiles: "
                    f"{len(cache_tileset['tiles'])}"
                )
                logger.info(info_msg)
                _seed_tiles_by_year(cache_tileset["tiles"], cache_tileset["year"])
