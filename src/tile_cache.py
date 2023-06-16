from abc import ABC, abstractmethod
from io import BytesIO

import boto3
import mercantile
from PIL import Image


class TileCache(ABC):
    """Abstract class for tile cache."""

    @abstractmethod
    def get_tile(self, x: int, y: int, z: int, year: int) -> Image:
        """Get tile image from cache.

        Parameters
        ----------
        x: int
            x coordinate of tile
        y: int
            y coordinate of tile
        z: int
            zoom level of tile
        year: int
            naip year

        Returns
        -------
        Image
            image if tile found in cache, None if not

        """
        pass

    @abstractmethod
    def save_tile(
        self, x: int, y: int, z: int, year: int, image: Image, is_rescaled: bool = False
    ) -> None:
        """Save tile image to cache.

        Parameters
        ----------
        x: int
            x coordinate of tile
        y: int
            y coordinate of tile
        z: int
            zoom level of tile
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
    def contains_tile(self, x: int, y: int, z: int, year: int) -> bool:
        """Checks if tile exists in cache.

        Parameters
        ----------
        x: int
            x coordinate of tile
        y: int
            y coordinate of tile
        z: int
            zoom level of tile
        year: int
            naip year

        Returns
        -------
        bool
            True if tile exists, False if not exists

        """
        pass

    def get_tile_from_downscaling(self, x: int, y: int, z: int, year: int) -> Image:
        """Create tile via merging & downscaling tiles from the next zoom level.

        Parameters
        ----------
        x: int
            x coordinate of tile
        y: int
            y coordinate of tile
        z: int
            zoom level of tile
        year: int
            naip year

        Returns
        -------
        Image
            image if downscaling was possible, None otherwise
        """
        children_tile_images = []
        for child_tile in mercantile.children(x, y, z):
            chile_tile_image = self.get_tile(
                child_tile.x, child_tile.y, child_tile.z, year
            )
            if not chile_tile_image:
                return None
            children_tile_images.append(chile_tile_image)

        downscaled_tile_img = Image.new("RGB", (512, 512))
        downscaled_tile_img.paste(children_tile_images[0], (0, 0))
        downscaled_tile_img.paste(children_tile_images[1], (256, 0))
        downscaled_tile_img.paste(children_tile_images[3], (0, 256))
        downscaled_tile_img.paste(children_tile_images[2], (256, 256))
        return downscaled_tile_img.resize((256, 256))

    def get_tile_from_upscaling(self, x: int, y: int, z: int, year: int) -> Image:
        """Create tile via cropping & upscaling the tile from the previous zoom level.

        Parameters
        ----------
        x: int
            x coordinate of tile
        y: int
            y coordinate of tile
        z: int
            zoom level of tile
        year: int
            naip year

        Returns
        -------
        Image
            image if upscaling was possible, None otherwise
        """
        parent_tile = mercantile.parent(x, y, z)
        parent_tile_image = self.get_tile(
            parent_tile.x, parent_tile.y, parent_tile.z, year
        )
        if not parent_tile_image:
            # cant do anything without the parent tile...
            return None

        # determine what region in the parent tile that should be cropped
        quadrant = mercantile.children(parent_tile).index(mercantile.Tile(x, y, z))
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
        self, bucket: str, downscale_max_zoom: int = 11, upscale_min_zoom: int = 18
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
        self.s3 = boto3.resource("s3").Bucket(bucket)
        self.downscale_max_zoom = downscale_max_zoom
        self.upscale_min_zoom = upscale_min_zoom

    def _get_key(self, x: int, y: int, z: int, year: int):
        return f"{year}/{z}/{y}/{x}.jpg"

    def get_tile(self, x: int, y: int, z: int, year: int) -> Image:
        """Get tile image from cache.

        Parameters
        ----------
        x: int
            x coordinate of tile
        y: int
            y coordinate of tile
        z: int
            zoom level of tile
        year: int
            naip year

        Returns
        -------
        Image
            image if tile found in cache, None if not

        """
        if self.contains_tile(x, y, z, year):
            file_key = self._get_key(x, y, z, year)
            image_bytes = BytesIO(self.s3.Object(key=file_key).get()["Body"].read())
            return Image.open(image_bytes)

        rescaled_tile = None
        if z <= self.downscale_max_zoom:
            rescaled_tile = self.get_tile_from_downscaling(x, y, z, year)
        elif z >= self.upscale_min_zoom:
            rescaled_tile = self.get_tile_from_upscaling(x, y, z, year)
        if rescaled_tile:
            self.save_tile(x, y, z, year, rescaled_tile, is_rescaled=True)

        return rescaled_tile

    def save_tile(
        self, x: int, y: int, z: int, year: int, image: Image, is_rescaled: bool = False
    ) -> None:
        """Save tile image to cache.

        Parameters
        ----------
        x: int
            x coordinate of tile
        y: int
            y coordinate of tile
        z: int
            zoom level of tile
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
        file_key = self._get_key(x, y, z, year)
        image_bytes = BytesIO()
        image.save(image_bytes, format="JPEG")
        self.s3.Object(key=file_key).put(
            Body=image_bytes.getvalue(),
            Metadata={"is_rescaled": "true"} if is_rescaled else {},
        )

    def contains_tile(self, x: int, y: int, z: int, year: int) -> bool:
        """Checks if tile exists in cache.

        Parameters
        ----------
        x: int
            x coordinate of tile
        y: int
            y coordinate of tile
        z: int
            zoom level of tile
        year: int
            naip year

        Returns
        -------
        bool
            True if tile exists, False if not exists

        """
        file_key = self._get_key(x, y, z, year)
        return len(list(self.s3.objects.filter(Prefix=file_key))) > 0
