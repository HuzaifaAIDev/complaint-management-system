"""
Secure file handling: random internal filenames, extension whitelist,
size limits (enforced globally via MAX_CONTENT_LENGTH), and best-effort
content sniffing. Client-provided filenames/MIME types are NEVER trusted
for anything beyond display.
"""
import os
import uuid
from flask import current_app
from werkzeug.utils import secure_filename

try:
    import magic  # python-magic, optional but recommended
    _HAS_MAGIC = True
except Exception:
    _HAS_MAGIC = False

# Map allowed extensions to expected sniffed MIME prefixes (best effort).
_EXT_MIME_HINTS = {
    "pdf": ("application/pdf",),
    "png": ("image/png",),
    "jpg": ("image/jpeg",),
    "jpeg": ("image/jpeg",),
    "gif": ("image/gif",),
    "txt": ("text/plain",),
    "csv": ("text/plain", "text/csv"),
    "doc": ("application/msword", "application/x-ole-storage"),
    "docx": ("application/zip", "application/x-zip"),
    "xls": ("application/vnd.ms-excel", "application/x-ole-storage"),
    "xlsx": ("application/zip", "application/x-zip"),
}


class UploadRejected(Exception):
    pass


def _extension_of(filename: str) -> str:
    if "." not in filename:
        return ""
    return filename.rsplit(".", 1)[1].lower()


def validate_and_store(file_storage, subdirectory: str) -> dict:
    """
    Validates an uploaded werkzeug FileStorage and stores it under
    UPLOAD_FOLDER/<subdirectory>/<random-uuid>.<ext> with a filesystem-safe,
    server-generated filename. Returns metadata to persist in the DB.
    Raises UploadRejected on any validation failure.
    """
    if file_storage is None or file_storage.filename == "":
        raise UploadRejected("No file provided")

    original_name = secure_filename(file_storage.filename)
    if not original_name:
        raise UploadRejected("Invalid filename")

    ext = _extension_of(original_name)
    allowed = current_app.config["ALLOWED_UPLOAD_EXTENSIONS"]
    if ext not in allowed:
        raise UploadRejected(f"File type '.{ext}' is not permitted")

    # Read a small header for sniffing without loading entire file into memory.
    head = file_storage.stream.read(2048)
    file_storage.stream.seek(0)

    if _HAS_MAGIC:
        try:
            sniffed = magic.from_buffer(head, mime=True)
        except Exception:
            sniffed = None
        hints = _EXT_MIME_HINTS.get(ext)
        if sniffed and hints and not any(sniffed.startswith(h) for h in hints):
            raise UploadRejected("File content does not match its extension")

    # Reject anything that looks like an executable/script regardless of extension.
    if head[:2] == b"MZ" or head[:4] == b"\x7fELF":
        raise UploadRejected("Executable files are not permitted")

    upload_root = current_app.config["UPLOAD_FOLDER"]
    target_dir = os.path.abspath(os.path.join(upload_root, subdirectory))
    # Path traversal guard: resolved target_dir must stay within upload_root.
    if not target_dir.startswith(os.path.abspath(upload_root)):
        raise UploadRejected("Invalid storage path")
    os.makedirs(target_dir, exist_ok=True)

    internal_name = f"{uuid.uuid4().hex}.{ext}"
    dest_path = os.path.join(target_dir, internal_name)
    file_storage.save(dest_path)
    size = os.path.getsize(dest_path)

    return {
        "file_path": os.path.join(subdirectory, internal_name),
        "original_filename": original_name,
        "content_type": file_storage.mimetype,
        "size_bytes": size,
    }


def resolve_safe_path(relative_path: str) -> str:
    """Resolves a DB-stored relative path to an absolute path, guaranteed to
    stay inside UPLOAD_FOLDER. Raises UploadRejected on any traversal attempt."""
    upload_root = os.path.abspath(current_app.config["UPLOAD_FOLDER"])
    candidate = os.path.abspath(os.path.join(upload_root, relative_path))
    if not candidate.startswith(upload_root + os.sep) and candidate != upload_root:
        raise UploadRejected("Invalid file path")
    if not os.path.isfile(candidate):
        raise UploadRejected("File not found")
    return candidate
