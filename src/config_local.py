from pathlib import Path

from config_common import get_py_youwol_env, on_before_startup

from youwol_stories_backend import Constants, Configuration

from youwol_utils import LocalStorageClient, LocalDocDbClient
from youwol_utils.clients.assets_gateway.assets_gateway import AssetsGatewayClient
from youwol_utils.context import ConsoleContextLogger
from youwol_utils.http_clients.stories_backend import STORIES_TABLE, DOCUMENTS_TABLE, DOCUMENTS_TABLE_BY_ID
from youwol_utils.middlewares.authentication_local import AuthLocalMiddleware
from youwol_utils.servers.fast_api import FastApiMiddleware, ServerOptions, AppConfiguration


async def get_configuration():

    env = await get_py_youwol_env()
    databases_path = Path(env['pathsBook']['databases'])

    async def _on_before_startup():
        await on_before_startup(service_config)

    service_config = Configuration(
        storage=LocalStorageClient(
            root_path=databases_path / 'storage',
            bucket_name=Constants.namespace
        ),
        doc_db_stories=LocalDocDbClient(
            root_path=databases_path / 'docdb',
            keyspace_name=Constants.namespace,
            table_body=STORIES_TABLE
        ),
        doc_db_documents=LocalDocDbClient(
            root_path=databases_path / 'docdb',
            keyspace_name=Constants.namespace,
            table_body=DOCUMENTS_TABLE,
            secondary_indexes=[DOCUMENTS_TABLE_BY_ID]
        ),
        assets_gtw_client=AssetsGatewayClient(url_base=f"http://localhost:{env['httpPort']}/api/assets-gateway")
    )
    server_options = ServerOptions(
        root_path="",
        http_port=env['portsBook']['stories-backend'],
        base_path="",
        middlewares=[FastApiMiddleware(AuthLocalMiddleware, {})],
        on_before_startup=_on_before_startup,
        ctx_logger=ConsoleContextLogger()
    )
    return AppConfiguration(
        server=server_options,
        service=service_config
    )
