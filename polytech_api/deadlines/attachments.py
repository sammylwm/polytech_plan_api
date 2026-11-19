import logging
from contextlib import contextmanager
from http import HTTPStatus
from pathlib import Path

from django.db import transaction
from dmr import APIError

from .models import DeadlineAttachment


logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = frozenset(
    """
    .pdf .doc .docx .xls .xlsx .ppt .pptx .odt .ods .odp .rtf .txt .csv .md
    .jpg .jpeg .png .gif .webp .bmp .tif .tiff .heic .heif .avif
    .zip .rar .7z
    """.split()
)
MAX_FILES = 5
MAX_FILE_SIZE = 20 * 1024 * 1024


def attachment_uploads(request):
    uploads = request.FILES.getlist("attachments")
    if request.FILES.keys() - {"attachments"} or len(uploads) > MAX_FILES:
        raise APIError(
            {"detail": "Передайте до 5 файлов в поле attachments"},
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        )
    for upload in uploads:
        extension = Path(upload.name).suffix.lower()
        content_type = (upload.content_type or "").lower()
        if extension not in ALLOWED_EXTENSIONS or content_type.startswith("video/"):
            raise APIError(
                {"detail": "Этот тип файла не поддерживается"},
                status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            )
        if upload.size > MAX_FILE_SIZE:
            raise APIError(
                {"detail": "Размер файла превышает 20 МиБ"},
                status_code=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            )
    return uploads


@contextmanager
def attachment_transaction(uploads):
    saved_files = []

    def save_attachments(deadline):
        for upload in uploads:
            attachment = DeadlineAttachment(
                deadline=deadline, name=upload.name, size=upload.size
            )
            extension = Path(upload.name).suffix.lower()
            attachment.file.save(f"{attachment.pk.hex}{extension}", upload, save=False)
            saved_files.append(attachment.file)
            attachment.save(force_insert=True)

    try:
        with transaction.atomic():
            yield save_attachments
    except Exception:
        for file in saved_files:
            try:
                file.storage.delete(file.name)
            except OSError:
                logger.exception("Failed to remove rolled-back attachment %s", file.name)
        raise
