import os
import sys
from dataclasses import dataclass
from typing import Union, Callable, Type, Dict, Coroutine, Any

from youwol_utils import (
    AuthClient, CacheClient, LocalCacheClient, LocalDocDbClient,
    LocalStorageClient, DocDbClient, StorageClient, find_platform_path,
    get_headers_auth_admin_from_env, get_headers_auth_admin_from_secrets_file, log_info,
)
from youwol_utils.context import ContextLogger, DeployedContextLogger
from youwol_utils.middlewares import Middleware
from youwol_utils.middlewares.authentication_local import AuthLocalMiddleware
from .models import DOCUMENTS_TABLE, STORIES_TABLE, DOCUMENTS_TABLE_BY_ID

DocDb = Union[DocDbClient, LocalDocDbClient]
Storage = Union[StorageClient, LocalStorageClient]
Cache = Union[CacheClient, LocalCacheClient]
AuthMiddleware = Union[Type[Middleware], Type[AuthLocalMiddleware]]


@dataclass(frozen=True)
class Configuration:
    open_api_prefix: str
    http_port: int
    base_path: str
    storage: Storage
    doc_db_stories: DocDb
    doc_db_documents: DocDb

    auth_middleware: AuthMiddleware
    auth_middleware_args: Dict[str, any]
    admin_headers: Union[Coroutine[Any, Any, Dict[str, str]], None]

    namespace: str = "stories"

    cache_prefix: str = "stories-backend_"

    unprotected_paths: Callable[[str], bool] = lambda url: \
        url.path.split("/")[-1] == "healthz" or url.path.split("/")[-1] == "openapi-docs"

    replication_factor: int = 2

    default_owner = "/youwol-users"

    local_http_port: int = 2534

    text_content_type = "text/plain"

    ctx_logger: ContextLogger = DeployedContextLogger()


async def get_tricot_config() -> Configuration:
    required_env_vars = ["AUTH_HOST", "AUTH_CLIENT_ID", "AUTH_CLIENT_SECRET", "AUTH_CLIENT_SCOPE"]
    not_founds = [v for v in required_env_vars if not os.getenv(v)]
    if not_founds:
        raise RuntimeError(f"Missing environments variable: {not_founds}")
    openid_host = os.getenv("AUTH_HOST")

    log_info("Use tricot configuration", openid_host=openid_host)

    storage = StorageClient(
        url_base="http://storage/api",
        bucket_name=Configuration.namespace
    )
    doc_db_stories = DocDbClient(
        url_base="http://docdb/api",
        keyspace_name=Configuration.namespace,
        table_body=STORIES_TABLE,
        replication_factor=Configuration.replication_factor
    )
    doc_db_documents = DocDbClient(
        url_base="http://docdb/api",
        keyspace_name=Configuration.namespace,
        table_body=DOCUMENTS_TABLE,
        secondary_indexes=[DOCUMENTS_TABLE_BY_ID],
        replication_factor=Configuration.replication_factor
    )

    auth_client = AuthClient(url_base=f"https://{openid_host}/auth")
    cache_client = CacheClient(host="redis-master.infra.svc.cluster.local", prefix=Configuration.cache_prefix)
    return Configuration(
        open_api_prefix='/api/stories-backend',
        http_port=8080,
        base_path="",
        storage=storage,
        doc_db_stories=doc_db_stories,
        doc_db_documents=doc_db_documents,
        auth_middleware=Middleware,
        auth_middleware_args={
            "auth_client": auth_client,
            "cache_client": cache_client,
            "unprotected_paths": Configuration.unprotected_paths
        },
        admin_headers=get_headers_auth_admin_from_env()
    )


async def get_remote_clients_config(url_cluster) -> Configuration:
    openid_host = "gc.auth.youwol.com"
    storage = StorageClient(
        url_base=f"https://{url_cluster}/api/storage",
        bucket_name=Configuration.namespace
    )
    doc_db_stories = DocDbClient(
        url_base=f"https://{url_cluster}/api/docdb",
        keyspace_name=Configuration.namespace,
        table_body=STORIES_TABLE,
        replication_factor=Configuration.replication_factor
    )
    doc_db_documents = DocDbClient(
        url_base=f"https://{url_cluster}/api/docdb",
        keyspace_name=Configuration.namespace,
        table_body=DOCUMENTS_TABLE,
        secondary_indexes=[DOCUMENTS_TABLE_BY_ID],
        replication_factor=Configuration.replication_factor
    )

    auth_client = AuthClient(url_base=f"https://{openid_host}/auth")
    cache_client = LocalCacheClient(prefix=Configuration.cache_prefix)

    return Configuration(
        open_api_prefix='/api/stories-backend',
        http_port=Configuration.local_http_port,
        base_path="",
        storage=storage,
        doc_db_stories=doc_db_stories,
        doc_db_documents=doc_db_documents,
        auth_middleware=Middleware,
        auth_middleware_args={
            "auth_client": auth_client,
            "cache_client": cache_client,
            "unprotected_paths": Configuration.unprotected_paths
        },
        admin_headers=get_headers_auth_admin_from_secrets_file(
            file_path=find_platform_path() / "secrets" / "tricot.json",
            url_cluster=url_cluster,
            openid_host=openid_host
        )
    )


async def get_full_local_config() -> Configuration:
    platform_path = find_platform_path()
    storage = LocalStorageClient(
        root_path=platform_path.parent / 'drive-shared' / 'storage',
        bucket_name=Configuration.namespace
    )

    doc_db_stories = LocalDocDbClient(
        root_path=platform_path.parent / 'drive-shared' / 'docdb',
        keyspace_name=Configuration.namespace,
        table_body=STORIES_TABLE
    )

    doc_db_documents = LocalDocDbClient(
        root_path=platform_path.parent / 'drive-shared' / 'docdb',
        keyspace_name=Configuration.namespace,
        table_body=DOCUMENTS_TABLE,
        secondary_indexes=[DOCUMENTS_TABLE_BY_ID]
    )

    return Configuration(
        open_api_prefix='',
        http_port=Configuration.local_http_port,
        base_path="",
        storage=storage,
        doc_db_stories=doc_db_stories,
        doc_db_documents=doc_db_documents,
        auth_middleware=AuthLocalMiddleware,
        auth_middleware_args={},
        admin_headers=None
    )


async def get_remote_clients_gc_config() -> Configuration:
    return await get_remote_clients_config("gc.platform.youwol.com")


configurations = {
    'tricot': get_tricot_config,
    'remote-clients': get_remote_clients_gc_config,
    'full-local': get_full_local_config
}

current_configuration = None


async def get_configuration():
    global current_configuration
    if current_configuration:
        return current_configuration

    current_configuration = await configurations[sys.argv[1]]()
    return current_configuration
