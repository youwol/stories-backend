import sys
from dataclasses import dataclass
from typing import List

from youwol_stories_backend import Configuration as ServiceConfiguration
from youwol_utils.servers.fast_api import FastApiMiddleware
from youwol_utils.utils_paths import get_running_py_youwol_env


@dataclass(frozen=True)
class ServerOptions:
    root_path: str
    http_port: int
    base_path: str
    middlewares: List[FastApiMiddleware]


@dataclass(frozen=True)
class FullConfiguration:
    server: ServerOptions
    service: ServiceConfiguration


async def get_py_youwol_env():
    py_youwol_port = sys.argv[2]
    if not py_youwol_port:
        raise RuntimeError("The configuration requires py-youwol to run on port provided as command line option")

    return await get_running_py_youwol_env(py_youwol_port)
