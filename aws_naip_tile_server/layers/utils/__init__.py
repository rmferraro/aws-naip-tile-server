import logging

import boto3

# https://stackoverflow.com/questions/37703609/using-python-logging-with-aws-lambda
# https://stackoverflow.com/questions/71119621/python-logging-in-aws-lambda
boto3.set_stream_logger(name="botocore.credentials", level=logging.ERROR)
logging.basicConfig(
    format="%(levelname)s | %(asctime)s | [%(module)s:%(funcName)s:%(lineno)d] %(message)s",
    level=logging.INFO,
    force=True,
    datefmt="%b-%d-%y %H:%M:%S",
)
logger = logging.getLogger()
