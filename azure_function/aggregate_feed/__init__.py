import datetime
import json
import os
import logging
import traceback
from typing import Any, Dict, List
from urllib.parse import urlparse

import azure.functions as func

# Ensure repo root is on sys.path to import aggregator.py
import sys
CURRENT_DIR = os.path.dirname(__file__)
# The Functions host adds site/wwwroot to sys.path; aggregator.py is deployed at that root.
# No extra sys.path manipulation is strictly required, but keep for safety if layout differs.
REPO_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, '..'))
if REPO_ROOT not in sys.path:
    sys.path.append(REPO_ROOT)


def _get_blob_service_client():
    # Prefer Azure Functions default storage connection
    conn_str = os.getenv("AzureWebJobsStorage") or os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if not conn_str:
        raise RuntimeError("Storage connection string not found. Set AzureWebJobsStorage.")
    try:
        from azure.storage.blob import BlobServiceClient  # defer import for clear error if missing
    except ModuleNotFoundError:
        logging.error("Missing azure-storage-blob. Ensure remote build installs requirements.txt and delete stale .python_packages if present.")
        raise
    return BlobServiceClient.from_connection_string(conn_str)


def _ensure_container(client: Any, container_name: str) -> None:
    try:
        client.create_container(container_name)
    except Exception:
        pass  # Likely exists


def main(mytimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()
    logging.info("aggregate_feed start %s | site=%s", utc_timestamp, os.getenv('WEBSITE_SITE_NAME', 'unknown'))
    try:
        # Import aggregator lazily so import errors are captured in logs
        from aggregator import UnifiedFeedAggregator
        aggregator = UnifiedFeedAggregator()
        posts: List[Dict[str, Any]] = aggregator.load_posts_from_sources()
        logging.info("aggregate_feed collected %d posts", len(posts))

        # Serialize
        payload = json.dumps(posts, ensure_ascii=False)

        # Blob targets
        container_name = os.getenv("FEED_CONTAINER", "feeds")
        latest_blob_name = os.getenv("FEED_BLOB_NAME", "latest.json")
        dated_blob_name = f"{datetime.datetime.utcnow().strftime('%Y-%m-%d')}.json"

        # Use Azure SDK client with connection string (requires azure-storage-blob and cryptography pinned)
        bsc = _get_blob_service_client()
        try:
            _ensure_container(bsc, container_name)
        except Exception as ce:
            logging.warning("Container ensure failed or already exists: %s", ce)
        container = bsc.get_container_client(container_name)
        container.upload_blob(name=latest_blob_name, data=payload.encode('utf-8'), overwrite=True)
        container.upload_blob(name=dated_blob_name, data=payload.encode('utf-8'), overwrite=True)

        logging.info("aggregate_feed uploaded: %s/%s and %s/%s", container_name, latest_blob_name, container_name, dated_blob_name)
    except Exception as e:
        logging.error("aggregate_feed failed: %s", e)
        logging.error(traceback.format_exc())
        raise
