import click

from src.admin_cli.commands import cache


@click.group(help="CLI tool to perform admin_cli actions")
def cli():
    """Admin CLI."""
    pass


cli.add_command(cache.seed, "seed-cache")
