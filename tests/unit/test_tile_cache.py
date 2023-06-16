import uuid

import boto3
import mercantile
import numpy as np
import pytest
from PIL import Image

from src.tile_cache import S3TileCache


@pytest.fixture(scope="module")
def s3_tile_cache():
    """Return S3TileCache instance backed by bucket created for this run of tests."""
    # create a bucket specifically for testing
    test_bucket_name = f"aws-naip-tile-server-test-{uuid.uuid4()}"
    s3 = boto3.resource("s3")
    s3.create_bucket(
        Bucket=test_bucket_name,
        CreateBucketConfiguration={"LocationConstraint": "us-west-2"},
    )

    # yield S3TileCache to be used in tests
    yield S3TileCache(test_bucket_name)

    # delete test bucket.  bucket needs to be empty to do
    bucket = s3.Bucket(test_bucket_name)
    bucket.objects.all().delete()
    bucket.delete()


@pytest.fixture()
def tile_image():
    """Return random tile sized image."""
    imarray = np.random.rand(256, 256, 3) * 255
    return Image.fromarray(imarray.astype("uint8")).convert("RGB")


def test_s3_save_tile(s3_tile_cache, tile_image):
    """Test confirms saving tile works."""
    s3_tile_cache.save_tile(1, 1, 1, 2099, tile_image)
    assert s3_tile_cache.contains_tile(1, 1, 1, 2099)


def test_s3_get_existing_tile(s3_tile_cache):
    """Test confirms getting cached tile returns image."""
    tile_image = s3_tile_cache.get_tile(1, 1, 1, 2099)
    assert tile_image is not None


def test_s3_get_nonexisting_tile(s3_tile_cache):
    """Test confirms getting non-cached tile returns None."""
    tile_image = s3_tile_cache.get_tile(1, 1, 5, 2099)
    assert tile_image is None


def test_s3_contain_existing_tile(s3_tile_cache):
    """Test confirms checking existence of cached tile returns True."""
    assert s3_tile_cache.contains_tile(1, 1, 1, 2099)


def test_s3_contain_nonexisting_tile(s3_tile_cache):
    """Test confirms checking existence of non-cached tile returns False."""
    assert not s3_tile_cache.contains_tile(1, 1, 5, 2099)


def test_s3_downscale_tile(s3_tile_cache, tile_image):
    """Test confirms that downscaling will return Image if children tiles in cache."""
    tile = mercantile.Tile(10, 10, 10)
    for children_tile in mercantile.children(tile):
        s3_tile_cache.save_tile(
            children_tile.x, children_tile.y, children_tile.z, 2099, tile_image
        )
    tile_image = s3_tile_cache.get_tile_from_downscaling(tile.x, tile.y, tile.z, 2099)
    assert tile_image is not None


def test_s3_downscale_tile_null(s3_tile_cache, tile_image):
    """Test confirms that downscaling will return None if children tiles don't exist."""
    tile = mercantile.Tile(8, 8, 8)
    tile_image = s3_tile_cache.get_tile_from_downscaling(tile.x, tile.y, tile.z, 2099)
    assert tile_image is None


def test_s3_upscale_tile(s3_tile_cache, tile_image):
    """Test confirms that upscaling will return Image if parent tile in cache."""
    tile = mercantile.Tile(11, 11, 11)
    parent_tile = mercantile.parent(tile)
    s3_tile_cache.save_tile(
        parent_tile.x, parent_tile.y, parent_tile.z, 2099, tile_image
    )
    tile_image = s3_tile_cache.get_tile_from_upscaling(tile.x, tile.y, tile.z, 2099)
    assert tile_image is not None


def test_s3_upscale_tile_null(s3_tile_cache, tile_image):
    """Test confirms that upscaling will return None if parent tile not in cache."""
    tile = mercantile.Tile(12, 12, 12)
    tile_image = s3_tile_cache.get_tile_from_upscaling(tile.x, tile.y, tile.z, 2099)
    assert tile_image is None


def test_s3_save_rescaled_tile(s3_tile_cache, tile_image):
    """Test confirms saving tile with is_rescaled metadata works."""
    s3_tile_cache.save_tile(1, 2, 3, 2099, tile_image, is_rescaled=True)
    assert s3_tile_cache.contains_tile(1, 2, 3, 2099)
