import click

from src.admin_cli.commands.cache import cache
from src.admin_cli.commands.stack import stack


@click.group(help="CLI tool to perform admin_cli actions")
def cli():
    """Admin CLI."""
    pass


cli.add_command(cache)
cli.add_command(stack)
