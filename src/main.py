import asyncio
import sys

from config_common import FullConfiguration
from youwol_stories_backend import get_router, init_resources
from youwol_utils.servers.fast_api import serve, FastApiApp, FastApiRouter


async def select_configuration() -> FullConfiguration:

    if sys.argv[1] == "local":
        from config_local import get_configuration as config
        return await config()

    if sys.argv[1] == "hybrid":
        from config_hybrid import get_configuration as config
        return await config()

    if sys.argv[1] == "prod":
        from config_prod import get_configuration as config
        return await config()

    raise RuntimeError(f"The configuration {sys.argv[1]} is not known")

selected_config: FullConfiguration = asyncio.get_event_loop().run_until_complete(select_configuration())


async def on_before_startup():
    await init_resources(selected_config.service)


serve(
    FastApiApp(
        title="stories-backend",
        description="Backend side of the stories service",
        root_path=selected_config.server.root_path,
        base_path=selected_config.server.base_path,
        root_router=FastApiRouter(
            router=get_router(selected_config.service)
        ),
        middlewares=selected_config.server.middlewares,
        ctx_logger=selected_config.service.ctx_logger,
        http_port=selected_config.server.http_port,
        on_before_startup=on_before_startup
    )
)
