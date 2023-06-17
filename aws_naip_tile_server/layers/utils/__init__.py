import logging

# https://stackoverflow.com/questions/37703609/using-python-logging-with-aws-lambda
# https://stackoverflow.com/questions/71119621/python-logging-in-aws-lambda
logging.basicConfig(
    format="[%(levelname)s] | %(asctime)s | %(message)s | %(module)s:%(funcName)s:%(lineno)d ",
    level=logging.INFO,
    force=True,
    datefmt="%b-%d-%y %H:%M:%S",
)
logger = logging.getLogger()
