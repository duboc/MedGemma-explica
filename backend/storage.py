import uuid
from datetime import datetime, timezone

from google.cloud import storage

from config import settings


def get_storage_client() -> storage.Client:
    return storage.Client(project=settings.project_id)


def upload_image(file_bytes: bytes, filename: str, content_type: str) -> str:
    """Upload an image to GCS and return the blob path."""
    client = get_storage_client()
    bucket = client.bucket(settings.gcs_bucket)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    blob_path = f"xrays/{timestamp}_{unique_id}_{filename}"

    blob = bucket.blob(blob_path)
    blob.upload_from_string(file_bytes, content_type=content_type)

    return blob_path


def download_image(blob_path: str) -> bytes:
    """Download image bytes from GCS."""
    client = get_storage_client()
    bucket = client.bucket(settings.gcs_bucket)
    blob = bucket.blob(blob_path)
    return blob.download_as_bytes()
