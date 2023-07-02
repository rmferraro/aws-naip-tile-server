import os.path
from dataclasses import asdict, dataclass

import click
from sh import npm

from src.admin_cli.commands import check_system_dependencies
from src.utils import ROOT_DIR
from src.utils.stack_info import get_is_stack_deployed, get_stack_output_value


@dataclass
class InspectorUISettings:
    """A class to help manage inspector-ui settings."""

    VITE_NAIP_TILE_API: str
    VITE_MIN_ZOOM: int
    VITE_MAX_ZOOM: int
    VITE_INITIAL_VIEW_ZOOM: int = 5
    VITE_INITIAL_VIEW_CENTER: str = "-95.7129,37.0902"

    @staticmethod
    def from_env_file(env_file: str):
        """Instantiates instance from env file."""
        config = {}
        with open(env_file, "r") as fid:
            for ln in fid.readlines():
                if ln.startswith("#"):
                    continue
                k, v = ln.strip().split("=")
                config[k] = v
        return InspectorUISettings(**config)

    def to_dict(self) -> dict:
        """Converts instance to dictionary."""
        return asdict(self)

    def to_env_file(self, env_file: str):
        """Writes instance to env file."""
        with open(env_file, "w") as fid:
            for k, v in self.to_dict().items():
                fid.write(f"{k}={v}\n")


def update_inspector_ui_settings() -> None:
    """Updates .env file in inspector-ui based on current state of aws-naip-tile-server AWS CloudFormation stack.

    If an .env file does not exist, this function will create one with default values for some properties not obtained
    from stack (VITE_NAIP_INITIAL_VIEW_ZOOM, VITE_NAIP_INITIAL_VIEW_CENTER).  If an .env file already exists, only
    stack derived properties are updated (VITE_NAIP_TILE_API, VITE_NAIP_MIN_ZOOM, VITE_NAIP_MAX_ZOOM).

    Returns
    -------
    None
    """
    naip_tile_api = get_stack_output_value("NAIPTileApi")
    min_zoom = int(get_stack_output_value("MinZoom"))
    max_zoom = int(get_stack_output_value("MaxZoom"))

    inspector_ui_env = os.path.join(ROOT_DIR, "inspector-ui", ".env")
    if os.path.exists(inspector_ui_env):
        settings = InspectorUISettings.from_env_file(inspector_ui_env)
        settings.VITE_NAIP_TILE_API = naip_tile_api
        settings.VITE_MIN_ZOOM = min_zoom
        settings.VITE_MAX_ZOOM = max_zoom
    else:
        settings = InspectorUISettings(VITE_NAIP_TILE_API=naip_tile_api, VITE_MIN_ZOOM=min_zoom, VITE_MAX_ZOOM=max_zoom)

    settings.to_env_file(inspector_ui_env)


@click.group
def inspector_ui():
    """Inspector UI related commands."""
    pass


@inspector_ui.command()
@check_system_dependencies(["npm"])
def start():
    """Start the Inspector UI in debug mode."""
    if get_is_stack_deployed():
        update_inspector_ui_settings()
        inspector_ui_root = os.path.join(ROOT_DIR, "inspector-ui")
        npm("install", _cwd=inspector_ui_root)
        npm("run", "dev", _cwd=inspector_ui_root)
    else:
        click.echo("aws-naip-tile-server AWS CloudFormation stack does not appear to be deployed")
