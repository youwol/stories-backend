import asyncio
import math
import time
import zipfile
from pathlib import Path
from typing import IO, Union, Dict

from youwol_utils import log_info
from .configurations import Configuration
from .models import GetDocumentResp


async def init_resources(config: Configuration):
    log_info("Ensure database resources")
    headers = await config.admin_headers if config.admin_headers else {}

    log_info("Successfully retrieved authorization for resources creation")
    await asyncio.gather(
        config.doc_db_stories.ensure_table(headers=headers),
        config.doc_db_documents.ensure_table(headers=headers),
        config.storage.ensure_bucket(headers=headers)
    )
    log_info("resources initialization done")


async def query_document(document_id: str, configuration: Configuration, headers):
    docs = await configuration.doc_db_documents.query(
        query_body=f"document_id={document_id}#1",
        owner=Configuration.default_owner,
        headers=headers
    )
    return docs['documents'][0]


def position_start():
    t = time.time()
    delta = t - math.floor(t)
    return position_format(5e5 + delta)


def position_next(index: str):
    t = time.time()
    delta = t - math.floor(t)
    return position_format(math.floor(float(index)) + 1 + delta)


def position_format(index: float):
    decimal = "{:.6f}".format(index)
    return (6 - len(decimal.split('.')[0])) * "0" + decimal


def format_document_resp(docdb_doc: Dict[str, str]):
    return GetDocumentResp(
        documentId=docdb_doc['document_id'],
        parentDocumentId=docdb_doc['parent_document_id'],
        storyId=docdb_doc['story_id'],
        title=docdb_doc['title'],
        contentId=docdb_doc['content_id'],
        position=float(docdb_doc['position'])
    )


def extract_zip_file(
        file: IO,
        zip_path: Union[Path, str],
        dir_path: Union[Path, str]
):
    dir_path = str(dir_path)
    with open(zip_path, 'ab') as f:
        for chunk in iter(lambda: file.read(10000), b''):
            f.write(chunk)

    compressed_size = zip_path.stat().st_size

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(dir_path)

    return compressed_size