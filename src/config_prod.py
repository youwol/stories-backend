import os

from config_common import on_before_startup, cache_prefix

from youwol_stories_backend import Configuration, Constants

from youwol_utils import StorageClient, DocDbClient, AuthClient, CacheClient, get_headers_auth_admin_from_env
from youwol_utils.clients.assets_gateway.assets_gateway import AssetsGatewayClient
from youwol_utils.context import DeployedContextLogger
from youwol_utils.http_clients.stories_backend import STORIES_TABLE, DOCUMENTS_TABLE, DOCUMENTS_TABLE_BY_ID
from youwol_utils.middlewares import Middleware
from youwol_utils.servers.fast_api import FastApiMiddleware, ServerOptions, AppConfiguration


async def get_configuration():
    required_env_vars = ["AUTH_HOST", "AUTH_CLIENT_ID", "AUTH_CLIENT_SECRET", "AUTH_CLIENT_SCOPE"]

    not_founds = [v for v in required_env_vars if not os.getenv(v)]
    if not_founds:
        raise RuntimeError(f"Missing environments variable: {not_founds}")

    storage = StorageClient(
        url_base="http://storage/api",
        bucket_name=Constants.namespace
    )
    doc_db_stories = DocDbClient(
        url_base="http://docdb/api",
        keyspace_name=Constants.namespace,
        table_body=STORIES_TABLE,
        replication_factor=2
    )
    doc_db_documents = DocDbClient(
        url_base="http://docdb/api",
        keyspace_name=Constants.namespace,
        table_body=DOCUMENTS_TABLE,
        secondary_indexes=[DOCUMENTS_TABLE_BY_ID],
        replication_factor=2
    )
    assets_gtw_client = AssetsGatewayClient(url_base="http://assets-gateway")

    openid_host = os.getenv("AUTH_HOST")
    auth_client = AuthClient(url_base=f"https://{openid_host}/auth")

    cache_client = CacheClient(host="redis-master.infra.svc.cluster.local", prefix=cache_prefix)

    async def _on_before_startup():
        await on_before_startup(service_config)

    service_config = Configuration(
        storage=storage,
        doc_db_stories=doc_db_stories,
        doc_db_documents=doc_db_documents,
        assets_gtw_client=assets_gtw_client,
        admin_headers=await get_headers_auth_admin_from_env()
    )
    server_options = ServerOptions(
        root_path='/api/stories-backend',
        http_port=8080,
        base_path="",
        middlewares=[
            FastApiMiddleware(
                Middleware, {
                    "auth_client": auth_client,
                    "cache_client": cache_client,
                    # healthz need to not be protected as it is used for liveness prob
                    "unprotected_paths": lambda url: url.path.split("/")[-1] == "healthz"
                }
            )
        ],
        on_before_startup=_on_before_startup,
        ctx_logger=DeployedContextLogger()
    )
    return AppConfiguration(
        server=server_options,
        service=service_config
    )
