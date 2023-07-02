import functools
from shutil import which

import click


def check_system_dependencies(dependencies: list[str]):
    """A decorator that checks if programs/dependencies are on PATH and marked as executable."""

    def actual_decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for dependency in dependencies:
                if which(dependency) is None:
                    raise click.ClickException(f"Missing system dependency: {dependency}")
            return func(*args, **kwargs)

        return wrapper

    return actual_decorator
