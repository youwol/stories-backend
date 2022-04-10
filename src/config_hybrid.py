from config_common import get_py_youwol_env, on_before_startup, cache_prefix

from youwol_stories_backend import Constants, Configuration
from youwol_utils import StorageClient, DocDbClient, AuthClient, LocalCacheClient

from youwol_utils.clients.assets_gateway.assets_gateway import AssetsGatewayClient
from youwol_utils.context import ConsoleContextLogger
from youwol_utils.http_clients.stories_backend import STORIES_TABLE, DOCUMENTS_TABLE, DOCUMENTS_TABLE_BY_ID
from youwol_utils.middlewares import Middleware
from youwol_utils.servers.fast_api import FastApiMiddleware, ServerOptions, AppConfiguration


def get_auth_token(env, url_cluster: str):
    return next(t['value'] for t in env['tokensCache'] if t['dependencies']['host'] == url_cluster)


async def get_configuration():

    env = await get_py_youwol_env()
    openid_host = env['k8sInstance']['openIdConnect']['host']
    url_cluster = env['k8sInstance']['host']

    service_config = Configuration(
        storage=StorageClient(
            url_base=f"https://{url_cluster}/api/storage",
            bucket_name=Constants.namespace
        ),
        doc_db_stories=DocDbClient(
            url_base=f"https://{url_cluster}/api/docdb",
            keyspace_name=Constants.namespace,
            table_body=STORIES_TABLE,
            replication_factor=2
        ),
        doc_db_documents=DocDbClient(
            url_base=f"https://{url_cluster}/api/docdb",
            keyspace_name=Constants.namespace,
            table_body=DOCUMENTS_TABLE,
            secondary_indexes=[DOCUMENTS_TABLE_BY_ID],
            replication_factor=2
        ),
        assets_gtw_client=AssetsGatewayClient(url_base=f"http://localhost:{env['httpPort']}/api/assets-gateway"),
        admin_headers={'authorization': f'Bearer {get_auth_token(env, url_cluster)}'}
    )

    async def _on_before_startup():
        await on_before_startup(service_config)

    server_options = ServerOptions(
        root_path="",
        http_port=env['portsBook']['stories-backend'],
        base_path="",
        middlewares=[FastApiMiddleware(Middleware, {
            "auth_client": AuthClient(url_base=f"https://{openid_host}/auth"),
            "cache_client": LocalCacheClient(prefix=cache_prefix)
        })],
        on_before_startup=_on_before_startup,
        ctx_logger=ConsoleContextLogger()
    )
    return AppConfiguration(
        server=server_options,
        service=service_config
    )
