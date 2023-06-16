from abc import ABC, abstractmethod
from io import BytesIO

import boto3
from botocore.exceptions import ClientError
from PIL import Image


class TileCache(ABC):
    @abstractmethod
    def get_tile(self, x: int, y: int, z: int, year: int) -> Image:
        pass

    @abstractmethod
    def save_tile(self, x: int, y: int, z: int, year: int, image: Image) -> None:
        pass

    @abstractmethod
    def contains_tile(self, x: int, y: int, z: int, year: int) -> bool:
        pass


class S3TileCache(TileCache):
    def __init__(self, bucket: str):
        """Initialize S3TileCache instance.

        Parameters
        ----------
        bucket: str
          s3 bucket name to be used as tile cache
        """
        self.s3 = boto3.resource("s3").Bucket(bucket)

    def _get_key(self, x: int, y: int, z: int, year: int):
        return f"{year}/{z}/{y}/{x}.jpg"

    def get_tile(self, x: int, y: int, z: int, year: int) -> Image:
        try:
            file_key = self._get_key(x, y, z, year)
            image_bytes = BytesIO(self.s3.Object(key=file_key).get()["Body"].read())
            return Image.open(image_bytes)
        except ClientError as ex:
            if ex.response["Error"]["Code"] == "NoSuchKey":
                return None
            else:
                raise

    def save_tile(self, x: int, y: int, z: int, year: int, image: Image) -> None:
        file_key = self._get_key(x, y, z, year)
        image_bytes = BytesIO()
        image.save(image_bytes, format="JPEG")
        self.s3.Object(key=file_key).put(Body=image_bytes.getvalue())

    def contains_tile(self, x: int, y: int, z: int, year: int) -> bool:
        file_key = self._get_key(x, y, z, year)
        return len(list(self.s3.objects.filter(Prefix=file_key))) > 0
