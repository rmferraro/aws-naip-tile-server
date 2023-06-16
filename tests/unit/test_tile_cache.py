import uuid

import boto3
import numpy as np
import pytest
from PIL import Image

from src.tile_cache import S3TileCache


@pytest.fixture(scope="module")
def s3_tile_cache():
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


def test_s3_save_tile(s3_tile_cache):
    imarray = np.random.rand(100, 100, 3) * 255
    tile_image = Image.fromarray(imarray.astype("uint8")).convert("RGB")
    s3_tile_cache.save_tile(1, 1, 1, 2099, tile_image)
    assert s3_tile_cache.contains_tile(1, 1, 1, 2099)


def test_s3_get_existing_tile(s3_tile_cache):
    tile_image = s3_tile_cache.get_tile(1, 1, 1, 2099)
    assert tile_image is not None


def test_s3_get_nonexisting_tile(s3_tile_cache):
    tile_image = s3_tile_cache.get_tile(1, 1, 5, 2099)
    assert tile_image is None


def test_s3_contain_existing_tile(s3_tile_cache):
    assert s3_tile_cache.contains_tile(1, 1, 1, 2099)


def test_s3_contain_nonexisting_tile(s3_tile_cache):
    assert not s3_tile_cache.contains_tile(1, 1, 5, 2099)
