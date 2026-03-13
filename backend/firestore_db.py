import uuid
from datetime import datetime, timezone

from google.cloud import firestore

from config import settings


def get_firestore_client() -> firestore.Client:
    return firestore.Client(project=settings.project_id)


def save_analysis(
    image_blob_path: str,
    object_name: str,
    response_text: str,
    bounding_boxes: list[dict],
    image_width: int,
    image_height: int,
    structure_names: list[str] | None = None,
    educational_infos: list[dict] | None = None,
) -> str:
    """Save an analysis result to Firestore. Returns the document ID."""
    client = get_firestore_client()
    doc_id = uuid.uuid4().hex

    data = {
        "id": doc_id,
        "image_blob_path": image_blob_path,
        "object_name": object_name,
        "response_text": response_text,
        "bounding_boxes": bounding_boxes,
        "image_width": image_width,
        "image_height": image_height,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if structure_names:
        data["structure_names"] = structure_names
    if educational_infos:
        data["educational_infos"] = educational_infos

    doc_ref = client.collection(settings.firestore_collection).document(doc_id)
    doc_ref.set(data)

    return doc_id


def get_analysis(doc_id: str) -> dict | None:
    """Retrieve a single analysis by ID."""
    client = get_firestore_client()
    doc = client.collection(settings.firestore_collection).document(doc_id).get()
    if doc.exists:
        return doc.to_dict()
    return None


def list_analyses(limit: int = 20) -> list[dict]:
    """List recent analyses ordered by creation time."""
    client = get_firestore_client()
    docs = (
        client.collection(settings.firestore_collection)
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )
    return [doc.to_dict() for doc in docs]


def update_analysis(doc_id: str, fields: dict) -> None:
    """Update specific fields on an existing analysis document."""
    client = get_firestore_client()
    doc_ref = client.collection(settings.firestore_collection).document(doc_id)
    fields["updated_at"] = datetime.now(timezone.utc).isoformat()
    doc_ref.update(fields)


def delete_analysis(doc_id: str) -> None:
    """Delete a single analysis by ID."""
    client = get_firestore_client()
    client.collection(settings.firestore_collection).document(doc_id).delete()


def delete_all_analyses() -> None:
    """Delete all analyses."""
    client = get_firestore_client()
    docs = client.collection(settings.firestore_collection).stream()
    for doc in docs:
        doc.reference.delete()
