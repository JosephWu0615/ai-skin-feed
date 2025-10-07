import datetime
import json
import os
import logging
import traceback
from typing import Any, Dict, List
import base64
import hashlib
import hmac
from urllib.parse import urlparse, quote

import azure.functions as func

# Ensure repo root is on sys.path to import aggregator.py
import sys
CURRENT_DIR = os.path.dirname(__file__)
# The Functions host adds site/wwwroot to sys.path; aggregator.py is deployed at that root.
# No extra sys.path manipulation is strictly required, but keep for safety if layout differs.
REPO_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, '..'))
if REPO_ROOT not in sys.path:
    sys.path.append(REPO_ROOT)


def _parse_conn_str(conn_str: str) -> Dict[str, str]:
    parts = dict(kv.split('=', 1) for kv in conn_str.split(';') if '=' in kv)
    return parts


def _storage_base_url(parts: Dict[str, str]) -> str:
    # Use BlobEndpoint if present; otherwise compose from AccountName/EndpointSuffix
    if 'BlobEndpoint' in parts:
        return parts['BlobEndpoint'].rstrip('/')
    account = parts['AccountName']
    suffix = parts.get('EndpointSuffix', 'core.windows.net')
    return f"https://{account}.blob.{suffix}"


def _canonicalized_headers(headers: Dict[str, str]) -> str:
    xms = {k.lower(): v for k, v in headers.items() if k.lower().startswith('x-ms-')}
    lines = [f"{k}:{xms[k].strip()}" for k in sorted(xms)]
    return "\n".join(lines)


def _canonicalized_resource(account: str, path: str, params: Dict[str, str]) -> str:
    # path should be like /container/blob or /container
    cr = f"/{account}{path}"
    if params:
        items = [(k.lower(), v) for k, v in params.items()]
        items.sort(key=lambda x: x[0])
        lines = [f"{k}:{v}" for k, v in items]
        return cr + "\n" + "\n".join(lines)
    return cr


def _build_auth_header(method: str, url: str, headers: Dict[str, str], account: str, key_b64: str, params: Dict[str, str]) -> str:
    # String-To-Sign per Azure Storage spec
    parsed = urlparse(url)
    path = parsed.path
    content_length = headers.get('Content-Length', '')
    # For PUT with zero length, some versions require empty string instead of 0. We keep as given.
    sts = "\n".join([
        method.upper(),
        headers.get('Content-Encoding', ''),
        headers.get('Content-Language', ''),
        content_length,
        headers.get('Content-MD5', ''),
        headers.get('Content-Type', ''),
        headers.get('Date', ''),
        headers.get('If-Modified-Since', ''),
        headers.get('If-Match', ''),
        headers.get('If-None-Match', ''),
        headers.get('If-Unmodified-Since', ''),
        headers.get('Range', ''),
        _canonicalized_headers(headers),
        _canonicalized_resource(account, path, params)
    ])
    key = base64.b64decode(key_b64)
    sig = base64.b64encode(hmac.new(key, sts.encode('utf-8'), hashlib.sha256).digest()).decode()
    return f"SharedKey {account}:{sig}"


def _ensure_container_shared_key(base_url: str, account: str, key_b64: str, container: str) -> None:
    import requests
    url = f"{base_url}/{quote(container)}?restype=container"
    headers = {
        'x-ms-date': datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT'),
        'x-ms-version': '2021-12-02',
        'Content-Length': '0',
    }
    auth = _build_auth_header('PUT', url, headers, account, key_b64, {'restype': 'container'})
    headers['Authorization'] = auth
    resp = requests.put(url, headers=headers)
    if resp.status_code not in (201, 202, 409):
        logging.warning("Create container failed: %s %s", resp.status_code, resp.text)


def _upload_blob_shared_key(base_url: str, account: str, key_b64: str, container: str, blob: str, payload: bytes, content_type: str = 'application/json') -> None:
    import requests
    url = f"{base_url}/{quote(container)}/{quote(blob)}"
    headers = {
        'x-ms-date': datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT'),
        'x-ms-version': '2021-12-02',
        'x-ms-blob-type': 'BlockBlob',
        'Content-Type': content_type,
        'Content-Length': str(len(payload)),
    }
    auth = _build_auth_header('PUT', url, headers, account, key_b64, {})
    headers['Authorization'] = auth
    resp = requests.put(url, headers=headers, data=payload)
    if resp.status_code not in (201,):
        raise RuntimeError(f"Blob upload failed {resp.status_code}: {resp.text}")


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

        # Use Shared Key auth via AzureWebJobsStorage (no external libs)
        conn_str = os.getenv("AzureWebJobsStorage") or os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        if not conn_str:
            raise RuntimeError("Storage connection string not found. Set AzureWebJobsStorage.")
        parts = _parse_conn_str(conn_str)
        account = parts['AccountName']
        key_b64 = parts['AccountKey']
        base_url = _storage_base_url(parts)

        _ensure_container_shared_key(base_url, account, key_b64, container_name)
        _upload_blob_shared_key(base_url, account, key_b64, container_name, latest_blob_name, payload.encode('utf-8'))
        _upload_blob_shared_key(base_url, account, key_b64, container_name, dated_blob_name, payload.encode('utf-8'))

        logging.info("aggregate_feed uploaded: %s/%s and %s/%s", container_name, latest_blob_name, container_name, dated_blob_name)
    except Exception as e:
        logging.error("aggregate_feed failed: %s", e)
        logging.error(traceback.format_exc())
        raise
