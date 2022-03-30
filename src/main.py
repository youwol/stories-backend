import asyncio
from configurations import get_configuration, Configuration
from youwol_stories_backend import router, init_resources, Dependencies
from youwol_utils.servers.fast_api import serve, FastApiApp, FastApiRouter, FastApiMiddleware

configuration: Configuration = asyncio.get_event_loop().run_until_complete(get_configuration())
asyncio.get_event_loop().run_until_complete(init_resources(configuration))

Dependencies.get_configuration = get_configuration

serve(
    FastApiApp(
        title="stories-backend",
        description="Backend side of the stories service",
        root_path=configuration.root_path,
        base_path=configuration.base_path,
        root_router=FastApiRouter(
            router=router
        ),
        middlewares=[FastApiMiddleware(
            configuration.auth_middleware,
            configuration.auth_middleware_args
        )],
        ctx_logger=configuration.ctx_logger,
        http_port=configuration.http_port
    )
)
