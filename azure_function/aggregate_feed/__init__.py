import datetime
import json
import os
import logging
import traceback
from typing import Any, Dict, List

import azure.functions as func
from azure.storage.blob import BlobServiceClient

# Ensure repo root is on sys.path to import aggregator.py
import sys
CURRENT_DIR = os.path.dirname(__file__)
REPO_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, '..', '..'))
if REPO_ROOT not in sys.path:
    sys.path.append(REPO_ROOT)

from aggregator import UnifiedFeedAggregator


def _get_blob_service_client() -> BlobServiceClient:
    # Prefer Azure Functions default storage connection
    conn_str = os.getenv("AzureWebJobsStorage") or os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if not conn_str:
        raise RuntimeError("Storage connection string not found. Set AzureWebJobsStorage.")
    return BlobServiceClient.from_connection_string(conn_str)


def _ensure_container(client: BlobServiceClient, container_name: str) -> None:
    try:
        client.create_container(container_name)
    except Exception:
        pass  # Likely exists


def main(mytimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()
    logging.info("aggregate_feed start %s | site=%s", utc_timestamp, os.getenv('WEBSITE_SITE_NAME', 'unknown'))
    try:
        # Aggregate posts
        aggregator = UnifiedFeedAggregator()
        posts: List[Dict[str, Any]] = aggregator.load_posts_from_sources()
        logging.info("aggregate_feed collected %d posts", len(posts))

        # Serialize
        payload = json.dumps(posts, ensure_ascii=False)

        # Blob targets
        container_name = os.getenv("FEED_CONTAINER", "feeds")
        latest_blob_name = os.getenv("FEED_BLOB_NAME", "latest.json")
        dated_blob_name = f"{datetime.datetime.utcnow().strftime('%Y-%m-%d')}.json"

        # Upload
        bsc = _get_blob_service_client()
        _ensure_container(bsc, container_name)
        container = bsc.get_container_client(container_name)

        container.upload_blob(name=latest_blob_name, data=payload, overwrite=True, content_settings=None)
        container.upload_blob(name=dated_blob_name, data=payload, overwrite=True, content_settings=None)

        logging.info("aggregate_feed uploaded: %s/%s and %s/%s", container_name, latest_blob_name, container_name, dated_blob_name)
    except Exception as e:
        logging.error("aggregate_feed failed: %s", e)
        logging.error(traceback.format_exc())
        raise
