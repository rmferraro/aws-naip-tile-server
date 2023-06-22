import click

from src.admin.commands import cache


@click.group(help="CLI tool to perform admin_cli actions")
def cli():
    """Admin CLI."""
    pass


cli.add_command(cache.seed, "seed-cache")

if __name__ == "__main__":
    cli()
