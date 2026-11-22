"""Private storage for professionals' CVs.

CVs hold personal data, so they live outside UPLOAD_DIR (which is publicly mounted at /static)
and are only ever streamed back through authenticated endpoints.
"""
import os
import re
import uuid
import zipfile
from pathlib import Path
from typing import Optional

RESUME_DIR = Path(os.getenv("PRIVATE_UPLOAD_DIR", "private_uploads")) / "resumes"
MAX_RESUME_BYTES = 10 * 1024 * 1024
RESUME_TYPES = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
_MAGIC = {".pdf": (b"%PDF",), ".docx": (b"PK\x03\x04",), ".doc": (b"\xd0\xcf\x11\xe0",)}


class ResumeError(ValueError):
    pass


def clean_filename(name: Optional[str]) -> str:
    base = os.path.basename(name or "").strip() or "cv"
    return re.sub(r"[\x00-\x1f]", "", base)[:255]


def validate(filename: str, data: bytes) -> str:
    """Return the lower-case extension, or raise ResumeError with a message people can act on."""
    ext = Path(filename).suffix.lower()
    if ext not in RESUME_TYPES:
        raise ResumeError("Upload your CV as a PDF or Word file (.pdf, .docx or .doc).")
    if not data:
        raise ResumeError("That file is empty.")
    if len(data) > MAX_RESUME_BYTES:
        raise ResumeError("Your CV is larger than 10 MB. Export a smaller PDF and try again.")
    if not data.startswith(_MAGIC[ext]):
        raise ResumeError(f"That file doesn't look like a real {ext} file. Export it again and retry.")
    return ext


def save(profile_id: str, ext: str, data: bytes) -> str:
    RESUME_DIR.mkdir(parents=True, exist_ok=True)
    path = RESUME_DIR / f"{profile_id}_{uuid.uuid4().hex}{ext}"
    path.write_bytes(data)
    os.chmod(path, 0o640)
    return str(path)


def resolve(stored_path: Optional[str]) -> Optional[Path]:
    """The stored file, only if it exists and sits inside RESUME_DIR."""
    if not stored_path:
        return None
    path = Path(stored_path).resolve()
    root = RESUME_DIR.resolve()
    if root not in path.parents or not path.is_file():
        return None
    return path


def delete(stored_path: Optional[str]) -> None:
    path = resolve(stored_path)
    if path:
        from app.services.ai_profile_service import forget_cached_analysis
        forget_cached_analysis(str(path))
        try:
            path.unlink()
        except OSError:
            pass


def media_type(filename: str) -> str:
    return RESUME_TYPES.get(Path(filename).suffix.lower(), "application/octet-stream")


def docx_text(path: Path) -> str:
    """Plain text from a .docx (paragraphs from word/document.xml), without extra dependencies."""
    try:
        with zipfile.ZipFile(path) as z:
            xml = z.read("word/document.xml").decode("utf-8", errors="ignore")
    except (KeyError, zipfile.BadZipFile, OSError):
        return ""
    xml = re.sub(r"</w:p>", "\n", xml)
    xml = re.sub(r"<w:tab/>", "\t", xml)
    text = re.sub(r"<[^>]+>", "", xml)
    for ent, ch in (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&apos;", "'")):
        text = text.replace(ent, ch)
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())
