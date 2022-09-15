import os

from config_common import on_before_startup
from youwol_stories_backend import Configuration, Constants
from youwol_utils import StorageClient, DocDbClient, get_authorization_header
from youwol_utils.clients.assets_gateway.assets_gateway import AssetsGatewayClient
from youwol_utils.clients.oidc.oidc_config import PrivateClient, OidcInfos
from youwol_utils.context import DeployedContextReporter
from youwol_utils.http_clients.stories_backend import STORIES_TABLE, DOCUMENTS_TABLE, DOCUMENTS_TABLE_BY_ID
from youwol_utils.middlewares import AuthMiddleware
from youwol_utils.servers.env import OPENID_CLIENT, Env
from youwol_utils.servers.fast_api import FastApiMiddleware, ServerOptions, AppConfiguration


async def get_configuration():
    required_env_vars = OPENID_CLIENT

    not_founds = [v for v in required_env_vars if not os.getenv(v)]
    if not_founds:
        raise RuntimeError(f"Missing environments variable: {not_founds}")

    openid_infos = OidcInfos(
        base_uri=os.getenv(Env.OPENID_BASE_URL),
        client=PrivateClient(
            client_id=os.getenv(Env.OPENID_CLIENT_ID),
            client_secret=os.getenv(Env.OPENID_CLIENT_SECRET)
        )
    )

    async def _on_before_startup():
        await on_before_startup(service_config)

    service_config = Configuration(
        storage=StorageClient(
            url_base="http://storage/api",
            bucket_name=Constants.namespace
        ),
        doc_db_stories=DocDbClient(
            url_base="http://docdb/api",
            keyspace_name=Constants.namespace,
            table_body=STORIES_TABLE,
            replication_factor=2
        ),
        doc_db_documents=DocDbClient(
            url_base="http://docdb/api",
            keyspace_name=Constants.namespace,
            table_body=DOCUMENTS_TABLE,
            secondary_indexes=[DOCUMENTS_TABLE_BY_ID],
            replication_factor=2
        ),
        assets_gtw_client=AssetsGatewayClient(url_base="http://assets-gateway"),
        admin_headers=await get_authorization_header(openid_infos)
    )
    server_options = ServerOptions(
        root_path='/api/stories-backend',
        http_port=8080,
        base_path="",
        middlewares=[
            FastApiMiddleware(
                AuthMiddleware, {
                    'openid_infos': openid_infos,
                    'predicate_public_path': lambda url:
                    url.path.endswith("/healthz")
                }
            )
        ],
        on_before_startup=_on_before_startup,
        ctx_logger=DeployedContextReporter()
    )
    return AppConfiguration(
        server=server_options,
        service=service_config
    )
