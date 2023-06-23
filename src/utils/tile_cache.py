from abc import ABC, abstractmethod
from io import BytesIO

import boto3
import mercantile
from PIL import Image


class TileCache(ABC):
    """Base class for tile cache."""

    def __init__(self, rescaling_enabled: bool = True, downscale_max_zoom: int = 11, upscale_min_zoom: int = 18):
        """Initialize TileCache.

        Parameters
        ----------
        rescaling_enabled: bool
            Create missing tiles by rescaling cached tiles
        downscale_max_zoom: int
            Max zoom level where attempts to create missing tile from downscaling will kick in
        upscale_min_zoom: int
            Min zoom level where attempts to create missing tile from upscaling will kick in
        """
        self._rescaling_enabled = rescaling_enabled
        self._downscale_max_zoom = downscale_max_zoom
        self._upscale_min_zoom = upscale_min_zoom

    @property
    def downscale_max_zoom(self) -> int:
        """Max zoom level where attempts to create missing tile from downscaling will kick in."""
        return self._downscale_max_zoom

    @property
    def rescaling_enabled(self) -> bool:
        """Create missing tiles by rescaling cached tiles."""
        return self._rescaling_enabled

    @property
    def upscale_min_zoom(self) -> int:
        """Min zoom level where attempts to create missing tile from upscaling will kick in."""
        return self._upscale_min_zoom

    @abstractmethod
    def get_tile_image(self, tile: mercantile.Tile, year: int) -> Image:
        """Get tile image from cache.

        Parameters
        ----------
        tile: mercantile.Tile
            mercator slippy-map tile
        year: int
            naip year

        Returns
        -------
        Image
            image if tile found in cache, None if not

        """
        pass

    @abstractmethod
    def save_tile_image(self, tile: mercantile.Tile, year: int, image: Image, is_rescaled: bool = False) -> None:
        """Save tile image to cache.

        Parameters
        ----------
        tile: mercantile.Tile
            mercator slippy-map tile
        year: int
            naip year
        image: Image
            tile image
        is_rescaled: bool
            boolean to indicate if tile was created from rescaling other tiles

        Returns
        -------
            None
        """
        pass

    @abstractmethod
    def contains_tile_image(self, tile: mercantile.Tile, year: int) -> bool:
        """Checks if tile image exists in cache.

        Parameters
        ----------
        tile: mercantile.Tile
            mercator slippy-map tile
        year: int
            naip year

        Returns
        -------
        bool
            True if tile exists, False if not exists

        """
        pass

    @abstractmethod
    def get_missing_tile_images(self, tiles: list[mercantile.Tile], year: int) -> list[mercantile.Tile]:
        """Efficiently find what tile images are missing in this cache from a large/deep list of tiles.

        Parameters
        ----------
        tiles: list[mercantile.Tile]
            list of tiles to check
        year: int
            naip year

        Returns
        -------
        list[mercantile.Tile]
            subset of tiles not found in cache

        """
        pass

    @abstractmethod
    def handle_null_tile_image(self, tile: mercantile.Tile, year: int) -> None:
        """Handle null tile image.  Will vary based on TileCache implementation.

        Parameters
        ----------
        tile: mercantile.Tile
            mercator slippy-map tile
        year: int
            naip year

        Returns
        -------
        None

        """
        pass

    def get_tile_image_from_downscaling(self, tile: mercantile.Tile, year: int) -> Image:
        """Create tile image via merging & downscaling tiles from the next zoom level.

        Parameters
        ----------
        tile: mercantile.Tile
            mercator slippy-map tile
        year: int
            naip year

        Returns
        -------
        Image
            image if downscaling was possible, None otherwise
        """
        children_tile_images = []
        for child_tile in mercantile.children(tile):
            chile_tile_image = self.get_tile_image(child_tile, year)
            if not chile_tile_image:
                return None
            children_tile_images.append(chile_tile_image)

        downscaled_tile_img = Image.new("RGBA", (512, 512))
        downscaled_tile_img.paste(children_tile_images[0], (0, 0))
        downscaled_tile_img.paste(children_tile_images[1], (256, 0))
        downscaled_tile_img.paste(children_tile_images[3], (0, 256))
        downscaled_tile_img.paste(children_tile_images[2], (256, 256))
        return downscaled_tile_img.resize((256, 256))

    def get_tile_image_from_upscaling(self, tile: mercantile.Tile, year: int) -> Image:
        """Create tile image via cropping & upscaling the tile from the previous zoom level.

        Parameters
        ----------
        tile: mercantile.Tile
            mercator slippy-map tile
        year: int
            naip year

        Returns
        -------
        Image
            image if upscaling was possible, None otherwise
        """
        parent_tile = mercantile.parent(tile)
        parent_tile_image = self.get_tile_image(parent_tile, year)
        if not parent_tile_image:
            # cant do anything without the parent tile...
            return None

        # determine what region in the parent tile that should be cropped
        quadrant = mercantile.children(parent_tile).index(tile)
        if quadrant == 0:
            crop_region = (0, 0, 128, 128)
        elif quadrant == 1:
            crop_region = (128, 0, 256, 128)
        elif quadrant == 3:
            crop_region = (0, 128, 128, 256)
        else:
            crop_region = (128, 128, 256, 256)

        # crop region from parent tile and resize to standard tile size
        return parent_tile_image.crop(crop_region).resize((256, 256))


class S3TileCache(TileCache):
    """S3 implementation of TileCache."""

    def __init__(
        self, bucket: str, rescaling_enabled: bool = True, downscale_max_zoom: int = 11, upscale_min_zoom: int = 18
    ):
        """Initialize S3TileCache instance.

        Parameters
        ----------
        bucket: str
            S3 bucket name to be used as tile cache
        downscale_max_zoom: int
            max zoom level where attempts to create missing tile from downscaling will
            kick-in.
        upscale_min_zoom: int
            min zoom level where attempts to create missing tile from upscaling will
            kick-in.
        """
        super(S3TileCache, self).__init__(rescaling_enabled, downscale_max_zoom, upscale_min_zoom)
        self.s3 = boto3.resource("s3").Bucket(bucket)
        if not self.s3.creation_date:
            raise ValueError(f"S3 Bucket: {bucket} not found")

    def _get_key(self, tile: mercantile.Tile, year: int):
        return f"{year}/{tile.z}/{tile.y}/{tile.x}.png"

    def get_tile_image(self, tile: mercantile.Tile, year: int) -> Image:
        """Get tile image from cache.

        Parameters
        ----------
        tile: mercantile.Tile
            mercator slippy-map tile
        year: int
            naip year

        Returns
        -------
        Image
            image if tile found in cache, None if not

        """
        if self.contains_tile_image(tile, year):
            file_key = self._get_key(tile, year)
            image_bytes = BytesIO(self.s3.Object(key=file_key).get()["Body"].read())
            return Image.open(image_bytes)

        rescaled_tile = None
        if tile.z <= self.downscale_max_zoom:
            rescaled_tile = self.get_tile_image_from_downscaling(tile, year)
        elif tile.z >= self.upscale_min_zoom:
            rescaled_tile = self.get_tile_image_from_upscaling(tile, year)
        if rescaled_tile:
            self.save_tile_image(tile, year, rescaled_tile, is_rescaled=True)

        return rescaled_tile

    def handle_null_tile_image(self, tile: mercantile.Tile, year: int) -> None:
        """Handle null tile image.

        To maximize efficacy of rescaling and prevent redundant,expensive calls to generate tiles where NAIP imagery
        is not available, just save blank tiles
        Parameters
        ----------
        tile: mercantile.Tile
            mercator slippy-map tile
        year: int
            naip year

        Returns
        -------
        None

        """
        blank_tile = Image.new("RGBA", (256, 256), (255, 0, 0, 0))
        self.save_tile_image(tile, year, blank_tile)

    def save_tile_image(self, tile: mercantile.Tile, year: int, image: Image, is_rescaled: bool = False) -> None:
        """Save tile image to cache.

        Parameters
        ----------
        tile: mercantile.Tile
            mercator slippy-map tile
        year: int
            naip year
        image: Image
            tile image
        is_rescaled: bool
            boolean to indicate if tile was created from rescaling other tiles

        Returns
        -------
            None
        """
        file_key = self._get_key(tile, year)
        image_bytes = BytesIO()
        image.save(image_bytes, format="PNG")
        self.s3.Object(key=file_key).put(
            Body=image_bytes.getvalue(),
            Metadata={"is_rescaled": "true"} if is_rescaled else {},
        )

    def contains_tile_image(self, tile: mercantile.Tile, year: int) -> bool:
        """Checks if tile image exists in cache.

        Parameters
        ----------
        tile: mercantile.Tile
            mercator slippy-map tile
        year: int
            naip year

        Returns
        -------
        bool
            True if tile exists, False if not exists

        """
        file_key = self._get_key(tile, year)
        return len(list(self.s3.objects.filter(Prefix=file_key))) > 0

    def get_missing_tile_images(self, tiles: list[mercantile.Tile], year: int) -> list[mercantile.Tile]:
        """Efficiently find what tile images are missing in this cache from a large/deep list of tiles.

        Parameters
        ----------
        tiles: list[mercantile.Tile]
            list of tiles to check
        year: int
            naip year

        Returns
        -------
        list[mercantile.Tile]
            subset of tiles not found in cache

        """
        inventory = set()
        for obj in self.s3.objects.filter(Prefix=(str(year))):
            if obj.key.endswith(".jpg"):
                _, z, y, x = obj.key.split("/")
                inventory.add((int(x.split(".")[0]), int(y), int(z)))

        return list(filter(lambda tile: (tile.x, tile.y, tile.z) not in inventory, tiles))
