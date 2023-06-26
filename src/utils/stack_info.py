import os
from functools import lru_cache
from pathlib import Path

import boto3
import tomli


@lru_cache(maxsize=1)
def get_stack_description():
    """Get info about the deployed CloudFormation."""
    stack_name = get_stack_name()
    client = boto3.client("cloudformation")
    try:
        response = client.describe_stacks(StackName=stack_name)
        return response["Stacks"][0]

    except Exception as e:
        raise ValueError(
            f"Cannot find stack {stack_name} \n" f'Please make sure a stack with the name "{stack_name}" exists'
        ) from e


def get_stack_name() -> str:
    """Get the stack name per samconfig.toml.

    Returns
    -------
    str
    """
    with open(os.path.join(Path(__file__).parent.parent.parent, "samconfig.toml"), mode="rb") as fp:
        config = tomli.load(fp)
        stack_name = config["default"]["global"]["parameters"]["stack_name"]
    return stack_name


def get_stack_output_value(output_key: str) -> str:
    """Get Stack output value for a given key.

    Parameters
    ----------
    output_key: str
        stack output key

    Returns
    -------
    str:
        key's value if found,
    """
    stack_outputs = get_stack_description()["Outputs"]
    api_outputs = [output for output in stack_outputs if output["OutputKey"] == output_key]

    if not api_outputs:
        raise KeyError(f"{output_key} not found in stack")

    return api_outputs[0]["OutputValue"]


def get_is_stack_deployed() -> bool:
    """Crude check to determine if AWS Stack has been deployed.

    Returns
    -------
    bool
        True if stack seems to have been deployed successfully, False otherwise

    """
    try:
        get_stack_description()
        return True
    except Exception:
        return False


def get_is_cache_enabled() -> bool:
    """Crude check to determine if tile caching is enabled in current stack configuration.

    CloudFormation parameters are not allowed to have null/empty value - so its possible some dummy values is used
    for NAIPTileCacheS3Bucket Parameter (i.e. S3 bucket is non-existent).  It's also possible that a once valid bucket
    is no longer valid (e.g. deleted).  This crude check does 2 things:
        1.  Checks if the NAIPTileCacheS3Bucket output from the last deployment exists
        2.  If so, checks that the NAIPLambdaRole can put/get objects

    Returns
    -------
    bool
        True if cacheing appears to be enabled, False otherwise
    """
    cache_s3_bucket_name = get_stack_output_value("TileCacheBucket")
    cache_s3_bucket = boto3.resource("s3").Bucket(cache_s3_bucket_name)
    if not cache_s3_bucket.creation_date:
        # bucket doesnt exist
        return False

    # lets confirm the can access the bucket
    # Run the policy simulation for the basic s3 operations
    iam = boto3.client("iam")
    naip_lambda_role_arn = get_stack_output_value("NAIPLambdaIamRole")
    results = iam.simulate_principal_policy(
        PolicySourceArn=naip_lambda_role_arn,
        ResourceArns=["arn:aws:s3:::%s/*" % cache_s3_bucket_name],
        ActionNames=["s3:PutObject", "s3:GetObject"],
    )
    for result in results["EvaluationResults"]:
        if result["EvalDecision"] != "allowed":
            return False
    return True
