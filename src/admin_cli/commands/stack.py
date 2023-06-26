import json
import os

import click
from rich import print_json
from sh import sam

from src.utils import ROOT_DIR
from src.utils.stack_info import get_is_stack_deployed, get_stack_description


@click.group
def stack():
    """AWS CloudFormation related commands."""
    pass


@stack.command()
def status():
    """Display basic info about deployed aws-naip-tile-server AWS CloudFormation stack."""
    if get_is_stack_deployed():
        stack_description = get_stack_description()
        for prop in list(stack_description.keys()):
            if prop not in ["StackId", "StackName", "CreationTime", "LastUpdatedTime", "Outputs"]:
                stack_description.pop(prop)

        print_json(json.dumps(stack_description, indent=4, default=str))
    else:
        click.echo("aws-naip-tile-server AWS CloudFormation stack does not appear to be deployed")


@stack.command()
def deploy():
    """Deploy aws-naip-tile-server AWS CloudFormation stack."""
    sam("build", _cwd=ROOT_DIR)

    parameter_overrides = []
    env_file = os.path.join(ROOT_DIR, ".env")
    if os.path.exists(env_file):
        with open(env_file, "r") as fid:
            for var in fid.readlines():
                snake_case_name, val = var.strip().split("=")
                camel_case_name = "".join(word.title() for word in snake_case_name.lower().split("_"))
                parameter_overrides.append(f"{camel_case_name}={val}")

    if parameter_overrides:
        formatted_parameter_overrides = " ".join(parameter_overrides)
        click.echo(f"--parameter-overrides: {formatted_parameter_overrides}")
        sam("deploy", "--parameter-overrides", formatted_parameter_overrides, "--no-confirm-changeset")
    else:
        sam("deploy", "--no-confirm-changeset")


@stack.command()
def delete():
    """Delete aws-naip-tile-server AWS CloudFormation stack."""
    if get_is_stack_deployed():
        sam("delete", "--no-prompts", _cwd=ROOT_DIR)
    else:
        click.echo("aws-naip-tile-server AWS CloudFormation stack does not appear to be deployed")
