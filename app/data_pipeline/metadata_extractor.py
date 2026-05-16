from pathlib import Path


_DIR_TO_DOC_TYPE = {
    "policies": "policy",
    "runbooks": "runbook",
    "incident_reports": "incident_report",
}

_FILENAME_TO_SERVICE = {
    "payment": "payment-api",
    "database": "database",
    "auth": "auth-service",
    "monitoring": "monitoring",
    "deployment": "deployment",
    "customer": "customer-data",
    "notification": "notification-service",
}


def extract_metadata(file_path: Path, chunk_index: int, chunk_id: str) -> dict:
    """Build metadata dict for a chunk from its source file path."""
    parts = file_path.parts
    doc_type = "unknown"
    for part in parts:
        if part in _DIR_TO_DOC_TYPE:
            doc_type = _DIR_TO_DOC_TYPE[part]
            break

    service = "general"
    name_lower = file_path.stem.lower()
    for keyword, svc in _FILENAME_TO_SERVICE.items():
        if keyword in name_lower:
            service = svc
            break

    return {
        "chunk_id": chunk_id,
        "source_file": file_path.name,
        "source_path": str(file_path),
        "document_type": doc_type,
        "service": service,
        "chunk_index": chunk_index,
    }
