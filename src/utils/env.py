import os

from src.utils import logger
from src.utils.tile_cache import S3TileCache, TileCache


class TileServerConfig:
    """A class for tile server configuration options."""

    def __init__(
        self,
        image_format: str,
        max_zoom: int,
        min_zoom: int,
        downscale_max_zoom: int,
        upscale_min_zoom: int,
        rescaling_enabled: bool,
        tile_cache_bucket: str,
    ):
        """Initialize TileServerConfig with validation."""
        assert min_zoom < max_zoom
        assert downscale_max_zoom < upscale_min_zoom

        self.image_format = image_format
        self.max_zoom = max_zoom
        self.min_zoom = min_zoom
        self.downscale_max_zoom = downscale_max_zoom
        self.upscale_min_zoom = upscale_min_zoom
        self.rescaling_enabled = rescaling_enabled
        self.tile_cache_bucket = tile_cache_bucket

    @staticmethod
    def from_env():
        """Create an instance of TileServerConfig from environment variables."""
        tile_server_config = TileServerConfig(
            image_format=os.getenv("IMAGE_FORMAT"),
            max_zoom=int(os.getenv("MAX_ZOOM")),
            min_zoom=int(os.getenv("MIN_ZOOM")),
            downscale_max_zoom=int(os.getenv("DOWNSCALE_MAX_ZOOM")),
            upscale_min_zoom=int(os.getenv("UPSCALE_MIN_ZOOM")),
            rescaling_enabled=bool(os.getenv("RESCALING_ENABLED")),
            tile_cache_bucket=os.getenv("TILE_CACHE_BUCKET"),
        )
        return tile_server_config

    @property
    def tile_cache(self) -> TileCache | None:
        """Instantiate TileCache based on config."""
        if not self.tile_cache_bucket:
            logger.warning("TILE_CACHE_S3_BUCKET env var missing - no tilecache")
            return None
        try:
            tile_cache = S3TileCache(
                bucket=self.tile_cache_bucket,
                downscale_max_zoom=self.downscale_max_zoom,
                upscale_min_zoom=self.upscale_min_zoom,
                rescaling_enabled=self.rescaling_enabled,
            )
            logger.info(f"Successfully created S3TileCache backed by bucket: {self.tile_cache_bucket}")
            return tile_cache
        except Exception as e:
            logger.error(f"error creating S3TileCache backed by bucket {self.tile_cache_bucket}: {e}")
            return None
