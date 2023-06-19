import click

from aws_naip_tile_server.admin.commands import cache


@click.group(help="CLI tool to perform admin actions")
def cli():
    """Admin CLI."""
    pass


cli.add_command(cache.seed, "seed-cache")

if __name__ == "__main__":
    cli()
