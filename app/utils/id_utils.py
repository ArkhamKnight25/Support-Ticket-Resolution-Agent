import hashlib


def generate_doc_id(filename: str) -> str:
    return hashlib.md5(filename.encode()).hexdigest()[:12]


def generate_chunk_id(doc_id: str, chunk_index: int) -> str:
    return f"{doc_id}_chunk_{chunk_index:04d}"
