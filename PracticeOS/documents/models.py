import os
import uuid

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import models


def private_storage():
    """Files live outside any web-served directory; only the download view can read them."""
    return FileSystemStorage(location=settings.UPLOAD_ROOT)


def upload_path(instance, filename):
    # <firm id>/<random>.<ext>: one folder per tenant; the original name stays in the DB only,
    # so a crafted filename can never influence where a file is written.
    return f"{instance.firm_id}/{uuid.uuid4().hex}{os.path.splitext(filename)[1].lower()}"


class Document(models.Model):
    class Type(models.TextChoices):
        UPLOAD = "UPLOAD", "Uploaded file"
        LINK = "LINK", "Digital link"
        PHYSICAL = "PHYSICAL", "Physical file"

    firm = models.ForeignKey("accounts.Firm", on_delete=models.CASCADE, related_name="documents")
    client = models.ForeignKey("crm.Client", on_delete=models.CASCADE, related_name="documents")
    uploaded_by = models.ForeignKey("accounts.User", null=True, on_delete=models.SET_NULL, related_name="+")
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=10, choices=Type.choices, default=Type.UPLOAD)
    file = models.FileField(storage=private_storage, upload_to=upload_path, null=True, blank=True)
    url = models.URLField("Link", max_length=1000, blank=True, help_text="Google Drive, OneDrive, SharePoint, DMS…")
    physical_location = models.CharField("Storage location", max_length=255, blank=True, help_text="e.g. Cabinet B / Shelf 3 / Box 12")
    mime_type = models.CharField(max_length=120, blank=True)
    size_bytes = models.PositiveIntegerField(null=True, blank=True)
    financial_year = models.CharField(max_length=9, blank=True, help_text="e.g. 2025-26")
    category = models.CharField(max_length=60, blank=True)
    shared_with_client = models.BooleanField("Visible to the client in their portal", default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["firm", "client"])]

    def __str__(self):
        return self.name
