"""
AWS Lambda — Document Validation
First step in the Step Functions ingestion pipeline.

Validates an uploaded document before it enters the embedding pipeline:
  - allowed file type
  - within size limits
  - non-empty / readable

Invoked by Step Functions with:
  { "bucket": "<s3-bucket>", "key": "<object-key>" }

Returns:
  { "valid": bool, "document_type": str, "reason": str }
"""
import os

import boto3

s3 = boto3.client("s3")

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".docx"}
MAX_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB
MIN_SIZE_BYTES = 10                # reject empty files

# Map S3 key prefix to a document_type used downstream for metadata
PREFIX_TO_TYPE = {
    "policies/": "policy",
    "runbooks/": "runbook",
    "incident_reports/": "incident_report",
}


def _document_type(key: str) -> str:
    for prefix, doc_type in PREFIX_TO_TYPE.items():
        if prefix in key:
            return doc_type
    return "unknown"


def _extension(key: str) -> str:
    _, ext = os.path.splitext(key)
    return ext.lower()


def handler(event, context):
    bucket = event["bucket"]
    key = event["key"]

    ext = _extension(key)
    if ext not in ALLOWED_EXTENSIONS:
        return {
            "valid": False,
            "document_type": "unknown",
            "reason": f"Unsupported file extension '{ext}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        }

    try:
        head = s3.head_object(Bucket=bucket, Key=key)
    except Exception as e:  # noqa: BLE001
        return {
            "valid": False,
            "document_type": "unknown",
            "reason": f"Could not read object metadata: {e}",
        }

    size = head["ContentLength"]
    if size < MIN_SIZE_BYTES:
        return {"valid": False, "document_type": "unknown", "reason": "File is empty."}
    if size > MAX_SIZE_BYTES:
        return {
            "valid": False,
            "document_type": "unknown",
            "reason": f"File too large ({size} bytes). Max is {MAX_SIZE_BYTES}.",
        }

    return {
        "valid": True,
        "document_type": _document_type(key),
        "reason": "ok",
    }
